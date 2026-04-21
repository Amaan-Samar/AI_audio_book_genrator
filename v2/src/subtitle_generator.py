"""
subtitle_generator.py
=====================
Generates subtitle files (SRT and/or WebVTT) from the ordered list of
text chunks and their corresponding WAV audio files.

Because the TTS engine produces the audio directly from known text, there
is no need for speech recognition — we simply read the duration of each
chunk WAV and accumulate timestamps.

Supported formats
-----------------
  .srt   — SubRip, universally supported (VLC, YouTube, most players)
  .vtt   — WebVTT, used by HTML5 <video>, YouTube, browser-based players

Usage (standalone)
------------------
    from src.subtitle_generator import SubtitleGenerator

    gen = SubtitleGenerator()
    entries = gen.build_entries(chunks, wav_paths, silence_ms=0)
    gen.write_srt(entries, "output/audio.srt")
    gen.write_vtt(entries, "output/audio.vtt")
"""

import os
import wave
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class SubtitleEntry:
    index:      int          # 1-based subtitle index
    start_ms:   int          # start time in milliseconds
    end_ms:     int          # end time in milliseconds
    text:       str          # display text
    wav_path:   str = ""     # path to the source chunk WAV (informational)

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


# ---------------------------------------------------------------------------
# Core class
# ---------------------------------------------------------------------------

class SubtitleGenerator:
    """
    Builds subtitle entries from synthesised chunk data and writes SRT / VTT.
    """

    # Maximum characters per subtitle line before wrapping
    LINE_WRAP_CHARS = 42

    def __init__(self, line_wrap: int = 42):
        self.line_wrap = line_wrap

    # ------------------------------------------------------------------
    # Building entries
    # ------------------------------------------------------------------

    def build_entries(
        self,
        texts:       List[str],
        wav_paths:   List[str],
        silence_ms:  int = 0,
        start_offset_ms: int = 0,
    ) -> List[SubtitleEntry]:
        """
        Create a list of SubtitleEntry objects from parallel lists of
        chunk texts and their synthesised WAV files.

        Args:
            texts:            Ordered list of text chunks (same order as audio).
            wav_paths:        Ordered list of WAV file paths for each chunk.
                              A path may be "" or non-existent for failed chunks
                              — those chunks are skipped.
            silence_ms:       Milliseconds of silence inserted between chunks
                              (must match the value used during audio assembly).
            start_offset_ms:  Global offset added to every timestamp (default 0).

        Returns:
            List of SubtitleEntry, one per successfully synthesised chunk.
        """
        if len(texts) != len(wav_paths):
            raise ValueError(
                f"texts ({len(texts)}) and wav_paths ({len(wav_paths)}) must have the same length."
            )

        entries: List[SubtitleEntry] = []
        cursor_ms = start_offset_ms
        sub_index = 1

        for i, (text, wav_path) in enumerate(zip(texts, wav_paths)):
            # Skip failed / missing chunks
            if not wav_path or not os.path.exists(wav_path):
                logger.warning("Chunk %d: WAV not found (%s), skipping subtitle.", i, wav_path)
                # Still advance cursor by a rough estimate so timing stays sane
                # (estimate: ~5 chars/second for Chinese, ~15 chars/second for English)
                est_ms = max(500, len(text) * 120)   # very rough
                cursor_ms += est_ms + silence_ms
                continue

            duration_ms = self._wav_duration_ms(wav_path)
            if duration_ms <= 0:
                logger.warning("Chunk %d: zero-length WAV, skipping subtitle.", i)
                cursor_ms += silence_ms
                continue

            start_ms = cursor_ms
            end_ms   = cursor_ms + duration_ms

            entries.append(SubtitleEntry(
                index    = sub_index,
                start_ms = start_ms,
                end_ms   = end_ms,
                text     = self._wrap(text),
                wav_path = wav_path,
            ))

            sub_index += 1
            # Advance past this chunk + inter-chunk silence
            cursor_ms = end_ms + silence_ms

        logger.info(
            "Built %d subtitle entries (total duration: %s)",
            len(entries),
            self._ms_to_srt(entries[-1].end_ms) if entries else "0",
        )
        return entries

    # ------------------------------------------------------------------
    # Writers
    # ------------------------------------------------------------------

    def write_srt(self, entries: List[SubtitleEntry], output_path: str) -> str:
        """
        Write an SRT subtitle file.

        SRT format:
            1
            00:00:00,000 --> 00:00:03,500
            Text of the subtitle

        Returns the output path.
        """
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        lines = []
        for entry in entries:
            lines.append(str(entry.index))
            lines.append(
                f"{self._ms_to_srt(entry.start_ms)} --> {self._ms_to_srt(entry.end_ms)}"
            )
            lines.append(entry.text)
            lines.append("")          # blank line between entries

        content = "\n".join(lines)

        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(content)

        logger.info("SRT written → %s  (%d entries)", output_path, len(entries))
        return output_path

    def write_vtt(self, entries: List[SubtitleEntry], output_path: str) -> str:
        """
        Write a WebVTT subtitle file.

        VTT format:
            WEBVTT

            1
            00:00:00.000 --> 00:00:03.500
            Text of the subtitle

        Returns the output path.
        """
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        lines = ["WEBVTT", ""]
        for entry in entries:
            lines.append(str(entry.index))
            lines.append(
                f"{self._ms_to_vtt(entry.start_ms)} --> {self._ms_to_vtt(entry.end_ms)}"
            )
            lines.append(entry.text)
            lines.append("")

        content = "\n".join(lines)

        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(content)

        logger.info("VTT written → %s  (%d entries)", output_path, len(entries))
        return output_path

    def write_all(
        self,
        entries:     List[SubtitleEntry],
        base_path:   str,
        formats:     Optional[List[str]] = None,
    ) -> dict:
        """
        Write subtitle files in one or more formats.

        Args:
            entries:    SubtitleEntry list from build_entries().
            base_path:  Path without extension, e.g. "output/audio".
                        The method appends .srt / .vtt automatically.
            formats:    List of formats to write, e.g. ["srt", "vtt"].
                        Default: ["srt", "vtt"] (both).

        Returns:
            dict mapping format name → output path.
        """
        if formats is None:
            formats = ["srt", "vtt"]

        written = {}
        for fmt in formats:
            fmt = fmt.lower().lstrip(".")
            path = f"{base_path}.{fmt}"
            if fmt == "srt":
                self.write_srt(entries, path)
                written["srt"] = path
            elif fmt == "vtt":
                self.write_vtt(entries, path)
                written["vtt"] = path
            else:
                logger.warning("Unknown subtitle format '%s', skipping.", fmt)

        return written

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _wav_duration_ms(path: str) -> int:
        """Return the duration of a WAV file in milliseconds."""
        try:
            with wave.open(path, "rb") as wf:
                frames     = wf.getnframes()
                frame_rate = wf.getframerate()
                if frame_rate == 0:
                    return 0
                return int(frames / frame_rate * 1000)
        except Exception as exc:
            logger.error("Could not read WAV duration for %s: %s", path, exc)
            return 0

    @staticmethod
    def _ms_to_srt(ms: int) -> str:
        """Convert milliseconds to SRT timestamp: HH:MM:SS,mmm"""
        ms    = max(0, ms)
        h     =  ms // 3_600_000;  ms %=  3_600_000
        m     =  ms //    60_000;  ms %=     60_000
        s     =  ms //     1_000;  ms %=      1_000
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    @staticmethod
    def _ms_to_vtt(ms: int) -> str:
        """Convert milliseconds to WebVTT timestamp: HH:MM:SS.mmm"""
        ms    = max(0, ms)
        h     =  ms // 3_600_000;  ms %=  3_600_000
        m     =  ms //    60_000;  ms %=     60_000
        s     =  ms //     1_000;  ms %=      1_000
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

    def _wrap(self, text: str) -> str:
        """
        Soft-wrap long lines at self.line_wrap characters.
        For Chinese text (no spaces), wraps at character count.
        For English text, wraps on word boundaries.
        """
        text = text.strip()
        if len(text) <= self.line_wrap:
            return text

        # Detect language heuristically
        cjk_ratio = sum(1 for c in text if '\u4e00' <= c <= '\u9fff') / max(1, len(text))
        if cjk_ratio > 0.3:
            # Chinese: hard wrap at character boundary
            return "\n".join(
                text[i: i + self.line_wrap]
                for i in range(0, len(text), self.line_wrap)
            )
        else:
            # English: word-boundary wrap
            words, lines, current = text.split(), [], ""
            for word in words:
                if len(current) + len(word) + (1 if current else 0) > self.line_wrap:
                    if current:
                        lines.append(current)
                    current = word
                else:
                    current = (current + " " + word).strip()
            if current:
                lines.append(current)
            return "\n".join(lines)


