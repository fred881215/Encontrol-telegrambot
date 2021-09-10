import telegram
from pymongo import MongoClient
import pyimgur
import configparser
import datetime
import time
import cv2
import os
import schedule
import _thread
import socket

config = configparser.ConfigParser()
config.read('config.ini')

# mongo atlas URL
myMongoClient = MongoClient(config['MONGODB']['URL'])
myMongoDb = myMongoClient["smart-data-center"]

# 攝影功能
dbCameraControl = myMongoDb['cameraControl']

# imgur 圖床設置
client_id = config['IMAGEPROCESS']['IMGUR_CLIENT_ID']
client_secret = config['IMAGEPROCESS']['IMGUR_CLIENT_SECRET']

# 讀取資料庫中存取的TelegramBot Token
dbTelegramBot_Token = myMongoDb['TelegramBot_Token']
TGToken = dbTelegramBot_Token.find_one()
bot = telegram.Bot(token=(TGToken["token"]))

# 錄影請求等候清單
schedule_camera = []

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
    # 客戶端使用攝像機請求
    def func_CameraControl():
        print("=====CameraControl=====")
        all_request = dbCameraControl.find()
        global schedule
        for request in all_request:
            if request["status"] == "intime_photo" or request["status"] == "intime_video":
                print("-----" + request["device_ip"] + "-----")
                result = socket_connection(request["device_ip"], int(request["device_port"]))
                if result == 0:
                    # 將欄位資料組合成 rtsp 協定格式的 url, 供 opencv 導入攝像機
                    url = f"rtsp://{request['account']}:{request['pin_code']}@{request['device_ip']}:{request['device_port']}{request['url']}"
                    # 拍照功能
                    if request["status"] == "intime_photo":
                        # 導入攝像機
                        cap = cv2.VideoCapture(url)
                        # 圖片名稱為當前時間 + .jpg(副檔名)
                        nowtime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        filename = str(nowtime) + ".jpg"
                        ret, frame = cap.read()
                        # 圖片暫存
                        cv2.imwrite(filename, frame)
                        # 攝像機記憶體空間釋放
                        cap.release()
                        # 圖片上傳至 imgur 後刪除本地存檔
                        im = pyimgur.Imgur(client_id)
                        uploaded_image = im.upload_image(filename, title="ImacPicture_" + str(nowtime))
                        os.remove(filename)
                        # 圖片網址回傳給使用者
                        respText = uploaded_image.link
                        bot.send_message(chat_id=request["chat_id"], text=respText, parse_mode="Markdown")
                        # 使用者請求清空
                        dbCameraControl.update_one({"device_number":request["device_number"]}, {"$set":{"status":"0", "video_second":"", "chat_id":"", "connection":"0"}}, upsert=True)
                    # 攝影功能
                    elif request["status"] == "intime_video":
                        def video_job(chat_id, device_number, video_second, url, recordFPS):
                            # 導入攝像機
                            cap = cv2.VideoCapture(url)
                            # 使用者請求清空
                            dbCameraControl.update_one({"device_number":device_number}, {"$set":{"status":"0", "video_second":"", "chat_id":"", "connection":"0"}}, upsert=True)
                            # 使用 xvid 編碼
                            recordForucc = cv2.VideoWriter_fourcc(*"XVID")
                            # 取得影像的解析度大小
                            recordWidth = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            recordHeight = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                            # 影像檔命名為當前時間
                            nowtime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            filename = str(nowtime) + ".avi"
                            # 建立 VideoWriter 物件，輸出影片至 $(datetime).avi
                            out = cv2.VideoWriter(filename, recordForucc, recordFPS, (recordWidth, recordHeight))
                            # 時間換算, 對比約為 公式 = $(recordFPS) * 實際秒數
                            cnt = 1
                            if video_second == "15":
                                timer = recordFPS*15
                            elif video_second == "30":
                                timer = recordFPS*30
                            elif video_second == "45":
                                timer = recordFPS*45
                            elif video_second == "60":
                                timer = recordFPS*60
                            # 迴圈錄影
                            while cnt < timer:
                                ret, frame = cap.read()
                                out.write(frame)
                                cnt += 1
                            # 回傳錄像給使用者
                            bot.send_video(chat_id=chat_id, video=open(filename, 'rb'), supports_streaming=True)
                            # 刪除等候隊列和影像存檔
                            if device_number in schedule_camera:
                                print("delete! number:" + device_number)
                                schedule_camera.remove(device_number)
                            os.remove(filename)
                            # 攝像機記憶體空間釋放
                            cap.release()
                            out.release()
                        # 檢查攝像機是否在行程中
                        if request["device_number"] in schedule_camera:
                            respText = "這台攝像機正在忙碌中, 請稍後～"
                            bot.send_message(chat_id=request["chat_id"], text=respText, parse_mode="Markdown")
                            # 使用者請求清空
                            dbCameraControl.update_one({"device_number":request["device_number"]}, {"$set":{"status":"0", "video_second":"", "chat_id":""}}, upsert=True)
                        else:
                            # 請求存入清單
                            schedule_camera.append(request["device_number"])
                            # 平行處理
                            _thread.start_new_thread(video_job, (request["chat_id"], request["device_number"], request["video_second"], url, int(request["fps"])))
                else:
                    respText = "該位址無法連通, 請修正後重新嘗試～"
                    # 使用者請求清空, 連線狀態更改為異常(1)
                    dbCameraControl.update_one({"device_number":request["device_number"]}, {"$set":{"status":"0", "video_second":"", "chat_id":"", "connection":"1"}}, upsert=True)
                    bot.send_message(chat_id=request["chat_id"], text=respText, parse_mode="Markdown")
    func_CameraControl()
main()

# 定時檢測, 每隔 5 秒執行 一次
schedule.every(5).seconds.do(main)

while True:
    schedule.run_pending()  
    time.sleep(1) 