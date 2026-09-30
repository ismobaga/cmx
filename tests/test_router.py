import unittest

from cmx_lid.router import route_hard, route_orthographic
from cmx_lid.tokenize import tokenize


def tok(s):
    (t,) = tokenize(s)
    return t


class TestRouter(unittest.TestCase):
    def test_bambara_letter_is_hard(self):
        r = route_hard(tok("kɛnɛ"))
        self.assertEqual((r.label, r.final), ("bam", True))

    def test_arabic_script(self):
        self.assertEqual(route_hard(tok("الله")).label, "univ")

    def test_french_diacritic(self):
        r = route_orthographic(tok("hôpital"))
        self.assertEqual((r.label, r.final), ("fra", True))

    def test_old_orthography_not_french(self):
        # è/ò are old Bambara spellings of ɛ/ɔ, so no French decision here
        self.assertIsNone(route_orthographic(tok("bè")))
        self.assertIsNone(route_hard(tok("bè")))

    def test_clitics(self):
        l_, _ = tokenize("l'école")
        k_, _ = tokenize("k'a")
        n_, _ = tokenize("n'a")
        self.assertEqual(route_orthographic(l_).label, "fra")
        self.assertEqual(route_orthographic(k_).label, "bam")
        self.assertIsNone(route_orthographic(n_))


if __name__ == "__main__":
    unittest.main()
