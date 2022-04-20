#!/usr/bin/env python3

import os
import cherrypy
import redis
import psycopg
import req
from auth import *


# Redis
RHOST    =     os.getenv("REDIS_SERVICE_HOST", "redis.tgr.svc.cluster.local")
RPORT    = int(os.getenv("REDIS_SERVICE_PORT", "6379"))

# QuestDB
PGHOST   =     os.getenv("QUESTDB_QUERY_SERVICE_HOST", "questdb-query.tgr.svc.cluster.local")
PGPORT   =     os.getenv("QUESTDB_SERVICE_PORT_QUERY", "8812")
PGDBNAME =     os.getenv("QUESTDB_DBNAME", "qdb")
PGUSER   =     os.getenv("QUESTDB_USER", "admin")
PGPWD    =     os.getenv("QUESTDB_PASSWORD", "quest")

qdConnectStr = "host=" + PGHOST + " port=" + PGPORT + " dbname=" + PGDBNAME + " user=" + PGUSER + " password=" + PGPWD

keyNs   = "controller.rtdata."


@cherrypy.expose
class System_v1(object):

    def __init__(self):
        self.events = SystemEvents_v1()
        self.services = SystemServices_v1()
        self.status = SystemStatus_v1()

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

        request = {'method':'GET','url':'system'}

        response = req.request_handler(controllerid, request)

        if response["status_code"] == 200:
            return response["body"]
        else:
            raise cherrypy.HTTPError(502)
            return


@cherrypy.expose
class SystemEvents_v1(object):

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

        key = "account.schema." + accountid
        if keyStore.exists(key):
            schema = keyStore.get(key)
        else:
            print("ERROR: Unable to locate account schema for {}".format(accountid))
            raise cherrypy.HTTPError(502)
            return

        try:
            qdConn = psycopg.connect(qdConnectStr)
        except:
            print("ERROR: Unable to connect to QuestDB service at: {}".format(qdConnectStr))
            raise cherrypy.HTTPError(502)
            return

        try:
            qdCur = qdConn.cursor()

            qdCur.execute("SELECT * FROM " + schema + "_events_{}".format(controllerid.replace('-','_')))

        except:
            print("ERROR: Unable to execute query with QuestDB service.")
            qdCur.close()
            qdConn.close()
            raise cherrypy.HTTPError(502)
            return
        else:
            result = qdCur.fetchall()
            data = list()
            for row in result:
                data.append({'ts':"{}".format(row[0]),'evtype':row[1],'evsource':row[2],'event':row[3]})

            qdCur.close()
            qdConn.close()

        return {'data':data}



@cherrypy.expose
class SystemServices_v1(object):

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

        request = {'method':'GET','url':'system/services'}

        response = req.request_handler(controllerid, request)

        if response["status_code"] == 200:
            return response["body"]
            return
        else:
            raise cherrypy.HTTPError(502)
            return


@cherrypy.expose
class SystemStatus_v1(object):

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

        request = {'method':'GET','url':'system/status'}

        response = req.request_handler(controllerid, request)

        if response["status_code"] == 200:
            return response["body"]
        else:
            raise cherrypy.HTTPError(502)
            return


