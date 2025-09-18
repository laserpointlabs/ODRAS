"""
Namespace Synchronization Service
Ensures Fuseki remains the single source of truth for ontology data
"""

import logging
from typing import List, Dict, Any, Optional
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)


class NamespaceSyncService:
    """Service to synchronize namespace data with Fuseki"""

    def __init__(self, fuseki_url: str = "http://localhost:3030"):
        self.fuseki_url = fuseki_url
        self.dataset = "odras"

    async def sync_class_to_fuseki(
        self, namespace_path: str, version: str, class_data: Dict[str, Any]
    ) -> bool:
        """Sync a single class to Fuseki"""
        try:
            # Create the graph IRI for this namespace version
            graph_iri = f"https://w3id.org/defense/{namespace_path}/{version}"

            # Prepare SPARQL update to add the class
            sparql_update = f"""
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

            INSERT DATA {{
                GRAPH <{graph_iri}> {{
                    <{class_data['iri']}> a owl:Class ;
                        rdfs:label "{class_data['label']}" .

                    {f'<{class_data["iri"]}> rdfs:comment "{class_data["comment"]}" .' if class_data.get('comment') else ''}
                }}
            }}
            """

            # Send update to Fuseki
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.fuseki_url}/{self.dataset}/update",
                    data=sparql_update,
                    headers={"Content-Type": "application/sparql-update"},
                    timeout=30.0,
                )

                if response.status_code == 200:
                    logger.info(f"Successfully synced class {class_data['local_name']} to Fuseki")
                    return True
                else:
                    logger.error(
                        f"Failed to sync class to Fuseki: {response.status_code} - {response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error syncing class to Fuseki: {e}")
            return False

    async def sync_namespace_to_fuseki(
        self, namespace_path: str, version: str, classes: List[Dict[str, Any]]
    ) -> bool:
        """Sync an entire namespace version to Fuseki"""
        try:
            # Create the graph IRI for this namespace version
            graph_iri = f"https://w3id.org/defense/{namespace_path}/{version}"

            # Prepare SPARQL update to add all classes
            class_triples = []
            for class_data in classes:
                class_triple = f"""
                    <{class_data['iri']}> a owl:Class ;
                        rdfs:label "{class_data['label']}" .
                """

                if class_data.get("comment"):
                    class_triple += (
                        f'<{class_data["iri"]}> rdfs:comment "{class_data["comment"]}" .'
                    )

                class_triples.append(class_triple)

            sparql_update = f"""
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

            INSERT DATA {{
                GRAPH <{graph_iri}> {{
                    {''.join(class_triples)}
                }}
            }}
            """

            # Send update to Fuseki
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.fuseki_url}/{self.dataset}/update",
                    data=sparql_update,
                    headers={"Content-Type": "application/sparql-update"},
                    timeout=30.0,
                )

                if response.status_code == 200:
                    logger.info(
                        f"Successfully synced namespace {namespace_path}/{version} with {len(classes)} classes to Fuseki"
                    )
                    return True
                else:
                    logger.error(
                        f"Failed to sync namespace to Fuseki: {response.status_code} - {response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error syncing namespace to Fuseki: {e}")
            return False

    async def get_classes_from_fuseki(
        self, namespace_path: str, version: str
    ) -> List[Dict[str, Any]]:
        """Get classes from Fuseki for a namespace version"""
        try:
            graph_iri = f"https://w3id.org/defense/{namespace_path}/{version}"

            sparql_query = f"""
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

            SELECT ?class ?label ?comment WHERE {{
                GRAPH <{graph_iri}> {{
                    ?class a owl:Class .
                    OPTIONAL {{ ?class rdfs:label ?label }}
                    OPTIONAL {{ ?class rdfs:comment ?comment }}
                }}
            }}
            ORDER BY ?label
            """

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.fuseki_url}/{self.dataset}/sparql",
                    data=sparql_query,
                    headers={"Content-Type": "application/sparql-query"},
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    classes = []

                    for binding in data.get("results", {}).get("bindings", []):
                        class_iri = binding.get("class", {}).get("value", "")
                        label = binding.get("label", {}).get("value", "")
                        comment = binding.get("comment", {}).get("value", "")

                        # Extract local name from IRI
                        local_name = (
                            class_iri.split("#")[-1]
                            if "#" in class_iri
                            else class_iri.split("/")[-1]
                        )

                        classes.append(
                            {
                                "iri": class_iri,
                                "local_name": local_name,
                                "label": label,
                                "comment": comment,
                            }
                        )

                    logger.info(
                        f"Retrieved {len(classes)} classes from Fuseki for {namespace_path}/{version}"
                    )
                    return classes
                else:
                    logger.error(
                        f"Failed to get classes from Fuseki: {response.status_code} - {response.text}"
                    )
                    return []

        except Exception as e:
            logger.error(f"Error getting classes from Fuseki: {e}")
            return []

    async def update_class_in_fuseki(
        self,
        namespace_path: str,
        version: str,
        class_iri: str,
        new_label: str,
        new_comment: Optional[str] = None,
    ) -> bool:
        """Update a class in Fuseki"""
        try:
            graph_iri = f"https://w3id.org/defense/{namespace_path}/{version}"

            # First delete existing label and comment
            delete_sparql = f"""
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

            DELETE {{
                GRAPH <{graph_iri}> {{
                    <{class_iri}> rdfs:label ?old_label .
                    <{class_iri}> rdfs:comment ?old_comment .
                }}
            }}
            WHERE {{
                GRAPH <{graph_iri}> {{
                    <{class_iri}> rdfs:label ?old_label .
                    OPTIONAL {{ <{class_iri}> rdfs:comment ?old_comment }}
                }}
            }}
            """

            # Then insert new label and comment
            insert_sparql = f"""
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

            INSERT DATA {{
                GRAPH <{graph_iri}> {{
                    <{class_iri}> rdfs:label "{new_label}" .
                    {f'<{class_iri}> rdfs:comment "{new_comment}" .' if new_comment else ''}
                }}
            }}
            """

            async with httpx.AsyncClient() as client:
                # Delete old values
                delete_response = await client.post(
                    f"{self.fuseki_url}/{self.dataset}/update",
                    data=delete_sparql,
                    headers={"Content-Type": "application/sparql-update"},
                    timeout=30.0,
                )

                if delete_response.status_code != 200:
                    logger.error(f"Failed to delete old class data: {delete_response.status_code}")
                    return False

                # Insert new values
                insert_response = await client.post(
                    f"{self.fuseki_url}/{self.dataset}/update",
                    data=insert_sparql,
                    headers={"Content-Type": "application/sparql-update"},
                    timeout=30.0,
                )

                if insert_response.status_code == 200:
                    logger.info(f"Successfully updated class {class_iri} in Fuseki")
                    return True
                else:
                    logger.error(
                        f"Failed to update class in Fuseki: {insert_response.status_code} - {insert_response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error updating class in Fuseki: {e}")
            return False

    async def delete_class_from_fuseki(
        self, namespace_path: str, version: str, class_iri: str
    ) -> bool:
        """Delete a class from Fuseki"""
        try:
            graph_iri = f"https://w3id.org/defense/{namespace_path}/{version}"

            sparql_update = f"""
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

            DELETE {{
                GRAPH <{graph_iri}> {{
                    <{class_iri}> ?p ?o .
                }}
            }}
            WHERE {{
                GRAPH <{graph_iri}> {{
                    <{class_iri}> ?p ?o .
                }}
            }}
            """

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.fuseki_url}/{self.dataset}/update",
                    data=sparql_update,
                    headers={"Content-Type": "application/sparql-update"},
                    timeout=30.0,
                )

                if response.status_code == 200:
                    logger.info(f"Successfully deleted class {class_iri} from Fuseki")
                    return True
                else:
                    logger.error(
                        f"Failed to delete class from Fuseki: {response.status_code} - {response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error deleting class from Fuseki: {e}")
            return False

