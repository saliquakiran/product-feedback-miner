"""
Clusterer Agent for grouping similar feedback using embeddings and clustering algorithms.

This agent takes classified feedback documents, generates embeddings,
clusters them based on similarity, and creates cluster records in the database.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from sqlalchemy.orm import Session

from agents.base.agent import BaseAgent, AgentResult, AgentContext
from agents.clusterer.embeddings import EmbeddingGenerator, ClusteringAlgorithm, SimilarityCalculator, EmbeddingCache
from database.models import ProcessedDocument, Cluster, ClusterMembership, ProcessingStatus
from config.settings import config

logger = logging.getLogger(__name__)

class ClustererAgent(BaseAgent):
    """
    Clusterer Agent for grouping similar feedback using embeddings and clustering.
    
    This agent:
    1. Fetches classified feedback documents
    2. Generates embeddings for the content
    3. Clusters documents based on similarity
    4. Creates cluster records and memberships
    5. Updates document cluster assignments
    """

    def __init__(self, config_overrides: Optional[Dict[str, Any]] = None):
        super().__init__("clusterer", config_overrides)
        
        # Initialize embedding generator
        self.embedding_generator = EmbeddingGenerator(
            model_name=self.config.get("embedding_model", "huggingface"),
            cache_dir=self.config.get("embedding_cache_dir", "data/embeddings")
        )
        
        # Initialize clustering algorithm
        self.clustering_algorithm = ClusteringAlgorithm(
            algorithm=self.config.get("clustering_algorithm", "dbscan"),
            eps=self.config.get("similarity_threshold", 0.3),
            min_samples=self.config.get("min_cluster_size", 2)
        )
        
        # Initialize similarity calculator
        self.similarity_calculator = SimilarityCalculator()
        
        # Initialize embedding cache
        self.embedding_cache = EmbeddingCache(
            cache_dir=self.config.get("embedding_cache_dir", "data/embeddings")
        )
        
        # Configuration
        self.batch_size = self.config.get("clustering_batch_size", 100)
        self.max_documents = self.config.get("max_documents_to_cluster", 1000)
        self.similarity_threshold = self.config.get("similarity_threshold", 0.3)
        self.min_cluster_size = self.config.get("min_cluster_size", 2)
        self.enable_incremental_clustering = self.config.get("enable_incremental_clustering", True)

    async def process(self, context: AgentContext) -> AgentResult:
        """
        Main processing method for the Clusterer Agent.

        Args:
            context: Agent context with execution metadata

        Returns:
            AgentResult: Processing results and statistics
        """
        start_time = datetime.utcnow()
        total_items = 0
        successful_items = 0
        failed_items = 0
        clusters_created = 0

        try:
            self.logger.info("Starting feedback clustering process")

            # Get documents that need clustering
            documents_to_cluster = await self._get_documents_for_clustering()
            total_items = len(documents_to_cluster)

            if not documents_to_cluster:
                self.logger.info("No documents to cluster")
                return AgentResult(
                    success=True,
                    items_processed=0,
                    items_successful=0,
                    items_failed=0,
                    execution_time=(datetime.utcnow() - start_time).total_seconds()
                )

            self.logger.info(f"Clustering {total_items} documents")

            # Process documents in batches
            for i in range(0, total_items, self.batch_size):
                batch = documents_to_cluster[i:i + self.batch_size]
                batch_result = await self._process_batch(batch)
                
                successful_items += batch_result["successful"]
                failed_items += batch_result["failed"]
                clusters_created += batch_result["clusters_created"]

                self.logger.info(f"Processed batch {i//self.batch_size + 1}/{(total_items + self.batch_size - 1)//self.batch_size}")

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            self.logger.info(
                f"Clustering completed: {successful_items}/{total_items} documents processed, "
                f"{clusters_created} clusters created"
            )

            return AgentResult(
                success=True,
                items_processed=total_items,
                items_successful=successful_items,
                items_failed=failed_items,
                execution_time=execution_time,
                metadata={
                    "clusters_created": clusters_created,
                    "average_cluster_size": clusters_created / max(successful_items, 1),
                    "similarity_threshold": self.similarity_threshold,
                    "min_cluster_size": self.min_cluster_size
                }
            )

        except Exception as e:
            self.logger.error(f"Clusterer Agent failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                items_processed=total_items,
                items_successful=successful_items,
                items_failed=failed_items,
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                error_message=str(e)
            )

    def get_input_dependencies(self) -> List[str]:
        """Get list of agent names that this agent depends on for input."""
        return ["classifier"]  # Depends on Classifier Agent

    async def _get_documents_for_clustering(self) -> List[ProcessedDocument]:
        """Get processed documents that need clustering."""
        async with self.get_db_session() as session:
            # Fetch documents that have been classified but not yet clustered
            documents = session.query(ProcessedDocument).filter(
                ProcessedDocument.feedback_type.isnot(None),  # Must be classified
                ProcessedDocument.processing_status == ProcessingStatus.COMPLETED,
                ProcessedDocument.cluster_id.is_(None)  # Not yet clustered
            ).limit(self.max_documents).all()
            
            return documents

    async def _process_batch(self, documents: List[ProcessedDocument]) -> Dict[str, int]:
        """Process a batch of documents for clustering."""
        try:
            # Generate embeddings for the batch
            texts = [self._prepare_text_for_embedding(doc) for doc in documents]
            embeddings = await self._generate_embeddings_batch(texts)
            
            if not embeddings:
                return {"successful": 0, "failed": len(documents), "clusters_created": 0}

            # Cluster the embeddings
            cluster_labels = self.clustering_algorithm.fit_predict(embeddings)
            
            # Create clusters and memberships
            clusters_created = await self._create_clusters_and_memberships(
                documents, embeddings, cluster_labels
            )
            
            return {
                "successful": len(documents),
                "failed": 0,
                "clusters_created": clusters_created
            }

        except Exception as e:
            self.logger.error(f"Failed to process batch: {e}")
            return {"successful": 0, "failed": len(documents), "clusters_created": 0}

    def _prepare_text_for_embedding(self, document: ProcessedDocument) -> str:
        """Prepare document text for embedding generation."""
        # Combine title and body for better clustering
        text_parts = []
        
        if document.title:
            text_parts.append(document.title)
        
        if document.body:
            text_parts.append(document.body)
        
        # Add component and feedback type for better clustering
        if document.component:
            text_parts.append(f"Component: {document.component}")
        
        if document.feedback_type:
            text_parts.append(f"Type: {document.feedback_type.value}")
        
        return " ".join(text_parts)

    async def _generate_embeddings_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for a batch of texts."""
        try:
            # Check cache first
            embeddings = []
            texts_to_embed = []
            text_indices = []
            
            for i, text in enumerate(texts):
                text_hash = str(hash(text))
                cached_embedding = self.embedding_cache.get(text_hash)
                
                if cached_embedding is not None:
                    embeddings.append(cached_embedding)
                else:
                    embeddings.append(None)
                    texts_to_embed.append(text)
                    text_indices.append(i)
            
            # Generate embeddings for uncached texts
            if texts_to_embed:
                new_embeddings = self.embedding_generator.generate_embeddings_batch(texts_to_embed)
                
                # Cache new embeddings and update results
                for i, (text, embedding) in enumerate(zip(texts_to_embed, new_embeddings)):
                    text_hash = str(hash(text))
                    self.embedding_cache.set(text_hash, embedding)
                    embeddings[text_indices[i]] = embedding
            
            return embeddings

        except Exception as e:
            self.logger.error(f"Failed to generate embeddings: {e}")
            return []

    async def _create_clusters_and_memberships(
        self, 
        documents: List[ProcessedDocument], 
        embeddings: List[np.ndarray], 
        cluster_labels: List[int]
    ) -> int:
        """Create cluster records and memberships in the database."""
        try:
            clusters_created = 0
            
            async with self.get_db_session() as session:
                # Group documents by cluster
                cluster_groups = {}
                for doc, embedding, label in zip(documents, embeddings, cluster_labels):
                    if label not in cluster_groups:
                        cluster_groups[label] = []
                    cluster_groups[label].append((doc, embedding))
                
                # Create clusters and memberships
                for cluster_id, group in cluster_groups.items():
                    if cluster_id == -1:  # Skip noise points
                        continue
                    
                    if len(group) < self.min_cluster_size:
                        continue
                    
                    # Create cluster record
                    cluster = await self._create_cluster_record(session, group, cluster_id)
                    if cluster:
                        clusters_created += 1
                        
                        # Create memberships
                        await self._create_memberships(session, cluster, group)
                
                session.commit()
                return clusters_created

        except Exception as e:
            self.logger.error(f"Failed to create clusters and memberships: {e}")
            return 0

    async def _create_cluster_record(
        self, 
        session: Session, 
        group: List[Tuple[ProcessedDocument, np.ndarray]], 
        cluster_id: int
    ) -> Optional[Cluster]:
        """Create a cluster record in the database."""
        try:
            if not group:
                return None
            
            # Calculate cluster centroid
            embeddings = [embedding for _, embedding in group]
            centroid = np.mean(embeddings, axis=0)
            
            # Get representative document (first one for now)
            representative_doc = group[0][0]
            
            # Create cluster
            cluster = Cluster(
                title=f"Cluster {cluster_id}",
                summary=f"Cluster of {len(group)} similar feedback items",
                centroid_embedding=centroid.tolist(),
                member_count=len(group),
                feedback_type=representative_doc.feedback_type.value if representative_doc.feedback_type else None,
                component=representative_doc.component,
                avg_severity=representative_doc.severity_score if hasattr(representative_doc, 'severity_score') else None,
                similarity_threshold=self.similarity_threshold
            )
            
            session.add(cluster)
            session.flush()  # Get the cluster ID
            
            return cluster

        except Exception as e:
            self.logger.error(f"Failed to create cluster record: {e}")
            return None

    async def _create_memberships(
        self, 
        session: Session, 
        cluster: Cluster, 
        group: List[Tuple[ProcessedDocument, np.ndarray]]
    ):
        """Create cluster membership records."""
        try:
            # Get the first document as representative
            representative_doc = group[0][0] if group else None
            
            for i, (doc, embedding) in enumerate(group):
                # Calculate similarity to centroid
                similarity = self.similarity_calculator.cosine_similarity(
                    embedding, np.array(cluster.centroid_embedding)
                )
                
                # Create membership
                membership = ClusterMembership(
                    cluster_id=cluster.id,
                    document_id=doc.id,
                    similarity_score=similarity,
                    is_representative=(i == 0)  # First document is representative
                )
                
                session.add(membership)
                
                # Update document with cluster assignment
                doc.cluster_id = cluster.id
                doc.processing_status = ProcessingStatus.COMPLETED  # Mark as completed by clusterer

        except Exception as e:
            self.logger.error(f"Failed to create memberships: {e}")
            raise

    async def get_clustering_stats(self) -> Dict[str, Any]:
        """Get clustering statistics."""
        try:
            with self.get_db_session() as session:
                # Get cluster count
                cluster_count = session.query(Cluster).count()
                
                # Get membership count
                membership_count = session.query(ClusterMembership).count()
                
                # Get average cluster size
                avg_cluster_size = membership_count / max(cluster_count, 1)
                
                # Get documents by cluster status
                clustered_docs = session.query(ClusterMembership).count()
                
                total_classified_docs = session.query(ProcessedDocument).filter(
                    ProcessedDocument.feedback_type.isnot(None)
                ).count()
                
                unclustered_docs = total_classified_docs - clustered_docs
                
                return {
                    "total_clusters": cluster_count,
                    "total_memberships": membership_count,
                    "average_cluster_size": avg_cluster_size,
                    "clustered_documents": clustered_docs,
                    "unclustered_documents": unclustered_docs,
                    "clustering_rate": clustered_docs / max(clustered_docs + unclustered_docs, 1)
                }

        except Exception as e:
            self.logger.error(f"Failed to get clustering stats: {e}")
            return {}

    async def test_embedding_generation(self) -> bool:
        """Test embedding generation functionality."""
        try:
            test_text = "This is a test feedback item for embedding generation"
            embedding = self.embedding_generator.generate_embedding(test_text)
            
            if embedding is None or len(embedding) == 0:
                return False
            
            # Test similarity calculation
            embedding2 = self.embedding_generator.generate_embedding("Similar test feedback")
            similarity = self.similarity_calculator.cosine_similarity(embedding, embedding2)
            
            # For hash-based embeddings, similarity can be negative
            return -1 <= similarity <= 1

        except Exception as e:
            self.logger.error(f"Embedding generation test failed: {e}")
            return False

    async def clear_embedding_cache(self):
        """Clear the embedding cache."""
        try:
            self.embedding_cache.clear()
            self.logger.info("Embedding cache cleared")
        except Exception as e:
            self.logger.error(f"Failed to clear embedding cache: {e}")

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get embedding cache statistics."""
        try:
            return {
                "cache_size": self.embedding_cache.size(),
                "cache_dir": str(self.embedding_cache.cache_dir)
            }
        except Exception as e:
            self.logger.error(f"Failed to get cache stats: {e}")
            return {}
