"""The origin side table must stay metadata: never reach the classifier."""
import re
import unittest
from pathlib import Path

from cmx_lid import Identifier
from cmx_lid.lexicon import Lexicon
from cmx_lid.origins import COLUMNS, ORIGIN_TABLE_PATH, OriginTable
from cmx_lid.paths import LEXICON_PATH

PKG = Path(__file__).resolve().parent.parent / "cmx_lid"
# Modules allowed to touch the side table: itself, the CLI (post-hoc display), and
# build.py, which only copies the file into the package for distribution.
ALLOWED = {"origins.py", "__main__.py", "build.py"}
FORBIDDEN = re.compile(r"^\s*(?:from|import)\s[^\n]*\borigins\b|loanword_origin|OriginTable",
                       re.MULTILINE)


class TestIsolation(unittest.TestCase):
    def test_no_other_module_references_side_table(self):
        offenders = [p.name for p in PKG.rglob("*.py")
                     if p.name not in ALLOWED and FORBIDDEN.search(p.read_text(encoding="utf-8"))]
        self.assertEqual(offenders, [], "classification code must not read the origin table")

    def test_table_has_no_label_column(self):
        self.assertNotIn("label", COLUMNS)


class TestConsistency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = OriginTable.load(ORIGIN_TABLE_PATH)
        cls.lexicon = Lexicon.load(LEXICON_PATH)

    def test_every_loanword_is_bambara_in_lexicon(self):
        bad = {f: sorted(self.lexicon.labels_of(f)) for f in self.table.forms()
               if self.lexicon.labels_of(f) != {"bam"}}
        self.assertEqual(bad, {}, "loanwords in the side table must be lexicon-labeled bam only")

    def test_annotate_is_post_hoc(self):
        toks = Identifier.load().identify("inchallah n taara lekɔli la")
        pairs = self.table.annotate(toks)
        self.assertEqual([t for t, _ in pairs], toks)  # labels untouched
        origins = {t.text: o.origin_lang for t, o in pairs if o}
        self.assertEqual(origins, {"inchallah": "ara", "lekɔli": "fra"})

    def test_query_by_origin(self):
        self.assertIn("inchallah", {o.form for o in self.table.by_origin("ara")})


if __name__ == "__main__":
    unittest.main()
