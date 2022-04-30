sudo apt-get install python3-venv
sudo mkdir /opt/alsa_indicator
sudo cp ~/alsa_indicator/alsa_indicator.py /opt/alsa_indicator
sudo apt-get install python3-venv
sudo python -m venv env
sudo cp ~/alsa_indicator/alsa_indicator.service /etc/systemd/system/alsa_indicator.service
sudo systemctl start alsa_indicator.service
sudo systemctl enable alsa_indicator.service

