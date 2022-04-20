#!/usr/bin/env python

try:
    import wsaccel
    wsaccel.patch_ws4py()
except ImportError:
    pass

from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket

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


class MyWriter(object):
    def __init__(self, ks):
        self.ks = ks

    def write(self, data):
        (k,v) = list(data.items())[0]
        if k.startswith("temp.health."):
            return

        if type(v) is str:
            try:
                ks.set(k, v)
            except Exception as e:
                print(f"Add/update {k} of type {type(v)} with {v} caused {e}")
        elif type(v) is dict:
            try:
                ks.hset(k, mapping=v)
            except Exception as e:
                print(f"Add/update {k} of type {type(v)} with {v} caused {e}")
        elif type(v) is list:
            try:
                ks.sadd(k, v)
            except Exception as e:
                print(f"Add/update {k} of type {type(v)} with {v} caused {e}")
        else:
            print(f"Unknown data type {type(v)} for key: {k}")


class MyReader(object):

    def __init__(self, ks):
        self.data = ''

        ks.config_set('notify-keyspace-events', 'KEA')
        self.ks = ks

        pubsub = ks.pubsub()
        pubsub.psubscribe(**{'__keyspace@0__:websocket.send': self.events})
        self.thread = pubsub.run_in_thread(sleep_time=0.01)

    def events(self, msg):
        if msg["data"] == "hset":
            self.data = json.dumps(self.ks.hgetall('websocket.send'))

    def read(self):
        data = self.data
        if len(data) > 0:
            self.data = ''
            self.ks.delete('websocket.send')
            return data


myReader = MyReader(ks)
myWriter = MyWriter(ks)

class MonitorWebSocketHandler(WebSocket):
    def received_message(self, m):
        jsonData = json.loads(f"{m}")
        if jsonData.get("msg") == "ready":
            self.send('{"request":"initialize"}')
        elif jsonData.get("response") == "done":
            self.send('{"request":"subscribe"}')
        elif (cherrypy.engine.websockets.currentData is not None and
                len(cherrypy.engine.websockets.currentData) > 0):
            self.send(cherrypy.engine.websockets.currentData)
        else:
            myWriter.write(jsonData)


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

cherrypy.quickstart(Root(), "/", config={"/echo": {"tools.websocket.on": True,"tools.websocket.handler_cls": MonitorWebSocketHandler}})

