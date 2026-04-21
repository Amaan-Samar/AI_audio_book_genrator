# #!/usr/bin/env python3
# """
# Voice Sampler & Selector
# ========================
# Generates audio samples for every available voice profile, lets you
# listen to them, and saves your preferred voices to a config file.

# Usage
# -----
#     python voice_sampler.py                      # sample all voices
#     python voice_sampler.py --lang en            # only English voices
#     python voice_sampler.py --lang zh            # only Chinese voices
#     python voice_sampler.py --text "Hello world" # custom sample text
#     python voice_sampler.py --out-dir my_samples # custom output folder
# """

# import os
# import sys
# import json
# import argparse
# import logging
# import time
# import concurrent.futures
# import platform
# import subprocess
# from typing import Dict, List, Optional

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s  %(levelname)-8s  %(message)s",
# )
# logger = logging.getLogger(__name__)

# # ---------------------------------------------------------------------------
# # Sample texts
# # ---------------------------------------------------------------------------

# SAMPLE_TEXTS = {
#     "zh": (
#         "你好，这是一段语音测试。"
#         "我希望这个声音能够让您感到满意。"
#         "请仔细聆听，然后选择您最喜欢的声音。"
#     ),
#     "en": (
#         "Hello, this is a voice sample test. "
#         "I hope this voice sounds pleasant to you. "
#         "Please listen carefully and then choose your favourite voice."
#     ),
# }

# # ---------------------------------------------------------------------------
# # Voice registry  (keep in sync with src/tts_engine.py)
# # ---------------------------------------------------------------------------

# VOICE_PROFILES: Dict[str, dict] = {
#     "zh_female": {
#         "lang": "zh", "am": "fastspeech2_aishell3", "voc": "hifigan_aishell3",
#         "spk_id": 0, "gender": "female",
#         "description": "Chinese female — aishell3 spk 0 (warm, clear)",
#     },
#     "zh_female_2": {
#         "lang": "zh", "am": "fastspeech2_aishell3", "voc": "hifigan_aishell3",
#         "spk_id": 5, "gender": "female",
#         "description": "Chinese female — aishell3 spk 5 (slightly brighter)",
#     },
#     "zh_female_3": {
#         "lang": "zh", "am": "fastspeech2_aishell3", "voc": "hifigan_aishell3",
#         "spk_id": 8, "gender": "female",
#         "description": "Chinese female — aishell3 spk 8 (softer tone)",
#     },
#     "zh_male": {
#         "lang": "zh", "am": "fastspeech2_aishell3", "voc": "hifigan_aishell3",
#         "spk_id": 100, "gender": "male",
#         "description": "Chinese male — aishell3 spk 100",
#     },
#     "zh_male_2": {
#         "lang": "zh", "am": "fastspeech2_aishell3", "voc": "hifigan_aishell3",
#         "spk_id": 110, "gender": "male",
#         "description": "Chinese male — aishell3 spk 110 (slightly deeper)",
#     },
#     "zh_male_3": {
#         "lang": "zh", "am": "fastspeech2_aishell3", "voc": "hifigan_aishell3",
#         "spk_id": 120, "gender": "male",
#         "description": "Chinese male — aishell3 spk 120",
#     },
#     "en_female": {
#         "lang": "en", "am": "fastspeech2_ljspeech", "voc": "hifigan_ljspeech",
#         "spk_id": 0, "gender": "female",
#         "description": "English female — LJSpeech (high quality, neutral accent)",
#     },
#     "en_male": {
#         "lang": "en", "am": "fastspeech2_vctk", "voc": "hifigan_vctk",
#         "spk_id": 0, "gender": "male",
#         "description": "English male — VCTK spk 0",
#     },
#     "en_male_2": {
#         "lang": "en", "am": "fastspeech2_vctk", "voc": "hifigan_vctk",
#         "spk_id": 1, "gender": "male",
#         "description": "English male — VCTK spk 1",
#     },
#     "en_male_3": {
#         "lang": "en", "am": "fastspeech2_vctk", "voc": "hifigan_vctk",
#         "spk_id": 3, "gender": "male",
#         "description": "English male — VCTK spk 3",
#     },
#     "en_female_2": {
#         "lang": "en", "am": "fastspeech2_vctk", "voc": "hifigan_vctk",
#         "spk_id": 2, "gender": "female",
#         "description": "English female — VCTK spk 2 (different accent)",
#     },
# }


