#!/usr/bin/env python3

import os
import cherrypy
import redis
import req
from auth import *


# Redis
RHOST    =     os.getenv("REDIS_SERVICE_HOST", "redis.tgr.svc.cluster.local")
RPORT    = int(os.getenv("REDIS_SERVICE_PORT", "6379"))


@cherrypy.expose
class Settings_v1(object):

    def __init__(self):
        self.environmental = EnvSetting_v1()
        self.alarms = AlarmSetting_v1()

    @cherrypy.tools.json_out()
    def GET(self, controllerid):

        accountid = AuthSession()

        if accountid == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

        try:
            keyStore = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = "controller.account.id." + controllerid
        if keyStore.exists(key):
            if not accountid == keyStore.get(key):
                raise cherrypy.HTTPError(403, "Unauthorized access.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return

        request = {'method':'GET','url':'settings'}

        response = req.request_handler(controllerid, request)

        if response["status_code"] == 200:
            return response["body"]
        else:
            raise cherrypy.HTTPError(502)
            return


@cherrypy.expose
@cherrypy.popargs('setting', 'value')
class EnvSetting_v1(object):

    def PUT(self, controllerid, setting, value):

        accountid = AuthSession()

        if accountid == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

        try:
            keyStore = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = "controller.account.id." + controllerid
        if keyStore.exists(key):
            if not accountid == keyStore.get(key):
                raise cherrypy.HTTPError(403, "Unauthorized access.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return

        request = {'method':'PUT','url':'settings/environmental/' + setting + "/" + value}

        response = req.request_handler(controllerid, request)

        if response["status_code"] == 202:
            cherrypy.response.status = 202
        else:
            raise cherrypy.HTTPError(502)

        return


@cherrypy.expose
@cherrypy.popargs('setting', 'value')
class AlarmSetting_v1(object):

    def PUT(self, controllerid, setting, value):

        accountid = AuthSession()

        if accountid == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

        try:
            keyStore = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = "controller.account.id." + controllerid
        if keyStore.exists(key):
            if not accountid == keyStore.get(key):
                raise cherrypy.HTTPError(403, "Unauthorized access.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return

        request = {'method':'PUT','url':'settings/alarms/' + setting + "/" + value}

        response = req.request_handler(controllerid, request)

        if response["status_code"] == 202:
            cherrypy.response.status = 202
        else:
            raise cherrypy.HTTPError(502)

        return


