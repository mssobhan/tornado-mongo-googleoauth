import os.path
import tornado.auth
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.options
from tornado import gen
from tornado.options import define, options, parse_command_line
import datetime
import pymongo
from pymongo import Connection
from pymongo.errors import ConnectionFailure
import json
from bson import json_util
from bson.json_util import dumps
from tornado.escape import json_decode
from bson.objectid import ObjectId
from datetime import datetime,timedelta


define("port", default=8811, help="run on the given port", type=int)



class Application(tornado.web.Application):
    # This portion of the application gets used to startup the settings, 
    # this is part of the settings, and configurations
    def __init__(self):
        handlers = [
            (r"/", IndexHandler),
            (r"/main", MainHandler),
            (r"/auth/login", AuthHandler),
            (r"/auth/logout", LogoutHandler),
            (r"/dashboard", DashboardHandler),

        ]
        settings = dict(
            cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            login_url="/auth/login",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
            debug=True,
            autoescape=None,

        )
        tornado.web.Application.__init__(self, handlers, **settings)
        try:
            self.con = Connection(host="localhost",port=27017)
            print "Connected Successfully"
        except ConnectionFailure, e:
            sys.stderr.write("Could not connect to MongoDB: %s"%e)
        self.db = self.con["testdb"]
        assert self.db.connection==self.con


class BaseHandler(tornado.web.RequestHandler):
    # This is the BaseHandler which is being inherited every time by the different classes,
    # and you can add your own Base Handler, like based on CORS if you need for handling mobile login or so.
    def get_current_user(self):
        user_json = self.get_secure_cookie("authdemo_user")
        if not user_json: return None
        return tornado.escape.json_decode(user_json)
    @property
    def db(self):
        return self.application.db

#(r"/main", MainHandler),
class MainHandler(BaseHandler):
    # On Signin this page ultimately redirects to the dashboard.
    # You can place your own logic, wher you can evaluate different 
    # paramters and based on that decide the redirects.
    @tornado.web.authenticated
    def get(self):
        #name = tornado.escape.xhtml_escape(self.current_user["name"])
        self.redirect("/dashboard")

#(r"/profile", ProfileHandler),
class ProfileHandler(BaseHandler):
    # A blank page where you can enter all the information for UserProfile
    @tornado.web.authenticated
    def get(self):
        users = self.db.users.find_one({"email":self.get_current_user()["email"]})
        self.render("profile.html",user=users)



#(r"/", IndexHandler),
class IndexHandler(BaseHandler):
    # This is the default page of entry
    def get(self):
        self.render("index.html",user=self.get_current_user())


#(r"/auth/login", AuthHandler),
class AuthHandler(BaseHandler, tornado.auth.GoogleMixin):
    # Here we handle the Auth Login Information, 
    # and based on that inserting into the database 
    # in MongoDB using pymongo

    @gen.coroutine
    def get(self):
        if self.get_argument("openid.mode", None):
            user = yield self.get_authenticated_user()
            self.set_secure_cookie("authdemo_user",
                                   tornado.escape.json_encode(user))
            #db = self.application.db
            if self.db.users.find_one({"email":user["email"]}):
                self.redirect("/dashboard")
            else:

                u = {
                    "email":user["email"],
                    "name":user["name"],
                    "user_locale":user["locale"],
                    "user_claimed_id":user["claimed_id"],
                    "created_on":datetime.now(),
                    "modified_on":datetime.now(),
                    "organization":"",
                    "connected_assets":[],
                    "super_user":False,
                    "staff":False,
                    "subscribed_plan":[],
                    "credit_days":0,
                    "org_admin":True
                }
                self.db.users.insert(u)
                users = self.db.users.find({"email":user["email"]})

                self.redirect("/dashboard")

            return
        self.authenticate_redirect()

#(r"/dashboard", DashboardHandler),
class DashboardHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):

        self.render("dashboard.html",user=self.get_current_user())

#(r"/auth/logout", LogoutHandler),
class LogoutHandler(BaseHandler):
    def get(self):
        # This logs the user out of this demo app, but does not log them
        # out of Google.  Since Google remembers previous authorizations,
        # returning to this app will log them back in immediately with no
        # interaction (unless they have separately logged out of Google in
        # the meantime).
        self.clear_cookie("authdemo_user")
        self.redirect("/")
        #self.write('You are now logged out. '
        #           'Click <a href="/">here</a> to log back in.')

def main():
    parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
