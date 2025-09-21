"""
Prioritizer Agent for scoring and ranking feedback items.

This agent takes classified and clustered feedback, applies business rules,
and generates priority scores and rankings to help product teams decide
what to work on first.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from sqlalchemy.orm import Session

from agents.base.agent import BaseAgent, AgentResult, AgentContext
from agents.prioritizer.scoring import (
    PriorityCalculator, ScoringWeights, BusinessRules, PriorityScore,
    PriorityLevel, UserSegment
)
from database.models import (
    ProcessedDocument, Cluster, ClusterMembership, 
    ProcessingStatus, FeedbackType
)
from database.models import PrioritizationScore
from config.database import get_session
from config.settings import config

logger = logging.getLogger(__name__)

class PrioritizerAgent(BaseAgent):
    """
    Prioritizer Agent for scoring and ranking feedback items.
    
    This agent:
    1. Fetches classified and clustered feedback
    2. Calculates priority scores using multiple factors
    3. Applies business rules and learning
    4. Generates rankings and reports
    5. Stores priority scores in the database
    """

    def __init__(self, config_overrides: Optional[Dict[str, Any]] = None):
        super().__init__("prioritizer", config_overrides)
        
        # Initialize scoring configuration
        self.weights = ScoringWeights(
            severity=self.config.get("severity_weight", 0.35),
            reach=self.config.get("reach_weight", 0.25),
            recency=self.config.get("recency_weight", 0.20),
            persona=self.config.get("persona_weight", 0.20)
        )
        self.weights.normalize()
        
        # Initialize business rules
        self.rules = BusinessRules(
            cluster_amplification_factor=self.config.get("cluster_amplification_factor", 0.1),
            urgency_boost_factor=self.config.get("urgency_boost_factor", 1.2),
            revenue_critical_boost=self.config.get("revenue_critical_boost", 1.15),
            max_priority_score=self.config.get("max_priority_score", 1.0),
            min_cluster_size_for_amplification=self.config.get("min_cluster_size_for_amplification", 2),
            revenue_critical_components=self.config.get("revenue_critical_components", [
                "authentication", "payment", "api", "database", "security", "core"
            ])
        )
        
        # Initialize priority calculator
        self.calculator = PriorityCalculator(self.weights, self.rules)
        
        # Configuration
        self.batch_size = self.config.get("prioritizer_batch_size", 100)
        self.max_items = self.config.get("max_items_to_prioritize", 1000)
        self.enable_learning = self.config.get("enable_learning", True)
        self.learning_rate = self.config.get("learning_rate", 0.1)

    async def process(self, context: AgentContext) -> AgentResult:
        """
        Main processing method for the Prioritizer Agent.

        Args:
            context: Agent context with execution metadata

        Returns:
            AgentResult: Processing results and statistics
        """
        start_time = datetime.utcnow()
        total_items = 0
        successful_items = 0
        failed_items = 0
        priority_scores_created = 0

        try:
            self.logger.info("Starting feedback prioritization process")

            # Get feedback items that need prioritization
            feedback_items = await self._get_feedback_for_prioritization()
            total_items = len(feedback_items)

            if not feedback_items:
                self.logger.info("No feedback items to prioritize")
                return AgentResult(
                    success=True,
                    items_processed=0,
                    items_successful=0,
                    items_failed=0,
                    execution_time=(datetime.utcnow() - start_time).total_seconds()
                )

            self.logger.info(f"Prioritizing {total_items} feedback items")

            # Process items in batches
            for i in range(0, total_items, self.batch_size):
                batch = feedback_items[i:i + self.batch_size]
                batch_result = await self._process_batch(batch)
                
                successful_items += batch_result["successful"]
                failed_items += batch_result["failed"]
                priority_scores_created += batch_result["scores_created"]

                self.logger.info(f"Processed batch {i//self.batch_size + 1}/{(total_items + self.batch_size - 1)//self.batch_size}")

            # Generate priority rankings
            rankings = await self._generate_rankings()

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            self.logger.info(
                f"Prioritization completed: {successful_items}/{total_items} items processed, "
                f"{priority_scores_created} priority scores created"
            )

            return AgentResult(
                success=True,
                items_processed=total_items,
                items_successful=successful_items,
                items_failed=failed_items,
                execution_time=execution_time,
                metadata={
                    "priority_scores_created": priority_scores_created,
                    "rankings_generated": len(rankings),
                    "priority_distribution": self._get_priority_distribution(),
                    "top_priority_items": rankings[:10] if rankings else []
                }
            )

        except Exception as e:
            self.logger.error(f"Prioritizer Agent failed: {e}", exc_info=True)
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
        return ["classifier", "clusterer"]  # Depends on both Classifier and Clusterer Agents

    async def _get_feedback_for_prioritization(self) -> List[ProcessedDocument]:
        """Get processed documents that need prioritization."""
        with get_session() as session:
            # Fetch documents that have been classified but not yet prioritized
            documents = session.query(ProcessedDocument).filter(
                ProcessedDocument.feedback_type.isnot(None),  # Must be classified
                ProcessedDocument.processing_status == ProcessingStatus.COMPLETED,
                ~ProcessedDocument.id.in_(
                    session.query(PrioritizationScore.document_id)
                )  # Not yet prioritized
            ).limit(self.max_items).all()
            
            return documents

    async def _process_batch(self, documents: List[ProcessedDocument]) -> Dict[str, int]:
        """Process a batch of documents for prioritization."""
        try:
            scores_created = 0
            
            for document in documents:
                # Get cluster data if document is clustered
                cluster_data = await self._get_cluster_data(document)
                
                # Prepare feedback data for scoring
                feedback_data = self._prepare_feedback_data(document, cluster_data)
                
                # Calculate priority score
                priority_score = self.calculator.calculate_priority(feedback_data, cluster_data)
                
                # Store priority score
                await self._store_priority_score(document.id, priority_score)
                scores_created += 1

            return {
                "successful": len(documents),
                "failed": 0,
                "scores_created": scores_created
            }

        except Exception as e:
            self.logger.error(f"Failed to process batch: {e}")
            return {"successful": 0, "failed": len(documents), "scores_created": 0}

    async def _get_cluster_data(self, document: ProcessedDocument) -> Optional[Dict]:
        """Get cluster data for a document."""
        try:
            with self.get_db_session() as session:
                # Find cluster membership
                membership = session.query(ClusterMembership).filter(
                    ClusterMembership.document_id == document.id
                ).first()
                
                if not membership:
                    return None
                
                # Get cluster information
                cluster = session.query(Cluster).filter(
                    Cluster.id == membership.cluster_id
                ).first()
                
                if not cluster:
                    return None
                
                # Get cluster statistics
                cluster_members = session.query(ClusterMembership).filter(
                    ClusterMembership.cluster_id == cluster.id
                ).all()
                
                # Calculate cluster quality metrics
                similarities = [m.similarity_score for m in cluster_members if m.similarity_score]
                avg_similarity = np.mean(similarities) if similarities else 0.5
                
                # Calculate temporal coherence (how close in time the reports are)
                member_docs = session.query(ProcessedDocument).filter(
                    ProcessedDocument.id.in_([m.document_id for m in cluster_members])
                ).all()
                
                timestamps = [doc.timestamp for doc in member_docs]
                if len(timestamps) > 1:
                    time_diffs = [abs((t1 - t2).total_seconds()) for t1 in timestamps for t2 in timestamps if t1 != t2]
                    avg_time_diff = np.mean(time_diffs) if time_diffs else 0
                    temporal_coherence = max(0, 1 - (avg_time_diff / (24 * 3600)))  # Normalize to 24 hours
                else:
                    temporal_coherence = 0.5
                
                # Calculate user diversity
                authors = set(doc.author for doc in member_docs if doc.author)
                user_diversity = len(authors) / len(member_docs) if member_docs else 0.5
                
                return {
                    "id": str(cluster.id),
                    "size": len(cluster_members),
                    "avg_similarity": avg_similarity,
                    "temporal_coherence": temporal_coherence,
                    "user_diversity": user_diversity,
                    "representative_document_id": str(cluster.representative_document_id)
                }

        except Exception as e:
            self.logger.error(f"Failed to get cluster data for document {document.id}: {e}")
            return None

    def _prepare_feedback_data(self, document: ProcessedDocument, cluster_data: Optional[Dict]) -> Dict:
        """Prepare feedback data for priority calculation."""
        # Determine user segment based on author or other indicators
        user_segment = self._determine_user_segment(document)
        
        # Estimate user count (for now, use cluster size or default to 1)
        user_count = cluster_data.get("size", 1) if cluster_data else 1
        
        # Determine feedback quality based on content
        feedback_quality = self._assess_feedback_quality(document)
        
        return {
            "id": str(document.id),
            "title": document.title,
            "body": document.body,
            "severity": document.feedback_type.value if document.feedback_type else "low",
            "component": document.component or "other",
            "timestamp": document.timestamp,
            "author": document.author,
            "user_segment": user_segment,
            "user_count": user_count,
            "feedback_quality": feedback_quality,
            "cluster_size": cluster_data.get("size", 1) if cluster_data else 1,
            "cluster_id": cluster_data.get("id") if cluster_data else None
        }

    def _determine_user_segment(self, document: ProcessedDocument) -> str:
        """Determine user segment based on available data."""
        # This is a simplified implementation
        # In production, this would use more sophisticated user profiling
        
        if not document.author:
            return UserSegment.UNKNOWN
        
        # Simple heuristics based on author patterns
        author = document.author.lower()
        
        if any(keyword in author for keyword in ["enterprise", "corp", "company", "business"]):
            return UserSegment.ENTERPRISE
        elif any(keyword in author for keyword in ["pro", "professional", "team"]):
            return UserSegment.PROFESSIONAL
        elif any(keyword in author for keyword in ["trial", "test", "demo"]):
            return UserSegment.TRIAL
        else:
            return UserSegment.INDIVIDUAL

    def _assess_feedback_quality(self, document: ProcessedDocument) -> str:
        """Assess the quality of feedback based on content."""
        if not document.body:
            return "low"
        
        body = document.body.lower()
        word_count = len(body.split())
        
        # High quality indicators
        high_quality_indicators = [
            "steps to reproduce", "expected behavior", "actual behavior",
            "environment", "version", "browser", "os", "screenshot",
            "error message", "stack trace", "logs"
        ]
        
        # Count quality indicators
        quality_score = sum(1 for indicator in high_quality_indicators if indicator in body)
        
        # Adjust for word count
        if word_count < 10:
            quality_score -= 2
        elif word_count > 100:
            quality_score += 1
        
        if quality_score >= 3:
            return "high"
        elif quality_score >= 1:
            return "medium"
        else:
            return "low"

    async def _store_priority_score(self, document_id: str, priority_score: PriorityScore):
        """Store priority score in the database."""
        try:
            with self.get_db_session() as session:
                # Check if score already exists
                existing_score = session.query(PrioritizationScore).filter(
                    PrioritizationScore.document_id == document_id
                ).first()
                
                if existing_score:
                    # Update existing score
                    existing_score.priority_score = priority_score.final_score
                    existing_score.severity_score = priority_score.severity_score
                    existing_score.reach_score = priority_score.reach_score
                    existing_score.recency_score = priority_score.recency_score
                    existing_score.persona_weight = priority_score.persona_score
                    existing_score.priority_level = self._convert_priority_level_to_int(priority_score.priority_level)
                    existing_score.is_revenue_critical = priority_score.revenue_boost > 1.0
                    existing_score.revenue_impact_multiplier = priority_score.revenue_boost
                else:
                    # Create new score
                    new_score = PrioritizationScore(
                        document_id=document_id,
                        priority_score=priority_score.final_score,
                        severity_score=priority_score.severity_score,
                        reach_score=priority_score.reach_score,
                        recency_score=priority_score.recency_score,
                        persona_weight=priority_score.persona_score,
                        priority_level=self._convert_priority_level_to_int(priority_score.priority_level),
                        is_revenue_critical=priority_score.revenue_boost > 1.0,
                        revenue_impact_multiplier=priority_score.revenue_boost
                    )
                    session.add(new_score)
                
                session.commit()

        except Exception as e:
            self.logger.error(f"Failed to store priority score for document {document_id}: {e}")
            raise

    def _convert_priority_level_to_int(self, priority_level: PriorityLevel) -> int:
        """Convert PriorityLevel enum to integer for database storage."""
        level_mapping = {
            PriorityLevel.CRITICAL: 5,
            PriorityLevel.HIGH: 4,
            PriorityLevel.MEDIUM: 3,
            PriorityLevel.LOW: 2,
            PriorityLevel.MINIMAL: 1
        }
        return level_mapping.get(priority_level, 1)

    async def _generate_rankings(self) -> List[Dict]:
        """Generate priority rankings."""
        try:
            with self.get_db_session() as session:
                # Get all priority scores ordered by priority score
                scores = session.query(PrioritizationScore).order_by(
                    PrioritizationScore.priority_score.desc()
                ).limit(100).all()
                
                rankings = []
                for i, score in enumerate(scores, 1):
                    # Get document details
                    document = session.query(ProcessedDocument).filter(
                        ProcessedDocument.id == score.document_id
                    ).first()
                    
                    if document:
                        rankings.append({
                            "rank": i,
                            "document_id": str(score.document_id),
                            "title": document.title,
                            "priority_score": score.priority_score,
                            "priority_level": score.priority_level,
                            "component": document.component,
                            "reasoning": score.reasoning or []
                        })
                
                return rankings

        except Exception as e:
            self.logger.error(f"Failed to generate rankings: {e}")
            return []

    def _get_priority_distribution(self) -> Dict[str, int]:
        """Get distribution of priority levels."""
        try:
            with self.get_db_session() as session:
                # Count scores by priority level
                distribution = {}
                for level in PriorityLevel:
                    count = session.query(PrioritizationScore).filter(
                        PrioritizationScore.priority_level == level.value
                    ).count()
                    distribution[level.value] = count
                
                return distribution

        except Exception as e:
            self.logger.error(f"Failed to get priority distribution: {e}")
            return {}

    async def get_prioritization_stats(self) -> Dict[str, Any]:
        """Get prioritization statistics."""
        try:
            with self.get_db_session() as session:
                # Get total scores
                total_scores = session.query(PrioritizationScore).count()
                
                # Get average scores
                avg_overall = session.query(PrioritizationScore.priority_score).all()
                avg_overall_score = np.mean([s[0] for s in avg_overall]) if avg_overall else 0
                
                # Get priority distribution
                priority_distribution = self._get_priority_distribution()
                
                # Get top components by priority
                component_scores = session.query(
                    ProcessedDocument.component,
                    PrioritizationScore.priority_score
                ).join(
                    PrioritizationScore, ProcessedDocument.id == PrioritizationScore.document_id
                ).all()
                
                component_avg = {}
                for component, score in component_scores:
                    if component not in component_avg:
                        component_avg[component] = []
                    component_avg[component].append(score)
                
                component_priorities = {
                    comp: np.mean(scores) for comp, scores in component_avg.items()
                }
                
                return {
                    "total_scores": total_scores,
                    "average_priority_score": avg_overall_score,
                    "priority_distribution": priority_distribution,
                    "component_priorities": component_priorities,
                    "weights": {
                        "severity": self.weights.severity,
                        "reach": self.weights.reach,
                        "recency": self.weights.recency,
                        "persona": self.weights.persona
                    }
                }

        except Exception as e:
            self.logger.error(f"Failed to get prioritization stats: {e}")
            return {}

    async def update_weights_from_feedback(self, feedback_data: List[Dict]):
        """Update scoring weights based on feedback loop data."""
        if not self.enable_learning:
            return
        
        try:
            # Simple learning algorithm - adjust weights based on resolution success
            for feedback in feedback_data:
                if feedback.get("resolution_successful", False):
                    # Increase weights for factors that led to successful resolution
                    if feedback.get("high_severity", False):
                        self.weights.severity += self.learning_rate * 0.1
                    if feedback.get("high_reach", False):
                        self.weights.reach += self.learning_rate * 0.1
                    if feedback.get("high_recency", False):
                        self.weights.recency += self.learning_rate * 0.1
                    if feedback.get("high_persona", False):
                        self.weights.persona += self.learning_rate * 0.1
            
            # Normalize weights
            self.weights.normalize()
            
            # Update calculator with new weights
            self.calculator = PriorityCalculator(self.weights, self.rules)
            
            self.logger.info(f"Updated scoring weights: {self.weights.__dict__}")

        except Exception as e:
            self.logger.error(f"Failed to update weights from feedback: {e}")

    async def test_prioritization_system(self) -> bool:
        """Test the prioritization system with sample data."""
        try:
            # Create test feedback data
            test_data = {
                "title": "Critical login issue",
                "body": "Users cannot log in to the system. This is blocking all operations.",
                "severity": "critical",
                "component": "authentication",
                "user_count": 100,
                "user_segment": "enterprise",
                "timestamp": datetime.utcnow(),
                "feedback_quality": "high"
            }
            
            # Calculate priority
            priority_score = self.calculator.calculate_priority(test_data)
            
            # Verify score is reasonable
            return (0 <= priority_score.final_score <= 1 and 
                    priority_score.priority_level in [PriorityLevel.CRITICAL, PriorityLevel.HIGH])

        except Exception as e:
            self.logger.error(f"Prioritization system test failed: {e}")
            return False
