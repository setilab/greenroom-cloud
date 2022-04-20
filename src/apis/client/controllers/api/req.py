#!/usr/bin/env python3

import os
import time
import requests
import json


# Requests 
REQHOST = os.getenv("CLIENT_API_REQUESTS_SERVICE_HOST", "client-api-requests.tgr.svc.cluster.local")
REQPORT = os.getenv("CLIENT_API_REQUESTS_SERVICE_PORT", "8080")
REQAPI  = os.getenv("CLIENT_API_REQUESTS_API_VERSION", "v2")

CLIENT_WSHOST = os.getenv("CLIENT_API_WSOCK_SERVICE_HOST", "client-api-wsock.tgr.svc.cluster.local")
CLIENT_WSPORT = os.getenv("CLIENT_API_WSOCK_SERVICE_PORT", "9000")

CONTROLLER_WSHOST = os.getenv("CONTROLLER_API_WSOCK_SERVICE_HOST", "controller-api-wsock.tgr.svc.cluster.local")
CONTROLLER_WSPORT = os.getenv("CONTROLLER_API_WSOCK_SERVICE_PORT", "9000")

APIKEY   = os.getenv("CLIENT_API_KEY", "2abe1372-a98e-4d03-a56e-2ad5cd82fbfb")
APITOKEN = os.getenv("CLIENT_API_TOKEN", "cce33fd8-a627-4861-899a-9b13a1b30216")

LOGIN_URL   = f"http://{REQHOST}:{REQPORT}/{REQAPI}/login"
REQUEST_URL = f"http://{REQHOST}:{REQPORT}/{REQAPI}/requests/"
CLIENT_WS_URL = f"http://{CLIENT_WSHOST}:{CLIENT_WSPORT}"
CONTROLLER_WS_URL = f"http://{CONTROLLER_WSHOST}:{CONTROLLER_WSPORT}"

MAX_TRIES = 5


def request_handler(controllerid, request):

    session = requests.Session()

    reqData = {'apikey':APIKEY,'token':APITOKEN}

    try:
        response = session.put(LOGIN_URL, json=reqData)
    except:
        status_msg = "ERROR: Unable to connect to Controller API service at: {}".format(LOGIN_URL)
        return {'status_code':"502",'status_msg':status_msg}

    reqData = {'request':request}

    try:
        response = session.post(REQUEST_URL + controllerid, json=reqData)
    except:
        status_msg = "ERROR: Unable to connect to Controller API service at: {}".format(REQUEST_URL)
        return {'status_code':"502",'status_msg':status_msg}
    else:
        if response.ok:
            job = json.loads(response.text)
            jobId = job["jobid"]
        else:
            status_msg = "ERROR: Unexpected response from Controller API service: {}".format(response)
            return {'status_code':"502",'status_msg':status_msg}

        status = ""
        tries = 0
        while True:
            try:
                response = session.get(REQUEST_URL + controllerid + "?jobId=" + jobId)
            except:
                status_msg = "ERROR: Unable to connect to Controller API service at: {}".format(REQUEST_URL)
                return {'status_code':"502",'status_msg':status_msg}
            else:
                if response.ok:
                    results = json.loads(response.text)
                    status = results["job"]
                    if status == "completed":
                        response = results["response"]
                        break

                if tries == MAX_TRIES:
                    status_msg = "ERROR: Max tries awaiting response from Controller API service."
                    return {'status_code':"502",'status_msg':status_msg}
                else:
                    tries = tries + 1

                time.sleep(2)

        if status == "completed":
            return response
        else:
            status_msg = "ERROR: Unexpected response from Controller API service: {}".format(response)
            return {'status_code':"502",'status_msg':status_msg}


def websocket_handler(endpoint, path, controllerid):

    session = requests.Session()

    reqData = {'apikey':APIKEY,'token':APITOKEN}

    try:
        response = session.put(LOGIN_URL, json=reqData)
    except:
        status_msg = "ERROR: Unable to connect to Controller API service at: {}".format(LOGIN_URL)
        return {'status_code':502,'status_msg':status_msg}

    if endpoint == "client":
        ws_url = f"{CLIENT_WS_URL}/{path}/{controllerid}"
    else:
        ws_url = f"{CONTROLLER_WS_URL}/{path}/{controllerid}"

    try:
        response = session.get(ws_url)
    except:
        status_msg = "ERROR: Unable to connect to API service at: {}".format(ws_url)
        return {'status_code':502,'status_msg':status_msg}
    else:
        if response.ok:
            return {'status_code':202,'status_msg':"complete"}
        else:
            return {'status_code':response.status_code,'status_msg':response.text}


