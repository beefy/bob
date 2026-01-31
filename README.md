# bob
Raspberry Pi AI Assistant

 - LLM runs locally (Phi-3-mini)
 - Edge TTS for text to speech
 - speech_recognition for STT

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
sudo apt-get install portaudio19-dev python3-dev alsa-utils libasound2-plugins flac
pip install -r requirements.txt
```

### Setup Local LLM (GGUF Models)

Download a GGUF model file. Start with a small model for testing:

```
# Create models directory
mkdir -p ~/models
cd ~/models

# Download a small model for testing (~600MB)
wget https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.q4_0.gguf

# Or download Phi-3-mini (~2.4GB)
wget https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf
```

**Note:** First model run will auto-detect the downloaded model. Loading takes 1-2 minutes on Raspberry Pi.

### Set Speaker As Default

```
# List audio cards (playback devices - speakers)
aplay -l

# List recording devices (microphones) 
arecord -l

# The output will look like:
# === Playback devices (aplay -l) ===
# card 0: vc4hdmi0 [vc4-hdmi-0] - Built-in HDMI audio
# card 1: vc4hdmi1 [vc4-hdmi-1] - Built-in HDMI audio  
# card 2: U0x19080x1331 [USB Device 0x1908:0x1331] - USB SPEAKER

# === Recording devices (arecord -l) ===
# card 3: Device [USB PnP Sound Device] - USB MICROPHONE

# For your setup: USB speaker is card 2
# Set default card to your USB speaker (card 2)
sudo nano /etc/asound.conf
```

Try the simple approach first (use card 2 for your USB speaker):
```
defaults.pcm.card 2
defaults.ctl.card 2
```

If that doesn't work, try:
```
pcm.!default {
    type hw
    card X
    device 0
}
ctl.!default {
    type hw
    card X
}
```

## Troubleshooting

 - `src/test_speaker.py` --> test that the speaker works
 - `src/test_tts.py` --> test the text to speech
 - `src/test_wake_word.py` --> test the speech recognition
 - `src/test_LLM.py` --> test the local LLM
