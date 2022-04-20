#!/bin/bash

if [ "$1" == "api" ]; then
    ../build/controller.api.requests.build

elif [ "$1" == "events" ]; then
    ../build/controller.events.requests.build

else
    ../build/controller.api.requests.build
    ../build/controller.events.requests.build
fi

kubectl delete deploy -n tgr controller-api-requests
kubectl apply -f ../deploy/controller-api-requests.yaml
sleep 15
kubectl get pods -n tgr
