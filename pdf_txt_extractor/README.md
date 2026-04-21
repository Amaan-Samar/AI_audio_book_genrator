Here's the corrected README with accurate command examples based on your actual usage:

# pdf_text_extractor

A Python tool that extracts clean, structured text from PDF files, optimized for text-to-audio (TTS) generation. Splits large documents into manageable chunks with estimated audio durations.

## Features

- **Clean Text Extraction** - Removes headers, footers, page numbers, and other artifacts
- **Smart Chunking** - Split PDFs into configurable page ranges for optimal TTS processing
- **Batch Processing** - Process entire directories of PDFs at once
- **Audio Duration Estimates** - Each output file includes estimated listening time
- **Preview Mode** - Inspect first pages before full extraction
- **Metadata Extraction** - View PDF information without processing
- **Organized Output** - Each PDF gets its own subdirectory with numbered parts

## Installation

### Prerequisites
- Python 3.7 or higher
- pip package manager
- Virtual environment (recommended)

### Setup Virtual Environment

```bash
# Create and activate virtual environment
conda activate tools/venv
# OR
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

### Install Dependencies

Or using requirements.txt:

pip install -r requirements.txt
```

### Project Structure

```
pdf_text_extractor/
├── run_extractor.py          # Main entry point
├── test_extractor.py         # Test suite
├── scripts/
│   ├── pdf_extractor.py      # Core extraction logic
│   └── batch_processor.py    # Batch processing utilities
├── input_pdfs/               # Default input directory
├── output_text/              # Default output directory
└── README.md                 # This file
```

## Usage

### Basic Commands - Single File

**Process a whole PDF (all pages):**
```bash
python run_extractor.py path/to/mybook.pdf --output-dir path/to/output
```

**Process specific page range only:**
```bash
python run_extractor.py path/to/mybook.pdf --output-dir path/to/output --start 10 --end 80
```

**Control pages per output file (default is 15):**
```bash
python run_extractor.py path/to/mybook.pdf --output-dir path/to/output --pages-per-file 20
```

**Show PDF metadata without extracting anything:**
```bash
python run_extractor.py path/to/mybook.pdf --output-dir path/to/output --info
```

**Preview the first 3 pages of text without saving:**
```bash
python run_extractor.py path/to/mybook.pdf --output-dir path/to/output --preview
```

### Batch Processing - Multiple PDFs

**Basic batch processing (uses default directories):**
```bash
python run_extractor.py --batch
```
*Scans `input_pdfs/` directory, writes to `output_text/` directory*

**Custom input and output directories:**
```bash
python run_extractor.py --batch --input-dir /path/to/your/pdf/folder --output-dir /path/to/output/folder
```

**Batch with page range and chunk size:**
```bash
python run_extractor.py --batch --input-dir my_pdfs/ --output-dir my_output/ --start 5 --end 100 --pages-per-file 20
```

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `pdf_path` | Path to a single PDF file | None |
| `--output-dir` | Root output directory | `output_text` |
| `--batch` | Process every PDF in input directory | False |
| `--input-dir` | Directory containing PDFs for batch processing | `input_pdfs` |
| `--start` | Starting page number | 1 |
| `--end` | Ending page number | Last page |
| `--pages-per-file` | Pages per output text file | 15 |
| `--preview` | Preview first 3 pages | False |
| `--info` | Show PDF information without extracting | False |

**Note:** In single file mode, `--output-dir` is required.

## Output Structure

The tool creates an organized output structure:

```
output_text/
├── mybook/
│   ├── part_001.txt    (Pages 1-15)
│   ├── part_002.txt    (Pages 16-30)
│   └── part_003.txt    (Pages 31-45)
├── another_book/
│   ├── part_001.txt
│   └── part_002.txt
└── ...
```

Each text file includes:
- Clean, extracted text content
- Header with file information
- Estimated audio duration (based on ~150 words per minute)

## Testing

Run the test suite to verify everything is working correctly:

**Normal test run:**
```bash
python test_extractor.py
```

**Verbose mode (shows each test name and pass/fail status):**
```bash
python test_extractor.py -v
```

**Note:** Place `test_extractor.py` in the same directory as `run_extractor.py`

## Example Workflow

1. **Activate your virtual environment:**
   ```bash
   conda activate tools/venv
   ```

2. **Place your PDFs** in `input_pdfs/` directory (or any custom folder)

3. **Run batch processing:**
   ```bash
   python run_extractor.py --batch
   ```

4. **Check output** in `output_text/` directory

5. **Use the text files** with your preferred TTS tool (e.g., Amazon Polly, Google TTS, Coqui TTS)

## Troubleshooting

### Common Issues

**"No PDF files found"**
- Ensure PDFs have `.pdf` extension
- Check the path specified in `--input-dir`

**Poor text quality**
- PDF might be scanned/image-based
- Consider using OCR software (e.g., Tesseract) first

**Memory errors with large PDFs**
- Reduce `--pages-per-file` value
- Process smaller page ranges

**Module not found errors**
- Ensure virtual environment is activated

## Advanced Usage Examples

### Real-world examples

```bash
# Process a specific chapter from a book
python run_extractor.py books/mybook.pdf --output-dir audio_prep --start 100 --end 150 --pages-per-file 10

# Extract metadata only
python run_extractor.py document.pdf --output-dir temp --info

# Quick preview before full extraction
python run_extractor.py unknown.pdf --output-dir temp --preview

# Batch process with custom locations
python run_extractor.py --batch --input-dir ~/Documents/pdfs --output-dir ~/Desktop/audio_text
```

## Contributing

Feel free to submit issues or pull requests for:
- Additional PDF processing features
- Performance improvements
- Bug fixes
- Documentation enhancements

## License

This project is open-source and available under the MIT License.

## Acknowledgments

- Built with PyPDF2 for PDF text extraction
- Inspired by audiobook creation and accessibility needs
```