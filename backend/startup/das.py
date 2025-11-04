"""
DAS (Digital Assistant System) initialization module.
"""

import logging

logger = logging.getLogger(__name__)


async def initialize_das() -> None:
    """
    Initialize DAS engine.
    """
    print("🔥 Step 8: Initializing DAS...")
    logger.info("🤖 Initializing DAS...")
    
    from ..api.das import initialize_das_engine
    
    await initialize_das_engine()
    print("✅ DAS initialized")
