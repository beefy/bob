#!/usr/bin/env python3
"""
Wake Word Detection Test using SpeechRecognition
Listens for "Hey Bob" wake word and responds with TTS.

List microphones:
python src/test_wake_word.py --list-devices

Use specific microphone:
python src/test_wake_word.py --mic-device 1

Custom wake phrase:
python src/test_wake_word.py --wake-phrase "hello computer"
"""

import speech_recognition as sr
import pyttsx3
import sys
import signal
import threading
import time


class WakeWordDetector:
    def __init__(self, wake_phrase="hey bob"):
        self.wake_phrase = wake_phrase.lower()
        self.running = False
        self.listening_paused = False
        
        # Speech recognition setup
        self.recognizer = sr.Recognizer()
        self.microphone = None
        
        # Adjust recognizer sensitivity
        self.recognizer.energy_threshold = 300  # Minimum audio energy to consider for recording
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 1.0  # Seconds of non-speaking audio before a phrase is considered complete
        
        # TTS setup
        self.tts_engine = pyttsx3.init()
        
        print(f"Wake Word Detector Configuration:")
        print(f"  Wake Phrase: '{self.wake_phrase}'")
        print(f"  Using Google Speech Recognition (requires internet)")
    
    def find_usb_microphone(self):
        """Find USB microphone device"""
        mic_list = sr.Microphone.list_microphone_names()
        
        print("\\nAvailable microphones:")
        for i, name in enumerate(mic_list):
            print(f"  {i}: {name}")
            # Look for USB devices - broader search
            if any(usb_indicator in name.lower() for usb_indicator in ['usb', 'device', '0x1908']):
                print(f"    ^ Found likely USB microphone: {i}")
                return i
        
        print("No USB microphone found, using default")
        return None
    
    def setup_microphone(self, device_index=None):
        """Setup microphone"""
        try:
            if device_index is None:
                device_index = self.find_usb_microphone()
            
            if device_index is not None:
                self.microphone = sr.Microphone(device_index=device_index)
                print(f"Using microphone device: {device_index}")
            else:
                self.microphone = sr.Microphone()
                print("Using default microphone")
            
            # Calibrate microphone for ambient noise
            print("Calibrating microphone for ambient noise... (speak now to test)")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
            
            print(f"✓ Microphone initialized (energy threshold: {self.recognizer.energy_threshold})")
            return True
            
        except Exception as e:
            print(f"✗ Failed to initialize microphone: {e}")
            return False
    
    def on_wake_word_detected(self):
        """Called when wake word is detected"""
        print(f"🎯 Wake phrase detected: '{self.wake_phrase}'")
        
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
        print(f"👂 Listening for wake phrase: '{self.wake_phrase}'")
        print("Speak clearly towards the microphone...")
        print("Press Ctrl+C to stop...")
        
        self.listening_paused = False
        
        while self.running:
            if self.listening_paused:
                time.sleep(0.1)
                continue
            
            try:
                # Listen for audio
                with self.microphone as source:
                    print("🎤 Listening...")
                    # Listen for audio with timeout
                    audio = self.recognizer.listen(source, timeout=1.0, phrase_time_limit=5.0)
                
                try:
                    # Use Google Speech Recognition (requires internet)
                    text = self.recognizer.recognize_google(audio).lower()
                    print(f"Heard: '{text}'")
                    
                    # Check if wake phrase is in the recognized text
                    if self.wake_phrase in text:
                        self.on_wake_word_detected()
                    
                except sr.UnknownValueError:
                    # Could not understand audio
                    print(".", end="", flush=True)  # Show activity
                    pass
                    
                except sr.RequestError as e:
                    print(f"Speech recognition error: {e}")
                    time.sleep(1.0)
                    
            except sr.WaitTimeoutError:
                # No speech detected within timeout
                print(".", end="", flush=True)  # Show activity
                pass
                
            except Exception as e:
                if self.running:
                    print(f"\\nAudio processing error: {e}")
                break
    
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
    
    parser = argparse.ArgumentParser(description='Wake word detection test using SpeechRecognition')
    parser.add_argument('--mic-device', type=int, help='Microphone device index')
    parser.add_argument('--list-devices', action='store_true', help='List available microphones')
    parser.add_argument('--wake-phrase', default='hey bob', help='Wake phrase to listen for')
    
    args = parser.parse_args()
    
    # List devices if requested
    if args.list_devices:
        print("\\n=== Available Microphones ===")
        mic_list = sr.Microphone.list_microphone_names()
        for i, name in enumerate(mic_list):
            print(f"Device {i}: {name}")
        return
    
    # Create wake word detector
    global detector
    detector = WakeWordDetector(wake_phrase=args.wake_phrase)
    
    # Setup signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        if detector.start(args.mic_device):
            # Keep running until interrupted
            while detector.running:
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