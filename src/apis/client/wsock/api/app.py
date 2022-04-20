#!/usr/bin/env python

try:
    import wsaccel
    wsaccel.patch_ws4py()
except ImportError:
    pass

from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket, EchoWebSocket

import cherrypy
from cherrypy.process import plugins
import redis
import json
import os

# Version & build
VERSION = "1.00"
BUILD   = os.getenv("TGR_API_BUILD", "X.xxx")

# Redis
RHOST   =     os.getenv("REDIS_SERVICE_HOST", "redis.tgr.svc.cluster.local")
RPORT   = int(os.getenv("REDIS_SERVICE_PORT", "6379"))

ks = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)


class MyReader(object):

    def __init__(self, ks):
        self.data = ''

        ks.config_set('notify-keyspace-events', 'KEA')
        self.ks = ks

        pubsub = ks.pubsub()
        pubsub.psubscribe(**{'__keyspace@0__:*': self.events})
        self.thread = pubsub.run_in_thread(sleep_time=0.01)

    def events(self, msg):
        key = msg["channel"].split(":")[1]
        controllerid = self.ks.get("websocket.controllerid")
        if controllerid and key.endswith("." + controllerid):
            e = msg["data"]
            if e == "set":
                self.data += json.dumps({key:self.ks.get(key)}) + "\n"
            elif e == "hset":
                self.data += json.dumps({key:self.ks.hgetall(key)}) + "\n"
            elif e == "sadd":
                self.data += json.dumps({key:list(self.ks.smembers(key))}) + "\n"
            elif e == "del":
                self.data += json.dumps({key:"deleted"}) + "\n"
            elif e == "expired":
                self.data += json.dumps({key:"expired"}) + "\n"

    def read(self):
        data = self.data
        if len(data) > 0:
            self.data = ''
            return data


myReader = MyReader(ks)

class MonitorWebSocketHandler(WebSocket):
    def received_message(self, m):
        self.send(cherrypy.engine.websockets.currentData)


class MonitorWebSocketPlugin(WebSocketPlugin):
    def __init__(self, bus, reader):
        WebSocketPlugin.__init__(self, bus)

        self.bus = bus
        self.reader = reader
        self.currentData = reader.read()
        plugins.Monitor(bus, self.broadcastChanges, 0.1).subscribe()

    def broadcastChanges(self):
        newData = self.reader.read()
        if (newData != self.currentData):
             self.bus.publish('websocket-broadcast', newData)
             self.currentData = newData


class Nothing(object):
    @cherrypy.expose
    def index(self):
        pass

    @cherrypy.expose
    def ws(self):
        pass


class Root(object):
    @cherrypy.expose
    def index(self):
        return "TGR Cloud Websocket Service"

    @cherrypy.expose
    def add(self, controllerid):
        ks.set("websocket.controllerid", controllerid)
        # Try to create a new websocket-capable path.
        conf = {"/ws": {"tools.websocket.on": True, "tools.websocket.handler_cls": MonitorWebSocketHandler}}
        cherrypy.tree.mount(Nothing(), "/controller/" + controllerid, config=conf)

    @cherrypy.expose
    def remove(self, controllerid):
        # Remove a previously created websocket-capable path.
        del cherrypy.tree.apps["/controller/" + controllerid]

    @cherrypy.expose
    def echo(self):
        pass


cherrypy.config.update({"server.socket_host": "0.0.0.0", "server.socket_port": 9000})
WebSocketPlugin(cherrypy.engine).subscribe()
cherrypy.tools.websocket = WebSocketTool()
cherrypy.engine.websockets = MonitorWebSocketPlugin(cherrypy.engine, myReader)
cherrypy.engine.signals.subscribe()

cherrypy.quickstart(Root(), "/", config={"/echo": {"tools.websocket.on": True,"tools.websocket.handler_cls": EchoWebSocket}})

