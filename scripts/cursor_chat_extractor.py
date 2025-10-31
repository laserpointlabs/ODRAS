#!/usr/bin/env python3
"""
Cursor Chat History Extractor

Extracts conversations from Cursor chat history JSON files and prepares them
for integration into ODRAS knowledge base.

Usage:
    python scripts/cursor_chat_extractor.py \
        --source "/mnt/c/Users/JohnDeHart/AppData/Roaming/Cursor/User/workspaceStorage" \
        --output data/cursor_chat_backups/ \
        --workspace-map "workspace_map.json"
"""

import json
import os
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CursorChatExtractor:
    """Extract and parse Cursor chat history JSON files."""

    def __init__(self, workspace_map: Optional[Dict[str, str]] = None):
        """
        Initialize extractor with optional workspace mapping.

        Args:
            workspace_map: Dict mapping workspace hash to project path
        """
        self.workspace_map = workspace_map or {}

    def extract_session(self, json_path: str) -> Optional[Dict[str, Any]]:
        """
        Extract conversation data from a single Cursor chat session JSON file.

        Args:
            json_path: Path to Cursor chat session JSON file

        Returns:
            Dict with extracted conversation data or None if extraction fails
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            session_id = data.get('sessionId', '')
            creation_date = data.get('creationDate', 0)
            workspace_hash = self._extract_workspace_hash(json_path)

            # Extract all conversations from requests
            conversations = []
            for request in data.get('requests', []):
                conv = self._extract_conversation(request, session_id)
                if conv:
                    conversations.append(conv)

            if not conversations:
                logger.warning(f"No conversations found in {json_path}")
                return None

            return {
                'session_id': session_id,
                'workspace_hash': workspace_hash,
                'workspace_path': self.workspace_map.get(workspace_hash, ''),
                'creation_date': creation_date,
                'creation_datetime': self._timestamp_to_datetime(creation_date),
                'conversations': conversations,
                'file_path': json_path,
                'file_size': os.path.getsize(json_path),
            }

        except Exception as e:
            logger.error(f"Error extracting {json_path}: {e}")
            return None

    def _extract_conversation(self, request: Dict, session_id: str) -> Optional[Dict[str, Any]]:
        """Extract a single conversation from a request."""
        try:
            request_id = request.get('requestId', '')
            timestamp = request.get('timestamp', 0)

            # Extract user message
            user_message = request.get('message', '')
            if not user_message:
                return None

            # Extract assistant response (may be list of dicts with 'value' keys)
            response_raw = request.get('response', '')
            if isinstance(response_raw, list):
                # Extract text from list of response parts
                response_parts = []
                for item in response_raw:
                    if isinstance(item, dict):
                        response_parts.append(item.get('value', ''))
                    elif isinstance(item, str):
                        response_parts.append(item)
                response = ' '.join(str(p) for p in response_parts if p)
            else:
                response = str(response_raw) if response_raw else ''

            result = request.get('result', {})

            # Extract code citations and references
            code_citations = request.get('codeCitations', [])
            content_references = request.get('contentReferences', [])

            # Build conversation text with context
            conversation_text = self._build_conversation_text(
                user_message, response, result, code_citations, content_references
            )

            # Extract metadata
            metadata = self._extract_metadata(
                user_message, response, code_citations, content_references
            )

            return {
                'request_id': request_id,
                'timestamp': timestamp,
                'datetime': self._timestamp_to_datetime(timestamp) if timestamp else None,
                'user_message': user_message,
                'assistant_response': response,  # Now properly formatted from list/dict
                'result': result,
                'conversation_text': conversation_text,
                'code_citations': code_citations,
                'content_references': content_references,
                'metadata': metadata,
            }

        except Exception as e:
            logger.error(f"Error extracting conversation: {e}")
            return None

    def _build_conversation_text(
        self,
        user_message: str,
        response: str,
        result: Dict,
        code_citations: List,
        content_references: List
    ) -> str:
        """Build a formatted conversation text for chunking."""
        lines = []

        # User message
        lines.append("## User Question")
        lines.append(str(user_message) if user_message else "")
        lines.append("")

        # Code/file references if any
        if code_citations or content_references:
            lines.append("### Context Files")
            all_refs = []
            if code_citations:
                all_refs.extend(code_citations)
            if content_references:
                all_refs.extend(content_references)
            
            for ref in all_refs:
                if isinstance(ref, dict):
                    # Try multiple possible keys for file path
                    file_path = (
                        ref.get('path') or
                        ref.get('file') or
                        ref.get('fsPath', '')
                    )
                    # Check nested reference structure
                    if not file_path and 'reference' in ref:
                        nested = ref['reference']
                        if isinstance(nested, dict):
                            file_path = nested.get('path') or nested.get('fsPath', '')
                    
                    if file_path:
                        lines.append(f"- {file_path}")
            lines.append("")

        # Assistant response
        lines.append("## Assistant Response")
        if response:
            lines.append(response)
        elif result:
            # Try to extract text from result
            text_result = result.get('text', result.get('message', ''))
            if text_result:
                lines.append(text_result)
        lines.append("")

        return "\n".join(lines)

    def _extract_metadata(
        self,
        user_message: str,
        response: str,
        code_citations: List,
        content_references: List
    ) -> Dict[str, Any]:
        """Extract metadata for knowledge categorization."""
        metadata = {
            'topics': [],
            'code_languages': set(),
            'files_referenced': [],
            'decision_type': None,
            'key_phrases': [],
        }

        # Extract file references
        all_refs = code_citations + content_references
        for ref in all_refs:
            if isinstance(ref, dict):
                file_path = ref.get('path', ref.get('file', ''))
                if file_path:
                    metadata['files_referenced'].append(file_path)
                    # Detect language from file extension
                    ext = Path(file_path).suffix.lower()
                    lang_map = {
                        '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
                        '.sql': 'sql', '.md': 'markdown', '.yml': 'yaml',
                        '.yaml': 'yaml', '.json': 'json', '.sh': 'bash'
                    }
                    if ext in lang_map:
                        metadata['code_languages'].add(lang_map[ext])

        # Simple topic detection from keywords
        user_text = str(user_message) if user_message else ""
        resp_text = str(response) if response else ""
        text = (user_text + " " + resp_text).lower()
        topic_keywords = {
            'database': ['database', 'postgres', 'sql', 'migration', 'schema'],
            'rag': ['rag', 'embedding', 'vector', 'qdrant', 'chunk'],
            'chunking': ['chunk', 'chunking', 'semantic', 'split'],
            'api': ['api', 'endpoint', 'route', 'request', 'response'],
            'auth': ['auth', 'authentication', 'login', 'token'],
            'ontology': ['ontology', 'rdf', 'sparql', 'fuseki'],
            'testing': ['test', 'pytest', 'unittest', 'integration'],
            'docker': ['docker', 'container', 'compose'],
        }

        for topic, keywords in topic_keywords.items():
            if any(kw in text for kw in keywords):
                metadata['topics'].append(topic)

        # Decision type detection
        if any(word in text for word in ['decided', 'decision', 'choose', 'selected']):
            metadata['decision_type'] = 'decision'
        elif any(word in text for word in ['implement', 'build', 'create', 'add']):
            metadata['decision_type'] = 'implementation'
        elif any(word in text for word in ['bug', 'fix', 'error', 'issue']):
            metadata['decision_type'] = 'bug_fix'
        elif any(word in text for word in ['feature', 'new', 'enhancement']):
            metadata['decision_type'] = 'feature'

        # Convert sets to lists for JSON serialization
        metadata['code_languages'] = list(metadata['code_languages'])

        return metadata

    def _extract_workspace_hash(self, json_path: str) -> str:
        """Extract workspace hash from JSON file path."""
        # Path format: .../workspaceStorage/{hash}/chatSessions/{session}.json
        parts = Path(json_path).parts
        try:
            ws_index = parts.index('workspaceStorage')
            if ws_index + 1 < len(parts):
                return parts[ws_index + 1]
        except ValueError:
            pass

        # Fallback: hash the directory name
        return hashlib.md5(str(Path(json_path).parent.parent).encode()).hexdigest()[:32]

    def _timestamp_to_datetime(self, timestamp: int) -> Optional[str]:
        """Convert timestamp (milliseconds) to ISO datetime string."""
        if not timestamp:
            return None
        try:
            dt = datetime.fromtimestamp(timestamp / 1000.0)
            return dt.isoformat()
        except Exception:
            return None

    def extract_all_sessions(self, source_dir: str) -> List[Dict[str, Any]]:
        """
        Extract all chat sessions from a workspaceStorage directory.

        Args:
            source_dir: Path to Cursor workspaceStorage directory

        Returns:
            List of extracted session data
        """
        sessions = []
        source_path = Path(source_dir)

        if not source_path.exists():
            logger.error(f"Source directory does not exist: {source_dir}")
            return sessions

        # Find all chat session JSON files
        chat_session_pattern = source_path / "*/chatSessions/*.json"
        json_files = list(source_path.glob("*/chatSessions/*.json"))

        logger.info(f"Found {len(json_files)} chat session files")

        for json_file in json_files:
            logger.info(f"Processing: {json_file.name}")
            session_data = self.extract_session(str(json_file))
            if session_data:
                sessions.append(session_data)

        logger.info(f"Successfully extracted {len(sessions)} sessions")
        return sessions

    def save_extracted_data(self, sessions: List[Dict[str, Any]], output_dir: str) -> Dict[str, Any]:
        """
        Save extracted session data to JSON files.

        Args:
            sessions: List of extracted session data
            output_dir: Directory to save extracted data

        Returns:
            Summary of saved data
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save individual sessions
        for session in sessions:
            session_id = session['session_id']
            filename = f"{session_id}.json"
            filepath = output_path / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(session, f, indent=2, ensure_ascii=False)

        # Save summary/index
        summary = {
            'extraction_date': datetime.now().isoformat(),
            'total_sessions': len(sessions),
            'workspaces': {},
            'statistics': {
                'total_conversations': sum(len(s.get('conversations', [])) for s in sessions),
                'total_size_bytes': sum(s.get('file_size', 0) for s in sessions),
                'date_range': {
                    'earliest': min(
                        (s.get('creation_datetime', '') for s in sessions if s.get('creation_datetime')),
                        default=''
                    ),
                    'latest': max(
                        (s.get('creation_datetime', '') for s in sessions if s.get('creation_datetime')),
                        default=''
                    ),
                }
            }
        }

        # Group by workspace
        for session in sessions:
            ws_hash = session['workspace_hash']
            if ws_hash not in summary['workspaces']:
                summary['workspaces'][ws_hash] = {
                    'workspace_path': session.get('workspace_path', ''),
                    'session_count': 0,
                }
            summary['workspaces'][ws_hash]['session_count'] += 1

        # Save summary
        summary_filepath = output_path / 'extraction_summary.json'
        with open(summary_filepath, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(sessions)} sessions to {output_dir}")
        logger.info(f"Summary saved to {summary_filepath}")

        return summary


def load_workspace_map(map_file: str) -> Dict[str, str]:
    """Load workspace hash to project path mapping."""
    if not os.path.exists(map_file):
        logger.warning(f"Workspace map file not found: {map_file}")
        return {}

    with open(map_file, 'r') as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description='Extract Cursor chat history')
    parser.add_argument(
        '--source',
        required=True,
        help='Path to Cursor workspaceStorage directory'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output directory for extracted data'
    )
    parser.add_argument(
        '--workspace-map',
        help='JSON file mapping workspace hash to project path'
    )
    args = parser.parse_args()

    # Load workspace map if provided
    workspace_map = {}
    if args.workspace_map:
        workspace_map = load_workspace_map(args.workspace_map)

    # Extract sessions
    extractor = CursorChatExtractor(workspace_map)
    sessions = extractor.extract_all_sessions(args.source)

    # Save extracted data
    if sessions:
        summary = extractor.save_extracted_data(sessions, args.output)
        print(f"\n✅ Extraction complete!")
        print(f"   Sessions extracted: {summary['total_sessions']}")
        print(f"   Total conversations: {summary['statistics']['total_conversations']}")
        print(f"   Output directory: {args.output}")
    else:
        print("❌ No sessions extracted")


if __name__ == '__main__':
    main()
