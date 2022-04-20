#!/usr/bin/env python3

import os
import datetime as dt
import cherrypy
import redis
import json
import random
import string
import psycopg

#Version & build
VERSION = "v2.0"
BUILD   = os.getenv("TGR_API_BUILD", "X.xxx")

# Redis
RHOST   =     os.getenv("REDIS_SERVICE_HOST", "redis.tgr.svc.cluster.local")
RPORT   = int(os.getenv("REDIS_SERVICE_PORT", "6379"))

keyNs   = "controller.rtdata."

# QuestDB
PGHOST   =     os.getenv("QUESTDB_QUERY_SERVICE_HOST", "questdb-query.tgr.svc.cluster.local")
PGPORT   =     os.getenv("QUESTDB_SERVICE_PORT_QUERY", "8812")
PGDBNAME =     os.getenv("QUESTDB_DBNAME", "qdb")
PGUSER   =     os.getenv("QUESTDB_USER", "admin")
PGPWD    =     os.getenv("QUESTDB_PASSWORD", "quest")

qdConnectStr = "host=" + PGHOST + " port=" + PGPORT + " dbname=" + PGDBNAME + " user=" + PGUSER + " password=" + PGPWD


@cherrypy.expose
class V2(object):

    def __init__(self):
        self.controller = Controller_v2()
        self.rtdata = RTData_v2()
        self.events = EventData_v2()
        self.version = Version_v2()


@cherrypy.expose
class Version_v2(object):

    @cherrypy.tools.json_out()
    def GET(self):
        return {'version':VERSION,'build':BUILD}


@cherrypy.expose
@cherrypy.popargs('controllerid')
class Controller_v2(object):

    def PUT(self, controllerid):

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        ds.sadd(keyNs + "ids", controllerid)

        key = keyNs + "status." + controllerid
        ds.set(key, "online", ex=30)

        cherrypy.response.status = 202
        return

    def DELETE(self, controllerid):

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = keyNs + "ids"
        if ds.exists(key) and ds.sismember(key, controllerid):
            ds.srem(key, controllerid)
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")

        key = keyNs + "status." + controllerid
        ds.delete(key)

        cherrypy.response.status = 202
        return


@cherrypy.expose
@cherrypy.popargs('controllerid')
class RTData_v2(object):

    @cherrypy.tools.json_in()
    def POST(self, controllerid):

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = keyNs + "ids"
        if ds.exists(key) and ds.sismember(key, controllerid):
            key = keyNs + "status." + controllerid
            ds.set(key, "online", ex=30)
        else:
            raise cherrypy.HTTPError(404, "Controllerid not found.")
            return

        try:
            rtd = cherrypy.request.json["data"]
        except:
            raise cherrypy.HTTPError(400, "Missing json payload.")
            return

        try:
            rtd["sensorVals"]["timeStamp"] = rtd["timeStamp"]
            rtd["alarmData"]["timeStamp"] = rtd["timeStamp"]
        except:
            raise cherrypy.HTTPError(400, "Missing key in payload.")
            return

        relayNames = {"timeStamp":rtd["timeStamp"]}
        relayStates = {"timeStamp":rtd["timeStamp"]}
        relayModes = {"timeStamp":rtd["timeStamp"]}

        for relay in rtd["relayData"]:
            relayNames[relay["id"]] = relay["name"]
            relayStates[relay["id"]] = relay["state"]
            relayModes[relay["id"]] = relay["mode"]

        key = keyNs + "sensor." + controllerid
        ds.hset(key, mapping=rtd["sensorVals"])

        key = keyNs + "alarm." + controllerid
        ds.hset(key, mapping=rtd["alarmData"])

        key = keyNs + "relay.names." + controllerid
        ds.hset(key, mapping=relayNames)

        key = keyNs + "relay.states." + controllerid
        ds.hset(key, mapping=relayStates)

        key = keyNs + "relay.modes." + controllerid
        ds.hset(key, mapping=relayModes)

        d,t = rtd["timeStamp"].split("T")
        if t == "00:00:00":
            ds.set("data.questdb.events.truncate", rtd["timeStamp"])

        cherrypy.response.status = 202
        return


@cherrypy.expose
@cherrypy.popargs('controllerid')
class EventData_v2(object):

    @cherrypy.tools.json_in()
    def POST(self, controllerid):

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = keyNs + "ids"
        if ds.exists(key) and ds.sismember(key, controllerid):
            key = keyNs + "status." + controllerid
            ds.set(key, "online", ex=30)
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return

        key = "controller.account.id." + controllerid
        if ds.exists(key):
            accountId = ds.get(key)
        else:
            print("ERROR: Unable to locate account id for controller id: {}".format(controllerid))
            raise cherrypy.HTTPError(502)
            return

        key = "account.schema." + accountId
        if ds.exists(key):
            schema = ds.get(key)
        else:
            print("ERROR: Unable to locate account schema for: {}".format(accountId))
            raise cherrypy.HTTPError(502, "Missing datastore key.")
            return

        try:
            evData = cherrypy.request.json["data"]
        except:
            raise cherrypy.HTTPError(400, "Missing json payload.")
            return

        try:
            timeStamp = evData["timeStamp"]
        except:
            raise cherrypy.HTTPError(400, "Missing timestamp in payload.")
            return

        try:
            eventData = evData["eventData"]
        except:
            raise cherrypy.HTTPError(400, "Missing event data in payload.")
            return

        try:
            evType,evSource,event = eventData.split("::")
        except:
            raise cherrypy.HTTPError(400, "Malformed event data in payload.")
            return

        try:
            conn = psycopg.connect(qdConnectStr)
        except:
            print("ERROR: Unable to connect to QuestDB service at: {}".format(qdConnectStr))
            raise cherrypy.HTTPError(502)
            return

        try:
            cur = conn.cursor()

            cur.execute("INSERT INTO " + schema + "_events_{}".format(controllerid.replace('-','_'))  + 
                        " (ts, evtype, evsource, event) VALUES (%s, %s, %s, %s)",
                        (timeStamp, evType, evSource, event))
        except:
            print("ERROR: Unable to execute query with QuestDB service.")
            raise cherrypy.HTTPError(502)
            return

        else:
            conn.commit()
        finally:
            cur.close()
            conn.close()

        cherrypy.response.status = 202
        return


