import datetime
import requests
import time
import json

preDay = 0
sendReport = 0

while (True):
    timeJson = json.loads(datetime.datetime.strftime(datetime.datetime.now() + datetime.timedelta(hours=8), '{"day":\"%d\", "hour":\"%H\"}'))
    print(str(datetime.datetime.now() + datetime.timedelta(hours=8)))
    if (int(timeJson["hour"]) == 8 and sendReport == 0):
        sendReport = 1
        try: 
            r = requests.get("http://127.0.0.1:5000/dailyReport")
            print(r.text)
        except: 
            pass
        try: 
            r = requests.get("http://127.0.0.1:5000/serviceList")
            print(r.text)
        except: 
            pass
        try: 
            r = requests.get("http://127.0.0.1:5000/rotationUser/0")
            print(r.text)
        except: 
            pass
    if (int(timeJson["day"]) != preDay): 
        preDay = int(timeJson["day"])
        sendReport = 0
    try: 
        r = requests.get("http://127.0.0.1:5000/serviceCheck")
        print(r.text)
    except: 
        pass
    time.sleep(60)