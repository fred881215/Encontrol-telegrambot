import telegram
from pymongo import MongoClient
import configparser
import time
import schedule
import socket

config = configparser.ConfigParser()
config.read('config.ini')

# mongo atlas URL
myMongoClient = MongoClient(config['MONGODB']['URL'])
myMongoDb = myMongoClient["smart-data-center"]

# 攝影功能
dbCameraCreate = myMongoDb['cameraCreate']
dbCameraControl = myMongoDb['cameraControl']

# 讀取資料庫中存取的TelegramBot Token
dbTelegramBot_Token = myMongoDb['TelegramBot_Token']
TGToken = dbTelegramBot_Token.find_one()
bot = telegram.Bot(token=(TGToken["token"]))

# 攝像機位址連接測試
def socket_connection(device_ip, device_port):
    # 使用 socket 套件進行 IP + Port 連通測試
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 設定 3 秒逾時
    sock.settimeout(3)
    result = sock.connect_ex((device_ip, device_port))
    # 改回設定預防阻塞
    sock.settimeout(None)
    # 使用後關閉 socket 連接
    sock.close()
    # 回傳連接結果
    return result

def main():
    # 客戶端新增攝像機請求
    def func_CameraCreate():
        print("=====CameraCreate=====")
        request = dbCameraCreate.find_one()
        if request["status"] == "1":
            result = socket_connection(request["ip"], int(request["port"]))
            print(result)
            if result == 0: 
                respText = "攝像機新增完成～"
                # 新增攝像機資料, 編號自動遞增
                count_list = len([i for i in dbCameraControl.find()])
                dbCameraControl.update_one({"device_number":str(count_list+1)}, {"$set":{"status":"0", "device_name":request["name"], "device_location":request["location"], "device_ip":request["ip"], "device_port":request["port"], "account":request["account"], "pin_code":request["pin_code"], "url":request["url"], "fps":request["fps"], "video_second":"", "chat_id":"", "connection":"0"}}, upsert=True)
            else:
                respText = "該位址無法連通, 請修正後重新嘗試～"
            # 測試結果回傳給使用者
            bot.send_message(chat_id=request["chat_id"], text=respText, parse_mode="Markdown")
            # 使用者請求清空
            dbCameraCreate.update_one({"feature":"datapost"}, {"$set":{"status":"0", "name":"", "location":"", "ip":"", "port":"", "account":"", "pin_code":"", "url":"", "chat_id":""}}, upsert=True)
    func_CameraCreate()
main()

# 定時檢測, 每隔 5 秒執行 一次
schedule.every(5).seconds.do(main)

while True:
    schedule.run_pending()  
    time.sleep(1) 