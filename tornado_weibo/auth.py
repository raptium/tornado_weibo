import os
import urllib
import logging
import mimetools
import itertools
from tornado.auth import OAuth2Mixin
from tornado.httputil import url_concat
from tornado import httpclient
from tornado import escape

# the default ca-certs shipped with Ubuntu failed to validate Weibo's cert
# we are using our own ca-certs(added GeoTrust CAs) here
_CA_CERTS = os.path.dirname(__file__) + "/ca-certificates.crt"

class WeiboMixin(OAuth2Mixin):
    """
    RequestHandler mixin for weibo authentication.
    """
    _OAUTH_ACCESS_TOKEN_URL = "https://api.weibo.com/oauth2/access_token?"
    _OAUTH_AUTHORIZE_URL = "https://api.weibo.com/oauth2/authorize?"
    _OAUTH_NO_CALLBACKS = False

    def authorize_redirect(self, redirect_uri, extra_params=None):
        """
        Redirect user to the weibo authorization page.

        User will be redirected to ``redirect_uri`` after he/she accepts/rejects
        the authorization request. If the user accepts the request, ``redirect_uri``
        will be visited with ``code`` parameter in HTTP GET, usually
        ``code`` will be further filled to :func:`get_authenticated_user`
        to obtain the ``access_code`` for later use.
        """
        self.require_setting("weibo_app_key", "Weibo OAuth2")
        args = {
            "redirect_uri": redirect_uri,
            "client_id": self.settings["weibo_app_key"],
            }
        if extra_params:
            args.update(extra_params)
        self.redirect(
            url_concat(self._OAUTH_AUTHORIZE_URL, args)
        )

    def get_authenticated_user(self, redirect_uri,
                               code, callback, extra_fields=None):
        """
        Get the authenticated user by given ``authorization_code``

        The ``callback`` function will be called with response of
        ``/users/show`` which is a dict with some information
        of specific user. ``access_token`` and ``session_expires``
        are also set in this dict, you should store ``access_token``
        to database/session for later use.

        This function calls ``OAuth2/access_token``, ``/account/get_uid``
        and ``/users/show`` internally, see
        http://open.weibo.com/wiki/OAuth2/access_token
        """
        self.require_setting("weibo_app_key", "Weibo OAuth2")
        self.require_setting("weibo_app_secret", "Weibo OAuth2")
        http = httpclient.AsyncHTTPClient()
        args = {
            "redirect_uri": redirect_uri,
            "extra_params": {"grant_type": 'authorization_code'},
            "code": code,
            "client_id": self.settings["weibo_app_key"],
            "client_secret": self.settings["weibo_app_secret"],
            }

        fields = {'id', 'name', 'profile_image_url', 'location', 'url'}
        if extra_fields:
            fields.update(extra_fields)

        # Weibo's oauth2 access_token only accepts POST method
        http.fetch(self._OAUTH_ACCESS_TOKEN_URL, method="POST",
            body=urllib.urlencode(args),
            callback=self.async_callback(self._on_access_token,
                callback, fields),
            ca_certs=_CA_CERTS
        )

    def _on_access_token(self, callback, fields, response):
        if response.error:
            logging.warning('Weibo auth error: %s' % str(response))
            callback(None)
            return

        session = escape.json_decode(response.body)

        self.weibo_request(
            path="/account/get_uid",
            callback=self.async_callback(
                self._on_get_uid, callback, session, fields),
            access_token=session["access_token"]
        )

    def _on_get_uid(self, callback, session, fields, response):
        if response is None or not "uid" in response:
            callback(None)
            return

        self.weibo_request(
            path="/users/show",
            callback=self.async_callback(
                self._on_get_user_info, callback, session, fields),
            access_token=session["access_token"],
            uid=response["uid"]
        )

    def _on_get_user_info(self, callback, session, fields, user):
        if user is None:
            callback(None)
            return

        fieldmap = {}
        for field in fields:
            fieldmap[field] = user.get(field)

        fieldmap.update({"access_token": session["access_token"],
                         "session_expires": session.get("expires_in")})
        callback(fieldmap)

    def weibo_request(self, path, callback, access_token=None,
                      post_args=None, **args):
        """
        This is a helper function to send Weibo API requests.

        ``path`` should be set to the API path which the request is sent to,
        e.g. ``'statuses/public_timeline'``

        The ``callback`` function will be called when the request finishes.
        The response json will be decoded and passed to the callback function.

        If ``post_args`` is given, the request will be sent using POST method
        with ``post_args``. Other parameters given in ``args`` will be send
        as HTTP GET parameters.

        .. note:: For ``/statuses/upload`` method, the ``pic`` parameter is
           required and it should be a dict with key ``filename``, ``content`` and
           ``mime_type``. ``/statuses/upload`` requires a ``multipart/form-data``
           post request, therefore it must be handled differently. tornado_weibo
           already knows how to construct a ``multipart/form-data`` request, so you
           don't have to do extra work besides providing the ``pic`` dict.
        """
        url = "https://api.weibo.com/2" + path + ".json"
        if path == "/statuses/upload":
            return self._weibo_upload_request(url, callback,
                access_token, args.get("pic"), status=args.get("status"))
        all_args = {}
        if access_token:
            all_args["access_token"] = access_token
            all_args.update(args)
            all_args.update(post_args or {})
        if all_args:
            url += "?" + urllib.urlencode(all_args)
        callback = self.async_callback(self._on_weibo_request, callback)
        http = httpclient.AsyncHTTPClient()
        if post_args is not None:
            http.fetch(url, method="POST", body=urllib.urlencode(post_args),
                callback=callback, ca_certs=_CA_CERTS)
        else:
            http.fetch(url, callback=callback, ca_certs=_CA_CERTS)

    def _weibo_upload_request(self, url, callback,
                              access_token, pic, status=None):
        # /statuses/upload is special
        if pic is None:
            raise Exception("pic not filled!")
        form = MultiPartForm()
        form.add_file("pic", pic["filename"], pic["content"], pic["mime_type"])

        form.add_field("status", status)
        headers = {
            "Content-Type": form.get_content_type(),
            }
        args = {
            "access_token": access_token
        }
        url += "?" + urllib.urlencode(args)
        http = httpclient.AsyncHTTPClient()
        http.fetch(url, method="POST", body=str(form),
            callback=self.async_callback(self._on_weibo_request, callback),
            headers=headers,
            ca_certs=_CA_CERTS)

    def _on_weibo_request(self, callback, response):
        if response.error:
            logging.warning("Error response %s fetching %s, body %s",
                response.error,
                response.request.url,
                response.body
            )
            callback(None)
            return
        callback(escape.json_decode(response.body))


