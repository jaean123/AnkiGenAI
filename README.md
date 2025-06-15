# AI Anki Deck Generator

An AI-powered tool for generating Anki flashcard decks with vocabulary cards. This project utilizes the genanki library to create Anki decks and the instructor library to make AI calls for content generation, with Google Cloud Text-to-Speech for audio generation.

## Features

- **AI-Generated Content**: Uses OpenAI models via OpenRouter to generate comprehensive vocabulary information
- **Audio Generation**: Integrates Google Cloud Text-to-Speech for pronunciation audio
- **Flexible Schema**: Configurable field structure for different types of vocabulary decks
- **Korean Language Support**: Specialized for Korean vocabulary with Sino-Korean roots, cultural notes, and more
- **Database Import**: Can import existing Anki databases for content enhancement

## Project Structure

```
.
├── deck_generator.py          # Main DeckGenerator class
├── gen_korean_deck.py         # Korean-specific deck generation script
├── requirements.txt           # Python dependencies
├── .env                      # Environment variables (API keys)
├── output/                  # Generated decks and logs
├── decks/                   # Source Anki databases
```

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd AnkiGenAI
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables in `.env`:
```env
OPENROUTER_API_KEY=your_openrouter_api_key
GOOGLE_API_KEY=your_google_cloud_api_key
```

## Usage

### Basic Usage

The main class [`DeckGenerator`](deck_generator.py) can be configured for different types of vocabulary decks:

```python
from deck_generator import DeckGenerator

# Configure AI settings
ai_config = DeckGenerator.AIConfig(
    open_router_key="your_api_key",
    google_tts_key="your_google_key",
    model="openai/gpt-4.1",
    temperature=0.3
)

# Configure Anki deck settings
anki_config = DeckGenerator.AnkiConfig(
    model_id=1234567890,
    deck_id=9876543210,
    deck_name="My Vocabulary Deck"
)

# Define the schema for AI-generated content
schema = DeckGenerator.SchemaConfig(
    ai_schema=your_schema,
    item_field="word",
    provided_fields={"frequency": []},
    field_order=["word", "definition", "example"]
)

# Create generator and generate deck
generator = DeckGenerator(schema, ai_config, anki_config, gen_audio=True)
generator.gen_deck(items=["word1", "word2"], output_dir="output")
```

### Korean Deck Generation Example

Run the Korean-specific script:

```bash
python gen_korean_deck.py
```

This script:
- Imports vocabulary from an existing Korean Anki database
- Randomly samples 100 words
- Generates comprehensive content including:
  - Word type and explanation
  - Example sentences in Korean and English
  - Sino-Korean and native Korean roots
  - Synonyms and antonyms
  - Cultural notes
- Creates audio files for pronunciation

## Configuration

### AI Schema Configuration

The [`SchemaConfig`](deck_generator.py) class allows you to define what information the AI should generate:

```python
ai_schema = {
    "definition": {
        "description": "Clear definition of the word",
    },
    "examples": {
        "description": "Example sentences using the word",
        "list": True,  # Indicates this field should be a list
    }
}
```

### Field Order

You can specify the order of fields in the generated Anki cards:

```python
field_order = ["frequency", "word", "definition", "examples"]
```

## Dependencies

Key dependencies include:
- `genanki` - Anki deck generation
- `instructor` - Structured AI responses
- `openai` - AI model integration
- `google-cloud-texttospeech` - Audio generation
- `pydantic` - Data validation and schema definition

See [requirements.txt](requirements.txt) for the complete list.

## Output

The generator creates:
- `.apkg` files ready for import into Anki
- Audio files in MP3 format for pronunciation
- Detailed logs of the generation process

## Card Template

- The generated cards do not include HTML Anki templates yet.
- Refer to [Anki templates](https://docs.ankiweb.net/templates/intro.html) for more info.

The generated cards use custom HTML and CSS templates located in the [`template/`](template/) directory:
- [`front.html`](template/front.html) - Defines the card layout
- [`style.css`](template/style.css) - Provides styling for the cards

## API Keys Required

1. **OpenRouter API Key**: For AI content generation
2. **Google Cloud API Key**: For text-to-speech audio generation

## Logging

The application logs all operations to `output/deck_gen.log` and also outputs to the console for real-time monitoring.

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is licensed under the MIT License - see below for details:

```
MIT License

Copyright (c) 2025 AnkiGenAI

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```