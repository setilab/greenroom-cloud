#!/usr/bin/env python3

import os
import datetime as dt
import cherrypy
import redis
import json
import psycopg


# Version & build
VERSION = "1.0"
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
        self.account = Account_v1()
        self.metadata = AccountMetadata_v1()
        self.version = Version_v1()


@cherrypy.expose
class Version_v1(object):

    @cherrypy.tools.json_out()
    def GET(self):
        return {'version':VERSION,'build':BUILD}


@cherrypy.expose
class Account_v1(object):

    def __init__(self):
        self.info = AccountInfo_v1()
        self.login = AccountLogin_v1()

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self):

        try:
            serialnum = cherrypy.request.json["serialnum"]
        except:
            raise cherrypy.HTTPError(400, "Invalid or missing 'serialnum' parameter.")
            return

        try:
            email = cherrypy.request.json["email"]
        except:
            raise cherrypy.HTTPError(400, "Invalid or missing 'email' parameter.")
            return

        try:
            password = cherrypy.request.json["password"]
        except:
            raise cherrypy.HTTPError(400, "Invalid or missing 'password' parameter.")
            return

        try:
            first = cherrypy.request.json["first"]
        except:
            first = ""

        try:
            last = cherrypy.request.json["last"]
        except:
            last = ""

        try:
            address1 = cherrypy.request.json["address1"]
        except:
            address1 = ""

        try:
            address2 = cherrypy.request.json["address2"]
        except:
            address2 = ""

        try:
            city = cherrypy.request.json["city"]
        except:
            city = ""

        try:
            state = cherrypy.request.json["state"]
        except:
            state = "none"

        try:
            zipcode = cherrypy.request.json["zip"]
        except:
            zipcode = ""

        try:
            country = cherrypy.request.json["country"]
        except:
            country = "none"

        try:
            phone = cherrypy.request.json["phone"]
        except:
            phone = ""

        try:
            membership = cherrypy.request.json["membership"]
        except:
            membership = "basic"

        active = "true"

        try:
            billcycle = cherrypy.request.json["billcycle"]
        except:
            billcycle = "monthly"

        try:
            conn = psycopg.connect(pgConnectStr)
        except:
            print("ERROR: Unable to connect to Postgres service at: {}".format(pgConnectStr))
            raise cherrypy.HTTPError(502)
            return

        cur = conn.cursor()

        try:
            cur.execute("INSERT INTO public.accounts " +
                        "(first, last, email, password, address1, " +
                        "address2, city, state, zip, country, " +
                        "phone, membership, active, billcycle) " +
                        "VALUES " +
                        "(%s, %s, %s, crypt(%s, gen_salt('bf', 8)), %s, %s, %s, " +
                        "%s, %s, %s, %s, %s, %s, %s) " +
                        "RETURNING (accountid, schemaid)",
                        (first, last, email, password, address1,
                         address2, city, state, zipcode, country,
                         phone, membership, active, billcycle))

        except psycopg.errors.UniqueViolation as ex:
            print("{}: {}".format(ex.diag.message_primary,ex.diag.message_detail))
            raise cherrypy.HTTPError(409)
            return
        except:
            raise cherrypy.HTTPError(400)
            return

        result = cur.fetchall()

        accountid,schemaid = result[0][0]
        schema = "cust_{}".format(schemaid.strip('\n'))

        try:
            keyStore = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = "account.schema." + accountid
        keyStore.set(key, schema)
        keyStore.persist(key)

        cur.execute("UPDATE public.controllers " +
                    "SET accountid = %s WHERE serialnum = %s",
                    (accountid, serialnum))

        cur.execute("INSERT INTO " + schema + ".controllers " +
                    "(serialnum) " +
                    "VALUES (%s) " +
                    "RETURNING (cloudsvcid)", ([serialnum]))

        result = cur.fetchall()
        conn.commit()
        cur.close()
        conn.close()

        cloudsvcid = "{}".format(result[0][0])

        key = "controller.account.id." + cloudsvcid
        keyStore.set(key, accountid)
        keyStore.persist(key)

        key = "account.controller.ids." + accountid
        keyStore.sadd(key, cloudsvcid)
        keyStore.persist(key)

        result = {'accountid':accountid,'cloudsvcid':cloudsvcid}
        return result


