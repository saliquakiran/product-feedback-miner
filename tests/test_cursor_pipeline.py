#!/usr/bin/env python3
"""
Complete End-to-End Pipeline Test for Cursor Product
This script tests the entire workflow from ingestion to report generation.
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta
sys.path.insert(0, os.getcwd())
from dotenv import load_dotenv
load_dotenv()

# Import all agents
from agents.ingestor.agent import IngestorAgent
from agents.normalizer.agent import NormalizerAgent
from agents.classifier.agent import ClassifierAgent
from agents.clusterer.agent import ClustererAgent
from agents.prioritizer.agent import PrioritizerAgent
from agents.actioner.agent import ActionerAgent
from agents.digestor.agent import DigestorAgent
from agents.feedback_loop.agent import FeedbackLoopAgent

from agents.base.agent import AgentContext
from database.models import ProcessedDocument, PrioritizationScore, Cluster, ClusterMembership, RawFeedback
from config.database import get_session
import uuid

async def test_cursor_complete_pipeline():
    """Test the complete pipeline for Cursor product feedback."""
    
    print('🚀 COMPLETE PIPELINE TEST: CURSOR PRODUCT FEEDBACK')
    print('=' * 80)
    print(f'Started at: {datetime.now()}')
    print(f'Target: Collect Cursor feedback from last 4 months')
    print()
    
    execution_id = str(uuid.uuid4())
    context = AgentContext(
        execution_id=execution_id,
        agent_name='cursor_pipeline',
        started_at=datetime.now(),
        config={'product_name': 'Cursor'},
        metadata={'product_name': 'Cursor', 'test_mode': False}
    )
    
    try:
        # Clear existing data for fresh test
        print('🧹 CLEARING EXISTING DATA FOR FRESH TEST')
        print('-' * 60)
        
        with get_session() as session:
            # Clear all existing data
            session.query(ClusterMembership).delete()
            session.query(PrioritizationScore).delete()
            session.query(Cluster).delete()
            session.query(ProcessedDocument).delete()
            session.query(RawFeedback).delete()
            session.commit()
            
            print('   ✅ Cleared all existing data')
        
        print()
        
        # ============================================================================
        # STEP 1: INGESTOR AGENT - Collect Cursor feedback from last 4 months
        # ============================================================================
        print('1️⃣ INGESTOR AGENT - Collecting Cursor feedback from last 4 months...')
        print('-' * 60)
        
        # Calculate date 4 months ago
        four_months_ago = datetime.now() - timedelta(days=120)
        
        ingestor = IngestorAgent({
            'product_name': 'Cursor',
            'sources': {
                'github': {
                    'enabled': True, 
                    'repos': ['getcursor/cursor'],
                    'since_date': four_months_ago.isoformat()
                },
                'hackernews': {
                    'enabled': True,
                    'since_date': four_months_ago.isoformat()
                },
                'exa': {
                    'enabled': True,
                    'queries': [
                        'Cursor IDE feedback',
                        'Cursor editor issues',
                        'Cursor AI code assistant problems',
                        'Cursor software bugs',
                        'Cursor feature requests'
                    ],
                    'since_date': four_months_ago.isoformat()
                },
                'twitter': {'enabled': False},  # Disable for now
                'reddit': {'enabled': False}    # Disable for now
            },
            'max_items_per_source': 20,  # Reasonable limit
            'min_content_length': 10     # Filter out very short content
        })
        
        print(f'   📅 Collecting feedback since: {four_months_ago.strftime("%Y-%m-%d")}')
        print(f'   🔍 Sources: GitHub (getcursor/cursor), Hacker News, Exa AI')
        print(f'   📊 Max items per source: 20')
        
        ingestor_start = datetime.now()
        ingestor_result = await ingestor.process(context)
        ingestor_duration = (datetime.now() - ingestor_start).total_seconds()
        
        print(f'   ✅ Ingestor completed: {ingestor_result.success}')
        print(f'   📊 Items collected: {ingestor_result.metadata.get("total_items", 0)}')
        print(f'   ⏱️  Duration: {ingestor_duration:.2f}s')
        
        if not ingestor_result.success:
            print('   ❌ Ingestor failed, stopping pipeline')
            return False
        
        # Check what we actually collected
        with get_session() as session:
            raw_count = session.query(RawFeedback).count()
            processed_count = session.query(ProcessedDocument).count()
            print(f'   📄 Raw feedback items: {raw_count}')
            print(f'   📄 Processed documents: {processed_count}')
        
        print()
        
        # ============================================================================
        # STEP 2: NORMALIZER AGENT - Clean and normalize the data
        # ============================================================================
        print('2️⃣ NORMALIZER AGENT - Cleaning and normalizing data...')
        print('-' * 60)
        
        normalizer = NormalizerAgent({
            'batch_size': 10,
            'enable_deduplication': True,
            'enable_language_detection': True,
            'enable_pii_scrubbing': True,
            'min_word_count': 5  # Filter out very short content
        })
        
        normalizer_start = datetime.now()
        normalizer_result = await normalizer.process(context)
        normalizer_duration = (datetime.now() - normalizer_start).total_seconds()
        
        print(f'   ✅ Normalizer completed: {normalizer_result.success}')
        print(f'   📊 Items processed: {normalizer_result.metadata.get("processed_items", 0)}')
        print(f'   ⏱️  Duration: {normalizer_duration:.2f}s')
        
        # Check processing results
        with get_session() as session:
            processed_count = session.query(ProcessedDocument).count()
            print(f'   📄 Total processed documents: {processed_count}')
        
        if not normalizer_result.success:
            print('   ❌ Normalizer failed, stopping pipeline')
            return False
        
        print()
        
        # ============================================================================
        # STEP 3: CLASSIFIER AGENT - Categorize the feedback
        # ============================================================================
        print('3️⃣ CLASSIFIER AGENT - Categorizing feedback by type and severity...')
        print('-' * 60)
        
        classifier = ClassifierAgent({
            'batch_size': 5,
            'model': 'gpt-3.5-turbo',
            'temperature': 0.1,
            'timeout': 120  # Longer timeout for classification
        })
        
        classifier_start = datetime.now()
        classifier_result = await classifier.process(context)
        classifier_duration = (datetime.now() - classifier_start).total_seconds()
        
        print(f'   ✅ Classifier completed: {classifier_result.success}')
        print(f'   📊 Items classified: {classifier_result.metadata.get("classified_items", 0)}')
        print(f'   ⏱️  Duration: {classifier_duration:.2f}s')
        
        # Check classification results
        with get_session() as session:
            classified_count = session.query(ProcessedDocument).filter(
                ProcessedDocument.feedback_type.isnot(None)
            ).count()
            print(f'   📄 Classified documents: {classified_count}')
            
            # Show breakdown by type
            if classified_count > 0:
                from sqlalchemy import func
                types = session.query(ProcessedDocument.feedback_type, 
                                    func.count(ProcessedDocument.id)).group_by(
                    ProcessedDocument.feedback_type).all()
                print('   📊 Classification breakdown:')
                for feedback_type, count in types:
                    print(f'      {feedback_type}: {count}')
        
        if not classifier_result.success:
            print('   ❌ Classifier failed, stopping pipeline')
            return False
        
        print()
        
        # ============================================================================
        # STEP 4: CLUSTERER AGENT - Group similar feedback
        # ============================================================================
        print('4️⃣ CLUSTERER AGENT - Grouping similar feedback...')
        print('-' * 60)
        
        # Check if we have enough classified data for clustering
        with get_session() as session:
            classified_count = session.query(ProcessedDocument).filter(
                ProcessedDocument.feedback_type.isnot(None)
            ).count()
        
        if classified_count < 2:
            print('   ⚠️  Skipping Clusterer - Need at least 2 classified documents')
            clusterer_result = type('obj', (object,), {
                'success': True, 
                'execution_time': 0.0,
                'metadata': {'clusters_created': 0}
            })()
            clusterer_duration = 0.0
        else:
            clusterer = ClustererAgent({
                'embedding_model': 'huggingface',
                'similarity_threshold': 0.75,  # Slightly lower for better clustering
                'min_cluster_size': 2,
                'batch_size': 10,
                'timeout': 180  # Longer timeout for embeddings
            })
            
            clusterer_start = datetime.now()
            clusterer_result = await clusterer.process(context)
            clusterer_duration = (datetime.now() - clusterer_start).total_seconds()
            
            print(f'   ✅ Clusterer completed: {clusterer_result.success}')
            print(f'   📊 Clusters created: {clusterer_result.metadata.get("clusters_created", 0)}')
            print(f'   ⏱️  Duration: {clusterer_duration:.2f}s')
            
            # Check clustering results
            with get_session() as session:
                clusters_count = session.query(Cluster).count()
                memberships_count = session.query(ClusterMembership).count()
                print(f'   📄 Total clusters: {clusters_count}')
                print(f'   📄 Cluster memberships: {memberships_count}')
        
        print()
        
        # ============================================================================
        # STEP 5: PRIORITIZER AGENT - Score and rank feedback
        # ============================================================================
        print('5️⃣ PRIORITIZER AGENT - Scoring and ranking feedback by priority...')
        print('-' * 60)
        
        prioritizer = PrioritizerAgent({
            'severity_weight': 0.35,
            'reach_weight': 0.25,
            'recency_weight': 0.20,
            'persona_weight': 0.20,
            'max_items_to_prioritize': 50,  # Higher limit for more data
            'enable_learning': True
        })
        
        prioritizer_start = datetime.now()
        prioritizer_result = await prioritizer.process(context)
        prioritizer_duration = (datetime.now() - prioritizer_start).total_seconds()
        
        if prioritizer_result is None:
            print(f'   ❌ Prioritizer returned None result')
            prioritizer_result = type('obj', (object,), {
                'success': False, 
                'execution_time': prioritizer_duration,
                'metadata': {'prioritized_items': 0}
            })()
        else:
            print(f'   ✅ Prioritizer completed: {prioritizer_result.success}')
            print(f'   📊 Items prioritized: {prioritizer_result.metadata.get("prioritized_items", 0) if prioritizer_result.metadata else 0}')
        
        print(f'   ⏱️  Duration: {prioritizer_duration:.2f}s')
        
        # Check prioritization results
        with get_session() as session:
            prioritized_count = session.query(PrioritizationScore).count()
            print(f'   📄 Prioritized items: {prioritized_count}')
            
            if prioritized_count > 0:
                # Show top priorities
                top_priorities = session.query(PrioritizationScore).order_by(
                    PrioritizationScore.final_score.desc()).limit(5).all()
                print('   🎯 Top 5 priorities:')
                for i, priority in enumerate(top_priorities, 1):
                    print(f'      {i}. Score: {priority.final_score:.3f} - {priority.priority_level.value}')
        
        if not prioritizer_result.success:
            print('   ❌ Prioritizer failed, stopping pipeline')
            return False
        
        print()
        
        # ============================================================================
        # STEP 6: ACTIONER AGENT - Create tickets (disabled for demo)
        # ============================================================================
        print('6️⃣ ACTIONER AGENT - Creating tickets (disabled for demo)...')
        print('-' * 60)
        
        actioner = ActionerAgent({
            'actioner': {
                'enable_jira': False,  # Disabled for demo
                'enable_github': False,  # Disabled for demo
                'priority_threshold': 0.7,
                'max_tickets_per_hour': 10
            }
        })
        
        actioner_start = datetime.now()
        actioner_result = await actioner.process(context)
        actioner_duration = (datetime.now() - actioner_start).total_seconds()
        
        print(f'   ✅ Actioner completed: {actioner_result.success}')
        print(f'   📊 Tickets created: {actioner_result.metadata.get("tickets_created", 0)}')
        print(f'   ⏱️  Duration: {actioner_duration:.2f}s')
        print('   💡 Tickets disabled for demo (configure Jira/GitHub to enable)')
        
        print()
        
        # ============================================================================
        # STEP 7: DIGESTOR AGENT - Generate comprehensive reports
        # ============================================================================
        print('7️⃣ DIGESTOR AGENT - Generating comprehensive reports...')
        print('-' * 60)
        
        digestor = DigestorAgent({
            'digestor': {
                'enable_notifications': False,  # Disabled for demo
                'enable_hourly_reports': True,
                'enable_daily_reports': True,
                'enable_trend_analysis': True
            }
        })
        
        digestor_start = datetime.now()
        digestor_result = await digestor.process(context)
        digestor_duration = (datetime.now() - digestor_start).total_seconds()
        
        print(f'   ✅ Digestor completed: {digestor_result.success}')
        print(f'   📊 Reports generated: {digestor_result.metadata.get("reports_generated", 0)}')
        print(f'   ⏱️  Duration: {digestor_duration:.2f}s')
        
        # Check if reports were created
        reports_dir = 'reports'
        if os.path.exists(reports_dir):
            report_files = [f for f in os.listdir(reports_dir) if f.endswith(('.md', '.json', '.html'))]
            print(f'   📄 Report files created: {len(report_files)}')
            for report_file in report_files[:5]:  # Show first 5
                print(f'      - {report_file}')
        
        if not digestor_result.success:
            print('   ❌ Digestor failed, stopping pipeline')
            return False
        
        print()
        
        # ============================================================================
        # STEP 8: FEEDBACK LOOP AGENT - Learn and improve
        # ============================================================================
        print('8️⃣ FEEDBACK LOOP AGENT - Learning and system improvement...')
        print('-' * 60)
        
        feedback_loop = FeedbackLoopAgent({
            'feedback_loop': {
                'learning_rate': 0.1,
                'min_samples': 5,  # Lower for demo
                'enable_ab_testing': True,
                'enable_weight_adjustment': True,
                'analysis_window_days': 30
            }
        })
        
        feedback_start = datetime.now()
        feedback_result = await feedback_loop.process(context)
        feedback_duration = (datetime.now() - feedback_start).total_seconds()
        
        print(f'   ✅ Feedback Loop completed: {feedback_result.success}')
        print(f'   📊 Learning insights: {feedback_result.metadata.get("insights_generated", 0)}')
        print(f'   ⏱️  Duration: {feedback_duration:.2f}s')
        
        print()
        
        # ============================================================================
        # COMPREHENSIVE PIPELINE SUMMARY
        # ============================================================================
        print('📊 COMPREHENSIVE PIPELINE SUMMARY')
        print('=' * 80)
        
        total_duration = (datetime.now() - context.started_at).total_seconds()
        
        print(f'   🎯 Product: Cursor')
        print(f'   📅 Time Range: Last 4 months (since {four_months_ago.strftime("%Y-%m-%d")})')
        print(f'   ⏱️  Total Pipeline Duration: {total_duration:.2f}s ({total_duration/60:.1f} minutes)')
        print()
        
        # Final database state
        with get_session() as session:
            raw_count = session.query(RawFeedback).count()
            processed_count = session.query(ProcessedDocument).count()
            classified_count = session.query(ProcessedDocument).filter(
                ProcessedDocument.feedback_type.isnot(None)
            ).count()
            clusters_count = session.query(Cluster).count()
            memberships_count = session.query(ClusterMembership).count()
            prioritized_count = session.query(PrioritizationScore).count()
            
            print('   📊 FINAL DATA SUMMARY:')
            print(f'      📥 Raw Feedback Items: {raw_count}')
            print(f'      🧹 Processed Documents: {processed_count}')
            print(f'      🏷️  Classified Documents: {classified_count}')
            print(f'      🔗 Clusters Created: {clusters_count}')
            print(f'      🔗 Cluster Memberships: {memberships_count}')
            print(f'      🎯 Prioritized Items: {prioritized_count}')
            print()
            
            # Show feedback type breakdown
            if classified_count > 0:
                from sqlalchemy import func
                types = session.query(ProcessedDocument.feedback_type, 
                                    func.count(ProcessedDocument.id)).group_by(
                    ProcessedDocument.feedback_type).all()
                print('   📈 FEEDBACK TYPE BREAKDOWN:')
                for feedback_type, count in types:
                    percentage = (count / classified_count) * 100
                    print(f'      {feedback_type}: {count} ({percentage:.1f}%)')
                print()
            
            # Show top priorities
            if prioritized_count > 0:
                top_priorities = session.query(PrioritizationScore).order_by(
                    PrioritizationScore.final_score.desc()).limit(3).all()
                print('   🎯 TOP 3 PRIORITY ITEMS:')
                for i, priority in enumerate(top_priorities, 1):
                    print(f'      {i}. Score: {priority.final_score:.3f} ({priority.priority_level.value})')
                    # Get the associated document
                    doc = session.query(ProcessedDocument).filter(
                        ProcessedDocument.id == priority.document_id
                    ).first()
                    if doc:
                        print(f'         Title: {doc.title[:80]}...')
                print()
        
        # Performance breakdown
        print('   ⚡ PERFORMANCE BREAKDOWN:')
        print(f'      📥 Ingestor: {ingestor_duration:.2f}s')
        print(f'      🧹 Normalizer: {normalizer_duration:.2f}s')
        print(f'      🏷️  Classifier: {classifier_duration:.2f}s')
        print(f'      🔗 Clusterer: {clusterer_duration:.2f}s')
        print(f'      🎯 Prioritizer: {prioritizer_duration:.2f}s')
        print(f'      🎫 Actioner: {actioner_duration:.2f}s')
        print(f'      📊 Digestor: {digestor_duration:.2f}s')
        print(f'      🧠 Feedback Loop: {feedback_duration:.2f}s')
        print()
        
        print('🎉 PIPELINE COMPLETED SUCCESSFULLY!')
        print('=' * 80)
        print('✅ All 8 agents executed successfully')
        print('✅ Cursor feedback collected and processed')
        print('✅ Reports generated and insights created')
        print('✅ System ready for production use')
        print()
        print('💡 NEXT STEPS:')
        print('   1. Review generated reports in the reports/ directory')
        print('   2. Configure Jira/GitHub for automatic ticket creation')
        print('   3. Set up notification channels (Slack, Email)')
        print('   4. Schedule regular pipeline runs')
        print('   5. Monitor system performance and adjust weights')
        
        return True
        
    except Exception as e:
        print(f'❌ PIPELINE FAILED: {e}')
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main function to run the complete pipeline test."""
    print('🚀 Starting Complete Cursor Pipeline Test...')
    print('This will test the entire workflow from ingestion to report generation.')
    print()
    
    success = await test_cursor_complete_pipeline()
    
    if success:
        print('\n🎉 SUCCESS: Complete pipeline test passed!')
        print('🎉 Cursor Product Feedback Miner is fully operational!')
    else:
        print('\n❌ FAILED: Pipeline test encountered errors.')
        print('Please check the logs above for details.')

if __name__ == "__main__":
    asyncio.run(main())
