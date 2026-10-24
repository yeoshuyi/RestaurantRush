import unittest

from tests import _path
from rrdv.coverage import CoverageDB


class CoverageTest(unittest.TestCase):
    def test_bins_ignore_illegal_merge(self):
        def make():
            db = CoverageDB()
            g = db.group("g")
            g.coverpoint("p", ["a", "b"], ignore={"c": "why"}, illegal={"d": "never"})
            g.cross("x", ["1", "2"], ["y"], ignore={("2", "y"): "why"})
            return db

        a, b = make(), make()
        a["g"]["p"].sample("a")
        a["g"]["x"].sample(("1", "y"))
        b["g"]["p"].sample("b")
        b["g"]["p"].sample("c")
        self.assertEqual(a.covered(), (2, 3))
        a.merge(b)
        self.assertEqual(a.covered(), (3, 3))
        self.assertEqual(a.percent(), 100.0)
        self.assertEqual(a.violations, [])
        a["g"]["p"].sample("d")
        a["g"]["p"].sample("zzz")
        self.assertEqual(len(a.violations), 2)
        self.assertIn("ILLEGAL_BIN", a.violations[0])
        self.assertIn("UNDECLARED_BIN", a.violations[1])


if __name__ == "__main__":
    unittest.main()
