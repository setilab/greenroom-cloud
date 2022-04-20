#!/usr/bin/env python3

import websocket
import time

ws_url = "http://cloud.thegreenroom.io:31003/echo"

def ws_message(ws, message):
    print("websocket message: {}".format(message))


def ws_error(ws, error):
    print("websocket error: {}".format(error))


def ws_close(ws):
    print("websocket closed.")


def ws_open(ws):
    print("websocket opened...")
    while True:
        ws.send("Hello, world!")
        time.sleep(3)


ws = websocket.WebSocketApp(ws_url,
                            on_message = ws_message,
                            on_error = ws_error,
                            on_close = ws_close)
ws.on_open = ws_open
ws.run_forever()

