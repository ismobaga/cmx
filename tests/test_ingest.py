import os
import tempfile
import unittest

from cmx_lid.ingest.kunkado import convert
from cmx_lid.ingest.wordlist import Counts, canon
from cmx_lid.lexicon import Lexicon
from cmx_lid.train import resolve_conflicts, wordlist_pairs


class TestKunkado(unittest.TestCase):
    def test_dataset_card_example(self):
        got = convert("__Voila donc bon__ a man nɔgɔ __quoi__ a man nɔgɔn")
        self.assertEqual([l for _, l in got],
                         ["fra"] * 3 + ["bam"] * 3 + ["fra"] + ["bam"] * 3)

    def test_elision_inside_span(self):
        self.assertEqual(convert("n taara __l'hôpital__ kunun"),
                         [("n", "bam"), ("taara", "bam"), ("l'", "fra"),
                          ("hôpital", "fra"), ("kunun", "bam")])

    def test_tags_and_punct(self):
        self.assertEqual(convert("[noise] a ko , <laugh> __merci__ ."),
                         [("a", "bam"), ("ko", "bam"), (",", "univ"),
                          ("merci", "fra"), (".", "univ")])

    def test_rejects_noise(self):
        self.assertIsNone(convert("__merci a bɛ"))   # unbalanced markers
        self.assertIsNone(convert("__a bɛ na__"))    # Bambara letter in a French span
        self.assertIsNone(convert("[music]"))


class TestWordlist(unittest.TestCase):
    def test_lang_aliases(self):
        self.assertEqual([canon(x) for x in ("bm", "FR", "eng_Latn", "xx")],
                         ["bam", "fra", "eng", None])

    def test_purity(self):
        c = Counts()
        for _ in range(9):
            c.add("a taara lekɔli la", "bam")
            c.add("il est parti à la maison", "fra")
        c.add("réunion bɛ kɛ", "bam")
        rows = {w: (l, n, p) for w, l, n, p, _ in c.rows()}
        self.assertEqual(rows["taara"][0], "bam")
        self.assertEqual(rows["maison"][0], "fra")
        self.assertAlmostEqual(rows["la"][2], 0.5)  # shared -> filtered at train time
        self.assertNotIn("bɛ", [w for w, (l, _, _) in rows.items() if l == "fra"])

    def test_wordlist_filter_and_conflicts(self):
        fd, path = tempfile.mkstemp(suffix=".tsv")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("word\tlabel\tcount\tpurity\tcounts\n"
                    "taara\tbam\t50\t1.0\tbam:50\n"
                    "la\tbam\t80\t0.5\tbam:40,fra:40\n"
                    "rare\tfra\t1\t1.0\tfra:1\n")
        try:
            pairs = wordlist_pairs(path, min_count=3, min_purity=0.9)
        finally:
            os.unlink(path)
        self.assertEqual(pairs, {("taara", "bam")})
        lex = Lexicon({"don": {"bam": 1}})
        self.assertEqual(resolve_conflicts({("don", "bam"), ("don", "eng"), ("x", "fra"),
                                            ("y", "bam"), ("y", "fra")}, lex),
                         [("don", "bam"), ("x", "fra")])


if __name__ == "__main__":
    unittest.main()


class TestColumnMapping(unittest.TestCase):
    def test_djelia_style_columns(self):
        import csv
        import json
        from cmx_lid.ingest.wordlist import main
        with tempfile.TemporaryDirectory() as d:
            src, out = os.path.join(d, "rows.jsonl"), os.path.join(d, "wl.tsv")
            with open(src, "w", encoding="utf-8") as f:
                f.write(json.dumps({"bm": "muso bɛ dumuni tobi", "fr": "la femme cuisine",
                                    "en": "the woman cooks"}, ensure_ascii=False) + "\n")
            main(["--jsonl", src, "--col", "bam=bm", "--col", "fra=fr", "--col", "eng=en",
                  "--out", out])
            with open(out, encoding="utf-8") as f:
                rows = {r["word"]: r["label"] for r in csv.DictReader(
                    (l for l in f if not l.startswith("#")), delimiter="\t")}
        self.assertEqual((rows["tobi"], rows["femme"], rows["woman"]), ("bam", "fra", "eng"))
