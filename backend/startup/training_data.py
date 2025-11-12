"""
DAS Training Data initialization module.

Automatically loads base training knowledge on system startup.
"""

import logging
import asyncio
from pathlib import Path
from typing import Optional

from ..services.config import Settings
from ..services.db import DatabaseService

logger = logging.getLogger(__name__)


async def initialize_training_data(settings: Settings, db: DatabaseService) -> None:
    """
    Initialize base DAS training data on startup.
    
    This function:
    1. Checks if base training collections exist
    2. Checks if base training data is already loaded
    3. Loads base training data if missing (idempotent)
    
    Args:
        settings: Application settings
        db: Database service instance
    """
    print("🔥 Step 7: Initializing DAS training data...")
    logger.info("📚 Initializing DAS training data...")
    
    try:
        # Check if we should auto-load training data
        auto_load = getattr(settings, 'auto_load_training_data', 'true').lower() == 'true'
        if not auto_load:
            logger.info("Auto-load training data disabled, skipping")
            print("ℹ️  Auto-load training data disabled")
            return
        
        # Check if base training data already exists
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                # Check if we have completed assets in any training collection
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM das_training_assets 
                    WHERE processing_status = 'completed' AND chunk_count > 0
                """)
                existing_count = cur.fetchone()[0]
                
                if existing_count > 0:
                    logger.info(f"Base training data already exists ({existing_count} completed assets)")
                    print(f"✅ Base training data already loaded ({existing_count} assets)")
                    return
        finally:
            db._return(conn)
        
        # Load base training data using the setup function
        logger.info("Loading base training data...")
        print("  Loading base training data...")
        
        # Run the setup (it's idempotent, so safe to call)
        result = await setup_base_training_data(settings, db)
        
        if result.get("success"):
            loaded_count = result.get("loaded_count", 0)
            logger.info(f"Successfully loaded {loaded_count} training assets")
            print(f"✅ Loaded {loaded_count} base training assets")
        else:
            error = result.get("error", "Unknown error")
            logger.warning(f"Failed to load base training data: {error}")
            print(f"⚠️  Failed to load base training data: {error}")
            # Don't fail startup if training data loading fails
        
    except Exception as e:
        logger.error(f"Failed to initialize training data: {e}")
        print(f"⚠️  Training data initialization failed: {e}")
        # Don't fail startup if training data loading fails
        import traceback
        logger.debug(f"Training data initialization traceback: {traceback.format_exc()}")


async def setup_base_training_data(settings: Settings, db: DatabaseService) -> dict:
    """
    Setup base training data programmatically using services directly.
    
    Args:
        settings: Application settings
        db: Database service instance
    
    Returns:
        Dict with success status and loaded count
    """
    try:
        from ..services.das_training_processor import DASTrainingProcessor
        from ..services.file_storage import get_file_storage_service
        
        # Calculate test data directory path (works from both repo root and backend/startup/)
        # Path from backend/startup/training_data.py -> backend -> repo root -> tests/test_data/das_training
        current_file = Path(__file__).resolve()
        repo_root = current_file.parent.parent.parent
        test_data_dir = repo_root / "tests" / "test_data" / "das_training"
        
        # Also try alternative path in case we're running from different location
        if not test_data_dir.exists():
            # Try from workspace root
            alt_path = Path("tests/test_data/das_training")
            if alt_path.exists():
                test_data_dir = alt_path
            else:
                logger.warning(f"Test data directory not found at {test_data_dir} or {alt_path}")
                return {"success": False, "error": f"Test data directory not found: {test_data_dir}"}
        
        # Training data mapping
        training_data = [
            ("ontology_basics.txt", "Ontology", "ontology"),
            ("requirements_writing.txt", "Requirements", "requirements"),
            ("systems_engineering.txt", "Systems Engineering", "systems_engineering"),
            ("odras_usage.txt", "Odras Usage", "odras_usage"),
            ("acquisition_basics.txt", "Acquisition", "acquisition"),
        ]
        
        processor = DASTrainingProcessor(settings)
        file_storage = get_file_storage_service()
        loaded_count = 0
        
        # Get admin user ID
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM public.users WHERE username = 'admin' LIMIT 1")
                admin_row = cur.fetchone()
                admin_user_id = str(admin_row[0]) if admin_row else None
        finally:
            db._return(conn)
        
        if not admin_user_id:
            return {"success": False, "error": "Admin user not found"}
        
        for filename, display_name, domain in training_data:
            file_path = test_data_dir / filename
            if not file_path.exists():
                logger.warning(f"Training file not found: {file_path}")
                continue
            
            # Get collection ID for this domain
            conn = db._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT collection_id FROM das_training_collections WHERE domain = %s LIMIT 1",
                        (domain,)
                    )
                    collection_row = cur.fetchone()
                    if not collection_row:
                        logger.warning(f"Collection not found for domain: {domain}")
                        continue
                    collection_id = str(collection_row[0])
                    
                    # Check if asset already exists
                    title = file_path.stem.replace("_", " ").title()
                    cur.execute(
                        """
                        SELECT asset_id FROM das_training_assets 
                        WHERE collection_id = %s AND title = %s AND processing_status = 'completed'
                        LIMIT 1
                        """,
                        (collection_id, title)
                    )
                    if cur.fetchone():
                        continue  # Already loaded
            finally:
                db._return(conn)
            
            # Read file content
            with open(file_path, "rb") as f:
                file_content = f.read()
            
            # Store file
            storage_result = await file_storage.store_file(
                content=file_content,
                filename=filename,
                content_type="text/plain",
                project_id=None,  # Global training data, no project
                tags={"training": "true", "domain": domain},
            )
            
            if not storage_result.get("success"):
                logger.warning(f"Failed to store file {filename}: {storage_result.get('error')}")
                continue
            
            file_id = storage_result["file_id"]
            
            # Process training file
            try:
                result = await processor.process_training_file(
                    file_id=file_id,
                    collection_id=collection_id,
                    title=title,
                    description=f"Base training document for {domain}",
                    source_type="text",
                    user_id=admin_user_id,
                )
                
                if result.get("success"):
                    loaded_count += 1
                    logger.info(f"Loaded training asset: {title}")
            except Exception as e:
                logger.warning(f"Failed to process training file {filename}: {e}")
                continue
        
        return {"success": True, "loaded_count": loaded_count}
        
    except Exception as e:
        logger.error(f"Failed to setup base training data: {e}")
        import traceback
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return {"success": False, "error": str(e)}
