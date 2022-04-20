#!/usr/bin/env python3

import os
import datetime as dt
import cherrypy
import redis
import json
import random
import string

# Version & build
VERSION = "1.1"
BUILD   = os.getenv("TGR_API_BUILD", "X.xxx")

# Redis
RHOST   =     os.getenv("REDIS_SERVICE_HOST", "redis.tgr.svc.cluster.local")
RPORT   = int(os.getenv("REDIS_SERVICE_PORT", "6379"))

keyNs   = "controller.requests."


@cherrypy.expose
class V1(object):

    def __init__(self):
        self.controller = Controller_v1()
        self.requests = Requests_v1()
        self.version = Version_v1()


@cherrypy.expose
class Version_v1(object):

    @cherrypy.tools.json_out()
    def GET(self):
        return {'version':VERSION,'build':BUILD}


@cherrypy.expose
class Controller_v1(object):

    @cherrypy.tools.json_out()
    def GET(self, controllerId):

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = keyNs + "ids"
        if not ds.exists(key) or not ds.sismember(key, controllerId):
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return
        else:
            key = keyNs + "status." + controllerId
            if ds.exists(key):
                return {'status':ds.get(key)}
            else:
                return {'status':'offline'}

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
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return

        cherrypy.response.status = 202
        return


@cherrypy.expose
class Requests_v1(object):

    @cherrypy.tools.json_out()
    def GET(self, jobId):

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = keyNs + "job." + jobId
        if ds.exists(key):

            job = ds.hgetall(key)

            if job["job"] == "completed":
                ds.delete(key)
                ds.srem(keyNs + "jobs", jobId)
            return job
        else:
            raise cherrypy.HTTPError(404, "Request job details not found.")

    @cherrypy.tools.json_out()
    def PUT(self, controllerId, request):

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = keyNs + "ids"
        if not ds.exists(key) or not ds.sismember(key, controllerId):
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return
        else:
            jobId = ''.join(random.sample(string.hexdigits, 16))
            key = keyNs + "job." + jobId
            ds.hmset(key, {'job':'pending','jobid':jobId,'request':request})
            ds.expire(key, 15)

            key = keyNs + "queue." + controllerId
            ds.zadd(key,{jobId:dt.datetime.timestamp(dt.datetime.now())})

            return {'jobid':jobId}


