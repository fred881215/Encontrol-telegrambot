from flask import Flask, request
from flask_api import status
import json
from pymongo import MongoClient
import datetime
import configparser
import MySQLdb
import requests
import time

# Load data from config.ini file
config = configparser.ConfigParser()
config.read('/home/ubuntu/IMAC_TelegramBot/config.ini')

# Initial Flask app
app = Flask(__name__)

# Setup mLab Mongodb info
# print(config['MONGODB']['SERVER_PROTOCOL'] + "://" + config['MONGODB']['USER'] + ":" + config['MONGODB']['PASSWORD'] + "@" + config['MONGODB']['SERVER'])
myMongoClient = MongoClient(config['MONGODB']['SERVER_PROTOCOL'] + "://" + config['MONGODB']['USER'] + ":" + config['MONGODB']['PASSWORD'] + "@" + config['MONGODB']['SERVER'])
myMongoDb = myMongoClient["smart-data-center"]
#myMongoDb.authenticate(config['MONGODB']['USER'], config['MONGODB']['PASSWORD'])

# Local Mysql Setup
mysqlIp = config['MYSQL']['SERVER_IP']
mysqlPort = config['MYSQL']['SERVER_PORT']
mysqlUser = config['MYSQL']['USER']
mysqlPass = config['MYSQL']['PASSWORD']
mysqlDb = config['MYSQL']['DATABASE']

# Cloud Server Setup
herokuServer = config['HEROKU']['SERVER']
herokuServerProtocol = config['HEROKU']['SERVER_PROTOCOL']

# Cloud mLab Setup
dbDl303TC = myMongoDb["dl303/tc"]
dbDl303RH = myMongoDb["dl303/rh"]
dbDl303CO2 = myMongoDb["dl303/co2"]
dbDl303DC = myMongoDb["dl303/dc"]
dbEt7044 = myMongoDb["et7044"]
dbUps = myMongoDb["ups"]
dbAirCondiction = myMongoDb["air_condiction"]
dbAirCondictionCurrent = myMongoDb["air_condiction_current"]
dbPowerBox = myMongoDb["power_box"]
dbDailyReport = myMongoDb["dailyReport"]
dbServiceCheck = myMongoDb["serviceCheck"]
dbServiceList = myMongoDb["serviceList"]
dbRotationUser = myMongoDb["rotationUser"]
dbWaterTank = myMongoDb['waterTank']
dbCameraPower = myMongoDb['cameraPower']

@app.route('/cameraPower', methods=['POST'])
def cameraPower_update():
    if request.method == 'POST':
        data = {}
        try:
            cameraPower = request.json
            cameraPower["cameraPower"]
        except:
            return {"cameraPower": "data-format-fail"}, status.HTTP_401_UNAUTHORIZED
        if (type(cameraPower.get("cameraPower")) not in [float]): return {"cameraPower": "data-type-fail"}, status.HTTP_401_UNAUTHORIZED
        if (dbCameraPower.find_one() == None):
            data["today"] = {}
            data["today"]["power"] = cameraPower["cameraPower"] 
            data["today"]["date"] = str(datetime.datetime.now())
            data["yesterday"] = {}
            data["yesterday"]["power"] = 0.0 
            data["yesterday"]["date"] = str(datetime.datetime.now())
            dbCameraPower.insert_one(data)
        else:
            data = dbCameraPower.find_one()
            del data["yesterday"]
            data["yesterday"] = data["today"]
            data["today"] = {}
            data["today"]["power"] = round(float(cameraPower["cameraPower"]), 2)
            data["today"]["date"] = str(datetime.datetime.now())
            dbCameraPower.update_one({}, {'$set': data})
        return {"cameraPower": "data_ok"}, status.HTTP_200_OK

