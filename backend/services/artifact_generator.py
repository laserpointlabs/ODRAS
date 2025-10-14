"""
DAS Artifact Generator Service
Generates various artifacts from DAS conversations using OpenAI
"""

import json
import logging
from typing import Any, Dict, List, Optional
import httpx

from .config import Settings

logger = logging.getLogger(__name__)


class ArtifactGenerator:
    """Generate artifacts from DAS conversations using OpenAI"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.openai_key = settings.openai_api_key
        self.model = "gpt-4o-mini"  # Fast and cost-effective
        
    def _format_conversation(self, messages: List[Dict]) -> str:
        """Format conversation history for LLM prompts"""
        formatted = []
        for msg in messages:
            # Handle SQL-first format (user_message/das_response)
            if "user_message" in msg or "das_response" in msg:
                user_msg = msg.get("user_message", "").strip()
                das_msg = msg.get("das_response", "").strip()
                
                if user_msg:
                    # Truncate extremely long messages (like requirement analysis prompts)
                    if len(user_msg) > 500:
                        user_msg = user_msg[:500] + "... [truncated]"
                    formatted.append(f"User: {user_msg}")
                
                if das_msg:
                    if len(das_msg) > 500:
                        das_msg = das_msg[:500] + "... [truncated]"
                    formatted.append(f"DAS: {das_msg}")
                
                if user_msg or das_msg:
                    formatted.append("")  # Empty line between conversations
            else:
                # Handle standard format (role/content)
                role = msg.get("role", "user")
                content = msg.get("content", "").strip()
                
                if content:
                    if len(content) > 500:
                        content = content[:500] + "... [truncated]"
                    
                    if role == "user":
                        formatted.append(f"User: {content}")
                    elif role == "assistant":
                        formatted.append(f"DAS: {content}")
                    else:
                        formatted.append(f"{role}: {content}")
                    formatted.append("")
        
        return "\n".join(formatted)
    
    async def _call_openai(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7
    ) -> str:
        """
        Call OpenAI API to generate content
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Generated text content
        """
        try:
            if not self.openai_key:
                logger.error("OpenAI API key not configured")
                return "Error: OpenAI API key not configured"
            
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.append({"role": "user", "content": prompt})
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                    return f"Error calling OpenAI API: {response.status_code}"
                
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return content.strip()
                
        except Exception as e:
            logger.error(f"Error calling OpenAI: {e}")
            return f"Error generating content: {str(e)}"
    
    async def refine_assumption(
        self,
        hint: str,
        conversation_history: List[Dict],
        max_messages: int = 5
    ) -> str:
        """
        Analyze hint + recent conversation to refine assumption
        
        Args:
            hint: User's assumption hint
            conversation_history: Full conversation history
            max_messages: Number of recent messages to analyze
            
        Returns:
            Refined assumption statement
        """
        # Get last N messages
        recent = conversation_history[-max_messages:] if len(conversation_history) > max_messages else conversation_history
        
        # Build prompt
        system_prompt = """You are an expert systems engineer analyzing technical discussions.
Your task is to extract and refine assumptions into clear, specific, testable statements."""
        
        conversation_text = self._format_conversation(recent)
        
        prompt = f"""Analyze this discussion and the user's hint to extract a clear, specific assumption.

Recent conversation:
{conversation_text}

User's hint: "{hint}"

Extract a single, clear assumption statement that:
- Is specific and actionable
- Can be validated or tested
- Is stated as a factual claim
- Is concise (1-2 sentences max)

Return ONLY the refined assumption text, no explanation or preamble."""
        
        return await self._call_openai(prompt, system_prompt=system_prompt, max_tokens=150, temperature=0.5)
    
    async def generate_white_paper(
        self,
        conversation_history: List[Dict],
        project_metadata: Dict
    ) -> str:
        """
        Generate white paper markdown from conversation
        
        Args:
            conversation_history: Full conversation history
            project_metadata: Project information
            
        Returns:
            White paper content in markdown format
        """
        system_prompt = """You are an expert technical writer creating professional white papers.
Create well-structured, clear, and concise technical documentation."""
        
        project_name = project_metadata.get('name', 'Unknown Project')
        conversation_text = self._format_conversation(conversation_history)
        
        prompt = f"""Generate a professional white paper summarizing this technical discussion.

Project: {project_name}
Discussion ({len(conversation_history)} messages):

{conversation_text}

Create a well-structured white paper with:
- Title (based on main topic)
- Executive Summary (2-3 paragraphs)
- Key Topics Discussed (with subsections for each major topic)
- Technical Details (implementation specifics, technologies, approaches)
- Decisions Made (if any key decisions were discussed)
- Conclusions and Next Steps

Format in clean markdown with proper headings (##, ###).
Be professional and concise. Focus on technical substance.
Include specific details from the conversation."""
        
        return await self._call_openai(prompt, system_prompt=system_prompt, max_tokens=3000, temperature=0.7)
    
    async def generate_mermaid_diagram(
        self,
        description: str,
        conversation_history: List[Dict]
    ) -> str:
        """
        Generate Mermaid diagram from description + conversation context
        
        Args:
            description: User's diagram description/request
            conversation_history: Full conversation history
            
        Returns:
            Mermaid diagram syntax
        """
        system_prompt = """You are an expert at creating technical diagrams using Mermaid syntax.
Generate clear, accurate Mermaid diagrams based on technical discussions."""
        
        # Use last 10 messages for context
        recent = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
        conversation_text = self._format_conversation(recent)
        
        prompt = f"""Generate a Mermaid diagram based on this request and discussion context.

User request: "{description}"

Recent discussion:
{conversation_text}

Generate valid Mermaid syntax for an appropriate diagram type:
- flowchart/graph (for processes, flows, architecture)
- sequenceDiagram (for interactions, API calls)
- classDiagram (for data models, OOP structures)
- erDiagram (for database schemas)
- stateDiagram (for state machines)

Choose the most appropriate type based on the request and context.
Return ONLY the complete mermaid code block, nothing else.
Start with the diagram type declaration (e.g., "flowchart TD" or "sequenceDiagram")."""
        
        return await self._call_openai(prompt, system_prompt=system_prompt, max_tokens=1500, temperature=0.5)
    
    async def generate_summary(
        self,
        conversation_history: List[Dict],
        max_messages: int = 10
    ) -> str:
        """
        Generate quick summary of recent messages
        
        Args:
            conversation_history: Full conversation history
            max_messages: Number of recent messages to summarize
            
        Returns:
            Summary text
        """
        recent = conversation_history[-max_messages:] if len(conversation_history) > max_messages else conversation_history
        
        if not recent:
            return "No recent messages to summarize."
        
        logger.info(f"📊 SUMMARY_DEBUG: Summarizing {len(recent)} messages from total {len(conversation_history)}")
        logger.info(f"📊 SUMMARY_DEBUG: First message sample: {str(recent[0])[:200]}")
        
        conversation_text = self._format_conversation(recent)
        
        logger.info(f"📊 SUMMARY_DEBUG: Formatted conversation length: {len(conversation_text)} chars")
        logger.info(f"📊 SUMMARY_DEBUG: Conversation preview: {conversation_text[:500]}")
        
        system_prompt = """You are a concise technical summarizer. Create brief, accurate summaries."""
        
        prompt = f"""Provide a concise 2-3 sentence summary of this recent discussion:

{conversation_text}

Focus on:
- Main topics discussed
- Key decisions or conclusions
- Current state/direction

Be specific and technical. Summary:"""
        
        return await self._call_openai(prompt, system_prompt=system_prompt, max_tokens=150, temperature=0.5)
