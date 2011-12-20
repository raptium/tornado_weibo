User Guide
============

Installation
------------
It is still easy to install if you are with `pip` and `git`:

.. code-block:: sh

  pip install git+git://github.com/raptium/tornado_weibo.git

Otherwise you may manually download the archive_ from github, extract the
archive to somewhere and run ``python setup.py install``.

.. _archive: https://github.com/raptium/tornado_weibo/zipball/master

Usage
-----

.. py:currentmodule:: tornado_weibo.auth

Get the Access Code
*******************
Before you can access any user data via Weibo API, your app needs to get
authorized by the user, i.e. get the ``access_token`` of the corresponding
user. This is usually done in two steps:

- Call :func:`WeiboMixin.authorize_redirect` to get an authorization code.
  User will be redirect to Weibo and be prompted if he/she want to 
  allow the authorization. Once the user makes decision, he/she will be
  redirected to the callback url you specified.
- Call :func:`WeiboMixin.get_authenticated_user` with the code you got in the
  first step, a dict containing user information will be passed to the callback
  function. ``access_token`` is also set in the user dict, you
  may want to store it in database/session so that it can be used later.

Example::

  class AuthenticationHandler(RequestHandler, WeiboMixin):
      def get(self):
          # the callback URL should be the same with that on your app info page.
          self.authorize_redirect(redirect_uri='http://example.net/callback')


  class CallbackHandler(RequestHandler, WeiboMixin):
      @asynchronous
      @gen.engine
      def get(self):
          user = yield gen.Task(self.get_authenticated_user,
              redirect_uri='http://example.net/callback',
              code=self.get_argument("code") # code is set if user accepts the authorization request
          )
          if user is None:
              self.send_error()
          else:
              self.set_cookie("uid", str(user["id"])) # get user id
              # store the access_token to cookie, perhaps not a good choice
              self.set_secure_cookie("weibo_access_token", user.access_token, 1)
              self.redirect('/')

Consume the Weibo API
**********************
:func:`WeiboMixin.weibo_request` is a helper function to send Weibo API
requests, you should provide parameters according to the Weibo API specification.
The response message will be parsed automatically and the result is
passed to the callback function. If ``post_args`` is given, the request
will be sent using POST method with ``post_args``. Anything in the keyword
arguments will sent as HTTP query string.

The following snippet fetches the latest 200 statuses of current user::

    class UserTimelineHandler(RequestHandler, WeiboMixin):
        @tornado.web.asynchronous
        @tornado.web.authenticated
        @tornado.gen.engine
        def get(self):
            # fetch usertime
            results = tornado.gen.Task(self.weibo_request,
                "/statuses/user_timeline",
                access_token=self.current_user["access_token"],
                count=200,
                uid=self.current_user["id"]
            )
            # do something with the results

.. note:: To send a request to ``/statuses/upload``, the ``pic`` parameter is
   required and it should be a dict with ``filename``, ``content`` and
   ``mime_type`` set.

   Example::

        class UploadHandler(RequestHandler, WeiboMixin):
            @asynchronous
            @gen.engine
            def get(self):
                # ...
                f = open('foo.png', 'r')
                pic = {
                    'filename': 'foo.png',
                    'content': f.read(),
                    'mime_type': 'image/png'
                }
                f.close()
                result = yield gen.Task(self.weibo_request, 'statuses/upload',
                    access_token=self.current_user["access_token"],
                    status='I like this photo!',
                    pic=pic
                )
                # do something with the result ...

Settings
--------
``weibo_app_key`` and ``weibo_app_secret`` are required for tornado_weibo
to work, you can get them from your app info page on http://open.weibo.com.
tornado_weibo reads it's settings from your tornado application setting::

    settings = {
        "weibo_app_key": "",
        "weibo_app_secret": "",
    }

    application = tornado.web.Application([
        (r"/login", AuthenticationHandler),
        (r"/back", AuthenticationHandler),
        (r"/", HomeHandler)
    ], **settings)

