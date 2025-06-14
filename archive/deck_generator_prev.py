import os
import logging

import instructor
import openai
import genanki
from pydantic import BaseModel
from google.cloud import texttospeech
from google.api_core.client_options import ClientOptions


class DeckGenerator:
    """Class for generating Anki decks with vocabulary cards."""
    class AIConfig:
        """Configuration for the AI model used to generate vocabulary content."""

        def __init__(self, open_router_key: str, google_tts_key: str = "", model: str = "openai/gpt-4.1", temperature: float = 0.3):
            """Initializes the AI configuration with model and temperature."""
            self.open_router_key = open_router_key
            self.google_tts_key = google_tts_key
            self.model = model
            self.temperature = temperature

    class AnkiConfig:
        """Configuration for Anki deck generation."""

        def __init__(self, model_id: int, deck_id: int, deck_name: str):
            self.model_id = model_id
            self.deck_id = deck_id
            self.deck_name = deck_name

    def __init__(
            self,
            ai_schema: BaseModel,
            ai_config: AIConfig,
            anki_config: AnkiConfig,
            gen_audio: bool = False):
        self.schema = ai_schema
        self.ai_config = ai_config
        self.anki_config = anki_config
        self.gen_audio = gen_audio

        client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.ai_config.open_router_key,
        )
        self.instructor_client = instructor.from_openai(client)

        if self.gen_audio:
            client_options = ClientOptions(api_key=ai_config.google_tts_key)
            self.google_tts_client = texttospeech.TextToSpeechClient(
                client_options=client_options)

        schema_info = self.schema.model_json_schema()
        field_names = list(schema_info['properties'].keys())
        self.anki_fields = [
            {'name': x.replace('_', ' ')} for x in field_names]
        self.anki_fields.insert(0, {'name': 'word'})
        if self.gen_audio:
            self.anki_fields.append({'name': 'audio'})

        self.anki_model = genanki.Model(
            self.anki_config.model_id,
            self.anki_config.deck_name,
            fields=self.anki_fields,
            templates=[
                {
                    'name': 'Card 1',
                    'qfmt': '{{word}}',
                    'afmt': '{{FrontSide}}'
                }
            ]
        )

    def gen_audio_file(self, text: str, audio_path: str):
        """Generates audio for a given word using Google Text-to-Speech."""
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="ko-KR",
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3)
        response = self.google_tts_client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config)
        with open(audio_path, "wb") as out:
            out.write(response.audio_content)
            logging.getLogger().info(
                f"[INFO] Audio content written to file '{text}.mp3'")

    def gen_card_note(self, word: str) -> BaseModel:
        card_note = self.instructor_client.chat.completions.create(
            model=self.ai_config.model,
            response_model=self.schema,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert language teacher. Your task is to help students understand and learn vocabulary words."
                },
                {
                    "role": "user",
                    "content": f"Generate content for the word {word}."
                },
            ],
        )
        return card_note

    def gen_anki_note(self, note_id: str, data: dict) -> genanki.Note:
        # Prepare fields for the Anki note
        note_fields = []
        for field in self.anki_fields:
            field_name = field['name']
            if field_name in data:
                if field_name == 'audio':
                    note_fields.append(f"[sound:{data[field_name]}]")
                elif type(data[field_name]) == str:
                    note_fields.append(data[field_name])
                elif type(data[field_name]) == list:
                    # Join list items with a <br> tag for Anki
                    note_fields.append('<br>'.join(data[field_name]))
                else:
                    logging.getLogger().error(
                        f"[ERROR] Unsupported field type for {field_name}: {type(data[field_name])}")

        note = genanki.Note(
            guid=note_id,
            model=self.anki_model,
            fields=note_fields
        )
        return note

    def gen_deck(self, items: list[str], output_dir: str):
        """Generates an Anki deck with vocabulary cards."""
        media_dir = os.path.join(output_dir, 'media')
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(media_dir, exist_ok=True)
        name_prefix = self.anki_config.deck_name.replace(' ', '')

        deck = genanki.Deck(
            self.anki_config.deck_id,
            self.anki_config.deck_name
        )

        audio_file_paths = []
        for i in range(len(items)):
            word = items[i]
            note_id = f"{name_prefix}-{i+1}"
            logging.getLogger().info(f"[INFO] Generating content for {word}")
            card_note_ai = self.gen_card_note(word)
            dct = card_note_ai.model_dump()
            dct = {key.replace('_', ' '): value for key, value in dct.items()}
            dct['word'] = word

            if self.gen_audio:
                # Generate audio for each word using Google Text-to-Speech
                audio_basename = f"{note_id}.mp3"
                audio_path = os.path.join(media_dir, audio_basename)
                self.gen_audio_file(word, audio_path)
                dct['audio'] = audio_basename
                audio_file_paths.append(audio_path)

            # Create Anki note
            note = self.gen_anki_note(
                note_id=note_id,
                data=dct)

            deck.add_note(note)

        # Save the deck to a file
        package = genanki.Package(deck)
        package.media_files = audio_file_paths
        package.write_to_file(os.path.join(output_dir, f"{name_prefix}.apkg"))
        logging.getLogger().info(
            f"[INFO] Anki deck '{self.anki_config.deck_name}' generated successfully at {output_dir}")
