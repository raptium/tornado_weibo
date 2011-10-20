import tornado.ioloop
import tornado.web
import tornado.escape
import logging
import math
from tornado_weibo.auth import WeiboMixin


class AuthenticationHandler(tornado.web.RequestHandler, WeiboMixin):

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


class HomeHandler(tornado.web.RequestHandler):

    def get_current_user(self):
        session = self.get_secure_cookie("weibo_session")
        if session is None:
            return None
        user = tornado.escape.json_decode(session)
        return user

    def get_login_url(self):
        return "/login"

    @tornado.web.authenticated
    def get(self):
        user = self.get_current_user()
        self.write("hello %s, you are from %s?, data : <br> %s" % (
            user.get("name"),
            user.get("location"),
            tornado.escape.json_encode(user),
        ))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # change the settings here
    settings = {
        "weibo_app_key": "",
        "weibo_app_secret": "",
        "cookie_secret": "",
    }

    application = tornado.web.Application([
        (r"/login", AuthenticationHandler),
        (r"/back", AuthenticationHandler),
        (r"/", HomeHandler)
    ], **settings)
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