@cherrypy.expose
#@cherrypy.popargs('accountid')
class AccountInfo_v1(object):

    def __init__(self):
        self.controller = AccountController_v1()

    def DELETE(self):

        accountid = AuthSession()

        if accountid == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

        try:
            keyStore = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redia service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = "account.controller.ids." + accountid
        if keyStore.exists(key):
            for controllerid in keyStore.smembers(key):
                if keyStore.exists("controller.rtdata.ids"):
                    keyStore.srem("controller.rtdata.ids", controllerid)

                if keyStore.exists("controller.requests.ids"):
                    keyStore.srem("controller.requests.ids", controllerid)

                for k in keyStore.keys("*." + controllerid):
                    keyStore.delete(k)

            keyStore.delete(key)

        key = "account.schema." + accountid
        if keyStore.exists(key):
            keyStore.delete(key)

        try:
            conn = psycopg.connect(pgConnectStr)
        except:
            print("ERROR: Unable to connect to Postgres service at: {}".format(pgConnectStr))
            raise cherrypy.HTTPError(502)
            return

        cur = conn.cursor()

        cur.execute("UPDATE public.controllers " +
                    "SET accountid = NULL WHERE accountid = %s",
                    ([accountid]))

        cur.execute("DELETE FROM public.accounts WHERE accountid = %s",
                    ([accountid]))

        conn.commit()
        cur.close()
        conn.close()

        cherrypy.response.status = 202
        return

    @cherrypy.tools.json_out()
    def GET(self):

        accountid = AuthSession()

        if accountid == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

        try:
            conn = psycopg.connect(pgConnectStr)
        except:
            print("ERROR: Unable to connect to Postgres service at: {}".format(pgConnectStr))
            raise cherrypy.HTTPError(502)
            return

        cur = conn.cursor()

        cur.execute("SELECT array_to_json(array_agg(row_to_json(t))) FROM (SELECT " +
	            "accountid,first,last,email,address1,address2,city," +
                    "state,zip,country,phone,membership,active,billcycle " +
	            "FROM public.accounts WHERE accountid = %s) t", ([accountid]))

        accountInfo = cur.fetchall()

        cur.execute("SELECT array_to_json(array_agg(row_to_json(t))) FROM (SELECT " +
                    "model,serialnum,macaddr " +
	            "FROM public.controllers WHERE accountid = %s) t", ([accountid]))

        controllers = cur.fetchall()

        cur.close()
        conn.close()

        result = accountInfo[0][0][0]
        result["controllers"] = controllers[0][0]
        return result

    @cherrypy.tools.json_in()
    def PUT(self):

        accountid = AuthSession()

        if accountid == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

        inputs = list()
        SQL = ""

        try:
            inputs.append(cherrypy.request.json["email"])
        except:
            pass
        else:
            SQL += "email = %s"

        try:
            inputs.append(cherrypy.request.json["password"])
        except:
            pass
        else:
            if len(SQL) > 0:
                sep = ", "
            else:
                sep = ""
            SQL += sep + "password = crypt(%s, gen_salt('bf', 8))"

        try:
            inputs.append(cherrypy.request.json["first"])
        except:
            pass
        else:
            if len(SQL) > 0:
                sep = ", "
            else:
                sep = ""
            SQL += sep + "first = %s"

        try:
            inputs.append(cherrypy.request.json["last"])
        except:
            pass
        else:
            if len(SQL) > 0:
                sep = ", "
            else:
                sep = ""
            SQL += sep + "last = %s"

        try:
            inputs.append(cherrypy.request.json["address1"])
        except:
            pass
        else:
            if len(SQL) > 0:
                sep = ", "
            else:
                sep = ""
            SQL += sep + "address1 = %s"

        try:
            inputs.append(cherrypy.request.json["address2"])
        except:
            pass
        else:
            if len(SQL) > 0:
                sep = ", "
            else:
                sep = ""
            SQL += sep + "address2 = %s"

        try:
            inputs.append(cherrypy.request.json["city"])
        except:
            pass
        else:
            if len(SQL) > 0:
                sep = ", "
            else:
                sep = ""
            SQL += sep + "city = %s"

        try:
            inputs.append(cherrypy.request.json["state"])
        except:
            pass
        else:
            if len(SQL) > 0:
                sep = ", "
            else:
                sep = ""
            SQL += sep + "state = %s"

        try:
            inputs.append(cherrypy.request.json["zip"])
        except:
            pass
        else:
            if len(SQL) > 0:
                sep = ", "
            else:
                sep = ""
            SQL += sep + "zip = %s"

        try:
            inputs.append(cherrypy.request.json["country"])
        except:
            pass
        else:
            if len(SQL) > 0:
                sep = ", "
            else:
                sep = ""
            SQL += sep + "country = %s"

        try:
            inputs.append(cherrypy.request.json["phone"])
        except:
            pass
        else:
            if len(SQL) > 0:
                sep = ", "
            else:
                sep = ""
            SQL += sep + "phone = %s"

        try:
            inputs.append(cherrypy.request.json["membership"])
        except:
            pass
        else:
            if len(SQL) > 0:
                sep = ", "
            else:
                sep = ""
            SQL += sep + "membership = %s"

        try:
            inputs.append(cherrypy.request.json["active"])
        except:
            pass
        else:
            if len(SQL) > 0:
                sep = ", "
            else:
                sep = ""
            SQL += sep + "active = %s"

        try:
            inputs.append(cherrypy.request.json["billcycle"])
        except:
            pass
        else:
            if len(SQL) > 0:
                sep = ", "
            else:
                sep = ""
            SQL += sep + "billcycle = %s"

        inputs.append(accountid)

        try:
            conn = psycopg.connect(pgConnectStr)
        except:
            print("ERROR: Unable to connect to Postgres service at: {}".format(pgConnectStr))
            raise cherrypy.HTTPError(502)
            return

        cur = conn.cursor()

        cur.execute("UPDATE public.accounts SET " + SQL +
                    " WHERE accountid = %s", (inputs))

        conn.commit()
        cur.close()
        conn.close()

        cherrypy.response.status = 202
        return


