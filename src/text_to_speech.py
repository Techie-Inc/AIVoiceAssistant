import os
import re
from google.cloud import texttospeech
from dotenv import load_dotenv
import base64

load_dotenv()

class TextToSpeech:
    def __init__(self):
        # Initialize Google Cloud client
        self.client = texttospeech.TextToSpeechClient()
        
        # Get voice settings from environment
        self.language = os.getenv('GOOGLE_TTS_LANGUAGE', 'en-GB')
        self.voice = os.getenv('GOOGLE_TTS_VOICE', 'en-GB-Standard-D')
        self.debug = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
        
        # Configure voice settings
        self.voice_selection = texttospeech.VoiceSelectionParams(
            language_code=self.language,
            name=self.voice
        )
        
        print(f"Using Google TTS with voice: {self.voice} ({self.language})")
        
        # Configure audio settings
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16
        )

        # Ensure output directory exists
        self.output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
        os.makedirs(self.output_dir, exist_ok=True)

    def debug_print(self, *args, **kwargs):
        if self.debug:
            print(*args, **kwargs)

    def extract_speech_text(self, text):
        """Extract text to be spoken, handling think wrapper if present"""
        # Check for think wrapper
        think_pattern = r'<think>(.*?)</think>'
        think_matches = re.findall(think_pattern, text, re.DOTALL)
        
        if think_matches:
            # Remove all think sections and get remaining text
            speech_text = text
            for think_section in think_matches:
                speech_text = speech_text.replace(f'<think>{think_section}</think>', '')
            
            # Clean up any extra whitespace
            speech_text = re.sub(r'\s+', ' ', speech_text).strip()
            
            self.debug_print("\n[DEBUG] Found think wrapper")
            self.debug_print(f"[DEBUG] Original text length: {len(text)}")
            self.debug_print(f"[DEBUG] Speech text length: {len(speech_text)}")
            
            return speech_text
        else:
            # No think wrapper, use entire text
            self.debug_print("\n[DEBUG] No think wrapper found, using full text")
            return text.strip()

    def speak(self, text):
        """Convert text to speech using Google Cloud TTS"""
        try:
            # Extract text to be spoken
            speech_text = self.extract_speech_text(text)
            
            if not speech_text:
                self.debug_print("\n[DEBUG] No text to speak after processing")
                return None
                
            self.debug_print(f"\n[DEBUG] Converting to speech: {speech_text}")
            
            # Set the text input to be synthesized
            synthesis_input = texttospeech.SynthesisInput(text=speech_text)

            # Perform the text-to-speech request
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=self.voice_selection,
                audio_config=self.audio_config
            )

            # Save the audio file
            output_path = os.path.join(self.output_dir, 'output.wav')
            with open(output_path, 'wb') as out:
                out.write(response.audio_content)
                
            self.debug_print(f"[DEBUG] Audio saved to: {output_path}")
            return output_path

        except Exception as e:
            self.debug_print(f"\n[DEBUG] TTS error: {e}")
            if self.debug:
                import traceback
                self.debug_print(traceback.format_exc())
            return None

    def __del__(self):
        """Cleanup when the object is destroyed."""
        if hasattr(self, 'temp_wav_path') and os.path.exists(self.temp_wav_path):
            try:
                os.remove(self.temp_wav_path)
            except Exception as e:
                print(f"Error cleaning up temporary file: {e}") 