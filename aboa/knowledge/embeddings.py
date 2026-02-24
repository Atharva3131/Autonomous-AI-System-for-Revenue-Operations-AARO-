"""
Embedding service for generating vector representations of text content.
"""

import logging
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

from aboa.core.exceptions import ABOAException

logger = logging.getLogger(__name__)


class EmbeddingException(ABOAException):
    """Exception raised for embedding-related errors."""
    pass


class EmbeddingService:
    """Service for generating text embeddings using sentence-transformers."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding service.
        
        Args:
            model_name: Name of the sentence-transformer model to use
        """
        self.model_name = model_name
        self._model: Optional[SentenceTransformer] = None
        
    def _load_model(self) -> SentenceTransformer:
        """Load the sentence transformer model."""
        if self._model is None:
            try:
                logger.info(f"Loading embedding model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
                logger.info("Embedding model loaded successfully")
            except Exception as e:
                raise EmbeddingException(f"Failed to load embedding model {self.model_name}: {str(e)}")
        return self._model
    
    def encode_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to encode
            
        Returns:
            Numpy array containing the embedding vector
            
        Raises:
            EmbeddingException: If encoding fails
        """
        if not text or not text.strip():
            raise EmbeddingException("Cannot encode empty or whitespace-only text")
            
        try:
            model = self._load_model()
            embedding = model.encode(text.strip())
            return embedding
        except Exception as e:
            raise EmbeddingException(f"Failed to encode text: {str(e)}")
    
    def encode_texts(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to encode
            
        Returns:
            List of numpy arrays containing embedding vectors
            
        Raises:
            EmbeddingException: If encoding fails
        """
        if not texts:
            return []
            
        # Filter out empty texts
        valid_texts = [text.strip() for text in texts if text and text.strip()]
        if not valid_texts:
            raise EmbeddingException("No valid texts to encode")
            
        try:
            model = self._load_model()
            embeddings = model.encode(valid_texts)
            return [embedding for embedding in embeddings]
        except Exception as e:
            raise EmbeddingException(f"Failed to encode texts: {str(e)}")
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this service.
        
        Returns:
            Dimension of embedding vectors
        """
        model = self._load_model()
        return model.get_sentence_embedding_dimension()