# ---------------------------------------------------------------------------
# Convenience: generate subtitles from an already-combined audio + text list
# (post-hoc, if you skipped subtitle generation during synthesis)
# ---------------------------------------------------------------------------

def generate_from_chunks(
    texts:       List[str],
    wav_paths:   List[str],
    output_base: str,
    silence_ms:  int = 0,
    formats:     Optional[List[str]] = None,
    line_wrap:   int = 42,
) -> dict:
    """
    Convenience wrapper: build entries and write subtitle files in one call.

    Args:
        texts:        Ordered list of chunk texts.
        wav_paths:    Ordered list of chunk WAV paths (parallel to texts).
        output_base:  Base path without extension (e.g. "output/zohar_1").
        silence_ms:   Silence padding between chunks (must match audio assembly).
        formats:      ["srt"], ["vtt"], or ["srt", "vtt"] (default: both).
        line_wrap:    Characters per subtitle line before wrapping.

    Returns:
        dict with keys "srt" and/or "vtt" → output file paths,
        plus "entries" → list of SubtitleEntry objects.
    """
    gen     = SubtitleGenerator(line_wrap=line_wrap)
    entries = gen.build_entries(texts, wav_paths, silence_ms=silence_ms)
    written = gen.write_all(entries, output_base, formats=formats)
    written["entries"] = entries
    return written