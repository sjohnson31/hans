import os
import queue
import threading

import numpy as np
from silero_vad import load_silero_vad
import torch
from transport import listen_for_client_audio
from TTS.api import TTS
from whisppy import transcriber

from src.command_runner import GRAMMAR, GRAMMAR_ROOT, INITIAL_PROMPT, run_command
from src.message_sender import send_audio_message
from src.voice_detector import VoiceDetector


def main():
    local_addr = 'hans.local'
    local_port = int(os.environ['SERVER_PORT'])
    stt_model_file = os.environ['STT_MODEL_FILE']
    cert_file = os.environ.get('CERT_FILE', 'certs/hans.local.pem')
    key_file = os.environ.get('KEY_FILE', 'certs/hans.local-key.pem')

    vad_model = load_silero_vad()
    voice_detector = VoiceDetector(vad_model)

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    tts_model = 'tts_models/en/jenny/jenny'
    tts = TTS(tts_model).to(device)

    frames = bytearray()

    num_voiceless_frames_seen = 0

    message_q = queue.Queue()
    sender_t = threading.Thread(
        target=send_audio_message, args=[message_q, tts], daemon=True
    )
    sender_t.start()

    with transcriber(stt_model_file, GRAMMAR) as t:
        print('Server ready')
        for packet in listen_for_client_audio(
            local_addr,
            local_port,
            cert_file=cert_file,
            key_file=key_file,
        ):
            audio_bytes = packet.audio_bytes
            # TODO: Collect frames until we have enough, don't assume a frame is perfect
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
                audio_data = (
                    np.frombuffer(frames, np.int16).astype(np.float32)
                    / np.iinfo(np.int16).max
                )
                # Make the audio at least one second long
                audio_data = np.concatenate(
                    (audio_data, np.zeros(16000 + 10)), dtype=np.float32
                )
                text = t.transcribe(
                    audio_data, initial_prompt=INITIAL_PROMPT, grammar_rule=GRAMMAR_ROOT
                )
                run_command(text, message_q, packet.sender_addr)
                frames = bytearray()


if __name__ == '__main__':
    main()
