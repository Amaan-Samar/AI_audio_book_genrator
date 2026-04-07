import os
import logging
import time
import re
from typing import Dict, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Voice profile registry
# ---------------------------------------------------------------------------
# PaddleSpeech models used:
#   Chinese  → fastspeech2_aishell3  (174 speakers, mixed gender)
#   English  → fastspeech2_ljspeech  (single female, best quality)
#              fastspeech2_vctk       (109 speakers, mixed gender)
#
# Speaker IDs verified by the PaddleSpeech team:
#   aishell3  : 0–8   → female,  9–99  → mixed, 100–173 → male
#   vctk      : even IDs generally female, odd IDs generally male
#                p225(0), p226(1)… use spk_id index not raw p-number
# ---------------------------------------------------------------------------

VOICE_PROFILES: Dict[str, dict] = {
    # ── Chinese ──────────────────────────────────────────────────────────
    "zh_female": {
        "lang": "zh",
        "am": "fastspeech2_aishell3",
        "voc": "hifigan_aishell3",
        "spk_id": 0,
        "description": "Chinese female (aishell3 spk 0)",
    },
    "zh_female_2": {
        "lang": "zh",
        "am": "fastspeech2_aishell3",
        "voc": "hifigan_aishell3",
        "spk_id": 5,
        "description": "Chinese female variant (aishell3 spk 5)",
    },
    "zh_male": {
        "lang": "zh",
        "am": "fastspeech2_aishell3",
        "voc": "hifigan_aishell3",
        "spk_id": 100,
        "description": "Chinese male (aishell3 spk 100)",
    },
    "zh_male_2": {
        "lang": "zh",
        "am": "fastspeech2_aishell3",
        "voc": "hifigan_aishell3",
        "spk_id": 110,
        "description": "Chinese male variant (aishell3 spk 110)",
    },
    # ── English ──────────────────────────────────────────────────────────
    # ljspeech: single high-quality female speaker — best for English narration
    "en_female": {
        "lang": "en",
        "am": "fastspeech2_ljspeech",
        "voc": "hifigan_ljspeech",
        "spk_id": 0,
        "description": "English female – LJSpeech (high quality)",
    },
    # vctk: multi-speaker model — gives us a usable male voice
    "en_male": {
        "lang": "en",
        "am": "fastspeech2_vctk",
        "voc": "hifigan_vctk",
        "spk_id": 0,          # p225 → female; try spk_id=1 (p226) for male-ish
        "description": "English male – VCTK spk 0",
    },
    "en_male_2": {
        "lang": "en",
        "am": "fastspeech2_vctk",
        "voc": "hifigan_vctk",
        "spk_id": 1,
        "description": "English male variant – VCTK spk 1",
    },

    "en_male_3": {
        "lang": "en", 
        "am": "fastspeech2_vctk", 
        "voc": "hifigan_vctk",
        "spk_id": 2, 
        "gender": "male",
        "description": "English male — VCTK spk 2 (different accent)",
    },

    
}

# Convenience aliases
VOICE_PROFILES["default"]    = VOICE_PROFILES["zh_female"]
VOICE_PROFILES["female"]     = VOICE_PROFILES["zh_female"]
VOICE_PROFILES["male"]       = VOICE_PROFILES["zh_male"]
VOICE_PROFILES["en_default"] = VOICE_PROFILES["en_female"]


def detect_language(text: str) -> str:
    """
    Heuristic: if >20 % of characters are CJK, treat as Chinese.
    Returns 'zh' or 'en'.
    """
    if not text:
        return "en"
    cjk = sum(1 for ch in text if '\u4e00' <= ch <= '\u9fff')
    return "zh" if cjk / len(text) > 0.2 else "en"


