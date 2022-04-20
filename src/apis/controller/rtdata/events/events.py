import os
import datetime
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

qdConnectStr = "host=" + PGHOST + " port=" + PGPORT + " dbname=" + PGDBNAME + " user=" + PGUSER + " password=" + PGPWD

try:
    ds = redis.Redis(host=RHOST, port=RPORT, db=0, decode_responses=True)
except:
    print("ERROR: Unable to connect to Redis service at: {}:{}".format(RHOST, RPORT))
    exit()

ds.config_set('notify-keyspace-events', 'KEA')


def hset_event_handler(msg):
    keyNs = "controller.rtdata."

    nsk,controllerId = msg["data"].rsplit(".", 1)

    if nsk == keyNs + "relay.modes":
        relayModes = ds.hgetall(msg["data"])

        ts = relayModes["timeStamp"]
        dt = datetime.datetime.fromisoformat(ts)
        if dt.minute % 5 == 0 and dt.second == 0:

            key = keyNs + "sensor." + controllerId
            if ds.exists(key):
                sensorData = ds.hgetall(key)
            else:
                print("Missing data store key: {}".format(key))
                return

            key = keyNs + "relay.names." + controllerId
            if ds.exists(key):
                relayNames = ds.hgetall(key)
            else:
                print("Missing data store key: {}".format(key))
                return

            key = keyNs + "relay.states." + controllerId
            if ds.exists(key):
                relayStates = ds.hgetall(key)
            else:
                print("Missing data store key: {}".format(key))
                return

            key = "controller.account.id." + controllerId
            if ds.exists(key):
                accountId = ds.get(key)
            else:
                print("Missing data store key: {}".format(key))
                return

            key = "account.schema." + accountId
            if ds.exists(key):
                schema = ds.get(key)
            else:
                print("Missing data store key: {}".format(key))
                return

            key = "controller.grow.id." + controllerId
            if ds.exists(key):
                growid = ds.get(key)
            else:
                return

            timeStamp = sensorData["timeStamp"]
            tScale    = sensorData["tScale"]
            intTemp   = sensorData["intTemp"]
            intRH     = sensorData["intRH"]
            extTemp   = sensorData["extTemp"]
            extRH     = sensorData["extRH"]
            Co2       = sensorData["Co2"]
            Lux       = sensorData["Lux"]

            try:
                conn = psycopg.connect(qdConnectStr)
            except:
                print("ERROR: Unable to connect to QuestDB service at: {}".format(qdConnectStr))
                return

            cur = conn.cursor()

            cur.execute("INSERT INTO " + schema + "_grow_" + growid  + "_sensors " +
                        "(ts, tscale, intemp, inrh, extemp, exrh, exco2, exlux) " +
                        "VALUES " +
                        "(%s, %s, %s, %s, %s, %s, %s, %s)",
                        (timeStamp, tScale, intTemp, intRH, extTemp, extRH, Co2, Lux))

            relayNames.pop("timeStamp")
            for relay in relayNames:
                cur.execute("INSERT INTO " + schema + "_grow_" + growid  + "_relays " +
                            "(ts, relayid, name, state, mode) " +
                            "VALUES " +
                            "(%s, %s, %s, %s, %s)",
                            (timeStamp, relay, relayNames[relay], relayStates[relay],
                            relayModes[relay]))

            conn.commit()
            cur.close()
            conn.close()


def set_event_handler(msg):
    keyNs = "controller.account.id"

    nsk,controllerId = msg["data"].rsplit(".", 1)

    if nsk == keyNs:

        key = "controller.account.id." + controllerId
        if ds.exists(key):
            accountId = ds.get(key)
        else:
            print("Missing data store key: {}".format(key))
            return

        key = "account.schema." + accountId
        if ds.exists(key):
            schema = ds.get(key)
        else:
            print("Missing data store key: {}".format(key))
            return

        try:
            conn = psycopg.connect(qdConnectStr)
        except:
            print("ERROR: Unable to connect to QuestDB service at: {}".format(qdConnectStr))
            return

        cur = conn.cursor()

        cur.execute("CREATE TABLE " + schema + "_events_{}".format(controllerId.replace('-','_')) +
                    """(ts TIMESTAMP, evtype symbol, evsource symbol, event string)
                       timestamp(ts) PARTITION BY DAY""")

        conn.commit()
        cur.close()
        conn.close()


pubsub = ds.pubsub()
pubsub.psubscribe(**{'__keyevent@0__:hset': hset_event_handler})
pubsub.psubscribe(**{'__keyevent@0__:set': set_event_handler})
thread = pubsub.run_in_thread(sleep_time=0.01)
