#!/usr/bin/env python3

import os
import datetime as dt
import cherrypy
import redis
import json
import psycopg


# Version & build
VERSION = "1.00"
BUILD   = os.getenv("TGR_API_BUILD", "X.xxx")

# Redis
RHOST    =     os.getenv("REDIS_SERVICE_HOST", "redis.tgr.svc.cluster.local")
RPORT    = int(os.getenv("REDIS_SERVICE_PORT", "6379"))

# Postgres
PGHOST   =     os.getenv("POSTGRES_SERVICE_HOST", "postgres.tgr.svc.cluster.local")
PGPORT   =     os.getenv("POSTGRES_SERVICE_PORT", "5432")
PGDBNAME =     os.getenv("POSTGRES_DBNAME", "tgr_master")
PGUSER   =     os.getenv("POSTGRES_USER", "pgadmin")
PGPWD    =     os.getenv("POSTGRES_PASSWORD", "thegreenroom")

pgConnectStr = "host=" + PGHOST + " port=" + PGPORT + " dbname=" + PGDBNAME + " user=" + PGUSER + " password=" + PGPWD

@cherrypy.expose
class V1(object):

    def __init__(self):
        self.controller = Controller_v1()
        self.version = Version_v1()


@cherrypy.expose
class Version_v1(object):

    @cherrypy.tools.json_out()
    def GET(self):
        return {'version':VERSION,'build':BUILD}


@cherrypy.expose
@cherrypy.popargs('controllerid')
class Controller_v1(object):

    def __init__(self):
        self.grows = Grows_v1()

    @cherrypy.tools.json_in()
    def PUT(self, controllerid):

        try:
            keyStore = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = "controller.account.id." + controllerid
        if keyStore.exists(key):
            accountId = keyStore.get(key)
        else:
            raise cherrypy.HTTPError(404)
            return

        key = "account.schema." + accountId
        if keyStore.exists(key):
            schema = keyStore.get(key)
        else:
            print("ERROR: Unable to locate account schema for: {}".format(accountId))
            raise cherrypy.HTTPError(502)
            return

        inputs = list()
        SQL = ""

        try:
            name = cherrypy.request.json["name"]
        except:
            pass
        else:
            inputs.append(name)
            SQL += "name = %s"

        try:
            growspace = cherrypy.request.json["growspace"]
        except:
            pass
        else:
            inputs.append(growspace)
            if len(SQL) > 0:
                sep = ", "
            else:
                sep = ""
            SQL += sep + "growspace = %s"

        try:
            usage = cherrypy.request.json["usage"]
        except:
            pass
        else:
            inputs.append(usage)
            if len(SQL) > 0:
                sep = ", "
            else:
                sep = ""
            SQL += sep + "usage = %s"

        inputs.append(controllerid)

        try:
            conn = psycopg.connect(pgConnectStr)
        except:
            print("ERROR: Unable to connect to Postgres service at: {}".format(pgConnectStr))
            raise cherrypy.HTTPError(502)
            return

        try:
            cur = conn.cursor()

            cur.execute("UPDATE " + schema + ".controllers SET " + SQL +
                        " WHERE cloudsvcid = %s",
                        (inputs))
        except:
            cur.close()
            conn.close()
            print("ERROR: Unable to execute SQL query with Postgres service.")
            raise cherrypy.HTTPError(502)
            return
        else:
            conn.commit()
        finally:
            cur.close()
            conn.close()

        cherrypy.response.status = 202
        return


@cherrypy.expose
@cherrypy.popargs('growid')
class Grows_v1(object):

    @cherrypy.tools.json_in()
    def PUT(self, controllerid, growid):

        try:
            keyStore = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = "controller.account.id." + controllerid
        if keyStore.exists(key):
            accountId = keyStore.get(key)
        else:
            raise cherrypy.HTTPError(404)
            return

        key = "account.schema." + accountId
        if keyStore.exists(key):
            schema = keyStore.get(key)
        else:
            print("ERROR: Unable to locate account schema for: {}".format(accountId))
            raise cherrypy.HTTPError(502)
            return

        inputs = list()
        SQL = ""

        try:
            started = cherrypy.request.json["started"]
        except:
            pass
        else:
            inputs.append(started)
            SQL += "started = %s"

        try:
            flipped = cherrypy.request.json["flipped"]
        except:
            pass
        else:
            inputs.append(flipped)
            if len(SQL) > 0:
                sep = ", "
            else:
                sep = ""
            SQL += sep + "flipped = %s"

        try:
            harvested = cherrypy.request.json["harvested"]
        except:
            pass
        else:
            inputs.append(harvested)
            if len(SQL) > 0:
                sep = ", "
            else:
                sep = ""
            SQL += sep + "harvested = %s"

        try:
            phase = cherrypy.request.json["phase"]
        except:
            pass
        else:
            inputs.append(phase)
            if len(SQL) > 0:
                sep = ", "
            else:
                sep = ""
            SQL += sep + "phase = %s"

        try:
            active = cherrypy.request.json["active"]
        except:
            pass
        else:
            inputs.append(active)
            if len(SQL) > 0:
                sep = ", "
            else:
                sep = ""
            SQL += sep + "active = %s"

        inputs.append(growid)
        inputs.append(controllerid)

        try:
            conn = psycopg.connect(pgConnectStr)
        except:
            print("ERROR: Unable to connect to Postgres service at: {}".format(pgConnectStr))
            raise cherrypy.HTTPError(502)
            return

        try:
            cur = conn.cursor()

            cur.execute("UPDATE " + schema + ".grows SET " + SQL +
                        " WHERE growid = %s AND controllerid = %s",
                        (inputs))
        except:
            cur.close()
            conn.close()
            print("ERROR: Unable to execute SQL query with Postgres service.")
            raise cherrypy.HTTPError(502)
            return
        else:
            conn.commit()
        finally:
            cur.close()
            conn.close()

        cherrypy.response.status = 202
        return


