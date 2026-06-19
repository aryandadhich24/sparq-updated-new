import math
import re
import logging
from collections import Counter

logger = logging.getLogger(__name__)

_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "was", "are", "were", "be", "been",
    "we", "our", "this", "that", "it", "its", "as", "not", "no", "so",
}


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


def _tfidf_cosine(text1: str, text2: str) -> float:
    """TF-IDF cosine similarity using only stdlib — no ML dependencies."""
    tokens1 = _tokenize(text1)
    tokens2 = _tokenize(text2)
    if not tokens1 or not tokens2:
        return 0.0

    tf1 = Counter(tokens1)
    tf2 = Counter(tokens2)
    vocab = set(tf1) | set(tf2)

    # IDF: log((2+1) / (df+1)) + 1  (smoothed, corpus = 2 docs)
    def idf(term: str) -> float:
        df = (term in tf1) + (term in tf2)
        return math.log(3.0 / (df + 1)) + 1.0

    def vec(tf: Counter) -> dict:
        total = sum(tf.values()) or 1
        return {t: (tf[t] / total) * idf(t) for t in vocab if t in tf}

    v1, v2 = vec(tf1), vec(tf2)
    dot = sum(v1.get(t, 0) * v2.get(t, 0) for t in vocab)
    mag1 = math.sqrt(sum(x * x for x in v1.values()))
    mag2 = math.sqrt(sum(x * x for x in v2.values()))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


class SemanticMatcher:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def compute_similarity(self, text1: str, text2: str) -> float:
        if not text1 or not text2:
            return 0.0
        try:
            return _tfidf_cosine(text1, text2)
        except Exception as e:
            logger.error(f"Error computing similarity: {e}")
            return 0.0
