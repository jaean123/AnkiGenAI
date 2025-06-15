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

### Examples

en_ko_gen.py - Generate Anki deck. Word data are from google-10000-no-swears list. 
ko_en_gen.py - Generate enhanced Anki deck utilizign data from an existing Anki deck of Korean words. 

This script:
- Imports vocabulary from an existing Korean Anki database
- Generates comprehensive content including:
  - Word type and explanation
  - Example sentences in Korean and English
  - Sino-Korean and native Korean roots
  - Synonyms and antonyms
  - Cultural notes
- Creates audio files for pronunciation

## Dependencies

Key dependencies include:
- `genanki` - Anki deck generation
- `instructor` - Structured AI responses
- `openai` - AI model integration
- `google-cloud-texttospeech` - Audio generation
- `pydantic` - Schema definition

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