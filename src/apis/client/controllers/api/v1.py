#!/usr/bin/env python3

import cherrypy
import json
import req
from auth import *

# Version & build
VERSION = "1.2"
BUILD   = os.getenv("TGR_API_BUILD", "X.xxx")

# Redis
RHOST   =     os.getenv("REDIS_SERVICE_HOST", "redis.tgr.svc.cluster.local")
RPORT   = int(os.getenv("REDIS_SERVICE_PORT", "6379"))

@cherrypy.expose
class V1(object):

    def __init__(self):
        self.controllers = Controllers_v1()
        self.version = Version_v1()


@cherrypy.expose
class Version_v1(object):

    @cherrypy.tools.json_out()
    def GET(self):
        return {'version':VERSION,'build':BUILD}


@cherrypy.expose
class Controllers_v1(object):

    def __init__(self):
        self.id = Controller_v1()


@cherrypy.expose
@cherrypy.popargs('controllerid')
class Controller_v1(object):

    @cherrypy.tools.json_out()
    def GET(self, controllerid, **kwargs):

        accountid = AuthSession()

        if accountid == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

        try:
            ks = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = "controller.account.id." + controllerid
        if ks.exists(key):
            if not accountid == ks.get(key):
                raise cherrypy.HTTPError(403, "Unauthorized access.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return

        if "query" in kwargs:

            request = {'type':'api','method':'GET','url':kwargs["query"]}

            response = req.request_handler(controllerid, request)

            if response["status_code"] == 200:
                return response["body"]
            else:
                raise cherrypy.HTTPError(response["status_code"])
                return

        elif "websocket" in kwargs:

            if kwargs["websocket"] == "open":
                response = req.websocket_handler("controller", "add", controllerid)

                if not response["status_code"] == 202:
                    raise cherrypy.HTTPError(response["status_code"])
                    return

                request = {'type':'websocket'}

                response = req.request_handler(controllerid, request)

                if not response["status_code"] == 202:
                    req.websocket_handler("controller", "remove", controllerid)
                    raise cherrypy.HTTPError(response["status_code"])
                    return

                response = req.websocket_handler("client", "add", controllerid)

                if not response["status_code"] == 202:
                    req.websocket_handler("controller", "remove", controllerid)
                    raise cherrypy.HTTPError(response["status_code"])
                    return

            elif kwargs["websocket"] == "pause":
                ks.hset("websocket.send", mapping={"request":"unsubscribe"})

            elif kwargs["websocket"] == "resume":
                ks.hset("websocket.send", mapping={"request":"subscribe"})

            elif kwargs["websocket"] == "close":
                ks.hset("websocket.send", mapping={"request":"close"})

                response = req.websocket_handler("controller", "remove", controllerid)

                if not response["status_code"] == 202:
                    print("Unable to remove controller websocket path. status code: {}".format(response["status_code"]))

                response = req.websocket_handler("client", "remove", controllerid)

                if not response["status_code"] == 202:
                    raise cherrypy.HTTPError(response["status_code"])
                    return
            else:
                raise cherrypy.HTTPError(400)
                return

        else:
            keyNs = "controller.requests."
            key = keyNs + "ids"

            if not ks.exists(key) or not ks.sismember(key, controllerid):
                raise cherrypy.HTTPError(404, "Controller id not found.")
                return
            else:
                key = keyNs + "status." + controllerid
                if ks.exists(key):
                    return {'status':ks.get(key)}
                else:
                    return {'status':'offline'}

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def PUT(self, controllerid, **kwargs):

        accountid = AuthSession()

        if accountid == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

        try:
            ks = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = "controller.account.id." + controllerid
        if ks.exists(key):
            if not accountid == ks.get(key):
                raise cherrypy.HTTPError(403, "Unauthorized access.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return

        if "url" in kwargs:

            request = {'type':'api','method':'PUT','url':kwargs["url"]}
            if any(cherrypy.request.json):
                request['json'] = cherrypy.request.json

            response = req.request_handler(controllerid, request)

            if response["status_code"] == 200:
                return response["body"]
            elif response["status_code"] == 202:
                cherrypy.response.status = 202
                return
            else:
                raise cherrypy.HTTPError(response["status_code"])
                return

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self, controllerid, **kwargs):

        accountid = AuthSession()

        if accountid == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

        try:
            ks = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = "controller.account.id." + controllerid
        if ks.exists(key):
            if not accountid == ks.get(key):
                raise cherrypy.HTTPError(403, "Unauthorized access.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return

        if "url" in kwargs:

            request = {'type':'api','method':'POST','url':kwargs["url"]}
            if any(cherrypy.request.json):
                request['json'] = cherrypy.request.json

            response = req.request_handler(controllerid, request)

            if response["status_code"] == 200:
                return response["body"]
            elif response["status_code"] == 202:
                cherrypy.response.status = 202
                return
            else:
                raise cherrypy.HTTPError(response["status_code"])
                return

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def DELETE(self, controllerid, **kwargs):

        accountid = AuthSession()

        if accountid == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

        try:
            ks = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = "controller.account.id." + controllerid
        if ks.exists(key):
            if not accountid == ks.get(key):
                raise cherrypy.HTTPError(403, "Unauthorized access.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return

        if "url" in kwargs:

            request = {'type':'api','method':'DELETE','url':kwargs["url"]}
            if any(cherrypy.request.json):
                request['json'] = cherrypy.request.json

            response = req.request_handler(controllerid, request)

            if response["status_code"] == 200:
                return response["body"]
            elif response["status_code"] == 202:
                cherrypy.response.status = 202
                return
            else:
                raise cherrypy.HTTPError(response["status_code"])
                return






