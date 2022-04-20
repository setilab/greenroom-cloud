#!/usr/bin/env python

import requests
import json
import time

CLIENT_URL = "http://cloud.thegreenroom.io:32001/v2/"
controllerId = "717eccbf-28d2-4b1d-807c-47c85253973f"

session = requests.Session()

print("Checking status of controller {}".format(controllerId))

try:
    response = session.get(CLIENT_URL + "controller/" + controllerId)
except:
    print("Unable to connect to client api.")
    exit()
else:
    if response.ok:
        controller = json.loads(response.text)
        status = controller["status"]
        print("The controller is {}".format(status))

if status == "offline":
    print("Aborting any further interaction.")
    exit()

print("Submitting request for state of Lamp1 device.")

request = {'request':{'method':'GET','url':'relays/id/lamp1'}}

try:
    response = session.post(CLIENT_URL + "requests/" + controllerId, json=request)
except:
    print("Unable to connect to client api.")
    exit()
else:
    if response.ok:
        job = json.loads(response.text)
        jobId = job["jobid"]
        print("Request assigned job ID {}".format(jobId))
    else:
        print("There was a problem with the request.")
        print(response)
        exit()

while True:
    try:
        response = session.get(CLIENT_URL + "requests/" + controllerId +
                               "?jobId=" + jobId
                              )
    except:
        print("Unable to connect to client api.")
        exit()
    else:
        if response.ok:
            results = json.loads(response.text)
            status = results["job"]
            if status == "completed":
                response = results["response"]
                break
            time.sleep(2)
        else:
            time.sleep(2)

if status == "completed":
    state = response["body"]["data"]["state"]
    print("Job completed. Lamp1 is {}".format(state))

if state == "on":
    newState = "off"
elif state == "off":
    newState = "on"

print("Submitting request to turn it {}.".format(newState))

request = {'request':{'method':'PUT','url':'relays/id/lamp1/' + newState}}

try:
    response = session.post(CLIENT_URL + "requests/" + controllerId,
                           json=request
                          )
except:
    print("Unable to connect to client api.")
    exit()
else:
    if response.ok:
        job = json.loads(response.text)
        jobId = job["jobid"]
        print("Request assigned job ID {}".format(jobId))
    else:
        print("There was a problem with the request.")
        print(response)
        exit()

while True:
    try:
        response = session.get(CLIENT_URL + "requests/" + controllerId +
                               "?jobId=" + jobId
                              )
    except:
        print("Unable to connect to client api.")
        exit()
    else:
        if response.ok:
            results = json.loads(response.text)
            status = results["job"]
            if status == "completed":
                response = results["response"]
                break

        time.sleep(2)

if status == "completed":
    if response["status_code"] == 202:
        print("Success!")

