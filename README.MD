# PDF to Audio Tool Suite

A comprehensive toolkit for converting documents to audio-ready formats, featuring:
1. **PDF Text Extractor** - Extract clean text from PDFs with intelligent chunking
2. **TTS Audio Generator** - Convert Chinese/English text to speech using PaddleSpeech

Both tools work together seamlessly: extract text from PDFs → generate audio files.

## Project Structure

```
pdf_audio_tools/
├── run_extractor.py              # PDF text extraction (main entry)
├── test_extractor.py             # Tests for PDF extractor
├── run_tts.py                    # TTS audio generation (main entry)
├── scripts/
│   ├── pdf_extractor.py          # Core PDF extraction logic
│   └── batch_processor.py        # Batch PDF processing utilities
├── src/
│   ├── tts_engine.py             # PaddleSpeech TTS engine
│   └── document_processor.py     # Document chunking & processing
├── input_pdfs/                   # Default PDF input directory
├── output_text/                  # Default text output directory
├── output_audio/                 # Default audio output directory
└── README.md                     # This file
```

## Tool 1: PDF Text Extractor

Extracts clean, structured text from PDF files, optimized for text-to-audio generation.

### Features

- **Clean Text Extraction** - Removes headers, footers, page numbers, and other artifacts
- **Smart Chunking** - Split PDFs into configurable page ranges for optimal TTS processing
- **Batch Processing** - Process entire directories of PDFs at once
- **Audio Duration Estimates** - Each output file includes estimated listening time
- **Preview Mode** - Inspect first pages before full extraction
- **Metadata Extraction** - View PDF information without processing
- **Organized Output** - Each PDF gets its own subdirectory with numbered parts

### Installation

```bash
# Activate virtual environment
conda activate tools/venv
# OR
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install pypdf2
```

### Usage - PDF Extractor

#### Single File Processing

```bash
# Process entire PDF
python run_extractor.py path/to/mybook.pdf --output-dir output_text

# Process specific page range
python run_extractor.py path/to/mybook.pdf --output-dir output_text --start 10 --end 80

# Control pages per output file (default 15)
python run_extractor.py path/to/mybook.pdf --output-dir output_text --pages-per-file 20

# Show metadata without extracting
python run_extractor.py path/to/mybook.pdf --output-dir output_text --info

# Preview first 3 pages
python run_extractor.py path/to/mybook.pdf --output-dir output_text --preview
```

#### Batch Processing

```bash
# Basic batch (default directories: input_pdfs/ → output_text/)
python run_extractor.py --batch

# Custom directories
python run_extractor.py --batch --input-dir /path/to/pdfs --output-dir /path/to/text

# Batch with page range and chunk size
python run_extractor.py --batch --input-dir my_pdfs/ --output-dir my_output/ --start 5 --end 100 --pages-per-file 20
```

#### Testing

```bash
# Run tests
python test_extractor.py

# Verbose output
python test_extractor.py -v
```

## Tool 2: TTS Audio Generator

Converts Chinese and English text to natural-sounding speech using PaddleSpeech.

### Features

- **Multi-language Support** - Chinese (zh) and English (en) with auto-detection
- **Multiple Voice Profiles** - Various male/female voices for each language
- **Parallel Processing** - Multi-worker synthesis for speed
- **Subtitle Generation** - Create SRT/VTT subtitle files alongside audio
- **Batch Processing** - Recursively process entire directory structures
- **Intelligent Chunking** - Handles long documents by splitting into optimal chunks
- **Silence Control** - Configurable gaps between audio chunks

### Installation

```bash
# Install PaddleSpeech (may take several minutes)
pip install paddlespeech

# Or install with specific dependencies
pip install paddlespeech[all]

# Additional dependencies
pip install pydub
```

### Usage - TTS Generator

#### Single File / Inline Text

```bash
# Convert text file to audio
python run_tts.py --file document.txt --output audio/output.wav

# Convert inline text
python run_tts.py --text "Hello, this is a test" --output test.wav

# Specify voice profile and language
python run_tts.py --file chinese.txt --profile zh_female --lang zh --output chinese_audio.wav

# Generate with subtitles
python run_tts.py --file document.txt --output audio.wav --subtitles srt vtt

# Control performance
python run_tts.py --file long.txt --workers 4 --chunk-size 300 --silence-ms 500
```

#### Directory (Batch) Mode

Process nested directory structures where each `.txt` file gets its own output folder:

```
Expected input structure:
  root/
    chapter1/
      page1.txt
      page2.txt
    chapter2/
      page3.txt

Output structure:
  root/
    chapter1/
      page1/
        audio.wav
        audio.srt (optional)
      page2/
        audio.wav
    chapter2/
      page3/
        audio.wav
    manifest.json
```

**Commands:**

```bash
# Process entire directory tree
python run_tts.py --dir /path/to/text/root

# With custom settings
python run_tts.py --dir text_root --profile en_male --subtitles srt --workers 4

# Directory mode with language override
python run_tts.py --dir chinese_docs --lang zh --profile zh_female_2
```

