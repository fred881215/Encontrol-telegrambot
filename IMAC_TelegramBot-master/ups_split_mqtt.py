import paho.mqtt.client as mqtt
import requests
import datetime
import json

broker_ip = "10.20.0.19"
broker_port = 1883

countA = 0
countB = 0
sendData = {}

def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    # client.subscribe("UPS_Monitor/#")
    client.subscribe("UPS/A/Monitor")
    client.subscribe("UPS/B/Monitor")


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global countA, countB, sendData
    data = str(msg.payload.decode('utf-8'))
    if (msg.topic == "UPS/A/Monitor"):
        print("A\t" + data)
        ups_a_data = json.loads(data)
        
        sendData["connect_A"] = "/dev/ttyUSB0 (牆壁)"
        sendData["ups_Life_A"] = "onLine(在線)"
        sendData["input_A"] = {}
        sendData["input_A"]["inputLine_A"] = str(ups_a_data["input"]["line"])
        sendData["input_A"]["inputFreq_A"] = str(ups_a_data["input"]["freq"])
        sendData["input_A"]["inputVolt_A"] = str(ups_a_data["input"]["volt"])
        sendData["output_A"] = {}
        sendData["output_A"]["systemMode_A"] = str(ups_a_data["output"]["mode"]).split(" ")[0]
        sendData["output_A"]["outputLine_A"] = str(ups_a_data["output"]["line"])
        sendData["output_A"]["outputFreq_A"] = str(ups_a_data["output"]["freq"])
        sendData["output_A"]["outputVolt_A"] = str(ups_a_data["output"]["volt"])
        sendData["output_A"]["outputAmp_A"] = str(ups_a_data["output"]["amp"])
        sendData["output_A"]["outputPercent_A"] = str(ups_a_data["output"]["percent"])
        sendData["output_A"]["outputWatt_A"] = str(ups_a_data["output"]["watt"])
        sendData["battery_A"] = {}
        sendData["battery_A"]["status"] = {}
        sendData["battery_A"]["lastChange"] = {}
        sendData["battery_A"]["nextChange"] = {}
        sendData["battery_A"]["status"]["batteryHealth_A"] = ups_a_data["battery"]["status"]["health"]
        sendData["battery_A"]["status"]["batteryStatus_A"] = ups_a_data["battery"]["status"]["status"]
        sendData["battery_A"]["status"]["batteryCharge_Mode_A"] = ups_a_data["battery"]["status"]["chargeMode"]
        sendData["battery_A"]["status"]["batteryVolt_A"] = str(ups_a_data["battery"]["status"]["volt"])
        sendData["battery_A"]["status"]["batteryTemp_A"] = str(ups_a_data["temp"])
        sendData["battery_A"]["status"]["batteryRemain_Percent_A"] = str(ups_a_data["battery"]["status"]["remainPercent"])
        sendData["battery_A"]["status"]["batteryRemain_Min_A"] = "None By Charging (充電中)"
        sendData["battery_A"]["status"]["batteryRemain_Sec_A"] = "None By Charging (充電中)"
        sendData["battery_A"]["lastChange"]["lastBattery_Year_A"] = str(ups_a_data["battery"]["lastChange"]["year"])
        sendData["battery_A"]["lastChange"]["lastBattery_Mon_A"] = str(ups_a_data["battery"]["lastChange"]["month"])
        sendData["battery_A"]["lastChange"]["lastBattery_Day_A"] = str(ups_a_data["battery"]["lastChange"]["day"])
        sendData["battery_A"]["nextChange"]["nextBattery_Year_A"] = str(ups_a_data["battery"]["nextChange"]["year"])
        sendData["battery_A"]["nextChange"]["nextBattery_Mon_A"] = str(ups_a_data["battery"]["nextChange"]["month"])
        sendData["battery_A"]["nextChange"]["nextBattery_Day_A"] = str(ups_a_data["battery"]["nextChange"]["day"])
        countA = 1
        
    if (msg.topic == "UPS/B/Monitor"):
        print("B\t" + data)
        ups_b_data = json.loads(data)

        sendData["connect_B"] = "/dev/ttyUSB1 (窗戶)"
        sendData["ups_Life_B"] = "onLine(在線)"
        sendData["input_B"] = {}
        sendData["input_B"]["inputLine_B"] = str(ups_b_data["input"]["line"])
        sendData["input_B"]["inputFreq_B"] = str(ups_b_data["input"]["freq"])
        sendData["input_B"]["inputVolt_B"] = str(ups_b_data["input"]["volt"])
        sendData["output_B"] = {}
        sendData["output_B"]["systemMode_B"] = str(ups_b_data["output"]["mode"]).split(" ")[0]
        sendData["output_B"]["outputLine_B"] = str(ups_b_data["output"]["line"])
        sendData["output_B"]["outputFreq_B"] = str(ups_b_data["output"]["freq"])
        sendData["output_B"]["outputVolt_B"] = str(ups_b_data["output"]["volt"])
        sendData["output_B"]["outputAmp_B"] = str(ups_b_data["output"]["amp"])
        sendData["output_B"]["outputPercent_B"] = str(ups_b_data["output"]["percent"])
        sendData["output_B"]["outputWatt_B"] = str(ups_b_data["output"]["watt"])
        sendData["battery_B"] = {}
        sendData["battery_B"]["status"] = {}
        sendData["battery_B"]["lastChange"] = {}
        sendData["battery_B"]["nextChange"] = {}
        sendData["battery_B"]["status"]["batteryHealth_B"] = ups_b_data["battery"]["status"]["health"]
        sendData["battery_B"]["status"]["batteryStatus_B"] = ups_b_data["battery"]["status"]["status"]
        sendData["battery_B"]["status"]["batteryCharge_Mode_B"] = ups_b_data["battery"]["status"]["chargeMode"]
        sendData["battery_B"]["status"]["batteryVolt_B"] = str(ups_b_data["battery"]["status"]["volt"])
        sendData["battery_B"]["status"]["batteryTemp_B"] = str(ups_b_data["temp"])
        sendData["battery_B"]["status"]["batteryRemain_Percent_B"] = str(ups_b_data["battery"]["status"]["remainPercent"])
        sendData["battery_B"]["status"]["batteryRemain_Min_B"] = "None By Charging (充電中)"
        sendData["battery_B"]["status"]["batteryRemain_Sec_B"] = "None By Charging (充電中)"
        sendData["battery_B"]["lastChange"]["lastBattery_Year_B"] = str(ups_b_data["battery"]["lastChange"]["year"])
        sendData["battery_B"]["lastChange"]["lastBattery_Mon_B"] = str(ups_b_data["battery"]["lastChange"]["month"])
        sendData["battery_B"]["lastChange"]["lastBattery_Day_B"] = str(ups_b_data["battery"]["lastChange"]["day"])
        sendData["battery_B"]["nextChange"]["nextBattery_Year_B"] = str(ups_b_data["battery"]["nextChange"]["year"])
        sendData["battery_B"]["nextChange"]["nextBattery_Mon_B"] = str(ups_b_data["battery"]["nextChange"]["month"])
        sendData["battery_B"]["nextChange"]["nextBattery_Day_B"] = str(ups_b_data["battery"]["nextChange"]["day"])
        countB = 1
        
    print(msg.topic+" "+ data + "\n")
    if (countA == 1 and countB == 1):
        countA = 0
        countB = 0
        print("send combine mqtt")
        print(str(sendData).replace('\'', "\""))
        client.publish("UPS_Monitor", str(sendData).replace('\'', "\""))
        sendData = {}

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(broker_ip, broker_port)
client.loop_forever()