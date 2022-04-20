../build/client.api.requests.build ; \
kubectl delete deploy -n tgr client-api-requests ; \
kubectl apply -f ../deploy/client-api-requests.yaml ; \
sleep 15 ; \
kubectl get pods -n tgr
