from flask import Flask, request, render_template, redirect, url_for, abort, jsonify
from werkzeug.utils import secure_filename
from pymongo import MongoClient
import configparser
import datetime
import pyimgur
import json
import os

app = Flask(__name__)

# 從 config.ini 讀取設定值
config = configparser.ConfigParser()
config.read('config.ini')

# mongo atlas URL
myMongoClient = MongoClient(config['MONGODB']['URL'])
myMongoDb = myMongoClient["smart-data-center"]

# 攝影功能
dbElectricmeterImage = myMongoDb['electricmeterImage']

# 存取路徑
File_path = config['IMAGEPROCESS']['LOCAL_PATH']
Nas_path = config['IMAGEPROCESS']['NAS_ENGINEROOM_PATH']

# imgur 圖床設置
client_id = config['IMAGEPROCESS']['IMGUR_CLIENT_ID']
client_secret = config['IMAGEPROCESS']['IMGUR_CLIENT_SECRET']

# 上傳電錶圖片檔案
@app.route('/electricmeter_upload', methods=['POST'])
def Electricmeter_upload():
    # 從請求中抓出電錶度數
    kWh = request.form['kWh']
    # 從請求中抓出圖片檔案
    image_file = request.files['image']
    # 暫存於程式執行的資料夾底下
    image_file.save(File_path + image_file.filename)
    # 圖片上傳至 imgur 後刪除本地存檔
    im = pyimgur.Imgur(client_id)
    uploaded_image = im.upload_image(image_file.filename, title="ImacPicture_" + image_file.filename)
    os.remove(image_file.filename)
    # 取出昨天存的當日電錶圖片資料
    yesterday_data = dbElectricmeterImage.find_one({"feature":"today"})
    # 儲存昨日電錶圖片資料
    dbElectricmeterImage.update_one({"feature":"yesterday"}, {"$set":{"url":yesterday_data["url"], "archive_date":yesterday_data["archive_date"], "kWh":yesterday_data["kWh"]}}, upsert=True)
    # 儲存當日電錶圖片資料
    archive_date = datetime.datetime.now().strftime('%Y-%m-%d')
    dbElectricmeterImage.update_one({"feature":"today"}, {"$set":{"url":uploaded_image.link, "archive_date":archive_date, "kWh":kWh}}, upsert=True)
    # 結束回傳
    return jsonify({'status': 'ok'})

# 上傳機房圖片檔案
@app.route('/engineroom_upload', methods=['POST'])
def Engineroom_upload():
    # 從請求中抓出圖片檔案
    image_file = request.files['image']
    # 定義當日日期格式
    archive_date = datetime.datetime.now().strftime('%Y%m%d')
    # 如果網路硬碟(NAS)的機房照片主資料夾底下已經有當日日期的子資料夾
    if os.path.isdir(Nas_path + archive_date):
        # 將圖片檔案儲存在子資料夾底下
        image_file.save(Nas_path + archive_date + "/" + image_file.filename)
    # 如果網路硬碟(NAS)的機房照片主資料夾底下尚未有當日日期的子資料夾
    else:
        # 在主資料夾底下創建當日日期的子資料夾
        os.mkdir(Nas_path + archive_date)
        # 將圖片檔案儲存在子資料夾底下
        image_file.save(Nas_path + archive_date + "/" + image_file.filename)
    # 結束回傳
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.debug = True
    app.run(host="0.0.0.0", port="5891")
