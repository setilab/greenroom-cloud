import os
import time
import redis

# Redis
RHOST   =     os.getenv("REDIS_SERVICE_HOST", "redis.tgr.svc.cluster.local")
RPORT   = int(os.getenv("REDIS_SERVICE_PORT", "6379"))

try:
    ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
except:
    print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
    exit()

ds.config_set('notify-keyspace-events', 'KEA')

keyNs = "controller.requests."

def event_handler(msg):
    ns,key = msg["data"].rsplit(".", 1)

    if ns == keyNs + "job":
        print("Removing stale job id ", key)
        ds.srem(keyNs + "jobs", key)


pubsub = ds.pubsub()
pubsub.psubscribe(**{'__keyevent@0__:expired': event_handler})
thread = pubsub.run_in_thread(sleep_time=0.01)
