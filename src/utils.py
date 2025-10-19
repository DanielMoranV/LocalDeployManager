"""
Utilidades generales para LDM
"""

import os
import sys
import json
import platform
import secrets
import string
from pathlib import Path
from typing import Optional, Dict, Any


def get_base_path() -> Path:
    """Obtiene el path base de LDM según el OS"""
    return Path.home() / "local-deployer"


def get_active_project_path() -> Path:
    """Obtiene el path del proyecto activo"""
    return get_base_path() / "active-project"


def is_linux() -> bool:
    """Verifica si está corriendo en Linux"""
    return platform.system() == "Linux"


def is_windows() -> bool:
    """Verifica si está corriendo en Windows"""
    return platform.system() == "Windows"


def is_macos() -> bool:
    """Verifica si está corriendo en macOS"""
    return platform.system() == "Darwin"


def get_os_name() -> str:
    """Retorna el nombre del OS"""
    return platform.system()


def generate_secure_password(length: int = 32) -> str:
    """Genera una contraseña segura"""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    # Evitar caracteres que puedan causar problemas en shells
    alphabet = alphabet.replace("'", "").replace('"', "").replace("\\", "").replace("`", "")
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_jwt_secret(length: int = 64) -> str:
    """Genera un JWT secret"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def load_json_file(file_path: Path) -> Optional[Dict[Any, Any]]:
    """Carga un archivo JSON"""
    try:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except Exception as e:
        raise Exception(f"Error loading JSON from {file_path}: {str(e)}")


def save_json_file(file_path: Path, data: Dict[Any, Any], indent: int = 2):
    """Guarda un archivo JSON"""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
    except Exception as e:
        raise Exception(f"Error saving JSON to {file_path}: {str(e)}")


def load_config() -> Dict[Any, Any]:
    """Carga el archivo de configuración global"""
    config_path = get_base_path() / "config.json"
    config = load_json_file(config_path)

    if config is None:
        # Retornar configuración por defecto
        return get_default_config()

    # Validar con Pydantic si es posible
    try:
        from .models import validate_global_config
        validated = validate_global_config(config)
        return validated.model_dump()
    except Exception:
        # Si falla la validación, retornar el dict original
        return config


def save_config(config: Dict[Any, Any]):
    """Guarda la configuración global"""
    config_path = get_base_path() / "config.json"
    save_json_file(config_path, config)


def get_default_config() -> Dict[str, Any]:
    """Retorna la configuración por defecto"""
    return {
        "version": "1.0.0",
        "base_path": str(get_base_path()),
        "docker_network_prefix": "ldm",
        "default_stack": "laravel-vue",
        "default_db": "mysql",
        "default_ports": {
            "http": 80,
            "https": 443,
            "mysql": 3306,
            "postgres": 5432
        },
        "auto_backup_on_deploy": False,
        "max_backups_per_project": 10,
        "log_level": "INFO",
        "java_version": "21",
        "php_version": "8.2",
        "node_version": "20"
    }


def ensure_base_directories():
    """Asegura que existan los directorios base"""
    base_path = get_base_path()
    directories = [
        base_path,
        base_path / "logs",
        base_path / "backups",
        base_path / "certs",
        base_path / "templates",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def project_exists() -> bool:
    """Verifica si existe un proyecto activo"""
    active_project = get_active_project_path()
    return active_project.exists() and (active_project / ".project-config.json").exists()


def get_project_config() -> Optional[Dict[Any, Any]]:
    """Obtiene la configuración del proyecto activo"""
    if not project_exists():
        return None

    config_path = get_active_project_path() / ".project-config.json"
    return load_json_file(config_path)


def save_project_config(config: Dict[Any, Any]):
    """Guarda la configuración del proyecto activo"""
    config_path = get_active_project_path() / ".project-config.json"
    save_json_file(config_path, config)


def command_exists(command: str) -> bool:
    """Verifica si un comando existe en el sistema"""
    from shutil import which
    return which(command) is not None


def get_version() -> str:
    """Obtiene la versión de LDM"""
    from . import __version__
    return __version__


def format_bytes(bytes_size: int) -> str:
    """Formatea bytes a formato legible"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def validate_domain(domain: str) -> bool:
    """Valida que un dominio tenga formato correcto"""
    import re
    # Pattern simple para dominios locales
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
    return re.match(pattern, domain) is not None


def validate_url(url: str) -> bool:
    """Valida que una URL de git sea correcta"""
    import re
    # Pattern para URLs de git (http/https/git)
    patterns = [
        r'^https?://',
        r'^git@',
        r'^ssh://',
        r'^github\.com/',  # Aceptar github.com sin protocolo
        r'^gitlab\.com/',  # Aceptar gitlab.com sin protocolo
        r'^bitbucket\.org/',  # Aceptar bitbucket.org sin protocolo
    ]
    return any(re.match(pattern, url) for pattern in patterns)


def normalize_git_url(url: str) -> str:
    """
    Normaliza una URL de git agregando https:// si es necesario

    Args:
        url: URL del repositorio

    Returns:
        URL normalizada con protocolo
    """
    import re

    # Si ya tiene protocolo, retornar como está
    if re.match(r'^(https?|git|ssh)://', url) or url.startswith('git@'):
        return url

    # Si es una URL de github, gitlab o bitbucket sin protocolo, agregar https://
    if re.match(r'^(github\.com|gitlab\.com|bitbucket\.org)/', url):
        return f'https://{url}'

    # Por defecto, retornar como está
    return url


def normalize_project_name(name: str) -> str:
    """Normaliza el nombre de un proyecto (elimina caracteres especiales)"""
    import re
    # Solo letras, números, guiones y underscores
    normalized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    return normalized.lower()
