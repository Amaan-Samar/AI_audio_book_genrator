#!/usr/bin/env python3
"""
predownload_models.py
=====================
Pre-downloads and validates ALL PaddleSpeech TTS models used by the project
**sequentially** (one at a time) so there are zero race conditions when the
main pipeline later runs with parallel workers.

Run this ONCE before using main.py or voice_sampler.py:

    python predownload_models.py            # download everything
    python predownload_models.py --lang en  # only English models
    python predownload_models.py --lang zh  # only Chinese models
    python predownload_models.py --verify   # check what's already downloaded

After this completes successfully, main.py and voice_sampler.py will never
try to download a model mid-run, eliminating the [Errno 17] / zip_tmp errors.
"""

import os
import sys
import argparse
import logging
import time
import shutil

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# All unique model combinations used across the project
# Each entry: (acoustic_model, vocoder, language, one representative spk_id)
# We only need to trigger the download once per unique (am, voc, lang) combo —
# speaker ID does not affect which files are downloaded.
# ---------------------------------------------------------------------------

MODELS = [
    # Chinese models  (fastspeech2_aishell3 + hifigan_aishell3)
    {
        "name":    "Chinese FastSpeech2 + HiFiGAN  (aishell3)",
        "lang":    "zh",
        "am":      "fastspeech2_aishell3",
        "voc":     "hifigan_aishell3",
        "spk_id":  0,
        "test_text": "你好，模型下载测试。",
    },
    # English LJSpeech  (single high-quality female)
    {
        "name":    "English FastSpeech2 + HiFiGAN  (ljspeech)",
        "lang":    "en",
        "am":      "fastspeech2_ljspeech",
        "voc":     "hifigan_ljspeech",
        "spk_id":  0,
        "test_text": "Hello, model download test.",
    },
    # English VCTK  (multi-speaker, used for en_male variants)
    {
        "name":    "English FastSpeech2 + HiFiGAN  (vctk)",
        "lang":    "en",
        "am":      "fastspeech2_vctk",
        "voc":     "hifigan_vctk",
        "spk_id":  0,
        "test_text": "Hello, VCTK model download test.",
    },
]

# ---------------------------------------------------------------------------
# PaddleSpeech model cache location
# ---------------------------------------------------------------------------

def get_model_cache_dir() -> str:
    """Return the directory where PaddleSpeech caches downloaded models."""
    return os.path.expanduser("~/.paddlespeech/models")


def _model_dir_exists(am: str, lang: str) -> bool:
    """
    Heuristic check: does the model directory exist and contain files?
    PaddleSpeech stores models as ~/.paddlespeech/models/<am>-<lang>/<version>/
    """
    base = get_model_cache_dir()
    model_dir = os.path.join(base, f"{am}-{lang}")
    if not os.path.isdir(model_dir):
        return False
    # Check that there's at least one subdirectory (version folder)
    subdirs = [d for d in os.listdir(model_dir)
               if os.path.isdir(os.path.join(model_dir, d))]
    return len(subdirs) > 0


def _remove_stale_tmp_files(am: str, lang: str):
    """
    Remove any leftover *.zip_tmp files from a previous failed download.
    These cause [Errno 2] errors on the next run.
    """
    base = get_model_cache_dir()
    model_dir = os.path.join(base, f"{am}-{lang}")
    if not os.path.isdir(model_dir):
        return
    removed = 0
    for root, dirs, files in os.walk(model_dir):
        for fname in files:
            if fname.endswith("_tmp") or fname.endswith(".tmp"):
                fp = os.path.join(root, fname)
                try:
                    os.remove(fp)
                    logger.info("  Removed stale temp file: %s", fp)
                    removed += 1
                except OSError as e:
                    logger.warning("  Could not remove %s: %s", fp, e)
    if removed:
        logger.info("  Cleaned up %d stale temp file(s).", removed)


# ---------------------------------------------------------------------------
# Core download + validate
# ---------------------------------------------------------------------------

