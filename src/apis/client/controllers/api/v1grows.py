#!/usr/bin/env python3

import os
from datetime import datetime
import cherrypy
import redis
import psycopg
import req
from auth import *


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

# QuestDB
PGHOST   =     os.getenv("QUESTDB_QUERY_SERVICE_HOST", "questdb-query.tgr.svc.cluster.local")
PGPORT   =     os.getenv("QUESTDB_SERVICE_PORT_QUERY", "8812")
PGDBNAME =     os.getenv("QUESTDB_DBNAME", "qdb")
PGUSER   =     os.getenv("QUESTDB_USER", "admin")
PGPWD    =     os.getenv("QUESTDB_PASSWORD", "quest")

qdConnectStr = "host=" + PGHOST + " port=" + PGPORT + " dbname=" + PGDBNAME + " user=" + PGUSER + " password=" + PGPWD


@cherrypy.expose
class Grows_v1(object):

    def __init__(self):
        self.id = Grow_v1()

    @cherrypy.tools.json_out()
    def GET(self, controllerid, active="none", properties="none"):

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

        if properties == "none":
            columns = "growid,name"
        elif properties == "all":
            columns = "growid,name,strain,medium,lighting,phase,growspace,started,veglen,flowerlen,active"
        else:
            raise cherrypy.HTTPError(400, "Invalid value for 'properties' parameter.")
            return

        if active == "none":
            where = ""
            variables = [controllerid]
        elif active == "yes" or active == "no":
            where = " AND active = %s"
            variables = [controllerid,active]
        else:
            raise cherrypy.HTTPError(400, "Invalid value for 'active' parameter.")
            return

        try:
            conn = psycopg.connect(pgConnectStr)
        except:
            print("ERROR: Unable to connect to Postgres service at {}".format(pgConnectStr))
            raise cherrypy.HTTPError(502)
            return
        else:

            cur = conn.cursor()

            cur.execute("SELECT array_to_json(array_agg(row_to_json(t))) FROM (SELECT " +
                           columns + " FROM " + schema + ".grows " +
                           "WHERE controllerid = %s" + where +
                           ") t", (variables))

            result = cur.fetchall()
            try:
                grows = result[0][0]
            except:
                raise cherrypy.HTTPError(404, "No grows found.")
                return
            finally:
                cur.close()
                conn.close()
                return grows

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self, controllerid):

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

        key = "controller.grow.id." + controllerid
        if keyStore.exists(key):
            raise cherrypy.HTTPError(409, "Only one active grow at a time allowed.")
            return 

        jsonData = {}
        inputs = list()
        SQLcols = "active"
        SQLvals = "true"

        inputs.append(controllerid)
        SQLcols += ", controllerid"
        SQLvals += ", %s"

        try:
            name = cherrypy.request.json["name"]
        except:
            raise cherrypy.HTTPError(400, "Must provide a name.")
            return
        else:
            jsonData["name"] = name
            inputs.append(name)
            SQLcols += ", name"
            SQLvals += ", %s"

        try:
            strain = cherrypy.request.json["strain"]
        except:
            pass
        else:
            jsonData["strain"] = strain
            inputs.append(strain)
            SQLcols += ", strain"
            SQLvals += ", %s"

        try:
            medium = cherrypy.request.json["medium"]
        except:
            pass
        else:
            jsonData["medium"] = medium
            inputs.append(medium)
            SQLcols += ", medium"
            SQLvals += ", %s"

        try:
            lighting = cherrypy.request.json["lighting"]
        except:
            pass
        else:
            jsonData["lighting"] = lighting
            inputs.append(lighting)
            SQLcols += ", lighting"
            SQLvals += ", %s"

        try:
            growspace = cherrypy.request.json["growspace"]
        except:
            pass
        else:
            jsonData["growspace"] = growspace
            inputs.append(growspace)
            SQLcols += ", growspace"
            SQLvals += ", %s"

        try:
            phase = cherrypy.request.json["phase"]
        except:
            pass
        else:
            if not phase in ["veg", "flower"]:
                raise cherrypy.HTTPError(400, "Must supply a valid phase.")
                return

            jsonData["phase"] = phase
            inputs.append(phase)
            SQLcols += ", phase"
            SQLvals += ", %s"

        try:
            startdate = cherrypy.request.json["startdate"]

            try:
                dt = datetime.fromisoformat(startdate)
            except:
                raise cherrypy.HTTPError(400, "Must supply a valid start date.")
                return
        except:
            pass
        else:
            jsonData["startdate"] = startdate
            inputs.append(startdate)
            SQLcols += ", started"
            SQLvals += ", %s"

        try:
            veglen = cherrypy.request.json["veglen"]
        except:
            pass
        else:
            if not int(veglen) > 0 and not int(veglen) < 180:
                raise cherrypy.HTTPError(400, "Must supply veglen value between 1 and 180.")
                return

            jsonData["veglen"] = veglen
            inputs.append(veglen)
            SQLcols += ", veglen"
            SQLvals += ", %s"

        try:
            flowerlen = cherrypy.request.json["flowerlen"]
        except:
            pass
        else:
            if not int(flowerlen) > 0 and not int(flowerlen) < 100:
                raise cherrypy.HTTPError(400, "Must supply flowerlen value between 1 and 100.")
                return

            jsonData["flowerlen"] = flowerlen
            inputs.append(flowerlen)
            SQLcols += ", flowerlen"
            SQLvals += ", %s"

        try:
            pgConn = psycopg.connect(pgConnectStr)
        except:
            print("ERROR: Error connecting to Postgres service at: {}".format(pgConnectStr))
            raise cherrypy.HTTPError(502)
            return
        else:
            pgCur = pgConn.cursor()

            pgCur.execute("INSERT INTO " + schema + ".grows (" +
                          SQLcols + ") VALUES (" +
                          SQLvals + ") RETURNING (growid)",
                          (inputs))

            result = pgCur.fetchall()
            pgConn.commit()

            growid = result[0][0]
            jsonData["growid"] = growid
        finally:
            pgCur.close()
            pgConn.close()

        try:
            qdConn = psycopg.connect(qdConnectStr)
        except:
            print("ERROR: Unable to connect to QuestDB service at: {}".format(qdConnectStr))
            raise cherrypy.HTTPError(502)
            return
        else:
            qdCur = qdConn.cursor()

            qdCur.execute("CREATE TABLE " + schema + "_grow_{}_sensors".format(growid) +
                          """(ts TIMESTAMP, tscale symbol, intemp SHORT, inrh SHORT, 
                              extemp SHORT, exrh SHORT, exco2 LONG, exlux LONG)
                             timestamp(ts)
                             PARTITION BY MONTH;""")

            qdCur.execute("CREATE TABLE " + schema + "_grow_{}_relays".format(growid) +
                          """(ts TIMESTAMP, relayid symbol index, name symbol index, state symbol, mode symbol)
                             timestamp(ts)
                             PARTITION BY MONTH;""")

        result = {}
        request = {'method':'POST','url':'grow/','json':jsonData}

        response = req.request_handler(controllerid, request)

        if response["status_code"] == 202:

            qdConn.commit()

            key = "controller.grow.id." + controllerid
            keyStore.set(key, growid)
            keyStore.persist(key)

            qdCur.close()
            qdConn.close()

            result = {'growid':growid}
            return result
        else:
            if "status_msg" in response:
                print("ERROR: {} {}".format(response["status_code"],response["status_msg"]))
            else:
                print("ERROR: {}".format(response["status_code"]))
            raise cherrypy.HTTPError(502)
            return


