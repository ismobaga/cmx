import importlib.util
import tempfile
import unittest
from pathlib import Path

from cmx_lid.classifier import CLASSIFIER_LABELS, CharNgramNB, load_classifier
from cmx_lid.paths import MODEL_PATH

PAIRS = [("taara", "bam"), ("kunun", "bam"), ("sisan", "bam"), ("dumuni", "bam"),
         ("maison", "fra"), ("demain", "fra"), ("merci", "fra"), ("possible", "fra"),
         ("tomorrow", "eng"), ("meeting", "eng"), ("download", "eng"), ("weather", "eng")]


class TestBackends(unittest.TestCase):
    def test_load_dispatch_json(self):
        self.assertIsInstance(load_classifier(MODEL_PATH), CharNgramNB)
        with self.assertRaises(ValueError):
            load_classifier("model.pkl")

    @unittest.skipUnless(importlib.util.find_spec("fasttext"), "fasttext not installed")
    def test_fasttext_roundtrip(self):
        from cmx_lid.fasttext_backend import FastTextClassifier
        with tempfile.TemporaryDirectory() as d:
            out = FastTextClassifier.train(PAIRS * 5, Path(d) / "m", epoch=50, quantize=False)
            clf = load_classifier(out)
            p = clf.predict_proba("taara")
            self.assertEqual(set(p), set(CLASSIFIER_LABELS))
            self.assertAlmostEqual(sum(p.values()), 1.0, places=5)
            self.assertEqual(max(p, key=p.get), "bam")


if __name__ == "__main__":
    unittest.main()
