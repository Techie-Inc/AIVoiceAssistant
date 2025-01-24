from TTS.api import TTS
import os
from dotenv import load_dotenv
import torch
from pydub import AudioSegment
import tempfile
import re

load_dotenv()

class TextToSpeech:
    def __init__(self):
        self.model = TTS(
            model_name=os.getenv('XTTS_MODEL'),
            gpu=torch.cuda.is_available()
        )
        self.reference_voice = self._sanitize_path(os.getenv('REFERENCE_VOICE_PATH'))
        print(f"Loading reference voice from: {self.reference_voice}")
        
    def _sanitize_path(self, path):
        """Clean and normalize the file path for Windows"""
        if path is None:
            raise ValueError("Reference voice path is not set in .env file")
            
        # Remove quotes if present
        path = path.strip('"\'')
        
        # Convert to raw string to handle Windows paths
        path = path.replace('\\', '\\\\')
        
        # Verify file exists
        if not os.path.exists(path):
            raise FileNotFoundError(f"Reference voice file not found: {path}")
            
        return path

    def speak(self, text, output_path="output.wav"):
        try:
            self.model.tts_to_file(
                text=text,
                file_path=output_path,
                speaker_wav=self.reference_voice,
                language="en"
            )
            return output_path
        except Exception as e:
            print(f"TTS error: {e}")
            print(f"Attempted to use reference voice: {self.reference_voice}")
            return None

    def __del__(self):
        """Cleanup temporary files when the object is destroyed."""
        if hasattr(self, 'temp_wav_path') and os.path.exists(self.temp_wav_path):
            try:
                os.remove(self.temp_wav_path)
            except Exception as e:
                print(f"Error cleaning up temporary file: {e}") 