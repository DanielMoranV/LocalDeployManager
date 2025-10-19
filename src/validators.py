"""
Validaciones para configuraciones de proyectos
Valida consistencia entre nginx, docker-compose y archivos de configuración
"""

import re
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from .logger import logger


def validate_springboot_nginx_ports(
    project_path: Path,
    nginx_config_path: Optional[Path] = None,
    application_properties_path: Optional[Path] = None
) -> Tuple[bool, List[str]]:
    """
    Valida que los puertos de SpringBoot y nginx sean compatibles

    Args:
        project_path: Ruta al proyecto activo
        nginx_config_path: Ruta opcional al nginx.conf (si no se provee, usa project_path/nginx.conf)
        application_properties_path: Ruta opcional al application.properties

    Returns:
        Tupla (is_valid, warnings) donde warnings es una lista de mensajes
    """
    warnings = []

    # Rutas por defecto
    if nginx_config_path is None:
        nginx_config_path = project_path / "nginx.conf"

    if application_properties_path is None:
        application_properties_path = project_path / "backend" / "src" / "main" / "resources" / "application.properties"

    # Verificar que existan los archivos
    if not nginx_config_path.exists():
        warnings.append(f"nginx.conf not found at {nginx_config_path}")
        return False, warnings

    if not application_properties_path.exists():
        warnings.append(f"application.properties not found at {application_properties_path}")
        return False, warnings

    # Extraer puerto de nginx
    nginx_port = extract_nginx_springboot_port(nginx_config_path)

    # Extraer puerto de application.properties
    app_port = extract_springboot_application_port(application_properties_path)

    # Validar que se hayan encontrado los puertos
    if nginx_port is None:
        warnings.append("Could not find SpringBoot upstream port in nginx.conf")
        return False, warnings

    if app_port is None:
        warnings.append("Could not find server.port in application.properties")
        return False, warnings

    # Comparar puertos
    if nginx_port != app_port:
        warnings.append(
            f"PORT MISMATCH: nginx expects SpringBoot on port {nginx_port}, "
            f"but application.properties has server.port={app_port}"
        )
        warnings.append(
            f"  → Fix: Change server.port={app_port} to server.port={nginx_port} in application.properties"
        )
        warnings.append(
            f"  → Or: Change 'server springboot:{nginx_port}' to 'server springboot:{app_port}' in nginx.conf"
        )
        return False, warnings

    return True, []


def extract_nginx_springboot_port(nginx_config_path: Path) -> Optional[int]:
    """
    Extrae el puerto del upstream de SpringBoot en nginx.conf

    Busca patrones como:
        upstream springboot_backend {
            server springboot:8080;
        }

    Args:
        nginx_config_path: Ruta al nginx.conf

    Returns:
        Puerto como int o None si no se encuentra
    """
    try:
        with open(nginx_config_path, 'r') as f:
            content = f.read()

        # Buscar patrón: server springboot:PUERTO;
        pattern = r'server\s+springboot:(\d+)\s*;'
        match = re.search(pattern, content)

        if match:
            return int(match.group(1))

        return None

    except Exception as e:
        logger.log_error(f"Error reading nginx.conf: {str(e)}")
        return None


def extract_springboot_application_port(application_properties_path: Path) -> Optional[int]:
    """
    Extrae el puerto de server.port en application.properties

    Busca líneas como:
        server.port=8080
        server.port = 8091

    Args:
        application_properties_path: Ruta al application.properties

    Returns:
        Puerto como int o None si no se encuentra
    """
    try:
        with open(application_properties_path, 'r') as f:
            content = f.read()

        # Buscar patrón: server.port=PUERTO o server.port = PUERTO
        # Ignorar líneas comentadas con #
        pattern = r'^(?!#)\s*server\.port\s*=\s*(\d+)'

        for line in content.split('\n'):
            match = re.match(pattern, line.strip())
            if match:
                return int(match.group(1))

        return None

    except Exception as e:
        logger.log_error(f"Error reading application.properties: {str(e)}")
        return None


