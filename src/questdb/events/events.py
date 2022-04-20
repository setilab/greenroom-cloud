import os
from datetime import date,timedelta
import redis
import psycopg

# Redis
RHOST    =     os.getenv("REDIS_SERVICE_HOST", "redis.tgr.svc.cluster.local")
RPORT    = int(os.getenv("REDIS_SERVICE_PORT", "6379"))

# QuestDB
PGHOST   =     os.getenv("QUESTDB_QUERY_SERVICE_HOST", "questdb-query.tgr.svc.cluster.local")
PGPORT   =     os.getenv("QUESTDB_SERVICE_PORT_QUERY", "8812")
PGDBNAME =     os.getenv("QUESTDB_DBNAME", "qdb")
PGUSER   =     os.getenv("QUESTDB_USER", "admin")
PGPWD    =     os.getenv("QUESTDB_PASSWORD", "quest")

# Truncate events older than
RETENTION    = int(os.getenv("TGR_EVENT_RETENTION", "10"))

print("Starting service with {} day retention.".format(RETENTION))

qdConnectStr = "host=" + PGHOST + " port=" + PGPORT + " dbname=" + PGDBNAME + " user=" + PGUSER + " password=" + PGPWD

try:
    ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
except:
    print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
    exit()

ds.config_set('notify-keyspace-events', 'KEA')


def set_event_handler(msg):

    if msg["data"] == "set":
        try:
            conn = psycopg.connect(qdConnectStr)
        except:
            print("ERROR: Unable to connect to QuestDB service at: {}".format(qdConnectStr))
            return

        ts = ds.get("data.questdb.events.truncate")
        d,t = ts.split("T")
        pd = "{}".format(date.isoformat(date.fromisoformat(d) - timedelta(days=RETENTION)))

        cur = conn.cursor()

        cur.execute("tables()")

        result = cur.fetchall()

        i = 0
        for row in result:
            if row[1].count("_events_") == 1:
                cur.execute("ALTER TABLE {} ".format(row[1]) +
                            "DROP PARTITION LIST '{}'".format(pd))
                i = i + 1

        if i > 0:
            conn.commit()
            print("Truncated {} event tables with partitions dated {}.".format(i, pd))

        cur.close()
        conn.close()

        ds.delete("data.questdb.events.truncate")


pubsub = ds.pubsub()
pubsub.psubscribe(**{'__keyspace@0__:data.questdb.events.truncate': set_event_handler})
thread = pubsub.run_in_thread(sleep_time=0.01)
