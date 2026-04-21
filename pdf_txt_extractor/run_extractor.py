# #!/usr/bin/env python3
# """
# PDF to Audio-Ready Text Extractor
# Main entry point for the application
# """

# import os
# import sys
# import argparse
# from pathlib import Path

# # This MUST come before importing from scripts/
# scripts_dir = os.path.join(os.path.dirname(__file__), 'scripts')
# sys.path.insert(0, scripts_dir)

# from pdf_extractor import PDFToAudioText, setup_logging  # now resolves to scripts/pdf_extractor.py
# from batch_processor import BatchPDFProcessor

# def main():
#     parser = argparse.ArgumentParser(
#         description='Extract clean text from PDFs for text-to-audio generation',
#         formatter_class=argparse.RawDescriptionHelpFormatter,
#         epilog="""
# Examples:
#   # Process a single PDF (all pages)
#   python run_extractor.py input_pdfs/mybook.pdf
  
#   # Process specific page range
#   python run_extractor.py input_pdfs/mybook.pdf --start 50 --end 200
  
#   # Process with custom pages per file
#   python run_extractor.py input_pdfs/mybook.pdf --pages-per-file 20
  
#   # Process all PDFs in input_pdfs folder
#   python run_extractor.py --batch
  
#   # Preview a PDF before processing
#   python run_extractor.py input_pdfs/mybook.pdf --preview
#         """
#     )
    
#     # Arguments
#     parser.add_argument('pdf_path', nargs='?', help='Path to PDF file (optional if using --batch)')
#     parser.add_argument('--batch', action='store_true', help='Process all PDFs in input_pdfs folder')
#     parser.add_argument('--start', type=int, default=1, help='Start page (default: 1)')
#     parser.add_argument('--end', type=int, help='End page (default: last page)')
#     parser.add_argument('--pages-per-file', type=int, default=15, 
#                        help='Pages per output file (default: 15)')
#     parser.add_argument('--output-dir', default='output_text', 
#                        help='Output directory (default: output_text)')
#     parser.add_argument('--preview', action='store_true', 
#                        help='Preview first 3 pages of PDF')
#     parser.add_argument('--info', action='store_true',
#                        help='Show PDF information without extracting')
    
#     args = parser.parse_args()
    
#     # Setup logging
#     logger = setup_logging()
    
#     # Batch processing mode
#     if args.batch:
#         logger.info("Starting batch processing mode...")
#         processor = BatchPDFProcessor("input_pdfs", args.output_dir)
#         results = processor.process_all_pdfs(
#             pages_per_file=args.pages_per_file,
#             start_page=args.start,
#             end_page=args.end
#         )
#         return
    
#     # Single PDF mode
#     if not args.pdf_path:
#         parser.print_help()
#         sys.exit(1)
    
#     # Check if PDF exists
#     if not os.path.exists(args.pdf_path):
#         logger.error(f"PDF file not found: {args.pdf_path}")
#         sys.exit(1)
    
#     try:
#         # Initialize processor
#         processor = PDFToAudioText(args.pdf_path, args.output_dir)
        
#         # Show info mode
#         if args.info:
#             info = processor.get_pdf_info()
#             print("\n📄 PDF INFORMATION")
#             print("="*50)
#             for key, value in info.items():
#                 if key == 'metadata':
#                     print(f"\nMetadata:")
#                     for meta_key, meta_value in value.items():
#                         print(f"  {meta_key}: {meta_value}")
#                 else:
#                     print(f"{key.replace('_', ' ').title()}: {value}")
#             return
        
#         # Preview mode
#         if args.preview:
#             processor.preview_text(num_pages=3)
#             return
        
#         # Normal extraction
#         logger.info(f"Starting extraction: {args.pdf_path}")
#         files = processor.save_to_audio_ready_files(
#             pages_per_file=args.pages_per_file,
#             start_page=args.start,
#             end_page=args.end
#         )
        
#         print(f"\n✅ Success! Created {len(files)} text files in '{args.output_dir}/'")
#         print("\nNext steps:")
#         print("  1. Check the output_text folder for your text files")
#         print("  2. Use these files with your text-to-audio generator")
#         print("  3. Each file includes estimated audio duration")
        
#     except Exception as e:
#         logger.error(f"Failed to process PDF: {str(e)}")
#         sys.exit(1)

# if __name__ == "__main__":
#     main()



#!/usr/bin/env python3
"""
PDF to Audio-Ready Text Extractor
Main entry point for the application
"""

import os
import sys
import argparse
from pathlib import Path

# This MUST come before importing from scripts/
scripts_dir = os.path.join(os.path.dirname(__file__), 'scripts')
sys.path.insert(0, scripts_dir)

# from pdf_extractor import PDFToAudioText, setup_logging  # now resolves to scripts/pdf_extractor.py
from scripts.pdf_extractor import PDFToAudioText, setup_logging
from scripts.batch_processor import BatchPDFProcessor


