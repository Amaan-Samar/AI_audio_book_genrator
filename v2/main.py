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
from __future__ import annotations

# import os
# import sys
# import argparse
# import logging

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
# )
# logger = logging.getLogger(__name__)


# def build_parser() -> argparse.ArgumentParser:
#     p = argparse.ArgumentParser(
#         description="Convert Chinese / English documents to audio using PaddleSpeech.",
#         formatter_class=argparse.RawDescriptionHelpFormatter,
#         epilog=__doc__,
#     )

#     # ── Input ────────────────────────────────────────────────────────────
#     ig = p.add_mutually_exclusive_group()
#     ig.add_argument("--text", type=str, help="Inline text to convert.")
#     ig.add_argument("--file", type=str, help="Path to input text file.")

#     # ── Output ───────────────────────────────────────────────────────────
#     p.add_argument(
#         "--output", "-o",
#         type=str,
#         default="output/document_audio.wav",
#         help="Output WAV file path (default: output/document_audio.wav).",
#     )

#     # ── Voice ────────────────────────────────────────────────────────────
#     p.add_argument(
#         "--profile", "-p",
#         type=str,
#         default=None,
#         help=(
#             "Voice profile key.  Common values:\n"
#             "  zh_female / zh_male / zh_female_2 / zh_male_2\n"
#             "  en_female / en_male / en_male_2\n"
#             "  default (= zh_female)\n"
#             "Omit to auto-detect from text."
#         ),
#     )
#     p.add_argument(
#         "--lang",
#         type=str,
#         choices=["zh", "en"],
#         default=None,
#         help="Force language ('zh' or 'en').  Overrides auto-detection.",
#     )

#     # ── Performance ──────────────────────────────────────────────────────
#     p.add_argument(
#         "--workers", "-w",
#         type=int,
#         default=None,
#         help="Number of parallel synthesis workers (default: auto based on CPU count).",
#     )
#     p.add_argument(
#         "--chunk-size",
#         type=int,
#         default=200,
#         help="Max characters per synthesis chunk (default: 200).",
#     )
#     p.add_argument(
#         "--silence-ms",
#         type=int,
#         default=0,
#         help="Milliseconds of silence between chunks (default: 0).",
#     )

#     # ── Subtitles ────────────────────────────────────────────────────────
#     p.add_argument(
#         "--subtitles", "-s",
#         nargs="+",
#         metavar="FORMAT",
#         choices=["srt", "vtt"],
#         default=None,
#         help=(
#             "Generate subtitle file(s) alongside the audio.\n"
#             "  --subtitles srt          -> output/audio.srt\n"
#             "  --subtitles vtt          -> output/audio.vtt\n"
#             "  --subtitles srt vtt      -> both formats\n"
#             "Subtitle base name matches the --output path."
#         ),
#     )

#     # ── Utility ──────────────────────────────────────────────────────────
#     p.add_argument("--list-profiles", action="store_true",
#                    help="Print all available voice profiles and exit.")
#     p.add_argument("--test", action="store_true",
#                    help="Run a quick synthesis test and exit.")
#     p.add_argument("--test-all", action="store_true",
#                    help="Test every voice profile and exit.")
#     p.add_argument("--no-cleanup", action="store_true",
#                    help="Keep temporary chunk files after combining.")

#     return p


# def main() -> int:
#     args = build_parser().parse_args()

#     # ── Lazy imports (heavy) ─────────────────────────────────────────────
#     try:
#         from src.tts_engine import ChineseTTSEngine
#         from src.document_processor import DocumentProcessor
#     except ImportError as exc:
#         logger.error("Import error: %s\nMake sure PaddleSpeech is installed.", exc)
#         return 1

#     try:
#         engine = ChineseTTSEngine()
#     except Exception as exc:
#         logger.error("Failed to initialise TTS engine: %s", exc)
#         return 1

#     # ── Utility modes ────────────────────────────────────────────────────
#     if args.list_profiles:
#         engine.list_speakers()
#         return 0

#     if args.test:
#         profile = args.profile or "default"
#         logger.info("Testing profile '%s'…", profile)
#         return 0 if engine.test_synthesis(voice_profile=profile) else 1

#     if args.test_all:
#         from src.tts_engine import VOICE_PROFILES
#         # Skip aliases
#         canonical = {k: v for k, v in VOICE_PROFILES.items()
#                      if k not in ("default", "female", "male", "en_default")}
#         ok = 0
#         for profile in canonical:
#             if engine.test_synthesis(voice_profile=profile):
#                 ok += 1
#         logger.info("%d / %d profiles passed.", ok, len(canonical))
#         return 0 if ok > 0 else 1

#     # ── Require input for conversion ─────────────────────────────────────
#     if not args.text and not args.file:
#         build_parser().print_help()
#         return 1

