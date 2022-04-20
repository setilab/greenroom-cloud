#!/usr/bin/env python3

import os
import cherrypy
import redis
import req
from auth import *


# Redis
RHOST   =     os.getenv("REDIS_SERVICE_HOST", "redis.tgr.svc.cluster.local")
RPORT   = int(os.getenv("REDIS_SERVICE_PORT", "6379"))

keyNs   = "controller.rtdata."


@cherrypy.expose
@cherrypy.popargs('controllerid')
class Relays_v1(object):

    def __init__(self):
        self.id = Relay_v1()
        self.keys = RelaysKeys_v1()
        self.states = RelaysStates_v1()
        self.properties = RelaysProperties_v1()

    @cherrypy.tools.json_out()
    def GET(self, controllerid):

        accountid = AuthSession()

        if accountid == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = "controller.account.id." + controllerid
        if ds.exists(key):
            if not accountid == ds.get(key):
                raise cherrypy.HTTPError(403, "Unauthorized access.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return

        key = keyNs + "ids"
        if ds.exists(key) and ds.sismember(key, controllerid):
            key = keyNs + "status." + controllerid
            if ds.exists(key) and ds.get(key) == "online":

                names = ds.hgetall(keyNs + "relay.names." + controllerid)

                names.pop("timeStamp")
                relays = list(names.values())

                return {'data':relays}
            else:
                print("ERROR: Unable to fetch relay names for controller: {}".format(controllerid))
                raise cherrypy.HTTPError(502)
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return


@cherrypy.expose
class RelaysKeys_v1(object):

    @cherrypy.tools.json_out()
    def GET(self, controllerid):

        accountid = AuthSession()

        if accountid == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = "controller.account.id." + controllerid
        if ds.exists(key):
            if not accountid == ds.get(key):
                raise cherrypy.HTTPError(403, "Unauthorized access.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return

        key = keyNs + "ids"
        if ds.exists(key) and ds.sismember(key, controllerid):
            key = keyNs + "status." + controllerid
            if ds.exists(key) and ds.get(key) == "online":

                names = ds.hgetall(keyNs + "relay.names." + controllerid)

                names.pop("timeStamp")

                return {'data':names}
            else:
                print("ERROR: Unable to fetch relay keys for controller: {}".format(controllerid))
                raise cherrypy.HTTPError(502)
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return


@cherrypy.expose
@cherrypy.popargs('state')
class RelaysStates_v1(object):

    @cherrypy.tools.json_out()
    def GET(self, controllerid):

        accountid = AuthSession()

        if accountid == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = "controller.account.id." + controllerid
        if ds.exists(key):
            if not accountid == ds.get(key):
                raise cherrypy.HTTPError(403, "Unauthorized access.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return

        key = keyNs + "ids"
        if ds.exists(key) and ds.sismember(key, controllerid):
            key = keyNs + "status." + controllerid
            if ds.exists(key) and ds.get(key) == "online":

                states = ds.hgetall(keyNs + "relay.states." + controllerid)
                modes = ds.hgetall(keyNs + "relay.modes." + controllerid)
                names = ds.hgetall(keyNs + "relay.names." + controllerid)

                states.pop("timeStamp")
                modes.pop("timeStamp")
                names.pop("timeStamp")

                relayData = {}

                for id in names:
                    relayData[names[id]] = {'id':id,'state':states[id],'mode':modes[id]}

                return {'data':relayData}
            else:
                print("ERROR: Unable to fetch relay data for controller: {}".format(controllerid))
                raise cherrypy.HTTPError(502)
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return

    def PUT(self, controllerid, state):

        accountid = AuthSession()

        if accountid == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

        inputs = ['off', 'auto', 'manual']
        if not state in inputs:
            raise cherrypy.HTTPError(400, "Invalid parameter {}".format(state))
            return

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = "controller.account.id." + controllerid
        if ds.exists(key):
            if not accountid == ds.get(key):
                raise cherrypy.HTTPError(403, "Unauthorized access.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return

        key = keyNs + "ids"
        if ds.exists(key) and ds.sismember(key, controllerid):
            key = keyNs + "status." + controllerid
            if ds.exists(key) and ds.get(key) == "online":

                request = {'method':'PUT','url':'relays/states/' + state}

                response = req.request_handler(controllerid, request)

                if response["status_code"] == 202:
                    cherrypy.response.status = 202
                    return
                else:
                    raise cherrypy.HTTPError(502)
            else:
                raise cherrypy.HTTPError(503, "Controller unregistered or offline.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return


@cherrypy.expose
class RelaysProperties_v1(object):

    @cherrypy.tools.json_out()
    def GET(self, controllerid):

        accountid = AuthSession()

        if accountid == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = "controller.account.id." + controllerid
        if ds.exists(key):
            if not accountid == ds.get(key):
                raise cherrypy.HTTPError(403, "Unauthorized access.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return

        key = keyNs + "ids"
        if ds.exists(key) and ds.sismember(key, controllerid):
            key = keyNs + "status." + controllerid
            if ds.exists(key) and ds.get(key) == "online":

                request = {'method':'GET','url':'relays/properties'}

                response = req.request_handler(controllerid, request)

                if response["status_code"] == 200:
                    return response["body"]
                else:
                    raise cherrypy.HTTPError(502)
            else:
                raise cherrypy.HTTPError(503, "Controller unregistered or offline.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return


@cherrypy.expose
@cherrypy.popargs('relay')
class Relay_v1(object):

    def __init__(self):
        self.state = RelayState_v1()
        self.name = RelayName_v1()
        self.device = RelayDevice_v1()
        self.timer = RelayTimer_v1()

    @cherrypy.tools.json_out()
    def GET(self, controllerid, relay):

        accountid = AuthSession()

        if accountid == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = "controller.account.id." + controllerid
        if ds.exists(key):
            if not accountid == ds.get(key):
                raise cherrypy.HTTPError(403, "Unauthorized access.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return

        key = keyNs + "ids"
        if ds.exists(key) and ds.sismember(key, controllerid):
            key = keyNs + "status." + controllerid
            if ds.exists(key) and ds.get(key) == "online":

                request = {'method':'GET','url':'relays/id/' + relay + "/properties"}

                response = req.request_handler(controllerid, request)

                if response["status_code"] == 200:
                    return response["body"]
                else:
                    raise cherrypy.HTTPError(502)
            else:
                raise cherrypy.HTTPError(503, "Controller unregistered or offline.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return


@cherrypy.expose
@cherrypy.popargs('state')
class RelayState_v1(object):

    def PUT(self, controllerid, relay, state):

        accountid = AuthSession()

        if accountid == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

        inputs = ['on', 'off', 'auto', 'manual']
        if not state in inputs:
            raise cherrypy.HTTPError(400, "Invalid parameter {}".format(state))
            return

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = "controller.account.id." + controllerid
        if ds.exists(key):
            if not accountid == ds.get(key):
                raise cherrypy.HTTPError(403, "Unauthorized access.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return

        key = keyNs + "ids"
        if ds.exists(key) and ds.sismember(key, controllerid):
            key = keyNs + "status." + controllerid
            if ds.exists(key) and ds.get(key) == "online":

                request = {'method':'PUT','url':'relays/id/' + relay + "/" + state}

                response = req.request_handler(controllerid, request)

                if response["status_code"] == 202:
                    cherrypy.response.status = 202
                    return
                else:
                    raise cherrypy.HTTPError(502)
            else:
                raise cherrypy.HTTPError(503, "Controller unregistered or offline.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return


@cherrypy.expose
@cherrypy.popargs('name')
class RelayName_v1(object):

    def PUT(self, controllerid, relay, name):

        accountid = AuthSession()

        if accountid == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = "controller.account.id." + controllerid
        if ds.exists(key):
            if not accountid == ds.get(key):
                raise cherrypy.HTTPError(403, "Unauthorized access.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return

        key = keyNs + "ids"
        if ds.exists(key) and ds.sismember(key, controllerid):
            key = keyNs + "status." + controllerid
            if ds.exists(key) and ds.get(key) == "online":

                request = {'method':'PUT','url':'relays/id/' + relay + "/name/" + name}

                response = req.request_handler(controllerid, request)

                if response["status_code"] == 202:
                    cherrypy.response.status = 202
                    return
                else:
                    raise cherrypy.HTTPError(502)
            else:
                raise cherrypy.HTTPError(503, "Controller unregistered or offline.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return


@cherrypy.expose
@cherrypy.popargs('device')
class RelayDevice_v1(object):

    def PUT(self, controllerid, relay, device):

        accountid = AuthSession()

        if accountid == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = "controller.account.id." + controllerid
        if ds.exists(key):
            if not accountid == ds.get(key):
                raise cherrypy.HTTPError(403, "Unauthorized access.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return

        if not device in ds.smembers("controller.device.types"):
            raise cherrypy.HTTPError(400, "Invalid device type '{}' provided.".format(device))
            return

        key = keyNs + "ids"
        if ds.exists(key) and ds.sismember(key, controllerid):
            key = keyNs + "status." + controllerid
            if ds.exists(key) and ds.get(key) == "online":

                request = {'method':'PUT','url':'relays/id/' + relay + "/device/" + device}

                response = req.request_handler(controllerid, request)

                if response["status_code"] == 202:
                    cherrypy.response.status = 202
                    return
                else:
                    raise cherrypy.HTTPError(502)
            else:
                raise cherrypy.HTTPError(503, "Controller unregistered or offline.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return


@cherrypy.expose
@cherrypy.popargs('device')
class RelayTimer_v1(object):

    @cherrypy.tools.json_out()
    def GET(self, controllerid, relay):

        accountid = AuthSession()

        if accountid == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = "controller.account.id." + controllerid
        if ds.exists(key):
            if not accountid == ds.get(key):
                raise cherrypy.HTTPError(403, "Unauthorized access.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return

        key = keyNs + "ids"
        if ds.exists(key) and ds.sismember(key, controllerid):
            key = keyNs + "status." + controllerid
            if ds.exists(key) and ds.get(key) == "online":

                request = {'method':'GET','url':'relays/id/' + relay + "/timer"}

                response = req.request_handler(controllerid, request)

                if response["status_code"] == 200:
                    return response["body"]
                else:
                    raise cherrypy.HTTPError(502)
            else:
                raise cherrypy.HTTPError(503, "Controller unregistered or offline.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return

    @cherrypy.tools.json_in()
    def PUT(self, controllerid, relay):

        accountid = AuthSession()

        if accountid == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = "controller.account.id." + controllerid
        if ds.exists(key):
            if not accountid == ds.get(key):
                raise cherrypy.HTTPError(403, "Unauthorized access.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return

        try:
            onhour = cherrypy.request.json["onhour"]
        except:
            raise cherrypy.HTTPError(400, "Must provide 'onhour' parameter.")
            return
        else:
            if int(onhour) < 0 or int(onhour) > 23:
                raise cherrypy.HTTPError(400, "Value for 'onhour' parameter must be within the range of 0-23.")
                return

        try:
            onmin = cherrypy.request.json["onmin"]
        except:
            raise cherrypy.HTTPError(400, "Must provide 'onmin' parameter.")
            return
        else:
            if int(onmin) < 0 or int(onmin) > 59:
                raise cherrypy.HTTPError(400, "Value for 'onmin' parameter must be within the range of 0-59.")
                return

        try:
            offhour = cherrypy.request.json["offhour"]
        except:
            raise cherrypy.HTTPError(400, "Must provide 'offhour' parameter.")
            return
        else:
            if int(offhour) < 0 or int(offhour) > 23:
                raise cherrypy.HTTPError(400, "Value for 'offhour' parameter must be within the range of 0-23.")
                return

        try:
            offmin = cherrypy.request.json["offmin"]
        except:
            raise cherrypy.HTTPError(400, "Must provide 'offmin' parameter.")
            return
        else:
            if int(onmin) < 0 or int(onmin) > 59:
                raise cherrypy.HTTPError(400, "Value for 'offmin' parameter must be within the range of 0-59.")
                return

        jsonData = {'onhour':onhour,'onmin':onmin,'offhour':offhour,'offmin':offmin}

        key = keyNs + "ids"
        if ds.exists(key) and ds.sismember(key, controllerid):
            key = keyNs + "status." + controllerid
            if ds.exists(key) and ds.get(key) == "online":

                request = {'method':'PUT','url':'relays/id/' + relay + "/timer",'json':jsonData}

                response = req.request_handler(controllerid, request)

                if response["status_code"] == 202:
                    cherrypy.response.status = 202
                    return
                else:
                    raise cherrypy.HTTPError(502)
            else:
                raise cherrypy.HTTPError(503, "Controller unregistered or offline.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return

    @cherrypy.tools.json_out()
    def DELETE(self, controllerid, relay):

        accountid = AuthSession()

        if accountid == None:
            raise cherrypy.HTTPError(401, "Requires authentication.")
            return

        try:
            ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
        except:
            print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
            raise cherrypy.HTTPError(502)
            return

        key = "controller.account.id." + controllerid
        if ds.exists(key):
            if not accountid == ds.get(key):
                raise cherrypy.HTTPError(403, "Unauthorized access.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return

        key = keyNs + "ids"
        if ds.exists(key) and ds.sismember(key, controllerid):
            key = keyNs + "status." + controllerid
            if ds.exists(key) and ds.get(key) == "online":

                request = {'method':'DELETE','url':'relays/id/' + relay + "/timer"}

                response = req.request_handler(controllerid, request)

                if response["status_code"] == 202:
                    cherrypy.response.status = 202
                    return
                else:
                    raise cherrypy.HTTPError(502)
            else:
                raise cherrypy.HTTPError(503, "Controller unregistered or offline.")
                return
        else:
            raise cherrypy.HTTPError(404, "Controller id not found.")
            return


