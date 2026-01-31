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
sudo apt-get install portaudio19-dev python3-dev alsa-utils libasound2-plugins flac
pip install -r requirements.txt
```

### Setup Local LLM (Phi-3-mini)

The Phi-3-mini model will be downloaded automatically on first run of `src/test_LLM.py` (~2.4GB). Make sure you have internet connection and enough storage:

```
# Check available disk space (need ~5GB free)
df -h

# The model will be cached in ~/.cache/huggingface/
# You can set a custom cache location if needed:
export HF_HOME=/path/to/custom/cache
```

**Note:** First model download and loading can take 10-15 minutes on Raspberry Pi. Subsequent runs are much faster.

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