#     # ── Read text ────────────────────────────────────────────────────────
#     if args.file:
#         try:
#             with open(args.file, "r", encoding="utf-8") as fh:
#                 text = fh.read()
#             logger.info("Read %d characters from '%s'.", len(text), args.file)
#         except OSError as exc:
#             logger.error("Cannot read file: %s", exc)
#             return 1
#     else:
#         text = args.text
#         logger.info("Processing %d characters from CLI.", len(text))

#     if not text or not text.strip():
#         logger.error("Input text is empty.")
#         return 1

#     # ── Build processor ──────────────────────────────────────────────────
#     processor = DocumentProcessor(
#         tts_engine=engine,
#         max_workers=args.workers,          # None → auto
#         chunk_size=args.chunk_size,
#         silence_between_chunks_ms=args.silence_ms,
#     )

#     # ── Convert ──────────────────────────────────────────────────────────
#     try:
#         result = processor.process_document(
#             document_text=text,
#             output_path=args.output,
#             voice_profile=args.profile,         # None → auto-detect
#             lang=args.lang,                     # None → auto-detect
#             cleanup=not args.no_cleanup,
#             subtitle_formats=args.subtitles,    # None → no subtitles
#         )
#     except Exception as exc:
#         logger.error("Unexpected error: %s", exc)
#         return 1

#     if result["success"]:
#         logger.info("=" * 60)
#         logger.info("✓ Success!")
#         logger.info("  Output     : %s", result["output_path"])
#         logger.info("  Profile    : %s", args.profile or "auto")
#         logger.info("  Chunks     : %d / %d processed  (%d failed)",
#                     result["processed_chunks"], result["total_chunks"], result["failed_chunks"])
#         logger.info("  Characters : %d", result["total_characters"])
#         logger.info("  Time       : %.1f s", result.get("elapsed_seconds", 0))
#         subs = result.get("subtitles") or {}
#         if subs and "error" not in subs:
#             for fmt, fpath in subs.items():
#                 logger.info("  Subtitle   : %s → %s", fmt.upper(), fpath)
#         elif "error" in subs:
#             logger.warning("  Subtitles  : generation failed — %s", subs["error"])
#         logger.info("=" * 60)
#         return 0
#     else:
#         logger.error("✗ Conversion failed: %s", result.get("error", "unknown"))
#         return 1


# if __name__ == "__main__":
#     sys.exit(main())






