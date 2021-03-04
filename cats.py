import cv2
import os
import requests

# url = "rtsp://admin:443926@192.168.1.252:554/live/profile.0"
# # 導入攝像機
# cap = cv2.VideoCapture(url)

# recordForucc = cv2.VideoWriter_fourcc(*"mp4v")
# print(recordForucc)
# recordFPS = int(cap.get(cv2.CAP_PROP_FPS))
# print(recordFPS)
# recordWidth = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
# print(recordWidth)
# recordHeight = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
# print(recordHeight)
# # 建立錄影實體物件
# record = cv2.VideoWriter('CameraRecord.mp4', recordForucc, recordFPS/2, (recordWidth, recordHeight))

# # 時間換算, 對比約為 1:15
# cnt = 1
# # 迴圈錄影
# while cnt < 150:
#     ret, frame = cap.read()
#     record.write(frame)
#     cnt += 1
# # 攝像機記憶體空間釋放
# cap.release()
# record.release()

album_id = '1iIvG0r'
access_token = '6b504b7f2a616efce455040a89eb9aaa36b28b48'
imgur_upload_url = 'https://api.imgur.com/3/album/1iIvG0r/add'

with open('CameraRecord.mp4', "rb") as file: #Path is video path
    files = [('video', file)]
    data = {"type": "video/webm", "album": album_id}
    headers = {
        'Authorization': 'Bearer {}'.format(access_token)
    }
    response = requests.request('POST', imgur_upload_url, headers=headers, data=data, files=files)
    print(response.json())