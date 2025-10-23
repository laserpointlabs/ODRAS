#!/usr/bin/env python3
"""
Migration script to extract and store dependencies for existing microtheories.

This script:
1. Queries database for all existing microtheories
2. Extracts dependencies from each MT's triples in Fuseki
3. Stores dependencies in mt_ontology_dependencies table

Run this after deploying Phase 1 to populate dependencies for existing MTs.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.config import Settings
from backend.services.db import DatabaseService
from backend.services.cqmt_dependency_tracker import CQMTDependencyTracker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Migrate existing MTs to have dependency records."""
    logger.info("=" * 70)
    logger.info("MT Dependency Migration Script")
    logger.info("=" * 70)
    
    try:
        # Initialize services
        settings = Settings()
        db = DatabaseService(settings)
        tracker = CQMTDependencyTracker(db, settings.fuseki_url)
        
        # Get all microtheories
        logger.info("Fetching all microtheories from database...")
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, iri, label, project_id
                    FROM microtheories
                    ORDER BY created_at DESC
                """)
                mts = cur.fetchall()
        finally:
            db._return(conn)
        
        logger.info(f"Found {len(mts)} microtheories to process")
        
        if not mts:
            logger.info("No microtheories found. Nothing to migrate.")
            return
        
        # Process each MT
        successful = 0
        failed = 0
        skipped = 0
        
        for mt_id, mt_iri, mt_label, project_id in mts:
            logger.info(f"\nProcessing MT: {mt_label} ({mt_id})")
            logger.info(f"  IRI: {mt_iri}")
            
            try:
                # Extract dependencies
                dependencies = tracker.extract_dependencies(mt_iri)
                
                if not dependencies:
                    logger.info(f"  No dependencies found - skipping")
                    skipped += 1
                    continue
                
                logger.info(f"  Found {len(dependencies)} dependencies")
                
                # Store dependencies
                tracker.store_dependencies(mt_id, dependencies)
                
                # Count by type
                type_counts = {}
                for dep in dependencies:
                    type_counts[dep.element_type] = type_counts.get(dep.element_type, 0) + 1
                
                logger.info(f"  Stored: {type_counts}")
                successful += 1
                
            except Exception as e:
                logger.error(f"  Error processing MT {mt_id}: {e}")
                failed += 1
        
        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("Migration Summary")
        logger.info("=" * 70)
        logger.info(f"Total MTs: {len(mts)}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Skipped (no dependencies): {skipped}")
        logger.info("=" * 70)
        
        if failed > 0:
            logger.warning(f"⚠️  {failed} MTs failed to migrate")
            return 1
        
        logger.info("✅ Migration completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
