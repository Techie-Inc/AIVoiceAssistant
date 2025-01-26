import os
from collections import deque
import requests
from openai import OpenAI
from dotenv import load_dotenv
from web_tools import WebTools
import json
import traceback

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

    def debug_print(self, *args, **kwargs):
        if self.debug:
            print(*args, **kwargs)

    def _load_system_prompt(self):
        """Load the system prompt from file"""
        try:
            prompt_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'system_prompt.txt')
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            print(f"Error loading system prompt: {e}")
            return "You are a helpful AI assistant."

    def _make_llm_call(self, messages, include_functions=True):
        """Make a call to the LLM (either OpenAI or local)"""
        try:
            self.debug_print(f"\n[DEBUG] Sending request to {self.provider} LLM...")
            
            if self.provider == 'openai':
                # Prepare OpenAI request
                kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": self.max_tokens
                }
                if include_functions:
                    kwargs.update({
                        "functions": self.function_schemas,
                        "function_call": "auto"
                    })
                response = self.client.chat.completions.create(**kwargs)
                return response.choices[0].message
                
            else:  # local
                # Prepare local LLM request
                request_data = {
                    "model": "local-model",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": self.max_tokens,
                    "stream": False,
                    "tools": [
                        {
                            "type": "function",
                            "function": schema
                        } for schema in self.function_schemas
                    ] if include_functions else None,
                    "tool_choice": "auto" if include_functions else "none"
                }
                
                self.debug_print("\n[DEBUG] Local LLM request data:")
                self.debug_print(json.dumps(request_data, indent=2))
                
                response = requests.post(
                    f"{self.api_url}/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
                    },
                    json=request_data
                )
                
                if response.status_code != 200:
                    self.debug_print(f"\n[DEBUG] Error from LLM: {response.status_code}")
                    self.debug_print(f"Response: {response.text}")
                    return None
                
                response_data = response.json()
                self.debug_print("\n[DEBUG] Local LLM response data:")
                self.debug_print(json.dumps(response_data, indent=2))
                
                # Handle tool calls (function calls)
                message = response_data['choices'][0]['message']
                if 'tool_calls' in message:  # Convert tool_calls to function_call format
                    tool_call = message['tool_calls'][0]
                    message['function_call'] = {
                        'name': tool_call['function']['name'],
                        'arguments': tool_call['function']['arguments']
                    }
                
                return message
                
        except Exception as e:
            self.debug_print(f"\n[DEBUG] LLM error: {e}")
            self.debug_print(traceback.format_exc())
            return None

    def _handle_function_call(self, response_message, messages):
        """Handle function calling for both providers"""
        try:
            # Extract function call details
            if self.provider == 'openai':
                # Check if function_call exists and has required attributes
                if not hasattr(response_message, 'function_call'):
                    self.debug_print("\n[DEBUG] No function call in response")
                    return response_message.content
                    
                function_name = response_message.function_call.name
                function_args = json.loads(response_message.function_call.arguments)
            else:
                if 'function_call' not in response_message:
                    self.debug_print("\n[DEBUG] No function call in response")
                    return response_message['content']
                    
                function_name = response_message['function_call']['name']
                function_args = json.loads(response_message['function_call']['arguments'])
            
            self.debug_print(f"\n[DEBUG] Function call requested:")
            self.debug_print(f"Function: {function_name}")
            self.debug_print(f"Arguments: {json.dumps(function_args, indent=2)}")
            
            # Call the function
            function_to_call = self.available_functions[function_name]
            self.debug_print("\n[DEBUG] Executing function...")
            function_response = function_to_call(**function_args)
            
            self.debug_print("\n[DEBUG] Adding function response to conversation:")
            self.debug_print(f"Response: {function_response}")
            
            # Add function response to messages with appropriate role
            if self.provider == 'openai':
                messages.append({
                    "role": "function",
                    "name": function_name,
                    "content": function_response
                })
            else:
                messages.append({
                    "role": "tool",  # Use 'tool' role for local LLM
                    "name": function_name,
                    "content": function_response
                })
            
            # Get final response
            self.debug_print("\n[DEBUG] Getting final response from LLM...")
            final_message = self._make_llm_call(messages, include_functions=False)
            
            if not final_message:
                return None
                
            final_response = final_message.content if self.provider == 'openai' else final_message['content']
            self.debug_print(f"\n[DEBUG] Final response: {final_response}")
            return final_response
            
        except Exception as e:
            self.debug_print(f"\n[DEBUG] Function handling error: {e}")
            self.debug_print(traceback.format_exc())
            return None

    def get_response(self, prompt):
        """Get response from LLM with function calling support"""
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
            
            # Get initial response
            response_message = self._make_llm_call(messages)
            if not response_message:
                self.debug_print("\n[DEBUG] No response from LLM")
                return "I apologize, but I encountered an error processing your request."
            
            # Check for function call
            has_function_call = (
                (self.provider == 'openai' and hasattr(response_message, 'function_call') and response_message.function_call is not None) or
                (self.provider == 'local' and 'function_call' in response_message and response_message['function_call'] is not None)
            )
            
            if has_function_call:
                assistant_response = self._handle_function_call(response_message, messages)
                if not assistant_response:
                    self.debug_print("\n[DEBUG] Error in function handling")
                    return "I apologize, but I encountered an error while processing the function call."
            else:
                assistant_response = response_message.content if self.provider == 'openai' else response_message['content']
                self.debug_print(f"\n[DEBUG] Direct response (no function call): {assistant_response}")
            
            if assistant_response:
                # Update conversation history
                self.conversation_history.append({"role": "user", "content": prompt})
                self.conversation_history.append({"role": "assistant", "content": assistant_response})
            
            return assistant_response
                
        except Exception as e:
            self.debug_print(f"\n[DEBUG] Error in get_response: {e}")
            self.debug_print(traceback.format_exc())
            return "I apologize, but I encountered an error processing your request."

    def clear_history(self):
        """Clear the conversation history"""
        self.conversation_history.clear() 