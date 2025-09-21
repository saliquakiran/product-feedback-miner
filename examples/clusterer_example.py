#!/usr/bin/env python3
"""
Example script demonstrating the Clusterer Agent functionality.

This script shows how to:
1. Initialize the Clusterer Agent
2. Process feedback documents for clustering
3. View clustering results and statistics
4. Test different clustering scenarios
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.clusterer.agent import ClustererAgent
from agents.clusterer.embeddings import EmbeddingGenerator, ClusteringAlgorithm, SimilarityCalculator
from agents.base.agent import AgentContext
from database.models import ProcessedDocument, RawFeedback, SourceType, ProcessingStatus, FeedbackType
from database.setup import get_session_maker, create_all_tables

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def create_sample_data():
    """Create sample feedback data for clustering demonstration."""
    logger.info("Creating sample feedback data...")
    
    # Sample feedback data with different clustering scenarios
    sample_feedback = [
        {
            "title": "Login button not working",
            "body": "When I click the login button, nothing happens. I can't access my account.",
            "component": "authentication",
            "feedback_type": FeedbackType.BUG,
            "severity": "high"
        },
        {
            "title": "Login button broken",
            "body": "The login button is broken and doesn't respond to clicks.",
            "component": "authentication", 
            "feedback_type": FeedbackType.BUG,
            "severity": "high"
        },
        {
            "title": "Can't log in to system",
            "body": "I'm unable to log in. The login button doesn't work properly.",
            "component": "authentication",
            "feedback_type": FeedbackType.BUG,
            "severity": "medium"
        },
        {
            "title": "Payment processing error",
            "body": "Getting an error when trying to process payments. Transaction fails.",
            "component": "payment",
            "feedback_type": FeedbackType.BUG,
            "severity": "critical"
        },
        {
            "title": "Payment system down",
            "body": "Payment processing is completely broken. All transactions are failing.",
            "component": "payment",
            "feedback_type": FeedbackType.BUG,
            "severity": "critical"
        },
        {
            "title": "Add dark mode theme",
            "body": "It would be great to have a dark mode option for the application.",
            "component": "ui",
            "feedback_type": FeedbackType.FEATURE_REQUEST,
            "severity": "low"
        },
        {
            "title": "Dark theme request",
            "body": "Please add a dark mode theme option to the interface.",
            "component": "ui",
            "feedback_type": FeedbackType.FEATURE_REQUEST,
            "severity": "low"
        },
        {
            "title": "API timeout issues",
            "body": "API calls are timing out frequently. Response times are too slow.",
            "component": "api",
            "feedback_type": FeedbackType.PERFORMANCE,
            "severity": "high"
        },
        {
            "title": "Slow API responses",
            "body": "The API is responding very slowly. Timeouts are common.",
            "component": "api",
            "feedback_type": FeedbackType.PERFORMANCE,
            "severity": "medium"
        },
        {
            "title": "Mobile app crashes",
            "body": "The mobile app crashes when I try to open it on my phone.",
            "component": "mobile",
            "feedback_type": FeedbackType.BUG,
            "severity": "high"
        }
    ]
    
    # Create database session
    session_maker = get_session_maker()
    
    with session_maker() as session:
        # Create raw feedback records
        raw_feedback_records = []
        for i, feedback in enumerate(sample_feedback):
            raw_feedback = RawFeedback(
                source_type=SourceType.GITHUB_ISSUE.value,
                source_id=f"cluster_sample_{i}",
                url=f"https://example.com/issue/{i}",
                title=feedback["title"],
                content=feedback["body"],
                timestamp=datetime.utcnow() - timedelta(hours=i*2)  # Stagger timestamps
            )
            session.add(raw_feedback)
            raw_feedback_records.append(raw_feedback)
        
        session.commit()
        
        # Create processed documents
        processed_docs = []
        for i, (raw_feedback, feedback) in enumerate(zip(raw_feedback_records, sample_feedback)):
            processed_doc = ProcessedDocument(
                raw_feedback_id=raw_feedback.id,
                title=feedback["title"],
                body=feedback["body"],
                author=f"user_{i}",
                timestamp=datetime.utcnow() - timedelta(hours=i*2),
                url=f"https://example.com/issue/{i}",
                language="en",
                word_count=len(feedback["body"].split()),
                feedback_type=feedback["feedback_type"],
                component=feedback["component"],
                processing_status=ProcessingStatus.COMPLETED
            )
            session.add(processed_doc)
            processed_docs.append(processed_doc)
        
        session.commit()
        logger.info(f"Created {len(processed_docs)} sample documents for clustering")
        return processed_docs

async def demonstrate_embedding_generation():
    """Demonstrate embedding generation functionality."""
    logger.info("=== Embedding Generation Demo ===")
    
    generator = EmbeddingGenerator()
    
    # Test different types of feedback
    test_texts = [
        "Login button not working",
        "Login button broken", 
        "Can't log in to system",
        "Payment processing error",
        "Add dark mode theme",
        "API timeout issues"
    ]
    
    logger.info("Generating embeddings for sample texts...")
    embeddings = []
    for text in test_texts:
        embedding = generator.generate_embedding(text)
        embeddings.append(embedding)
        logger.info(f"  '{text}' -> embedding dim: {len(embedding)}")
    
    # Test similarity between similar texts
    logger.info("\nTesting similarity between similar texts:")
    similarity_calc = SimilarityCalculator()
    
    # Login-related texts
    login_similarity = similarity_calc.cosine_similarity(embeddings[0], embeddings[1])
    logger.info(f"  'Login button not working' vs 'Login button broken': {login_similarity:.3f}")
    
    # Different topics
    different_similarity = similarity_calc.cosine_similarity(embeddings[0], embeddings[4])
    logger.info(f"  'Login button not working' vs 'Add dark mode theme': {different_similarity:.3f}")

async def demonstrate_clustering_algorithms():
    """Demonstrate different clustering algorithms."""
    logger.info("\n=== Clustering Algorithms Demo ===")
    
    # Generate sample embeddings
    generator = EmbeddingGenerator()
    test_texts = [
        "Login button not working",
        "Login button broken",
        "Can't log in to system", 
        "Payment processing error",
        "Payment system down",
        "Add dark mode theme",
        "Dark theme request",
        "API timeout issues",
        "Slow API responses",
        "Mobile app crashes"
    ]
    
    embeddings = [generator.generate_embedding(text) for text in test_texts]
    
    # Test DBSCAN clustering
    logger.info("Testing DBSCAN clustering:")
    dbscan = ClusteringAlgorithm(algorithm="dbscan", eps=0.3, min_samples=2)
    dbscan_labels = dbscan.fit_predict(embeddings)
    
    # Group texts by cluster
    dbscan_clusters = {}
    for i, (text, label) in enumerate(zip(test_texts, dbscan_labels)):
        if label not in dbscan_clusters:
            dbscan_clusters[label] = []
        dbscan_clusters[label].append(text)
    
    for cluster_id, texts in dbscan_clusters.items():
        if cluster_id == -1:
            logger.info(f"  Noise: {texts}")
        else:
            logger.info(f"  Cluster {cluster_id}: {texts}")
    
    # Test K-means clustering
    logger.info("\nTesting K-means clustering:")
    kmeans = ClusteringAlgorithm(algorithm="kmeans", n_clusters=3, random_state=42)
    kmeans_labels = kmeans.fit_predict(embeddings)
    
    # Group texts by cluster
    kmeans_clusters = {}
    for i, (text, label) in enumerate(zip(test_texts, kmeans_labels)):
        if label not in kmeans_clusters:
            kmeans_clusters[label] = []
        kmeans_clusters[label].append(text)
    
    for cluster_id, texts in kmeans_clusters.items():
        logger.info(f"  Cluster {cluster_id}: {texts}")

async def demonstrate_clustering_process():
    """Demonstrate the full clustering process."""
    logger.info("\n=== Clustering Process Demo ===")
    
    # Initialize agent
    agent = ClustererAgent({
        "clustering_batch_size": 5,
        "max_documents_to_cluster": 50,
        "similarity_threshold": 0.3,
        "min_cluster_size": 2
    })
    
    # Create agent context
    context = AgentContext(
        agent_name="clusterer",
        execution_id="demo_execution",
        started_at=datetime.utcnow()
    )
    
    # Run clustering process
    logger.info("Running clustering process...")
    result = await agent.process(context)
    
    if result.success:
        logger.info(f"Clustering completed successfully!")
        logger.info(f"Items processed: {result.items_processed}")
        logger.info(f"Items successful: {result.items_successful}")
        logger.info(f"Items failed: {result.items_failed}")
        logger.info(f"Execution time: {result.execution_time:.2f} seconds")
        
        if result.metadata:
            logger.info(f"Clusters created: {result.metadata.get('clusters_created', 0)}")
            logger.info(f"Average cluster size: {result.metadata.get('average_cluster_size', 0):.2f}")
            logger.info(f"Similarity threshold: {result.metadata.get('similarity_threshold', 0)}")
            logger.info(f"Min cluster size: {result.metadata.get('min_cluster_size', 0)}")
    else:
        logger.error(f"Clustering failed: {result.error_message}")

async def demonstrate_clustering_statistics():
    """Demonstrate clustering statistics."""
    logger.info("\n=== Clustering Statistics Demo ===")
    
    agent = ClustererAgent()
    
    # Get clustering statistics
    stats = await agent.get_clustering_stats()
    
    logger.info("Clustering Statistics:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")

async def demonstrate_embedding_cache():
    """Demonstrate embedding cache functionality."""
    logger.info("\n=== Embedding Cache Demo ===")
    
    agent = ClustererAgent()
    
    # Test cache operations
    logger.info("Testing embedding cache...")
    
    # Get initial cache stats
    initial_stats = await agent.get_cache_stats()
    logger.info(f"Initial cache size: {initial_stats.get('cache_size', 0)}")
    
    # Test embedding generation (should populate cache)
    test_text = "This is a test for embedding cache"
    embedding = agent.embedding_generator.generate_embedding(test_text)
    logger.info(f"Generated embedding for test text (dim: {len(embedding)})")
    
    # Get updated cache stats
    updated_stats = await agent.get_cache_stats()
    logger.info(f"Updated cache size: {updated_stats.get('cache_size', 0)}")
    
    # Test cache clearing
    await agent.clear_embedding_cache()
    final_stats = await agent.get_cache_stats()
    logger.info(f"Cache size after clearing: {final_stats.get('cache_size', 0)}")

async def demonstrate_similarity_calculations():
    """Demonstrate different similarity calculation methods."""
    logger.info("\n=== Similarity Calculations Demo ===")
    
    generator = EmbeddingGenerator()
    similarity_calc = SimilarityCalculator()
    
    # Generate embeddings for comparison
    text1 = "Login button not working"
    text2 = "Login button broken"
    text3 = "Payment processing error"
    
    emb1 = generator.generate_embedding(text1)
    emb2 = generator.generate_embedding(text2)
    emb3 = generator.generate_embedding(text3)
    
    logger.info(f"Comparing: '{text1}' vs '{text2}'")
    cosine_sim = similarity_calc.cosine_similarity(emb1, emb2)
    euclidean_dist = similarity_calc.euclidean_distance(emb1, emb2)
    manhattan_dist = similarity_calc.manhattan_distance(emb1, emb2)
    
    logger.info(f"  Cosine similarity: {cosine_sim:.3f}")
    logger.info(f"  Euclidean distance: {euclidean_dist:.3f}")
    logger.info(f"  Manhattan distance: {manhattan_dist:.3f}")
    
    logger.info(f"\nComparing: '{text1}' vs '{text3}'")
    cosine_sim2 = similarity_calc.cosine_similarity(emb1, emb3)
    euclidean_dist2 = similarity_calc.euclidean_distance(emb1, emb3)
    manhattan_dist2 = similarity_calc.manhattan_distance(emb1, emb3)
    
    logger.info(f"  Cosine similarity: {cosine_sim2:.3f}")
    logger.info(f"  Euclidean distance: {euclidean_dist2:.3f}")
    logger.info(f"  Manhattan distance: {manhattan_dist2:.3f}")

async def main():
    """Main demonstration function."""
    logger.info("Starting Clusterer Agent Demonstration")
    logger.info("=" * 60)
    
    try:
        # Ensure database is set up
        logger.info("Setting up database...")
        create_all_tables()
        
        # Create sample data
        await create_sample_data()
        
        # Demonstrate embedding generation
        await demonstrate_embedding_generation()
        
        # Demonstrate clustering algorithms
        await demonstrate_clustering_algorithms()
        
        # Demonstrate full clustering process
        await demonstrate_clustering_process()
        
        # Demonstrate statistics
        await demonstrate_clustering_statistics()
        
        # Demonstrate embedding cache
        await demonstrate_embedding_cache()
        
        # Demonstrate similarity calculations
        await demonstrate_similarity_calculations()
        
        logger.info("\n" + "=" * 60)
        logger.info("Clusterer Agent demonstration completed successfully!")
        
    except Exception as e:
        logger.error(f"Demonstration failed: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    # Run the demonstration
    exit_code = asyncio.run(main())
    sys.exit(exit_code)