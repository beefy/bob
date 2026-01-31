#!/usr/bin/env python3
"""
Local LLM Test using GGUF models via llama-cpp-python on Raspberry Pi 5
Tests local LLM models running via llama.cpp backend for text generation.
"""

import sys
import time
import argparse
import os
from llama_cpp import Llama


class LocalLLM:
    def __init__(self, model_path=None, n_ctx=2048, n_threads=4):
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.model = None
        
        print(f"Local LLM Configuration:")
        print(f"  Model Path: {self.model_path}")
        print(f"  Context Length: {self.n_ctx}")
        print(f"  CPU Threads: {self.n_threads}")
    
    def find_model_file(self):
        """Find a GGUF model file in common locations"""
        possible_paths = [
            "./models/",
            "~/models/",
            "/home/bob/models/",
            "./"
        ]
        
        model_names = [
            "phi-3-mini-4k-instruct.q4_0.gguf",
            "phi-3-mini-4k-instruct.gguf",
            "llama-2-7b-chat.q4_0.gguf",
            "llama-2-7b-chat.gguf",
            "tinyllama-1.1b-chat-v1.0.q4_0.gguf"
        ]
        
        print("\n🔍 Searching for model files...")
        for path in possible_paths:
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path):
                for model_name in model_names:
                    full_path = os.path.join(expanded_path, model_name)
                    if os.path.exists(full_path):
                        print(f"✅ Found model: {full_path}")
                        return full_path
        
        print("❌ No model files found in common locations")
        print("\nTo download a model:")
        print("  mkdir -p ~/models")
        print("  cd ~/models")
        print("  # Download a small model (TinyLlama ~600MB):")
        print("  wget https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.q4_0.gguf")
        print("  # Or download Phi-3-mini (~2.4GB):")
        print("  wget https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf")
        
        return None
    
    def load_model(self):
        """Load the GGUF model"""
        print("🔄 Loading model... (this may take a few minutes)")
        start_time = time.time()
        
        # Find model if not specified
        if self.model_path is None:
            self.model_path = self.find_model_file()
            if self.model_path is None:
                return False
        
        try:
            self.model = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                verbose=False,  # Reduce output noise
                use_mmap=True,
                use_mlock=False  # Don't lock memory on Pi
            )
            
            load_time = time.time() - start_time
            print(f"✅ Model loaded successfully in {load_time:.1f} seconds")
            return True
            
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            print("This may be due to:")
            print("  1. Corrupted model file - try re-downloading")
            print("  2. Incompatible GGUF version - try a different quantization")
            print("  3. Insufficient RAM - try a smaller model")
            return False
    
    def generate_response(self, prompt, max_tokens=256, temperature=0.7, stop=None):
        """Generate a response using the loaded model"""
        if self.model is None:
            print("❌ Model not loaded. Call load_model() first.")
            return None
        
        print(f"🤔 Generating response for: \"{prompt[:50]}...\"")
        start_time = time.time()
        
        try:
            # Format prompt - simple format for compatibility
            formatted_prompt = f"User: {prompt}\nAssistant: "
            
            # Generate response
            output = self.model(
                formatted_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop or ["User:", "\n\n"],
                echo=False
            )
            
            response = output['choices'][0]['text'].strip()
            
            generation_time = time.time() - start_time
            tokens_generated = output['usage']['completion_tokens']
            tokens_per_second = tokens_generated / generation_time if generation_time > 0 else 0
            
            print(f"⚡ Generated {tokens_generated} tokens in {generation_time:.1f}s ({tokens_per_second:.1f} tokens/s)")
            
            return response
            
        except Exception as e:
            print(f"❌ Error generating response: {e}")
            return None
    
    def chat_loop(self):
        """Interactive chat loop"""
        print("\n💬 Interactive chat mode. Type 'quit' to exit.")
        print("Ask me anything!")
        
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("👋 Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                response = self.generate_response(user_input)
                
                if response:
                    print(f"🤖 Bob: {response}")
                else:
                    print("😕 Sorry, I couldn't generate a response.")
                    
            except KeyboardInterrupt:
                print("\n👋 Chat interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error in chat: {e}")


def main():
    parser = argparse.ArgumentParser(description='Local LLM test using GGUF models on Raspberry Pi')
    parser.add_argument('--prompt', type=str, 
                       default="How many R's are in the word strawberry?",
                       help='Single prompt to test (default: R counting question)')
    parser.add_argument('--chat', action='store_true',
                       help='Start interactive chat mode')
    parser.add_argument('--model-path', type=str,
                       help='Path to GGUF model file')
    parser.add_argument('--max-tokens', type=int, default=256,
                       help='Maximum response tokens (default: 256)')
    parser.add_argument('--temperature', type=float, default=0.7,
                       help='Generation temperature (default: 0.7)')
    parser.add_argument('--threads', type=int, default=4,
                       help='CPU threads to use (default: 4)')
    
    args = parser.parse_args()
    
    # Create LLM instance
    llm = LocalLLM(model_path=args.model_path, n_threads=args.threads)
    
    # Load model
    if not llm.load_model():
        sys.exit(1)
    
    try:
        if args.chat:
            # Interactive chat mode
            llm.chat_loop()
        else:
            # Single prompt mode
            print(f"\n🔍 Testing with prompt: '{args.prompt}'")
            response = llm.generate_response(
                args.prompt, 
                max_tokens=args.max_tokens,
                temperature=args.temperature
            )
            
            if response:
                print(f"\n🤖 Response:")
                print(f"{response}")
                print("\n✅ Test completed successfully!")
            else:
                print("❌ Test failed - no response generated")
                sys.exit(1)
                
    except KeyboardInterrupt:
        print("\n👋 Test interrupted")
    except Exception as e:
        print(f"❌ Error during test: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

