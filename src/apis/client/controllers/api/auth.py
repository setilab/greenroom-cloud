import os
import cherrypy
import redis

# Redis
RHOST   =     os.getenv("REDIS_SERVICE_HOST", "redis.tgr.svc.cluster.local")
RPORT   = int(os.getenv("REDIS_SERVICE_PORT", "6379"))

def AuthSession():

        if not "accountid" in cherrypy.session:
            return None

        accountid = cherrypy.session["accountid"]

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

