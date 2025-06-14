import os
import logging

import instructor
import openai
import genanki
from pydantic import BaseModel, Field, create_model
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

    class SchemaConfig:
        def __init__(self, ai_schema: dict, item_field: str, provided_fields: dict = None, field_order: list = None):
            """Initializes the schema with AI output structure."""
            self.ai_schema = ai_schema
            self.item_field = item_field
            self.provided_fields = provided_fields or {}
            self.field_order = field_order or []

        def gen_ai_schema(self, model_name: str = "AISchemaModel") -> type[BaseModel]:
            fields = {}
            for field_name, attributes in self.ai_schema.items():
                field_name = field_name.replace(' ', '_')
                is_list = attributes.get("list", False)
                description = attributes["description"]
                field_type = list[str] if is_list else str
                fields[field_name] = (field_type, Field(..., description=description))
            return create_model(model_name, __base__=BaseModel, **fields)

    def __init__(
            self,
            schema: SchemaConfig,
            ai_config: AIConfig,
            anki_config: AnkiConfig,
            gen_audio: bool = False):
        self.schema_config = schema
        self.pydantic_schema = schema.gen_ai_schema()
        self.ai_config = ai_config
        self.anki_config = anki_config
        self.gen_audio = gen_audio

        # Set Up Instructor AI client
        client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=ai_config.open_router_key,
        )
        self.instructor_client = instructor.from_openai(client)

        # Set up Google Text-to-Speech client if audio generation is enabled
        if self.gen_audio:
            client_options = ClientOptions(api_key=ai_config.google_tts_key)
            self.google_tts_client = texttospeech.TextToSpeechClient(
                client_options=client_options)

        # Generate Anki model and fields from schema
        if schema.field_order is None or schema.field_order == []:
            schema_info = self.pydantic_schema.model_json_schema()
            field_names = list(schema_info['properties'].keys())
            self.anki_fields = [
                {'name': x.replace('_', ' ')} for x in field_names]
            for provided_field in schema.provided_fields:
                self.anki_fields.append(
                    {'name': provided_field.replace('_', ' ')})
            self.anki_fields.insert(0, {'name': schema.item_field})
        else:
            self.anki_fields = [
                {'name': x.replace('_', ' ')} for x in schema.field_order]
        # Ensure 'audio' field is included if audio generation is enabled
        if not any(field['name'] == 'audio' for field in self.anki_fields) and self.gen_audio:
            self.anki_fields.append({'name': 'audio'})

        self.anki_model = genanki.Model(
            self.anki_config.model_id,
            self.anki_config.deck_name,
            fields=self.anki_fields,
            templates=[
                {
                    "name": "Card 1",
                    "qfmt": f"{{{{{schema.item_field}}}}}",
                    "afmt": "{{FrontSide}}"
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

    def gen_ai_content(self, word: str) -> BaseModel:
        card_note = self.instructor_client.chat.completions.create(
            model=self.ai_config.model,
            response_model=self.pydantic_schema,
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
                elif type(data[field_name]) == int or type(data[field_name]) == float:
                    note_fields.append(str(data[field_name]))
                else:
                    logging.getLogger().error(
                        f"[ERROR] Unsupported field type for {field_name}: {type(data[field_name])}")

        note = genanki.Note(
            guid=note_id,
            model=self.anki_model,
            fields=note_fields
        )
        return note

    def gen_deck(self, items: list[str], provided_content: dict[list] = None, output_dir: str = "output"):
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
            item = items[i]
            note_id = f"{name_prefix}-{i+1}"
            logging.getLogger().info(f"[INFO] ({i+1}/{len(items)}) Generating content for {item}")

            # Generate content for the word using AI
            card_note_ai = self.gen_ai_content(item)
            
            # Create dictionary from AI model
            dct = card_note_ai.model_dump()
            dct = {key.replace('_', ' '): value for key, value in dct.items()}

            # Add the item to the dictionary
            dct[self.schema_config.item_field] = item

            # Add provided content if available to the dictionary
            for field, field_values in provided_content.items():
                dct[field] = field_values[i]

            # Generate audio for the word if enabled
            if self.gen_audio:
                # Generate audio for each word using Google Text-to-Speech
                audio_basename = f"{note_id}.mp3"
                audio_path = os.path.join(media_dir, audio_basename)
                self.gen_audio_file(item, audio_path)
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