def process_directory(input_dir: str, output_dir: str, pages_per_file: int,
                       start_page: int, end_page, logger):
    """
    Walk input_dir, and for every PDF found:
      1. Create  <output_dir>/<pdf_stem>/
      2. Extract text into that subdirectory
    Returns a summary dict  {pdf_path: [output_files] | Exception}
    """
    input_path = Path(input_dir)
    if not input_path.is_dir():
        logger.error(f"Input directory not found: {input_dir}")
        sys.exit(1)

    pdf_files = sorted(input_path.glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDF files found in: {input_dir}")
        return {}

    logger.info(f"Found {len(pdf_files)} PDF(s) in '{input_dir}'")

    summary = {}
    for pdf_path in pdf_files:
        # One subdirectory per PDF, named after the PDF (without extension)
        pdf_output_dir = str(Path(output_dir) / pdf_path.stem)
        logger.info(f"Processing: {pdf_path.name}  →  {pdf_output_dir}/")

        try:
            processor = PDFToAudioText(str(pdf_path), pdf_output_dir)
            files = processor.save_to_audio_ready_files(
                pages_per_file=pages_per_file,
                start_page=start_page,
                end_page=end_page,
            )
            summary[str(pdf_path)] = files
            print(f"  ✅ {pdf_path.name}: {len(files)} file(s) → '{pdf_output_dir}/'")
        except Exception as exc:
            logger.error(f"  ❌ Failed to process {pdf_path.name}: {exc}")
            summary[str(pdf_path)] = exc

    return summary


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

  # Process all PDFs in a directory  (new: each PDF gets its own output subfolder)
  python run_extractor.py --batch --input-dir my_pdfs/ --output-dir my_output/

  # Batch using the legacy default folder names
  python run_extractor.py --batch

  # Preview a PDF before processing
  python run_extractor.py input_pdfs/mybook.pdf --preview
        """
    )

    # ── arguments ────────────────────────────────────────────────────────────
    parser.add_argument('pdf_path', nargs='?',
                        help='Path to a single PDF file (omit when using --batch)')
    parser.add_argument('--batch', action='store_true',
                        help='Process every PDF inside --input-dir')
    parser.add_argument('--input-dir', default='input_pdfs',
                        help='Directory that contains the PDFs to batch-process '
                             '(default: input_pdfs)')
    parser.add_argument('--start', type=int, default=1,
                        help='Start page (default: 1)')
    parser.add_argument('--end', type=int,
                        help='End page (default: last page)')
    parser.add_argument('--pages-per-file', type=int, default=15,
                        help='Pages per output file (default: 15)')
    parser.add_argument('--output-dir', default='output_text',
                        help='Root output directory (default: output_text)')
    parser.add_argument('--preview', action='store_true',
                        help='Preview first 3 pages of a single PDF')
    parser.add_argument('--info', action='store_true',
                        help='Show PDF information without extracting')

    args = parser.parse_args()
    logger = setup_logging()

    # ── batch mode ────────────────────────────────────────────────────────────
    if args.batch:
        logger.info(f"Batch mode: scanning '{args.input_dir}' ...")
        summary = process_directory(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            pages_per_file=args.pages_per_file,
            start_page=args.start,
            end_page=args.end,
            logger=logger,
        )

        total_pdfs   = len(summary)
        failed       = [p for p, v in summary.items() if isinstance(v, Exception)]
        succeeded    = total_pdfs - len(failed)

        print(f"\n{'='*55}")
        print(f"Batch complete — {succeeded}/{total_pdfs} PDF(s) processed successfully.")
        if failed:
            print("Failed PDFs:")
            for f in failed:
                print(f"  • {f}")
        print(f"\nOutput structure:")
        print(f"  {args.output_dir}/")
        print(f"  ├── <pdf-name-1>/")
        print(f"  │   ├── part_001.txt")
        print(f"  │   └── ...")
        print(f"  └── <pdf-name-2>/")
        print(f"      └── ...")
        return

    # ── single-PDF mode ───────────────────────────────────────────────────────
    if not args.pdf_path:
        parser.print_help()
        sys.exit(1)

    if not os.path.exists(args.pdf_path):
        logger.error(f"PDF file not found: {args.pdf_path}")
        sys.exit(1)

    try:
        # Mirror the batch behaviour: output_dir/<pdf_stem>/part_xxx.txt
        pdf_stem = Path(args.pdf_path).stem
        single_output_dir = str(Path(args.output_dir) / pdf_stem)
        processor = PDFToAudioText(args.pdf_path, single_output_dir)

        if args.info:
            info = processor.get_pdf_info()  # read-only, output dir doesn't matter here
            print("\n📄 PDF INFORMATION")
            print("=" * 50)
            for key, value in info.items():
                if key == 'metadata':
                    print("\nMetadata:")
                    for mk, mv in value.items():
                        print(f"  {mk}: {mv}")
                else:
                    print(f"{key.replace('_', ' ').title()}: {value}")
            return

        if args.preview:
            processor.preview_text(num_pages=3)
            return

        logger.info(f"Starting extraction: {args.pdf_path}")
        files = processor.save_to_audio_ready_files(
            pages_per_file=args.pages_per_file,
            start_page=args.start,
            end_page=args.end,
        )

        print(f"\n✅ Success! Created {len(files)} text file(s) in '{single_output_dir}/'")
        print("\nNext steps:")
        print(f"  1. Check '{single_output_dir}/' for your text files")
        print("  2. Use these files with your text-to-audio generator")
        print("  3. Each file includes estimated audio duration")

    except Exception as e:
        logger.error(f"Failed to process PDF: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()