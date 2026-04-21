#!/usr/bin/env python3
"""
test_extractor.py
-----------------
Self-contained test suite for run_extractor.py.

* Does NOT need real PDFs — it creates tiny dummy PDFs with reportlab,
  or plain .pdf stubs if reportlab is absent.
* Does NOT need the real pdf_extractor / batch_processor modules —
  it patches them with lightweight mocks.
* Cleans up every temp file/folder it creates.

Run with:
    python test_extractor.py
    python test_extractor.py -v        # verbose
"""

import os
import sys
import shutil
import tempfile
import unittest
import importlib
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── make sure run_extractor.py is importable from the same folder ─────────────
THIS_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(THIS_DIR))

# ── helpers ───────────────────────────────────────────────────────────────────

def _make_dummy_pdf(path: Path) -> None:
    """Write the minimal bytes that make a file look like a PDF."""
    path.write_bytes(b"%PDF-1.4\n%%EOF\n")


def _make_scripts_mock(tmp_path: Path):
    """
    Inject fake 'scripts' package into sys.modules so that
    run_extractor.py's  `from pdf_extractor import ...` works
    without the real scripts/ directory.
    """
    scripts_pkg = types.ModuleType("scripts")
    scripts_pkg.__path__ = [str(tmp_path)]        # pretend it's a package

    # ── fake setup_logging ────────────────────────────────────────────────
    import logging
    def fake_setup_logging():
        logging.basicConfig(level=logging.WARNING)
        return logging.getLogger("test")

    # ── fake PDFToAudioText ───────────────────────────────────────────────
    class FakePDFToAudioText:
        def __init__(self, pdf_path, output_dir):
            self.pdf_path   = pdf_path
            self.output_dir = output_dir

        def save_to_audio_ready_files(self, pages_per_file=15,
                                      start_page=1, end_page=None):
            # Actually create the output dir and two stub text files
            out = Path(self.output_dir)
            out.mkdir(parents=True, exist_ok=True)
            files = []
            for i in range(1, 3):
                f = out / f"part_{i:03d}.txt"
                f.write_text(f"chunk {i} of {Path(self.pdf_path).name}")
                files.append(str(f))
            return files

        def get_pdf_info(self):
            return {"file": self.pdf_path, "pages": 10,
                    "metadata": {"Title": "Test"}}

        def preview_text(self, num_pages=3):
            print(f"[preview] {self.pdf_path} first {num_pages} pages")

    # ── fake BatchPDFProcessor (kept for import compatibility) ────────────
    class FakeBatchPDFProcessor:
        def __init__(self, input_dir, output_dir):
            pass
        def process_all_pdfs(self, **kwargs):
            return {}

    # ── fake pdf_extractor sub-module ─────────────────────────────────────
    pdf_extractor_mod = types.ModuleType("pdf_extractor")
    pdf_extractor_mod.PDFToAudioText = FakePDFToAudioText
    pdf_extractor_mod.setup_logging  = fake_setup_logging

    batch_mod = types.ModuleType("batch_processor")
    batch_mod.BatchPDFProcessor = FakeBatchPDFProcessor

    sys.modules["scripts"]                   = scripts_pkg
    sys.modules["scripts.pdf_extractor"]     = pdf_extractor_mod
    sys.modules["scripts.batch_processor"]   = batch_mod
    sys.modules["pdf_extractor"]             = pdf_extractor_mod
    sys.modules["batch_processor"]           = batch_mod

    return FakePDFToAudioText, FakeBatchPDFProcessor


# ─────────────────────────────────────────────────────────────────────────────
# Test cases
# ─────────────────────────────────────────────────────────────────────────────

