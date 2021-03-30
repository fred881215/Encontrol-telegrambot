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
            # 如果資料表狀態值為請求月份(檢查月份是否存在存檔資料夾, 存在則標記綠色打勾顏文字)
            if request["status"] == "request_month":
                print("-----" + request["device_number"] + "-----")
                # 如果傳過來的年份是當前年份
                if request["archive_date"] == str(datetime.date.today()).split("-")[0]:
                    # 取當前最大月份
                    now_month = int(str(datetime.date.today()).split("-")[1])
                    # 將月份依序存入陣列
                    max_month = [month for month in range(1, now_month+1)]
                    # 如果月份數字不足四的倍數
                    if len(max_month) in [1, 5, 9]:
                        # 用空白字元補到四的倍數
                        for i in range(1, 3+1):
                            max_month.append(' ')
                    elif len(max_month) in [2, 6, 10]:
                        for i in range(1, 2+1):
                            max_month.append(' ')
                    elif len(max_month) in [3, 7, 11]:
                        max_month.append(' ')
                # 如果傳過來的年份不是當前年份
                else:
                    # 取最大月份(12)
                    max_month = [month for month in range(1, 12+1)]
                # 透過使用者請求的設備特定掛載的網路硬碟資料夾內容
                all_video_list = os.listdir("//mnt/telegram/2706_" + request["device_number"])
                # 宣告存放顏文字unicode的空列表
                unicode_emoji_list = []
                # 父迴圈, 從1開始遞增, 直到最大月份結束
                for i in range(1, len(max_month)+1):
                    # 如果月份字串長度等於1, 字元前面補0
                    if len(str(i)) == 1:
                        month_count = "0" + str(i)
                    # 否則維持原樣
                    else:
                        month_count = str(i)
                    # 子迴圈, 掃描資料夾內的子資料夾檔名
                    for video_file in all_video_list:
                        # 如果使用者選的年份+遞增的月份包含在資料夾名稱內
                        if request["archive_date"] + month_count in video_file:
                            # 增加綠色打勾圖案後跳出子迴圈, 繼續跑父迴圈
                            unicode_emoji_list.append("\U00002705")
                            break
                        # 如果子迴圈已經跑到列表的最後一個元素
                        elif video_file == all_video_list[-1]:
                            # 增加紅色打叉圖案後結束子迴圈, 繼續跑父迴圈
                            unicode_emoji_list.append("\U0000274C")
                # 回傳當前選取狀態文字提示
                respText = "請選擇影片存檔月份～"
                bot.send_message(chat_id=request["chat_id"], text=respText, reply_markup = InlineKeyboardMarkup([
                    [InlineKeyboardButton(unicode_emoji_list[i] + str(max_month[i]), callback_data = "archive_day:" + request["device_number"] + ":" + request["archive_date"] + ":" + str(max_month[i])),
                        InlineKeyboardButton(unicode_emoji_list[i+1] + str(max_month[i+1]), callback_data = "archive_day:" + request["device_number"] + ":" + request["archive_date"] + ":" + str(max_month[i+1])),
                        InlineKeyboardButton(unicode_emoji_list[i+2] + str(max_month[i+2]), callback_data = "archive_day:" + request["device_number"] + ":" + request["archive_date"] + ":" + str(max_month[i+2])),
                        InlineKeyboardButton(unicode_emoji_list[i+3] + str(max_month[i+3]), callback_data = "archive_day:" + request["device_number"] + ":" + request["archive_date"] + ":" + str(max_month[i+3]))] for i in range(0, len(max_month)) if i in [0, 4, 8]
                ]), parse_mode="Markdown")
                # 使用者請求清空
                dbArchiveRequest.update_one({"chat_id":request["chat_id"]}, {"$set":{"status":"0"}}, upsert=True)
            # 如果資料表狀態值為請求日期(檢查日期是否存在存檔資料夾, 存在則標記綠色打勾顏文字)
            elif request["status"] == "request_day":
                print("-----" + request["device_number"] + "-----")
                # 擷取 archive_date 欄位字串中的年份(如'2020'01)
                year = request["archive_date"][0:4]
                # 擷取 archive_date 欄位字串中的月份(如2020'01')
                month = request["archive_date"][4:6]
                # 如果月份為大
                if int(month) in [1,3,5,7,8,10,12]:
                    max_day = [day for day in range(1, 31+1)]
                    # 增加空值補齊日期按鈕
                    for i in range(1, 10):
                        max_day.append(' ')
                # 如果月份為小
                elif int(month) in [4,6,9,11]:
                    max_day = [day for day in range(1, 30+1)]
                    for i in range(1, 10):
                        max_day.append(' ')
                # 如果月份為二
                else:
                    # 如果為閏年
                    if int(year)%4 == 0:
                        max_day = [day for day in range(1, 29+1)]
                        for i in range(1, 10):
                            max_day.append(' ')
                    # 如果非閏年
                    else:
                        max_day = [day for day in range(1, 28+1)]
                # 透過使用者請求的設備特定掛載的網路硬碟資料夾內容
                all_video_list = os.listdir("//mnt/telegram/2706_" + request["device_number"])
                # 宣告存放顏文字unicode的空列表
                unicode_emoji_list = []
                # 宣告檢查資料夾是否存在的空布林值
                exist_check = None
                # 迴圈掃描主資料夾內的年月份資料夾
                for video_file in all_video_list:
                    # 如果使用者請求的年月份資料夾存在
                    if request["archive_date"] in video_file:
                        # 將結果保存
                        exist_check = True
                # 如果找不到該年月份資料夾, 回傳錯誤訊息
                if exist_check != True:
                    respText = "此月份沒有影片存檔～"
                    bot.send_message(chat_id=request["chat_id"], text=respText, parse_mode="Markdown")
                    return
                # 父迴圈, 從1開始遞增, 直到最大日期結束
                for i in range(1, len(max_day)+1):
                    # 如果日期字串長度等於1, 字元前面補0
                    if len(str(i)) == 1:
                        day_count = "0" + str(i)
                    # 否則維持原樣
                    else:
                        day_count = str(i)
                    # 子迴圈, 掃描資料夾內的子資料夾檔名
                    for video_file in all_video_list:
                        # 如果使用者選的年月份+遞增的日期包含在資料夾名稱內
                        if request["archive_date"] + day_count in video_file:
                            # 增加綠色打勾圖案後跳出子迴圈, 繼續跑父迴圈
                            unicode_emoji_list.append("\U00002705")
                            break
                        # 如果子迴圈已經跑到列表的最後一個元素
                        elif video_file == all_video_list[-1]:
                            # 增加紅色打叉圖案後結束子迴圈, 繼續跑父迴圈
                            unicode_emoji_list.append("\U0000274C")
                # 回傳當前選取狀態文字提示
                respText = "請選擇影片存檔日期～"
                bot.send_message(chat_id=request["chat_id"], text=respText, reply_markup = InlineKeyboardMarkup([
                    [InlineKeyboardButton(unicode_emoji_list[i] + str(max_day[i]), callback_data = "archive_hour:" + request["device_number"] + ":" + year + ":" + month + ":" + str(max_day[i])),
                        InlineKeyboardButton(unicode_emoji_list[i+1] + str(max_day[i+1]), callback_data = "archive_hour:" + request["device_number"] + ":" + year + ":" + month + ":" + str(max_day[i+1])),
                        InlineKeyboardButton(unicode_emoji_list[i+2] + str(max_day[i+2]), callback_data = "archive_hour:" + request["device_number"] + ":" + year + ":" + month + ":" + str(max_day[i+2])),
                        InlineKeyboardButton(unicode_emoji_list[i+3] + str(max_day[i+3]), callback_data = "archive_hour:" + request["device_number"] + ":" + year + ":" + month + ":" + str(max_day[i+3])),
                        InlineKeyboardButton(unicode_emoji_list[i+4] + str(max_day[i+4]), callback_data = "archive_hour:" + request["device_number"] + ":" + year + ":" + month + ":" + str(max_day[i+4])),
                        InlineKeyboardButton(unicode_emoji_list[i+5] + str(max_day[i+5]), callback_data = "archive_hour:" + request["device_number"] + ":" + year + ":" + month + ":" + str(max_day[i+5])),
                        InlineKeyboardButton(unicode_emoji_list[i+6] + str(max_day[i+6]), callback_data = "archive_hour:" + request["device_number"] + ":" + year + ":" + month + ":" + str(max_day[i+6]))] for i in range(0, len(max_day)) if i in [0, 7, 14, 21, 28]
                ]), parse_mode="Markdown")
                # 使用者請求清空
                dbArchiveRequest.update_one({"chat_id":request["chat_id"]}, {"$set":{"status":"0"}}, upsert=True)
            # 如果資料表狀態值為選擇檔案(列出時間內大小不超過50MB的影片存檔供使用者選擇)
            elif request["status"] == "select_file":
                print("-----" + request["device_number"] + "-----")
                # 分割影片日期與時間
                archive_date = request["archive_date"].split(":")[0]
                archive_hour = request["archive_date"].split(":")[1]
                try:
                    # 透過使用者請求的日期特定掛載的網路硬碟資料夾內容, 執行失敗代表資料夾不存在
                    all_video_list = os.listdir("//mnt/telegram/2706_" + request["device_number"] + "/" + archive_date)
                except:
                    respText = "該時段沒有存檔～"
                    # 傳送提示文字給使用者
                    bot.send_message(chat_id=request["chat_id"], text=respText, parse_mode="Markdown")
                else:
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
                                # 名稱字串每兩個數插入時間單位(先將字串轉成陣列, 然後使用list.insert插入字元, 最後再用join將陣列轉回字串)
                                str_list = list(video_file.split("-")[2])
                                str_list.insert(2, ":")
                                str_list.insert(5, ":")
                                show_name = ''.join(str_list)
                                # 依照名稱字串分開計算時分秒
                                end_hour = video_file.split("-")[2][0:2]
                                # 結束時間為起始時間(名稱字串3,4字元)的分鐘數加5
                                end_min = str(int(video_file.split("-")[2][2:4])+5)
                                end_sec = video_file.split("-")[2][4:6]
                                # 如果加總過後的分鐘數大於等於60
                                if int(end_min) >= 60:
                                    # 結束時間的小時數加1
                                    end_hour = str(int(end_hour)+1)
                                    # 結束時間的分鐘數減去60
                                    end_min = str(int(end_min)-60)
                                    # 如果加總過後的小時數字小於十位數且未補0
                                    if len(end_hour) == 1:
                                        # 在字元前面自動補上0
                                        end_hour = "0" + end_hour
                                # 如果加總過後的分鐘數小於十位數
                                if len(end_min) == 1:
                                    # 在字元前面自動補上0
                                    end_min = "0" + end_min
                                # 如果結束時間的小時數超過0~23的範圍
                                if int(end_hour) > 23:
                                    # 將小時數歸零(24轉00)
                                    end_hour = "00"
                                # 按鈕名稱為"起始時間~結束時間"
                                show_name += f"~{end_hour}:{end_min}:{end_sec}"
                                show_list.append(show_name)
                    # 如果選擇清單不為空
                    if len(video_list) != 0:
                        respText = "請選擇影片存檔起始時間～"
                        # 傳送選擇清單給使用者
                        bot.send_message(chat_id=request["chat_id"], text=respText, reply_markup = InlineKeyboardMarkup([
                            [InlineKeyboardButton(show_list[i], callback_data = "archive_check:" +  request["device_number"] + ":" + request["archive_date"] + ":" + video_list[i] + ":" + str(request["chat_id"])),
                                InlineKeyboardButton(show_list[i+1], callback_data = "archive_check:" +  request["device_number"] + ":" + request["archive_date"] + ":" + video_list[i+1] + ":" + str(request["chat_id"]))] for i in range(0, len(video_list)) if i == 0 or (i % 2) == 0
                        ]), parse_mode="Markdown")
                    # 如果選擇清單為空
                    else:
                        respText = "該時段沒有存檔～"
                        # 傳送提示文字給使用者
                        bot.send_message(chat_id=request["chat_id"], text=respText, parse_mode="Markdown")
                # 使用者請求清空
                dbArchiveRequest.update_one({"chat_id":request["chat_id"]}, {"$set":{"status":"0"}}, upsert=True)
            # 如果資料表狀態值為回傳結果(將使用者選擇的檔案從網路硬碟回傳到使用者的Telegram私人訊息))
            elif request["status"] == "return_result":
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
