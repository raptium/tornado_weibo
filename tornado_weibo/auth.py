import os
import urllib
import logging
from tornado.auth import OAuth2Mixin
from tornado.httputil import url_concat
from tornado import httpclient
from tornado import escape

# the default ca-certs shipped with Ubuntu failed to validate Weibo's cert
# we are using our own ca-certs(added GeoTrust CAs) here
_CA_CERTS = os.path.dirname(__file__) + "/ca-certificates.crt"


class WeiboMixin(OAuth2Mixin):

    _OAUTH_ACCESS_TOKEN_URL = "https://api.weibo.com/oauth2/access_token?"
    _OAUTH_AUTHORIZE_URL = "https://api.weibo.com/oauth2/authorize?"
    _OAUTH_NO_CALLBACKS = False

    def authorize_redirect(self, redirect_uri, extra_params=None):
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

        fields = set(['id', 'name', 'profile_image_url', 'location', 'url'])
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
        url = "https://api.weibo.com/2" + path + ".json"
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

    def _on_weibo_request(self, callback, response):
        if response.error:
            logging.warning("Error response %s fetching %s", response.error,
                            response.request.url)
            callback(None)
            return
        callback(escape.json_decode(response.body))
