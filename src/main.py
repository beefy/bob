#!/usr/bin/env python3
"""
Bob - AI Voice Assistant
Integrates wake word detection, speech recognition, local LLM, and text-to-speech
for a complete voice-controlled AI assistant on Raspberry Pi 5.
"""

import speech_recognition as sr
import sys
import signal
import threading
import time
import os
import asyncio
import tempfile
import subprocess
from llama_cpp import Llama

# Try to import edge-tts, fall back to pyttsx3 if not available
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    import pyttsx3
    EDGE_TTS_AVAILABLE = False


class BobAssistant:
    def __init__(self, wake_phrase="hey bob", model_path=None):
        self.wake_phrase = wake_phrase.lower()
        self.running = False
        self.model_path = model_path
        self.llm = None
        
        # Speech recognition setup
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # TTS setup
        self.use_edge_tts = EDGE_TTS_AVAILABLE
        if self.use_edge_tts:
            print("🎤 Using Edge TTS (high quality)")
            self.voice = "en-US-AriaNeural"  # High quality female voice
        else:
            print("🎤 Using pyttsx3 (fallback)")
            self.tts_engine = pyttsx3.init()
            self.setup_pyttsx3()
        
        # Adjust for ambient noise
        print("📏 Calibrating microphone for ambient noise... Please wait.")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        print("✅ Microphone calibrated")
    
    def setup_pyttsx3(self):
        """Configure pyttsx3 TTS engine settings (fallback)"""
        voices = self.tts_engine.getProperty('voices')
        if voices:
            # Try to find a female voice, fall back to first available
            for voice in voices:
                if 'female' in voice.name.lower() or 'woman' in voice.name.lower():
                    self.tts_engine.setProperty('voice', voice.id)
                    break
            else:
                self.tts_engine.setProperty('voice', voices[0].id)
        
        # Set speech rate and volume
        self.tts_engine.setProperty('rate', 150)  # Slightly slower than default
        self.tts_engine.setProperty('volume', 0.9)
    
    async def speak_edge_tts(self, text):
        """Use Edge TTS for high-quality speech"""
        try:
            # Create TTS communication
            communicate = edge_tts.Communicate(text, self.voice)
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                tmp_filename = tmp_file.name
                await communicate.save(tmp_filename)
            
            # Play the audio file
            if os.path.exists(tmp_filename):
                if sys.platform.startswith('linux'):
                    # Try different playback methods on Linux/Pi
                    try:
                        # First try with mpv (better format support)
                        subprocess.run(['mpv', '--no-video', '--really-quiet', tmp_filename], 
                                     check=True, timeout=30, capture_output=True)
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        try:
                            # Try with ffplay (from ffmpeg)
                            subprocess.run(['ffplay', '-nodisp', '-autoexit', '-v', 'quiet', tmp_filename], 
                                         check=True, timeout=30, capture_output=True)
                        except (subprocess.CalledProcessError, FileNotFoundError):
                            try:
                                # Convert to WAV with proper format and use aplay
                                wav_file = tmp_filename.replace('.mp3', '.wav')
                                subprocess.run(['ffmpeg', '-i', tmp_filename, '-acodec', 'pcm_s16le', 
                                              '-ar', '44100', '-ac', '1', '-y', wav_file], 
                                             check=True, capture_output=True)
                                subprocess.run(['aplay', '-D', 'default', wav_file], check=True, capture_output=True)
                                os.unlink(wav_file)
                            except (subprocess.CalledProcessError, FileNotFoundError):
                                raise Exception("No suitable audio player found. Install mpv, ffmpeg, or check aplay configuration.")
                                
                elif sys.platform == 'darwin':
                    subprocess.run(['afplay', tmp_filename], check=True, capture_output=True)
                
                # Clean up
                os.unlink(tmp_filename)
                
        except Exception as e:
            print(f"❌ Edge TTS error: {e}")
            # Fall back to pyttsx3
            if hasattr(self, 'tts_engine'):
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
    
    def speak_pyttsx3(self, text):
        """Use pyttsx3 for speech (fallback)"""
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()
    
    def speak(self, text):
        """Convert text to speech using best available method"""
        print(f"🔊 Bob: {text}")
        
        if self.use_edge_tts:
            # Run Edge TTS in async context
            try:
                asyncio.run(self.speak_edge_tts(text))
            except Exception as e:
                print(f"❌ Edge TTS failed, falling back to pyttsx3: {e}")
                if hasattr(self, 'tts_engine'):
                    self.speak_pyttsx3(text)
        else:
            self.speak_pyttsx3(text)
    
    def find_model_file(self):
        """Find a GGUF model file in common locations"""
        possible_paths = [
            "./models/",
            "~/models/",
            "/home/bob/models/",
            "./"
        ]
        
        model_names = [
            "Phi-3-mini-4k-instruct-q4.gguf",
            "phi-3-mini-4k-instruct.q4_0.gguf",
            "phi-3-mini-4k-instruct.gguf",
            "llama-2-7b-chat.q4_0.gguf",
            "llama-2-7b-chat.gguf",
            "tinyllama-1.1b-chat-v1.0.q4_0.gguf"
        ]
        
        print("🔍 Searching for model files...")
        for path in possible_paths:
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path):
                for model_name in model_names:
                    full_path = os.path.join(expanded_path, model_name)
                    if os.path.exists(full_path):
                        print(f"✅ Found model: {full_path}")
                        return full_path
        
        print("❌ No model files found in common locations")
        return None
    
    def load_llm(self):
        """Load the LLM model"""
        print("🔄 Loading LLM model... (this may take a few minutes)")
        start_time = time.time()
        
        # Find model if not specified
        if self.model_path is None:
            self.model_path = self.find_model_file()
            if self.model_path is None:
                self.speak("Error: No LLM model found. Please download a model first.")
                return False
        
        try:
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=2048,
                n_threads=4,
                verbose=False
            )
            
            load_time = time.time() - start_time
            print(f"✅ Model loaded in {load_time:.1f} seconds")
            return True
            
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            self.speak("Error loading LLM model. Please check the console for details.")
            return False
    
    def get_llm_response(self, prompt):
        """Get response from the LLM"""
        if self.llm is None:
            return "Sorry, the LLM model is not loaded."
        
        try:
            print(f"🤔 Thinking about: {prompt}")
            
            # Format prompt for chat
            formatted_prompt = f"User: {prompt}\nAssistant:"
            
            response = self.llm(
                formatted_prompt,
                max_tokens=256,
                temperature=0.7,
                top_p=0.9,
                echo=False,
                stop=["User:", "\n\n"]
            )
            
            answer = response['choices'][0]['text'].strip()
            return answer
            
        except Exception as e:
            print(f"❌ Error getting LLM response: {e}")
            return "Sorry, I encountered an error while thinking about your question."
    
    def listen_for_speech(self, timeout=5):
        """Listen for speech and return transcription"""
        try:
            with self.microphone as source:
                print("👂 Listening...")
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
            
            print("🔄 Processing speech...")
            text = self.recognizer.recognize_google(audio).lower()
            print(f"📝 Heard: {text}")
            return text
            
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            print("❓ Could not understand audio")
            return None
        except sr.RequestError as e:
            print(f"❌ Speech recognition error: {e}")
            return None
    
    def listen_for_wake_word(self):
        """Continuously listen for the wake phrase"""
        print(f"👂 Listening for wake phrase: '{self.wake_phrase}'")
        
        while self.running:
            try:
                text = self.listen_for_speech(timeout=1)
                if text and self.wake_phrase in text:
                    print(f"✅ Wake phrase detected!")
                    return True
                    
            except Exception as e:
                if self.running:  # Only show error if we're still running
                    print(f"❌ Wake word detection error: {e}")
                    time.sleep(1)
        
        return False
    
    def conversation_loop(self):
        """Handle a conversation after wake word is detected"""
        self.speak("Listening")
        
        # Listen for the user's question
        print("👂 Waiting for your question...")
        question = self.listen_for_speech(timeout=10)
        
        if question:
            print(f"❓ Question: {question}")
            
            # Get LLM response
            response = self.get_llm_response(question)
            
            # Speak the response
            self.speak(response)
        else:
            self.speak("I didn't hear a question. Try again by saying hey bob.")
    
    def run(self):
        """Main assistant loop"""
        print("🤖 Starting Bob Assistant...")
        
        # Load LLM first
        if not self.load_llm():
            print("❌ Failed to load LLM. Exiting.")
            return
        
        # Announce ready state
        self.speak("Up and running")
        
        self.running = True
        
        try:
            while self.running:
                # Wait for wake word
                if self.listen_for_wake_word():
                    # Handle conversation
                    self.conversation_loop()
                    print(f"👂 Listening for wake phrase: '{self.wake_phrase}'")
                
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
        finally:
            self.running = False
    
    def stop(self):
        """Stop the assistant"""
        self.running = False


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print('\n🛑 Interrupted! Shutting down...')
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, signal_handler)
    
    print("🤖 Bob - AI Voice Assistant")
    print("=" * 50)
    print("Say 'Hey Bob' to start a conversation")
    print("Press Ctrl+C to exit")
    print("=" * 50)
    
    # Create and run the assistant
    bob = BobAssistant()
    bob.run()


if __name__ == "__main__":
    main()