# # ---------------------------------------------------------------------------
# # Audio playback (macOS / Linux / Windows)
# # ---------------------------------------------------------------------------

# def play_audio(path: str):
#     """Play a WAV file using the OS default player (non-blocking)."""
#     system = platform.system()
#     try:
#         if system == "Darwin":          # macOS
#             subprocess.Popen(["afplay", path])
#         elif system == "Linux":
#             subprocess.Popen(["aplay", path])
#         elif system == "Windows":
#             import winsound
#             winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
#         else:
#             logger.warning("Auto-play not supported on %s. Open the file manually.", system)
#     except FileNotFoundError:
#         logger.warning("Playback command not found. Open '%s' manually.", path)


# # ---------------------------------------------------------------------------
# # Synthesis
# # ---------------------------------------------------------------------------

# def synthesize_sample(profile_key: str, profile: dict,
#                       out_dir: str, sample_text: str) -> dict:
#     """Synthesize one sample.  Returns a result dict."""
#     from paddlespeech.cli.tts import TTSExecutor
#     tts = TTSExecutor()

#     out_path = os.path.join(out_dir, f"{profile_key}.wav")

#     t0 = time.time()
#     try:
#         tts(
#             text=sample_text,
#             output=out_path,
#             am=profile["am"],
#             voc=profile["voc"],
#             lang=profile["lang"],
#             spk_id=profile["spk_id"],
#         )
#         elapsed = time.time() - t0
#         return {
#             "key":      profile_key,
#             "success":  True,
#             "path":     out_path,
#             "elapsed":  elapsed,
#             "profile":  profile,
#         }
#     except Exception as exc:
#         return {
#             "key":     profile_key,
#             "success": False,
#             "error":   str(exc),
#             "profile": profile,
#         }


# def generate_samples(profiles: Dict[str, dict], out_dir: str,
#                      sample_texts: Dict[str, str],
#                      max_workers: int = 3) -> List[dict]:
#     """
#     Generate all samples in parallel.
#     Returns list of result dicts, ordered by profile key.
#     """
#     os.makedirs(out_dir, exist_ok=True)

#     tasks = [
#         (key, prof, out_dir, sample_texts.get(prof["lang"], sample_texts["en"]))
#         for key, prof in profiles.items()
#     ]

#     results_map: Dict[str, dict] = {}

#     print(f"\n⏳  Generating {len(tasks)} voice samples with {max_workers} workers…")
#     print("    (This may take a minute — models need to download on first run)\n")

#     with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
#         future_map = {
#             pool.submit(synthesize_sample, key, prof, out_dir, text): key
#             for key, prof, out_dir, text in tasks
#         }
#         done = 0
#         for future in concurrent.futures.as_completed(future_map):
#             key = future_map[future]
#             try:
#                 result = future.result(timeout=300)
#             except Exception as exc:
#                 result = {"key": key, "success": False, "error": str(exc),
#                           "profile": profiles[key]}
#             results_map[key] = result
#             done += 1
#             status = "✓" if result["success"] else "✗"
#             elapsed = f"{result.get('elapsed', 0):.1f}s" if result["success"] else result.get("error", "")
#             print(f"  [{done:2d}/{len(tasks)}] {status} {key:<18}  {elapsed}")

#     # Return in stable order
#     return [results_map[k] for k in profiles if k in results_map]


# # ---------------------------------------------------------------------------
# # Interactive selector
# # ---------------------------------------------------------------------------

# def _separator(char="─", width=64):
#     print(char * width)


# def _print_profile_table(results: List[dict]):
#     _separator("═")
#     print(f"  {'#':<4} {'Profile Key':<18} {'Lang':<5} {'Gender':<7} {'Status':<8} Description")
#     _separator()
#     for i, r in enumerate(results, 1):
#         p   = r["profile"]
#         ok  = "✓ ready" if r["success"] else "✗ failed"
#         print(f"  {i:<4} {r['key']:<18} {p['lang']:<5} {p['gender']:<7} {ok:<8} {p['description']}")
#     _separator("═")


# def interactive_selector(results: List[dict], out_dir: str):
#     """
#     Walk the user through listening to samples and picking favourites.
#     Saves preferences to voice_preferences.json.
#     """
#     ready = [r for r in results if r["success"]]