@app.route('/rotationUser/<x>', methods=['GET', 'POST'])
def rotationUser(x):
    if request.method == 'GET':
        if (dbServiceList.find_one() != None):
            weekDay = 0
            if (int(datetime.date.today().month)%6 == 3): weekDay = 0
            elif (int(datetime.date.today().month)%6 == 4): weekDay = 1
            elif (int(datetime.date.today().month)%6 == 5): weekDay = 2
            elif (int(datetime.date.today().month)%6 == 6): weekDay = 3
            elif (int(datetime.date.today().month)%6 == 7): weekDay = 4
            elif (int(datetime.date.today().month)%6 == 8): weekDay = 5
            user = dbRotationUser.find_one()["rotation"][weekDay]['user']
            dbRotationUser.update_one({},{'$set':{"rotation." + str(6) + ".user": user}})
        try:
            requests.get(herokuServerProtocol + "://" + herokuServer + "/rotationUser")
        except:
            pass
        return {"rotationUser": "get-success"}, status.HTTP_200_OK

    if request.method == 'POST':
        if (int(x) < 1 and int(x) > 7): return {"rotationUser": "weekDay-fail"}, status.HTTP_401_UNAUTHORIZED
        try:
            userList = request.json
            userList["user"]
        except:
            return {"rotationUser": "data-format-fail"}, status.HTTP_401_UNAUTHORIZED
        if (type(userList.get("user")) not in [list]): return {"rotationUser": "data-type-fail"}, status.HTTP_401_UNAUTHORIZED
        if (dbServiceList.find_one() == None): 
                data = {}
                data["rotation"] = []
                for y in range(1, 8):
                    weekDay = ""
                    if (y == 1): weekDay = "一"
                    elif (y == 2): weekDay = "二"
                    elif (y == 3): weekDay = "三"
                    elif (y == 4): weekDay = "四"
                    elif (y == 5): weekDay = "五"
                    elif (y == 6): weekDay = "六"
                    else: weekDay = "日"
                    data["rotation"].append({})
                    data["rotation"][int(y)-1]["user"] = []
                    if (int(x)-1 == y):
                        for z in range(0, len(userList["user"])):
                            data["rotation"][int(y)-1]["user"].append(userList["user"][z])
                    else:
                        data["rotation"][int(y)-1]["user"].append("星期" + weekDay +  "_人員_0")
                        data["rotation"][int(y)-1]["user"].append("星期" + weekDay + "_人員_1")
                print(str(data).replace("\'", "\""))
                dbRotationUser.insert_one(data)
                del data["_id"]
        else: 
            dbRotationUser.update_one({},{'$set':{"rotation." + str(int(x)-1) + ".user": userList["user"]}})
            data = dbRotationUser.find_one()
            del data["_id"]
    
        return {"rotationUser": "success", "data": data}, status.HTTP_200_OK

@app.route('/serviceList', methods=['GET'])
def serviceList():
    if request.method == 'GET':
        updateService = 0
        data = {}
        data["error"] = []
        data["date"] = str(datetime.datetime.now())

        try:
            data["service"] = json.loads(requests.get("http://10.0.0.140:30010/").text)["res"]
        except:
            updateService = 1
            data["error"].append("輪播 Dashboard")

        if (not updateService):
            for x in range(len(data["service"])-1, -1, -1):
                if data["service"][x]["enabled"] == False:
                    data["service"].pop(x)
                # try:
                #     if (data["service"][x]["name"] != "Kubernetes Dashboard"): r = requests.get(data["service"][x]["url"])
                #     else: r = requests.get(data["service"][x]["url"], verify=False)
                #     if (r.status_code == 200): 
                #         data["service"][x]["status"] = "正常"
                #     else: 
                #         data["service"][x]["name"]["status"] = "異常"
                #         data["error"].append(data["service"][x]["name"])
                # except:
                #     data["service"][x]["status"] = "異常"
                #     if (data["service"][x]["enabled"] == True): data["error"].append(data["service"][x]["name"])
                elif (data["service"][x].get("notice") != None):
                    if (data["service"][x]["notice"].find("帳") >= 0 and data["service"][x]["notice"].find("密") >= 0):
                        data["service"][x]["user"] = data["service"][x]["notice"].split("帳")[1].split(" ")[0]
                        data["service"][x]["pass"] = data["service"][x]["notice"].split("密")[1]
                    del data["service"][x]["notice"]

        if (dbServiceList.find_one() == None): 
            dbServiceList.insert_one(data)
            del data["_id"]
        else: 
            dbServiceList.update_one({},{'$set':data})

        return {"serviceList": str(data["date"]).split(".")[0] + "-success", "data": data}, status.HTTP_200_OK