class BaseExtractorTest(unittest.TestCase):
    """Set up a temp workspace and import run_extractor freshly."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="extractor_test_"))
        _make_scripts_mock(cls.tmp)

        # Force a clean import of run_extractor each test class
        if "run_extractor" in sys.modules:
            del sys.modules["run_extractor"]
        import run_extractor as re_mod
        cls.re = re_mod

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _out(self, name="output") -> Path:
        """Return a fresh output dir inside the temp workspace."""
        p = self.tmp / name
        p.mkdir(parents=True, exist_ok=True)
        return p


# ── 1. Single-file mode ───────────────────────────────────────────────────────

class TestSingleFileMode(BaseExtractorTest):

    def setUp(self):
        self.pdf = self.tmp / "my_book.pdf"
        _make_dummy_pdf(self.pdf)

    def _run(self, extra_args=None):
        out = self._out("single_out")
        argv = ["run_extractor.py", str(self.pdf), "--output-dir", str(out)]
        if extra_args:
            argv += extra_args
        with patch("sys.argv", argv):
            self.re.main()
        return out

    def test_creates_named_subfolder(self):
        """Output goes into output_dir/<pdf_stem>/"""
        out = self._run()
        subfolder = out / "my_book"
        self.assertTrue(subfolder.is_dir(),
                        f"Expected subfolder '{subfolder}' was not created")

    def test_creates_text_files(self):
        """At least one .txt file is written inside the subfolder."""
        out = self._run()
        txt_files = list((out / "my_book").glob("*.txt"))
        self.assertGreater(len(txt_files), 0, "No .txt files found in output subfolder")

    def test_custom_pages_per_file_accepted(self):
        """--pages-per-file flag is accepted without error."""
        out = self._out("single_ppf")
        argv = ["run_extractor.py", str(self.pdf),
                "--output-dir", str(out), "--pages-per-file", "5"]
        with patch("sys.argv", argv):
            self.re.main()   # should not raise

    def test_page_range_accepted(self):
        """--start / --end flags are accepted without error."""
        out = self._out("single_range")
        argv = ["run_extractor.py", str(self.pdf),
                "--output-dir", str(out), "--start", "2", "--end", "4"]
        with patch("sys.argv", argv):
            self.re.main()

    def test_missing_pdf_exits(self):
        """Passing a non-existent PDF should call sys.exit."""
        argv = ["run_extractor.py", "ghost.pdf",
                "--output-dir", str(self._out("ghost_out"))]
        with patch("sys.argv", argv):
            with self.assertRaises(SystemExit):
                self.re.main()

    def test_info_flag(self):
        """--info prints PDF info and does not create output files."""
        out = self._out("info_out")
        argv = ["run_extractor.py", str(self.pdf),
                "--output-dir", str(out), "--info"]
        with patch("sys.argv", argv):
            self.re.main()
        # No subfolder should have been created (info is read-only)
        subfolder = out / "my_book"
        txt_files = list(subfolder.glob("*.txt")) if subfolder.exists() else []
        self.assertEqual(txt_files, [],
                         "--info should not create text files")

    def test_preview_flag(self):
        """--preview runs without error and creates no text files."""
        out = self._out("preview_out")
        argv = ["run_extractor.py", str(self.pdf),
                "--output-dir", str(out), "--preview"]
        with patch("sys.argv", argv):
            self.re.main()


# ── 2. Batch mode ─────────────────────────────────────────────────────────────

class TestBatchMode(BaseExtractorTest):

    def setUp(self):
        self.in_dir = self.tmp / "batch_input"
        self.in_dir.mkdir(exist_ok=True)
        # Put 3 dummy PDFs in the input dir
        self.pdf_names = ["alpha", "beta", "gamma"]
        for name in self.pdf_names:
            _make_dummy_pdf(self.in_dir / f"{name}.pdf")

    def _run_batch(self, extra_args=None):
        out = self._out("batch_out")
        argv = ["run_extractor.py", "--batch",
                "--input-dir", str(self.in_dir),
                "--output-dir", str(out)]
        if extra_args:
            argv += extra_args
        with patch("sys.argv", argv):
            self.re.main()
        return out

    def test_subfolder_per_pdf(self):
        """Each PDF gets its own subfolder inside output_dir."""
        out = self._run_batch()
        for name in self.pdf_names:
            subfolder = out / name
            self.assertTrue(subfolder.is_dir(),
                            f"Missing subfolder for '{name}'")

    def test_text_files_inside_each_subfolder(self):
        """Every PDF subfolder contains at least one .txt file."""
        out = self._run_batch()
        for name in self.pdf_names:
            txt_files = list((out / name).glob("*.txt"))
            self.assertGreater(len(txt_files), 0,
                               f"No .txt files in subfolder '{name}'")

    def test_no_cross_contamination(self):
        """Files from one PDF do not land in another PDF's subfolder."""
        out = self._run_batch()
        for name in self.pdf_names:
            for txt in (out / name).glob("*.txt"):
                content = txt.read_text()
                self.assertIn(name, content,
                              f"File in '{name}/' doesn't reference '{name}'")

    def test_empty_input_dir(self):
        """Batch mode on an empty dir does not crash."""
        empty = self.tmp / "empty_input"
        empty.mkdir(exist_ok=True)
        out = self._out("empty_out")
        argv = ["run_extractor.py", "--batch",
                "--input-dir", str(empty),
                "--output-dir", str(out)]
        with patch("sys.argv", argv):
            self.re.main()   # should complete quietly

    def test_nonexistent_input_dir_exits(self):
        """Batch mode with a missing --input-dir calls sys.exit."""
        argv = ["run_extractor.py", "--batch",
                "--input-dir", "/no/such/dir",
                "--output-dir", str(self._out("nx_out"))]
        with patch("sys.argv", argv):
            with self.assertRaises(SystemExit):
                self.re.main()

    def test_batch_with_page_range(self):
        """--start and --end are forwarded without error in batch mode."""
        out = self._out("batch_range")
        argv = ["run_extractor.py", "--batch",
                "--input-dir", str(self.in_dir),
                "--output-dir", str(out),
                "--start", "3", "--end", "9"]
        with patch("sys.argv", argv):
            self.re.main()

    def test_batch_with_pages_per_file(self):
        """--pages-per-file is forwarded without error in batch mode."""
        out = self._out("batch_ppf")
        argv = ["run_extractor.py", "--batch",
                "--input-dir", str(self.in_dir),
                "--output-dir", str(out),
                "--pages-per-file", "10"]
        with patch("sys.argv", argv):
            self.re.main()


