import os
from collections import deque
import requests
from openai import OpenAI
from dotenv import load_dotenv
from web_tools import WebTools
import json

load_dotenv()

class LLMClient:
    def __init__(self, max_history=10):
        self.provider = os.getenv('LLM_PROVIDER', 'local').lower()
        self.max_tokens = int(os.getenv('MAX_TOKENS', '500'))
        self.debug = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
        
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
        
        self.web_tools = WebTools()
        
        # Define available functions
        self.available_functions = {
            "search_web": self.web_tools.search_web,
            "get_sa_time": self.web_tools.get_sa_time
        }
        
        # Define function schemas
        self.function_schemas = [
            {
                "name": "search_web",
                "description": "Search the web for current information about any topic (including weather, news, etc)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query"
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "Number of results to return (default: 3)"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_sa_time",
                "description": "Get the current date and time",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
        
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
        """Get response from OpenAI API with function calling"""
        try:
            self.debug_print("\n[DEBUG] Sending request to OpenAI...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=self.max_tokens,
                functions=self.function_schemas,
                function_call="auto"
            )
            
            response_message = response.choices[0].message
            
            # Check if the model wants to call a function
            if response_message.function_call:
                function_name = response_message.function_call.name
                function_args = json.loads(response_message.function_call.arguments)
                
                self.debug_print(f"\n[DEBUG] Function call requested:")
                self.debug_print(f"Function: {function_name}")
                self.debug_print(f"Arguments: {json.dumps(function_args, indent=2)}")
                
                # Call the function
                function_to_call = self.available_functions[function_name]
                self.debug_print("\n[DEBUG] Executing function...")
                function_response = function_to_call(**function_args)
                
                self.debug_print("\n[DEBUG] Adding function response to conversation:")
                self.debug_print(f"Response: {function_response}")
                
                # Add function response to messages
                messages.append({
                    "role": "function",
                    "name": function_name,
                    "content": function_response
                })
                
                # Get final response from model
                self.debug_print("\n[DEBUG] Getting final response from OpenAI...")
                second_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=self.max_tokens
                )
                
                final_response = second_response.choices[0].message.content
                self.debug_print(f"\n[DEBUG] Final response: {final_response}")
                return final_response
            
            self.debug_print(f"\n[DEBUG] Direct response (no function call): {response_message.content}")
            return response_message.content
            
        except Exception as e:
            self.debug_print(f"\n[DEBUG] OpenAI API error: {e}")
            if self.debug:
                self.debug_print("[DEBUG] Full error details:")
                import traceback
                self.debug_print(traceback.format_exc())
            return None
        
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

    def debug_print(self, *args, **kwargs):
        if self.debug:
            print(*args, **kwargs) 