"""
DAS Integration Service
Handles communication with DAS for configuration generation
"""

import json
import uuid
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from backend.services.config import Settings
from backend.services.db import DatabaseService
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

# Shared database service instance to prevent multiple connection pools
_db_service_instance = None

def get_db_service():
    """Get shared database service instance (connection pool)"""
    global _db_service_instance
    if _db_service_instance is None:
        settings = Settings()
        _db_service_instance = DatabaseService(settings)
        logger.info("DAS Integration: Using shared connection pool")
    return _db_service_instance

class DASIntegration:
    """
    Handles DAS communication for configuration generation
    """
    
    def __init__(self):
        pass
    
    async def start_batch_generation(
        self,
        project_id: str,
        requirement_ids: Optional[List[str]] = None,
        das_options: Dict[str, Any] = None,
        filters: Dict[str, Any] = None,
        user_id: str = None
    ) -> str:
        """
        Start batch generation process for configurations
        """
        try:
            job_id = str(uuid.uuid4())
            
            # Store job in database using connection pool
            db_service = get_db_service()
            conn = db_service._conn()
            try:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO das_generation_jobs (
                        job_id, project_id, user_id, status, 
                        requirement_ids, das_options, filters,
                        created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    job_id, project_id, user_id, "started",
                    json.dumps(requirement_ids) if requirement_ids else None,
                    json.dumps(das_options) if das_options else None,
                    json.dumps(filters) if filters else None,
                    datetime.now(timezone.utc), datetime.now(timezone.utc)
                ))
                
                conn.commit()
                logger.info(f"✅ DAS Integration: Job {job_id} stored using connection pool")
                
            finally:
                db_service._return(conn)
            
            # Start background task
            asyncio.create_task(self._process_batch_generation(job_id, project_id, requirement_ids, das_options))
            
            logger.info(f"✅ Started DAS batch generation job: {job_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"❌ Error starting batch generation: {e}")
            raise e
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get status of DAS generation job
        """
        try:
            db_service = get_db_service()
            conn = db_service._conn()
            try:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                cursor.execute("""
                    SELECT * FROM das_generation_jobs 
                    WHERE job_id = %s
                """, (job_id,))
                
                job = cursor.fetchone()
                
                if not job:
                    raise ValueError(f"Job {job_id} not found")
                
                # Parse JSON fields
                if job["requirement_ids"]:
                    job["requirement_ids"] = json.loads(job["requirement_ids"])
                if job["das_options"]:
                    job["das_options"] = json.loads(job["das_options"])
                if job["filters"]:
                    job["filters"] = json.loads(job["filters"])
                if job["results"]:
                    job["results"] = json.loads(job["results"])
                if job["errors"]:
                    job["errors"] = json.loads(job["errors"])
                
                return job
                
            finally:
                db_service._return(conn)
                
        except Exception as e:
            logger.error(f"❌ Error getting job status: {e}")
            raise e
    
    async def _process_batch_generation(
        self,
        job_id: str,
        project_id: str,
        requirement_ids: Optional[List[str]],
        das_options: Dict[str, Any]
    ):
        """
        Background task to process batch generation
        """
        try:
            # Update job status
            await self._update_job_status(job_id, "processing")
            
            # Get requirements to process
            requirements = await self._get_requirements_to_process(project_id, requirement_ids)
            
            configurations = []
            errors = []
            
            for req in requirements:
                try:
                    # Generate configuration for this requirement
                    config = await self._generate_configuration_for_requirement(req, das_options)
                    configurations.append(config)
                    
                    # Update progress
                    progress = len(configurations) / len(requirements) * 100
                    await self._update_job_progress(job_id, progress)
                    
                except Exception as e:
                    logger.error(f"❌ Error generating configuration for requirement {req.get('id')}: {e}")
                    errors.append({
                        "requirement_id": req.get("id"),
                        "error": str(e)
                    })
            
            # Update final results
            await self._update_job_results(job_id, "completed", configurations, errors)
            
            logger.info(f"✅ Batch generation completed: {len(configurations)} configs, {len(errors)} errors")
            
        except Exception as e:
            logger.error(f"❌ Error in batch generation: {e}")
            await self._update_job_status(job_id, "failed", str(e))
    
    async def _generate_configuration_for_requirement(
        self, 
        requirement: Dict[str, Any], 
        das_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate configuration for a single requirement using DAS
        
        For now, this is a mock implementation that generates a simple configuration.
        In the future, this would make actual API calls to DAS.
        """
        try:
            req_name = requirement.get("name", "Unknown Requirement")
            req_id = requirement.get("id", str(uuid.uuid4()))
            
            # Mock DAS response - in reality, this would be an API call
            config = {
                "config_id": str(uuid.uuid4()),
                "name": f"DAS Generated: {req_name}",
                "ontology_graph": requirement.get("ontology_graph", ""),
                "source_requirement": req_id,
                "das_metadata": {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "das_version": "2.0-mock",
                    "confidence": 0.85,
                    "rationale": f"Generated configuration for requirement: {req_name}"
                },
                "structure": {
                    "class": "Requirement",
                    "instanceId": req_id,
                    "properties": {
                        "name": req_name,
                        "description": requirement.get("description", "")
                    },
                    "relationships": [
                        {
                            "property": "has_constraint",
                            "multiplicity": "0..*",
                            "targets": [
                                {
                                    "class": "Constraint",
                                    "instanceId": f"const-{req_id}",
                                    "properties": {
                                        "name": "Performance Constraint",
                                        "type": "performance",
                                        "dasRationale": "Standard performance constraint for system requirements"
                                    }
                                }
                            ]
                        },
                        {
                            "property": "specifies",
                            "multiplicity": "1..*",
                            "targets": [
                                {
                                    "class": "Component",
                                    "instanceId": f"comp-{req_id}",
                                    "properties": {
                                        "name": f"Processing Engine for {req_name}",
                                        "dasRationale": "Primary processing component for this requirement"
                                    },
                                    "relationships": [
                                        {
                                            "property": "presents",
                                            "multiplicity": "1..*",
                                            "targets": [
                                                {
                                                    "class": "Interface",
                                                    "instanceId": f"intf-{req_id}",
                                                    "properties": {
                                                        "name": "API Interface",
                                                        "dasRationale": "Standard API interface"
                                                    }
                                                }
                                            ]
                                        },
                                        {
                                            "property": "performs",
                                            "multiplicity": "1..0",
                                            "targets": [
                                                {
                                                    "class": "Process",
                                                    "instanceId": f"proc-{req_id}",
                                                    "properties": {
                                                        "name": "Data Processing",
                                                        "dasRationale": "Core processing logic"
                                                    },
                                                    "relationships": [
                                                        {
                                                            "property": "realizes",
                                                            "multiplicity": "1..0",
                                                            "targets": [
                                                                {
                                                                    "class": "Function",
                                                                    "instanceId": f"func-{req_id}",
                                                                    "properties": {
                                                                        "name": "Process Data",
                                                                        "dasRationale": "Data processing function"
                                                                    },
                                                                    "relationships": [
                                                                        {
                                                                            "property": "specifically_depends_upon",
                                                                            "multiplicity": "1..0",
                                                                            "targets": [
                                                                                {"componentRef": f"comp-{req_id}"}
                                                                            ]
                                                                        }
                                                                    ]
                                                                }
                                                            ]
                                                        }
                                                    ]
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            }
            
            # Add some randomness to confidence and structure
            import random
            config["das_metadata"]["confidence"] = round(0.7 + random.random() * 0.25, 2)
            
            return config
            
        except Exception as e:
            logger.error(f"❌ Error generating configuration: {e}")
            raise e
    
    async def _get_requirements_to_process(
        self, 
        project_id: str, 
        requirement_ids: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """
        Get requirements that need configuration generation
        """
        try:
            db_service = get_db_service()
            conn = db_service._conn()
            try:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                if requirement_ids:
                    # Specific requirements
                    placeholders = ','.join(['%s'] * len(requirement_ids))
                    query = f"""
                        SELECT instance_id as id, instance_name as name, properties 
                        FROM individual_instances ii
                        JOIN individual_tables_config itc ON ii.table_id = itc.table_id
                        WHERE itc.project_id = %s AND ii.class_name = 'Requirement'
                        AND ii.instance_id IN ({placeholders})
                    """
                    cursor.execute(query, [project_id] + requirement_ids)
                else:
                    # All requirements
                    cursor.execute("""
                        SELECT instance_id as id, instance_name as name, properties 
                        FROM individual_instances ii
                        JOIN individual_tables_config itc ON ii.table_id = itc.table_id
                        WHERE itc.project_id = %s AND ii.class_name = 'Requirement'
                    """, (project_id,))
                
                requirements = cursor.fetchall()
                
                # Parse properties JSON
                for req in requirements:
                    if req["properties"]:
                        try:
                            req["properties"] = json.loads(req["properties"])
                        except:
                            req["properties"] = {}
                
                return requirements
                
            finally:
                db_service._return(conn)
                
        except Exception as e:
            logger.error(f"❌ Error getting requirements: {e}")
            return []
    
    async def _update_job_status(self, job_id: str, status: str, error: str = None):
        """Update job status"""
        try:
            db_service = get_db_service()
            conn = db_service._conn()
            try:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE das_generation_jobs 
                    SET status = %s, error_message = %s, updated_at = %s
                    WHERE job_id = %s
                """, (status, error, datetime.now(timezone.utc), job_id))
                
                conn.commit()
                logger.debug(f"✅ DAS Integration: Job {job_id} status updated to {status}")
                
            finally:
                db_service._return(conn)
                
        except Exception as e:
            logger.error(f"❌ Error updating job status: {e}")
    
    async def _update_job_progress(self, job_id: str, progress: float):
        """Update job progress"""
        try:
            db_service = get_db_service()
            conn = db_service._conn()
            try:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE das_generation_jobs 
                    SET progress = %s, updated_at = %s
                    WHERE job_id = %s
                """, (progress, datetime.now(timezone.utc), job_id))
                
                conn.commit()
                logger.debug(f"✅ DAS Integration: Job {job_id} progress updated to {progress:.1f}%")
                
            finally:
                db_service._return(conn)
                
        except Exception as e:
            logger.error(f"❌ Error updating job progress: {e}")
    
    async def _update_job_results(
        self, 
        job_id: str, 
        status: str, 
        configurations: List[Dict[str, Any]], 
        errors: List[Dict[str, Any]]
    ):
        """Update job with final results"""
        try:
            db_service = get_db_service()
            conn = db_service._conn()
            try:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE das_generation_jobs 
                    SET status = %s, progress = 100, results = %s, errors = %s, 
                        configurations_generated = %s, updated_at = %s
                    WHERE job_id = %s
                """, (
                    status, 
                    json.dumps(configurations),
                    json.dumps(errors) if errors else None,
                    len(configurations),
                    datetime.now(timezone.utc), 
                    job_id
                ))
                
                conn.commit()
                logger.debug(f"✅ DAS Integration: Job {job_id} results updated - {len(configurations)} configs")
                
            finally:
                db_service._return(conn)
                
        except Exception as e:
            logger.error(f"❌ Error updating job results: {e}")
