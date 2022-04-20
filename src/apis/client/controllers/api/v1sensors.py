#!/usr/bin/env python3

import os
import datetime as dt
import cherrypy
import redis
import json
import req
from auth import *

# Redis
RHOST   =     os.getenv("REDIS_SERVICE_HOST", "redis.tgr.svc.cluster.local")
RPORT   = int(os.getenv("REDIS_SERVICE_PORT", "6379"))

keyNs   = "controller.rtdata."


@cherrypy.expose
class Sensors_v1(object):

    def __init__(self):
        self.properties = SensorProperties_v1()

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

                sensors = ds.hgetall(keyNs + "sensor." + controllerid)
                sensors.pop("timeStamp")

                result = {'data':{'internal':{
                                  'temperature':sensors['intTemp'] + sensors['tScale'],
                                  'humidity':sensors['intRH'] + "%"},
                                  'external':{
                                  'temperature':sensors['extTemp'] + sensors['tScale'],
                                  'humidity':sensors['extRH'] + "%",
                                  'co2':sensors['Co2'] + "ppm",
                                  'illuminance':sensors['Lux'] + "lux",}}}

                return result
            else:
                print("ERROR: Unable to fetch sensor data for controllerid: {}".format(controllerid))
                raise cherrypy.HTTPError(502)
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return


@cherrypy.expose
@cherrypy.popargs('device')
class SensorProperties_v1(object):

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

                request = {'method':'GET','url':'sensors/properties'}

                response = req.request_handler(controllerid, request)

                if response["status_code"] == 200:
                    return response["body"]
                else:
                    raise cherrypy.HTTPError(502)
            else:
                raise cherrypy.HTTPError(503, "Controller unregistered or offline.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return


