import unittest

from cmx_lid.tokenize import CLITIC, UNIV, WORD, tokenize


def texts(s):
    return [t.text for t in tokenize(s)]


class TestTokenize(unittest.TestCase):
    def test_french_elision_split(self):
        self.assertEqual(texts("n taara l'hôpital"), ["n", "taara", "l'", "hôpital"])

    def test_bambara_contraction_split(self):
        self.assertEqual(texts("k'a fɔ"), ["k'", "a", "fɔ"])

    def test_curly_apostrophe(self):
        toks = tokenize("l’école")
        self.assertEqual([t.kind for t in toks], [CLITIC, WORD])
        self.assertEqual(toks[0].norm, "l'")

    def test_english_contractions_kept(self):
        self.assertEqual(texts("it's we're I'm"), ["it's", "we're", "I'm"])

    def test_long_prefix_not_split(self):
        self.assertEqual(texts("aujourd'hui insha'allah"), ["aujourd'hui", "insha'allah"])

    def test_hyphen_and_offsets(self):
        s = "al-hamdoulillah, 10h30 https://x.ml 🙂"
        toks = tokenize(s)
        self.assertEqual([t.text for t in toks],
                         ["al-hamdoulillah", ",", "10h30", "https://x.ml", "🙂"])
        for t in toks:
            self.assertEqual(s[t.start:t.end], t.text)
        self.assertEqual([t.kind for t in toks[1:]], [UNIV] * 4)

    def test_combining_tone_marks(self):
        self.assertEqual(texts("bɛ́ taa"), ["bɛ́", "taa"])


if __name__ == "__main__":
    unittest.main()
