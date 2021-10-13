from kubernetes import client, config as kubeconfig, utils
import telegram
from pymongo import MongoClient
import configparser
import time
import schedule
import socket
import os

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

# 連通K8s client
kubeconfig.load_incluster_config()
k8s_client = client.ApiClient()

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
                # count_list = len([i for i in dbCameraControl.find()])
                # dbCameraControl.update_one({"device_number":str(count_list+1)}, {"$set":{"status":"0", "device_name":request["name"], "device_location":request["location"], "device_ip":request["ip"], "device_port":request["port"], "account":request["account"], "pin_code":request["pin_code"], "url":request["url"], "fps":request["fps"], "storage_space":request["storage_space"], "nfs_dir":request["nfs_dir"], "video_second":"", "chat_id":"", "connection":"0"}}, upsert=True)
                # 設定串流Yaml檔名
                filename = "fetchcron.yaml"
                # 判斷Rtsp Url格式
                if request['account'] == "null" and request['pin_code'] == "null":
                    yaml_url = f"rtsp://{request['ip']}:{request['port']}{request['url']}"
                else:
                    yaml_url = f"rtsp://{request['account']}:{request['pin_code']}@{request['ip']}:{request['port']}{request['url']}"
                # nfs_dir 大寫轉小寫, Yaml 檔 metadata_name 欄位內容只可以包含小寫英文、數字、符號[-.]
                metadata_name = request["nfs_dir"].lower()
                # 讀取串流Yaml, 依照攝像機資料修改欄位內容
                with open(filename, "w+", encoding='utf8') as yaml:
                    yaml_data = f'apiVersion: batch/v1beta1\n\
kind: CronJob\n\
metadata:\n\
  name: cron-camera-{metadata_name}\n\
  namespace: default\n\
spec:\n\
  schedule: "*/5 * * * *"\n\
  jobTemplate:\n\
    spec:\n\
      template:\n\
        spec:\n\
          containers:\n\
          - name: thisiscontainername\n\
            image: vincent5753/capture\n\
            volumeMounts:\n\
            - name: nfs-volume\n\
              mountPath: //mnt/telegram\n\
            env:\n\
            - name: STOREPATH\n\
              value: "/mnt/telegram"\n\
            - name: NAME\n\
              value: "{request["nfs_dir"]}"\n\
            - name: URL\n\
              value: "{yaml_url}"\n\
            command: ["/bin/bash","-c"]\n\
            args: ["bash /var/capture/capture.sh $STOREPATH $NAME $URL"]\n\
          restartPolicy: OnFailure\n\
          volumes:\n\
          - name: nfs-volume\n\
            nfs:\n\
              server: 10.0.0.173\n\
              path: /var/nfsshare/volume1/surveillance'
                    yaml.write(yaml_data)
                    yaml.close()
                # 設定監控Yaml檔名
                filename = "deletecron.yaml"
                # 讀取監控Yaml, 依照攝像機資料修改欄位內容
                with open(filename, "w+", encoding='utf8') as yaml:
                    yaml_data = f'apiVersion: batch/v1beta1\n\
kind: CronJob\n\
metadata:\n\
  name: cron-delete-{metadata_name}\n\
  namespace: default\n\
spec:\n\
  schedule: "*/30 * * * *"\n\
  jobTemplate:\n\
    spec:\n\
      template:\n\
        spec:\n\
          containers:\n\
          - name: thisiscontainername\n\
            image: vincent5753/delete\n\
            volumeMounts:\n\
            - name: nfs-volume\n\
              mountPath: //mnt/telegram\n\
            env:\n\
            - name: STOREPATH\n\
              value: "/mnt/telegram"\n\
            - name: NAME\n\
              value: "{request["nfs_dir"]}"\n\
            - name: KSI\n\
              value: {request["storage_space"]}\n\
            command: ["/bin/bash","-c"]\n\
            args: ["bash /var/capture/delete.sh $STOREPATH $NAME $KSI"]\n\
          restartPolicy: OnFailure\n\
          volumes:\n\
          - name: nfs-volume\n\
            nfs:\n\
              server: 10.0.0.173\n\
              path: /var/nfsshare/volume1/surveillance'
                    yaml.write(yaml_data)
                    yaml.close()
                # 部署修改後的兩個Yaml檔
                filename = "fetchcron.yaml"
                os.system("kubectl apply -f " + filename)
                # utils.create_from_yaml(k8s_client, filename)
                filename = "deletecron.yaml"
                os.system("kubectl apply -f " + filename)
                # utils.create_from_yaml(k8s_client, filename)
            else:
                respText = "該位址無法連通, 請修正後重新嘗試～"
            # 測試結果回傳給使用者
            bot.send_message(chat_id=request["chat_id"], text=respText, parse_mode="Markdown")
            # 使用者請求清空
            dbCameraCreate.update_one({"feature":"datapost"}, {"$set":{"status":"0", "name":"", "location":"", "ip":"", "port":"", "account":"", "pin_code":"", "url":"", "fps":"", "storage_space":"", "nfs_dir":"", "chat_id":""}}, upsert=True)
    func_CameraCreate()
main()

# 定時檢測, 每隔 5 秒執行 一次
schedule.every(5).seconds.do(main)

while True:
    schedule.run_pending()  
    time.sleep(1) 
