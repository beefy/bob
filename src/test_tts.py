#!/usr/bin/env python3
"""
Text-to-Speech Test Script for Raspberry Pi 5
Uses Piper TTS to synthesize speech and play it through the speaker.

Usage:
python test_tts.py [--text "Hello world"] [--list-devices]
"""

import pyaudio
import numpy as np
import sys
import argparse
import signal
import subprocess
import tempfile
import os
import wave
from io import BytesIO


class PiperTTS:
    def __init__(self, sample_rate=22050, chunk_size=1024, channels=1, volume=0.7):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.volume = volume
        self.format = pyaudio.paInt16  # Piper outputs 16-bit audio
        
        self.audio = None
        self.output_stream = None
        
        print(f"Piper TTS Configuration:")
        print(f"  Sample Rate: {self.sample_rate} Hz")
        print(f"  Chunk Size: {self.chunk_size} samples")
        print(f"  Channels: {self.channels}")
        print(f"  Volume: {int(self.volume * 100)}%")
    
    def check_piper_installation(self):
        """Check if Piper is installed and available"""
        try:
            # Try to run piper with --help to check if it's available
            result = subprocess.run(['piper', '--help'], 
                                   capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False
    
    def install_piper(self):
        """Provide instructions for installing Piper"""
        print("\n❌ Piper TTS is not installed!")
        print("\nTo install Piper on Raspberry Pi:")
        print("1. Install via pip:")
        print("   pip install piper-tts")
        print("\nOR")
        print("2. Install the system package:")
        print("   sudo apt update")
        print("   sudo apt install piper-tts")
        print("\nOR")
        print("3. Download the binary release:")
        print("   wget https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_arm64.tar.gz")
        print("   tar -xzf piper_arm64.tar.gz")
        print("   sudo mv piper /usr/local/bin/")
        print("\nAfter installation, you'll also need a voice model.")
        print("Download a voice model from: https://github.com/rhasspy/piper/blob/master/VOICES.md")
        return None
    
    def list_devices(self):
        """List all available audio devices"""
        if self.audio is None:
            self.audio = pyaudio.PyAudio()
        
        print("\n=== Available Audio Devices ===")
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            print(f"Device {i}: {info['name']}")
            print(f"  Max Input Channels: {info['maxInputChannels']}")
            print(f"  Max Output Channels: {info['maxOutputChannels']}")
            print(f"  Default Sample Rate: {info['defaultSampleRate']}")
            print()
    
    def find_usb_devices(self):
        """Find USB audio devices"""
        if self.audio is None:
            self.audio = pyaudio.PyAudio()
        
        usb_devices = []
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            name = info['name'].lower()
            if 'usb' in name or 'external' in name:
                usb_devices.append((i, info))
        
        return usb_devices
    
    def get_supported_sample_rates(self, device_index):
        """Get supported sample rates for output device"""
        if self.audio is None:
            self.audio = pyaudio.PyAudio()
            
        device_info = self.audio.get_device_info_by_index(device_index)
        
        # Common sample rates to test
        standard_rates = [8000, 11025, 16000, 22050, 44100, 48000]
        supported_rates = []
        
        for rate in standard_rates:
            try:
                if device_info['maxOutputChannels'] > 0:
                    test_stream = self.audio.open(
                        format=self.format,
                        channels=1,
                        rate=rate,
                        output=True,
                        output_device_index=device_index,
                        frames_per_buffer=1024
                    )
                    test_stream.close()
                    supported_rates.append(rate)
            except:
                pass  # Rate not supported
        
        return supported_rates
    
    def setup_output_stream(self, output_device=None):
        """Setup output stream"""
        self.audio = pyaudio.PyAudio()
        
        # Find USB device if not specified
        if output_device is None:
            usb_devices = self.find_usb_devices()
            if usb_devices:
                print(f"\nFound {len(usb_devices)} USB audio device(s):")
                for idx, (dev_id, info) in enumerate(usb_devices):
                    print(f"  USB Device {dev_id}: {info['name']}")
                    if info['maxOutputChannels'] > 0:
                        output_device = dev_id
                        break
        
        if output_device is None:
            print("No suitable output device found. Using default.")
        else:
            print(f"\nUsing Output Device: {output_device}")
            
            # Check supported sample rates
            supported_rates = self.get_supported_sample_rates(output_device)
            print(f"Supported sample rates: {supported_rates}")
            
            if supported_rates and self.sample_rate not in supported_rates:
                new_rate = max(supported_rates)
                print(f"Changing sample rate from {self.sample_rate} to {new_rate}")
                self.sample_rate = new_rate
        
        # Setup output stream
        try:
            self.output_stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                output_device_index=output_device,
                frames_per_buffer=self.chunk_size
            )
            print("✓ Output stream initialized")
            return True
        except Exception as e:
            print(f"✗ Failed to initialize output stream: {e}")
            return False
    
    def find_voice_model(self):
        """Find available Piper voice models"""
        # Common locations for voice models
        model_locations = [
            "/usr/share/piper-voices",
            "/usr/local/share/piper-voices",
            "~/piper-voices",
            "./voices",
            os.path.expanduser("~/.local/share/piper-voices")
        ]
        
        for location in model_locations:
            expanded_path = os.path.expanduser(location)
            if os.path.exists(expanded_path):
                # Look for .onnx files
                for root, dirs, files in os.walk(expanded_path):
                    for file in files:
                        if file.endswith('.onnx'):
                            return os.path.join(root, file)
        
        # If no model found, suggest downloading one
        return None
    
    def synthesize_speech(self, text, voice_model=None):
        """Use Piper to synthesize speech from text"""
        if not self.check_piper_installation():
            self.install_piper()
            return None
        
        # Find voice model if not specified
        if voice_model is None:
            voice_model = self.find_voice_model()
            if voice_model is None:
                print("\n❌ No Piper voice model found!")
                print("\nTo download a voice model:")
                print("1. Create voices directory:")
                print("   mkdir -p ~/piper-voices")
                print("   cd ~/piper-voices")
                print("\n2. Download a voice model (example - US English):")
                print("   wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx")
                print("   wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json")
                print("\nOr browse all available voices at:")
                print("   https://github.com/rhasspy/piper/blob/master/VOICES.md")
                return None
        
        print(f"🎤 Using voice model: {os.path.basename(voice_model)}")
        print(f"💬 Synthesizing: \"{text}\"")
        
        try:
            # Create temporary file for output
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_filename = temp_file.name
            
            # Run Piper to generate speech
            cmd = [
                'piper',
                '--model', voice_model,
                '--output_file', temp_filename
            ]
            
            # Send text to piper via stdin
            result = subprocess.run(
                cmd, 
                input=text, 
                text=True, 
                capture_output=True, 
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"❌ Piper failed: {result.stderr}")
                os.unlink(temp_filename)
                return None
            
            # Read the generated audio file
            try:
                with wave.open(temp_filename, 'rb') as wav_file:
                    # Get audio parameters
                    sample_rate = wav_file.getframerate()
                    n_channels = wav_file.getnchannels()
                    sample_width = wav_file.getsampwidth()
                    
                    print(f"📊 Generated audio: {sample_rate}Hz, {n_channels} channels, {sample_width*8}-bit")
                    
                    # Read audio data
                    audio_data = wav_file.readframes(wav_file.getnframes())
                    
                    # Clean up temp file
                    os.unlink(temp_filename)
                    
                    # Update our sample rate to match the generated audio
                    self.sample_rate = sample_rate
                    
                    return audio_data
            
            except Exception as e:
                print(f"❌ Error reading generated audio: {e}")
                if os.path.exists(temp_filename):
                    os.unlink(temp_filename)
                return None
                
        except subprocess.TimeoutExpired:
            print("❌ Piper timed out")
            return None
        except Exception as e:
            print(f"❌ Error running Piper: {e}")
            return None
    
    def play_audio_data(self, audio_data):
        """Play raw audio data through the speaker"""
        if self.output_stream is None:
            print("Output stream not initialized")
            return False
        
        if not audio_data or not isinstance(audio_data, bytes):
            print("Invalid audio data provided")
            return False
        
        try:
            # Start the stream
            self.output_stream.start_stream()
            
            # Convert to numpy array for volume control
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Apply volume control
            audio_array = (audio_array.astype(np.float32) * self.volume).astype(np.int16)
            
            # Play audio in chunks
            for i in range(0, len(audio_array), self.chunk_size):
                chunk = audio_array[i:i + self.chunk_size]
                
                # Pad with zeros if chunk is too small
                if len(chunk) < self.chunk_size:
                    chunk = np.pad(chunk, (0, self.chunk_size - len(chunk)), mode='constant')
                
                # Convert to bytes and play
                chunk_bytes = chunk.tobytes()
                self.output_stream.write(chunk_bytes, exception_on_underflow=False)
            
            # Stop the stream
            self.output_stream.stop_stream()
            return True
            
        except Exception as e:
            print(f"Error playing audio: {e}")
            return False
    
    def speak(self, text, output_device=None, voice_model=None):
        """Synthesize speech and play it through the speaker"""
        print(f"\n🗣️  Speaking: \"{text}\"")
        
        # Generate speech audio
        audio_data = self.synthesize_speech(text, voice_model)
        if audio_data is None or not audio_data:
            print("❌ Failed to synthesize speech")
            return False
        
        # Setup output stream
        if not self.setup_output_stream(output_device):
            return False
        
        # Play the audio
        success = self.play_audio_data(audio_data)
        
        if success:
            print("✓ Speech played successfully")
        else:
            print("✗ Failed to play speech")
        
        self.cleanup()
        return success
    
    def cleanup(self):
        """Clean up audio resources"""
        if self.output_stream:
            self.output_stream.close()
            self.output_stream = None
        
        if self.audio:
            self.audio.terminate()
            self.audio = None


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\nReceived interrupt signal...")
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description='Text-to-Speech test for Raspberry Pi 5 using Piper')
    parser.add_argument('--text', type=str, default='Hello',
                       help='Text to speak (default: "Hello")')
    parser.add_argument('--list-devices', action='store_true',
                       help='List available audio devices and exit')
    parser.add_argument('--output-device', type=int,
                       help='Output device index (speaker)')
    parser.add_argument('--voice-model', type=str,
                       help='Path to Piper voice model (.onnx file)')
    parser.add_argument('--volume', type=float, default=0.7,
                       help='Output volume (0.0-1.0, default: 0.7)')
    parser.add_argument('--sample-rate', type=int, default=22050,
                       help='Sample rate in Hz (default: 22050)')
    
    args = parser.parse_args()
    
    # Validate volume
    if args.volume < 0.0 or args.volume > 1.0:
        print("Error: Volume must be between 0.0 and 1.0")
        sys.exit(1)
    
    # Create TTS instance
    tts = PiperTTS(
        sample_rate=args.sample_rate,
        volume=args.volume
    )
    
    # List devices if requested
    if args.list_devices:
        tts.list_devices()
        return
    
    # Setup signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        success = tts.speak(args.text, args.output_device, args.voice_model)
        
        if success:
            print("\n✅ Text-to-Speech test completed successfully!")
        else:
            print("\n❌ Text-to-Speech test failed")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
