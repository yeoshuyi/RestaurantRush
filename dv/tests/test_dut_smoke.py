"""End-to-end smoke test against the real Java DUT"""

import shutil
import unittest

from tests import _path  # noqa: F401
from rrdv.driver import JavaDUT, find_repo_root
from rrdv.regress import run_one
from rrdv.spec import STAGE1
from rrdv.stimulus import generate


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"), "JDK not installed")
class DutSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dut = JavaDUT(find_repo_root())
        cls.dut.build()

    def test_a_few_seeds(self):
        for seed, prof in [(1, "greedy"), (2, "random"), (3, "chaos"), (4, "lazy")]:
            res = run_one(self.dut, STAGE1, generate(STAGE1, seed, prof))
            self.assertTrue(res.passed, "\n".join(res.errors[:10]))


if __name__ == "__main__":
    unittest.main()
