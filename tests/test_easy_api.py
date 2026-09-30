import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import cmx_lid
from cmx_lid.__main__ import main as cli
from cmx_lid.build import complete_conll


class TestEasyApi(unittest.TestCase):
    def test_tag(self):
        self.assertEqual(cmx_lid.tag("n taara l'hôpital, kunun"),
                         [("n", "bam"), ("taara", "bam"), ("l'", "fra"), ("hôpital", "fra"),
                          ("kunun", "bam")])
        self.assertIn((",", "univ"), cmx_lid.tag("a ko, n bɛ na", include_punct=True))

    def test_detect_and_switch(self):
        self.assertEqual(cmx_lid.detect("n bɛ taa sugu la sini"), "bam")
        self.assertEqual(cmx_lid.detect("je suis fatigué aujourd'hui"), "fra")
        self.assertIsNone(cmx_lid.detect("... 123 🙂"))
        self.assertTrue(cmx_lid.is_code_switched("réunion bɛ kɛ demain"))
        self.assertFalse(cmx_lid.is_code_switched("n bɛ taa so"))

    def test_cli_default_view(self):
        out = io.StringIO()
        with redirect_stdout(out):
            cli(["n taara l'hôpital kunun"])
        text = out.getvalue()
        self.assertIn("[fra] l'hôpital", text)
        self.assertIn("code-switched", text)


class TestBuildHelpers(unittest.TestCase):
    def test_complete_marker(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "k.conll"
            p.write_text("a\tbam\n\n", encoding="utf-8")
            self.assertFalse(complete_conll(p))
            p.write_text("a\tbam\n\n# done: {'rows': 1}\n", encoding="utf-8")
            self.assertTrue(complete_conll(p))
            self.assertFalse(complete_conll(Path(d) / "missing.conll"))


if __name__ == "__main__":
    unittest.main()
