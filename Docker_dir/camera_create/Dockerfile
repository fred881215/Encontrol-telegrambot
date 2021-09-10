# 使用官方的 ubuntu 執行環境作為基底
FROM ubuntu:18.04

# apt 包初始更新
RUN apt-get update

# 安裝 python3 及附屬套件
RUN apt-get install -y software-properties-common vim
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get update -y
RUN apt-get install -y python3.8
RUN apt-get install -y python3-pip

RUN DEBIAN_FRONTEND="noninteractive" apt-get -y install tzdata

# pip 包初始更新
RUN pip3 install wheel
RUN pip3 install --upgrade pip

# 安裝 nfs 客戶端
RUN apt-get install -y nfs-common

# 安裝 opencv
RUN apt-get install -y python-opencv

# 建立 nfs 資料夾
RUN service rpcbind start
RUN mkdir -p //mnt/telegram

# 建立工作目錄
RUN mkdir /app

# 設定工作目錄
WORKDIR /app

# 複製目前目錄下的內容，放進工作目錄
ADD . /app

# 安裝 requirements.txt 中所列的必要套件
RUN pip3 install -r requirements.txt

# 當 Docker 容器啟動時，自動執行 python 主程式
CMD ["python3", "camera_create.py"]