import os
import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path

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
    ig.add_argument(
        "--dir", "-d",
        type=str,
        metavar="ROOT_DIR",
        help=(
            "Root directory to process recursively.\n"
            "Structure expected:\n"
            "  ROOT_DIR/\n"
            "    subdir_A/\n"
            "      file1.txt\n"
            "      file2.txt\n"
            "    subdir_B/\n"
            "      file3.txt\n"
            "Each .txt file gets its own output folder:\n"
            "  ROOT_DIR/subdir_A/file1/audio.wav\n"
            "  ROOT_DIR/subdir_A/file1/audio.srt  (if --subtitles given)\n"
            "A manifest.json is written to ROOT_DIR when done."
        ),
    )

    # ── Output (single-file mode only) ───────────────────────────────────
    p.add_argument(
        "--output", "-o",
        type=str,
        default="output/document_audio.wav",
        help=(
            "Output WAV file path (default: output/document_audio.wav).\n"
            "Ignored when --dir is used."
        ),
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
            "  --subtitles srt          -> audio.srt\n"
            "  --subtitles vtt          -> audio.vtt\n"
            "  --subtitles srt vtt      -> both formats\n"
            "In --dir mode the base name is always 'audio'.\n"
            "In single-file mode it matches the --output path."
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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _collect_txt_files(root: Path) -> list[tuple[Path, list[Path]]]:
    """
    Walk *root* one level deep (root → subdirs → .txt files).
    Returns a list of (subdir, [txt_file, ...]) pairs, both sorted.
    Only subdirs that contain at least one .txt file are included.
    """
    pairs: list[tuple[Path, list[Path]]] = []
    for subdir in sorted(p for p in root.iterdir() if p.is_dir()):
        txts = sorted(subdir.glob("*.txt"))
        if txts:
            pairs.append((subdir, txts))
    return pairs


def _process_single_file(
    *,
    txt_path: Path,
    output_dir: Path,
    processor,
    args,
) -> dict:
    """
    Read *txt_path*, synthesise to *output_dir/audio.wav* (+ optional subtitles).
    Returns a result dict suitable for the JSON manifest entry.
    """
    try:
        text = txt_path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.error("Cannot read '%s': %s", txt_path, exc)
        return {
            "source": str(txt_path),
            "success": False,
            "error": str(exc),
        }

    if not text.strip():
        logger.warning("'%s' is empty — skipping.", txt_path)
        return {
            "source": str(txt_path),
            "success": False,
            "error": "empty file",
        }

    output_dir.mkdir(parents=True, exist_ok=True)
    audio_path = output_dir / "audio.wav"

    logger.info("  → %s  (%d chars)", txt_path.name, len(text))

    try:
        result = processor.process_document(
            document_text=text,
            output_path=str(audio_path),
            voice_profile=args.profile,
            lang=args.lang,
            cleanup=not args.no_cleanup,
            subtitle_formats=args.subtitles,
        )
    except Exception as exc:
        logger.error("  ✗ Unexpected error processing '%s': %s", txt_path, exc)
        return {
            "source": str(txt_path),
            "success": False,
            "error": str(exc),
        }

    if not result["success"]:
        logger.error("  ✗ Failed: %s", result.get("error", "unknown"))
        return {
            "source": str(txt_path),
            "success": False,
            "error": result.get("error", "unknown"),
        }

    entry: dict = {
        "source": str(txt_path),
        "success": True,
        "audio": str(audio_path),
        "subtitles": {},
        "stats": {
            "characters": result.get("total_characters", 0),
            "chunks_processed": result.get("processed_chunks", 0),
            "chunks_failed": result.get("failed_chunks", 0),
            "elapsed_seconds": round(result.get("elapsed_seconds", 0), 2),
        },
    }

    subs = result.get("subtitles") or {}
    if subs and "error" not in subs:
        for fmt, fpath in subs.items():
            entry["subtitles"][fmt] = fpath
            logger.info("    subtitle: %s → %s", fmt.upper(), fpath)
    elif "error" in subs:
        logger.warning("    subtitles failed: %s", subs["error"])
        entry["subtitles"]["error"] = subs["error"]

    logger.info(
        "  ✓ Done  [%d chars · %.1f s]",
        result.get("total_characters", 0),
        result.get("elapsed_seconds", 0),
    )
    return entry


def _run_directory_mode(args, processor) -> int:
    """
    Recursively process all .txt files under args.dir.

    Layout written to disk:
        ROOT/
          subdir/
            filename/          ← folder named after the .txt file
              audio.wav
              audio.srt        (if requested)
              audio.vtt        (if requested)
          manifest.json        ← written at the root when everything is done
    """
    root = Path(args.dir).resolve()
    if not root.is_dir():
        logger.error("'%s' is not a directory.", root)
        return 1

    pairs = _collect_txt_files(root)
    if not pairs:
        logger.error("No .txt files found in any subdirectory of '%s'.", root)
        return 1

    total_files = sum(len(txts) for _, txts in pairs)
    logger.info("=" * 60)
    logger.info("Directory mode: %s", root)
    logger.info("  Subdirectories : %d", len(pairs))
    logger.info("  Text files     : %d", total_files)
    logger.info("=" * 60)

    manifest: dict = {
        "root": str(root),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "profile": args.profile or "auto",
        "subtitle_formats": args.subtitles or [],
        "subdirectories": [],
    }

    overall_ok = 0
    overall_fail = 0

    for subdir, txt_files in pairs:
        logger.info("")
        logger.info("[ %s ]", subdir.name)

        subdir_entry: dict = {
            "subdir": str(subdir),
            "files": [],
        }

        for txt_path in txt_files:
            output_dir = subdir / txt_path.stem      # e.g. subdir/my_doc/
            entry = _process_single_file(
                txt_path=txt_path,
                output_dir=output_dir,
                processor=processor,
                args=args,
            )
            subdir_entry["files"].append(entry)
            if entry["success"]:
                overall_ok += 1
            else:
                overall_fail += 1

        manifest["subdirectories"].append(subdir_entry)

    # ── Write manifest ────────────────────────────────────────────────────
    manifest_path = root / "manifest.json"
    try:
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("")
        logger.info("Manifest written → %s", manifest_path)
    except OSError as exc:
        logger.error("Could not write manifest: %s", exc)

    logger.info("=" * 60)
    logger.info("All done!  %d succeeded · %d failed  (total %d)",
                overall_ok, overall_fail, total_files)
    logger.info("=" * 60)

    return 0 if overall_fail == 0 else 1


# ── Entry point ───────────────────────────────────────────────────────────────

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
        canonical = {k: v for k, v in VOICE_PROFILES.items()
                     if k not in ("default", "female", "male", "en_default")}
        ok = 0
        for profile in canonical:
            if engine.test_synthesis(voice_profile=profile):
                ok += 1
        logger.info("%d / %d profiles passed.", ok, len(canonical))
        return 0 if ok > 0 else 1

    # ── Build processor (shared by both modes) ────────────────────────────
    processor = DocumentProcessor(
        tts_engine=engine,
        max_workers=args.workers,
        chunk_size=args.chunk_size,
        silence_between_chunks_ms=args.silence_ms,
    )

    # ── Directory mode ────────────────────────────────────────────────────
    if args.dir:
        return _run_directory_mode(args, processor)

    # ── Single-file / inline-text mode ────────────────────────────────────
    if not args.text and not args.file:
        build_parser().print_help()
        return 1

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

    try:
        result = processor.process_document(
            document_text=text,
            output_path=args.output,
            voice_profile=args.profile,
            lang=args.lang,
            cleanup=not args.no_cleanup,
            subtitle_formats=args.subtitles,
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