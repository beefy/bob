import edge_tts
import asyncio
import tempfile
import subprocess
import os
import sys

async def test_edge_tts():
    """Test Edge TTS with a sample phrase"""
    text = 'The quick brown fox jumps over the lazy dog.'
    voice = "en-US-AriaNeural"  # High quality female voice
    
    print(f"🔊 Speaking: {text}")
    print(f"🎤 Using voice: {voice}")
    
    try:
        # Create TTS communication
        communicate = edge_tts.Communicate(text, voice)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            tmp_filename = tmp_file.name
            await communicate.save(tmp_filename)
        
        # Play the audio file
        if os.path.exists(tmp_filename):
            print("🎵 Playing audio...")
            if sys.platform.startswith('linux'):
                subprocess.run(['aplay', tmp_filename], check=True)
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
    asyncio.run(test_edge_tts())
