import os
import queue
import socket
import struct
import threading
import wave

import torch
import numpy as np
from TTS.api import TTS
from silero_vad import load_silero_vad
from whisppy import transcriber
from transport import listen_for_client_audio

from src.message_sender import send_audio_message
from src.voice_detector import VoiceDetector
from src.command_runner import run_command

# Backus–Naur form grammar for commands
# https://en.wikipedia.org/wiki/Backus%E2%80%93Naur_form
GRAMMAR = """
root ::= "Hey Hans, set a " duration " timer."
duration ::= number " " ("second" | "minute" | "hour") (" and " number " hour")?
number ::= [0-9] [0-9]? [0-9]?
"""

GRAMMAR_ROOT = "root"

# Transcription examples for expected voice commands
# Used by whispercpp to guide transcription
# https://github.com/ggerganov/whisper.cpp/blob/cadfc50eabb46829a0d5ac7ffcb3778ad60a1257/include/whisper.h#L516
INITIAL_PROMPT = """
Hey Hans, set a 5 minute timer.
Hey Hans, set a 15 hour and 3 minute timer.
"""

def write_audio(frames):
    channels = 1
    with wave.open('testing.wav', 'wb') as f:
        f.setnchannels(channels)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.writeframes(frames)
        

def main():
    local_addr = '0.0.0.0'
    local_port = int(os.environ['SERVER_PORT'])
    stt_model_file = os.environ['STT_MODEL_FILE']

    vad_model = load_silero_vad()
    voice_detector = VoiceDetector(vad_model)

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    tts_model = 'tts_models/en/jenny/jenny'
    tts = TTS(tts_model).to(device)

    frames = bytearray()

    num_voiceless_frames_seen = 0

    message_q = queue.Queue()
    sender_t = threading.Thread(target=send_audio_message, args=[message_q, tts], daemon=True)
    sender_t.start()


    with transcriber(stt_model_file, GRAMMAR) as t:
        print('Server ready')
        for packet in listen_for_client_audio(local_addr, local_port):
            audio_bytes = packet.audio_bytes
            #TODO: Collect frames until we have enough, don't assume a frame is perfect
            # OR MAYBE DO?!?!?
            frame_is_voice = voice_detector.big_chunk_is_voice(audio_bytes)
            if frame_is_voice:
                num_voiceless_frames_seen = 0
            else:
                num_voiceless_frames_seen += 1

            if frame_is_voice or (frames and num_voiceless_frames_seen < 5):
                frames.extend(audio_bytes)

            if not frame_is_voice and num_voiceless_frames_seen > 5 and frames:
                print('decided to transcribe')
                audio_data = np.frombuffer(frames, np.int16).astype(np.float32) / np.iinfo(np.int16).max
                # Make the audio at least one second long
                audio_data = np.concatenate((audio_data, np.zeros((int(16000) + 10))), dtype=np.float32)
                text = t.transcribe(audio_data, initial_prompt=INITIAL_PROMPT, grammar_rule=GRAMMAR_ROOT)
                run_command(text, message_q, packet.sender_addr)
                frames = bytearray()


if __name__ == '__main__':
    main()
