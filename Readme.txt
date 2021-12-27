telegram機器人: app.py
本地服務: Docker_Dir/

pip install python-telegram-bot
pip install pymongo
pip install dnspython
pip install opencv-python
pip install imgurpython
pip install pyimgur
pip install schedule

Telegram 網路 NFS 硬碟掛載(已白名單之機房電腦可連線)
  !Sysnology NAS 設定:
    IP: 10.0.0.73:5000
    User: telegram
    Password: iamcuser

Linux NFS 掛載
  !NFS 套件安裝:
    apt-get update
    apt-get install nfs-common

  !掛載:
    mkdir /mnt/telegram
    mount -t nfs 10.0.0.173:/volume1/surveillance /mnt/telegram
  
  !解掛載:
    umount /mnt/telegram
 