def download_model(model: dict, verify_only: bool = False) -> dict:
    """
    Trigger a full download + synthesis test for one model entry.

    Returns a result dict with keys: name, success, elapsed, error, skipped.
    """
    name   = model["name"]
    am     = model["am"]
    voc    = model["voc"]
    lang   = model["lang"]
    spk_id = model["spk_id"]
    text   = model["test_text"]

    # ── Clean up stale temp files first ──────────────────────────────────
    _remove_stale_tmp_files(am, lang)

    if verify_only:
        exists = _model_dir_exists(am, lang)
        status = "✓ cached" if exists else "✗ missing"
        print(f"  {status:<12}  {name}")
        return {"name": name, "success": exists, "skipped": True}

    print(f"\n{'─'*64}")
    print(f"  Model  : {name}")
    print(f"  AM     : {am}")
    print(f"  Vocoder: {voc}")
    print(f"  Lang   : {lang}")

    if _model_dir_exists(am, lang):
        print(f"  Status : already cached — running quick synthesis test…")
    else:
        print(f"  Status : NOT cached — downloading now (may take several minutes)…")

    # ── Synthesize a short test utterance (forces download + unpacking) ──
    tmp_wav = f"/tmp/_predownload_{am}_{lang}_test.wav"
    t0 = time.time()

    try:
        from paddlespeech.cli.tts import TTSExecutor
        tts = TTSExecutor()
        tts(
            text=text,
            output=tmp_wav,
            am=am,
            voc=voc,
            lang=lang,
            spk_id=spk_id,
        )
        elapsed = time.time() - t0

        # Verify the output file was actually created
        if not os.path.exists(tmp_wav) or os.path.getsize(tmp_wav) == 0:
            raise RuntimeError("Output WAV is missing or empty after synthesis.")

        print(f"  ✓ Done in {elapsed:.1f}s  →  test WAV: {tmp_wav}")
        return {"name": name, "success": True, "elapsed": elapsed, "skipped": False}

    except Exception as exc:
        elapsed = time.time() - t0
        logger.error("  ✗ FAILED in %.1fs: %s", elapsed, exc)
        return {
            "name":    name,
            "success": False,
            "elapsed": elapsed,
            "error":   str(exc),
            "skipped": False,
        }
    finally:
        # Clean up test WAV
        if os.path.exists(tmp_wav):
            try:
                os.remove(tmp_wav)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        description="Pre-download all PaddleSpeech TTS models used by this project.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--lang", choices=["zh", "en"], default=None,
                   help="Only download models for this language.")
    p.add_argument("--verify", action="store_true",
                   help="Only check which models are already cached — do not download.")
    p.add_argument("--force", action="store_true",
                   help="Re-download even if model appears to be already cached.")
    return p


def main() -> int:
    args = build_parser().parse_args()

    # Filter models
    models = MODELS
    if args.lang:
        models = [m for m in models if m["lang"] == args.lang]

    if not models:
        print("No models match the given filters.")
        return 1

    print("\n" + "=" * 64)
    print("  PaddleSpeech Model Pre-Downloader")
    print("=" * 64)
    print(f"  Cache dir : {get_model_cache_dir()}")
    print(f"  Models    : {len(models)}")
    print(f"  Mode      : {'verify only' if args.verify else 'download + test'}")
    print("=" * 64)

    if args.verify:
        print("\n  Cache status:\n")
        results = [download_model(m, verify_only=True) for m in models]
        cached  = sum(1 for r in results if r["success"])
        print(f"\n  {cached}/{len(results)} models are cached.")
        return 0 if cached == len(results) else 1

    # ── Sequential download ───────────────────────────────────────────────
    # IMPORTANT: do NOT parallelize — each download must fully complete before
    # the next starts to prevent the [Errno 17] / zip_tmp race conditions.
    print(f"\n  Downloading {len(models)} model(s) sequentially…")
    print("  (Running one at a time to avoid race conditions)\n")

    results = []
    for i, model in enumerate(models, 1):
        print(f"\n[{i}/{len(models)}]", end="")
        if not args.force and _model_dir_exists(model["am"], model["lang"]):
            print(f"  Skipping '{model['name']}' — already cached.")
            print("  (Use --force to re-download and re-test)")
            results.append({"name": model["name"], "success": True,
                            "skipped": True, "elapsed": 0})
            continue
        result = download_model(model)
        results.append(result)

    # ── Summary ───────────────────────────────────────────────────────────
    ok      = [r for r in results if r["success"]]
    failed  = [r for r in results if not r["success"]]
    skipped = [r for r in results if r.get("skipped") and r["success"]]

    print("\n" + "=" * 64)
    print("  SUMMARY")
    print("=" * 64)
    for r in results:
        if r["success"]:
            note = " (already cached, skipped)" if r.get("skipped") else f"  ({r.get('elapsed', 0):.1f}s)"
            print(f"  ✓  {r['name']}{note}")
        else:
            print(f"  ✗  {r['name']}")
            print(f"       Error: {r.get('error', 'unknown')}")

    print(f"\n  Result: {len(ok)}/{len(results)} models ready"
          + (f"  ({len(skipped)} already cached)" if skipped else ""))

    if failed:
        print("\n  ⚠  Some models failed. Common causes:")
        print("     • Network timeout — try again or check your connection")
        print("     • Disk full — PaddleSpeech models are ~400 MB each")
        print("     • Stale zip_tmp file — run with --force to clean and retry")
        print("=" * 64)
        return 1

    print("\n  ✓ All models ready. You can now run:")
    print("    python main.py --file doc.txt --output out.wav --profile en_female")
    print("    python voice_sampler.py --lang en")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())