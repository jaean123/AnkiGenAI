import os
import logging
import instructor
import genanki
import json
import shutil
import signal
import atexit
from pydantic import BaseModel, Field, create_model
from google.cloud import texttospeech
from google.cloud.texttospeech import VoiceSelectionParams


class DeckGenerator:
    """Class for generating Anki decks with vocabulary cards."""
    class LLMConfig:
        """Configuration for the LLM model used to generate vocabulary content."""

        def __init__(
                self,
                instructor: instructor.Instructor,
                system_prompt: str = "You are an expert language teacher. Your task is to help students understand and learn vocabulary words.",
                model: str = "openai/gpt-4.1",
                temperature: float = 0.3):
            """Initializes the AI configuration with model and temperature."""
            self.instructor = instructor
            self.system_prompt = system_prompt
            self.model = model
            self.temperature = temperature

    class TTSConfig:
        """Configuration for Google Text-to-Speech."""

        def __init__(self,
                     google_tts_client: texttospeech.TextToSpeechClient,
                     voice_params: VoiceSelectionParams,
                     speak_rate: float = 1.0):
            self.google_tts_client = google_tts_client
            self.voice_params = voice_params
            self.speak_rate = speak_rate

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
                fields[field_name] = (
                    field_type, Field(..., description=description))
            return create_model(model_name, __base__=BaseModel, **fields)

    def __init__(
            self,
            schema: SchemaConfig,
            anki_config: AnkiConfig,
            llm_config: LLMConfig,
            tts_config: TTSConfig = None,
            gen_audio: bool = False,
            cache_dir: str = None):
        self.schema_config = schema
        self.pydantic_schema = schema.gen_ai_schema()
        self.llm_config = llm_config
        self.tts_config = tts_config
        self.anki_config = anki_config
        self.gen_audio = gen_audio
        self.cache_dir = cache_dir
        
        # Initialize cache if cache_dir is provided
        if self.cache_dir:
            os.makedirs(self.cache_dir, exist_ok=True)
            self.ai_cache_file = os.path.join(self.cache_dir, "ai_content_cache.json")
            self.audio_cache_dir = os.path.join(self.cache_dir, "audio")
            os.makedirs(self.audio_cache_dir, exist_ok=True)
            self._load_ai_cache()
            self._register_cleanup_handlers()
        else:
            self.ai_content_cache = {}

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
                    "qfmt": f'<p style="font-size: 24px; ">{{{{{schema.item_field}}}}}</p>',
                    "afmt": self.gen_afmt(),
                }
            ]
        )

    def gen_afmt(self) -> str:
        """Generates the back template for the Anki card."""
        tmpl = """<div style="text-align: left; font-size: 16px; ">{{FrontSide}}</div><hr>"""
        for field in self.anki_fields:
            field_name = field['name']
            tmpl += f'{{{{#{field_name}}}}}<p><span style="font-size: 11px; ">{field_name}</span><br>{{{{{field_name}}}}}</p>{{{{/{field_name}}}}}'
        tmpl += "</div>"
        return tmpl

    def _load_ai_cache(self):
        """Load the AI content cache from disk."""
        if os.path.exists(self.ai_cache_file):
            try:
                with open(self.ai_cache_file, 'r', encoding='utf-8') as f:
                    self.ai_content_cache = json.load(f)
                logging.getLogger().info(f"[INFO] Loaded AI cache with {len(self.ai_content_cache)} entries")
            except Exception as e:
                logging.getLogger().warning(f"[WARNING] Failed to load AI cache: {e}. Starting with empty cache.")
                self.ai_content_cache = {}
        else:
            self.ai_content_cache = {}

    def _save_ai_cache(self):
        """Save the AI content cache to disk."""
        if not self.cache_dir:
            return
        try:
            with open(self.ai_cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.ai_content_cache, f, indent=2, ensure_ascii=False)
            logging.getLogger().info(f"[INFO] Saved AI cache with {len(self.ai_content_cache)} entries")
        except Exception as e:
            logging.getLogger().error(f"[ERROR] Failed to save AI cache: {e}")

    def _register_cleanup_handlers(self):
        """Register cleanup handlers to save cache on program termination."""
        # Register atexit handler for normal program termination
        atexit.register(self._cleanup_cache)
        
        # Register signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logging.getLogger().info(f"[INFO] Received signal {signum}, saving cache before exit...")
            self._cleanup_cache()
            # Re-raise the signal to allow normal termination
            signal.signal(signum, signal.SIG_DFL)
            os.kill(os.getpid(), signum)
        
        signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

    def _cleanup_cache(self):
        """Cleanup method to save cache before program termination."""
        if hasattr(self, 'cache_dir') and self.cache_dir:
            logging.getLogger().info("[INFO] Saving cache before program termination...")
            self._save_ai_cache()

    def gen_audio_file(self, text: str, audio_path: str):
        """Generates audio for a given word using Google Text-to-Speech, using cache if available."""
        # Check if we should use caching and if cached audio exists
        if self.cache_dir:
            audio_filename = os.path.basename(audio_path)
            cached_audio_path = os.path.join(self.audio_cache_dir, audio_filename)
            
            if os.path.exists(cached_audio_path):
                # Copy from cache to target location
                shutil.copy2(cached_audio_path, audio_path)
                logging.getLogger().info(f"[INFO] Using cached audio for '{text}'")
                return
        
        # Generate new audio
        logging.getLogger().info(f"[INFO] Generating new audio for '{text}'")
        synthesis_input = texttospeech.SynthesisInput(text=text)
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=self.tts_config.speak_rate,
        )
        response = self.tts_config.google_tts_client.synthesize_speech(
            input=synthesis_input, voice=self.tts_config.voice_params, audio_config=audio_config)
        
        # Save to target location
        with open(audio_path, "wb") as out:
            out.write(response.audio_content)
            
        # Also save to cache if caching is enabled
        if self.cache_dir:
            audio_filename = os.path.basename(audio_path)
            cached_audio_path = os.path.join(self.audio_cache_dir, audio_filename)
            shutil.copy2(audio_path, cached_audio_path)
            
        logging.getLogger().info(f"[INFO] Audio content written to file '{text}.mp3'")

    def gen_ai_content(self, word: str) -> BaseModel:
        """Generate AI content for a word, using cache if available."""
        # Check cache if caching is enabled
        if self.cache_dir and word in self.ai_content_cache:
            logging.getLogger().info(f"[INFO] Using cached AI content for '{word}'")
            cached_data = self.ai_content_cache[word]
            return self.pydantic_schema(**cached_data)
        
        # Generate new content
        logging.getLogger().info(f"[INFO] Generating new AI content for '{word}'")
        card_note = self.llm_config.instructor.chat.completions.create(
            model=self.llm_config.model,
            response_model=self.pydantic_schema,
            messages=[
                {
                    "role": "system",
                    "content": self.llm_config.system_prompt
                },
                {
                    "role": "user",
                    "content": f"Generate content for the word {word}."
                },
            ],
        )
        
        # Cache the result if caching is enabled
        if self.cache_dir:
            self.ai_content_cache[word] = card_note.model_dump()
            
        return card_note

    def gen_anki_note(self, guid: str, data: dict) -> genanki.Note:
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
            guid=guid,
            model=self.anki_model,
            fields=note_fields
        )
        return note

    def gen_deck(self, items: list[str], provided_content: dict[list] = None, guids: list[str] = None, output_dir: str = "output"):
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
        
        try:
            for i in range(len(items)):
                item = items[i]
                
                if guids is not None:
                    guid = guids[i]
                else:
                    guid = f"{name_prefix}-{i+1}"

                logging.getLogger().info(
                    f"[INFO] ({i+1}/{len(items)}) Generating content for {item}")

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
                    audio_basename = f"{guid}.mp3"
                    audio_path = os.path.join(media_dir, audio_basename)
                    self.gen_audio_file(item, audio_path)
                    dct['audio'] = audio_basename
                    audio_file_paths.append(audio_path)

                # Create Anki note
                note = self.gen_anki_note(
                    guid=guid,
                    data=dct)

                deck.add_note(note)

        finally:
            # Always save cache, even if generation was interrupted
            if self.cache_dir:
                self._save_ai_cache()

        # Save the deck to a file
        package = genanki.Package(deck)
        package.media_files = audio_file_paths
        package.write_to_file(os.path.join(output_dir, f"{name_prefix}.apkg"))
            
        logging.getLogger().info(
            f"[INFO] Anki deck '{self.anki_config.deck_name}' generated successfully at {output_dir}")
