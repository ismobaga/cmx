import json
import unittest
from dataclasses import fields
from pathlib import Path

from cmx_lid import schema

ROOT = Path(__file__).resolve().parent.parent

# Pinned. If this fails you changed the frozen contract: bump SCHEMA_VERSION
# (major), update schema/token.schema.json, then update this value.
PINNED_FINGERPRINT = "d19b84b1ee075c10"


class TestFrozenSchema(unittest.TestCase):
    def test_fingerprint_pinned(self):
        self.assertEqual(schema.fingerprint(), PINNED_FINGERPRINT)

    def test_labels_exact(self):
        self.assertEqual(schema.LABELS, ("bam", "fra", "eng", "univ"))

    def test_json_schema_matches_code(self):
        js = json.loads((ROOT / "schema" / "token.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(js["properties"]["label"]["enum"], list(schema.LABELS))
        self.assertEqual(js["properties"]["source"]["enum"], list(schema.SOURCES))
        self.assertEqual(js["required"], [f.name for f in fields(schema.Token)])
        self.assertIn(schema.SCHEMA_VERSION, js["$id"])

    def test_token_validates(self):
        with self.assertRaises(ValueError):
            schema.Token("x", 0, 1, "xx", 1.0, "router")


if __name__ == "__main__":
    unittest.main()