@app.route('/serviceCheck', methods=['GET'])
def serviceCheck():
    if request.method == 'GET':
        updateService = 0
        data = {}
        data["error"] = []
        data["date"] = str(datetime.datetime.now())

        try:
            data["service"] = json.loads(requests.get("http://10.0.0.140:30010/").text)["res"]
        except:
            updateService = 1
            data["error"].append("輪播 Dashboard")

        if (not updateService):
            for x in range(0, len(data["service"])):
                try:
                    if (data["service"][x]["name"] != "Kubernetes Dashboard"): r = requests.get(data["service"][x]["url"])
                    else: r = requests.get(data["service"][x]["url"], verify=False)
                    if (r.status_code == 200): 
                        data["service"][x]["status"] = "正常"
                    else: 
                        data["service"][x]["name"]["status"] = "異常"
                        if (data["service"][x]["enabled"] == True): data["error"].append(data["service"][x]["name"])
                except:
                    data["service"][x]["status"] = "異常"
                    data["error"].append(data["service"][x]["name"])

                if (data["service"][x].get("notice") != None): del data["service"][x]["notice"]

        if (dbServiceCheck.find_one() == None): 
            dbServiceCheck.insert_one(data)
            del data["_id"]
        else: 
            dbServiceCheck.update_one({},{'$set':data})

        if (data["date"] >= data["date"].split(" ")[0] + " 12:00:00" and data["date"] <= data["date"].split(" ")[0] + " 12:00:59"):
            try:
                requests.get(herokuServerProtocol + "://" + herokuServer + "/serviceCheck")
            except:
                pass

        return {"serviceCheck": str(data["date"]).split(".")[0] + "-success", "data": data}, status.HTTP_200_OK

    
