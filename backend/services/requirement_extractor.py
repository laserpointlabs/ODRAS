import re
from typing import List


SHALL_PATTERN = re.compile(r"\b(shall|should|must|will)\b", re.IGNORECASE)


class RequirementExtractor:
    def extract(self, text: str) -> List[str]:
        """Very simple requirement extraction: split by sentence, keep sentences with modal verbs.
        Replace with ML/LLM pipeline later.
        """
        sentences = re.split(r"(?<=[.!?])\s+", text)
        reqs = [s.strip() for s in sentences if s and SHALL_PATTERN.search(s)]
        return reqs




