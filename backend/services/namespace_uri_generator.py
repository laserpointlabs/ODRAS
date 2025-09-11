"""
Namespace URI Generator Service for ODRAS
Generates proper organizational URIs based on installation configuration
"""

import logging
from typing import Dict, Optional
from urllib.parse import quote

from .config import Settings

logger = logging.getLogger(__name__)


class NamespaceURIGenerator:
    """
    Generates proper organizational URIs for ontologies based on installation configuration.
    Supports hierarchical namespace structures for government, defense, and industry contexts.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_uri = settings.installation_base_uri.rstrip("/")
        self.prefix = settings.installation_prefix

    def generate_ontology_uri(
        self,
        namespace_type: str,
        domain: Optional[str] = None,
        program: Optional[str] = None,
        project: Optional[str] = None,
        se_domain: Optional[str] = None,
        mission_type: Optional[str] = None,
        platform_type: Optional[str] = None,
        ontology_name: str = "ontology",
    ) -> str:
        """
        Generate a proper organizational URI for an ontology based on its type and context.

        Args:
            namespace_type: Type of namespace (core, domain, program, project, se, mission, platform)
            domain: Domain name (e.g., 'aviation', 'logistics')
            program: Program name (e.g., 'avp', 'f35')
            project: Project name (e.g., 'x1', 'block-4')
            se_domain: Systems engineering domain (e.g., 'reliability', 'sustainment')
            mission_type: Mission type (e.g., 'asw', 'cas')
            platform_type: Platform type (e.g., 'ddg', 'frigate')
            ontology_name: Name of the ontology

        Returns:
            Full URI for the ontology
        """

        # Sanitize inputs
        ontology_name = self._sanitize_name(ontology_name)

        if namespace_type == "core":
            return f"{self.base_uri}/core/{ontology_name}"

        elif namespace_type == "domain" and domain:
            domain = self._sanitize_name(domain)
            return f"{self.base_uri}/{domain}/{ontology_name}"

        elif namespace_type == "program" and program:
            program = self._sanitize_name(program)
            return f"{self.base_uri}/{program}/core/{ontology_name}"

        elif namespace_type == "project" and program and project:
            program = self._sanitize_name(program)
            project = self._sanitize_name(project)
            return f"{self.base_uri}/{program}/{project}/{ontology_name}"

        elif namespace_type == "se" and se_domain:
            se_domain = self._sanitize_name(se_domain)
            return f"{self.base_uri}/se/{se_domain}/{ontology_name}"

        elif namespace_type == "mission" and mission_type:
            mission_type = self._sanitize_name(mission_type)
            return f"{self.base_uri}/mission/{mission_type}/{ontology_name}"

        elif namespace_type == "platform" and platform_type:
            platform_type = self._sanitize_name(platform_type)
            return f"{self.base_uri}/platform/{platform_type}/{ontology_name}"

        else:
            # Fallback to simple structure
            logger.warning(
                f"Invalid namespace type '{namespace_type}' or missing required parameters. Using fallback."
            )
            return f"{self.base_uri}/{ontology_name}"

    def generate_class_uri(self, ontology_uri: str, class_name: str) -> str:
        """
        Generate a full IRI for a class within an ontology.

        Args:
            ontology_uri: Base URI of the ontology
            class_name: Name of the class

        Returns:
            Full IRI for the class
        """
        class_name = self._sanitize_name(class_name)
        return f"{ontology_uri}#{class_name}"

    def generate_property_uri(self, ontology_uri: str, property_name: str) -> str:
        """
        Generate a full IRI for a property within an ontology.

        Args:
            ontology_uri: Base URI of the ontology
            property_name: Name of the property

        Returns:
            Full IRI for the property
        """
        property_name = self._sanitize_name(property_name)
        return f"{ontology_uri}#{property_name}"

    def get_namespace_prefix(self, ontology_uri: str) -> str:
        """
        Extract a suitable prefix for an ontology URI.

        Args:
            ontology_uri: Full URI of the ontology

        Returns:
            Suggested prefix for the ontology
        """
        # Extract the last meaningful part of the URI
        parts = ontology_uri.rstrip("/").split("/")

        if len(parts) >= 2:
            # Use the last two parts for the prefix
            if len(parts) >= 3:
                return f"{parts[-2]}-{parts[-1]}"
            else:
                return parts[-1]
        else:
            return self.prefix

    def get_external_namespace_mappings(self) -> Dict[str, str]:
        """
        Get standard external namespace mappings for common ontologies.

        Returns:
            Dictionary mapping prefixes to URIs
        """
        return {
            # Government/DoD ontologies
            "gov": "https://w3id.org/defense/gov/core#",
            "dod": "https://w3id.org/defense/dod/core#",
            # Service ontologies
            "usn": "https://w3id.org/defense/usn/core#",
            "usaf": "https://w3id.org/defense/usaf/core#",
            "usa": "https://w3id.org/defense/usa/core#",
            "usmc": "https://w3id.org/defense/usmc/core#",
            "ussf": "https://w3id.org/defense/ussf/core#",
            # Domain ontologies
            "mission": "https://w3id.org/defense/dod/joint/mission#",
            "logistics": "https://w3id.org/defense/dod/joint/logistics#",
            # Industry ontologies (examples)
            "boeing": "https://ontology.boeing.com/defense#",
            "lockheed": "https://ontology.lockheedmartin.com/defense#",
            "northrop": "https://ontology.northropgrumman.com/defense#",
            # Standard ontologies
            "bfo": "http://purl.obolibrary.org/obo/bfo/",
            "owl": "http://www.w3.org/2002/07/owl#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "skos": "http://www.w3.org/2004/02/skos/core#",
            "dct": "http://purl.org/dc/terms/",
            "vann": "http://purl.org/vocab/vann/",
        }

    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize a name for use in URIs.

        Args:
            name: Raw name to sanitize

        Returns:
            Sanitized name safe for URIs
        """
        if not name:
            return "unnamed"

        # Convert to lowercase and replace spaces/special chars with hyphens
        sanitized = name.lower().strip()
        sanitized = sanitized.replace(" ", "-")
        sanitized = sanitized.replace("_", "-")

        # Remove any characters that aren't alphanumeric or hyphens
        import re

        sanitized = re.sub(r"[^a-z0-9\-]", "", sanitized)

        # Remove multiple consecutive hyphens
        sanitized = re.sub(r"-+", "-", sanitized)

        # Remove leading/trailing hyphens
        sanitized = sanitized.strip("-")

        # Ensure it's not empty
        if not sanitized:
            sanitized = "unnamed"

        return sanitized

    def generate_import_statement(self, ontology_uri: str, prefix: str) -> str:
        """
        Generate a proper import statement for an ontology.

        Args:
            ontology_uri: URI of the ontology to import
            prefix: Prefix to use for the imported ontology

        Returns:
            Turtle import statement
        """
        return f"@prefix {prefix}: <{ontology_uri}#> ."

    def generate_ontology_header(
        self,
        ontology_uri: str,
        title: str,
        description: str = "",
        version: str = "1.0.0",
        imports: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Generate a proper ontology header in Turtle format.

        Args:
            ontology_uri: URI of the ontology
            title: Title of the ontology
            description: Description of the ontology
            version: Version of the ontology
            imports: Dictionary of prefix -> URI for imports

        Returns:
            Turtle ontology header
        """
        lines = [
            f"@base <{ontology_uri}> .",
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
            "@prefix dct: <http://purl.org/dc/terms/> .",
            "@prefix vann: <http://purl.org/vocab/vann/> .",
            "",
        ]

        # Add import statements
        if imports:
            for prefix, uri in imports.items():
                lines.append(f"@prefix {prefix}: <{uri}> .")
            lines.append("")

        # Add ontology declaration
        lines.extend(
            [
                f"<{ontology_uri}> a owl:Ontology ;",
                f'  dct:title "{title}" ;',
                f"  owl:versionIRI <{ontology_uri}/v{version}> ;",
                f'  vann:preferredNamespacePrefix "{self.get_namespace_prefix(ontology_uri)}" ;',
                f'  vann:preferredNamespaceUri "{ontology_uri}#"',
            ]
        )

        if description:
            lines.append(f'  ; rdfs:comment "{description}"')

        lines.append("  .")
        lines.append("")

        return "\n".join(lines)
