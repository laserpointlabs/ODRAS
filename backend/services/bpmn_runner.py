import uuid
from typing import Any, Dict, List

from .config import Settings
from .embeddings import SimpleHasherEmbedder
from .llm_team import LLMTeam
from .ontology_schema import REQUIREMENT_SCHEMA
from .persistence import PersistenceLayer
from .requirement_extractor import RequirementExtractor


class BPMNWorkflowRunner:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.extractor = RequirementExtractor()
        self.llm_team = LLMTeam(settings)
        self.embedder = SimpleHasherEmbedder()
        self.persistence = PersistenceLayer(settings)
        self.status = {
            "status": "initialized",
            "requirements_found": 0,
            "iterations": 0,
            "results": [],
        }

    async def start_run(self, document_bytes: bytes, filename: str, iterations: int = 10) -> str:
        run_id = str(uuid.uuid4())
        self.status.update(
            {
                "status": "running",
                "filename": filename,
                "iterations": iterations,
                "run_id": run_id,
            }
        )

        # Parse doc text (MVP: treat as utf-8 text)
        try:
            text = document_bytes.decode("utf-8", errors="ignore")
        except Exception:
            text = ""

        # 1) Extract requirements
        requirements = self.extractor.extract(text)
        self.status["requirements_found"] = len(requirements)

        # 2) Monte Carlo loop over requirements
        collected_json: List[Dict[str, Any]] = []
        for i in range(iterations):
            for r in requirements:
                json_obj = await self.llm_team.analyze_requirement(r, REQUIREMENT_SCHEMA)
                json_obj.setdefault("id", f"{uuid.uuid4()}_{i}")
                json_obj.setdefault("text", r)
                collected_json.append(json_obj)

        self.status["results"] = collected_json[:10]  # show sample in UI

        # 3) Embed and push to vector store
        texts = [obj.get("text", "") for obj in collected_json]
        vectors = self.embedder.embed(texts)
        self.persistence.upsert_vector_records(
            embeddings=vectors,
            payloads=collected_json,
        )

        # 4) Push to graph db (very simple schema)
        triples = []
        for obj in collected_json:
            rid = obj.get("id")
            entities = obj.get("entities", [])
            for e in entities:
                triples.append((f"req:{rid}", "HAS_ENTITY", f"ent:{e.get('id')}"))
            for rel in obj.get("relationships", []):
                triples.append(
                    (
                        f"ent:{rel.get('source')}",
                        rel.get("type", "REL"),
                        f"ent:{rel.get('target')}",
                    )
                )
        self.persistence.write_graph(triples)

        # 5) Push to RDF (sketch TTL via simple triples)
        ttl_lines = []
        for s, p, o in triples:
            ttl_lines.append(f"<{s}> <{p}> <{o}> .")
        ttl = "\n".join(ttl_lines)
        self.persistence.write_rdf(ttl)

        # 6) Simple analysis (counts)
        analysis = {
            "num_requirements": len(requirements),
            "num_iterations": iterations,
            "num_records": len(collected_json),
            "entity_type_counts": self._count_entity_types(collected_json),
        }
        self.status["analysis"] = analysis

        self.status["status"] = "completed"
        return run_id

    def to_dict(self) -> Dict[str, Any]:
        return self.status

    def _count_entity_types(self, records: List[Dict[str, Any]]):
        counts: Dict[str, int] = {}
        for r in records:
            for e in r.get("entities", []) or []:
                et = e.get("type", "Unknown")
                counts[et] = counts.get(et, 0) + 1
        return counts
