import telegram
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
from imgurpython import ImgurClient
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

bot = telegram.Bot(token=(config['TELEGRAM']['ACCESS_TOKEN']))

# mongo atlas URL
myMongoClient = MongoClient(config['MONGODB']['URL'])
myMongoDb = myMongoClient["smart-data-center"]

# 攝影功能
dbCameraControl = myMongoDb['cameraControl']
dbCameraCreate = myMongoDb['cameraCreate']
dbArchiveRequest = myMongoDb['archiveRequest']

# imgur 圖床設置
client_id = 'b0ab73e0ddc8fc4'
client_secret = 'ed9354c61ef5dd4f14639e86d533f58d7ba3d7e9'
client = ImgurClient(client_id, client_secret)

# 錄影請求等候清單
schedule_camera = []

def main():
    # 客戶端新增攝像機請求
    def func_CameraCreate():
        print("=====CameraCreate=====")
        create_page = dbCameraCreate.find_one()
        if create_page["status"] == "1":
            # 使用 socket 套件進行 IP + Port 連通測試
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((create_page["ip"], int(create_page["port"])))
            sock.close()
            if result == 0:
                respText = "攝像機新增完成～"
                # 新增攝像機資料, 編號自動遞增
                count_list = len([i for i in dbCameraControl.find()])
                dbCameraControl.update_one({"device_number":str(count_list+1)}, {"$set":{"status":"0", "device_name":create_page["name"], "device_location":create_page["location"], "device_ip":create_page["ip"], "device_port":create_page["port"], "pin_code":create_page["pin_code"], "video_second":"", "chat_id":"", "connection":"0"}}, upsert=True)
            else:
                respText = "該位址無法連通, 請修正後重新嘗試～"
            print(respText)
            # 測試結果回傳給使用者
            bot.send_message(chat_id=create_page["chat_id"], text=respText, parse_mode="Markdown")
            # 使用者請求清空
            dbCameraCreate.update_one({"feature":"datapost"}, {"$set":{"status":"0", "name":"", "location":"", "ip":"", "port":"", "pin_code":"", "chat_id":""}}, upsert=True)
    # 客戶端使用攝像機請求
    def func_CameraControl():
        print("=====CameraControl=====")
        all_camera = dbCameraControl.find()
        global schedule
        for camera in all_camera:
            if camera["status"] == "1" or camera["status"] == "2":
                print("-----" + camera["device_name"] + "-----")
                # 攝像機連線檢查
                # 使用 socket 套件進行 IP + Port 連通測試
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex((camera["device_ip"], int(camera["device_port"])))
                sock.close()
                if result == 0:
                    url = 'rtsp://admin:' + camera["pin_code"] + '@' + camera["device_ip"] + ':' + camera["device_port"] + '/live/profile.0'
                    # 拍照功能
                    if camera["status"] == "1":
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
                        bot.send_message(chat_id=camera["chat_id"], text=respText, parse_mode="Markdown")
                        # 使用者請求清空
                        dbCameraControl.update_one({"device_number":camera["device_number"]}, {"$set":{"status":"0", "video_second":"", "chat_id":"", "connection":"0"}}, upsert=True)
                    # 攝影功能
                    elif camera["status"] == "2":
                        def video_job(chat_id, device_number, video_second, url):
                            # 導入攝像機
                            cap = cv2.VideoCapture(url)
                            # 使用者請求清空
                            dbCameraControl.update_one({"device_number":device_number}, {"$set":{"status":"0", "video_second":"", "chat_id":"", "connection":"0"}}, upsert=True)
                            # 使用 mp4v 編碼
                            recordForucc = cv2.VideoWriter_fourcc(*"XVID")
                            # 取得攝影機 fps 設定值
                            recordFPS = int(cap.get(cv2.CAP_PROP_FPS))
                            # 取得影像的解析度大小
                            recordWidth = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            recordHeight = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                            # 影像檔命名為當前時間
                            nowtime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            filename = str(nowtime) + ".avi"
                            # 建立 VideoWriter 物件，輸出影片至 $(datetime).avi
                            out = cv2.VideoWriter(filename, recordForucc, recordFPS/2, (recordWidth, recordHeight))
                            # 時間換算, 對比約為 1:15
                            cnt = 1
                            if video_second == "15":
                                timer = 225
                            elif video_second == "30":
                                timer = 450
                            elif video_second == "60":
                                timer = 900
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
                        if camera["device_number"] in schedule_camera:
                            respText = "這台攝像機正在忙碌中, 請稍後～"
                            bot.send_message(chat_id=camera["chat_id"], text=respText, parse_mode="Markdown")
                            # 使用者請求清空
                            dbCameraControl.update_one({"device_number":camera["device_number"]}, {"$set":{"status":"0", "video_second":"", "chat_id":""}}, upsert=True)
                        else:
                            # 請求存入清單
                            schedule_camera.append(camera["device_number"])
                            # 平行處理
                            _thread.start_new_thread(video_job, (camera["chat_id"], camera["device_number"], camera["video_second"], url))
                else:
                    respText = "該位址無法連通, 請修正後重新嘗試～"
                    # 使用者請求清空, 連線狀態更改為異常(1)
                    dbCameraControl.update_one({"device_number":camera["device_number"]}, {"$set":{"status":"0", "video_second":"", "chat_id":"", "connection":"1"}}, upsert=True)
                    bot.send_message(chat_id=camera["chat_id"], text=respText, parse_mode="Markdown")
    # 客戶端調取影片檔請求
    def func_ArchiveRequest():
        print("=====ArchiveRequest=====")
        requests = dbArchiveRequest.find()
        for request in requests:
            if request["status"] == "1":
                print("-----" + request["device_number"] + "-----")
                # 分割影片日期與時間
                archive_date = request["archive_date"].split(":")[0]
                archive_hour = request["archive_date"].split(":")[1]
                # 透過使用者請求的日期特定掛載的網路硬碟資料夾內容
                all_video_list = os.listdir("//mnt/telegram/2706_" + request["device_number"] + "/" + archive_date)
                # 設定暫存清單
                video_list = []
                show_list = []
                # 迴圈掃描所有資料夾內的影片檔
                for video_file in all_video_list:
                    # 如果檔名符合使用者請求的時間
                    if archive_hour == video_file.split("-")[2][0:2]:
                        # 檢查影片檔的大小是否符合Telegram bot Api的傳輸限制(最大不可超過50MB)
                        file_size = os.path.getsize("//mnt/telegram/2706_" + request["device_number"] + "/" + archive_date + "/" + video_file)
                        # 如果影片檔小於50MB將檔名加入video_list, 顯示在按鈕上的名稱則另外存入show_list
                        if file_size < 50000000:
                            video_list.append(video_file.split("-")[2])
                            # 名稱字串每兩個數插入時間單位(先將字串轉成陣列, 然後使用list.insert插入字元, 最後再將陣列轉回字串)
                            str_list = list(video_file.split("-")[2])
                            str_list.insert(2, "點")
                            str_list.insert(5, "分")
                            str_list.insert(8, "秒")
                            show_name = ''.join(str_list)
                            show_list.append(show_name)
                # 如果選擇清單不為空
                if len(video_list) != 0:
                    respText = "請選擇影片存檔～"
                    # 傳送選擇清單給使用者
                    bot.send_message(chat_id=request["chat_id"], text=respText, reply_markup = InlineKeyboardMarkup([
                        [InlineKeyboardButton(show_name, callback_data = "archive_check:" +  request["device_number"] + ":" + request["archive_date"] + ":" + video_name + ":" + str(request["chat_id"]))] for video_name, show_name in zip(video_list, show_list)
                    ]), parse_mode="Markdown")
                # 如果選擇清單為空
                else:
                    respText = "該時段沒有存檔～"
                    # 傳送提示文字給使用者
                    bot.send_message(chat_id=request["chat_id"], text=respText, parse_mode="Markdown")
                # 使用者請求清空
                dbArchiveRequest.update_one({"chat_id":request["chat_id"]}, {"$set":{"status":"0"}}, upsert=True)
            elif request["status"] == "2":
                def archive_job(chat_id, video_path):
                    # 回傳錄像給使用者
                    try:
                        bot.send_video(chat_id=chat_id, video=open(video_path, 'rb'))
                    # 回傳失敗時發送錯誤訊息
                    except:
                        respText = "該存檔無法傳送, 請選擇其他時段～"
                        bot.send_message(chat_id=chat_id, text=respText, parse_mode="Markdown")
                print("-----" + request["device_number"] + "-----")
                # 分隔使用者請求的錄影日期(如20200202AM)
                archive_date = request["archive_date"].split(":")[0]
                # 特定使用者請求的攝像機與錄影日期資料夾
                all_video_list = os.listdir("//mnt/telegram/2706_" + request["device_number"] + "/" + archive_date)
                # 搜尋資料夾內符合使用者請求的檔名
                for video_file in all_video_list:
                    if request["video_name"] == video_file.split("-")[2]:
                        file_name = video_file
                # 將找到的檔名和上層路徑組合成檔案的絕對路徑
                video_path = "//mnt/telegram/2706_" + request["device_number"] + "/" + archive_date + "/" + file_name
                # 平行處理
                _thread.start_new_thread(archive_job, (request["chat_id"], video_path))
                # 使用者請求清空
                dbArchiveRequest.update_one({"chat_id":request["chat_id"]}, {"$set":{"status":"0", "device_number":"", "archive_date":"", "video_name":""}}, upsert=True)
    func_CameraCreate()
    func_CameraControl()
    func_ArchiveRequest()
main()

# 定時檢測, 每隔 10 秒執行 一次
schedule.every(10).seconds.do(main)

while True:
    schedule.run_pending()  
    time.sleep(1) 
