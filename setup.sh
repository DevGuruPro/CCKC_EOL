#!/usr/bin/env bash

cur_dir="$( cd "$(dirname "$0")" ; pwd -P )"
user="$(id -u -n)"

echo "Installing CCKC EOL"

sudo apt update

cd /tmp
wget http://www.airspayce.com/mikem/bcm2835/bcm2835-1.60.tar.gz
tar zxvf bcm2835-1.60.tar.gz
cd bcm2835-1.60/
sudo ./configure
sudo make
sudo make check
sudo make install

cd ${cur_dir}
sudo apt install -y python3-pip
sudo pip3 install -U pip
sudo pip3 install -r requirements.txt

# Enable SPI
echo "dtparam=spi=on" | sudo tee -a /boot/firmware/config.txt
echo "dtoverlay=mcp2515-can1,oscillator=16000000,interrupt=25" | sudo tee -a /boot/firmware/config.txt
echo "dtoverlay=mcp2515-can0,oscillator=16000000,interrupt=23" | sudo tee -a /boot/firmware/config.txt
echo "dtoverlay=spi-bcm2835-overlay" | sudo tee -a /boot/firmware/config.txt