@cherrypy.expose
class AccountLogin_v1(object):

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def PUT(self):

        try:
            email = cherrypy.request.json["email"]
        except:
            raise cherrypy.HTTPError(400, "Missing 'email' parameter.")
            return

        try:
            password = cherrypy.request.json["password"]
        except:
            raise cherrypy.HTTPError(400, "Missing 'password' parameter.")
            return

        try:
            conn = psycopg.connect(pgConnectStr)
        except:
            print("ERROR: Unable to connect to Postgres service at: {}".format(pgConnectStr))
            raise cherrypy.HTTPError(502)
            return

        cur = conn.cursor()

        cur.execute("SELECT accountid,membership,active FROM accounts " +
                    "WHERE email = lower(%s) AND " +
                    "password = crypt(%s, password)",
                    (email, password))

        result = cur.fetchall()

        try:
            accountid = result[0][0]
        except:
            print("ERROR: Failed login attempt from {}".format(email))
            raise cherrypy.HTTPError(401, "Invalid login attempt.")
            return
            
        membership = result[0][1]

        if result[0][2] == True:
            active = "yes"
        else:
            active = "no"

        cur.close()
        conn.close()

        try:
            keyStore = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        if not "accountid" in cherrypy.session:
            cherrypy.session["accountid"] = "{}".format(accountid)
            cherrypy.session["membership"] = membership
            cherrypy.session["active"] = active

        key = "account.session.id.{}".format(accountid)
        keyStore.set(key, cherrypy.session.id)
        keyStore.pexpire(key, 300000)

        return


