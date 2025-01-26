import os
import time
import sounddevice as sd
import soundfile as sf
from dotenv import load_dotenv
from audio_recorder import AudioRecorder
from speech_to_text import SpeechToText
from text_to_speech import TextToSpeech
from llm_client import LLMClient

load_dotenv()

class VoiceAssistant:
    def __init__(self):
        self.recorder = AudioRecorder()
        self.stt = SpeechToText()
        self.tts = TextToSpeech()
        self.llm = LLMClient(max_history=10)
        
        # Define multiple wake words/phrases
        self.wake_words = [
            "jarvis",
            "javis",  
            "travis",  
            "service",    
            "drivers",
            "jobbers",
            "james",
            "thomas",
            "jalvis",
        ]
        
        self.conversation_timeout = 20  # seconds
        self.last_response_time = 0
        self.in_conversation = False
        self.debug = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
        
    def debug_print(self, *args, **kwargs):
        if self.debug:
            print(*args, **kwargs)

    def check_wake_word(self, text):
        """Check if any wake word is present in text"""
        text_lower = text.lower()
        for wake_word in self.wake_words:
            if wake_word in text_lower:
                self.debug_print(f"\n[DEBUG] Wake word detected: '{wake_word}'")
                return wake_word
        return None

    def remove_wake_word(self, text, detected_wake_word):
        """Remove the detected wake word from the text"""
        return text.lower().replace(detected_wake_word, '').strip()

    def is_conversation_active(self):
        """Check if we're within the conversation timeout window"""
        if not self.in_conversation:
            return False
        
        time_since_last_response = time.time() - self.last_response_time
        if time_since_last_response > self.conversation_timeout:
            self.debug_print("\n[DEBUG] Conversation timeout reached")
            self.in_conversation = False
            return False
            
        return True

    def play_audio(self, file_path):
        """Play audio file using sounddevice"""
        try:
            # Load the audio file
            data, samplerate = sf.read(file_path)
            # Play the audio
            sd.play(data, samplerate)
            sd.wait()  # Wait until the audio is finished playing
        except Exception as e:
            print(f"Error playing audio: {e}")
        
    def handle_commands(self, text):
        """Handle special commands"""
        text_lower = text.lower().strip()
        
        if text_lower == "clear memory" or text_lower == "clear history":
            self.llm.clear_history()
            return "Conversation history has been cleared."
        elif text_lower == "show history" or text_lower == "show memory":
            if not self.llm.conversation_history:
                return "No conversation history available."
            
            history = "\n".join([
                f"{'You' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                for msg in self.llm.conversation_history
            ])
            return f"Here's our conversation history:\n{history}"
            
        return None
        
    def run(self):
        print("\n" + "="*50)
        print("Voice Assistant is ready! Speak to begin...")
        print("Special commands:")
        print("- 'Clear memory': Clears conversation history")
        print("- 'Show history': Shows recent conversation history")
        print("\nMicrophone Settings:")
        print(f"Using device: {sd.default.device}")
        print(f"Available devices:")
        for i, dev in enumerate(sd.query_devices()):
            print(f"{i}: {dev['name']}")
        print("="*50 + "\n")
        
        while True:
            try:
                print("\nListening for speech...")
                audio_data = self.recorder.record_until_silence()
                
                if audio_data is not None and len(audio_data) > 0:
                    print("\nTranscribing speech...")
                    text = self.stt.transcribe(audio_data)
                    
                    if text:
                        self.debug_print(f"\n[DEBUG] Transcribed text: {text}")
                        
                        # Check if we need wake word
                        if not self.is_conversation_active():
                            detected_wake_word = self.check_wake_word(text)
                            if not detected_wake_word:
                                self.debug_print("\n[DEBUG] Wake word not detected")
                                continue
                        
                        # If wake word detected, start conversation
                        detected_wake_word = self.check_wake_word(text)
                        if detected_wake_word and not self.is_conversation_active():
                            self.debug_print("\n[DEBUG] Starting conversation")
                            self.in_conversation = True
                            # Remove wake word from text
                            text = self.remove_wake_word(text, detected_wake_word)
                            if not text:  # If only wake word was spoken
                                self.debug_print("\n[DEBUG] Only wake word was spoken")
                                output_path = self.tts.speak("Yes, Sir?")
                                if output_path:
                                    self.play_audio(output_path)
                                self.last_response_time = time.time()
                                continue

                        print(f"\nYou said: {text}")
                        
                        # Check for special commands
                        command_response = self.handle_commands(text)
                        if command_response:
                            print(f"\nAssistant: {command_response}")
                            output_path = self.tts.speak(command_response)
                            if output_path:
                                print("\nPlaying response...")
                                self.play_audio(output_path)
                            continue
                        
                        # Get response from LLM
                        print("\nGetting AI response...")
                        response = self.llm.get_response(text)
                        
                        if response:
                            print(f"\nAssistant: {response}")
                            
                            # Convert response to speech
                            print("\nGenerating speech...")
                            output_path = self.tts.speak(response)
                            
                            if output_path:
                                # Play the response
                                print("\nPlaying response...")
                                self.play_audio(output_path)
                                # Update conversation timeout
                                self.last_response_time = time.time()
                                self.in_conversation = True
                        else:
                            print("\nError getting response")
                            self.tts.speak("I apologize, but I encountered an error processing your request.")
                            self.last_response_time = time.time()
                else:
                    print("No speech detected in audio")
                
            except KeyboardInterrupt:
                print("\nStopping Voice Assistant...")
                break
            except Exception as e:
                print(f"\nError in main loop: {e}")
                continue

if __name__ == "__main__":
    assistant = VoiceAssistant()
    assistant.run() 