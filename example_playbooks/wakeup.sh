#!/bin/bash
WD=/home/alf/ansible
for MAC in `awk '{print $4}' $WD/macs.lst`
do
    sudo ether-wake -i enp5s1 $MAC
done