@app.route('/dailyReport', methods=['GET'])
def daily_report():
    if request.method == 'GET':
        data = {}
        sendTelegram = 0
        yesterdayDate = str(datetime.datetime.now() + datetime.timedelta(days=-2, hours=8)).split(" ")[0]
        todayDate = str(datetime.datetime.now() + datetime.timedelta(days=-1, hours=8)).split(" ")[0]
        data["date"] = str(datetime.datetime.now() + datetime.timedelta(hours=8)).split(" ")[0]
        data["error"] = []
        defaultUrl = "https://opendata.cwb.gov.tw/api/v1/rest/datastore/F-D0047-073"
        apiToken = "CWB-011FFC7B-436E-4268-ABCA-998FBD6AD424"
        locationName = "%E5%8C%97%E5%8D%80"
        timeStamp_a = "T06%3A00%3A00"
        timeStamp_b = "T09%3A00%3A00"
        timeStamp_c = "T12%3A00%3A00"

        try:
            mysql_conn = MySQLdb.connect(host=mysqlIp, \
                port=int(mysqlPort), \
                user=mysqlUser, \
                passwd=mysqlPass, \
                db=mysqlDb)
            mysql_connection = mysql_conn.cursor()
        except:
            data["error"].append('power')

        print("select AVG(Output_Watt)*24+(220.0*1.0*24/1000) from UPS_A where Time_Stamp between \"" + yesterdayDate + " 16:00:00\" and \"" + todayDate + " 16:00:00\";")
        try:
            mysql_connection.execute("select AVG(Output_Watt)*24+(220.0*1.5*24/1000) from UPS_A where Time_Stamp between \"" + yesterdayDate + " 16:00:00\" and \"" + todayDate + " 16:00:00\";")
            data["ups_a"] = round(float(mysql_connection.fetchone()[0]), 4)
        except:
            data["ups_a"] = 0.01
            data["error"].append('ups_a')
        
        print("select AVG(Output_Watt)*24+(220.0*1.0*24/1000) from UPS_B where Time_Stamp between \"" + yesterdayDate + " 16:00:00\" and \"" + todayDate + " 16:00:00\";")
        try:
            mysql_connection.execute("select AVG(Output_Watt)*24+(220.0*2.0*24/1000) from UPS_B where Time_Stamp between \"" + yesterdayDate + " 16:00:00\" and \"" + todayDate + " 16:00:00\";")
            data["ups_b"] = round(float(mysql_connection.fetchone()[0]), 4)
        except:
            data["ups_b"] = 0.01
            data["error"].append('ups_b')

        print("select AVG(Current_A)*220*12*1.732/1000 from Power_Meter where Current_A > 0 and Time_Stamp between \"" + yesterdayDate + " 16:00:00\" and \"" + todayDate + " 16:00:00\";")
        try:
            mysql_connection.execute("select AVG(Current_A)*220*24*1.732/1000 from Power_Meter where Time_Stamp between \"" + yesterdayDate + " 16:00:00\" and \"" + todayDate + " 16:00:00\";")
            data["air_condiction_a"] = round(float(mysql_connection.fetchone()[0]), 4)
        except:
            data["air_condiction_a"] = 0.01
            data["error"].append('air_condiction_a')

        print("select AVG(Current_B)*220*12*1.732/1000 from Power_Meter where Current_B > 0 and Time_Stamp between \"" + yesterdayDate + " 16:00:00\" and \"" + todayDate + " 16:00:00\";")
        try:
            mysql_connection.execute("select AVG(Current_B)*220*24*1.732/1000 from Power_Meter where Time_Stamp between \"" + yesterdayDate + " 16:00:00\" and \"" + todayDate + " 16:00:00\";")
            data["air_condiction_b"] = round(float(mysql_connection.fetchone()[0]), 4)
        except:
            data["air_condiction_b"] = 0.01
            data["error"].append('air_condiction_b')
        
        print("select AVG(Current)*220*24*1.732/1000 from Water_Tank where Time_Stamp between \"" + yesterdayDate + " 16:00:00\" and \"" + todayDate + " 16:00:00\";")
        try:
            mysql_connection.execute("select AVG(Current)*220*24*1.732/1000 from Water_Tank where Time_Stamp between \"" + yesterdayDate + " 16:00:00\" and \"" + todayDate + " 16:00:00\";")
            data["water_tank"] = round(float(mysql_connection.fetchone()[0]), 4)
        except:
            data["water_tank"] = 0.01
            data["error"].append('water_tank')

        data["total"] = round(float(data["air_condiction_a"] + data["air_condiction_b"] + data["ups_a"] + data["ups_b"] + data["water_tank"]), 4)
    
        try:
            requestUrl = defaultUrl + "?Authorization=" + apiToken + "&locationName=" + locationName + "&startTime=" + data["date"] + timeStamp_a + "," + data["date"] + timeStamp_b + "," + data["date"] + timeStamp_c + "&dataTime=" + data["date"] + timeStamp_b
            weatherJson = json.loads(requests.get(requestUrl, headers = {'accept': 'application/json'}).text)
            for x in range(0, len(weatherJson["records"]["locations"][0]["location"][0]["weatherElement"])):
                module = weatherJson["records"]["locations"][0]["location"][0]["weatherElement"][x]["elementName"]
                if (module == "CI"):
                    value = weatherJson["records"]["locations"][0]["location"][0]["weatherElement"][x]["time"][0]["elementValue"][1]["value"]
                else:
                    value = weatherJson["records"]["locations"][0]["location"][0]["weatherElement"][x]["time"][0]["elementValue"][0]["value"]
                if (not (module in ["WeatherDescription", "WD", "Wx", "CI"])): value = int(value) 
                data[module] = value
        except:
            data["error"].append('weather')
        # print(str(data).replace("\'", "\""))

        if (dbDailyReport.find_one() == None):
            dbDailyReport.insert_one(data)
            del data["_id"]
            sendTelegram = 1
        else: 
            if (dbDailyReport.find_one()["date"] != data["date"]):
                dbDailyReport.update_one({},{'$set':data})
                sendTelegram = 1
                
        if (sendTelegram == 1):
            time.sleep(5)
            try:
                requests.get(herokuServerProtocol + "://" + herokuServer + "/dailyReport")
            except:
                pass

        return {"dailyReport": str(data["date"]).split(".")[0] + "-success", "data": data}, status.HTTP_200_OK

