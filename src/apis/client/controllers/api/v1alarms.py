#!/usr/bin/env python3

import os
import cherrypy
import redis
import req
from auth import *


# Redis
RHOST    =     os.getenv("REDIS_SERVICE_HOST", "redis.tgr.svc.cluster.local")
RPORT    = int(os.getenv("REDIS_SERVICE_PORT", "6379"))

keyNs   = "controller.rtdata."


@cherrypy.expose
class Alarms_v1(object):

    def __init__(self):
        self.sources = AlarmSources_v1()
        self.silence = AlarmSilence_v1()

    @cherrypy.tools.json_out()
    def GET(self, controllerid):

        accountid = AuthSession()

        if accountid == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = "controller.account.id." + controllerid
        if ds.exists(key):
            if not accountid == ds.get(key):
                raise cherrypy.HTTPError(403, "Unauthorized access.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return

        key = keyNs + "ids"
        if ds.exists(key) and ds.sismember(key, controllerid):
            key = keyNs + "status." + controllerid
            if ds.exists(key) and ds.get(key) == "online":

                alarm = ds.hgetall(keyNs + "alarm." + controllerid)

                alarm.pop("timeStamp")

                return {'data':alarm}
            else:
                print("ERROR: Unable to fetch alarm data for controller: {}".format(controllerid))
                raise cherrypy.HTTPError(502)
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return


@cherrypy.expose
class AlarmSources_v1(object):

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

        request = {'method':'GET','url':'alarm/sources'}

        response = req.request_handler(controllerid, request)

        if response["status_code"] == 200:
            return response["body"]
        else:
            raise cherrypy.HTTPError(502)
            return


@cherrypy.expose
class AlarmSilence_v1(object):

    @cherrypy.tools.json_out()
    def PUT(self, controllerid):

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

        request = {'method':'PUT','url':'alarm/silence'}

        response = req.request_handler(controllerid, request)

        if response["status_code"] == 202:
            cherrypy.response.status = 202
            return
        else:
            raise cherrypy.HTTPError(502)
            return


