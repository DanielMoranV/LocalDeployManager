"""
Gestión de archivos .env
Maneja creación, carga, actualización y validación de variables de entorno
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv, set_key, unset_key

from .logger import logger
from .utils import (
    get_active_project_path,
    generate_secure_password,
    generate_jwt_secret
)


class EnvManager:
    """Manager para archivos .env"""

    def __init__(self, env_path: Optional[Path] = None):
        """
        Inicializa el EnvManager

        Args:
            env_path: Path al archivo .env. Si es None, usa active-project/backend/.env
        """
        if env_path is None:
            self.env_path = get_active_project_path() / "backend" / ".env"
        else:
            self.env_path = Path(env_path)

    def load(self) -> Dict[str, str]:
        """
        Carga variables desde el archivo .env

        Returns:
            Dict con todas las variables de entorno
        """
        if not self.env_path.exists():
            logger.log_warning(f".env file not found at {self.env_path}")
            return {}

        # Cargar en ambiente
        load_dotenv(self.env_path)

        # Parsear manualmente para retornar dict
        env_vars = {}
        with open(self.env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Ignorar comentarios y líneas vacías
                if not line or line.startswith('#'):
                    continue

                # Parsear KEY=VALUE
                match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line)
                if match:
                    key, value = match.groups()
                    # Remover comillas si existen
                    value = value.strip('"').strip("'")
                    env_vars[key] = value

        logger.log_debug(f"Loaded {len(env_vars)} variables from {self.env_path}")
        return env_vars

    def create_from_template(self, template_path: Path, replacements: Dict[str, str]):
        """
        Crea un archivo .env desde un template

        Args:
            template_path: Path al archivo template
            replacements: Dict con valores a reemplazar
        """
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        logger.step(f"Creating .env from template: {template_path.name}")

        # Leer template
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Reemplazar placeholders
        for key, value in replacements.items():
            placeholder = f"{{{{{key}}}}}"  # {{KEY}}
            content = content.replace(placeholder, str(value))

        # Crear directorio si no existe
        self.env_path.parent.mkdir(parents=True, exist_ok=True)

        # Guardar .env
        with open(self.env_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.success(f".env created at {self.env_path}")

    def set(self, key: str, value: str):
        """
        Establece o actualiza una variable

        Args:
            key: Nombre de la variable
            value: Valor a establecer
        """
        if not self.env_path.exists():
            # Crear archivo vacío
            self.env_path.parent.mkdir(parents=True, exist_ok=True)
            self.env_path.touch()

        # Usar dotenv set_key
        set_key(str(self.env_path), key, value)
        logger.log_debug(f"Set {key} in {self.env_path}")

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Obtiene el valor de una variable

        Args:
            key: Nombre de la variable
            default: Valor por defecto si no existe

        Returns:
            Valor de la variable o default
        """
        env_vars = self.load()
        return env_vars.get(key, default)

    def delete(self, key: str):
        """
        Elimina una variable del .env

        Args:
            key: Nombre de la variable a eliminar
        """
        if not self.env_path.exists():
            return

        unset_key(str(self.env_path), key)
        logger.log_debug(f"Deleted {key} from {self.env_path}")

    def update_multiple(self, variables: Dict[str, str]):
        """
        Actualiza múltiples variables a la vez

        Args:
            variables: Dict con las variables a actualizar
        """
        for key, value in variables.items():
            self.set(key, value)

        logger.log_info(f"Updated {len(variables)} variables in .env")

    def generate_laravel_keys(self) -> Dict[str, str]:
        """
        Genera claves para Laravel (APP_KEY, JWT_SECRET, DB_PASSWORD)

        Returns:
            Dict con las claves generadas
        """
        logger.step("Generating Laravel keys...")

        keys = {
            'APP_KEY': f'base64:{generate_jwt_secret(32)}',
            'JWT_SECRET': generate_jwt_secret(64),
            'DB_PASSWORD': generate_secure_password(32),
        }

        logger.success("Laravel keys generated")
        return keys

    def generate_springboot_keys(self) -> Dict[str, str]:
        """
        Genera claves para SpringBoot

        Returns:
            Dict con las claves generadas
        """
        logger.step("Generating SpringBoot keys...")

        keys = {
            'JWT_SECRET': generate_jwt_secret(64),
            'DB_PASSWORD': generate_secure_password(32),
            'ENCRYPTION_KEY': generate_jwt_secret(32),
        }

        logger.success("SpringBoot keys generated")
        return keys

    def validate_required(self, required_vars: List[str]) -> tuple[bool, List[str]]:
        """
        Valida que existan las variables requeridas

        Args:
            required_vars: Lista de variables requeridas

        Returns:
            Tupla (all_present, missing_vars)
        """
        env_vars = self.load()
        missing = []

        for var in required_vars:
            if var not in env_vars or not env_vars[var]:
                missing.append(var)

        is_valid = len(missing) == 0

        if not is_valid:
            logger.log_warning(f"Missing required variables: {', '.join(missing)}")

        return is_valid, missing

    def get_required_vars_for_stack(self, stack: str) -> List[str]:
        """
        Obtiene la lista de variables requeridas según el stack

        Args:
            stack: 'laravel-vue' o 'springboot-vue'

        Returns:
            Lista de variables requeridas
        """
        base_vars = ['APP_NAME', 'APP_ENV', 'DB_HOST', 'DB_DATABASE', 'DB_USERNAME', 'DB_PASSWORD']

        if stack == 'laravel-vue':
            return base_vars + [
                'APP_KEY',
                'APP_URL',
                'DB_CONNECTION',
            ]
        elif stack == 'springboot-vue':
            return base_vars + [
                'SPRING_DATASOURCE_URL',
                'SERVER_PORT',
            ]
        else:
            return base_vars

    def backup(self, backup_path: Optional[Path] = None):
        """
        Crea un backup del archivo .env

        Args:
            backup_path: Path donde guardar el backup. Si es None, usa .env.backup
        """
        if not self.env_path.exists():
            logger.warning("No .env file to backup")
            return

        if backup_path is None:
            backup_path = self.env_path.parent / ".env.backup"

        import shutil
        shutil.copy2(self.env_path, backup_path)
        logger.success(f".env backed up to {backup_path}")

    def restore(self, backup_path: Optional[Path] = None):
        """
        Restaura un backup del .env

        Args:
            backup_path: Path del backup. Si es None, usa .env.backup
        """
        if backup_path is None:
            backup_path = self.env_path.parent / ".env.backup"

        if not backup_path.exists():
            logger.error(f"Backup not found: {backup_path}")
            return

        import shutil
        shutil.copy2(backup_path, self.env_path)
        logger.success(f".env restored from {backup_path}")

    def exists(self) -> bool:
        """Verifica si el archivo .env existe"""
        return self.env_path.exists()

    def show_config(self, hide_secrets: bool = True):
        """
        Muestra la configuración actual de forma legible

        Args:
            hide_secrets: Si es True, oculta passwords y secrets
        """
        env_vars = self.load()

        if not env_vars:
            logger.warning("No .env file found or empty")
            return

        # Ocultar secrets si es necesario
        display_vars = {}
        secret_keywords = ['password', 'secret', 'key', 'token', 'api_key']

        for key, value in env_vars.items():
            if hide_secrets and any(keyword in key.lower() for keyword in secret_keywords):
                display_vars[key] = "********"
            else:
                display_vars[key] = value

        logger.print_config(display_vars, f"Environment Variables ({self.env_path.name})")

    def get_database_config(self) -> Dict[str, str]:
        """
        Extrae la configuración de base de datos del .env

        Returns:
            Dict con configuración de DB
        """
        env_vars = self.load()

        db_config = {
            'host': env_vars.get('DB_HOST', 'localhost'),
            'port': env_vars.get('DB_PORT', '3306'),
            'database': env_vars.get('DB_DATABASE', ''),
            'username': env_vars.get('DB_USERNAME', ''),
            'password': env_vars.get('DB_PASSWORD', ''),
            'connection': env_vars.get('DB_CONNECTION', 'mysql'),
        }

        return db_config

    def copy_example(self):
        """Copia .env.example a .env si existe"""
        example_path = self.env_path.parent / ".env.example"

        if not example_path.exists():
            logger.warning(f"No .env.example found at {example_path}")
            return False

        import shutil
        shutil.copy2(example_path, self.env_path)
        logger.success(f"Copied .env.example to .env")
        return True


