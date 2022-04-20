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

    def PUT(self, controllerId):

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPTError(502)
            return

        ds.sadd(keyNs + "ids", controllerId)

        cherrypy.response.status = 202
        return

    def DELETE(self, controllerId):
        ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)

        key = keyNs + "ids"
        if ds.exists(key) and ds.sismember(key, controllerId):
            ds.srem(key, controllerId)
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")

        cherrypy.response.status = 202
        return

@cherrypy.expose
class Requests_v1(object):

    @cherrypy.tools.json_out()
    def GET(self, controllerId):

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPTError(502)
            return

        key = keyNs + "ids"
        if ds.exists(key) and ds.sismember(key, controllerId):
            key = keyNs + "status." + controllerId
            ds.set(key, "online", ex=30)

            reqKey = keyNs + "queue." + controllerId
            jobKey = ds.zpopmin(reqKey)

            if len(jobKey) > 0:
                jobId,score = jobKey[0]

                job = ds.hgetall(keyNs + "job." + jobId)

                ds.sadd(keyNs + "jobs", jobId)

                key = keyNs + "job." + jobId
                ds.hset(key, 'job', 'running')

                return job
            else:
                raise cherrypy.HTTPError(404, "Request job details not found.")
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")

    def POST(self, jobId, response):

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPTError(502)
            return

        key = keyNs + "jobs"
        if ds.exists(key) and ds.sismember(key, jobId):
            key = keyNs + "job." + jobId
            ds.hmset(key, dict(job='completed',response=response))
            ds.expire(key, 30)
        else:
            raise cherrypy.HTTPError(404, "Job id not found in queue.")


