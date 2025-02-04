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

from src.message_sender import send_audio_message
from src.voice_detector import VoiceDetector
from src.command_runner import run_command

MAX_COUNTER = 4_294_967_295
FRAME_INDICATOR = 1
END_INDICATOR = 2
MAX_PACKET_SIZE = 65_507


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

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((local_addr, local_port))

    vad_model = load_silero_vad()
    voice_detector = VoiceDetector(vad_model)

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    tts_model = 'tts_models/en/jenny/jenny'
    tts = TTS(tts_model).to(device)

    header_fmt = '<hLH'
    header_size = struct.calcsize(header_fmt)
    frames = bytearray()

    last_frame_num = None
    num_voiceless_frames_seen = 0

    message_q = queue.Queue()
    sender_t = threading.Thread(target=send_audio_message, args=[message_q, tts], daemon=True)
    sender_t.start()

    print('Server ready')

    with transcriber(stt_model_file, 'root ::= "Hey Hans, set a 5 minute timer"') as t:
        while True:
            data, sender_addr = sock.recvfrom(MAX_PACKET_SIZE)
            sender_addr = (sender_addr[0], local_port)
            indicator, frame_num, audio_length = struct.unpack_from(header_fmt, data)
            audio_fmt = f'<{audio_length}h'
            audio_bytes = bytes(struct.unpack_from(audio_fmt, data, offset=header_size))

            if last_frame_num is not None:
                if frame_num != last_frame_num + 1 or (last_frame_num == MAX_COUNTER and frame_num != 0):
                    print(f'WARNING: frame {frame_num} received out of order')
                    last_frame_num = frame_num
                    continue

            if indicator == FRAME_INDICATOR:
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
                    text = t.transcribe(audio_data, initial_prompt="Hey Hans, set a 5 minute timer", grammar_rule="root")
                    run_command(text, message_q, sender_addr)
                    frames = bytearray()

            last_frame_num = frame_num



if __name__ == '__main__':
    main()
