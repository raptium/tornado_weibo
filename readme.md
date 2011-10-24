# tornado_weibo

Just a simple `RequestHandler` mixin for adding Weibo OAuth support to [Tornado](http://www.tornadoweb.org).

## Usage

The usage is similar to other auth mixins(Google, Facebook, ...) shipped with Tornado.

```python
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
        if not user:
            raise tornado.web.HTTPError(500, "Weibo auth failed")
        # Save the user with, e.g., set_secure_cookie()
```
