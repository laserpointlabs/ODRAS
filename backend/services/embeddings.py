from typing import List
import hashlib


class SimpleHasherEmbedder:
    """MVP placeholder embedder.
    Produces 384-dim pseudo-embeddings via hashing for end-to-end dev without model deps.
    Replace with sentence-transformers later.
    """

    def __init__(self, dim: int = 384):
        self.dim = dim

    def embed(self, texts: List[str]) -> List[List[float]]:
        embeddings: List[List[float]] = []
        for t in texts:
            vec = [0.0] * self.dim
            for i in range(self.dim):
                h = hashlib.sha256((t + str(i)).encode()).hexdigest()
                # Map first 8 hex chars to float in [0,1)
                val = int(h[:8], 16) / 0xFFFFFFFF
                vec[i] = float(val)
            embeddings.append(vec)
        return embeddings