#### Utility Commands

```bash
# List all available voice profiles
python run_tts.py --list-profiles

# Test a specific voice profile
python run_tts.py --test --profile en_male

# Test all voice profiles
python run_tts.py --test-all
```

### Voice Profiles

| Profile | Language | Description |
|---------|----------|-------------|
| `zh_female` | Chinese | Female voice (default) |
| `zh_female_2` | Chinese | Alternative female voice |
| `zh_male` | Chinese | Male voice |
| `zh_male_2` | Chinese | Alternative male voice |
| `en_female` | English | Female voice |
| `en_male` | English | Male voice |
| `en_male_2` | English | Alternative male voice |

### TTS Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--text` | Inline text to convert | None |
| `--file` | Path to input text file | None |
| `--dir` | Root directory for batch processing | None |
| `--output, -o` | Output WAV file path | `output/document_audio.wav` |
| `--profile, -p` | Voice profile key | Auto-detect |
| `--lang` | Force language ('zh' or 'en') | Auto-detect |
| `--workers, -w` | Parallel synthesis workers | Auto (CPU count) |
| `--chunk-size` | Max chars per chunk | 200 |
| `--silence-ms` | Silence between chunks (ms) | 0 |
| `--subtitles, -s` | Generate subtitles (srt/vtt) | None |
| `--list-profiles` | List available voices | - |
| `--test` | Test a voice profile | - |
| `--test-all` | Test all profiles | - |
| `--no-cleanup` | Keep temporary chunk files | False |

## Complete Workflow: PDF to Audio

Here's how to use both tools together:

### Step 1: Extract Text from PDF

```bash
# Extract text from your PDF
python run_extractor.py mybook.pdf --output-dir text_output --pages-per-file 20
```

### Step 2: Generate Audio from Text

```bash
# Process all extracted text files
python run_tts.py --dir text_output/mybook/ --profile zh_female --subtitles srt
```

### Batch Workflow for Multiple PDFs

```bash
# Step 1: Extract all PDFs in input_pdfs/
python run_extractor.py --batch

# Step 2: Generate audio for all extracted text
python run_tts.py --dir output_text/ --profile en_male --subtitles srt vtt --workers 4
```

## Testing

### Test PDF Extractor
```bash
python test_extractor.py -v
```

### Test TTS Generator
```bash
# Quick test with default voice
python run_tts.py --test

# Test all voices
python run_tts.py --test-all

# Test with specific file
python run_tts.py --file sample.txt --output test.wav
```

## Output Formats

### PDF Extractor Output
```
output_text/
└── mybook/
    ├── part_001.txt  (Pages 1-15, ~2,500 words, ~10 min audio)
    ├── part_002.txt  (Pages 16-30)
    └── part_003.txt  (Pages 31-45)
```

### TTS Generator Output
```
output_audio/
└── mybook/
    ├── part_001/
    │   ├── audio.wav
    │   └── audio.srt
    ├── part_002/
    │   ├── audio.wav
    │   └── audio.srt
    └── manifest.json
```

## Performance Tips

### For PDF Extraction
- **Optimal chunk size**: 15-20 pages per file
- **Preview first**: Use `--preview` to check quality
- **Clean PDFs**: Scanned PDFs may need OCR preprocessing

### For TTS Generation
- **Chunk size**: 200-300 characters works well for most languages
- **Workers**: Set to CPU count for batch processing
- **Silence**: 300-500ms between chunks improves natural flow
- **Subtitles**: Only generate if needed (adds processing time)

## Troubleshooting

### Common Issues

**"Module not found"**
```bash
# For PDF extractor
pip install pypdf2

# For TTS generator
pip install paddlespeech
```

**PaddleSpeech installation fails**
```bash
# Try with specific Python version (3.8-3.10 recommended)
conda create -n tts_env python=3.9
conda activate tts_env
pip install paddlespeech
```

**Out of memory errors**
- Reduce `--chunk-size` to 100-150
- Reduce `--workers` to 2-4
- Process smaller page ranges in PDF extractor

**Poor TTS quality**
- Ensure clean text (use PDF extractor's preview)
- Try different voice profiles
- Adjust chunk size and silence parameters

## Future: Unified CLI

Both tools will eventually be accessible from a single command:

```bash
# Future unified interface (planned)
python audio_tools.py pdf extract input.pdf --output text/
python audio_tools.py tts generate --text "Hello" --output hello.wav
python audio_tools.py pipeline pdf-to-audio input.pdf --voice zh_female
```

## Contributing

Contributions welcome! Areas for improvement:
- Additional PDF processing features
- More TTS engine backends
- GPU acceleration support
- Real-time streaming output
- Web interface

## License

MIT License - feel free to use in personal or commercial projects.

## Acknowledgments

- **PDF Extraction**: Built with PyPDF2
- **TTS Engine**: Powered by PaddleSpeech (Baidu)
- **Inspiration**: Audiobook creation and accessibility tools
```