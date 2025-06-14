import os
import logging
import random
import sqlite3
import dotenv
from deck_generator import DeckGenerator

output_dir = "output"

# Set up logging
os.makedirs(output_dir, exist_ok=True)
logging.basicConfig(filename=f"{output_dir}/deck_gen.log",
                    format='%(asctime)s %(message)s',
                    filemode='w')
logger = logging.getLogger()
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

db_path = "decks/Topik6000_Korean_Vocab/collection.anki2"

# AI Configuration
ai_config = DeckGenerator.AIConfig(
    open_router_key=dotenv.get_key(".env", "OPENROUTER_API_KEY"),
    google_tts_key=dotenv.get_key(".env", "GOOGLE_API_KEY"),
    model="openai/gpt-4.1",
    temperature=0.3
)

# Anki Configuration
anki_config = DeckGenerator.AnkiConfig(
    model_id=1234567890,
    deck_id=9876543210,
    deck_name="Test Korean Deck"
)

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
    "cultural note": {
        "description": "Cultural note about the word if it is sensible in a language class to include it. If not, output an empty string.",
    }
}

provided_fields = ["frequency"]

field_order = [
    "frequency", "word", "type", "explanation", "example sentences",
    "sino roots", "korean roots", "cultural note"
]

schema = DeckGenerator.SchemaConfig(
    ai_schema=ai_schema,
    item_field="word",
    provided_fields=provided_fields,
    field_order=field_order
)

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
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        notes = import_notes(cursor)
        logger.info(f"Imported {len(notes)} notes from Anki database.")

    items = [note['Word'] for note in notes]
    provided_content = {
        "frequency": [note['Frequency'] for note in notes]
    }

    # Randomly sample n items from the notes
    sample_size = 10
    random_indices = random.sample(range(len(notes)), sample_size)
    items = [items[i] for i in random_indices]
    provided_content = {
        "frequency": [provided_content["frequency"][i] for i in random_indices]
    }


    deck_generator = DeckGenerator(
        schema=schema,
        ai_config=ai_config,
        anki_config=anki_config,
        gen_audio=True
    )

    deck_generator.gen_deck(
        items=items,
        provided_content=provided_content,
        output_dir=output_dir,
    )

if __name__ == "__main__":
    main()