@cherrypy.expose
@cherrypy.popargs('growid')
class Grow_v1(object):

    @cherrypy.tools.json_out()
    def GET(self, controllerid, growid):

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

        key = "controller.grow.id." + controllerid
        if (keyStore.exists(key) and 
            keyStore.get(key) == growid
            ):
        
            request = {'method':'GET','url':'grow/id/' + growid}

            response = req.request_handler(controllerid, request)

            if response["status_code"] == 200:
                return response["body"]
            else:
                if "status_msg" in response:
                    print("ERROR: {} {}".format(response["status_code"],response["status_msg"]))
                else:
                    print("ERROR: {}".format(response["status_code"]))
                raise cherrypy.HTTPError(502)
                return
        else:
            try:
                conn = psycopg.connect(pgConnectStr)
            except:
                print("ERROR: Unable to connect to Postgres service at: {}".format(pgConnectStr))
                raise cherrypy.HTTPError(502)
                return
            else:

                cur = conn.cursor()

                cur.execute("""SELECT array_to_json(array_agg(row_to_json(t))) FROM (SELECT 
                               name,strain,medium,lighting,phase,growspace,started,
                               veglen,flowerlen,active FROM """ +
                               schema + ".grows WHERE growid = %s) t""", ([growid]))

                result = cur.fetchall()
                try:
                    grow = result[0][0][0]
                except:
                    raise cherrypy.HTTPError(404, "Growid not found.")
                    return
                finally:
                    cur.close()
                    conn.close()
                    return grow

    def DELETE(self, controllerid, growid):

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
            pgConn = psycopg.connect(pgConnectStr)
        except:
            print("ERROR: Unable to connect to Postgres service at: {}".format(pgConnectStr))
            raise cherrypy.HTTPError(502)
            return
        else:
            pgCur = pgConn.cursor()

            try:
                pgCur.execute("""SELECT array_to_json(array_agg(row_to_json(t))) FROM (SELECT 
                              active FROM """ + schema + ".grows WHERE growid = %s) t""",
                              ([growid]))

                result = pgCur.fetchall()
                try:
                    grow = result[0][0][0]
                except:
                    pgCur.close()
                    pgConn.close()
                    raise cherrypy.HTTPError(404, "Growid not found.")
                    return

            except:
                pgCur.close()
                pgConn.close()
                print("ERROR: Unable to fetch growid from Postgres service.")
                raise cherrypy.HTTPError(502)
                return

            try:
                pgCur.execute("DELETE FROM " + schema + ".grows WHERE growid = %s", ([growid]))
            except:
                pgCur.close()
                pgConn.close()
                print("ERROR: Unable to delete growid from Postgres service.")
                raise cherrypy.HTTPError(502)
                return
            else:
                if grow["active"] == False:
                    pgConn.commit()
                else:
                    try:
                        qdConn = psycopg.connect(qdConnectStr)
                    except:
                        pgCur.close()
                        pgConn.close()
                        print("Unable to connect to QuestDB service at: {}".format(qdConnectStr))
                        raise cherrypy.HTTPError(502)
                        return
                    else:
                        qdCur = qdConn.cursor()

                        try:
                            qdCur.execute("DROP TABLE " + schema + "_grow_" + growid + "_sensors")
                            qdCur.execute("DROP TABLE " + schema + "_grow_" + growid + "_relays")
                        except:
                            pgCur.close()
                            pgConn.close()
                            qdCur.close()
                            qdConn.close()
                            print("ERROR: Unable to execute SQL query with QuestDB service.")
                            raise cherrypy.HTTPError(502)
                            return
                        else:
                            request = {'method':'DELETE','url':'grow/id/' + growid}

                            response = req.request_handler(controllerid, request)
                            print(response)

                            if response["status_code"] == 202:

                                pgConn.commit()
                                qdConn.commit()

                                key = "controller.grow.id." + controllerid
                                if keyStore.exists(key):
                                    if growid == keyStore.get(key):
                                        keyStore.delete(key)
                            else:
                                if "status_msg" in response:
                                    print("ERROR: {} {}".format(response["status_code"],response["status_msg"]))
                                else:
                                    print("ERROR: {}".format(response["status_code"]))
                                raise cherrypy.HTTPError(502)
                                return
                        finally:
                            qdCur.close()
                            qdConn.close()
                    finally:
                        qdCur.close()
                        qdConn.close()
        finally:
            pgCur.close()
            pgConn.close()

        cherrypy.response.status = 202
        return

    @cherrypy.tools.json_in()
    def PUT(self, controllerid, growid):

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
            startdate = cherrypy.request.json["startdate"]
        except:
            pass
        else:
            raise cherrypy.HTTPError(400, "Cannot change start date.")
            return

        try:
            veglen = cherrypy.request.json["veglen"]
        except:
            pass
        else:
            raise cherrypy.HTTPError(400, "Cannot change veglen.")
            return

        try:
            flowerlen = cherrypy.request.json["flowerlen"]
        except:
            pass
        else:
            raise cherrypy.HTTPError(400, "Cannot change flowerlen.")
            return

        try:
            pgConn = psycopg.connect(pgConnectStr)
        except:
            print("ERROR: Unable to connect to Postgres service at: {}".format(pgConnectStr))
            raise cherrypy.HTTPError(502)
            return
        else:
            pgCur = pgConn.cursor()

            pgCur.execute("""SELECT array_to_json(array_agg(row_to_json(t))) FROM (SELECT 
                           phase,active FROM """ +
                           schema + ".grows WHERE growid = %s) t""", ([growid]))

            result = pgCur.fetchall()
            try:
                grow = result[0][0][0]
            except:
                pgCur.close()
                pgConn.close()
                raise cherrypy.HTTPError(404, "Growid not found.")
                return

        jsonData = {}
        inputs = list()
        SQL = ""

        try:
            harvest = cherrypy.request.json["harvest"]
        except:
            pass
        else:
            if not harvest == "yes":
                raise cherrypy.HTTPError(400, "Invalid value for harvest parameter.")
                return

            if grow["active"] == "no":
                raise cherrypy.HTTPError(409, "Cannot harvest an inactive grow.")
                return 

            jsonData["harvest"] = harvest

        try:
            harvestdate = cherrypy.request.json["harvestdate"]
            try:
                dt = datetime.fromisoformat(harvestdate)
            except:
                raise cherrypy.HTTPError(400, "Must supply a valid harvest date.")
                return
            else:
                if grow["active"] == "no":
                    raise cherrypy.HTTPError(409, "Cannot harvest an inactive grow.")
                    return 

                jsonData["harvested"] = harvestdate
        except:
            pass

        try:
            active = cherrypy.request.json["active"]
        except:
            active = "unspecified"
        else:
            if not active == "no":
                raise cherrypy.HTTPError(400, "Invalid value for active parameter.")
                return

            if grow["active"] == False:
                raise cherrypy.HTTPError(409, "Grow is already inactive.")
                return 

            inputs.append(active)
            jsonData["active"] = "False"
            SQL += "active = %s"

        try:
            name = cherrypy.request.json["name"]
        except:
            pass
        else:
            if len(SQL) > 0:
                sep = ", "
            else:
                sep = ""
            SQL += sep + "name = %s"
            inputs.append(name)
            jsonData["name"] = name

        try:
            strain = cherrypy.request.json["strain"]
        except:
            pass
        else:
            if len(SQL) > 0:
                sep = ", "
            else:
                sep = ""
            SQL += sep + "strain = %s"
            inputs.append(strain)
            jsonData["strain"] = strain

        try:
            medium = cherrypy.request.json["medium"]
        except:
            pass
        else:
            if len(SQL) > 0:
                sep = ", "
            else:
                sep = ""
            SQL += sep + "medium = %s"
            inputs.append(medium)
            jsonData["medium"] = medium

        try:
            lighting = cherrypy.request.json["lighting"]
        except:
            pass
        else:
            if len(SQL) > 0:
                sep = ", "
            else:
                sep = ""
            SQL += sep + "lighting = %s"
            inputs.append(lighting)
            jsonData["lighting"] = lighting

        try:
            growspace = cherrypy.request.json["growspace"]
        except:
            pass
        else:
            if len(SQL) > 0:
                sep = ", "
            else:
                sep = ""
            SQL += sep + "growspace = %s"
            inputs.append(growspace)
            jsonData["growspace"] = growspace

        try:
            phase = cherrypy.request.json["phase"]
        except:
            pass
        else:
            if not phase in ["veg", "flower"]:
                raise cherrypy.HTTPError(400, "Must supply a valid phase.")
                return

            if phase == "veg" and grow["phase"] == "flower":
                raise cherrypy.HTTPError(409, "Cannot change from flower to veg phase.")
                return

            if len(SQL) > 0:
                sep = ", "
            else:
                sep = ""
            SQL += sep + "phase = %s"
            inputs.append(phase)
            jsonData["phase"] = phase

        inputs.append(growid)

        if len(SQL) > 0:
            pgCur.execute("UPDATE " + schema + ".grows SET " + SQL +
                      " WHERE growid = %s", (inputs))

            pgConn.commit()

        if grow["active"] == True:

            request = {'method':'PUT','url':'grow/id/' + growid,'json':jsonData}

            response = req.request_handler(controllerid, request)

            if response["status_code"] == 202:
    
                if grow["active"] == True and active == "no":
                    key = "controller.grow.id." + controllerid
                    if keyStore.exists(key):
                        if growid == keyStore.get(key):
                            keyStore.delete(key)

                elif active == "yes":
                    key = "controller.grow.id." + controllerid
                    keyStore.set(key, growid)
                    keyStore.persist(key)
            else:
                pgCur.close()
                pgConn.close()
                if "status_msg" in response:
                    print("ERROR: {} {}".format(response["status_code"],response["status_msg"]))
                else:
                    print("ERROR: {}".format(response["status_code"]))
                raise cherrypy.HTTPError(502)
                return

        pgCur.close()
        pgConn.close()

        cherrypy.response.status = 202
        return


