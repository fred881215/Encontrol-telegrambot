import paho.mqtt.client as mqtt
import requests
import datetime
import json

broker_ip = "10.20.0.19"
broker_port = 1883

http_server_protocol = "http"
#http_server_ip = "10.20.0.74"
http_server_ip = "127.0.0.1"
http_server_port = 5000

mLab_et7044_history = [True, False, False, False, False, False, False, False]

def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    
    client.subscribe("DL303/#")
    # client.subscribe("DL303/TC")
    # client.subscribe("DL303/CO2")
    # client.subscribe("DL303/RH")
    # client.subscribe("DL303/DC")
    client.subscribe("ET7044/DOstatus")
    client.subscribe("current")
    # client.subscribe("UPS_Monitor/#")
    # client.subscribe("UPS_Monitor")
    client.subscribe("UPS/A/Monitor")
    client.subscribe("UPS/B/Monitor")
    client.subscribe("air_condiction/#")
    client.subscribe("waterTank")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    sendData = {}
    data = str(msg.payload.decode('utf-8'))
    print(msg.topic+" "+ data)
    if (msg.topic in ["DL303/TC", "DL303/CO2", "DL303/RH", "DL303/DC"]):
        moduleName = msg.topic.lower().split("/")[1]
        try:
            sendData[moduleName] = data
            requests.post(http_server_protocol + "://" + http_server_ip + ":" + str(http_server_port) + "/dl303/" + moduleName, json=sendData)
        except:
            pass
    if (msg.topic == "ET7044/DOstatus"):
        mLab_change_status = False
        local_change_status = False
        data = data.split("[")[1].split("]")[0].split(",")
        for x in range(0, len(data)):
            sendData["sw" + str(x)] = data[x].lower() in ['true']
        mLab_et7044_status = json.loads(requests.get(http_server_protocol + "://" + http_server_ip + ":" + str(http_server_port) + "/et7044").text)
        for x in range(0, len(data)):
            if (mLab_et7044_history[x] != mLab_et7044_status["sw" + str(x)]): mLab_change_status = True
            if (mLab_et7044_history[x] != sendData["sw" + str(x)]): local_change_status = True
            mLab_et7044_history[x] = mLab_et7044_status["sw" + str(x)]
        print(local_change_status, mLab_change_status)
        if (mLab_change_status == False or (mLab_change_status == True and local_change_status == True)):
            print("mLab no change or renew data to mLab")
            try:
                requests.post(http_server_protocol + "://" + http_server_ip + ":" + str(http_server_port) + "/et7044", json=sendData)
            except:
                pass
        else:
            print("mLab change")
            client.publish("ET7044/write", str(mLab_et7044_history).lower())
        
    if (msg.topic == "current"):
        data = json.loads(data)
        air_condiction_a = {}
        air_condiction_b = {}
        power_box = {}
        air_condiction_a['current'] = data['current_a']
        air_condiction_b['current'] = data['current_b']
        power_box["temp"] = data["Temperature"]
        power_box["humi"] = data["Humidity"]
        try:
            requests.post(http_server_protocol + "://" + http_server_ip + ":" + str(http_server_port) + "/power_box", json=power_box)
            requests.post(http_server_protocol + "://" + http_server_ip + ":" + str(http_server_port) + "/air_condiction/current/a", json=air_condiction_a)
            requests.post(http_server_protocol + "://" + http_server_ip + ":" + str(http_server_port) + "/air_condiction/current/b", json=air_condiction_b)
        except:
            pass
    
    if (msg.topic in ["UPS/A/Monitor", "UPS/B/Monitor"]):
        try:
            moduleName = msg.topic.lower().split("/")[1]
            requests.post(http_server_protocol + "://" + http_server_ip + ":" + str(http_server_port) + "/ups/" + moduleName, json=json.loads(data.replace("'", '"')))
        except:
            pass
    
    if (msg.topic in ["air_condiction/A", "air_condiction/B"]):
        try:
            moduleName = msg.topic.lower().split("/")[1]
            requests.post(http_server_protocol + "://" + http_server_ip + ":" + str(http_server_port) + "/air_condiction/environment/" + moduleName, json=json.loads(data))
        except:
            pass

    if (msg.topic == "waterTank"):
        try:
            requests.post(http_server_protocol + "://" + http_server_ip + ":" + str(http_server_port) + "/water_tank", json=json.loads(data))
        except:
            pass

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(broker_ip, broker_port)
client.loop_forever()