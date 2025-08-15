import re
from typing import List

SHALL_PATTERN = re.compile(r"\b(shall|should|must|will)\b", re.IGNORECASE)


class RequirementExtractor:
    def extract(self, text: str) -> List[str]:
        """Very simple requirement extraction: split by sentence, keep sentences with modal verbs.
        Replace with ML/LLM pipeline later.
        """
        cleaned = self._preprocess_markdown(text)
        # Split on sentence boundaries or line breaks (to catch list items without punctuation)
        sentences = re.split(r"(?<=[.!?])\s+|[\r\n]+", cleaned)
        reqs = [s.strip() for s in sentences if s and SHALL_PATTERN.search(s)]
        return reqs

    def _preprocess_markdown(self, text: str) -> str:
        """Lightweight Markdown cleanup for requirement extraction.
        - Remove fenced code blocks and inline code
        - Remove images, keep link text
        - Strip heading markers
        - Normalize list items as standalone lines
        - Remove emphasis markers
        - Collapse excessive whitespace
        """
        if not text:
            return ""

        # Remove fenced code blocks ``` ... ```
        without_code_blocks = re.sub(r"```[\s\S]*?```", " ", text)

        # Remove inline code `code`
        without_inline_code = re.sub(r"`[^`]*`", " ", without_code_blocks)

        # Remove images ![alt](url)
        without_images = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", without_inline_code)

        # Replace links [text](url) -> text
        links_to_text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", without_images)

        # Process line-by-line for headings and list items
        processed_lines: List[str] = []
        for raw_line in links_to_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            # Strip heading markers like #, ##, ###
            line = re.sub(r"^#{1,6}\s*", "", line)

            # Normalize list bullets (-, *, +, 1.) → keep text only
            line = re.sub(r"^\s*(?:[-*+]\s+|\d+\.\s+)", "", line)

            if not line:
                continue

            processed_lines.append(line)

        processed_text = "\n".join(processed_lines)

        # Remove emphasis markers **bold**, *italics*, __bold__, _italics_
        processed_text = re.sub(r"(\*\*|__)([^*_]+)\1", r"\2", processed_text)
        processed_text = re.sub(r"(\*|_)([^*_]+)\1", r"\2", processed_text)

        # Collapse excessive whitespace
        processed_text = re.sub(r"[\t\x0b\x0c\r]+", " ", processed_text)
        processed_text = re.sub(r"\s{2,}", " ", processed_text)

        return processed_text.strip()
