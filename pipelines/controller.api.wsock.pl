#!/bin/bash

if [ "$1" == "api" ]; then
    ../build/controller.api.wsock.build

elif [ "$1" == "events" ]; then
    ../build/controller.events.wsock.build

else
    ../build/controller.api.wsock.build
    ../build/controller.events.wsock.build
fi

kubectl delete deploy -n tgr controller-api-wsock
kubectl apply -f ../deploy/controller-api-wsock.yaml
sleep 15
kubectl get pods -n tgr
