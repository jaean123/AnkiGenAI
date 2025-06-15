import os
import logging
import dotenv
import openai
import instructor
from deck_generator import DeckGenerator
from google.cloud import texttospeech
from google.api_core.client_options import ClientOptions
from google.cloud.texttospeech import VoiceSelectionParams

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

output_dir = "output"

# Data
word_path = "data/google-10000-english-no-swears.txt"

# LLM Config
system_prompt = "You are an expert English language teacher based in Korea. Your task is to help students understand and learn English words."
llm_model = "openai/gpt-4.1"
llm_temperature = 0.3

# Google TTS Config
generate_audio = True
language_code = "en-US"
voice_name = "en-US-Chirp3-HD-Achernar"

# Anki Config
anki_config = DeckGenerator.AnkiConfig(
    model_id=1234567890,
    deck_id=9876543210,
    deck_name="English AI"
)

word_field = "word"

# Define the structured data model for AI output
ai_schema = {
    "type": {
        "description": "Type of the word (noun, verb, etc.)",
    },
    "explanation": {
        "description": "Explanation of the word in Korean",
    },
    "example sentences": {
        "description": "List of example sentences using the word in English and Korean in the following format: "
                       "[Sentence in English] - [Setnence translation in Korean].",
        "list": True,
    },
    "roots": {
        "description": "If applicable, provide list of root words in the following format: "
                       "[Root Word] - [Meaning in English]. If not applicable, output an empty list.",
        "list": True,
    },
    "synonyms": {
        "description": "List of synonyms in the following format: [Synonym Word] - [Meaning in English]. If not applicable, output an empty list.",
        "list": True,
    },
    "antonyms": {
        "description": "List of antonyms in the following format: [Antonym Word] - [Meaning in English]. If not applicable, output an empty list.",
        "list": True,
    },
    "cultural note": {
        "description": "Cultural note about the word if it is sensible in a language class to include it. If not, output an empty string.",
    }
}

provided_fields = ["frequency"]

field_order = [
    "frequency", word_field, "type", "explanation", "example sentences",
    "roots", "cultural note", "synonyms", "antonyms"
]

# ---------------------------------------------------------------------
# Main Method
# ---------------------------------------------------------------------


def main():
    # SETUP LOGGING
    os.makedirs(output_dir, exist_ok=True)
    logging.basicConfig(filename=f"{output_dir}/deck_gen.log",
                        format='%(asctime)s %(message)s',
                        filemode='w')
    logger = logging.getLogger()
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)

    # AI CLIENT CONFIGURATION & SETUP
    client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=dotenv.get_key(".env", "OPENROUTER_API_KEY")
    )
    instructor_client = instructor.from_openai(client)
    llm_config = DeckGenerator.LLMConfig(
        instructor=instructor_client,
        system_prompt=system_prompt,
        model=llm_model,
        temperature=llm_temperature
    )

    # GOOGLE TTS CONFIGURATION & SETUP
    client_options = ClientOptions(
        api_key=dotenv.get_key(".env", "GOOGLE_API_KEY"))
    google_tts_client = texttospeech.TextToSpeechClient(
        client_options=client_options)
    voice = VoiceSelectionParams(language_code=language_code, name=voice_name)
    tts_config = DeckGenerator.TTSConfig(
        google_tts_client=google_tts_client,
        voice=voice,
    )

    # SCHEMA CONFIGURATION
    schema = DeckGenerator.SchemaConfig(
        ai_schema=ai_schema,
        item_field=word_field,
        provided_fields=provided_fields,
        field_order=field_order
    )

    # IMPORT WORDS FROM FILE
    with open(word_path, "r", encoding="utf-8") as f:
        words = [line.strip() for line in f if line.strip()]

    provided_content = {
        # Frequency is just the index + 1
        "frequency": [i + 1 for i in range(len(words))]
    }

    # RANDOMLY SAMPLE N ITEMS
    # sample_size = 10
    # random_indices = random.sample(range(len(words)), sample_size)
    # words = [words[i] for i in random_indices]
    # provided_content = {
    #     "frequency": [provided_content["frequency"][i] for i in random_indices]
    # }

    # GENERATE ANKI DECK
    deck_generator = DeckGenerator(
        schema=schema,
        llm_config=llm_config,
        tts_config=tts_config,
        anki_config=anki_config,
        gen_audio=generate_audio
    )

    deck_generator.gen_deck(
        items=words,
        provided_content=provided_content,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    main()
