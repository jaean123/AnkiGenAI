import logging
from deck_generator import DeckGenerator
from deck_utils import setup_logging, create_llm_config, create_tts_config

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

output_dir = "output"

# Data
word_path = "data/google-10000-english-no-swears.txt"

# LLM Config
system_prompt = "You are an expert English language teacher based in Korea. Your task is to help students understand and learn English words."

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
    setup_logging(output_dir)

    # Create configurations
    llm_config = create_llm_config(system_prompt)
    tts_config = create_tts_config(language_code, voice_name)
    schema = DeckGenerator.SchemaConfig(
        ai_schema=ai_schema,
        item_field=word_field,
        provided_fields=provided_fields,
        field_order=field_order
    )

    # Load data
    with open(word_path, "r", encoding="utf-8") as f:
        words = [line.strip() for line in f if line.strip()]
        logging.getLogger().info(f"[INFO] Imported {len(words)} from {word_path}")

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

    # Generate Anki deck
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
