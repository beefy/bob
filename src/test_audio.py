#!/usr/bin/env python3
"""
Audio Test Script for Raspberry Pi 5
Listens to microphone input and plays it back through speaker with delay.

Usage:
python test_audio.py [--delay SECONDS] [--list-devices]
"""

import pyaudio
import numpy as np
import time
import sys
import argparse
from collections import deque
import signal
import threading


class AudioLoopback:
    def __init__(self, delay_seconds=1.0, sample_rate=44100, chunk_size=1024, channels=1, volume=0.5):
        self.delay_seconds = delay_seconds
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.volume = volume
        self.format = pyaudio.paFloat32
        
        # Calculate buffer size for delay
        self.delay_samples = int(delay_seconds * sample_rate)
        self.delay_chunks = self.delay_samples // chunk_size + 1
        
        # Initialize audio buffer (circular buffer for delay)
        self.audio_buffer = deque(maxlen=self.delay_chunks)
        
        # Fill initial buffer with silence
        silence = np.zeros(chunk_size, dtype=np.float32)
        for _ in range(self.delay_chunks):
            self.audio_buffer.append(silence)
        
        self.audio = None
        self.input_stream = None
        self.output_stream = None
        self.running = False
        
        print(f"Audio Loopback Configuration:")
        print(f"  Sample Rate: {self.sample_rate} Hz")
        print(f"  Chunk Size: {self.chunk_size} samples")
        print(f"  Channels: {self.channels}")
        print(f"  Delay: {self.delay_seconds} seconds")
        print(f"  Volume: {int(self.volume * 100)}%")
        print(f"  Buffer Size: {self.delay_chunks} chunks")
    
    def list_devices(self):
        """List all available audio devices with supported sample rates"""
        if self.audio is None:
            self.audio = pyaudio.PyAudio()
        
        print("\n=== Available Audio Devices ===")
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            print(f"Device {i}: {info['name']}")
            print(f"  Max Input Channels: {info['maxInputChannels']}")
            print(f"  Max Output Channels: {info['maxOutputChannels']}")
            print(f"  Default Sample Rate: {info['defaultSampleRate']}")
            
            # Show supported sample rates for devices with inputs/outputs
            if info['maxInputChannels'] > 0:
                input_rates = self.get_supported_sample_rates(i, is_input=True)
                print(f"  Supported Input Rates: {input_rates}")
            
            if info['maxOutputChannels'] > 0:
                output_rates = self.get_supported_sample_rates(i, is_input=False)
                print(f"  Supported Output Rates: {output_rates}")
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
    
    def get_supported_sample_rates(self, device_index, is_input=True):
        """Get supported sample rates for a device"""
        if self.audio is None:
            self.audio = pyaudio.PyAudio()
            
        device_info = self.audio.get_device_info_by_index(device_index)
        
        # Common sample rates to test
        standard_rates = [8000, 11025, 16000, 22050, 44100, 48000, 88200, 96000]
        supported_rates = []
        
        for rate in standard_rates:
            try:
                if is_input and device_info['maxInputChannels'] > 0:
                    # Test input
                    test_stream = self.audio.open(
                        format=self.format,
                        channels=1,
                        rate=rate,
                        input=True,
                        input_device_index=device_index,
                        frames_per_buffer=1024
                    )
                    test_stream.close()
                    supported_rates.append(rate)
                elif not is_input and device_info['maxOutputChannels'] > 0:
                    # Test output
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

    def setup_streams(self, input_device=None, output_device=None):
        """Setup input and output streams with automatic sample rate detection"""
        self.audio = pyaudio.PyAudio()
        
        # Find USB devices if not specified
        if input_device is None or output_device is None:
            usb_devices = self.find_usb_devices()
            if usb_devices:
                print(f"\nFound {len(usb_devices)} USB audio device(s):")
                for idx, (dev_id, info) in enumerate(usb_devices):
                    print(f"  USB Device {dev_id}: {info['name']}")
                    if input_device is None and info['maxInputChannels'] > 0:
                        input_device = dev_id
                    if output_device is None and info['maxOutputChannels'] > 0:
                        output_device = dev_id
        
        print(f"\nUsing Input Device: {input_device}")
        print(f"Using Output Device: {output_device}")
        
        # Find compatible sample rate
        if input_device is not None:
            input_rates = self.get_supported_sample_rates(input_device, is_input=True)
            print(f"Input device supported rates: {input_rates}")
        else:
            input_rates = [self.sample_rate]
            
        if output_device is not None:
            output_rates = self.get_supported_sample_rates(output_device, is_input=False)
            print(f"Output device supported rates: {output_rates}")
        else:
            output_rates = [self.sample_rate]
        
        # Find common sample rate
        common_rates = list(set(input_rates) & set(output_rates))
        if common_rates:
            # Prefer higher sample rates, but use the original if available
            if self.sample_rate in common_rates:
                working_rate = self.sample_rate
            else:
                working_rate = max(common_rates)
            print(f"Using sample rate: {working_rate} Hz")
            self.sample_rate = working_rate
            
            # Recalculate delay buffer with new sample rate
            self.delay_samples = int(self.delay_seconds * self.sample_rate)
            self.delay_chunks = self.delay_samples // self.chunk_size + 1
            self.audio_buffer = deque(maxlen=self.delay_chunks)
            silence = np.zeros(self.chunk_size, dtype=np.float32)
            for _ in range(self.delay_chunks):
                self.audio_buffer.append(silence)
        else:
            print("✗ No common sample rate found between input and output devices")
            return False
        
        # Setup input stream (microphone) - blocking mode
        try:
            self.input_stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=input_device,
                frames_per_buffer=self.chunk_size
            )
            print("✓ Input stream initialized")
        except Exception as e:
            print(f"✗ Failed to initialize input stream: {e}")
            return False
        
        # Setup output stream (speaker) - blocking mode
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
        except Exception as e:
            print(f"✗ Failed to initialize output stream: {e}")
            return False
        
        return True
    
    def process_audio_loop(self):
        """Main audio processing loop - blocking approach"""
        print("Starting audio processing loop...")
        
        try:
            while self.running:
                # Read audio from microphone
                try:
                    input_data = self.input_stream.read(self.chunk_size, exception_on_overflow=False)
                    # Convert to numpy array
                    audio_data = np.frombuffer(input_data, dtype=np.float32)
                    
                    # Add to delay buffer
                    self.audio_buffer.append(audio_data.copy())
                    
                    # Get delayed audio from buffer
                    if len(self.audio_buffer) > 0:
                        delayed_audio = self.audio_buffer[0].copy()
                        # Apply volume control
                        delayed_audio *= self.volume
                    else:
                        delayed_audio = np.zeros(self.chunk_size, dtype=np.float32)
                    
                    # Write to speaker
                    output_data = delayed_audio.astype(np.float32).tobytes()
                    self.output_stream.write(output_data, exception_on_underflow=False)
                    
                except Exception as e:
                    if self.running:  # Only print error if we're supposed to be running
                        print(f"Audio processing error: {e}")
                    break
                    
        except KeyboardInterrupt:
            print("\nReceived interrupt in audio loop")
        finally:
            print("Audio processing loop ended")
    
    def start(self, input_device=None, output_device=None):
        """Start the audio loopback"""
        if not self.setup_streams(input_device, output_device):
            return False
        
        # Start streams
        self.input_stream.start_stream()
        self.output_stream.start_stream()
        self.running = True
        
        print(f"\n🎤 Audio loopback started!")
        print(f"📢 Speaking into the microphone will play back with {self.delay_seconds}s delay")
        print(f"🔊 Volume set to {int(self.volume * 100)}%")
        print("Press Ctrl+C to stop...")
        
        # Start audio processing in a separate thread
        import threading
        self.audio_thread = threading.Thread(target=self.process_audio_loop, daemon=True)
        self.audio_thread.start()
        
        return True
    
    def stop(self):
        """Stop the audio loopback"""
        self.running = False
        
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
        
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
        
        if self.audio:
            self.audio.terminate()
        
        print("\n🛑 Audio loopback stopped")


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\nReceived interrupt signal...")
    global loopback
    if loopback:
        loopback.stop()
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description='Audio loopback test for Raspberry Pi 5')
    parser.add_argument('--delay', type=float, default=1.0,
                       help='Delay in seconds (default: 1.0)')
    parser.add_argument('--list-devices', action='store_true',
                       help='List available audio devices and exit')
    parser.add_argument('--input-device', type=int,
                       help='Input device index (microphone)')
    parser.add_argument('--output-device', type=int,
                       help='Output device index (speaker)')
    parser.add_argument('--sample-rate', type=int, default=44100,
                       help='Sample rate in Hz (default: 44100)')
    parser.add_argument('--chunk-size', type=int, default=1024,
                       help='Audio chunk size (default: 1024)')
    parser.add_argument('--volume', type=float, default=0.5,
                       help='Output volume (0.0-1.0, default: 0.5)')
    
    args = parser.parse_args()
    
    # Validate volume
    if args.volume < 0.0 or args.volume > 1.0:
        print("Error: Volume must be between 0.0 and 1.0")
        sys.exit(1)
    
    # Create loopback instance
    global loopback
    loopback = AudioLoopback(
        delay_seconds=args.delay,
        sample_rate=args.sample_rate,
        chunk_size=args.chunk_size,
        volume=args.volume
    )
    
    # List devices if requested
    if args.list_devices:
        loopback.list_devices()
        return
    
    # Setup signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Start the loopback
        if loopback.start(args.input_device, args.output_device):
            # Keep running until interrupted
            while loopback.running:
                time.sleep(0.1)
        else:
            print("Failed to start audio loopback")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        loopback.stop()


if __name__ == "__main__":
    main()
