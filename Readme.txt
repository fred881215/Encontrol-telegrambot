添加影像相關功能的 IMAC 機房環控系統，使用 Telegram Bot 作為使用者介面，Heroku 作為託管平台，MongoDB Atlas 作為雲端資料庫，如需改動請至 config.ini 修改設定。
使用前開啟 Heroku 服務並部署程式碼，並在本地端運行 Docker_Dir/ 底下的四個本地服務，可以下載 Docker Hub 上 bydufish/(本地服務資料夾名稱) 的映像檔並背景運行。

Telegram Bot 機器人: app,py
本地端服務: Docker_Dir/*
Python 套件清單: config.ini

監控錄影檔留存在 IMAC NFS Server，使用 Docker 映像檔部署本地服務時容器內部會自動掛載。
NFS Server 有開啟白名單，部署本地服務的伺服器需連通 2706 區域網路並加入白名單

！如果需要本地掛載 NFS Server！
NFS 套件安裝:
    apt-get update
    apt-get install nfs-common

NFS 硬碟掛載設定(已白名單的機房電腦可連線)
Sysnology NAS 設定:
    IP: 10.0.0.73:5000
    User: telegram
    Password: iamcuser

本地掛載指令:
    mkdir /mnt/telegram
    mount -t nfs 10.0.0.173:/volume1/surveillance /mnt/telegram
  
解除掛載指令:
    umount /mnt/telegram
 
