import os
import subprocess
from dotenv import load_dotenv
import tempfile

load_dotenv()

class TextToSpeech:
    def __init__(self):
        self.piper_exe = self._sanitize_path(os.getenv('PIPER_EXE_PATH'))
        self.model_path = self._sanitize_path(os.getenv('PIPER_MODEL_PATH'))
        print(f"Using Piper executable: {self.piper_exe}")
        print(f"Using Piper model: {self.model_path}")
        
        # Verify piper executable exists and is runnable
        self._verify_piper()
        
    def _verify_piper(self):
        """Verify piper executable exists and can run"""
        if not os.path.exists(self.piper_exe):
            raise FileNotFoundError(f"Piper executable not found: {self.piper_exe}")
            
        try:
            # Test piper with --help command
            result = subprocess.run([self.piper_exe, '--help'], 
                                 capture_output=True, 
                                 text=True)
            if result.returncode != 0:
                raise RuntimeError(f"Piper test failed: {result.stderr}")
        except Exception as e:
            raise RuntimeError(f"Failed to run piper executable: {e}")
        
    def _sanitize_path(self, path):
        """Clean and normalize the file path for Windows"""
        if path is None:
            raise ValueError("Path not set in .env file")
            
        # Remove quotes if present
        path = path.strip('"\'')
        
        # Convert to raw string to handle Windows paths
        path = path.replace('\\', '\\\\')
        
        return path

    def speak(self, text, output_path="output.wav"):
        try:
            # Build the piper command
            cmd = [
                self.piper_exe,
                '-m', self.model_path,
                '-f', output_path
            ]

            # Run piper with text piped to stdin
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Send text to piper's stdin and get output
            stdout, stderr = process.communicate(input=text)
            
            if process.returncode != 0:
                raise RuntimeError(f"Piper failed: {stderr}")
            
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