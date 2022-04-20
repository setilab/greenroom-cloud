../build/client.api.controllers.build ; \
kubectl delete deploy -n tgr client-api-controllers ; \
kubectl apply -f ../deploy/client-api-controllers.yaml ; \
sleep 15 ; \
kubectl get pods -n tgr
