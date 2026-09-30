"""Release guard: the files shipped in the package match the repo's current model."""
import filecmp
import unittest

from cmx_lid import paths


class TestPackagedResources(unittest.TestCase):
    def test_resources_present_and_current(self):
        for name in ("cmx-lid-nb.json", "lexicon.tsv", "loanword_origin.tsv"):
            shipped = paths.PACKAGE_RESOURCES / name
            self.assertTrue(shipped.exists(), f"{shipped} missing: run python -m cmx_lid.build")
            repo = paths.resource(name)
            if repo != shipped:
                self.assertTrue(filecmp.cmp(repo, shipped, shallow=False),
                                f"{name} in cmx_lid/resources/ is stale: run python -m cmx_lid.build")


if __name__ == "__main__":
    unittest.main()
