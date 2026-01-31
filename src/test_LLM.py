#!/usr/bin/env python3
"""
Local LLM Test using Phi-3-mini on Raspberry Pi 5
Tests the Microsoft Phi-3-mini model running locally for text generation.
"""

import sys
import time
import argparse
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch


class LocalLLM:
    def __init__(self, model_name="microsoft/Phi-3-mini-4k-instruct", max_memory_gb=6):
        self.model_name = model_name
        self.max_memory_gb = max_memory_gb
        self.tokenizer = None
        self.model = None
        self.device = "cpu"  # Use CPU for Raspberry Pi
        
        print(f"Local LLM Configuration:")
        print(f"  Model: {self.model_name}")
        print(f"  Device: {self.device}")
        print(f"  Max Memory: {self.max_memory_gb}GB")
    
    def load_model(self):
        """Load the Phi-3-mini model and tokenizer"""
        print("🔄 Loading model... (this may take several minutes)")
        start_time = time.time()
        
        try:
            # Load tokenizer
            print("Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            
            # Load model with simplified parameters for Raspberry Pi
            print("Loading model (this is the slow part)...")
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                low_cpu_mem_usage=True,
                torch_dtype=torch.float32  # Explicit float32 for CPU
            )
            
            # Move model to CPU explicitly
            self.model = self.model.to('cpu')
            
            # Set pad token if not present
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            load_time = time.time() - start_time
            print(f"✅ Model loaded successfully in {load_time:.1f} seconds")
            
            # Print model info
            try:
                num_params = sum(p.numel() for p in self.model.parameters())
                print(f"📊 Model parameters: {num_params:,}")
            except:
                print("📊 Model loaded (parameter count unavailable)")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            print(f"Error type: {type(e).__name__}")
            
            # Try alternative loading method
            print("🔄 Trying alternative loading method...")
            try:
                # Simplified loading without device_map
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    trust_remote_code=True
                )
                self.model = self.model.to('cpu')
                print("✅ Model loaded with alternative method")
                return True
            except Exception as e2:
                print(f"❌ Alternative loading also failed: {e2}")
                return False
    
    def generate_response(self, prompt, max_length=512, temperature=0.7, do_sample=True):
        """Generate a response using the loaded model"""
        if self.model is None or self.tokenizer is None:
            print("❌ Model not loaded. Call load_model() first.")
            return None
        
        print(f"🤔 Generating response for: \"{prompt}\"")
        start_time = time.time()
        
        try:
            # Format prompt for Phi-3 chat format
            formatted_prompt = f"<|user|>\\n{prompt}<|end|>\\n<|assistant|>\\n"
            
            # Tokenize input
            inputs = self.tokenizer.encode(
                formatted_prompt,
                return_tensors="pt",
                truncation=True,
                max_length=max_length - 100  # Leave room for response
            )
            
            # Generate response
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_length=max_length,
                    temperature=temperature,
                    do_sample=do_sample,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    num_return_sequences=1,
                    repetition_penalty=1.1
                )
            
            # Decode response
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract just the assistant's response
            if "<|assistant|>" in response:
                response = response.split("<|assistant|>")[-1].strip()
            else:
                # Fallback - remove the original prompt
                response = response.replace(formatted_prompt, "").strip()
            
            generation_time = time.time() - start_time
            tokens_generated = len(outputs[0]) - len(inputs[0])
            tokens_per_second = tokens_generated / generation_time if generation_time > 0 else 0
            
            print(f"⚡ Generated {tokens_generated} tokens in {generation_time:.1f}s ({tokens_per_second:.1f} tokens/s)")
            
            return response
            
        except Exception as e:
            print(f"❌ Error generating response: {e}")
            return None
    
    def chat_loop(self):
        """Interactive chat loop"""
        print("\\n💬 Interactive chat mode. Type 'quit' to exit.")
        print("Ask me anything!")
        
        while True:
            try:
                user_input = input("\\n👤 You: ").strip()
                
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
                print("\\n👋 Chat interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error in chat: {e}")


def main():
    parser = argparse.ArgumentParser(description='Local LLM test using Phi-3-mini on Raspberry Pi')
    parser.add_argument('--prompt', type=str, 
                       default="How many R's are in the word strawberry?",
                       help='Single prompt to test (default: R counting question)')
    parser.add_argument('--chat', action='store_true',
                       help='Start interactive chat mode')
    parser.add_argument('--model', type=str,
                       default="microsoft/Phi-3-mini-4k-instruct",
                       help='Model name to use')
    parser.add_argument('--max-memory', type=int, default=6,
                       help='Maximum memory in GB (default: 6)')
    parser.add_argument('--max-length', type=int, default=512,
                       help='Maximum response length (default: 512)')
    parser.add_argument('--temperature', type=float, default=0.7,
                       help='Generation temperature (default: 0.7)')
    
    args = parser.parse_args()
    
    # Create LLM instance
    llm = LocalLLM(model_name=args.model, max_memory_gb=args.max_memory)
    
    # Load model
    if not llm.load_model():
        sys.exit(1)
    
    try:
        if args.chat:
            # Interactive chat mode
            llm.chat_loop()
        else:
            # Single prompt mode
            print(f"\\n🔍 Testing with prompt: '{args.prompt}'")
            response = llm.generate_response(
                args.prompt, 
                max_length=args.max_length,
                temperature=args.temperature
            )
            
            if response:
                print(f"\\n🤖 Response:")
                print(f"{response}")
                print("\\n✅ Test completed successfully!")
            else:
                print("❌ Test failed - no response generated")
                sys.exit(1)
                
    except KeyboardInterrupt:
        print("\\n👋 Test interrupted")
    except Exception as e:
        print(f"❌ Error during test: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