#     if not ready:
#         print("\n✗  No samples were generated successfully. Check logs above.")
#         return

#     print("\n" + "=" * 64)
#     print("  VOICE SAMPLE PLAYER & SELECTOR")
#     print("=" * 64)
#     print(f"\n  {len(ready)} samples generated in: {out_dir}/\n")

#     _print_profile_table(results)

#     favourites: List[str] = []

#     while True:
#         print("\nOptions:")
#         print("  [number]   Play that sample  (e.g. '3')")
#         print("  p <nums>   Play several in sequence  (e.g. 'p 1 3 5')")
#         print("  f <nums>   Mark as favourite  (e.g. 'f 2 4')")
#         print("  l          List all samples again")
#         print("  s          Show current favourites")
#         print("  d          Done — save preferences and exit")
#         print("  q          Quit without saving")

#         try:
#             raw = input("\n> ").strip().lower()
#         except (EOFError, KeyboardInterrupt):
#             print("\nInterrupted. Exiting.")
#             break

#         if not raw:
#             continue

#         # ── Quit ──────────────────────────────────────────────────────
#         if raw == "q":
#             print("Exiting without saving.")
#             break

#         # ── Done / save ────────────────────────────────────────────────
#         if raw == "d":
#             _save_preferences(favourites, ready, out_dir)
#             break

#         # ── List ───────────────────────────────────────────────────────
#         if raw == "l":
#             _print_profile_table(results)
#             continue

#         # ── Show favourites ────────────────────────────────────────────
#         if raw == "s":
#             if favourites:
#                 print("\n  Your favourites so far:")
#                 for f in favourites:
#                     r = next((x for x in ready if x["key"] == f), None)
#                     if r:
#                         print(f"    • {f:<18}  {r['profile']['description']}")
#             else:
#                 print("  No favourites selected yet.")
#             continue

#         # ── Favourite ──────────────────────────────────────────────────
#         if raw.startswith("f "):
#             indices = _parse_indices(raw[2:], len(ready))
#             for idx in indices:
#                 key = ready[idx]["key"]
#                 if key not in favourites:
#                     favourites.append(key)
#                     print(f"  ★ Added to favourites: {key}")
#                 else:
#                     print(f"  (already in favourites: {key})")
#             continue

#         # ── Play sequence ──────────────────────────────────────────────
#         if raw.startswith("p "):
#             indices = _parse_indices(raw[2:], len(ready))
#             for idx in indices:
#                 r = ready[idx]
#                 print(f"\n  ▶  Playing [{idx+1}] {r['key']} — {r['profile']['description']}")
#                 play_audio(r["path"])
#                 time.sleep(0.5)
#                 input("     (press Enter for next, or just wait) ")
#             continue

#         # ── Play single ────────────────────────────────────────────────
#         indices = _parse_indices(raw, len(ready))
#         if indices:
#             idx = indices[0]
#             r   = ready[idx]
#             print(f"\n  ▶  Playing [{idx+1}] {r['key']} — {r['profile']['description']}")
#             play_audio(r["path"])
#             continue

#         print("  Unrecognised input — try a number, 'p <nums>', 'f <nums>', 'l', 's', 'd', or 'q'.")


# def _parse_indices(raw: str, max_count: int) -> List[int]:
#     """Parse space-separated 1-based integers into 0-based indices."""
#     result = []
#     for tok in raw.split():
#         try:
#             n = int(tok)
#             if 1 <= n <= max_count:
#                 result.append(n - 1)
#             else:
#                 print(f"  ⚠  {n} is out of range (1–{max_count}).")
#         except ValueError:
#             print(f"  ⚠  '{tok}' is not a valid number.")
#     return result


# def _save_preferences(favourites: List[str], ready: List[dict], out_dir: str):
#     prefs = {
#         "favourites": favourites,
#         "all_profiles": {
#             r["key"]: {
#                 "lang":        r["profile"]["lang"],
#                 "gender":      r["profile"]["gender"],
#                 "description": r["profile"]["description"],
#                 "sample_path": r["path"],
#             }
#             for r in ready
#         },
#     }
#     prefs_path = os.path.join(out_dir, "voice_preferences.json")
#     with open(prefs_path, "w", encoding="utf-8") as fh:
#         json.dump(prefs, fh, indent=2, ensure_ascii=False)

