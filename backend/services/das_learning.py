"""
DAS Learning Implementation

Implements LearningInterface for learning from interactions and improving over time.
Stores interactions, processes feedback, and generates learning insights.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime, timedelta, timezone

from .learning_interface import (
    LearningInterface,
    InteractionRecord,
    InteractionType,
    FeedbackType,
    LearningInsight,
)
from .config import Settings
from .db import DatabaseService

logger = logging.getLogger(__name__)


class DASLearning(LearningInterface):
    """
    DAS learning system implementation.
    
    Records interactions, learns from feedback and corrections,
    and generates insights for improving DAS behavior.
    """
    
    def __init__(
        self,
        settings: Settings,
        db_service: Optional[DatabaseService] = None,
    ):
        """
        Initialize DAS learning system.
        
        Args:
            settings: Application settings
            db_service: Optional database service
        """
        self.settings = settings
        self.db_service = db_service or DatabaseService(settings)
    
    async def record_interaction(self, interaction: InteractionRecord) -> bool:
        """Record an interaction for learning."""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO das_interactions
                    (interaction_id, interaction_type, user_id, project_id,
                     query, response, context, feedback, correction, corrected_response,
                     metadata, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s::jsonb, %s)
                """, (
                    interaction.interaction_id,
                    interaction.interaction_type.value,
                    interaction.user_id,
                    interaction.project_id,
                    interaction.query,
                    interaction.response,
                    json.dumps(interaction.context),
                    interaction.feedback.value if interaction.feedback else None,
                    interaction.correction,
                    interaction.metadata.get("corrected_response") if interaction.metadata else None,
                    json.dumps(interaction.metadata),
                    interaction.timestamp,
                ))
                conn.commit()
            
            logger.debug(f"Recorded interaction {interaction.interaction_id}")
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to record interaction: {e}", exc_info=True)
            return False
        finally:
            self.db_service._return(conn)
    
    async def learn_from_feedback(
        self,
        interaction_id: str,
        feedback_type: FeedbackType,
        feedback_text: Optional[str] = None,
    ) -> bool:
        """Learn from user feedback."""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                # Update interaction with feedback
                cur.execute("""
                    UPDATE das_interactions
                    SET feedback = %s, metadata = metadata || %s::jsonb
                    WHERE interaction_id = %s
                """, (
                    feedback_type.value,
                    json.dumps({"feedback_text": feedback_text} if feedback_text else {}),
                    interaction_id,
                ))
                conn.commit()
                
                if cur.rowcount == 0:
                    logger.warning(f"Interaction {interaction_id} not found for feedback")
                    return False
                
                # Generate learning insights from feedback
                await self._generate_insights_from_feedback(interaction_id, feedback_type)
                
                return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to learn from feedback: {e}")
            return False
        finally:
            self.db_service._return(conn)
    
    async def learn_from_correction(
        self,
        interaction_id: str,
        correction: str,
        corrected_response: str,
    ) -> bool:
        """Learn from user correction."""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                # Update interaction with correction
                cur.execute("""
                    UPDATE das_interactions
                    SET correction = %s, corrected_response = %s,
                        feedback = 'correction', metadata = metadata || %s::jsonb
                    WHERE interaction_id = %s
                """, (
                    correction,
                    corrected_response,
                    json.dumps({"has_correction": True}),
                    interaction_id,
                ))
                conn.commit()
                
                if cur.rowcount == 0:
                    logger.warning(f"Interaction {interaction_id} not found for correction")
                    return False
                
                # Generate learning insights from correction
                await self._generate_insights_from_correction(interaction_id, correction, corrected_response)
                
                return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to learn from correction: {e}")
            return False
        finally:
            self.db_service._return(conn)
    
    async def get_improvements(
        self,
        persona_name: Optional[str] = None,
        domain: Optional[str] = None,
        limit: int = 10,
    ) -> List[LearningInsight]:
        """Get learning insights and improvements."""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                conditions = ["is_active = TRUE"]
                params = []
                
                if persona_name:
                    conditions.append("persona_name = %s")
                    params.append(persona_name)
                
                if domain:
                    conditions.append("domain = %s")
                    params.append(domain)
                
                where_clause = " AND ".join(conditions)
                
                cur.execute(f"""
                    SELECT 
                        insight_id, insight_type, description, confidence,
                        recommendations, persona_name, domain, source_interaction_ids,
                        metadata
                    FROM das_learning_insights
                    WHERE {where_clause}
                    ORDER BY confidence DESC, created_at DESC
                    LIMIT %s
                """, tuple(params + [limit]))
                
                rows = cur.fetchall()
                insights = []
                for row in rows:
                    insight_id, insight_type, description, confidence, \
                    recommendations, persona_name_val, domain_val, source_ids, metadata = row
                    
                    insights.append(LearningInsight(
                        insight_id=str(insight_id),
                        insight_type=insight_type,
                        description=description,
                        confidence=confidence or 0.5,
                        recommendations=recommendations or [],
                        metadata=metadata or {},
                    ))
                
                return insights
        except Exception as e:
            logger.error(f"Failed to get improvements: {e}")
            return []
        finally:
            self.db_service._return(conn)
    
    async def get_interaction_history(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        interaction_type: Optional[InteractionType] = None,
        limit: int = 50,
    ) -> List[InteractionRecord]:
        """Get interaction history for analysis."""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                conditions = []
                params = []
                
                if user_id:
                    conditions.append("user_id = %s")
                    params.append(user_id)
                
                if project_id:
                    conditions.append("project_id = %s")
                    params.append(project_id)
                
                if interaction_type:
                    conditions.append("interaction_type = %s")
                    params.append(interaction_type.value)
                
                where_clause = " AND ".join(conditions) if conditions else "TRUE"
                
                cur.execute(f"""
                    SELECT 
                        interaction_id, interaction_type, user_id, project_id,
                        query, response, context, feedback, correction, corrected_response,
                        metadata, created_at
                    FROM das_interactions
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT %s
                """, tuple(params + [limit]))
                
                rows = cur.fetchall()
                interactions = []
                for row in rows:
                    interaction_id, interaction_type_str, user_id_val, project_id_val, \
                    query, response, context_json, feedback_str, correction, corrected_response, \
                    metadata_json, created_at = row
                    
                    try:
                        interaction_type_enum = InteractionType(interaction_type_str)
                    except ValueError:
                        interaction_type_enum = InteractionType.QUERY
                    
                    feedback_enum = None
                    if feedback_str:
                        try:
                            feedback_enum = FeedbackType(feedback_str)
                        except ValueError:
                            pass
                    
                    interactions.append(InteractionRecord(
                        interaction_id=str(interaction_id),
                        interaction_type=interaction_type_enum,
                        user_id=user_id_val,
                        project_id=str(project_id_val) if project_id_val else None,
                        query=query,
                        response=response,
                        context=context_json or {},
                        feedback=feedback_enum,
                        correction=correction,
                        metadata=metadata_json or {},
                        timestamp=created_at,
                    ))
                
                return interactions
        except Exception as e:
            logger.error(f"Failed to get interaction history: {e}")
            return []
        finally:
            self.db_service._return(conn)
    
    async def analyze_patterns(
        self,
        domain: Optional[str] = None,
        time_period_days: int = 30,
    ) -> Dict[str, Any]:
        """Analyze patterns in interactions."""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=time_period_days)
                
                conditions = ["created_at >= %s"]
                params = [cutoff_date]
                
                if domain:
                    # Extract domain from context if available
                    conditions.append("context->>'domain' = %s")
                    params.append(domain)
                
                where_clause = " AND ".join(conditions)
                
                # Analyze feedback patterns
                cur.execute(f"""
                    SELECT 
                        feedback,
                        COUNT(*) as count,
                        COUNT(*) FILTER (WHERE feedback = 'positive') as positive_count,
                        COUNT(*) FILTER (WHERE feedback = 'negative') as negative_count,
                        COUNT(*) FILTER (WHERE feedback = 'correction') as correction_count
                    FROM das_interactions
                    WHERE {where_clause} AND feedback IS NOT NULL
                    GROUP BY feedback
                """, tuple(params))
                
                feedback_stats = {}
                for row in cur.fetchall():
                    feedback, count, positive, negative, correction = row
                    feedback_stats[feedback] = {
                        "total": count,
                        "positive": positive or 0,
                        "negative": negative or 0,
                        "correction": correction or 0,
                    }
                
                # Analyze interaction types
                cur.execute(f"""
                    SELECT interaction_type, COUNT(*) as count
                    FROM das_interactions
                    WHERE {where_clause}
                    GROUP BY interaction_type
                    ORDER BY count DESC
                """, tuple(params))
                
                type_stats = {}
                for row in cur.fetchall():
                    interaction_type, count = row
                    type_stats[interaction_type] = count
                
                return {
                    "time_period_days": time_period_days,
                    "domain": domain,
                    "feedback_patterns": feedback_stats,
                    "interaction_types": type_stats,
                    "total_interactions": sum(type_stats.values()),
                }
        except Exception as e:
            logger.error(f"Failed to analyze patterns: {e}")
            return {}
        finally:
            self.db_service._return(conn)
    
    async def apply_learning(
        self,
        insight_id: str,
        persona_name: Optional[str] = None,
    ) -> bool:
        """Apply a learning insight to improve behavior."""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                # Mark insight as applied
                cur.execute("""
                    UPDATE das_learning_insights
                    SET applied_at = NOW(), updated_at = NOW()
                    WHERE insight_id = %s
                """, (insight_id,))
                conn.commit()
                
                if cur.rowcount == 0:
                    logger.warning(f"Insight {insight_id} not found")
                    return False
                
                # TODO: Actually apply insight to persona/system
                # This would involve updating persona prompts, system configurations, etc.
                logger.info(f"Applied learning insight {insight_id}")
                
                return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to apply learning: {e}")
            return False
        finally:
            self.db_service._return(conn)
    
    async def _generate_insights_from_feedback(
        self,
        interaction_id: str,
        feedback_type: FeedbackType,
    ):
        """Generate learning insights from feedback."""
        # Simple insight generation - can be enhanced with ML/AI
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                # Get interaction context
                cur.execute("""
                    SELECT context, persona_name
                    FROM das_interactions
                    WHERE interaction_id = %s
                """, (interaction_id,))
                
                row = cur.fetchone()
                if not row:
                    return
                
                context, persona_name = row
                context_dict = context or {}
                persona_name = context_dict.get("persona_name") if isinstance(context_dict, dict) else None
                
                # Generate insight based on feedback type
                if feedback_type == FeedbackType.NEGATIVE:
                    insight_type = "improvement"
                    description = f"User provided negative feedback. Review response quality."
                    confidence = 0.7
                    recommendations = [
                        "Review similar queries for patterns",
                        "Consider adjusting persona prompts",
                        "Check if additional context is needed",
                    ]
                elif feedback_type == FeedbackType.POSITIVE:
                    insight_type = "pattern"
                    description = f"User provided positive feedback. Identify successful patterns."
                    confidence = 0.6
                    recommendations = [
                        "Identify what made this response successful",
                        "Consider applying similar approach to other queries",
                    ]
                else:
                    return  # Don't generate insights for other feedback types yet
                
                # Store insight
                import uuid
                insight_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO das_learning_insights
                    (insight_id, insight_type, description, confidence, recommendations,
                     persona_name, source_interaction_ids, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                """, (
                    insight_id,
                    insight_type,
                    description,
                    confidence,
                    recommendations,
                    persona_name,
                    [interaction_id],
                ))
                conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to generate insights from feedback: {e}")
        finally:
            self.db_service._return(conn)
    
    async def _generate_insights_from_correction(
        self,
        interaction_id: str,
        correction: str,
        corrected_response: str,
    ):
        """Generate learning insights from correction."""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                # Get interaction context
                cur.execute("""
                    SELECT context, persona_name
                    FROM das_interactions
                    WHERE interaction_id = %s
                """, (interaction_id,))
                
                row = cur.fetchone()
                if not row:
                    return
                
                context, persona_name = row
                context_dict = context or {}
                persona_name = context_dict.get("persona_name") if isinstance(context_dict, dict) else None
                
                # Generate correction insight
                insight_type = "correction"
                description = f"User provided correction: {correction[:100]}..."
                confidence = 0.9  # High confidence for explicit corrections
                recommendations = [
                    "Update knowledge base with corrected information",
                    "Review similar responses for similar errors",
                    "Consider updating persona prompts to avoid this error",
                ]
                
                # Store insight
                import uuid
                insight_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO das_learning_insights
                    (insight_id, insight_type, description, confidence, recommendations,
                     persona_name, source_interaction_ids, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                """, (
                    insight_id,
                    insight_type,
                    description,
                    confidence,
                    recommendations,
                    persona_name,
                    [interaction_id],
                ))
                conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to generate insights from correction: {e}")
        finally:
            self.db_service._return(conn)
