import unittest

from fastapi import HTTPException

try:
    from backend.api.games import _validate_score_bounds
except ModuleNotFoundError:
    _validate_score_bounds = None


@unittest.skipIf(_validate_score_bounds is None, "Project dependencies are missing")
class ScoreValidationTests(unittest.TestCase):
    def test_accepts_scores_in_range(self):
        _validate_score_bounds(0, 10)
        _validate_score_bounds(10, 0)
        _validate_score_bounds(5, 5)

    def test_rejects_negative_scores(self):
        with self.assertRaises(HTTPException) as ctx:
            _validate_score_bounds(-1, 3)
        self.assertEqual(ctx.exception.status_code, 422)
        self.assertIn("positifs", str(ctx.exception.detail))

    def test_rejects_scores_above_ten(self):
        with self.assertRaises(HTTPException) as ctx:
            _validate_score_bounds(11, 2)
        self.assertEqual(ctx.exception.status_code, 422)
        self.assertIn("0 et 10", str(ctx.exception.detail))


if __name__ == "__main__":
    unittest.main()