class MultiPartForm(object):
    """Helper class to build a multipart form"""

    def __init__(self):
        self.form_fields = []
        self.files = []
        self.boundary = mimetools.choose_boundary()
        return

    def get_content_type(self):
        return 'multipart/form-data; boundary=%s' % self.boundary

    def add_field(self, name, value):
        """Add a simple field to the form data."""
        self.form_fields.append((name, value))
        return

    def add_file(self, fieldname, filename, body, mimetype):
        """Add a file to be uploaded."""
        self.files.append((fieldname, filename, mimetype, body))
        return

    def __str__(self):
        """Return a string representing the form data,
        including attached files.
        """
        # Build a list of lists, each containing "lines" of the
        # request.  Each part is separated by a boundary string.
        # Once the list is built, return a string where each
        # line is separated by '\r\n'.
        parts = []
        part_boundary = '--' + self.boundary

        # Add the form fields
        parts.extend(
            [part_boundary,
             'Content-Disposition: form-data; name="%s"' % name,
             '',
             value,
             ]
            for name, value in self.form_fields
        )

        # Add the files to upload
        parts.extend(
            [part_boundary,
             'Content-Disposition: form-data; name="%s"; filename="%s"' %\
             (field_name, filename),
             'Content-Type: %s' % content_type,
             '',
             body,
             ]
            for field_name, filename, content_type, body in self.files
        )

        # Flatten the list and add closing boundary marker,
        # then return CR+LF separated data
        flattened = list(itertools.chain(*parts))
        flattened.append('--' + self.boundary + '--')
        flattened.append('')
        return '\r\n'.join(flattened)