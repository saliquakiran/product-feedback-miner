"""
Embedding generation and similarity utilities for the Clusterer Agent.

This module provides functionality for generating embeddings from text,
computing similarities, and managing vector operations for clustering.
"""

import asyncio
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import DBSCAN, KMeans
import pickle
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    """Generates embeddings for text using Hugging Face models with OpenAI fallback."""
    
    def __init__(self, model_name: str = "huggingface", cache_dir: Optional[str] = None):
        """
        Initialize the embedding generator.
        
        Args:
            model_name: Name of the embedding model to use ('huggingface', 'openai')
            cache_dir: Directory to cache the model
        """
        self.model_name = model_name
        self.cache_dir = cache_dir or os.path.join(os.getcwd(), "data", "embeddings")
        self.embedding_dim = 768  # Dimension for distilbert-base-nli-mean-tokens
        self.hf_model = "sentence-transformers/all-MiniLM-L6-v2"  # Fast, good quality model
        self.hf_embedding_model = "sentence-transformers/distilbert-base-nli-mean-tokens"  # Working embedding model
        self.hf_token = os.getenv("HUGGINGFACE_TOKEN")  # Optional token for higher rate limits
        self.openai_api_key = os.getenv("OPENAI_API_KEY")  # OpenAI API key for fallback
        self._setup_model()
    
    def _setup_model(self):
        """Setup the embedding model."""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            
            if self.model_name == "huggingface":
                logger.info(f"Initialized Hugging Face embedding generator with model: {self.hf_model}")
                if self.hf_token:
                    logger.info("Using Hugging Face token for higher rate limits")
                else:
                    logger.info("Using free tier (30K requests/month)")
                if self.openai_api_key:
                    logger.info("OpenAI fallback available")
                else:
                    logger.warning("No OpenAI API key found - HF failures will cause errors")
            elif self.model_name == "openai":
                logger.info("Initialized OpenAI embedding generator")
            else:
                raise ValueError(f"Unsupported model: {self.model_name}. Use 'huggingface' or 'openai'")
                
        except Exception as e:
            logger.error(f"Failed to setup embedding model {self.model_name}: {e}")
            raise
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text using HF → OpenAI fallback chain.
        
        Args:
            text: Input text to embed
            
        Returns:
            numpy array representing the embedding
            
        Raises:
            RuntimeError: If both HF and OpenAI fail
        """
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for embedding generation")
                return np.zeros(self.embedding_dim)
            
            if self.model_name == "huggingface":
                return self._generate_with_fallback_chain(text)
            elif self.model_name == "openai":
                return self._generate_openai_embedding(text)
            else:
                raise ValueError(f"Unsupported model: {self.model_name}")
                
        except Exception as e:
            logger.error(f"Failed to generate embedding for text: {e}")
            raise RuntimeError(f"All embedding methods failed: {e}")
    
    def _generate_with_fallback_chain(self, text: str) -> np.ndarray:
        """Generate embedding with HF → OpenAI fallback chain."""
        # Try Hugging Face first
        if self.hf_token:
            try:
                embedding = self._generate_hf_embedding(text)
                if embedding is not None and not np.all(embedding == 0):
                    logger.debug("Successfully generated HF embedding")
                    return embedding
            except Exception as e:
                logger.warning(f"HF embedding failed: {e}")
        
        # Fallback to OpenAI if available
        if self.openai_api_key:
            try:
                # Use synchronous OpenAI client for fallback
                import openai
                client = openai.OpenAI(api_key=self.openai_api_key)
                response = client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=text
                )
                embedding = np.array(response.data[0].embedding)
                embedding = embedding / np.linalg.norm(embedding)
                logger.info("Using OpenAI fallback for embedding")
                return embedding
            except Exception as e:
                logger.error(f"OpenAI embedding failed: {e}")
        
        # No fallback available
        raise RuntimeError("Both Hugging Face and OpenAI embedding methods failed. Please check your API keys and network connection.")
    
    def _generate_hf_embedding(self, text: str) -> np.ndarray:
        """Generate embedding using Hugging Face Inference API with proper embedding model."""
        import requests
        import json
        
        try:
            # Use a working embedding model
            url = f"https://api-inference.huggingface.co/models/{self.hf_embedding_model}"
            headers = {"Content-Type": "application/json"}
            if self.hf_token:
                headers["Authorization"] = f"Bearer {self.hf_token}"
            
            # Simple payload for this model (it works with basic inputs)
            payload = {"inputs": text}
            
            # Make request
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    # Check if result[0] is a list (nested) or a flat list of numbers
                    if isinstance(result[0], list):
                        # Nested format: [[embedding_values]]
                        embedding_array = np.array(result[0])
                    else:
                        # Flat format: [embedding_values]
                        embedding_array = np.array(result)
                    
                    embedding_array = embedding_array / np.linalg.norm(embedding_array)
                    return embedding_array
                else:
                    raise ValueError(f"Unexpected response format from HF API: {result}")
            else:
                raise RuntimeError(f"HF API request failed ({response.status_code}): {response.text}")
                
        except Exception as e:
            logger.error(f"HF embedding generation failed: {e}")
            raise
    
    async def _generate_openai_embedding(self, text: str) -> np.ndarray:
        """Generate embedding using OpenAI Embeddings API."""
        import openai
        from openai import AsyncOpenAI
        
        try:
            # Create OpenAI client
            client = AsyncOpenAI(api_key=self.openai_api_key)
            
            # Generate embedding
            response = await client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            
            # Extract embedding and normalize
            embedding = np.array(response.data[0].embedding)
            embedding = embedding / np.linalg.norm(embedding)
            return embedding
            
        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {e}")
            raise
    
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for a batch of texts with fallback chain.
        
        Args:
            texts: List of input texts to embed
            
        Returns:
            List of numpy arrays representing the embeddings
            
        Raises:
            RuntimeError: If both HF and OpenAI fail
        """
        try:
            if not texts:
                return []
            
            if self.model_name == "huggingface":
                return self._generate_batch_with_fallback_chain(texts)
            elif self.model_name == "openai":
                return self._generate_openai_embeddings_batch(texts)
            else:
                raise ValueError(f"Unsupported model: {self.model_name}")
                
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise RuntimeError(f"All batch embedding methods failed: {e}")
    
    def _generate_batch_with_fallback_chain(self, texts: List[str]) -> List[np.ndarray]:
        """Generate batch embeddings with HF → OpenAI fallback chain."""
        # Try Hugging Face first
        if self.hf_token:
            try:
                embeddings = self._generate_hf_embeddings_batch(texts)
                if embeddings and not all(np.all(emb == 0) for emb in embeddings):
                    logger.debug("Successfully generated HF batch embeddings")
                    return embeddings
            except Exception as e:
                logger.warning(f"HF batch embedding failed: {e}")
        
        # Fallback to OpenAI if available
        if self.openai_api_key:
            try:
                # Use synchronous OpenAI client for fallback
                import openai
                client = openai.OpenAI(api_key=self.openai_api_key)
                response = client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=texts
                )
                result = []
                for embedding_data in response.data:
                    embedding = np.array(embedding_data.embedding)
                    embedding = embedding / np.linalg.norm(embedding)
                    result.append(embedding)
                logger.info("Using OpenAI fallback for batch embeddings")
                return result
            except Exception as e:
                logger.error(f"OpenAI batch embedding failed: {e}")
        
        # No fallback available
        raise RuntimeError("Both Hugging Face and OpenAI batch embedding methods failed. Please check your API keys and network connection.")
    
    def _generate_hf_embeddings_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings using Hugging Face batch API."""
        import requests
        import json
        
        try:
            # Use the proper embedding model for batch requests
            url = f"https://api-inference.huggingface.co/models/{self.hf_embedding_model}"
            headers = {"Content-Type": "application/json"}
            if self.hf_token:
                headers["Authorization"] = f"Bearer {self.hf_token}"
            
            payload = {"inputs": texts}
            
            # Make request
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                embeddings = response.json()
                if isinstance(embeddings, list) and len(embeddings) == len(texts):
                    # Convert to numpy arrays and normalize
                    result = []
                    for embedding in embeddings:
                        if isinstance(embedding, list):
                            # Nested format: [[embedding_values]]
                            embedding_array = np.array(embedding[0] if len(embedding) > 0 else embedding)
                        else:
                            # Flat format: [embedding_values]
                            embedding_array = np.array(embedding)
                        
                        embedding_array = embedding_array / np.linalg.norm(embedding_array)
                        result.append(embedding_array)
                    return result
                else:
                    raise ValueError(f"Unexpected batch response format from HF API: {embeddings}")
            else:
                raise RuntimeError(f"HF batch API request failed ({response.status_code}): {response.text}")
                
        except Exception as e:
            logger.error(f"HF batch embedding generation failed: {e}")
            raise
    
    async def _generate_openai_embeddings_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings using OpenAI batch API."""
        import openai
        from openai import AsyncOpenAI
        
        try:
            # Create OpenAI client
            client = AsyncOpenAI(api_key=self.openai_api_key)
            
            # Generate embeddings
            response = await client.embeddings.create(
                model="text-embedding-ada-002",
                input=texts
            )
            
            # Extract embeddings and normalize
            result = []
            for embedding_data in response.data:
                embedding = np.array(embedding_data.embedding)
                embedding = embedding / np.linalg.norm(embedding)
                result.append(embedding)
            
            return result
            
        except Exception as e:
            logger.error(f"OpenAI batch embedding generation failed: {e}")
            raise
    
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            
        Returns:
            Cosine similarity score between 0 and 1
        """
        try:
            # Reshape for sklearn
            emb1 = embedding1.reshape(1, -1)
            emb2 = embedding2.reshape(1, -1)
            
            similarity = cosine_similarity(emb1, emb2)[0][0]
            return float(similarity)
        except Exception as e:
            logger.error(f"Failed to compute similarity: {e}")
            return 0.0
    
    def compute_similarity_matrix(self, embeddings: List[np.ndarray]) -> np.ndarray:
        """
        Compute similarity matrix for a list of embeddings.
        
        Args:
            embeddings: List of embeddings
            
        Returns:
            Similarity matrix
        """
        try:
            if not embeddings:
                return np.array([])
            
            # Stack embeddings into a 2D array
            embedding_matrix = np.vstack(embeddings)
            similarity_matrix = cosine_similarity(embedding_matrix)
            return similarity_matrix
        except Exception as e:
            logger.error(f"Failed to compute similarity matrix: {e}")
            return np.array([])

class ClusteringAlgorithm:
    """Implements various clustering algorithms for feedback grouping."""
    
    def __init__(self, algorithm: str = "dbscan", **kwargs):
        """
        Initialize clustering algorithm.
        
        Args:
            algorithm: Clustering algorithm to use ('dbscan', 'kmeans')
            **kwargs: Algorithm-specific parameters
        """
        self.algorithm = algorithm
        self.params = kwargs
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the clustering model based on algorithm choice."""
        if self.algorithm == "dbscan":
            self.model = DBSCAN(
                eps=self.params.get("eps", 0.3),
                min_samples=self.params.get("min_samples", 2),
                metric="cosine"
            )
        elif self.algorithm == "kmeans":
            self.model = KMeans(
                n_clusters=self.params.get("n_clusters", 5),
                random_state=self.params.get("random_state", 42),
                n_init=self.params.get("n_init", 10)
            )
        else:
            raise ValueError(f"Unsupported clustering algorithm: {self.algorithm}")
    
    def fit_predict(self, embeddings: List[np.ndarray]) -> List[int]:
        """
        Fit the clustering model and predict cluster assignments.
        
        Args:
            embeddings: List of embeddings to cluster
            
        Returns:
            List of cluster labels (-1 for noise in DBSCAN)
        """
        try:
            if not embeddings:
                return []
            
            # Stack embeddings into a 2D array
            embedding_matrix = np.vstack(embeddings)
            
            # Fit and predict
            cluster_labels = self.model.fit_predict(embedding_matrix)
            return cluster_labels.tolist()
        except Exception as e:
            logger.error(f"Clustering failed: {e}")
            return [-1] * len(embeddings)
    
    def get_cluster_centers(self, embeddings: List[np.ndarray], labels: List[int]) -> Dict[int, np.ndarray]:
        """
        Get cluster centers from embeddings and labels.
        
        Args:
            embeddings: List of embeddings
            labels: Cluster labels
            
        Returns:
            Dictionary mapping cluster_id to centroid embedding
        """
        try:
            if not embeddings or not labels:
                return {}
            
            embedding_matrix = np.vstack(embeddings)
            cluster_centers = {}
            
            unique_labels = set(labels)
            for label in unique_labels:
                if label == -1:  # Skip noise points
                    continue
                
                # Get embeddings for this cluster
                cluster_mask = np.array(labels) == label
                cluster_embeddings = embedding_matrix[cluster_mask]
                
                # Compute centroid
                centroid = np.mean(cluster_embeddings, axis=0)
                cluster_centers[label] = centroid
            
            return cluster_centers
        except Exception as e:
            logger.error(f"Failed to compute cluster centers: {e}")
            return {}

