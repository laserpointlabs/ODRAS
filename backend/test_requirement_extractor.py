import sys
import os
import unittest

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.services.requirement_extractor import RequirementExtractor

class TestRequirementExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = RequirementExtractor()

    def test_extract_requirements(self):
        text = "The system shall do this. The system should do that. This is a test."
        expected = ["The system shall do this.", "The system should do that."]
        self.assertEqual(self.extractor.extract(text), expected)

    def test_no_requirements(self):
        text = "This is a test. No requirements here."
        expected = []
        self.assertEqual(self.extractor.extract(text), expected)

    def test_empty_text(self):
        text = ""
        expected = []
        self.assertEqual(self.extractor.extract(text), expected)

    def test_markdown_lists_and_links(self):
        md = (
            """# Requirements

- The service SHALL respond within 200ms.
- The client should retry at most 3 times.
- See [API spec](https://example.com) for details.
```
Code blocks must not influence extraction and may contain shall or must.
```
"""
        )
        result = self.extractor.extract(md)
        # Order preserved by lines; sentence boundaries by punctuation or line breaks
        self.assertIn("The service SHALL respond within 200ms.", result)
        self.assertIn("The client should retry at most 3 times.", result)
        # Link-only line has no modal verb → not included
        self.assertTrue(all("API spec" not in r for r in result))

    def test_markdown_inline_code_and_images(self):
        md = (
            "The module must handle `NULL` values correctly.\n"
            "An image: ![alt](image.png) should not be included.\n"
        )
        result = self.extractor.extract(md)
        # Inline code removed, whitespace collapsed
        self.assertIn("The module must handle values correctly.", result)

if __name__ == "__main__":
    unittest.main()
