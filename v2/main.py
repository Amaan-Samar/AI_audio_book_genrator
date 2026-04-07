#!/usr/bin/env python3
"""
Chinese / English Document → Audio Converter
Uses PaddleSpeech with parallel chunk processing for speed.

Usage examples
--------------
# Chinese female voice (auto-detected from text)
python main.py --file doc.txt --output out.wav

# English, explicit voice
python main.py --file doc.txt --output out.wav --profile en_female

# English male voice
python main.py --file doc.txt --output out.wav --profile en_male

# Chinese male voice, 4 parallel workers
python main.py --file doc.txt --output out.wav --profile zh_male --workers 4

# Force language, override auto-detect
python main.py --file doc.txt --output out.wav --lang zh --profile zh_female

# List all voice profiles
python main.py --list-profiles

# Quick synthesis test
python main.py --test --profile en_female
"""

import os
import sys
import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Convert Chinese / English documents to audio using PaddleSpeech.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # ── Input ────────────────────────────────────────────────────────────
    ig = p.add_mutually_exclusive_group()
    ig.add_argument("--text", type=str, help="Inline text to convert.")
    ig.add_argument("--file", type=str, help="Path to input text file.")

    # ── Output ───────────────────────────────────────────────────────────
    p.add_argument(
        "--output", "-o",
        type=str,
        default="output/document_audio.wav",
        help="Output WAV file path (default: output/document_audio.wav).",
    )

    # ── Voice ────────────────────────────────────────────────────────────
    p.add_argument(
        "--profile", "-p",
        type=str,
        default=None,
        help=(
            "Voice profile key.  Common values:\n"
            "  zh_female / zh_male / zh_female_2 / zh_male_2\n"
            "  en_female / en_male / en_male_2\n"
            "  default (= zh_female)\n"
            "Omit to auto-detect from text."
        ),
    )
    p.add_argument(
        "--lang",
        type=str,
        choices=["zh", "en"],
        default=None,
        help="Force language ('zh' or 'en').  Overrides auto-detection.",
    )

    # ── Performance ──────────────────────────────────────────────────────
    p.add_argument(
        "--workers", "-w",
        type=int,
        default=None,
        help="Number of parallel synthesis workers (default: auto based on CPU count).",
    )
    p.add_argument(
        "--chunk-size",
        type=int,
        default=200,
        help="Max characters per synthesis chunk (default: 200).",
    )
    p.add_argument(
        "--silence-ms",
        type=int,
        default=0,
        help="Milliseconds of silence between chunks (default: 0).",
    )

    # ── Subtitles ────────────────────────────────────────────────────────
    p.add_argument(
        "--subtitles", "-s",
        nargs="+",
        metavar="FORMAT",
        choices=["srt", "vtt"],
        default=None,
        help=(
            "Generate subtitle file(s) alongside the audio.\n"
            "  --subtitles srt          -> output/audio.srt\n"
            "  --subtitles vtt          -> output/audio.vtt\n"
            "  --subtitles srt vtt      -> both formats\n"
            "Subtitle base name matches the --output path."
        ),
    )

    # ── Utility ──────────────────────────────────────────────────────────
    p.add_argument("--list-profiles", action="store_true",
                   help="Print all available voice profiles and exit.")
    p.add_argument("--test", action="store_true",
                   help="Run a quick synthesis test and exit.")
    p.add_argument("--test-all", action="store_true",
                   help="Test every voice profile and exit.")
    p.add_argument("--no-cleanup", action="store_true",
                   help="Keep temporary chunk files after combining.")

    return p


def main() -> int:
    args = build_parser().parse_args()

    # ── Lazy imports (heavy) ─────────────────────────────────────────────
    try:
        from src.tts_engine import ChineseTTSEngine
        from src.document_processor import DocumentProcessor
    except ImportError as exc:
        logger.error("Import error: %s\nMake sure PaddleSpeech is installed.", exc)
        return 1

    try:
        engine = ChineseTTSEngine()
    except Exception as exc:
        logger.error("Failed to initialise TTS engine: %s", exc)
        return 1

    # ── Utility modes ────────────────────────────────────────────────────
    if args.list_profiles:
        engine.list_speakers()
        return 0

    if args.test:
        profile = args.profile or "default"
        logger.info("Testing profile '%s'…", profile)
        return 0 if engine.test_synthesis(voice_profile=profile) else 1

    if args.test_all:
        from src.tts_engine import VOICE_PROFILES
        # Skip aliases
        canonical = {k: v for k, v in VOICE_PROFILES.items()
                     if k not in ("default", "female", "male", "en_default")}
        ok = 0
        for profile in canonical:
            if engine.test_synthesis(voice_profile=profile):
                ok += 1
        logger.info("%d / %d profiles passed.", ok, len(canonical))
        return 0 if ok > 0 else 1

    # ── Require input for conversion ─────────────────────────────────────
    if not args.text and not args.file:
        build_parser().print_help()
        return 1

    # ── Read text ────────────────────────────────────────────────────────
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as fh:
                text = fh.read()
            logger.info("Read %d characters from '%s'.", len(text), args.file)
        except OSError as exc:
            logger.error("Cannot read file: %s", exc)
            return 1
    else:
        text = args.text
        logger.info("Processing %d characters from CLI.", len(text))

    if not text or not text.strip():
        logger.error("Input text is empty.")
        return 1

    # ── Build processor ──────────────────────────────────────────────────
    processor = DocumentProcessor(
        tts_engine=engine,
        max_workers=args.workers,          # None → auto
        chunk_size=args.chunk_size,
        silence_between_chunks_ms=args.silence_ms,
    )

    # ── Convert ──────────────────────────────────────────────────────────
    try:
        result = processor.process_document(
            document_text=text,
            output_path=args.output,
            voice_profile=args.profile,         # None → auto-detect
            lang=args.lang,                     # None → auto-detect
            cleanup=not args.no_cleanup,
            subtitle_formats=args.subtitles,    # None → no subtitles
        )
    except Exception as exc:
        logger.error("Unexpected error: %s", exc)
        return 1

    if result["success"]:
        logger.info("=" * 60)
        logger.info("✓ Success!")
        logger.info("  Output     : %s", result["output_path"])
        logger.info("  Profile    : %s", args.profile or "auto")
        logger.info("  Chunks     : %d / %d processed  (%d failed)",
                    result["processed_chunks"], result["total_chunks"], result["failed_chunks"])
        logger.info("  Characters : %d", result["total_characters"])
        logger.info("  Time       : %.1f s", result.get("elapsed_seconds", 0))
        subs = result.get("subtitles") or {}
        if subs and "error" not in subs:
            for fmt, fpath in subs.items():
                logger.info("  Subtitle   : %s → %s", fmt.upper(), fpath)
        elif "error" in subs:
            logger.warning("  Subtitles  : generation failed — %s", subs["error"])
        logger.info("=" * 60)
        return 0
    else:
        logger.error("✗ Conversion failed: %s", result.get("error", "unknown"))
        return 1


if __name__ == "__main__":
    sys.exit(main())