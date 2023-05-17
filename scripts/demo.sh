#!/bin/bash

if cat ~/ISI/final-present/sample.txt | grep "not-in";
then 
  echo success 
else
  echo failed
fi

(
  echo "text for the file"
) > ~/testing

Print1() {
 echo $a
}

a="something random"
Print1

testing=Print1
testing2=$(Print1)


Print2(){
 echo $a
}
tmp1=$(a="has more words"; Print2)
echo $tmp1

tmp2=${a:2:1}
echo $tmp2

tmp3=$(echo ${testing:1:1})

n="1 2 3 4"
for i in $n;
do 
  for j in 1 2 3 4; 
  do
    echo ${tmp2:0:1} ${tmp2:1:1}
  done
done

testing=$(a="Some-interesting-text-fr-"; echo $a | rev)

a=$b
echo $a
echo ${a[2]}

random=$(echo this; a=b; mv ~/testing ~/elsewhere)

Print3(){
  echo $1$2
  shift
  shift
  echo $1
  shift
  echo $1
}

unset a

random=$(Print3 $tmp3 $tmp2 $a ${testing:0:3})

echo $random/
echo "Turns out this was malware all along"
