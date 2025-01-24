import queue
import threading
import sounddevice as sd
import numpy as np
import webrtcvad
from scipy import signal
import os
from dotenv import load_dotenv

load_dotenv()

class AudioRecorder:
    def __init__(self):
        self.sample_rate = int(os.getenv('SAMPLE_RATE'))
        self.vad = webrtcvad.Vad(3)  # Aggressiveness level 3
        self.frame_duration = int(os.getenv('VAD_FRAME_DURATION'))
        self.buffer = queue.Queue()
        self.recording = False
        self.audio_data = []
        self.silence_threshold = float(os.getenv('SILENCE_THRESHOLD'))
        self.min_speech_duration = float(os.getenv('MIN_SPEECH_DURATION'))
        self.silence_duration = float(os.getenv('SILENCE_DURATION'))
        print(f"AudioRecorder initialized with settings:")
        print(f"Sample rate: {self.sample_rate}")
        print(f"VAD frame duration: {self.frame_duration}")
        print(f"Silence threshold: {self.silence_threshold}")
        print(f"Min speech duration: {self.min_speech_duration}")
        print(f"Silence duration: {self.silence_duration}")
        
    def callback(self, indata, frames, time, status):
        if status:
            print(f"Status: {status}")
        # Ensure single channel by taking mean across channels if stereo
        if len(indata.shape) > 1 and indata.shape[1] > 1:
            indata = np.mean(indata, axis=1, keepdims=True)
        self.buffer.put(indata.copy())
        # Print audio levels for debugging
        audio_level = np.abs(indata).mean()
        #if audio_level > 0.01:  # Only print if there's significant audio
            #print(f"Audio level: {audio_level:.4f}")

    def is_speech(self, audio_frame):
        try:
            is_speech_frame = self.vad.is_speech(audio_frame.tobytes(), self.sample_rate)
            if is_speech_frame:
                print("X", end="", flush=True)  # Visual indicator of speech
            return is_speech_frame
        except Exception as e:
            print(f"Error in VAD processing: {e}")
            return False

    def record_until_silence(self):
        print("\nListening...")
        self.recording = True
        self.audio_data = []
        silence_counter = 0
        speech_detected = False
        
        try:
            with sd.InputStream(callback=self.callback,
                              channels=1,  # Force single channel
                              samplerate=self.sample_rate,
                              dtype=np.int16,
                              device=None,  # Use default device
                              blocksize=int(self.sample_rate * self.frame_duration / 1000)):
                
                while self.recording:
                    try:
                        audio_chunk = self.buffer.get(timeout=1.0)  # 1 second timeout
                        self.audio_data.append(audio_chunk)
                        
                        # Check for speech in the current frame
                        is_speech_frame = self.is_speech(audio_chunk)
                        
                        if is_speech_frame:
                            speech_detected = True
                            silence_counter = 0
                        elif speech_detected:
                            silence_counter += len(audio_chunk) / self.sample_rate
                            print(".", end="", flush=True)  # Visual indicator of silence
                            
                            if silence_counter >= self.silence_duration:
                                print("\nSpeech complete.")
                                self.recording = False
                                
                    except queue.Empty:
                        continue
                    
        except Exception as e:
            print(f"\nError in recording: {e}")
            return None
                
        if self.audio_data:
            # Ensure single channel output
            audio_data = np.concatenate(self.audio_data)
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
            return audio_data
        else:
            return None

    def stop(self):
        self.recording = False 