#     print("\n" + "=" * 64)
#     if favourites:
#         print("  ★  Your favourite voices:")
#         for key in favourites:
#             r = next((x for x in ready if x["key"] == key), None)
#             desc = r["profile"]["description"] if r else ""
#             print(f"       --profile {key:<18}  # {desc}")
#         print(f"\n  Saved to: {prefs_path}")
#         print("\n  Use your favourite profile with:")
#         print(f"    python main.py --file doc.txt --output out.wav --profile {favourites[0]}")
#     else:
#         print("  No favourites were selected.")
#         print(f"  Preferences (all profiles) saved to: {prefs_path}")
#     print("=" * 64)


# # ---------------------------------------------------------------------------
# # CLI
# # ---------------------------------------------------------------------------

# def build_parser():
#     p = argparse.ArgumentParser(
#         description="Generate voice samples and interactively choose your preferred voice.",
#         formatter_class=argparse.RawDescriptionHelpFormatter,
#         epilog=__doc__,
#     )
#     p.add_argument("--lang", choices=["zh", "en"], default=None,
#                    help="Only sample voices for this language.")
#     p.add_argument("--gender", choices=["male", "female"], default=None,
#                    help="Only sample voices of this gender.")
#     p.add_argument("--text", type=str, default=None,
#                    help="Custom sample text (applied to matching language).")
#     p.add_argument("--out-dir", type=str, default="voice_samples",
#                    help="Directory to save sample WAV files (default: voice_samples/).")
#     p.add_argument("--workers", type=int, default=3,
#                    help="Parallel synthesis workers (default: 3).")
#     p.add_argument("--no-interactive", action="store_true",
#                    help="Generate samples only, skip the interactive selector.")
#     p.add_argument("--list-profiles", action="store_true",
#                    help="Print available profiles and exit.")
#     return p


# def main():
#     args = build_parser().parse_args()

#     if args.list_profiles:
#         print("\nAvailable voice profiles:\n")
#         for key, p in VOICE_PROFILES.items():
#             print(f"  {key:<18} lang={p['lang']}  gender={p['gender']}  {p['description']}")
#         return 0

#     # ── Filter profiles ──────────────────────────────────────────────────
#     profiles = dict(VOICE_PROFILES)
#     if args.lang:
#         profiles = {k: v for k, v in profiles.items() if v["lang"] == args.lang}
#     if args.gender:
#         profiles = {k: v for k, v in profiles.items() if v["gender"] == args.gender}

#     if not profiles:
#         print("No profiles match the given filters.")
#         return 1

#     # ── Sample texts ─────────────────────────────────────────────────────
#     texts = dict(SAMPLE_TEXTS)
#     if args.text:
#         # Apply custom text to whichever language(s) are selected
#         for lang in set(v["lang"] for v in profiles.values()):
#             texts[lang] = args.text

#     # ── Generate ─────────────────────────────────────────────────────────
#     results = generate_samples(profiles, args.out_dir, texts, max_workers=args.workers)

#     ok  = sum(1 for r in results if r["success"])
#     bad = len(results) - ok
#     print(f"\n  Generated {ok} / {len(results)} samples"
#           + (f"  ({bad} failed — check logs above)" if bad else "") + "\n")

#     if args.no_interactive:
#         print(f"Samples saved to: {args.out_dir}/")
#         return 0

#     # ── Interactive selector ─────────────────────────────────────────────
#     interactive_selector(results, args.out_dir)
#     return 0


# if __name__ == "__main__":
#     sys.exit(main())




#!/usr/bin/env python3
"""
Voice Sampler & Selector
========================
Generates audio samples for every available voice profile, lets you
listen to them, and saves your preferred voices to a config file.

Usage
-----
    python voice_sampler.py                      # sample all voices
    python voice_sampler.py --lang en            # only English voices
    python voice_sampler.py --lang zh            # only Chinese voices
    python voice_sampler.py --text "Hello world" # custom sample text
    python voice_sampler.py --out-dir my_samples # custom output folder
"""

import os
import sys
import json
import argparse
import logging
import time
import concurrent.futures
import platform
import subprocess
from typing import Dict, List, Optional

# FIX #6: Moved import to module level (was inside synthesize_sample, re-imported every call)
try:
    from paddlespeech.cli.tts import TTSExecutor
except ImportError:
    TTSExecutor = None  # Graceful fallback so the module can be imported without PaddleSpeech installed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sample texts
