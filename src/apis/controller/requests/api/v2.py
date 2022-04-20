#!/usr/bin/env python3

import os
import datetime as dt
import cherrypy
import redis
import json
import random
import string

# Version & build
VERSION = "2.0"
BUILD   = os.getenv("TGR_API_BUILD", "X.xxx")

# Redis
RHOST   =     os.getenv("REDIS_SERVICE_HOST", "redis.tgr.svc.cluster.local")
RPORT   = int(os.getenv("REDIS_SERVICE_PORT", "6379"))

keyNs   = "controller.requests."


@cherrypy.expose
class V2(object):

    def __init__(self):
        self.controller = Controller_v2()
        self.requests = Requests_v2()
        self.version = Version_v2()


@cherrypy.expose
class Version_v2(object):

    @cherrypy.tools.json_out()
    def GET(self):
        return {'version':VERSION,'build':BUILD}


@cherrypy.expose
class Controller_v2(object):

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

            cherrypy.response.status = 202
            return
        else:
            raise cherrypy.HTTPError(404)
            return


@cherrypy.expose
@cherrypy.popargs('controllerId')
class Requests_v2(object):

    @cherrypy.tools.json_out()
    def GET(self, controllerId):

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

            reqKey = keyNs + "queue." + controllerId
            jobKey = ds.zpopmin(reqKey)

            if len(jobKey) > 0:
                jobId,score = jobKey[0]

                job = ds.hgetall(keyNs + "job." + jobId)
                req = json.loads(ds.get(keyNs + "job.request." + jobId))

                job["request"] = req

                ds.sadd(keyNs + "jobs", jobId)

                key = keyNs + "job." + jobId
                ds.hset(key, 'job', 'running')

                return job
            else:
                raise cherrypy.HTTPError(404, "Request job details not found.")
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")

    @cherrypy.tools.json_in()
    def PUT(self, controllerId):

        try:
            jobId = cherrypy.request.json["jobid"]
        except:
            raise cherrypy.HTTPError(400, "Must provide jobid.")

        try:
            response = cherrypy.request.json["response"]
        except:
            raise cherrypy.HTTPError(400, "Must provide response.")

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = keyNs + "jobs"
        if ds.exists(key) and ds.sismember(key, jobId):
            key = keyNs + "job." + jobId
            ds.hset(key, mapping=dict(job='completed'))
            ds.expire(key, 30)

            key = keyNs + "job.response." + jobId
            ds.set(key, json.dumps(response))
            ds.expire(key, 30)

            cherrypy.response.status = 202
            return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return


