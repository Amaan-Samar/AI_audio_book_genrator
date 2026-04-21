import os
import re
import logging
import wave
import struct
import concurrent.futures
import multiprocessing
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _optimal_workers() -> int:
    """
    Conservative worker count:
    - On Apple Silicon (M1/M2/M3) PaddleSpeech already uses all CPU cores
      internally, so >4 threads often hurts throughput.
    - On Intel Macs with many cores we can push a bit higher.
    Cap at 6 to avoid memory pressure from loading multiple TTS models.
    """
    cores = multiprocessing.cpu_count()
    if cores <= 4:
        return 2
    elif cores <= 8:
        return 3
    else:
        return min(6, cores - 2)


def _combine_wav_files(file_list: List[str], output_path: str):
    """Concatenate a list of WAV files into *output_path*."""
    if not file_list:
        raise ValueError("No audio files to combine.")

    data_chunks = []
    params = None

    for fp in file_list:
        if not os.path.exists(fp):
            logger.warning("Missing audio file, skipping: %s", fp)
            continue
        try:
            with wave.open(fp, "rb") as wf:
                if params is None:
                    params = wf.getparams()
                data_chunks.append(wf.readframes(wf.getnframes()))
        except Exception as exc:
            logger.error("Could not read %s: %s", fp, exc)

    if not data_chunks:
        raise ValueError("No valid WAV data to combine.")

    with wave.open(output_path, "wb") as out:
        out.setparams(params)
        for chunk in data_chunks:
            out.writeframes(chunk)

    logger.info("Combined %d files → %s", len(data_chunks), output_path)


def _make_silence(duration_ms: int, sample_rate: int = 24000) -> bytes:
    """Return raw 16-bit mono silence frames for *duration_ms* milliseconds."""
    n_samples = int(sample_rate * duration_ms / 1000)
    return struct.pack("<h", 0) * n_samples


# ---------------------------------------------------------------------------
# Text splitting
# ---------------------------------------------------------------------------

class TextSplitter:
    """Language-aware text chunker."""

    # Chinese sentence-ending punctuation
    _ZH_SENT_RE = re.compile(r"([。！？!?\.])")
    _ZH_COMMA_RE = re.compile(r"[，,；;]")
    # English sentence endings
    _EN_SENT_RE  = re.compile(r"([.!?]+)")

    def __init__(self, max_length: int = 200):
        self.max_length = max_length

    def split(self, text: str, lang: str = "zh") -> List[str]:
        text = re.sub(r"\s+", " ", text.strip())
        if lang == "zh":
            return self._split_chinese(text)
        return self._split_english(text)

    def _split_chinese(self, text: str) -> List[str]:
        parts = self._ZH_SENT_RE.split(text)
        return self._merge_parts(parts, self._ZH_COMMA_RE)

    def _split_english(self, text: str) -> List[str]:
        parts = self._EN_SENT_RE.split(text)
        return self._merge_parts(parts, re.compile(r"[,;]"))

    def _merge_parts(self, parts: List[str], comma_re) -> List[str]:
        chunks: List[str] = []
        current = ""

        i = 0
        while i < len(parts):
            # Pair sentence body with its punctuation token (if present)
            seg = parts[i]
            if i + 1 < len(parts) and len(parts[i + 1]) <= 2:
                seg += parts[i + 1]
                i += 2
            else:
                i += 1

            seg = seg.strip()
            if not seg:
                continue

            if len(current) + len(seg) <= self.max_length:
                current = (current + " " + seg).strip() if current else seg
            else:
                if current:
                    chunks.append(current)
                if len(seg) > self.max_length:
                    # Break on commas, then hard-split as last resort
                    sub_parts = [s.strip() for s in comma_re.split(seg) if s.strip()]
                    if len(sub_parts) > 1:
                        micro = ""
                        for sp in sub_parts:
                            if len(micro) + len(sp) <= self.max_length:
                                micro = (micro + " " + sp).strip() if micro else sp
                            else:
                                if micro:
                                    chunks.append(micro)
                                micro = sp
                        current = micro
                    else:
                        for j in range(0, len(seg), self.max_length):
                            chunks.append(seg[j: j + self.max_length])
                        current = ""
                else:
                    current = seg

        if current:
            chunks.append(current)

        logger.info("Split text into %d chunks (max_len=%d)", len(chunks), self.max_length)
        return chunks


# ---------------------------------------------------------------------------
# Main processor
# ---------------------------------------------------------------------------

