User Guide
============

Installation
------------
tornado_weibo is not in the CheeseShop, it is still easy to install if
you are with `pip` and `git`:

.. code-block:: sh

  pip install git+git://github.com/raptium/tornado_weibo.git

Or you may manually download the archive from github and run ``python setup.py install``.

Usage
-----

.. py:currentmodule:: tornado_weibo.auth

Get the Access Code
*******************
Before you can access any user data via Weibo API, your app needs to get
authorized by the user, i.e. get the ``access_token`` of the corresponding
user. This is usually done in two steps:

- Call :func:`WeiboMixin.authorize_redirect` to get an authorization code
- Call :func:`WeiboMixin.get_authenticate_user` with the code you got in the
  first step to get an user dict. ``access_token`` is set in the user dict, you
  may want to store it in database/session so that it can be used later.

Example::

  class AuthenticationHandler(tornado.web.RequestHandler, WeiboMixin):
      @tornado.web.asynchronous
      def get(self):
          self.require_setting("weibo_callback_uri")
          code = self.get_argument("code", None)
          if code:
              self.get_authenticated_user(
                  redirect_uri=self.settings["weibo_callback_uri"],
                  code=code,
                  callback=self.async_callback(self._on_authorize,
                      next=self.get_cookie("login_next", "/"))
              )
              return
          if self.get_argument("next"):
              self.set_cookie("login_next", self.get_argument("next"))
          self.authorize_redirect(
              redirect_uri=self.settings["weibo_callback_uri"])

      def _on_authorize(self, user, next='/'):
          if user is None:
              self.send_error()
              return

          self.set_cookie("uid", str(user["id"])) # session cookie
          self.set_secure_cookie("weibo_session",
              tornado.escape.json_encode(user), 1)
          self.redirect(next)


Send Weibo API Request
**********************

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

