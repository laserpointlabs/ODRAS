from typing import Optional
from pydantic import Field

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    qdrant_url: str = "http://localhost:6333"
    neo4j_url: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "testpassword"
    fuseki_url: str = "http://localhost:3030/odras"
    fuseki_user: Optional[str] = None
    fuseki_password: Optional[str] = None
    ollama_url: str = "http://localhost:11434"
    redis_url: str = "redis://localhost:6379"

    llm_provider: str = "openai"  # openai | ollama
    llm_model: str = "gpt-4o-mini"
    openai_api_key: Optional[str] = None

    collection_name: str = "odras_requirements"

    # RAG SQL-first Configuration
    rag_dual_write: str = "true"  # Enable dual-write (SQL + vectors)
    rag_sql_read_through: str = "true"  # Enable SQL read-through for chunk content

    # File Storage Configuration
    storage_backend: str = "minio"  # local | minio | postgresql

    # MinIO Configuration
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_name: str = "odras-files"
    minio_secure: bool = False

    # PostgreSQL Configuration
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_database: str = "odras"
    postgres_user: str = "postgres"
    postgres_password: str = "password"

    # Database Connection Pool Configuration
    postgres_pool_min_connections: int = 5
    postgres_pool_max_connections: int = 50
    postgres_pool_connection_timeout: int = 30
    postgres_pool_connection_lifetime: int = 3600  # 1 hour

    # Local Storage Configuration
    local_storage_path: str = "./storage/files"

    # Camunda BPM Configuration
    camunda_base_url: str = "http://localhost:8080"

    # Application Configuration
    api_base_url: str = "http://localhost:8000"
    environment: str = "development"
    log_level: str = "INFO"

    # Installation Configuration for Installation-Specific IRIs
    # These values are loaded from environment variables with INSTALLATION_ prefix
    installation_name: str = Field(
        default="ODRAS-DEV", alias="INSTALLATION_NAME"
    )  # Installation identifier (e.g., 'XMA-ADT', 'AFIT-RESEARCH')
    installation_organization: str = Field(
        default="ODRAS Development", alias="INSTALLATION_ORGANIZATION"
    )
    installation_base_uri: str = Field(
        default="https://odras-dev.local", alias="INSTALLATION_BASE_URI"
    )  # Installation-specific domain (e.g., 'https://xma-adt.usn.mil')
    installation_prefix: str = Field(default="odras", alias="INSTALLATION_PREFIX")
    installation_type: str = Field(
        default="development", alias="INSTALLATION_TYPE"
    )  # usn, usaf, usa, usmc, ussf, industry, research, etc.
    installation_program_office: str = Field(
        default="Development", alias="INSTALLATION_PROGRAM_OFFICE"
    )
    top_level_domain: str = Field(
        default="local", alias="TOP_LEVEL_DOMAIN"
    )  # mil, gov, com, edu, org
    authority_contact: str = Field(
        default="admin@odras.local", alias="AUTHORITY_CONTACT"
    )  # Responsible authority for this installation

    # Namespace URI Templates
    namespace_core_template: str = "{base_uri}/core#{entity}"
    namespace_domain_template: str = "{base_uri}/{domain}#{entity}"
    namespace_program_template: str = "{base_uri}/{program}/core#{entity}"
    namespace_project_template: str = "{base_uri}/{program}/{project}#{entity}"
    namespace_se_template: str = "{base_uri}/se/{se_domain}#{entity}"
    namespace_mission_template: str = "{base_uri}/mission/{mission_type}#{entity}"
    namespace_platform_template: str = "{base_uri}/platform/{platform_type}#{entity}"

    # Pydantic v2 settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",  # ignore unrelated environment variables
    )