@cherrypy.expose
@cherrypy.popargs('serialnum')
class AccountController_v1(object):

    @cherrypy.tools.json_out()
    def GET(self, serialnum):

        accountid = AuthSession()

        if accountid == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

        try:
            keyStore = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = "account.schema." + accountid
        if keyStore.exists(key):
            schema = keyStore.get(key)
        else:
            print("ERROR: Unable to locate schema for account: {}".format(accountid))
            raise cherrypy.HTTPError(502)
            return

        try:
            conn = psycopg.connect(pgConnectStr)
        except:
            print("ERROR: Unable to connect to Postgres service at: {}".format(pgConnectStr))
            raise cherrypy.HTTPError(502)
            return

        cur = conn.cursor()

        cur.execute("SELECT array_to_json(array_agg(row_to_json(t))) FROM (SELECT " +
                    "p.model,p.macaddr,c.cloudsvcid,c.name,c.growspace,c.usage " +
	            "FROM public.controllers AS p, " + schema + ".controllers AS c " +
                    "WHERE p.serialnum = %s AND p.serialnum = c.serialnum) t",
                    ([serialnum]))

        controller = cur.fetchall()

        cur.close()
        conn.close()

        try:
            result = controller[0][0][0]
        except:
            raise cherrypy.HTTPError(404, "Controller serial number not found.")
            return

        return result

    @cherrypy.tools.json_out()
    def PUT(self, serialnum):

        accountid = AuthSession()

        if accountid == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

        try:
            keyStore = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = "account.schema." + accountid
        if keyStore.exists(key):
            schema = keyStore.get(key)
        else:
            print("ERROR: Unable to locate schema for account: {}".format(accountid))
            raise cherrypy.HTTPError(500)
            return

        try:
            conn = psycopg.connect(pgConnectStr)
        except:
            print("ERROR: Unable to connect to Postgres service at: {}".format(pgConnectStr))
            raise cherrypy.HTTPError(502)
            return

        cur = conn.cursor()

        cur.execute("UPDATE public.controllers " +
                    "SET inservice = now(), accountid = %s WHERE serialnum = %s",
                    (accountid, serialnum))

        cur.execute("INSERT INTO " + schema + ".controllers " +
                    "(serialnum) " +
                    "VALUES ('" + serialnum + "') " +
                    "RETURNING (cloudsvcid)")

        result = cur.fetchall()
        conn.commit()
        cur.close()
        conn.close()

        cloudsvcid = "{}".format(result[0][0])

        key = "controller.account.id." + cloudsvcid
        keyStore.set(key, accountid)
        keyStore.persist(key)

        key = "account.controller.ids." + accountid
        keyStore.sadd(key, cloudsvcid)
        keyStore.persist(key)

        result = {'cloudsvcid':cloudsvcid}
        return result


@cherrypy.expose
@cherrypy.popargs('datatype')
class AccountMetadata_v1(object):

    @cherrypy.tools.json_out()
    def GET(self, datatype):

        try:
            conn = psycopg.connect(pgConnectStr)
        except:
            print("ERROR: Unable to connect to Postgres service at: {}".format(pgConnectStr))
            raise cherrypy.HTTPError(502)
            return

        cur = conn.cursor()

        if datatype == "country":
            cur.execute("SELECT * FROM public.country")

        else:
            cur.execute("""SELECT enum.enumlabel AS value FROM pg_enum AS enum
                           JOIN pg_type AS type ON (type.oid = enum.enumtypid)
                           WHERE type.typname = %s""",
                           ([datatype]))

        result = cur.fetchall()
        cur.close()
        conn.close()

        data = list()
        for row in result:
            if datatype == "country":
                data.append({row[0]:row[1]})
            else:
                data.append(row[0])

        return {'data':data}


def AuthSession():

        if not "accountid" in cherrypy.session:
            return None

        accountid = cherrypy.session.get("accountid")

        try:
            keyStore = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return None

        key = "account.session.id.{}".format(accountid)
        sessionid = keyStore.get(key)

        if not sessionid == cherrypy.session.id:
            return None

        keyStore.pexpire(key, 300000)
        return accountid

