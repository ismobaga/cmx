"""Parquet download path against a local fake Hub (no network)."""
import importlib.util
import io
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import mock

from cmx_lid.ingest import hf


@unittest.skipUnless(importlib.util.find_spec("pyarrow"), "pyarrow not installed")
class TestParquetPath(unittest.TestCase):
    def setUp(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        buf = io.BytesIO()
        pq.write_table(pa.table({"bm": ["muso bɛ dumuni tobi"], "fr": ["la femme cuisine"],
                                 "en": ["the woman cooks"]}), buf)
        parq, seen = buf.getvalue(), {}
        self.seen = seen

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                base = f"http://127.0.0.1:{self.server.server_port}"
                if self.path.endswith("/parquet"):
                    body = json.dumps({"clean": {"train": [base + "/hub/0.parquet"],
                                                 "test": [base + "/hub/1.parquet"]}}).encode()
                    self.send_response(200); self.end_headers(); self.wfile.write(body)
                elif self.path.startswith("/hub/"):
                    seen["hub_auth"] = self.headers.get("Authorization")
                    self.send_response(302)
                    self.send_header("Location", base + "/cdn" + self.path)
                    self.end_headers()
                elif self.path.startswith("/cdn/"):
                    seen["cdn_auth"] = self.headers.get("Authorization")
                    self.send_response(200); self.end_headers(); self.wfile.write(parq)

        self.srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        port = self.srv.server_port
        # pretend /hub/ and /api/ are huggingface.co and /cdn/ is the CDN
        self.patches = [mock.patch.object(hf, "HUB", f"http://127.0.0.1:{port}/api/datasets"),
                        mock.patch.object(hf, "_is_hub", lambda url: "/cdn/" not in url),
                        mock.patch.dict(os.environ, {"HF_TOKEN": "hf_test",
                                                     "NO_PROXY": "127.0.0.1", "no_proxy": "127.0.0.1"})]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.srv.shutdown()
        self.srv.server_close()

    def test_all_splits_and_token_not_sent_to_cdn(self):
        rows = list(hf.iter_hf_parquet("djelia/bambara-mt-dataset", split="all"))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["bm"], "muso bɛ dumuni tobi")
        self.assertEqual(self.seen["hub_auth"], "Bearer hf_test")
        self.assertIsNone(self.seen["cdn_auth"])

    def test_single_split_and_limit(self):
        self.assertEqual(len(list(hf.iter_hf_parquet("x/y", split="test"))), 1)
        self.assertEqual(len(list(hf.iter_hf_parquet("x/y", split="all", limit=1))), 1)


if __name__ == "__main__":
    unittest.main()
