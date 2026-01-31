#!/usr/bin/env python3
"""
Simple Speaker Test Script for Raspberry Pi 5
Plays a test tone through the speaker to verify audio output.

Usage:
python test_speaker.py [--frequency HZ] [--duration SECONDS] [--list-devices]
"""

import pyaudio
import numpy as np
import time
import sys
import argparse
import signal


class SpeakerTest:
    def __init__(self, sample_rate=44100, chunk_size=1024, channels=1, volume=0.3):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.volume = volume
        self.format = pyaudio.paFloat32
        
        self.audio = None
        self.output_stream = None
        
        print(f"Speaker Test Configuration:")
        print(f"  Sample Rate: {self.sample_rate} Hz")
        print(f"  Chunk Size: {self.chunk_size} samples")
        print(f"  Channels: {self.channels}")
        print(f"  Volume: {int(self.volume * 100)}%")
    
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
        standard_rates = [8000, 11025, 16000, 22050, 44100, 48000, 88200, 96000]
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
    
    def generate_tone(self, frequency, duration):
        """Generate a sine wave tone"""
        total_samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, total_samples, False)
        
        # Generate sine wave
        tone = np.sin(2 * np.pi * frequency * t).astype(np.float32)
        
        # Apply volume
        tone *= self.volume
        
        return tone
    
    def generate_sweep(self, start_freq, end_freq, duration):
        """Generate a frequency sweep"""
        total_samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, total_samples, False)
        
        # Generate frequency sweep
        # Frequency changes linearly from start_freq to end_freq
        instantaneous_freq = start_freq + (end_freq - start_freq) * t / duration
        phase = 2 * np.pi * np.cumsum(instantaneous_freq) / self.sample_rate
        
        sweep = np.sin(phase).astype(np.float32)
        
        # Apply volume
        sweep *= self.volume
        
        return sweep
    
    def generate_noise(self, duration):
        """Generate white noise"""
        total_samples = int(self.sample_rate * duration)
        noise = np.random.normal(0, 0.1, total_samples).astype(np.float32)
        
        # Apply volume
        noise *= self.volume
        
        return noise
    
    def play_audio(self, audio_data):
        """Play audio data through the speaker"""
        if self.output_stream is None:
            print("Output stream not initialized")
            return False
        
        try:
            # Start the stream
            self.output_stream.start_stream()
            
            # Play audio in chunks
            for i in range(0, len(audio_data), self.chunk_size):
                chunk = audio_data[i:i + self.chunk_size]
                
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
    
    def test_tone(self, frequency=440, duration=2.0, output_device=None):
        """Test speaker with a simple tone"""
        print(f"\n🔊 Playing {frequency}Hz tone for {duration} seconds...")
        
        if not self.setup_output_stream(output_device):
            return False
        
        tone = self.generate_tone(frequency, duration)
        success = self.play_audio(tone)
        
        if success:
            print("✓ Tone played successfully")
        else:
            print("✗ Failed to play tone")
        
        self.cleanup()
        return success
    
    def test_sweep(self, start_freq=200, end_freq=2000, duration=3.0, output_device=None):
        """Test speaker with a frequency sweep"""
        print(f"\n🎵 Playing frequency sweep {start_freq}Hz to {end_freq}Hz for {duration} seconds...")
        
        if not self.setup_output_stream(output_device):
            return False
        
        sweep = self.generate_sweep(start_freq, end_freq, duration)
        success = self.play_audio(sweep)
        
        if success:
            print("✓ Sweep played successfully")
        else:
            print("✗ Failed to play sweep")
        
        self.cleanup()
        return success
    
    def test_noise(self, duration=2.0, output_device=None):
        """Test speaker with white noise"""
        print(f"\n📢 Playing white noise for {duration} seconds...")
        
        if not self.setup_output_stream(output_device):
            return False
        
        noise = self.generate_noise(duration)
        success = self.play_audio(noise)
        
        if success:
            print("✓ Noise played successfully")
        else:
            print("✗ Failed to play noise")
        
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
    parser = argparse.ArgumentParser(description='Speaker test for Raspberry Pi 5')
    parser.add_argument('--frequency', type=float, default=440,
                       help='Test tone frequency in Hz (default: 440)')
    parser.add_argument('--duration', type=float, default=2.0,
                       help='Test duration in seconds (default: 2.0)')
    parser.add_argument('--list-devices', action='store_true',
                       help='List available audio devices and exit')
    parser.add_argument('--output-device', type=int,
                       help='Output device index (speaker)')
    parser.add_argument('--sample-rate', type=int, default=44100,
                       help='Sample rate in Hz (default: 44100)')
    parser.add_argument('--volume', type=float, default=0.3,
                       help='Output volume (0.0-1.0, default: 0.3)')
    parser.add_argument('--test-type', choices=['tone', 'sweep', 'noise', 'all'], default='tone',
                       help='Type of test to run (default: tone)')
    
    args = parser.parse_args()
    
    # Validate volume
    if args.volume < 0.0 or args.volume > 1.0:
        print("Error: Volume must be between 0.0 and 1.0")
        sys.exit(1)
    
    # Create speaker test instance
    speaker_test = SpeakerTest(
        sample_rate=args.sample_rate,
        volume=args.volume
    )
    
    # List devices if requested
    if args.list_devices:
        speaker_test.list_devices()
        return
    
    # Setup signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        success = False
        
        if args.test_type == 'tone':
            success = speaker_test.test_tone(args.frequency, args.duration, args.output_device)
        elif args.test_type == 'sweep':
            success = speaker_test.test_sweep(200, 2000, args.duration, args.output_device)
        elif args.test_type == 'noise':
            success = speaker_test.test_noise(args.duration, args.output_device)
        elif args.test_type == 'all':
            print("Running all tests...")
            success1 = speaker_test.test_tone(440, 2.0, args.output_device)
            time.sleep(0.5)
            success2 = speaker_test.test_sweep(200, 2000, 3.0, args.output_device)
            time.sleep(0.5)
            success3 = speaker_test.test_noise(1.5, args.output_device)
            success = success1 and success2 and success3
        
        if success:
            print("\n✅ Speaker test completed successfully!")
        else:
            print("\n❌ Speaker test failed")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()