@app.route('/power_box', methods=['POST'])
def power_box_update():
    if request.method == 'POST':
        data = request.json
        try:
            data["humi"]
            data["temp"]
        except:
            return {"power_box": "data_fail"}, status.HTTP_401_UNAUTHORIZED
        if (dbPowerBox.find_one() == None): dbPowerBox.insert_one(data)
        else: dbPowerBox.update_one({'humi': dbPowerBox.find_one()['humi']},{'$set':data})
        return {"power_box": "data_ok"}, status.HTTP_200_OK

@app.route('/water_tank', methods=['POST'])
def water_tank_update():
    if request.method == 'POST':
        try:
            data = request.json
            data['current']
            data["date"] = str(datetime.datetime.now())
            if (dbWaterTank.find_one() == None): dbWaterTank.insert_one(data)
            else: dbWaterTank.update_one({}, {'$set': data})
            return {"power_tank": "data_ok"}, status.HTTP_200_OK
        except:
            return {"power_tank": "data_format_fail"}, status.HTTP_401_UNAUTHORIZED 

@app.route('/air_condiction/<module>/<sequence>', methods=['POST'])
def air_condiction_update(module, sequence):
    if request.method == 'POST':
        if (not (module.lower() in ["environment", "current"])): return {"air-condiction": "api_module_fail"}, status.HTTP_401_UNAUTHORIZED 
        if (not (sequence.lower() in ["a", "b"])): return {"air-condiction": "api_sequence_fail"}, status.HTTP_401_UNAUTHORIZED
        try:
            data = request.json
            if (module == "environment"): 
                try:
                    data["humi"]
                    data["temp"]
                except:
                    return {"air-condiction-environment": "data_fail"}, status.HTTP_401_UNAUTHORIZED
            if (module == "current"):
                try:
                    data["current"]
                except:
                    return {"air-condiction-current": "data_fail"}, status.HTTP_401_UNAUTHORIZED
        except:
            return {"air-condiction": "data_format_fail"}, status.HTTP_401_UNAUTHORIZED
        data["sequence"] = sequence
        data["date"] = datetime.datetime.now()
        if (module == "environment"):
            if (dbAirCondiction.find({"sequence": sequence}).count() == 0): dbAirCondiction.insert_one(data)
            else: dbAirCondiction.update_one({"sequence": sequence},{'$set':data})
            return {"air-condiction-environment": "data_ok"}, status.HTTP_200_OK
        else:
            if (dbAirCondictionCurrent.find({"sequence": sequence}).count() == 0): dbAirCondictionCurrent.insert_one(data)
            else: dbAirCondictionCurrent.update_one({"sequence": sequence},{'$set':data})
            return {"air-condiction-current": "data_ok"}, status.HTTP_200_OK

@app.route('/ups/<sequence>', methods=['POST'])
def ups_update(sequence):
    if request.method == 'POST':
        if (not (sequence.lower() in ["a", "b"])): return {"ups": "api_sequence_fail"}, status.HTTP_401_UNAUTHORIZED
        try:
            data = request.json
            data["input"]["line"]
            data["input"]["freq"]
            data["input"]["volt"]
            data["output"]["mode"]
            data["output"]["line"]
            data["output"]["freq"]
            data["output"]["volt"]
            data["output"]["amp"]
            data["output"]["percent"]
            data["output"]["watt"]
            data["battery"]["status"]["health"]
            data["battery"]["status"]["status"]
            data["battery"]["status"]["chargeMode"]
            data["battery"]["status"]["volt"]
            data["temp"]
            data["battery"]["status"]["remainPercent"]
            data["battery"]["lastChange"]["year"]
            data["battery"]["lastChange"]["month"]
            data["battery"]["lastChange"]["day"]
            data["battery"]["nextChange"]["year"]
            data["battery"]["nextChange"]["month"]
            data["battery"]["nextChange"]["day"]
        except:
            return {"ups": "data_fail"}, status.HTTP_401_UNAUTHORIZED
        data["date"] = datetime.datetime.now()
        data["sequence"] = sequence
        if (dbUps.find({"sequence": sequence}).count() == 0): dbUps.insert_one(data)
        else: dbUps.update_one({'sequence': sequence},{'$set':data})
        return {"ups": "data_ok"}, status.HTTP_200_OK