def create_env_from_config(
    env_path: Path,
    project_name: str,
    domain: str,
    stack: str,
    db_config: Dict[str, str],
    ports: Dict[str, int]
) -> EnvManager:
    """
    Helper function para crear un .env desde configuración del proyecto

    Args:
        env_path: Path donde crear el .env
        project_name: Nombre del proyecto
        domain: Dominio del proyecto
        stack: Stack tecnológico
        db_config: Configuración de base de datos
        ports: Puertos asignados

    Returns:
        EnvManager configurado
    """
    manager = EnvManager(env_path)

    # Determinar valores base
    base_vars = {
        'APP_NAME': project_name,
        'APP_ENV': 'local',
        'APP_DEBUG': 'true',
        'APP_URL': f'https://{domain}',
        'DB_HOST': db_config.get('host', 'mysql'),
        'DB_PORT': str(db_config.get('port', 3306)),
        'DB_DATABASE': db_config.get('database', project_name),
        'DB_USERNAME': db_config.get('username', 'root'),
        'DB_PASSWORD': db_config.get('password', generate_secure_password(32)),
    }

    # Agregar variables específicas del stack
    if stack == 'laravel-vue':
        base_vars.update({
            'APP_KEY': f'base64:{generate_jwt_secret(32)}',
            'JWT_SECRET': generate_jwt_secret(64),
            'DB_CONNECTION': 'mysql',
            'CACHE_DRIVER': 'redis',
            'SESSION_DRIVER': 'redis',
            'QUEUE_CONNECTION': 'redis',
            'REDIS_HOST': 'redis',
            'REDIS_PORT': '6379',
        })
    elif stack == 'springboot-vue':
        db_url = f"jdbc:postgresql://{base_vars['DB_HOST']}:{base_vars['DB_PORT']}/{base_vars['DB_DATABASE']}"
        base_vars.update({
            'SPRING_DATASOURCE_URL': db_url,
            'SPRING_DATASOURCE_USERNAME': base_vars['DB_USERNAME'],
            'SPRING_DATASOURCE_PASSWORD': base_vars['DB_PASSWORD'],
            'SERVER_PORT': str(ports.get('backend', 8080)),
            'JWT_SECRET': generate_jwt_secret(64),
        })

    # Crear archivo .env con todas las variables
    manager.update_multiple(base_vars)

    logger.success(f".env created with {len(base_vars)} variables")
    return manager
