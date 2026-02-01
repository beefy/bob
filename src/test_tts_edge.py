import edge_tts
import asyncio
import tempfile
import subprocess
import os
import sys
import argparse

async def test_edge_tts(text=None, voice="en-US-AriaNeural"):
    """Test Edge TTS with a sample phrase"""
    if text is None:
        text = 'The quick brown fox jumps over the lazy dog.'
    
    print(f"🔊 Speaking: {text}")
    print(f"🎤 Using voice: {voice}")
    
    try:
        # Create TTS communication
        communicate = edge_tts.Communicate(text, voice)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            tmp_filename = tmp_file.name
            await communicate.save(tmp_filename)
        
        # Play the audio file
        if os.path.exists(tmp_filename):
            print("🎵 Playing audio...")
            
            if sys.platform.startswith('linux'):
                # Try different playback methods on Linux/Pi
                try:
                    # First try with mpv (better format support)
                    subprocess.run(['mpv', '--no-video', '--really-quiet', tmp_filename], 
                                 check=True, timeout=30)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    try:
                        # Try with ffplay (from ffmpeg)
                        subprocess.run(['ffplay', '-nodisp', '-autoexit', '-v', 'quiet', tmp_filename], 
                                     check=True, timeout=30)
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        try:
                            # Convert to WAV with proper format and use aplay
                            wav_file = tmp_filename.replace('.mp3', '.wav')
                            subprocess.run(['ffmpeg', '-i', tmp_filename, '-acodec', 'pcm_s16le', 
                                          '-ar', '44100', '-ac', '1', '-y', wav_file], 
                                         check=True, capture_output=True)
                            subprocess.run(['aplay', '-D', 'default', wav_file], check=True)
                            os.unlink(wav_file)
                        except (subprocess.CalledProcessError, FileNotFoundError):
                            print("❌ No suitable audio player found. Install mpv, ffmpeg, or check aplay configuration.")
                            
            elif sys.platform == 'darwin':
                subprocess.run(['afplay', tmp_filename], check=True)
            else:
                print("❌ Unsupported platform for audio playback")
            
            # Clean up
            os.unlink(tmp_filename)
            print("✅ Test completed successfully")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test Edge TTS with custom text')
    parser.add_argument('text', nargs='?', 
                       default='The quick brown fox jumps over the lazy dog.',
                       help='Text to speak (default: "The quick brown fox jumps over the lazy dog.")')
    parser.add_argument('--voice', '-v', 
                       default='en-US-AriaNeural',
                       help='Voice to use (default: en-US-AriaNeural)')
    
    args = parser.parse_args()
    
    asyncio.run(test_edge_tts(args.text, args.voice))
