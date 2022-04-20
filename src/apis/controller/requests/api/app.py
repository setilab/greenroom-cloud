#!/usr/bin/env python3

import cherrypy
import json
from v1 import *
from v2 import *


@cherrypy.expose
class Versions(object):

    @cherrypy.tools.json_out()
    def GET(self):
        return {'service':'Controller Requests API','versions':['v1','v2']}


if __name__ == '__main__':

    cherrypy.config.update({'server.socket_host': '0.0.0.0',
                            'server.socket_port': 8080,
                           })

    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'request.show_tracebacks': False,
            'tools.encode.on': True,
            'tools.sessions.on': True,
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Content-Type', 'application/json')],
        }
    }
    cherrypy.tree.mount(V1(), '/v1', conf)
    cherrypy.tree.mount(V2(), '/v2', conf)
    cherrypy.quickstart(Versions(), '/', conf)