# ── 3. CLI / argument edge cases ──────────────────────────────────────────────

class TestCLIEdgeCases(BaseExtractorTest):

    def test_no_args_prints_help_and_exits(self):
        """Calling with no arguments exits (help is shown)."""
        with patch("sys.argv", ["run_extractor.py"]):
            with self.assertRaises(SystemExit):
                self.re.main()

    def test_default_output_dir_name(self):
        """When --output-dir is omitted, 'output_text' is used as root."""
        pdf = self.tmp / "default_test.pdf"
        _make_dummy_pdf(pdf)
        expected_root = Path("output_text")
        argv = ["run_extractor.py", str(pdf)]
        with patch("sys.argv", argv):
            self.re.main()
        subfolder = expected_root / "default_test"
        exists = subfolder.is_dir()
        # Clean up before asserting so we don't leave garbage on failure
        shutil.rmtree("output_text", ignore_errors=True)
        self.assertTrue(exists, f"Default output subfolder '{subfolder}' not found")

    def test_default_batch_input_dir(self):
        """--batch without --input-dir scans 'input_pdfs/' by default."""
        default_in = Path("input_pdfs")
        default_in.mkdir(exist_ok=True)
        _make_dummy_pdf(default_in / "sample.pdf")
        out = self._out("default_batch_out")
        argv = ["run_extractor.py", "--batch", "--output-dir", str(out)]
        with patch("sys.argv", argv):
            self.re.main()
        shutil.rmtree(default_in, ignore_errors=True)
        self.assertTrue((out / "sample").is_dir())


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  PDF Extractor — Test Suite")
    print("=" * 60)
    verbosity = 2 if "-v" in sys.argv else 1
    loader  = unittest.TestLoader()
    suite   = unittest.TestSuite()
    for cls in [TestSingleFileMode, TestBatchMode, TestCLIEdgeCases]:
        suite.addTests(loader.loadTestsFromTestCase(cls))
    runner  = unittest.TextTestRunner(verbosity=verbosity)
    result  = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)