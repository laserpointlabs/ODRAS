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

if __name__ == "__main__":
    unittest.main()
