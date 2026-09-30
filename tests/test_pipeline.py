"""Behavioural tests for the labeling policy (usage, not etymology)."""
import unittest

from cmx_lid import Config, Identifier


def labels(ident, text):
    return [(t.text, t.label) for t in ident.identify(text)]


class TestPolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ident = Identifier.load()

    def test_arabic_latin_loans_are_bambara(self):
        for w in ("inchallah", "al-hamdoulillah", "bismillah", "barika"):
            self.assertEqual(labels(self.ident, f"{w} n bɛ na")[0], (w, "bam"))

    def test_nativized_french_is_bambara(self):
        for w in ("lopital", "taabali", "lekɔli", "mobili"):
            self.assertEqual(dict(labels(self.ident, f"n taara {w} la"))[w], "bam")

    def test_live_french_switch(self):
        self.assertEqual(labels(self.ident, "n taara l'hôpital"),
                         [("n", "bam"), ("taara", "bam"), ("l'", "fra"), ("hôpital", "fra")])

    def test_nativized_phonology(self):
        self.assertEqual({l for _, l in labels(self.ident, "n taara opital la")}, {"bam"})

    def test_french_spelling_wins_by_default(self):
        # Decision: French orthography => fra, even without elision.
        self.assertEqual(dict(labels(self.ident, "n taara hôpital la"))["hôpital"], "fra")

    def test_spelling_rule_is_configurable(self):
        soft = Identifier(self.ident.lexicon, self.ident.model,
                          Config(french_orthography_final=False))
        tok = [t for t in soft.identify("n taara hôpital la") if t.text == "hôpital"][0]
        self.assertIn(tok.label, ("fra", "bam"))  # now decided by evidence + context

    def test_old_orthography(self):
        self.assertEqual(dict(labels(self.ident, "n bè taa sugu la"))["bè"], "bam")

    def test_arabic_script_is_neutral(self):
        got = dict(labels(self.ident, "Ala ka an kisi الحمد لله"))
        self.assertEqual((got["الحمد"], got["لله"], got["kisi"]), ("univ", "univ", "bam"))

    def test_nko_script_is_bambara(self):
        toks = self.ident.identify("ߒ ߓߍ߫ ߕߊ߯")
        self.assertEqual({t.label for t in toks}, {"bam"})

    def test_univ_and_offsets(self):
        text = "inchallah, n bɛ na 10h 🙂"
        toks = self.ident.identify(text)
        for t in toks:
            self.assertEqual(text[t.start:t.end], t.text)
            self.assertTrue(0.0 <= t.confidence <= 1.0)
        self.assertEqual([t.label for t in toks if t.text in (",", "10h", "🙂")], ["univ"] * 3)

    def test_english_switch(self):
        self.assertEqual(dict(labels(self.ident, "n bɛ download kɛ sisan"))["download"], "eng")

    def test_empty(self):
        self.assertEqual(self.ident.identify(""), [])


if __name__ == "__main__":
    unittest.main()
