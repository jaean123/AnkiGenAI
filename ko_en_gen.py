import os
import logging
import sqlite3
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

output_dir = "output/korean"

# Data
db_path = "data/Topik6000_Korean_Vocab/collection.anki2"

# LLM Config
system_prompt = "You are an expert Korean language teacher based in US. Your task is to help students understand and learn Korean words."
llm_model = "openai/gpt-4.1"
llm_temperature = 0.3

# Google TTS Config
generate_audio = True
language_code = "ko-KR"
voice_name = "ko-KR-Chirp3-HD-Achernar"

# Anki Config
anki_config = DeckGenerator.AnkiConfig(
    model_id=1234567892,
    deck_id=9876543214,
    deck_name="Korean AI"
)

word_field = "word"

# Define the structured data model for AI output
ai_schema = {
    "type": {
        "description": "Type of the word (noun, verb, etc.)",
    },
    "explanation": {
        "description": "Explanation of the word in English",
    },
    "example sentences": {
        "description": "List of example sentences using the word in English and Korean in the following format: "
                       "[Sentence in Korean] - [Setnence translation in English]. If not applicable, output an empty list.",
        "list": True,
    },
    "sino roots": {
        "description": "If applicable, provide list of sino-Korean root words in the following format: "
                       "[Hanguel] ([Hanja Character]) - [Meaning in English]. If not applicable, output an empty list.",
        "list": True,
    },
    "korean roots": {
        "description": "If applicable, provide list of native Korean root words in the following format: "
                       "[Hanguel] - [Meaning in English]. If not applicable, output an empty list.",
        "list": True,
    },
    "synonyms": {
        "description": "List of synonyms in Korean in the following format: [Hanguel] - [Meaning in English]. If not applicable, output an empty list.",
        "list": True,
    },
    "antonyms": {
        "description": "List of antonyms in Korean in the following format: [Hanguel] - [Meaning in English]. If not applicable, output an empty list.",
        "list": True,
    },
    "cultural note": {
        "description": "Cultural note about the word if it is sensible in a language class to include it. If not, output an empty string.",
    }
}

provided_fields = ["frequency"]

field_order = [
    "frequency", word_field, "type", "explanation", "example sentences", 
    "sino roots", "korean roots", "cultural note", "synonyms", "antonyms",
]

# ---------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------

def import_notes(cursor):
    cursor.execute("SELECT id, flds FROM notes ORDER BY id")
    # note_data = [row[0] for row in cursor.fetchall()]
    note_data = cursor.fetchall()
    notes = []
    for row in note_data:
        id = row[0]
        elem = row[1].split('\x1f')
        notes.append({
            'id': id,
            'Frequency': elem[0],
            'Word': elem[1],
            'Classification': elem[2],
            'Complexity': elem[3],
            'HanjaRef': elem[4],
            'English': elem[5],
            'Wiktionary Link': elem[6],
            'Wordreference Link': elem[7],
            'Note': elem[8],
            'Audio': elem[9][7:-1]
        })
    return notes


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

    # IMPORT DATA FROM DB
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        notes = import_notes(cursor)
        logger.info(f"Imported {len(notes)} notes from Anki database.")

    items = [note['Word'] for note in notes]
    provided_content = {
        "frequency": [note['Frequency'] for note in notes]
    }

    # Randomly sample n items from the notes
    # sample_size = 100
    # random_indices = random.sample(range(len(notes)), sample_size)
    # items = [items[i] for i in random_indices]
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
        items=items,
        provided_content=provided_content,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    main()
