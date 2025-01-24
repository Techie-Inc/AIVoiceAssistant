from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import torch
import os
import numpy as np
from dotenv import load_dotenv

load_dotenv()

class SpeechToText:
    def __init__(self):
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        
        self.model_id = os.getenv('WHISPER_MODEL')
        self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
            self.model_id, 
            torch_dtype=self.torch_dtype,
            low_cpu_mem_usage=True,
            use_safetensors=True
        ).to(self.device)
        
        self.processor = AutoProcessor.from_pretrained(self.model_id)
        
        self.pipe = pipeline(
            "automatic-speech-recognition",
            model=self.model,
            tokenizer=self.processor.tokenizer,
            feature_extractor=self.processor.feature_extractor,
            torch_dtype=self.torch_dtype,
            device=self.device,
        )

    def transcribe(self, audio_array):
        try:
            # Ensure audio is the right format (single channel, float32)
            if len(audio_array.shape) > 1:
                audio_array = np.mean(audio_array, axis=1)
            
            # Convert from int16 to float32 and normalize
            if audio_array.dtype == np.int16:
                audio_array = audio_array.astype(np.float32) / 32768.0
            
            result = self.pipe(audio_array)
            return result["text"].strip()
        except Exception as e:
            print(f"Transcription error: {e}")
            return "" 