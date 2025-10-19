"""
Modelos Pydantic para validación de datos
"""

from typing import Optional, Dict, Literal
from pathlib import Path
from pydantic import BaseModel, Field, validator, field_validator
from datetime import datetime


class PortsConfig(BaseModel):
    """Configuración de puertos"""
    http: int = Field(default=80, ge=1, le=65535)
    https: int = Field(default=443, ge=1, le=65535)
    mysql: Optional[int] = Field(default=3306, ge=1, le=65535)
    postgres: Optional[int] = Field(default=5432, ge=1, le=65535)
    redis: Optional[int] = Field(default=6379, ge=1, le=65535)
    backend: Optional[int] = Field(default=8080, ge=1, le=65535)

    @field_validator('http', 'https', 'mysql', 'postgres', 'redis', 'backend')
    @classmethod
    def validate_port_range(cls, v):
        if v is not None and (v < 1 or v > 65535):
            raise ValueError(f'Port must be between 1 and 65535')
        return v


class DatabaseConfig(BaseModel):
    """Configuración de base de datos"""
    host: str = Field(default="localhost")
    port: int = Field(default=3306, ge=1, le=65535)
    database: str
    username: str
    password: str
    connection: Literal["mysql", "postgres", "sqlite"] = "mysql"


class GlobalConfig(BaseModel):
    """Configuración global de LDM"""
    version: str = "1.0.0"
    base_path: str = "~/local-deployer"
    docker_network_prefix: str = "ldm"
    default_stack: Literal["laravel-vue", "springboot-vue"] = "laravel-vue"
    default_db: Literal["mysql", "postgres"] = "mysql"
    default_ports: PortsConfig = Field(default_factory=PortsConfig)
    auto_backup_on_deploy: bool = False
    max_backups_per_project: int = Field(default=10, ge=1, le=100)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    java_version: str = "21"
    php_version: str = "8.2"
    node_version: str = "20"

    @field_validator('base_path')
    @classmethod
    def expand_path(cls, v):
        """Expande ~ en el path"""
        return str(Path(v).expanduser())


class ProjectConfig(BaseModel):
    """Configuración de un proyecto específico"""
    name: str
    stack: Literal["laravel-vue", "springboot-vue"]
    domain: str
    backend_repo: str
    frontend_repo: str
    ports: PortsConfig
    database: DatabaseConfig
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_deploy: Optional[datetime] = None
    docker_network: str
    ssl_enabled: bool = True

    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v):
        """Valida formato de dominio"""
        import re
        pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
        if not re.match(pattern, v):
            raise ValueError(f'Invalid domain format: {v}')
        return v

    @field_validator('backend_repo', 'frontend_repo')
    @classmethod
    def validate_repo_url(cls, v):
        """Valida URL de repositorio"""
        import re
        patterns = [r'^https?://', r'^git@', r'^ssh://']
        if not any(re.match(pattern, v) for pattern in patterns):
            raise ValueError(f'Invalid repository URL: {v}')
        return v

    def model_post_init(self, __context):
        """Post-init para generar docker_network si no existe"""
        if not hasattr(self, 'docker_network') or not self.docker_network:
            self.docker_network = f"ldm_{self.name}_network"


class DeployHistory(BaseModel):
    """Registro de un deploy"""
    id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    success: bool
    duration_seconds: Optional[float] = None
    git_commit_backend: Optional[str] = None
    git_commit_frontend: Optional[str] = None
    changes: Optional[str] = None
    error_message: Optional[str] = None
    flags: Dict[str, bool] = Field(default_factory=dict)  # fresh_db, seed, etc.


class BackupMetadata(BaseModel):
    """Metadata de un backup"""
    id: str
    name: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    project_name: str
    git_commit_backend: str
    git_commit_frontend: str
    db_size_bytes: int
    db_tables_count: int
    backup_path: str

    @property
    def formatted_size(self) -> str:
        """Retorna el tamaño formateado"""
        from .utils import format_bytes
        return format_bytes(self.db_size_bytes)


class CredentialsConfig(BaseModel):
    """Credenciales generadas automáticamente"""
    app_key: Optional[str] = None
    jwt_secret: str
    db_root_password: str
    db_password: str
    encryption_key: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        # Evitar que se serialicen en logs
        json_schema_extra = {
            "sensitive": True
        }


# Validadores helpers

def validate_global_config(config_dict: Dict) -> GlobalConfig:
    """
    Valida y retorna un objeto GlobalConfig

    Args:
        config_dict: Dict con configuración

    Returns:
        GlobalConfig validado

    Raises:
        ValidationError si la configuración es inválida
    """
    return GlobalConfig(**config_dict)


def validate_project_config(config_dict: Dict) -> ProjectConfig:
    """
    Valida y retorna un objeto ProjectConfig

    Args:
        config_dict: Dict con configuración del proyecto

    Returns:
        ProjectConfig validado

    Raises:
        ValidationError si la configuración es inválida
    """
    return ProjectConfig(**config_dict)