class ChineseTTSEngine:
    """
    Unified TTS engine for Chinese and English using PaddleSpeech.
    Thread-safe: each thread gets its own TTSExecutor via thread-local storage.
    """

    def __init__(self):
        logger.info("Initializing PaddleSpeech TTS Engine…")
        # Lazy import so the module loads even if PaddleSpeech isn't installed yet
        from paddlespeech.cli.tts import TTSExecutor  # noqa: F401 – just verify import
        self._TTSExecutor = TTSExecutor

        import threading
        self._local = threading.local()
        self.voice_profiles = VOICE_PROFILES
        logger.info("✓ TTS Engine ready.  Profiles: %s", ", ".join(VOICE_PROFILES))

    # ------------------------------------------------------------------
    def _get_tts(self):
        """Return a thread-local TTSExecutor, creating it on first use."""
        if not hasattr(self._local, "tts"):
            self._local.tts = self._TTSExecutor()
        return self._local.tts

    # ------------------------------------------------------------------
    def resolve_profile(self, voice_profile: Optional[str], text: str = "") -> dict:
        """
        Return the voice profile dict to use.
        Falls back to auto-detection when voice_profile is None or unknown.
        """
        if voice_profile and voice_profile in self.voice_profiles:
            return self.voice_profiles[voice_profile]
        # Auto-detect from text
        lang = detect_language(text)
        fallback = "zh_female" if lang == "zh" else "en_female"
        if voice_profile:
            logger.warning("Profile '%s' not found — falling back to '%s'.", voice_profile, fallback)
        return self.voice_profiles[fallback]

    # ------------------------------------------------------------------
    def synthesize(self, text: str, output_path: str,
                   speed: float = 1.0,
                   voice_profile: Optional[str] = None) -> dict:
        """
        Synthesize *text* to a WAV file at *output_path*.

        Args:
            text:          Text to synthesize (Chinese or English).
            output_path:   Destination .wav file path.
            speed:         Placeholder – not yet supported by all PS models.
            voice_profile: Key from VOICE_PROFILES, or None for auto-detect.

        Returns:
            dict with keys: success, output_path, processing_time, …
        """
        profile = self.resolve_profile(voice_profile, text)
        tts = self._get_tts()

        preview = text[:60].replace("\n", " ")
        logger.info("Synthesizing [%s] '%s…'  profile=%s spk=%s",
                    profile["lang"], preview, profile["description"], profile["spk_id"])

        os.makedirs(
            os.path.dirname(output_path) if os.path.dirname(output_path) else ".",
            exist_ok=True,
        )

        t0 = time.time()
        try:
            tts(
                text=text,
                output=output_path,
                am=profile["am"],
                voc=profile["voc"],
                lang=profile["lang"],
                spk_id=profile["spk_id"],
            )
            elapsed = time.time() - t0
            logger.info("✓ Done in %.2fs → %s", elapsed, output_path)
            return {
                "success": True,
                "output_path": output_path,
                "processing_time": elapsed,
                "text_length": len(text),
                "model_used": profile["am"],
                "speaker_id": profile["spk_id"],
                "voice_profile": voice_profile,
                "lang": profile["lang"],
            }
        except Exception as exc:
            logger.error("✗ Synthesis failed: %s", exc)
            return {
                "success": False,
                "error": str(exc),
                "processing_time": time.time() - t0,
            }

    # ------------------------------------------------------------------
    def list_speakers(self):
        print("\n" + "=" * 72)
        print("AVAILABLE VOICE PROFILES")
        print("=" * 72)
        for name, p in self.voice_profiles.items():
            if name in ("default", "female", "male", "en_default"):
                continue  # skip aliases to keep output tidy
            print(f"  {name:<18} lang={p['lang']}  spk={p['spk_id']:<4}  {p['description']}")
        print("\nAliases:  default=zh_female  female=zh_female  male=zh_male  en_default=en_female")
        print("=" * 72)

    def get_available_options(self) -> dict:
        return {
            "voice_profiles": list(self.voice_profiles.keys()),
            "acoustic_models": [p["am"] for p in self.voice_profiles.values()],
            "vocoders":        [p["voc"] for p in self.voice_profiles.values()],
            "note": "Use zh_* profiles for Chinese, en_* profiles for English.",
        }

    def test_synthesis(self, voice_profile: str = "default") -> bool:
        profile = self.resolve_profile(voice_profile)
        if profile["lang"] == "zh":
            text = "你好，这是一个中文语音合成测试。欢迎使用PaddleSpeech。"
        else:
            text = "Hello, this is an English speech synthesis test using PaddleSpeech."

        out = f"test_{voice_profile}.wav"
        result = self.synthesize(text, out, voice_profile=voice_profile)
        if result["success"]:
            logger.info("✓ Test OK → %s", out)
            return True
        logger.error("✗ Test failed: %s", result.get("error"))
        return False