#!/usr/bin/env python3

import os
import datetime as dt
import cherrypy
import redis
import json
import random
import string

# Version & build
VERSION = "v1.1"
BUILD   = os.getenv("TGR_API_BUILD", "X.xxx")

# Redis
RHOST   =     os.getenv("REDIS_SERVICE_HOST", "redis.tgr.svc.cluster.local")
RPORT   = int(os.getenv("REDIS_SERVICE_PORT", "6379"))

keyNs   = "controller.rtdata."


@cherrypy.expose
class V1(object):

    def __init__(self):
        self.controller = Controller_v1()
        self.rtdata = RTData_v1()
        self.version = Version_v1()


@cherrypy.expose
class Version_v1(object):

    @cherrypy.tools.json_out()
    def GET(self):
        return {'version':VERSION,'build':BUILD}


@cherrypy.expose
class Controller_v1(object):

    def PUT(self, controllerId):

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        ds.sadd(keyNs + "ids", controllerId)

        cherrypy.response.status = 202
        return

    def DELETE(self, controllerId):

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = keyNs + "ids"
        if ds.exists(key) and ds.sismember(key, controllerId):
            ds.srem(key, controllerId)
        else:
            raise cherrypy.HTTPError(404)
            return

        cherrypy.response.status = 202
        return

@cherrypy.expose
class RTData_v1(object):

    def POST(self, controllerId, rtdata):

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = keyNs + "ids"
        if ds.exists(key) and ds.sismember(key, controllerId):
            key = keyNs + "status." + controllerId
            ds.set(key, "online", ex=30)

            rtd = json.loads("{}".format(rtdata.replace("'", '"')))

            rtd["sensorVals"]["timeStamp"] = rtd["timeStamp"]
            rtd["relayStates"]["timeStamp"] = rtd["timeStamp"]
            rtd["relayModes"]["timeStamp"] = rtd["timeStamp"]

            key = keyNs + "sensor." + controllerId
            ds.hset(key, mapping=rtd["sensorVals"])

            key = keyNs + "relay.states." + controllerId
            ds.hset(key, mapping=rtd["relayStates"])

            key = keyNs + "relay.modes." + controllerId
            ds.hset(key, mapping=rtd["relayModes"])
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")


