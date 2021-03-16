Heroku 帳號@gmail, 密碼加點:a056966155.

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
  
Show mount:
  root@sdn-k8s-b3-1:~# ls /mnt/telegram
    2706_1  2706_2
  root@sdn-k8s-b3-1:~# ls /mnt/telegram/2706_1/
    20201106PM  20201113PM  20201120PM  20201128AM 
  root@sdn-k8s-b3-1:~# ls /mnt/telegram/2706_1/20201106PM/
    2706_1-20201106-174746-1604656066.mp4  2706_1-20201106-184924-1604659764.mp4