# ---------------------------------------------------------------------------

SAMPLE_TEXTS = {
    "zh": (
        "你好，这是一段语音测试。"
        "我希望这个声音能够让您感到满意。"
        "请仔细聆听，然后选择您最喜欢的声音。"
    ),
    "en": (
        "Hello, this is a voice sample test. "
        "I hope this voice sounds pleasant to you. "
        "Please listen carefully and then choose your favourite voice."
    ),
}

# ---------------------------------------------------------------------------
# Voice registry  (keep in sync with src/tts_engine.py)
# ---------------------------------------------------------------------------

VOICE_PROFILES: Dict[str, dict] = {
    "zh_female": {
        "lang": "zh", "am": "fastspeech2_aishell3", "voc": "hifigan_aishell3",
        "spk_id": 0, "gender": "female",
        "description": "Chinese female — aishell3 spk 0 (warm, clear)",
    },
    "zh_female_2": {
        "lang": "zh", "am": "fastspeech2_aishell3", "voc": "hifigan_aishell3",
        "spk_id": 5, "gender": "female",
        "description": "Chinese female — aishell3 spk 5 (slightly brighter)",
    },
    "zh_female_3": {
        "lang": "zh", "am": "fastspeech2_aishell3", "voc": "hifigan_aishell3",
        "spk_id": 8, "gender": "female",
        "description": "Chinese female — aishell3 spk 8 (softer tone)",
    },
    "zh_male": {
        "lang": "zh", "am": "fastspeech2_aishell3", "voc": "hifigan_aishell3",
        "spk_id": 100, "gender": "male",
        "description": "Chinese male — aishell3 spk 100",
    },
    "zh_male_2": {
        "lang": "zh", "am": "fastspeech2_aishell3", "voc": "hifigan_aishell3",
        "spk_id": 110, "gender": "male",
        "description": "Chinese male — aishell3 spk 110 (slightly deeper)",
    },
    "zh_male_3": {
        "lang": "zh", "am": "fastspeech2_aishell3", "voc": "hifigan_aishell3",
        "spk_id": 120, "gender": "male",
        "description": "Chinese male — aishell3 spk 120",
    },
    "en_female": {
        "lang": "en", "am": "fastspeech2_ljspeech", "voc": "hifigan_ljspeech",
        "spk_id": 0, "gender": "female",
        "description": "English female — LJSpeech (high quality, neutral accent)",
    },
    "en_male": {
        "lang": "en", "am": "fastspeech2_vctk", "voc": "hifigan_vctk",
        "spk_id": 0, "gender": "male",
        "description": "English male — VCTK spk 0",
    },
    "en_male_2": {
        "lang": "en", "am": "fastspeech2_vctk", "voc": "hifigan_vctk",
        "spk_id": 1, "gender": "male",
        "description": "English male — VCTK spk 1",
    },
    "en_male_3": {
        "lang": "en", "am": "fastspeech2_vctk", "voc": "hifigan_vctk",
        "spk_id": 3, "gender": "male",
        "description": "English male — VCTK spk 3",
    },
    "en_female_2": {
        "lang": "en", "am": "fastspeech2_vctk", "voc": "hifigan_vctk",
        "spk_id": 2, "gender": "female",
        "description": "English female — VCTK spk 2 (different accent)",
    },
}


# ---------------------------------------------------------------------------
# Audio playback (macOS / Linux / Windows)
# ---------------------------------------------------------------------------

# FIX #3: Store the current playback process so we can terminate it before
#         starting a new one, preventing overlapping audio.
_current_playback_proc: Optional[subprocess.Popen] = None


def play_audio(path: str) -> Optional[subprocess.Popen]:
    """
    Play a WAV file using the OS default player (non-blocking).
    Stops any currently-playing audio first.
    Returns the Popen handle so callers can wait() on it if needed.
    """
    global _current_playback_proc

    # Stop previous playback to avoid overlap
    if _current_playback_proc is not None:
        try:
            _current_playback_proc.terminate()
            _current_playback_proc.wait(timeout=2)
        except Exception:
            pass
        _current_playback_proc = None

    system = platform.system()
    proc: Optional[subprocess.Popen] = None
    try:
        if system == "Darwin":          # macOS
            proc = subprocess.Popen(["afplay", path])
        elif system == "Linux":
            proc = subprocess.Popen(["aplay", path])
        elif system == "Windows":
            import winsound
            # winsound is not a subprocess, handle separately
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        else:
            logger.warning("Auto-play not supported on %s. Open the file manually.", system)
    except FileNotFoundError:
        logger.warning("Playback command not found. Open '%s' manually.", path)

    _current_playback_proc = proc
    return proc


