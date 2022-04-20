#!/usr/bin/env python3

import os
import datetime as dt
import cherrypy
import redis
import json
import random
import string
import psycopg
from auth import *

# Version & build
VERSION = "2.0"
BUILD   = os.getenv("TGR_API_BUILD", "X.xxx")

# Redis
RHOST   =     os.getenv("REDIS_SERVICE_HOST", "redis.tgr.svc.cluster.local")
RPORT   = int(os.getenv("REDIS_SERVICE_PORT", "6379"))

# Postgres
PGHOST   =     os.getenv("POSTGRES_SERVICE_HOST", "postgres.tgr.svc.cluster.local")
PGPORT   =     os.getenv("POSTGRES_SERVICE_PORT", "5432")
PGDBNAME =     os.getenv("POSTGRES_DBNAME", "tgr_master")
PGUSER   =     os.getenv("POSTGRES_USER", "pgadmin")
PGPWD    =     os.getenv("POSTGRES_PASSWORD", "thegreenroom")

pgConnectStr = "host=" + PGHOST + " port=" + PGPORT + " dbname=" + PGDBNAME + " user=" + PGUSER + " password=" + PGPWD

keyNs   = "controller.requests."


@cherrypy.expose
class V2(object):

    def __init__(self):
        self.controller = Controller_v2()
        self.login = APILogin_v2()
        self.requests = Requests_v2()
        self.version = Version_v2()


@cherrypy.expose
class Version_v2(object):

    @cherrypy.tools.json_out()
    def GET(self):
        return {'version':VERSION,'build':BUILD}


@cherrypy.expose
class Controller_v2(object):

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


@cherrypy.expose
@cherrypy.popargs('controllerId')
class Requests_v2(object):

    @cherrypy.tools.json_out()
    def GET(self, controllerId, jobId):

        scope = AuthSession()

        if scope == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

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
                key2 = keyNs + "job.response." + jobId
                response = json.loads(ds.get(key2))

                job["response"] = response

                ds.delete(key)
                ds.delete(key2)
                ds.srem(keyNs + "jobs", jobId)

            return job
        else:
            raise cherrypy.HTTPError(404, "Request job details not found.")

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self, controllerId):

        scope = AuthSession()

        if scope == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

        try:
            request = cherrypy.request.json["request"]
        except:
            raise cherrypy.HTTPError(400)

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = keyNs + "ids"
        if not ds.exists(key) or not ds.sismember(key, controllerId):
            raise cherrypy.HTTPError(404, "Controller id not found.")
        else:
            jobId = ''.join(random.sample(string.hexdigits, 16))

            key = keyNs + "job." + jobId
            ds.hset(key, mapping={'job':'pending','jobid':jobId})
            ds.expire(key, 15)

            key = keyNs + "job.request." + jobId
            ds.set(key, json.dumps(request))
            ds.expire(key, 15)

            key = keyNs + "queue." + controllerId
            ds.zadd(key,{jobId:dt.datetime.timestamp(dt.datetime.now())})

            return {'jobid':jobId}


@cherrypy.expose
class APILogin_v2(object):

    @cherrypy.tools.json_in()
    def PUT(self):

        try:
            apikey = cherrypy.request.json["apikey"]
        except:
            raise cherrypy.HTTPError(400, "Missing 'apikey' parameter.")
            return

        try:
            token = cherrypy.request.json["token"]
        except:
            raise cherrypy.HTTPError(400, "Missing 'token' parameter.")
            return

        try:
            conn = psycopg.connect(pgConnectStr)
        except:
            print("ERROR: Unable to connect to Postgres service at: {}".format(pgConnectStr))
            raise cherrypy.HTTPError(502)
            return

        cur = conn.cursor()

        cur.execute("SELECT scope FROM public.apitokens " +
                    "WHERE id = %s AND " +
                    "token = crypt(%s, token)",
                    (apikey, token))

        result = cur.fetchall()

        scope = result[0][0]

        cur.close()
        conn.close()

        try:
            keyStore = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        if not "apikey" in cherrypy.session:
            cherrypy.session["apikey"] = "{}".format(apikey)
            cherrypy.session["scope"] = scope

        key = "api.session.id.{}".format(apikey)
        keyStore.set(key, cherrypy.session.id)
        keyStore.pexpire(key, 3000)

        return


