#!/usr/bin/env python3
"""
Wake Word Detection Test using OpenWakeWord
Listens for "Hey Bob" wake word and responds with TTS.
"""

import pyaudio
import numpy as np
import pyttsx3
import sys
import signal
import threading
from openwakeword.model import Model
from openwakeword import utils


class WakeWordDetector:
    def __init__(self, wake_word_models=None, sample_rate=16000, chunk_size=1280):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.format = pyaudio.paInt16
        self.channels = 1
        
        # Initialize OpenWakeWord model
        if wake_word_models is None:
            # Use default "hey jarvis" model (closest to "hey bob")
            wake_word_models = ["hey_jarvis_v0.1"]
        
        self.model = Model(wakeword_models=wake_word_models, inference_framework="tflite")
        self.wake_words = list(self.model.models.keys())
        
        # Audio setup
        self.audio = None
        self.input_stream = None
        self.running = False
        
        # TTS setup
        self.tts_engine = pyttsx3.init()
        
        print(f"Wake Word Detector Configuration:")
        print(f"  Sample Rate: {self.sample_rate} Hz")
        print(f"  Chunk Size: {self.chunk_size} samples")
        print(f"  Wake Words: {self.wake_words}")
        print(f"  Note: Using 'hey jarvis' model as closest match to 'Hey Bob'")
    
    def find_usb_microphone(self):
        """Find USB microphone device"""
        if self.audio is None:
            self.audio = pyaudio.PyAudio()
        
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            name = info['name'].lower()
            if 'usb' in name and info['maxInputChannels'] > 0:
                return i
        
        return None
    
    def setup_microphone(self, device_index=None):
        """Setup microphone stream"""
        if self.audio is None:
            self.audio = pyaudio.PyAudio()
        
        if device_index is None:
            device_index = self.find_usb_microphone()
        
        if device_index is not None:
            print(f"Using microphone device: {device_index}")
        else:
            print("Using default microphone device")
        
        try:
            self.input_stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.chunk_size
            )
            print("✓ Microphone initialized")
            return True
        except Exception as e:
            print(f"✗ Failed to initialize microphone: {e}")
            return False
    
    def on_wake_word_detected(self, wake_word):
        """Called when wake word is detected"""
        print(f"🎯 Wake word detected: {wake_word}")
        
        # Stop listening temporarily
        self.pause_listening()
        
        # Respond with TTS
        response_text = 'The quick brown fox jumps over the lazy dog.'
        print(f"🗣️ Responding: {response_text}")
        
        self.tts_engine.say(response_text)
        self.tts_engine.runAndWait()
        
        print("👂 Listening again...")
        # Resume listening
        self.resume_listening()
    
    def pause_listening(self):
        """Temporarily pause wake word detection"""
        self.listening_paused = True
    
    def resume_listening(self):
        """Resume wake word detection"""
        self.listening_paused = False
    
    def listen_for_wake_word(self):
        """Main listening loop"""
        print("👂 Listening for wake word...")
        print("Say 'Hey Jarvis' (closest to 'Hey Bob' in available models)")
        print("Press Ctrl+C to stop...")
        
        self.listening_paused = False
        
        try:
            while self.running:
                if self.listening_paused:
                    # Wait while paused
                    import time
                    time.sleep(0.1)
                    continue
                
                # Read audio data
                try:
                    audio_data = self.input_stream.read(self.chunk_size, exception_on_overflow=False)
                    audio_array = np.frombuffer(audio_data, dtype=np.int16)
                    
                    # Convert to float32 for OpenWakeWord (normalized to -1 to 1)
                    audio_float = audio_array.astype(np.float32) / 32768.0
                    
                    # Get predictions from the model
                    prediction = self.model.predict(audio_float)
                    
                    # Check for wake word detection
                    for wake_word, score in prediction.items():
                        if score > 0.5:  # Threshold for detection
                            self.on_wake_word_detected(wake_word)
                            break
                            
                except Exception as e:
                    if self.running:
                        print(f"Audio processing error: {e}")
                    break
                    
        except KeyboardInterrupt:
            print("\\nReceived interrupt in listening loop")
        finally:
            print("Listening stopped")
    
    def start(self, mic_device=None):
        """Start wake word detection"""
        if not self.setup_microphone(mic_device):
            return False
        
        self.running = True
        
        # Start listening in a separate thread
        self.listen_thread = threading.Thread(target=self.listen_for_wake_word, daemon=True)
        self.listen_thread.start()
        
        return True
    
    def stop(self):
        """Stop wake word detection"""
        self.running = False
        
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
        
        if self.audio:
            self.audio.terminate()
        
        if self.tts_engine:
            self.tts_engine.stop()
        
        print("\\n🛑 Wake word detection stopped")


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\\nReceived interrupt signal...")
    global detector
    if detector:
        detector.stop()
    sys.exit(0)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Wake word detection test using OpenWakeWord')
    parser.add_argument('--mic-device', type=int, help='Microphone device index')
    parser.add_argument('--list-devices', action='store_true', help='List available audio devices')
    
    args = parser.parse_args()
    
    # List devices if requested
    if args.list_devices:
        audio = pyaudio.PyAudio()
        print("\\n=== Available Input Devices (Microphones) ===")
        for i in range(audio.get_device_count()):
            info = audio.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                print(f"Device {i}: {info['name']}")
                print(f"  Max Input Channels: {info['maxInputChannels']}")
                print(f"  Default Sample Rate: {info['defaultSampleRate']}")
                print()
        audio.terminate()
        return
    
    # Create wake word detector
    global detector
    detector = WakeWordDetector()
    
    # Setup signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        if detector.start(args.mic_device):
            # Keep running until interrupted
            while detector.running:
                import time
                time.sleep(0.1)
        else:
            print("Failed to start wake word detection")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        detector.stop()


if __name__ == "__main__":
    main()