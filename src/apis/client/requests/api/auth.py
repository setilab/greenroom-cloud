import os
import cherrypy
import redis

# Redis
RHOST   =     os.getenv("REDIS_SERVICE_HOST", "redis.tgr.svc.cluster.local")
RPORT   = int(os.getenv("REDIS_SERVICE_PORT", "6379"))

def AuthSession():

        if not "apikey" in cherrypy.session:
            print("Missing apikey.")
            return None

        apikey = cherrypy.session["apikey"]

        if not "scope" in cherrypy.session:
            print("Missing scope.")
            return None

        scope = cherrypy.session["scope"]

        try:
            keyStore = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return None

        key = "api.session.id.{}".format(apikey)
        sessionid = keyStore.get(key)

        if not sessionid == cherrypy.session.id:
            print("Session ids don't match.")
            print("sessionid: {}".format(sessionid))
            print("cherrypy sessionid: {}".format(cherrypy.session.id))
            return None

        keyStore.pexpire(key, 3000)
        return scope

