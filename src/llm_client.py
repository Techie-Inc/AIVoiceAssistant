import os
from collections import deque
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class LLMClient:
    def __init__(self, max_history=10):
        self.provider = os.getenv('LLM_PROVIDER', 'local').lower()
        self.max_tokens = int(os.getenv('MAX_TOKENS', '500'))
        
        if self.provider == 'openai':
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        else:  # local
            self.api_url = os.getenv('LM_STUDIO_API_URL')
            self.api_key = os.getenv('LM_STUDIO_API_KEY')
            
        self.conversation_history = deque(maxlen=max_history)
        self.system_prompt = self._load_system_prompt()
        
        print(f"Using LLM provider: {self.provider}")
        print(f"Max tokens: {self.max_tokens}")
        
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
            
            # Get response based on provider
            if self.provider == 'openai':
                assistant_response = self._get_openai_response(messages)
            else:
                assistant_response = self._get_local_response(messages)
            
            if assistant_response:
                # Update conversation history
                self.conversation_history.append({"role": "user", "content": prompt})
                self.conversation_history.append({"role": "assistant", "content": assistant_response})
            
            return assistant_response
                
        except Exception as e:
            print(f"LLM error: {e}")
            return None
            
    def _get_openai_response(self, messages):
        """Get response from OpenAI API"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=self.max_tokens
        )
        return response.choices[0].message.content
        
    def _get_local_response(self, messages):
        """Get response from local LM Studio API"""
        response = requests.post(
            f"{self.api_url}/chat/completions",
            headers={
                "Content-Type": "application/json",
            },
            json={
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": self.max_tokens,
            }
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            print(f"Error: {response.status_code}")
            return None
            
    def clear_history(self):
        """Clear the conversation history"""
        self.conversation_history.clear() 