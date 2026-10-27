import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import reddit_evidence as evidence


class BuildEvidenceTests(unittest.TestCase):
    def test_counts_distinct_threads_and_keeps_source_links(self):
        with tempfile.TemporaryDirectory() as directory:
            review = Path(directory) / "review.csv"
            output = Path(directory) / "evidence.json"
            rows = [
                {"subreddit": "Bumble", "post_id": "a", "post_url": "https://www.reddit.com/a",
                 "comment_url": "https://www.reddit.com/a/1", "comment_excerpt": "Advice one",
                 "themes": "first_photo;reply_hook"},
                {"subreddit": "Bumble", "post_id": "a", "post_url": "https://www.reddit.com/a",
                 "comment_url": "https://www.reddit.com/a/2", "comment_excerpt": "Advice two",
                 "themes": "first_photo"},
                {"subreddit": "Tinder", "post_id": "b", "post_url": "https://www.reddit.com/b",
                 "comment_url": "https://www.reddit.com/b/1", "comment_excerpt": "Advice three",
                 "themes": "first_photo"},
            ]
            with review.open("w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=evidence.FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            with patch.object(evidence, "REVIEW", review), patch.object(evidence, "OUTPUT", output):
                evidence.build()
            result = json.loads(output.read_text(encoding="utf-8"))
            first_photo = next(theme for theme in result["themes"] if theme["id"] == "first_photo")
            self.assertEqual(first_photo["counts"], {"bumble": 1, "hingeapp": 0, "tinder": 1})
            self.assertEqual(first_photo["sources"]["bumble"], [
                "https://www.reddit.com/a/1", "https://www.reddit.com/a/2"
            ])
            self.assertEqual(result["coded_threads"], 2)


if __name__ == "__main__":
    unittest.main()
