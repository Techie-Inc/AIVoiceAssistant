import requests
import os
from dotenv import load_dotenv
from collections import deque

load_dotenv()

class LLMClient:
    def __init__(self, max_history=10):
        self.api_url = os.getenv('LM_STUDIO_API_URL')
        self.api_key = os.getenv('LM_STUDIO_API_KEY')
        self.conversation_history = deque(maxlen=max_history)
        self.system_prompt = self._load_system_prompt()
        
    def _load_system_prompt(self):
        """Load the system prompt from file"""
        try:
            prompt_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'system_prompt.txt')
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            print(f"Error loading system prompt: {e}")
            return "You are a helpful AI assistant."
        
    def get_response(self, prompt):
        try:
            # Build messages with conversation history
            messages = [
                {"role": "system", "content": self.system_prompt}
            ]
            
            # Add conversation history
            for msg in self.conversation_history:
                messages.append(msg)
                
            # Add current prompt
            messages.append({"role": "user", "content": prompt})
            
            response = requests.post(
                f"{self.api_url}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                },
                json={
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 500,
                }
            )
            
            if response.status_code == 200:
                assistant_response = response.json()['choices'][0]['message']['content']
                
                # Update conversation history
                self.conversation_history.append({"role": "user", "content": prompt})
                self.conversation_history.append({"role": "assistant", "content": assistant_response})
                
                return assistant_response
            else:
                print(f"Error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"LLM error: {e}")
            return None
            
    def clear_history(self):
        """Clear the conversation history"""
        self.conversation_history.clear() 