class SimilarityCalculator:
    """Calculates various similarity metrics for clustering."""
    
    @staticmethod
    def cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings."""
        try:
            dot_product = np.dot(embedding1, embedding2)
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
        except Exception as e:
            logger.error(f"Failed to calculate cosine similarity: {e}")
            return 0.0
    
    @staticmethod
    def euclidean_distance(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate Euclidean distance between two embeddings."""
        try:
            distance = np.linalg.norm(embedding1 - embedding2)
            return float(distance)
        except Exception as e:
            logger.error(f"Failed to calculate Euclidean distance: {e}")
            return float('inf')
    
    @staticmethod
    def manhattan_distance(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate Manhattan distance between two embeddings."""
        try:
            distance = np.sum(np.abs(embedding1 - embedding2))
            return float(distance)
        except Exception as e:
            logger.error(f"Failed to calculate Manhattan distance: {e}")
            return float('inf')

class EmbeddingCache:
    """Manages caching of embeddings to avoid recomputation."""
    
    def __init__(self, cache_dir: str):
        """
        Initialize embedding cache.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "embeddings_cache.pkl"
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict[str, np.ndarray]:
        """Load embeddings from cache file."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'rb') as f:
                    return pickle.load(f)
            return {}
        except Exception as e:
            logger.warning(f"Failed to load embedding cache: {e}")
            return {}
    
    def _save_cache(self):
        """Save embeddings to cache file."""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.cache, f)
        except Exception as e:
            logger.warning(f"Failed to save embedding cache: {e}")
    
    def get(self, text_hash: str) -> Optional[np.ndarray]:
        """Get embedding from cache."""
        return self.cache.get(text_hash)
    
    def set(self, text_hash: str, embedding: np.ndarray):
        """Store embedding in cache."""
        self.cache[text_hash] = embedding
        self._save_cache()
    
    def clear(self):
        """Clear the cache."""
        self.cache.clear()
        if self.cache_file.exists():
            self.cache_file.unlink()
    
    def size(self) -> int:
        """Get cache size."""
        return len(self.cache)
