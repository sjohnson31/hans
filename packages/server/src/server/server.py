import asyncio
from collections.abc import AsyncIterator
import os
import sys
from typing import NoReturn

#from audio_debugger.audio_debugger import AudioDebugger, DebugMode
import numpy as np
from silero_vad import load_silero_vad
import torch
from transport.transport import AudioSegment, serve
from TTS.api import TTS
from whisppy import transcriber

from server.command_runner import CommandRunner
from server.commands.command import Command
from server.commands.groceries.add_to_grocery_list_command import (
    AddToGroceryListCommand,
)
from server.commands.groceries.tandoor_groceries_client import TandoorGroceriesClient
from server.commands.groceries.text_file_groceries_client import TextFileGroceriesClient
from server.commands.timer_command import TimerCommand
from server.message_sender import text_to_audio
from server.voice_detector import VoiceDetector


def main() -> NoReturn:
    asyncio.run(amain())
    raise RuntimeError("amain should not return")


async def amain() -> NoReturn:
    local_addr = 'hans.local'
    local_port = int(os.environ['SERVER_PORT'])
    stt_model_file = os.environ['STT_MODEL_FILE']
    cert_file = os.environ.get('CERT_FILE', 'certs/hans.local.pem')
    key_file = os.environ.get('KEY_FILE', 'certs/hans.local-key.pem')
    grocery_list_text_file = os.environ.get('GROCERY_LIST_TEXT_FILE')
    tandoor_base_url = os.environ.get('TANDOOR_BASE_URL')
    tandoor_api_key = os.environ.get('TANDOOR_API_KEY')

    if tandoor_api_key and tandoor_base_url and grocery_list_text_file:
        sys.exit(
            'Groceries text file and tandoor server cannot both be configured in '
            'environment'
        )

    commands: list[Command] = [TimerCommand()]

    if grocery_list_text_file or (tandoor_api_key and tandoor_base_url):
        if grocery_list_text_file:
            groceries_client = TextFileGroceriesClient(grocery_list_text_file)
        elif tandoor_api_key and tandoor_base_url:
            groceries_client = TandoorGroceriesClient(tandoor_base_url, tandoor_api_key)
        commands.append(AddToGroceryListCommand(groceries_client))

    command_runner = CommandRunner(commands)

    vad_model = load_silero_vad()
    voice_detector = VoiceDetector(vad_model)

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    tts_model = 'tts_models/en/jenny/jenny'
    tts = TTS(tts_model).to(device)

    async def handle_client(
        audio_stream: AsyncIterator[AudioSegment],
        out_q: asyncio.Queue[AudioSegment],
    ):
        # Handle the audio stream from the client
        # This is where you would process the incoming audio data
        seconds_of_voiceless_frames = 0
        frames = bytearray()
        frame = bytearray()
        #audio_debugger = AudioDebugger(mode=DebugMode.SAVE)

        async with asyncio.TaskGroup() as tg:
            text_q: asyncio.Queue[str] = asyncio.Queue()
            tg.create_task(text_to_audio(text_q, out_q, tts))
            with transcriber(stt_model_file, command_runner.grammar) as t:
                async for audio_chunk in audio_stream:
                    #audio_debugger.append(audio_chunk.audio.tobytes())
                    if audio_chunk.sample_rate != 16000:
                        raise ValueError(
                            f'Audio sample rate {audio_chunk.sample_rate} '
                            f'does not match expected rate of 16000'
                        )
                    frame.extend(audio_chunk.audio.tobytes())
                    if len(frame) < 1024:
                        continue

                    audio_bytes = frame[: 1024 * (len(frame) // 1024)]
                    frame = frame[len(audio_bytes) :]

                    frame_is_voice = voice_detector.big_chunk_is_voice(audio_bytes)
                    if frame_is_voice:
                        print('voice frame detected')
                        seconds_of_voiceless_frames = 0
                    else:
                        seconds_of_voiceless_frames += (len(audio_bytes) / 2.0) / 16000.0

                    if frame_is_voice or (frames and seconds_of_voiceless_frames < 2):
                        frames.extend(audio_bytes)

                    if not frame_is_voice and seconds_of_voiceless_frames > 2 and frames:
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
                            audio_data,
                            initial_prompt=command_runner.initial_prompt,
                            grammar_rule=command_runner.grammar_root,
                        )
                        await command_runner.run(text, text_q)
                        frames = bytearray()

    await serve(
        handle_client,
        local_addr,
        local_port,
    )


if __name__ == '__main__':
    asyncio.run(main())
