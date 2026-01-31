# bob
Raspberry Pi AI Assistant

## Hardware requirements

 - Raspberry Pi 5 with at least 8gb RAM
 - Raspberry Pi Case with heat sink and fan
 - USB 3.0 microphone
 - USB 3.0 speaker
 - Power supply for Raspberry Pi (USB C cable)
 - Micro SDXC Card
 - SD Card Reader

## Setup for a new Raspberry Pi

### Flash Image

 - Buy a micro SDXC card and an SD card reader.
 - Download the raspberry pi imager: https://www.raspberrypi.com/software/
 - Flash the SD card
 - Connect to the raspberry pi: https://connect.raspberrypi.com/devices

### Setup Github

 - Setup git user
```
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

 - Setup ssh key for github
```
ssh-keygen -t ed25519 -C "your.email@example.com"
cat ~/.ssh/id_ed25519.pub
```

 - Add the SSH key to github: https://github.com/settings/keys

### Create a virtual environment

```
python3 -m venv venv
source venv/bin/activate
```

### Clone this repo

```
mkdir ~/Code
cd Code
git clone git@github.com:beefy/bob.git
cd bob
```

### Install system dependencies

```
sudo apt-get update
sudo apt-get install portaudio19-dev python3-dev
sudo apt install espeak-ng espeak-ng-data libespeak-ng-dev
pip install -r requirements.txt
```

### Setup TTS

Create a directory for voice models and download a US English voice:

```
mkdir -p ~/piper-voices
cd ~/piper-voices
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
```

Browse other available voices at: https://github.com/rhasspy/piper/blob/master/VOICES.md
