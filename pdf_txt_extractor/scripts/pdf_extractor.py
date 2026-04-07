import os
import re
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional
import pdfplumber
from tqdm import tqdm

# Setup logging
def setup_logging(log_dir="logs"):
    Path(log_dir).mkdir(exist_ok=True)
    log_file = Path(log_dir) / f"processing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

class PDFToAudioText:
    """Extract clean text from PDFs optimized for text-to-audio generation."""
    
    def __init__(self, pdf_path: str, output_dir: str = "output_text", config_path: str = "config/settings.json"):
        self.pdf_path = pdf_path
        self.pdf_name = Path(pdf_path).stem
        self.output_dir = output_dir
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Validate PDF exists
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    def _load_config(self, config_path):
        """Load configuration from JSON file"""
        default_config = {
            "default_pages_per_file": 15,
            "audio_speed_wpm": 150,
            "clean_text": True,
            "remove_headers_footers": True
        }
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                default_config.update(config)
        
        return default_config
    
    def _clean_for_audio(self, text: str) -> str:
        """Clean text specifically for text-to-audio generation."""
        if not text:
            return ""
        
        if not self.config.get("clean_text", True):
            return text
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip common header/footer patterns if enabled
            if self.config.get("remove_headers_footers", True):
                if re.match(r'^\s*\d+\s*$', line):  # Just page numbers
                    continue
                if re.match(r'^\s*www\.', line):  # URLs
                    continue
                if line.strip().isdigit():  # Page numbers
                    continue
            
            cleaned_lines.append(line.strip())
        
        text = '\n'.join(cleaned_lines)
        
        # Fix spacing and punctuation for better TTS
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = re.sub(r'([.!?])\s*([A-Z])', r'\1  \2', text)  # Ensure double space after sentences
        text = re.sub(r'([,;:])\s*', r'\1 ', text)  # Fix punctuation spacing
        
        # Remove common PDF artifacts
        text = re.sub(r'[^\x00-\x7F]+', ' ', text)  # Remove non-ASCII characters
        text = re.sub(r'\s+-\s+', ' - ', text)  # Fix hyphens
        text = re.sub(r'\s+', ' ', text)  # Final whitespace normalization
        
        return text.strip()
    
    def extract_pages_range(self, start_page: int = 1, end_page: Optional[int] = None) -> str:
        """Extract text from specific page range."""
        with pdfplumber.open(self.pdf_path) as pdf:
            total_pages = len(pdf.pages)
            
            if start_page < 1 or start_page > total_pages:
                raise ValueError(f"Start page {start_page} invalid. PDF has {total_pages} pages")
            
            if end_page is None or end_page > total_pages:
                end_page = total_pages
            
            logger.info(f"Extracting pages {start_page} to {end_page} (total: {end_page - start_page + 1} pages)")
            
            extracted_text = []
            for page_num in tqdm(range(start_page - 1, end_page), desc="Extracting pages"):
                page = pdf.pages[page_num]
                text = page.extract_text()
                if text:
                    clean_text = self._clean_for_audio(text)
                    extracted_text.append(f"[Page {page_num + 1}]\n{clean_text}")
            
            return "\n\n".join(extracted_text)
    
    def save_to_audio_ready_files(self, pages_per_file: int = 15, 
                                   start_page: int = 1, 
                                   end_page: Optional[int] = None,
                                   output_prefix: Optional[str] = None) -> List[str]:
        """Save text as clean files ready for TTS processing."""
        
        # Use config value if not provided
        if pages_per_file == 15 and self.config.get("default_pages_per_file"):
            pages_per_file = self.config["default_pages_per_file"]
        
        with pdfplumber.open(self.pdf_path) as pdf:
            total_pages = len(pdf.pages)
            
            if end_page is None or end_page > total_pages:
                end_page = total_pages
            
            # Calculate number of chunks
            num_chunks = ((end_page - start_page + 1) + pages_per_file - 1) // pages_per_file
            
            logger.info(f"Processing {self.pdf_name}")
            logger.info(f"Total pages: {total_pages}, Output range: {start_page}-{end_page}")
            logger.info(f"Pages per file: {pages_per_file}, Will create {num_chunks} files")
            
            created_files = []
            prefix = output_prefix or f"{self.pdf_name}_pages_{start_page}_to_{end_page}"
            
            for chunk_idx in range(num_chunks):
                chunk_start = start_page + (chunk_idx * pages_per_file)
                chunk_end = min(chunk_start + pages_per_file - 1, end_page)
                
                logger.info(f"Processing chunk {chunk_idx + 1}/{num_chunks}: pages {chunk_start}-{chunk_end}")
                
                chunk_text = []
                for page_num in range(chunk_start - 1, chunk_end):
                    page = pdf.pages[page_num]
                    text = page.extract_text()
                    if text:
                        clean_text = self._clean_for_audio(text)
                        chunk_text.append(clean_text)
                
                full_chunk = "\n\n".join(chunk_text)
                
                # Calculate statistics
                word_count = len(full_chunk.split())
                audio_minutes = word_count / self.config.get("audio_speed_wpm", 150)
                
                # Create filename
                filename = f"{prefix}_part_{chunk_idx + 1:03d}_pages_{chunk_start}-{chunk_end}.txt"
                filepath = os.path.join(self.output_dir, filename)
                
                # Add metadata header
                header = f""
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(header + full_chunk)
                
                logger.info(f"  ✓ Created: {filename} ({word_count:,} words, ~{audio_minutes:.1f} min audio)")
                created_files.append(filepath)
            
            logger.info(f"✅ Complete! Generated {len(created_files)} files in '{self.output_dir}/'")
            return created_files
    
    def get_pdf_info(self) -> dict:
        """Get information about the PDF file"""
        with pdfplumber.open(self.pdf_path) as pdf:
            info = {
                "filename": Path(self.pdf_path).name,
                "total_pages": len(pdf.pages),
                "file_size_mb": os.path.getsize(self.pdf_path) / (1024 * 1024),
                "metadata": pdf.metadata if pdf.metadata else {}
            }
            return info
    
    def preview_text(self, num_pages: int = 3):
        """Preview first few pages to check extraction quality."""
        logger.info(f"\n--- PREVIEW (first {num_pages} pages) ---\n")
        preview_text = self.extract_pages_range(1, num_pages)
        # Show first 1500 characters of preview
        print(preview_text[:1500])
        if len(preview_text) > 1500:
            print("\n... (preview truncated)")
        logger.info(f"Total characters in preview: {len(preview_text):,}")