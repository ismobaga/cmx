"""Behaviour added in 0.2: informal spelling, roman numerals, names, summary API."""
import unittest

from cmx_lid import Identifier, segments, summarize
from cmx_lid.augment import variants
from cmx_lid.lexicon import Lexicon
from cmx_lid.train import augment_pairs, resolve_conflicts


def lab(ident, text):
    return {t.text: t.label for t in ident.identify(text)}


class TestAugment(unittest.TestCase):
    def test_variants(self):
        v = variants("dugu")
        self.assertIn("dougou", v)
        self.assertIn("be", variants("bɛ"))
        self.assertIn("tche", variants("cɛ"))
        self.assertNotIn("dugu", v)

    def test_augment_does_not_steal_real_words(self):
        out = augment_pairs([("bɛ", "bam"), ("be", "eng")])
        self.assertIn(("be", "eng"), out)
        self.assertNotIn(("be", "bam"), out)
        self.assertIn(("bè", "bam"), out)

    def test_keep_ambiguous(self):
        pairs = {("or", "fra"), ("or", "eng"), ("x", "bam")}
        lex = Lexicon({"q": {"bam": 1}})
        self.assertEqual(resolve_conflicts(pairs, lex, keep_ambiguous=True),
                         [("or", "eng"), ("or", "fra"), ("x", "bam")])
        self.assertEqual(resolve_conflicts(pairs, lex), [("x", "bam")])


class TestPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ident = Identifier.load()

    def test_roman_numerals_are_univ(self):
        self.assertEqual(lab(self.ident, "Tilayɔrɔ IV ni VII")["IV"], "univ")
        self.assertEqual(lab(self.ident, "I ka kɛnɛ wa")["I"], "bam")

    def test_ambiguous_short_word_follows_context(self):
        self.assertEqual(lab(self.ident, "meeting in bɛ kɛ sini")["in"], "bam")

    def test_informal_spelling(self):
        got = lab(self.ident, "n be taa dougou la sini")
        self.assertEqual({got[w] for w in ("be", "taa", "dougou", "la", "sini")}, {"bam"})

    def test_name_takes_context(self):
        self.assertEqual(lab(self.ident, "n ye Kulubali ye sugu la")["Kulubali"], "bam")


class TestSummary(unittest.TestCase):
    def test_summary_and_segments(self):
        ident = Identifier.load()
        text = "n taara l'hôpital kunun ."
        toks = ident.identify(text)
        s = summarize(toks)
        self.assertEqual(s.dominant, "bam")
        self.assertTrue(s.code_switched)
        self.assertEqual(s.n_switches, 2)
        self.assertEqual([(g.label, text[g.start:g.end]) for g in segments(toks)],
                         [("bam", "n taara"), ("fra", "l'hôpital"), ("bam", "kunun")])

    def test_empty(self):
        s = summarize([])
        self.assertEqual((s.dominant, s.n_words, s.code_switched), (None, 0, False))


if __name__ == "__main__":
    unittest.main()
