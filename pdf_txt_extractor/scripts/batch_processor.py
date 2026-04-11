import os
from pathlib import Path
from typing import Optional
from pdf_extractor import PDFToAudioText, logger  # Changed from .pdf_extractor

class BatchPDFProcessor:
    """Process multiple PDFs for audio text extraction"""
    
    def __init__(self, input_dir: str, output_base_dir: str = "output_text"):
        self.input_dir = input_dir
        self.output_base_dir = output_base_dir
        Path(output_base_dir).mkdir(parents=True, exist_ok=True)
        
        if not os.path.exists(input_dir):
            raise FileNotFoundError(f"Input directory not found: {input_dir}")
    
    def process_all_pdfs(self, pages_per_file: int = 15, 
                        start_page: int = 1, 
                        end_page: Optional[int] = None,
                        file_pattern: str = "*.pdf"):
        """Process all PDFs in a directory"""
        
        pdf_files = list(Path(self.input_dir).glob(file_pattern))
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {self.input_dir} matching {file_pattern}")
            return
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        results = {}
        for idx, pdf_file in enumerate(pdf_files, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"[{idx}/{len(pdf_files)}] Processing: {pdf_file.name}")
            
            try:
                # Create output directory for this PDF
                output_dir = os.path.join(self.output_base_dir, pdf_file.stem)
                
                processor = PDFToAudioText(str(pdf_file), output_dir)
                
                # Show PDF info
                info = processor.get_pdf_info()
                logger.info(f"  Pages: {info['total_pages']}, Size: {info['file_size_mb']:.2f} MB")
                
                # Process the PDF
                files = processor.save_to_audio_ready_files(pages_per_file, start_page, end_page)
                results[pdf_file.name] = {
                    "status": "success",
                    "files_created": len(files),
                    "output_dir": output_dir
                }
                
            except Exception as e:
                logger.error(f"  ❌ Failed to process {pdf_file.name}: {str(e)}")
                results[pdf_file.name] = {"status": "failed", "error": str(e)}
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info("PROCESSING SUMMARY")
        logger.info(f"{'='*60}")
        success_count = sum(1 for r in results.values() if r['status'] == 'success')
        logger.info(f"Total PDFs: {len(pdf_files)}")
        logger.info(f"Successful: {success_count}")
        logger.info(f"Failed: {len(pdf_files) - success_count}")
        
        return results