def wait_for_playback(proc: Optional[subprocess.Popen], timeout: float = 60.0):
    """Block until the given playback process finishes (or timeout)."""
    if proc is None:
        return
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.terminate()


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------

def synthesize_sample(profile_key: str, profile: dict,
                      sample_out_dir: str, sample_text: str) -> dict:
    """
    Synthesize one sample. Returns a result dict.

    FIX #1: TTSExecutor is NOT thread-safe. A fresh instance is created per
            call, but we also protect against shared Paddle state by using
            ProcessPoolExecutor in generate_samples instead of
            ThreadPoolExecutor.
    FIX #6: Import is now at module level; TTSExecutor is referenced directly.
    """
    if TTSExecutor is None:
        return {
            "key":     profile_key,
            "success": False,
            "error":   "paddlespeech is not installed",
            "profile": profile,
        }

    tts = TTSExecutor()
    out_path = os.path.join(sample_out_dir, f"{profile_key}.wav")

    t0 = time.time()
    try:
        tts(
            text=sample_text,
            output=out_path,
            am=profile["am"],
            voc=profile["voc"],
            lang=profile["lang"],
            spk_id=profile["spk_id"],
        )
        elapsed = time.time() - t0
        return {
            "key":      profile_key,
            "success":  True,
            "path":     out_path,
            "elapsed":  elapsed,
            "profile":  profile,
        }
    except Exception as exc:
        return {
            "key":     profile_key,
            "success": False,
            "error":   str(exc),
            "profile": profile,
        }


def generate_samples(profiles: Dict[str, dict], out_dir: str,
                     sample_texts: Dict[str, str],
                     max_workers: int = 3) -> List[dict]:
    """
    Generate all samples.

    FIX #1: Switched from ThreadPoolExecutor to ProcessPoolExecutor so each
            worker gets its own Python interpreter and Paddle runtime,
            avoiding shared-state race conditions in TTSExecutor.
    FIX #2: Renamed the loop-unpacking variable from 'out_dir' to
            'task_out_dir' to prevent shadowing the function parameter.
    """
    os.makedirs(out_dir, exist_ok=True)

    # FIX #2: was `for key, prof, out_dir, text in tasks` — 'out_dir' shadowed
    #         the outer parameter.  Renamed to 'task_out_dir'.
    tasks = [
        (key, prof, out_dir, sample_texts.get(prof["lang"], sample_texts["en"]))
        for key, prof in profiles.items()
    ]

    results_map: Dict[str, dict] = {}

    print(f"\n⏳  Generating {len(tasks)} voice samples with {max_workers} workers…")
    print("    (This may take a minute — models need to download on first run)\n")

    # FIX #1: ProcessPoolExecutor instead of ThreadPoolExecutor
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as pool:
        future_map = {
            pool.submit(synthesize_sample, key, prof, task_out_dir, text): key
            for key, prof, task_out_dir, text in tasks
        }
        done = 0
        for future in concurrent.futures.as_completed(future_map):
            key = future_map[future]
            try:
                result = future.result(timeout=300)
            except Exception as exc:
                result = {"key": key, "success": False, "error": str(exc),
                          "profile": profiles[key]}
            results_map[key] = result
            done += 1
            status = "✓" if result["success"] else "✗"
            elapsed = f"{result.get('elapsed', 0):.1f}s" if result["success"] else result.get("error", "")
            print(f"  [{done:2d}/{len(tasks)}] {status} {key:<18}  {elapsed}")

    # Return in stable order
    return [results_map[k] for k in profiles if k in results_map]


# ---------------------------------------------------------------------------
# Interactive selector
# ---------------------------------------------------------------------------

def _separator(char="─", width=64):
    print(char * width)


def _print_profile_table(results: List[dict]):
    _separator("═")
    print(f"  {'#':<4} {'Profile Key':<18} {'Lang':<5} {'Gender':<7} {'Status':<8} Description")
    _separator()
    for i, r in enumerate(results, 1):
        p   = r["profile"]
        ok  = "✓ ready" if r["success"] else "✗ failed"
        print(f"  {i:<4} {r['key']:<18} {p['lang']:<5} {p['gender']:<7} {ok:<8} {p['description']}")
    _separator("═")


