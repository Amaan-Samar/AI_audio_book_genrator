#!/usr/bin/env python3
"""
PDF to Audio-Ready Text Extractor
Main entry point for the application
"""

# import os
# import sys
# import argparse
# from pathlib import Path

# # Add scripts directory to path
# sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

# from pdf_extractor import PDFToAudioText, setup_logging
# from batch_processor import BatchPDFProcessor

import os
import sys
import argparse
from pathlib import Path

# This MUST come before importing from scripts/
scripts_dir = os.path.join(os.path.dirname(__file__), 'scripts')
sys.path.insert(0, scripts_dir)

from pdf_extractor import PDFToAudioText, setup_logging  # now resolves to scripts/pdf_extractor.py
from batch_processor import BatchPDFProcessor

def main():
    parser = argparse.ArgumentParser(
        description='Extract clean text from PDFs for text-to-audio generation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single PDF (all pages)
  python run_extractor.py input_pdfs/mybook.pdf
  
  # Process specific page range
  python run_extractor.py input_pdfs/mybook.pdf --start 50 --end 200
  
  # Process with custom pages per file
  python run_extractor.py input_pdfs/mybook.pdf --pages-per-file 20
  
  # Process all PDFs in input_pdfs folder
  python run_extractor.py --batch
  
  # Preview a PDF before processing
  python run_extractor.py input_pdfs/mybook.pdf --preview
        """
    )
    
    # Arguments
    parser.add_argument('pdf_path', nargs='?', help='Path to PDF file (optional if using --batch)')
    parser.add_argument('--batch', action='store_true', help='Process all PDFs in input_pdfs folder')
    parser.add_argument('--start', type=int, default=1, help='Start page (default: 1)')
    parser.add_argument('--end', type=int, help='End page (default: last page)')
    parser.add_argument('--pages-per-file', type=int, default=15, 
                       help='Pages per output file (default: 15)')
    parser.add_argument('--output-dir', default='output_text', 
                       help='Output directory (default: output_text)')
    parser.add_argument('--preview', action='store_true', 
                       help='Preview first 3 pages of PDF')
    parser.add_argument('--info', action='store_true',
                       help='Show PDF information without extracting')
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging()
    
    # Batch processing mode
    if args.batch:
        logger.info("Starting batch processing mode...")
        processor = BatchPDFProcessor("input_pdfs", args.output_dir)
        results = processor.process_all_pdfs(
            pages_per_file=args.pages_per_file,
            start_page=args.start,
            end_page=args.end
        )
        return
    
    # Single PDF mode
    if not args.pdf_path:
        parser.print_help()
        sys.exit(1)
    
    # Check if PDF exists
    if not os.path.exists(args.pdf_path):
        logger.error(f"PDF file not found: {args.pdf_path}")
        sys.exit(1)
    
    try:
        # Initialize processor
        processor = PDFToAudioText(args.pdf_path, args.output_dir)
        
        # Show info mode
        if args.info:
            info = processor.get_pdf_info()
            print("\n📄 PDF INFORMATION")
            print("="*50)
            for key, value in info.items():
                if key == 'metadata':
                    print(f"\nMetadata:")
                    for meta_key, meta_value in value.items():
                        print(f"  {meta_key}: {meta_value}")
                else:
                    print(f"{key.replace('_', ' ').title()}: {value}")
            return
        
        # Preview mode
        if args.preview:
            processor.preview_text(num_pages=3)
            return
        
        # Normal extraction
        logger.info(f"Starting extraction: {args.pdf_path}")
        files = processor.save_to_audio_ready_files(
            pages_per_file=args.pages_per_file,
            start_page=args.start,
            end_page=args.end
        )
        
        print(f"\n✅ Success! Created {len(files)} text files in '{args.output_dir}/'")
        print("\nNext steps:")
        print("  1. Check the output_text folder for your text files")
        print("  2. Use these files with your text-to-audio generator")
        print("  3. Each file includes estimated audio duration")
        
    except Exception as e:
        logger.error(f"Failed to process PDF: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()