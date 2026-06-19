import logging
try:
    from sentence_transformers import SentenceTransformer, util
except ImportError:
    SentenceTransformer = None

logger = logging.getLogger(__name__)

class SemanticMatcher:
    _instance = None
    _model = None

    def __new__(cls, model_name="all-MiniLM-L6-v2"):
        # Singleton to share model across calls
        if cls._instance is None:
            cls._instance = super(SemanticMatcher, cls).__new__(cls)
            cls._instance.model_name = model_name
        return cls._instance

    def initialize(self):
        """Lazy load the model to avoid slow startup compatibility issues if not installed."""
        if self._model is None:
            if SentenceTransformer is None:
                logger.error("sentence_transformers not installed.")
                return
            logger.info(f"Loading Semantic Model: {self.model_name}...")
            self._model = SentenceTransformer(self.model_name)
            logger.info("Semantic Model loaded.")

    def compute_similarity(self, text1: str, text2: str) -> float:
        if not text1 or not text2:
            return 0.0
        
        if self._model is None:
            self.initialize()
            if self._model is None:
                return 0.0

        try:
            # Encode both at once for efficiency
            embeddings = self._model.encode([text1, text2])
            # Compute cosine similarity
            score = util.cos_sim(embeddings[0], embeddings[1])
            return float(score.item())
        except Exception as e:
            logger.error(f"Error computing similarity: {e}")
            return 0.0