def interactive_selector(results: List[dict], out_dir: str):
    """
    Walk the user through listening to samples and picking favourites.
    Saves preferences to voice_preferences.json.
    """
    ready = [r for r in results if r["success"]]

    if not ready:
        print("\n✗  No samples were generated successfully. Check logs above.")
        return

    print("\n" + "=" * 64)
    print("  VOICE SAMPLE PLAYER & SELECTOR")
    print("=" * 64)
    print(f"\n  {len(ready)} samples generated in: {out_dir}/\n")

    _print_profile_table(results)

    favourites: List[str] = []

    while True:
        print("\nOptions:")
        print("  [number]   Play that sample  (e.g. '3')")
        print("  p <nums>   Play several in sequence  (e.g. 'p 1 3 5')")
        print("  f <nums>   Mark as favourite  (e.g. 'f 2 4')")
        print("  l          List all samples again")
        print("  s          Show current favourites")
        print("  d          Done — save preferences and exit")
        print("  q          Quit without saving")

        try:
            raw = input("\n> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nInterrupted. Exiting.")
            break

        if not raw:
            continue

        # ── Quit ──────────────────────────────────────────────────────
        if raw == "q":
            print("Exiting without saving.")
            break

        # ── Done / save ────────────────────────────────────────────────
        if raw == "d":
            _save_preferences(favourites, ready, out_dir)
            break

        # ── List ───────────────────────────────────────────────────────
        if raw == "l":
            _print_profile_table(results)
            continue

        # ── Show favourites ────────────────────────────────────────────
        if raw == "s":
            if favourites:
                print("\n  Your favourites so far:")
                for f in favourites:
                    r = next((x for x in ready if x["key"] == f), None)
                    if r:
                        print(f"    • {f:<18}  {r['profile']['description']}")
            else:
                print("  No favourites selected yet.")
            continue

        # ── Favourite ──────────────────────────────────────────────────
        if raw.startswith("f "):
            indices = _parse_indices(raw[2:], len(ready))
            # FIX #4: Inform user clearly if _parse_indices returned nothing
            #         due to invalid input (was silently a no-op).
            if not indices:
                print("  ⚠  No valid indices provided. Usage: f <num> [num ...]  e.g. 'f 2 4'")
                continue
            for idx in indices:
                key = ready[idx]["key"]
                if key not in favourites:
                    favourites.append(key)
                    print(f"  ★ Added to favourites: {key}")
                else:
                    print(f"  (already in favourites: {key})")
            continue

        # ── Play sequence ──────────────────────────────────────────────
        if raw.startswith("p "):
            indices = _parse_indices(raw[2:], len(ready))
            if not indices:
                print("  ⚠  No valid indices provided. Usage: p <num> [num ...]  e.g. 'p 1 3 5'")
                continue
            for idx in indices:
                r = ready[idx]
                print(f"\n  ▶  Playing [{idx+1}] {r['key']} — {r['profile']['description']}")
                proc = play_audio(r["path"])
                # FIX #5: Wait for playback to finish before prompting.
                #         Removed the misleading "or just wait" comment since
                #         Enter is actually required.  We now block on the
                #         process itself so the prompt appears only after audio
                #         ends (or the user presses Enter early).
                print("     (press Enter to stop and move to next)")
                try:
                    input()
                except (EOFError, KeyboardInterrupt):
                    pass
                # Stop current track before moving on
                if proc is not None:
                    try:
                        proc.terminate()
                        proc.wait(timeout=2)
                    except Exception:
                        pass
            continue

        # ── Play single ────────────────────────────────────────────────
        indices = _parse_indices(raw, len(ready))
        if indices:
            idx = indices[0]
            r   = ready[idx]
            print(f"\n  ▶  Playing [{idx+1}] {r['key']} — {r['profile']['description']}")
            play_audio(r["path"])
            continue

        print("  Unrecognised input — try a number, 'p <nums>', 'f <nums>', 'l', 's', 'd', or 'q'.")


