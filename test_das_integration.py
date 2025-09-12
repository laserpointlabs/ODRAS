#!/usr/bin/env python3
"""
Test script for DAS integration

This script tests the basic DAS functionality to ensure everything is working correctly.
"""

import asyncio
import sys
import os
import logging

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.services.config import Settings
from backend.services.rag_service import RAGService
from backend.services.das_core_engine import DASCoreEngine
from backend.services.db import DatabaseService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_das_integration():
    """Test basic DAS functionality"""
    try:
        logger.info("Starting DAS integration test...")
        
        # Initialize services
        settings = Settings()
        db_service = DatabaseService(settings)
        rag_service = RAGService(settings)
        
        # Initialize DAS engine
        das_engine = DASCoreEngine(settings, rag_service, db_service)
        await das_engine.initialize()
        
        logger.info("✅ DAS engine initialized successfully")
        
        # Test session creation
        test_user_id = "test_user_123"
        session = await das_engine.start_session(test_user_id, "test_project")
        
        logger.info(f"✅ DAS session created: {session.session_id}")
        
        # Test message processing
        test_messages = [
            "How do I create a new ontology?",
            "What is the ODRAS system?",
            "How do I upload a document?",
            "Show me available commands"
        ]
        
        for message in test_messages:
            logger.info(f"Testing message: '{message}'")
            response = await das_engine.process_message(session.session_id, message, test_user_id)
            
            logger.info(f"✅ Response: {response.message[:100]}...")
            logger.info(f"   Intent: {response.intent.value}")
            logger.info(f"   Confidence: {response.confidence.value}")
            
            if response.suggestions:
                logger.info(f"   Suggestions: {len(response.suggestions)} available")
        
        # Test session cleanup
        await das_engine.end_session(session.session_id)
        logger.info("✅ DAS session ended successfully")
        
        logger.info("🎉 All DAS integration tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ DAS integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    success = await test_das_integration()
    if success:
        print("\n🎉 DAS integration test completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ DAS integration test failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
