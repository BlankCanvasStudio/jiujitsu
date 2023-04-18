#!/bin/bash
# The following code kills bashlex. So hopefully we can implement it but its a longer term vision


i=0
((i++))
echo i
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
$[RANDOM%223+1]
if [ "$release" == "CentOS" ]; then
  echo "$release 1"
elif [[ "$release" == "Ubuntu" ]] || [[ "$release" == "Debian" ]]; then
  echo "$release 2"
else
  exit 1
fi
value=$(( 3 * 7 / 2 ))

if ! sudo -n true 2>/dev/null; then
  echo this;
done

testing=3
if [ $testing != 106 -a $testing != 95 ]; then
  echo this;
done

[[ $tesing = 3 ]] || (echo "it isn't")
echo $((${ssr_port}+0)) &>/dev/null

for((integer = 0; integer <= 100; integer++))
do
  echo this;
done

for((integer = 100; integer >= 1; integer--))
do
  echo this
done