## tornado_weibo

Just a simple `RequestHandler` mixin for adding Weibo OAuth support to Tornado.

## Usage

The usage is similar to other auth mixins(Google, Facebook, ...) shipped with Tornado.

    class WeiboHandler(tornado.web.RequestHandler, WeiboMixin):

        @tornado.web.asynchronous
        def get(self):
            code = self.get_argument("code", None)
            if code:
                self.get_authenticated_user(
                    redirect_uri="http://example.com/back",
                    code=code,
                    callback=self.async_callback(self._on_authorize,
                        next=self.get_argument("next", "/"))
                )
                return
            self.authorize_redirect(
                redirect_uri="http://example.com/back")

        def _on_authorize(self, user, next='/'):
            if user is None:
                self.send_error()
                return

            # session expires in user["session_expires"] sec
            self.set_secure_cookie("weibo_session",
                tornado.escape.json_encode(user),
                math.ceil(user["session_expires"] / 86400.0))
            self.redirect(next)
