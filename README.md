The Greenroom Cloud Services Platform

This repo contains ~~ sample ~~ code from a management platform for automated greenroom or greenhouse IoT controllers.

The cloud services platform provides capabilities for managing one or more IoT controllers. All services modelled and supported by the platform are required to be both cloud-native, as well as cloud-agnostic, essentially meaning Kubernetes provides the container orchestration/runtime environment.

For information about the related IoT controller device, visit the https://github.com/setilab/TGR-A8D4-R3.git repo.

Several services, such as Redis key store, require persistent datastores. This can be done numerous ways depeding on your back-end infrsatructure supporting Kubernetes. This example uses NFS, and it must be correctly configured & deployed into the desired namespace prior to deploying anything else on top.

To deploy one of these services, first deploy a namespace using the ns.yaml manifest located in the deploy folder:

> $ kubectl create -f ./deploy/ns.yaml

Next, configure the NFS provider contained within the ./deploy/nfs-client folder by following the included instructions.

Then, execute the desired service's pipeline contained in the pipeline folder:

> $ ./pipelines/client.api.controllers.pl

To deploy all of the services, first deploy a namespace as shown above, configure/deploy NFS provider, then execute the master pipeline:

> $ ./pipelines/master.pl

Other Tidbits

The "container" folder stores the Dockerfile and other resources needed when building the various container images.
The "build" folder contains the build scripts called from individual pipelines to actually build the container images.
The "deploy" folder contains the manifests which provide the declaritive configurations for each service.
The "src" folder contains the actual code that will be executed within its respective container image.

Some services require multiple container images for processing asynchronous events that are typically triggered by Redis key/value PUBSUB subscriptions.

Troubleshooting

Use normal Kubernetes techniques for analyzing various services.

For example to see the logs produced by a running container image use:

> $ kubectl logs -f -n <NAMESPACE> <POD_ID> {CONTAINER_ID} (if more than one container in the pod)

To shell into a running container:

> $ kubectl exec -it -n <NAMESPACE> <POD_ID> {CONTAINER_ID} -- /bin/bash

To peek inside of Redis, first shell into any running python-based container built with Redis python client module, then execute:

> api$ env | grep REDIS_SERVICE

*** Notate the values for both REDIS_SERVICE_HOST & REDIS_SERVICE_PORT ***

> api$ python
  
  >> import redis
  
  >> ks = redis.Redis(host="<REDIS_SERVICE_HOST>", port=<REDIS_SERVICE_PORT>, db=0, decode_responses=True)
  
  >> ks.keys("*") -- Lists all keys defined within the Redis DB #0
  
* See the Python module Redis.py docs for more information about available Redis commands supported by the module.

