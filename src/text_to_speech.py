import os
from google.cloud import texttospeech
from dotenv import load_dotenv
import base64

load_dotenv()

class TextToSpeech:
    def __init__(self):
        # Initialize Google Cloud client
        self.client = texttospeech.TextToSpeechClient()
        
        # Configure voice settings
        self.voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Standard-A"
        )
        
        # Configure audio settings
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16
        )

    def speak(self, text, output_path="output.wav"):
        try:
            # Set the text input to be synthesized
            synthesis_input = texttospeech.SynthesisInput(text=text)

            # Perform the text-to-speech request
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=self.voice,
                audio_config=self.audio_config
            )

            # Write the response to the output file
            with open(output_path, "wb") as out:
                out.write(response.audio_content)
                
            return output_path
            
        except Exception as e:
            print(f"TTS error: {e}")
            return None

    def __del__(self):
        """Cleanup when the object is destroyed."""
        if hasattr(self, 'temp_wav_path') and os.path.exists(self.temp_wav_path):
            try:
                os.remove(self.temp_wav_path)
            except Exception as e:
                print(f"Error cleaning up temporary file: {e}") 