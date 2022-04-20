#!/bin/bash

../build/client.api.wsock.build
kubectl delete deploy -n tgr client-api-wsock
kubectl apply -f ../deploy/client-api-wsock.yaml
sleep 15
kubectl get pods -n tgr