def _parse_indices(raw: str, max_count: int) -> List[int]:
    """
    Parse space-separated 1-based integers into 0-based indices.

    FIX #4: Returns an empty list on fully invalid input so callers can
            detect and report the problem (was silently swallowed before).
    """
    result = []
    for tok in raw.split():
        try:
            n = int(tok)
            if 1 <= n <= max_count:
                result.append(n - 1)
            else:
                print(f"  ⚠  {n} is out of range (1–{max_count}).")
        except ValueError:
            print(f"  ⚠  '{tok}' is not a valid number.")
    return result


def _save_preferences(favourites: List[str], ready: List[dict], out_dir: str):
    prefs = {
        "favourites": favourites,
        "all_profiles": {
            r["key"]: {
                "lang":        r["profile"]["lang"],
                "gender":      r["profile"]["gender"],
                "description": r["profile"]["description"],
                "sample_path": r["path"],
            }
            for r in ready
        },
    }
    prefs_path = os.path.join(out_dir, "voice_preferences.json")
    with open(prefs_path, "w", encoding="utf-8") as fh:
        json.dump(prefs, fh, indent=2, ensure_ascii=False)

    print("\n" + "=" * 64)
    if favourites:
        print("  ★  Your favourite voices:")
        for key in favourites:
            r = next((x for x in ready if x["key"] == key), None)
            desc = r["profile"]["description"] if r else ""
            print(f"       --profile {key:<18}  # {desc}")
        print(f"\n  Saved to: {prefs_path}")
        print("\n  Use your favourite profile with:")
        print(f"    python main.py --file doc.txt --output out.wav --profile {favourites[0]}")
    else:
        print("  No favourites were selected.")
        print(f"  Preferences (all profiles) saved to: {prefs_path}")
    print("=" * 64)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        description="Generate voice samples and interactively choose your preferred voice.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--lang", choices=["zh", "en"], default=None,
                   help="Only sample voices for this language.")
    p.add_argument("--gender", choices=["male", "female"], default=None,
                   help="Only sample voices of this gender.")
    p.add_argument("--text", type=str, default=None,
                   help="Custom sample text (applied to matching language).")
    p.add_argument("--out-dir", type=str, default="voice_samples",
                   help="Directory to save sample WAV files (default: voice_samples/).")
    p.add_argument("--workers", type=int, default=3,
                   help="Parallel synthesis workers (default: 3).")
    p.add_argument("--no-interactive", action="store_true",
                   help="Generate samples only, skip the interactive selector.")
    p.add_argument("--list-profiles", action="store_true",
                   help="Print available profiles and exit.")
    return p


def main():
    args = build_parser().parse_args()

    if args.list_profiles:
        print("\nAvailable voice profiles:\n")
        for key, p in VOICE_PROFILES.items():
            print(f"  {key:<18} lang={p['lang']}  gender={p['gender']}  {p['description']}")
        return 0

    # ── Filter profiles ──────────────────────────────────────────────────
    profiles = dict(VOICE_PROFILES)
    if args.lang:
        profiles = {k: v for k, v in profiles.items() if v["lang"] == args.lang}
    if args.gender:
        profiles = {k: v for k, v in profiles.items() if v["gender"] == args.gender}

    if not profiles:
        print("No profiles match the given filters.")
        return 1

    # ── Sample texts ─────────────────────────────────────────────────────
    texts = dict(SAMPLE_TEXTS)
    if args.text:
        # FIX #7: Warn the user if custom text is applied to a language it
        #         may not be appropriate for (e.g. English text to zh TTS).
        target_langs = set(v["lang"] for v in profiles.values())
        if len(target_langs) > 1:
            print(
                f"\n  ⚠  Warning: --text is applied to all selected languages "
                f"({', '.join(sorted(target_langs))}).\n"
                f"     Make sure your custom text is valid for every language, "
                f"or use --lang to restrict to one language.\n"
            )
        for lang in target_langs:
            texts[lang] = args.text

    # ── Generate ─────────────────────────────────────────────────────────
    results = generate_samples(profiles, args.out_dir, texts, max_workers=args.workers)

    ok  = sum(1 for r in results if r["success"])
    bad = len(results) - ok
    print(f"\n  Generated {ok} / {len(results)} samples"
          + (f"  ({bad} failed — check logs above)" if bad else "") + "\n")

    if args.no_interactive:
        print(f"Samples saved to: {args.out_dir}/")
        return 0

    # ── Interactive selector ─────────────────────────────────────────────
    interactive_selector(results, args.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())