@app.route('/et7044', methods=['POST', 'GET'])
def et7044_update():
    if request.method == 'POST':
        try:
            data = request.json
            if (not ((data['sw0'] in [True, False]) and (data['sw1'] in [True, False]) and (data['sw2'] in [True, False]) and (data['sw3'] in [True, False]) and (data['sw4'] in [True, False]) and (data['sw5'] in [True, False]) and (data['sw6'] in [True, False]) and (data['sw7'] in [True, False]))):
                return {"et7044": "data_info_fail"}, status.HTTP_401_UNAUTHORIZED
            data["date"] = datetime.datetime.now()
            if (dbEt7044.find_one() == None): dbEt7044.insert_one(data)
            else: dbEt7044.update_one({}, {'$set': data})
            return {"et7044": "data_ok"}, status.HTTP_200_OK
        except:
            return {"et7044": "data_fail"}, status.HTTP_401_UNAUTHORIZED
    else:
        data = dbEt7044.find_one()
        return {"sw0": data['sw0'], "sw1": data['sw1'], "sw2": data['sw2'], "sw3": data['sw3'], "sw4": data['sw4'], "sw5": data['sw5'], "sw6": data['sw6'], "sw7": data['sw7'], "date": datetime.datetime.now()}

@app.route('/dl303/<module>', methods=['POST'])
def dl303_update(module):
    if request.method == 'POST':
        if (not (module in ["tc", "rh", "co2", "dc"])): return {"dl303": "api_module_fail"}, status.HTTP_401_UNAUTHORIZED
        try: data = request.json
        except: return {"dl303": "data_fail"}, status.HTTP_401_UNAUTHORIZED
        if (module == 'tc'):
            try:
                data['tc']
                data["date"] = datetime.datetime.now()
                if (dbDl303TC.find_one() == None): dbDl303TC.insert_one(data)
                else: dbDl303TC.update_one({}, {'$set': data})
                return {"dl303": "tc_data_ok"}, status.HTTP_200_OK
            except:
                return {"dl303": "tc_data_info_fail"}, status.HTTP_401_UNAUTHORIZED
        elif (module == 'rh'):
            try:
                data['rh']
                data["date"] = datetime.datetime.now()
                if (dbDl303RH.find_one() == None): dbDl303RH.insert_one(data)
                else: dbDl303RH.update_one({}, {'$set': data})
                return {"dl303": "rh_data_ok"}, status.HTTP_200_OK
            except:
                return {"dl303": "rh_data_info_fail"}, status.HTTP_401_UNAUTHORIZED
        elif (module == 'co2'):
            try:
                data['co2']
                data["date"] = datetime.datetime.now()
                if (dbDl303CO2.find_one() == None): dbDl303CO2.insert_one(data)
                else: dbDl303CO2.update_one({}, {'$set': data})
                return {"dl303": "co2_data_ok"}, status.HTTP_200_OK
            except:
                return {"dl303": "co2_data_info_fail"}, status.HTTP_401_UNAUTHORIZED
        elif (module == 'dc'):
            try:
                data['dc']
                data["date"] = datetime.datetime.now()
                if (dbDl303DC.find_one() == None): dbDl303DC.insert_one(data)
                else: dbDl303DC.update_one({}, {'$set': data})
                return {"dl303": "dc_data_ok"}, status.HTTP_200_OK
            except:
                return {"dl303": "dc_data_info_fail"}, status.HTTP_401_UNAUTHORIZED

if __name__ == "__main__":
    # Running server
    app.run(host="0.0.0.0")