def validate_laravel_nginx_ports(
    project_path: Path,
    nginx_config_path: Optional[Path] = None
) -> Tuple[bool, List[str]]:
    """
    Valida que los puertos de Laravel/PHP-FPM y nginx sean compatibles

    Args:
        project_path: Ruta al proyecto activo
        nginx_config_path: Ruta opcional al nginx.conf

    Returns:
        Tupla (is_valid, warnings)
    """
    warnings = []

    # Rutas por defecto
    if nginx_config_path is None:
        nginx_config_path = project_path / "nginx.conf"

    if not nginx_config_path.exists():
        warnings.append(f"nginx.conf not found at {nginx_config_path}")
        return False, warnings

    try:
        with open(nginx_config_path, 'r') as f:
            content = f.read()

        # Verificar que haya configuración de fastcgi_pass
        if 'fastcgi_pass' not in content:
            warnings.append("No fastcgi_pass configuration found in nginx.conf")
            return False, warnings

        # Buscar fastcgi_pass php:9000
        pattern = r'fastcgi_pass\s+php:(\d+)\s*;'
        match = re.search(pattern, content)

        if match:
            port = int(match.group(1))
            if port != 9000:
                warnings.append(
                    f"WARNING: PHP-FPM typically runs on port 9000, but nginx is configured for port {port}"
                )
                return False, warnings

        return True, []

    except Exception as e:
        logger.log_error(f"Error validating Laravel nginx config: {str(e)}")
        warnings.append(f"Error reading nginx.conf: {str(e)}")
        return False, warnings


def validate_docker_compose_ports(
    compose_path: Path,
    expected_ports: Dict[str, int]
) -> Tuple[bool, List[str]]:
    """
    Valida que los puertos en docker-compose.yml coincidan con los esperados

    Args:
        compose_path: Ruta al docker-compose.yml
        expected_ports: Dict con puertos esperados {'service': port}

    Returns:
        Tupla (is_valid, warnings)
    """
    warnings = []

    if not compose_path.exists():
        warnings.append(f"docker-compose.yml not found at {compose_path}")
        return False, warnings

    try:
        import yaml

        with open(compose_path, 'r') as f:
            compose_config = yaml.safe_load(f)

        services = compose_config.get('services', {})

        for service_name, expected_port in expected_ports.items():
            if service_name not in services:
                warnings.append(f"Service '{service_name}' not found in docker-compose.yml")
                continue

            service_config = services[service_name]

            # Verificar variable de entorno SERVER_PORT para SpringBoot
            if service_name == 'springboot':
                env_vars = service_config.get('environment', [])
                server_port = None

                for env in env_vars:
                    if isinstance(env, str) and env.startswith('SERVER_PORT='):
                        server_port = int(env.split('=')[1])
                        break

                if server_port and server_port != expected_port:
                    warnings.append(
                        f"docker-compose.yml has SERVER_PORT={server_port} but expected {expected_port}"
                    )

        return len(warnings) == 0, warnings

    except Exception as e:
        logger.log_error(f"Error validating docker-compose.yml: {str(e)}")
        warnings.append(f"Error reading docker-compose.yml: {str(e)}")
        return False, warnings


def run_all_validations(project_path: Path, stack: str) -> bool:
    """
    Ejecuta todas las validaciones relevantes para el stack

    Args:
        project_path: Ruta al proyecto activo
        stack: Tipo de stack ('springboot-vue', 'laravel-vue')

    Returns:
        True si todas las validaciones pasaron
    """
    logger.header("Validating Configuration")

    all_valid = True

    if stack == 'springboot-vue':
        logger.step("Validating SpringBoot and nginx port configuration")

        is_valid, warnings = validate_springboot_nginx_ports(project_path)

        if is_valid:
            logger.success("Port configuration is valid")
        else:
            all_valid = False
            logger.error("Port configuration validation failed:")
            for warning in warnings:
                logger.warning(f"  • {warning}")

    elif stack == 'laravel-vue':
        logger.step("Validating Laravel and nginx configuration")

        is_valid, warnings = validate_laravel_nginx_ports(project_path)

        if is_valid:
            logger.success("Nginx configuration is valid")
        else:
            all_valid = False
            logger.error("Nginx configuration validation failed:")
            for warning in warnings:
                logger.warning(f"  • {warning}")

    logger.print()

    return all_valid
