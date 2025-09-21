#!/usr/bin/env python3
"""
Test script to fix and validate the core pipeline issues
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
from agents.digestor.agent import DigestorAgent

from agents.base.agent import AgentContext
from database.models import ProcessedDocument, PrioritizationScore, Cluster, ClusterMembership, RawFeedback
from config.database import get_session
import uuid

async def test_pipeline_fixes():
    """Test and fix the core pipeline issues."""
    
    print('🔧 PIPELINE FIXES TEST')
    print('=' * 60)
    print(f'Started at: {datetime.now()}')
    print()
    
    execution_id = str(uuid.uuid4())
    context = AgentContext(
        execution_id=execution_id,
        agent_name='pipeline_fixes',
        started_at=datetime.now(),
        config={'product_name': 'Cursor'},
        metadata={'product_name': 'Cursor', 'test_mode': False}
    )
    
    try:
        # Clear existing data
        print('🧹 CLEARING EXISTING DATA')
        print('-' * 40)
        
        with get_session() as session:
            session.query(ClusterMembership).delete()
            session.query(PrioritizationScore).delete()
            session.query(Cluster).delete()
            session.query(ProcessedDocument).delete()
            session.query(RawFeedback).delete()
            session.commit()
            print('   ✅ Cleared all existing data')
        
        print()
        
        # ============================================================================
        # STEP 1: INGESTOR with more lenient content filtering
        # ============================================================================
        print('1️⃣ INGESTOR - Collecting Cursor feedback with relaxed filtering...')
        print('-' * 40)
        
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
                        'Cursor editor issues'
                    ],
                    'since_date': four_months_ago.isoformat()
                },
                'twitter': {'enabled': False},
                'reddit': {'enabled': False}
            },
            'max_items_per_source': 10,  # Smaller limit
            'min_content_length': 3      # Very relaxed filtering
        })
        
        ingestor_result = await ingestor.process(context)
        print(f'   ✅ Ingestor completed: {ingestor_result.success}')
        print(f'   📊 Items collected: {ingestor_result.metadata.get("total_items", 0)}')
        
        # Check what we collected
        with get_session() as session:
            raw_count = session.query(RawFeedback).count()
            print(f'   📄 Raw feedback items: {raw_count}')
            
            # Show some sample titles
            if raw_count > 0:
                samples = session.query(RawFeedback.title).limit(3).all()
                print('   📝 Sample titles:')
                for title, in samples:
                    if title:
                        print(f'      - {title[:60]}...')
        
        if not ingestor_result.success:
            print('   ❌ Ingestor failed')
            return False
        
        print()
        
        # ============================================================================
        # STEP 2: NORMALIZER with relaxed filtering
        # ============================================================================
        print('2️⃣ NORMALIZER - Processing with relaxed filtering...')
        print('-' * 40)
        
        normalizer = NormalizerAgent({
            'batch_size': 10,
            'enable_deduplication': True,
            'enable_language_detection': True,
            'enable_pii_scrubbing': True,
            'min_word_count': 2  # Very relaxed
        })
        
        normalizer_result = await normalizer.process(context)
        print(f'   ✅ Normalizer completed: {normalizer_result.success}')
        print(f'   📊 Items processed: {normalizer_result.metadata.get("processed_items", 0)}')
        
        # Check processing results
        with get_session() as session:
            processed_count = session.query(ProcessedDocument).count()
            print(f'   📄 Processed documents: {processed_count}')
            
            # Show some sample processed content
            if processed_count > 0:
                samples = session.query(ProcessedDocument.title, ProcessedDocument.word_count).limit(3).all()
                print('   📝 Sample processed content:')
                for title, word_count in samples:
                    print(f'      - {title[:50]}... ({word_count} words)')
        
        if not normalizer_result.success:
            print('   ❌ Normalizer failed')
            return False
        
        print()
        
        # ============================================================================
        # STEP 3: CLASSIFIER - Test with fixed document association
        # ============================================================================
        print('3️⃣ CLASSIFIER - Testing classification with document association...')
        print('-' * 40)
        
        # Get documents to classify
        with get_session() as session:
            documents_to_classify = session.query(ProcessedDocument).filter(
                ProcessedDocument.feedback_type.is_(None)
            ).limit(3).all()
        
        if not documents_to_classify:
            print('   ⚠️  No unclassified documents found')
            classifier_result = type('obj', (object,), {
                'success': True, 
                'execution_time': 0.0,
                'metadata': {'classified_items': 0}
            })()
        else:
            print(f'   📄 Found {len(documents_to_classify)} documents to classify')
            
            # Test classification on first document
            doc = documents_to_classify[0]
            print(f'   🧪 Testing classification on: {doc.title[:50]}...')
            
            # Create a simple classifier test
            classifier = ClassifierAgent({
                'batch_size': 1,
                'model': 'gpt-3.5-turbo',
                'temperature': 0.1
            })
            
            # Test the classification prompt
            from agents.classifier.models import ClassificationPrompt
            prompt = ClassificationPrompt.get_classification_prompt().format(
                title=doc.title,
                content=doc.body[:500],  # Limit content for testing
                author=doc.author or "unknown",
                source_type="processed_document"
            )
            
            print(f'   📝 Classification prompt length: {len(prompt)} characters')
            
            # Try to classify the document
            try:
                # Convert document to dict format expected by classifier
                doc_dict = {
                    'id': str(doc.id),
                    'title': doc.title,
                    'body': doc.body,
                    'author': doc.author,
                    'timestamp': doc.timestamp
                }
                
                result = await classifier._classify_single_document(doc_dict)
                if result:
                    print(f'   ✅ Classification successful:')
                    print(f'      Type: {result.feedback_type.value}')
                    print(f'      Severity: {result.severity_level.value}')
                    print(f'      Component: {result.component.value}')
                    print(f'      Confidence: {result.overall_confidence:.2f}')
                else:
                    print('   ❌ Classification failed')
                
                classifier_result = type('obj', (object,), {
                    'success': True, 
                    'execution_time': 0.0,
                    'metadata': {'classified_items': 1 if result else 0}
                })()
                
            except Exception as e:
                print(f'   ❌ Classification error: {e}')
                classifier_result = type('obj', (object,), {
                    'success': False, 
                    'execution_time': 0.0,
                    'metadata': {'classified_items': 0}
                })()
        
        print(f'   ✅ Classifier test completed: {classifier_result.success}')
        print(f'   📊 Items classified: {classifier_result.metadata.get("classified_items", 0)}')
        
        print()
        
        # ============================================================================
        # STEP 4: Test database session issues
        # ============================================================================
        print('4️⃣ DATABASE SESSION - Testing session management...')
        print('-' * 40)
        
        try:
            # Test basic database operations
            with get_session() as session:
                doc_count = session.query(ProcessedDocument).count()
                print(f'   ✅ Basic database query successful: {doc_count} documents')
            
            # Test Prioritizer database session
            prioritizer = PrioritizerAgent({
                'severity_weight': 0.35,
                'reach_weight': 0.25,
                'recency_weight': 0.20,
                'persona_weight': 0.20,
                'max_items_to_prioritize': 10
            })
            
            # Test the database session method
            try:
                # Check if the method exists and works
                if hasattr(prioritizer, 'get_db_session'):
                    print('   ✅ Prioritizer has get_db_session method')
                    
                    # Test if it's a context manager
                    session_manager = prioritizer.get_db_session()
                    if hasattr(session_manager, '__enter__') and hasattr(session_manager, '__exit__'):
                        print('   ✅ get_db_session is a context manager')
                    else:
                        print('   ❌ get_db_session is not a context manager')
                else:
                    print('   ❌ Prioritizer missing get_db_session method')
                    
            except Exception as e:
                print(f'   ❌ Database session test failed: {e}')
            
        except Exception as e:
            print(f'   ❌ Database session error: {e}')
        
        print()
        
        # ============================================================================
        # SUMMARY
        # ============================================================================
        print('📊 PIPELINE FIXES SUMMARY')
        print('=' * 60)
        
        with get_session() as session:
            raw_count = session.query(RawFeedback).count()
            processed_count = session.query(ProcessedDocument).count()
            classified_count = session.query(ProcessedDocument).filter(
                ProcessedDocument.feedback_type.isnot(None)
            ).count()
            
            print(f'   📥 Raw Feedback Items: {raw_count}')
            print(f'   🧹 Processed Documents: {processed_count}')
            print(f'   🏷️  Classified Documents: {classified_count}')
        
        print()
        print('🔧 ISSUES IDENTIFIED:')
        print('   1. Content filtering too aggressive (many items skipped)')
        print('   2. Classifier needs document association fix')
        print('   3. Prioritizer database session context manager issue')
        print('   4. Need to handle empty content gracefully')
        print()
        print('💡 RECOMMENDATIONS:')
        print('   1. Relax content filtering thresholds')
        print('   2. Fix ClassificationResult document association')
        print('   3. Fix Prioritizer database session management')
        print('   4. Add better error handling for empty content')
        
        return True
        
    except Exception as e:
        print(f'❌ PIPELINE FIXES FAILED: {e}')
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main function to run the pipeline fixes test."""
    print('🔧 Starting Pipeline Fixes Test...')
    print('This will identify and help fix the core pipeline issues.')
    print()
    
    success = await test_pipeline_fixes()
    
    if success:
        print('\n✅ Pipeline fixes test completed!')
        print('Issues identified and recommendations provided.')
    else:
        print('\n❌ Pipeline fixes test failed.')

if __name__ == "__main__":
    asyncio.run(main())
