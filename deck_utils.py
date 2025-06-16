import os
import logging
import dotenv
import openai
import instructor
from deck_generator import DeckGenerator
from google.cloud import texttospeech
from google.api_core.client_options import ClientOptions
from google.cloud.texttospeech import VoiceSelectionParams


def setup_logging(output_dir: str):
    """Setup logging configuration."""
    os.makedirs(output_dir, exist_ok=True)
    logging.basicConfig(
        filename=f"{output_dir}/deck_gen.log",
        format='%(asctime)s %(message)s',
        filemode='w'
    )
    logger = logging.getLogger()
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)


def create_llm_config(system_prompt: str, model: str = "openai/gpt-4.1", temperature: float = 0.3) -> DeckGenerator.LLMConfig:
    """Create LLM configuration."""
    client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=dotenv.get_key(".env", "OPENROUTER_API_KEY")
    )
    instructor_client = instructor.from_openai(client)

    return DeckGenerator.LLMConfig(
        instructor=instructor_client,
        system_prompt=system_prompt,
        model=model,
        temperature=temperature
    )


def create_tts_config(language_code: str, voice_name: str, speak_rate: float = 1.0) -> DeckGenerator.TTSConfig:
    """Create TTS configuration."""
    client_options = ClientOptions(
        api_key=dotenv.get_key(".env", "GOOGLE_API_KEY")
    )
    google_tts_client = texttospeech.TextToSpeechClient(
        client_options=client_options
    )
    voice = VoiceSelectionParams(language_code=language_code, name=voice_name)

    return DeckGenerator.TTSConfig(
        google_tts_client=google_tts_client,
        voice_params=voice,
        speak_rate=speak_rate
    )
