../build/client.api.account.build ; \
kubectl delete deploy -n tgr client-api-account ; \
kubectl apply -f ../deploy/client-api-account.yaml ; \
sleep 15 ; \
kubectl get pods -n tgr