class DocumentProcessor:
    """
    Converts a document (plain text) to a WAV audio file using a TTS engine.

    Key improvements over the original:
    • Parallel chunk synthesis via ThreadPoolExecutor
    • Language-aware text splitting
    • Optional inter-chunk silence padding
    • Graceful partial failure handling
    """

    def __init__(self, tts_engine=None, max_workers: Optional[int] = None,
                 chunk_size: int = 200, silence_between_chunks_ms: int = 0):
        from src.tts_engine import ChineseTTSEngine
        self.tts_engine   = tts_engine or ChineseTTSEngine()
        self.max_workers  = max_workers or _optimal_workers()
        self.splitter     = TextSplitter(max_length=chunk_size)
        self.silence_ms   = silence_between_chunks_ms

        logger.info(
            "DocumentProcessor ready: workers=%d  chunk_size=%d  silence=%dms",
            self.max_workers, chunk_size, silence_between_chunks_ms,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_document(self, document_text: str, output_path: str,
                         voice_profile: Optional[str] = None,
                         lang: Optional[str] = None,
                         cleanup: bool = True,
                         subtitle_formats: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Convert *document_text* to a WAV file at *output_path*.

        Args:
            document_text:    Full text to convert.
            output_path:      Destination WAV file path.
            voice_profile:    Profile key (e.g. 'zh_female', 'en_male').
                              None → auto-detect from text.
            lang:             'zh' or 'en'.  None → auto-detect.
            cleanup:          Delete temporary chunk files after combining.
            subtitle_formats: List of subtitle formats to generate, e.g.
                              ["srt"], ["vtt"], or ["srt", "vtt"].
                              None / [] → no subtitles generated.

        Returns:
            dict with keys: success, output_path, total_chunks,
                            processed_chunks, failed_chunks, total_characters,
                            elapsed_seconds, subtitles  (and 'error' on failure).
            'subtitles' is a dict mapping format → file path, e.g.
                {"srt": "output/audio.srt", "vtt": "output/audio.vtt"}
        """
        import time
        t0 = time.time()

        # Auto-detect language if not supplied
        if lang is None:
            from src.tts_engine import detect_language
            lang = detect_language(document_text)
        logger.info("Language: %s", lang)

        # Create output directory
        out_dir = os.path.dirname(output_path) or "."
        os.makedirs(out_dir, exist_ok=True)

        # Temp dir for chunk files (alongside output)
        tmp_dir = os.path.join(out_dir, "_chunks_tmp")
        os.makedirs(tmp_dir, exist_ok=True)

        chunks = self.splitter.split(document_text, lang=lang)
        if not chunks:
            return {"success": False, "error": "No text chunks generated.", "output_path": None}
        
        logger.info("Pre-warming TTS model (ensures model is downloaded before parallel workers start)…")
        warmup_path = os.path.join(tmp_dir, "warmup.wav")
        warmup_text = "你好" if lang == "zh" else "Hello."
        warmup_result = self.tts_engine.synthesize(
            text=warmup_text,
            output_path=warmup_path,
            voice_profile=voice_profile,
        )
        if not warmup_result.get("success"):
            logger.warning("Pre-warm failed: %s — proceeding anyway.", warmup_result.get("error"))
        elif os.path.exists(warmup_path):
            os.remove(warmup_path)  # discard warmup audio

        logger.info("Processing %d chunks with %d workers…", len(chunks), self.max_workers)

        logger.info("Processing %d chunks with %d workers…", len(chunks), self.max_workers)

        # ── Parallel synthesis ──────────────────────────────────────────
        tasks = [
            {
                "index":         i,
                "text":          chunk,
                "temp_path":     os.path.join(tmp_dir, f"chunk_{i:05d}.wav"),
                "voice_profile": voice_profile,
            }
            for i, chunk in enumerate(chunks)
        ]

        results: List[Dict] = [None] * len(tasks)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            future_map = {
                pool.submit(self._synthesize_chunk, t): t["index"]
                for t in tasks
            }
            for future in concurrent.futures.as_completed(future_map):
                idx = future_map[future]
                try:
                    results[idx] = future.result(timeout=180)
                except concurrent.futures.TimeoutError:
                    logger.error("Chunk %d timed out.", idx)
                    results[idx] = {"index": idx, "success": False, "error": "Timeout"}
                except Exception as exc:
                    logger.error("Chunk %d raised: %s", idx, exc)
                    results[idx] = {"index": idx, "success": False, "error": str(exc)}

        # ── Collect results in order ────────────────────────────────────
        # Keep parallel lists: one entry per original chunk (failed chunks
        # get an empty wav_path so the subtitle generator can skip them).
        ok_files:    List[str] = []   # only successful WAVs, for audio combine
        sub_texts:   List[str] = []   # all chunk texts  (subtitle alignment)
        sub_wavs:    List[str] = []   # all chunk paths  (subtitle timing)
        total_chars = 0
        failed      = 0

        for r in results:
            if r and r.get("success"):
                ok_files.append(r["temp_path"])
                sub_texts.append(chunks[r["index"]])
                sub_wavs.append(r["temp_path"])
                total_chars += r.get("text_length", 0)
                logger.info("✓ chunk %05d  (%.2fs)", r["index"], r.get("processing_time", 0))
            else:
                # Failed chunk: record empty path so subtitle indices stay aligned
                sub_texts.append(chunks[r["index"]] if r else "")
                sub_wavs.append("")
                failed += 1
                logger.error("✗ chunk %05d  error: %s", r["index"] if r else "?",
                             r.get("error") if r else "unknown")

        if not ok_files:
            return {"success": False, "error": "All chunks failed.", "output_path": None}

        # ── Optionally interleave silence ───────────────────────────────
        if self.silence_ms > 0:
            ok_files = self._interleave_silence(ok_files, tmp_dir)

        # ── Combine audio ────────────────────────────────────────────────
        try:
            _combine_wav_files(ok_files, output_path)
        except Exception as exc:
            logger.error("Combining failed: %s", exc)
            return {"success": False, "error": f"Combine error: {exc}", "output_path": None}

        # ── Generate subtitles (before cleanup so chunk WAVs still exist) ─
        subtitle_files: dict = {}
        if subtitle_formats:
            try:
                from src.subtitle_generator import SubtitleGenerator
                gen     = SubtitleGenerator()
                entries = gen.build_entries(
                    texts      = sub_texts,
                    wav_paths  = sub_wavs,
                    silence_ms = self.silence_ms,
                )
                # Derive subtitle base path from audio output path
                base = os.path.splitext(output_path)[0]
                subtitle_files = gen.write_all(entries, base, formats=subtitle_formats)
                for fmt, path in subtitle_files.items():
                    logger.info("Subtitle [%s] → %s", fmt.upper(), path)
            except Exception as exc:
                logger.error("Subtitle generation failed: %s", exc)
                subtitle_files = {"error": str(exc)}

        # ── Cleanup ─────────────────────────────────────────────────────
        if cleanup:
            self._rm_dir(tmp_dir)

        elapsed = time.time() - t0
        logger.info("=" * 60)
        logger.info("✓ Finished in %.1fs → %s", elapsed, output_path)
        logger.info("  chunks: %d ok / %d failed   chars: %d",
                    len(ok_files), failed, total_chars)
        if subtitle_files:
            logger.info("  subtitles: %s", subtitle_files)
        logger.info("=" * 60)

        return {
            "success":          True,
            "output_path":      output_path,
            "total_chunks":     len(chunks),
            "processed_chunks": len(ok_files),
            "failed_chunks":    failed,
            "total_characters": total_chars,
            "elapsed_seconds":  elapsed,
            "subtitles":        subtitle_files,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _synthesize_chunk(self, task: dict) -> dict:
        result = self.tts_engine.synthesize(
            text=task["text"],
            output_path=task["temp_path"],
            voice_profile=task["voice_profile"],
        )
        result["index"]     = task["index"]
        result["temp_path"] = task["temp_path"]
        return result

    def _interleave_silence(self, wav_files: List[str], tmp_dir: str) -> List[str]:
        """Insert a silence WAV between each file."""
        if not wav_files:
            return wav_files

        # Derive params from the first file
        with wave.open(wav_files[0], "rb") as wf:
            params = wf.getparams()

        silence_path = os.path.join(tmp_dir, "silence.wav")
        raw_silence  = _make_silence(self.silence_ms, sample_rate=params.framerate)

        with wave.open(silence_path, "wb") as sw:
            sw.setnchannels(params.nchannels)
            sw.setsampwidth(params.sampwidth)
            sw.setframerate(params.framerate)
            sw.writeframes(raw_silence)

        interleaved: List[str] = []
        for i, fp in enumerate(wav_files):
            interleaved.append(fp)
            if i < len(wav_files) - 1:
                interleaved.append(silence_path)
        return interleaved

    @staticmethod
    def _rm_dir(path: str):
        import shutil
        try:
            shutil.rmtree(path)
        except Exception as exc:
            logger.warning("Could not remove temp dir %s: %s", path, exc)