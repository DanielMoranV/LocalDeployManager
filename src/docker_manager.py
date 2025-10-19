"""
Gestión de Docker y Docker Compose
Maneja contenedores, imágenes, redes, volúmenes, compose, etc.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import docker
from docker.errors import DockerException, APIError, NotFound
import yaml

from .logger import logger


class DockerManager:
    """Manager para operaciones Docker"""

    def __init__(self, compose_file: Optional[Path] = None):
        """
        Inicializa el DockerManager

        Args:
            compose_file: Path al docker-compose.yml
        """
        self.compose_file = Path(compose_file) if compose_file else None
        self.client = None

        # Detectar comando de Docker Compose (v1 vs v2)
        self.compose_cmd = self._detect_compose_command()

        try:
            self.client = docker.from_env()
            logger.log_debug("Docker client initialized")
        except DockerException as e:
            logger.log_error(f"Failed to initialize Docker client: {str(e)}")

    def _detect_compose_command(self) -> List[str]:
        """
        Detecta qué comando de Docker Compose usar

        Returns:
            Lista con el comando a usar (['docker', 'compose'] o ['docker-compose'])
        """
        # Intentar docker compose (v2, integrado)
        try:
            result = subprocess.run(
                ['docker', 'compose', 'version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.log_debug("Using Docker Compose v2 (docker compose)")
                return ['docker', 'compose']
        except Exception:
            pass

        # Intentar docker-compose (v1, standalone)
        try:
            result = subprocess.run(
                ['docker-compose', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.log_debug("Using Docker Compose v1 (docker-compose)")
                return ['docker-compose']
        except Exception:
            pass

        # Default a v2 (más moderno)
        return ['docker', 'compose']

    def is_docker_running(self) -> bool:
        """
        Verifica si Docker está corriendo

        Returns:
            True si Docker está disponible
        """
        try:
            if self.client:
                self.client.ping()
                return True
            return False
        except Exception:
            return False

    def get_docker_version(self) -> Optional[Dict]:
        """
        Obtiene versión de Docker

        Returns:
            Dict con info de versión o None
        """
        try:
            if self.client:
                return self.client.version()
            return None
        except Exception as e:
            logger.log_error(f"Error getting Docker version: {str(e)}")
            return None

    # === Docker Compose Operations ===

    def compose_up(
        self,
        detached: bool = True,
        build: bool = False,
        force_recreate: bool = False
    ) -> bool:
        """
        Ejecuta docker-compose up

        Args:
            detached: Ejecutar en background (-d)
            build: Rebuild de imágenes (--build)
            force_recreate: Forzar recreación (--force-recreate)

        Returns:
            True si exitoso
        """
        if not self.compose_file or not self.compose_file.exists():
            logger.error(f"docker-compose.yml not found at {self.compose_file}")
            return False

        try:
            cmd = self.compose_cmd + ['-f', str(self.compose_file), 'up']

            if detached:
                cmd.append('-d')
            if build:
                cmd.append('--build')
            if force_recreate:
                cmd.append('--force-recreate')

            logger.step("Starting Docker Compose")
            logger.info(f"Command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                cwd=self.compose_file.parent,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                logger.success("Docker Compose up completed")
                if result.stdout:
                    logger.log_debug(f"Output: {result.stdout}")
                return True
            else:
                logger.error(f"Docker Compose up failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error running docker-compose up: {str(e)}")
            logger.log_exception(e)
            return False

    def compose_down(self, remove_volumes: bool = False) -> bool:
        """
        Ejecuta docker-compose down

        Args:
            remove_volumes: Eliminar volúmenes (-v)

        Returns:
            True si exitoso
        """
        if not self.compose_file or not self.compose_file.exists():
            logger.error(f"docker-compose.yml not found at {self.compose_file}")
            return False

        try:
            cmd = self.compose_cmd + ['-f', str(self.compose_file), 'down']

            if remove_volumes:
                cmd.append('-v')

            logger.step("Stopping Docker Compose")

            result = subprocess.run(
                cmd,
                cwd=self.compose_file.parent,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                logger.success("Docker Compose down completed")
                return True
            else:
                logger.error(f"Docker Compose down failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error running docker-compose down: {str(e)}")
            logger.log_exception(e)
            return False

    def compose_restart(self, services: Optional[List[str]] = None) -> bool:
        """
        Reinicia servicios de Docker Compose

        Args:
            services: Lista de servicios a reiniciar (None = todos)

        Returns:
            True si exitoso
        """
        if not self.compose_file or not self.compose_file.exists():
            logger.error(f"docker-compose.yml not found at {self.compose_file}")
            return False

        try:
            cmd = self.compose_cmd + ['-f', str(self.compose_file), 'restart']

            if services:
                cmd.extend(services)
                logger.step(f"Restarting services: {', '.join(services)}")
            else:
                logger.step("Restarting all services")

            result = subprocess.run(
                cmd,
                cwd=self.compose_file.parent,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                logger.success("Services restarted")
                return True
            else:
                logger.error(f"Restart failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error restarting services: {str(e)}")
            logger.log_exception(e)
            return False

    def compose_build(self, services: Optional[List[str]] = None, no_cache: bool = False) -> bool:
        """
        Build de servicios Docker Compose

        Args:
            services: Lista de servicios a buildear (None = todos)
            no_cache: No usar cache (--no-cache)

        Returns:
            True si exitoso
        """
        if not self.compose_file or not self.compose_file.exists():
            logger.error(f"docker-compose.yml not found at {self.compose_file}")
            return False

        try:
            cmd = self.compose_cmd + ['-f', str(self.compose_file), 'build']

            if no_cache:
                cmd.append('--no-cache')

            if services:
                cmd.extend(services)

            logger.step("Building Docker images")

            result = subprocess.run(
                cmd,
                cwd=self.compose_file.parent,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                logger.success("Build completed")
                return True
            else:
                logger.error(f"Build failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error building: {str(e)}")
            logger.log_exception(e)
            return False

    def compose_ps(self) -> Optional[List[Dict]]:
        """
        Lista servicios de Docker Compose

        Returns:
            Lista de servicios con su info o None
        """
        if not self.compose_file or not self.compose_file.exists():
            return None

        try:
            cmd = self.compose_cmd + ['-f', str(self.compose_file), 'ps', '--format', 'json']

            result = subprocess.run(
                cmd,
                cwd=self.compose_file.parent,
                capture_output=True,
                text=True
            )

            if result.returncode == 0 and result.stdout:
                import json
                # docker-compose ps --format json retorna líneas JSON
                services = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        services.append(json.loads(line))
                return services
            return []

        except Exception as e:
            logger.log_error(f"Error getting compose services: {str(e)}")
            return None

    def compose_logs(
        self,
        service: Optional[str] = None,
        follow: bool = False,
        tail: int = 100
    ) -> bool:
        """
        Muestra logs de servicios

        Args:
            service: Servicio específico (None = todos)
            follow: Seguir logs en tiempo real
            tail: Número de líneas a mostrar

        Returns:
            True si exitoso
        """
        if not self.compose_file or not self.compose_file.exists():
            logger.error(f"docker-compose.yml not found at {self.compose_file}")
            return False

        try:
            cmd = self.compose_cmd + ['-f', str(self.compose_file), 'logs', f'--tail={tail}']

            if follow:
                cmd.append('-f')

            if service:
                cmd.append(service)

            logger.info(f"Showing logs for {service or 'all services'}")

            # Ejecutar sin captura para que se muestre en tiempo real
            result = subprocess.run(
                cmd,
                cwd=self.compose_file.parent
            )

            return result.returncode == 0

        except Exception as e:
            logger.error(f"Error showing logs: {str(e)}")
            logger.log_exception(e)
            return False

    def compose_exec(self, service: str, command: List[str]) -> Tuple[bool, str]:
        """
        Ejecuta un comando en un servicio

        Args:
            service: Nombre del servicio
            command: Lista con el comando a ejecutar

        Returns:
            Tupla (success, output)
        """
        if not self.compose_file or not self.compose_file.exists():
            return False, "docker-compose.yml not found"

        try:
            cmd = self.compose_cmd + ['-f', str(self.compose_file), 'exec', '-T', service] + command

            result = subprocess.run(
                cmd,
                cwd=self.compose_file.parent,
                capture_output=True,
                text=True
            )

            return result.returncode == 0, result.stdout or result.stderr

        except Exception as e:
            return False, str(e)

    # === Container Operations ===

    def get_container(self, name: str):
        """
        Obtiene un contenedor por nombre

        Args:
            name: Nombre del contenedor

        Returns:
            Container object o None
        """
        try:
            if self.client:
                return self.client.containers.get(name)
            return None
        except NotFound:
            return None
        except Exception as e:
            logger.log_error(f"Error getting container {name}: {str(e)}")
            return None

    def get_container_status(self, name: str) -> Optional[str]:
        """
        Obtiene el estado de un contenedor

        Args:
            name: Nombre del contenedor

        Returns:
            Estado ('running', 'exited', etc.) o None
        """
        container = self.get_container(name)
        if container:
            return container.status
        return None

    def is_container_running(self, name: str) -> bool:
        """
        Verifica si un contenedor está corriendo

        Args:
            name: Nombre del contenedor

        Returns:
            True si está corriendo
        """
        status = self.get_container_status(name)
        return status == 'running'

    def get_container_logs(self, name: str, tail: int = 100) -> Optional[str]:
        """
        Obtiene logs de un contenedor

        Args:
            name: Nombre del contenedor
            tail: Líneas a obtener

        Returns:
            Logs como string o None
        """
        container = self.get_container(name)
        if container:
            try:
                logs = container.logs(tail=tail, timestamps=True)
                return logs.decode('utf-8')
            except Exception as e:
                logger.log_error(f"Error getting logs: {str(e)}")
                return None
        return None

    def container_health(self, name: str) -> Optional[str]:
        """
        Obtiene el health status de un contenedor

        Args:
            name: Nombre del contenedor

        Returns:
            Health status ('healthy', 'unhealthy', etc.) o None
        """
        container = self.get_container(name)
        if container:
            try:
                health = container.attrs.get('State', {}).get('Health', {})
                return health.get('Status')
            except Exception:
                return None
        return None

    # === Network Operations ===

    def create_network(self, name: str, driver: str = "bridge") -> bool:
        """
        Crea una red Docker

        Args:
            name: Nombre de la red
            driver: Driver de red (default: bridge)

        Returns:
            True si exitoso
        """
        try:
            if not self.client:
                return False

            # Verificar si ya existe
            try:
                self.client.networks.get(name)
                logger.info(f"Network {name} already exists")
                return True
            except NotFound:
                pass

            logger.step(f"Creating Docker network: {name}")
            self.client.networks.create(name, driver=driver)
            logger.success(f"Network {name} created")
            return True

        except Exception as e:
            logger.error(f"Error creating network: {str(e)}")
            logger.log_exception(e)
            return False

    def remove_network(self, name: str) -> bool:
        """
        Elimina una red Docker

        Args:
            name: Nombre de la red

        Returns:
            True si exitoso
        """
        try:
            if not self.client:
                return False

            network = self.client.networks.get(name)
            logger.step(f"Removing network: {name}")
            network.remove()
            logger.success(f"Network {name} removed")
            return True

        except NotFound:
            logger.info(f"Network {name} not found")
            return True
        except Exception as e:
            logger.error(f"Error removing network: {str(e)}")
            logger.log_exception(e)
            return False

    # === Volume Operations ===

    def create_volume(self, name: str) -> bool:
        """
        Crea un volumen Docker

        Args:
            name: Nombre del volumen

        Returns:
            True si exitoso
        """
        try:
            if not self.client:
                return False

            # Verificar si ya existe
            try:
                self.client.volumes.get(name)
                logger.info(f"Volume {name} already exists")
                return True
            except NotFound:
                pass

            logger.step(f"Creating Docker volume: {name}")
            self.client.volumes.create(name)
            logger.success(f"Volume {name} created")
            return True

        except Exception as e:
            logger.error(f"Error creating volume: {str(e)}")
            logger.log_exception(e)
            return False

    def remove_volume(self, name: str) -> bool:
        """
        Elimina un volumen Docker

        Args:
            name: Nombre del volumen

        Returns:
            True si exitoso
        """
        try:
            if not self.client:
                return False

            volume = self.client.volumes.get(name)
            logger.step(f"Removing volume: {name}")
            volume.remove()
            logger.success(f"Volume {name} removed")
            return True

        except NotFound:
            logger.info(f"Volume {name} not found")
            return True
        except Exception as e:
            logger.error(f"Error removing volume: {str(e)}")
            logger.log_exception(e)
            return False

    # === Utility Functions ===

    def get_services_status(self) -> Dict[str, Dict]:
        """
        Obtiene estado de todos los servicios del compose

        Returns:
            Dict con info de cada servicio
        """
        services_info = {}
        services = self.compose_ps()

        if not services:
            return {}

        for service in services:
            name = service.get('Name', 'unknown')
            services_info[name] = {
                'name': name,
                'state': service.get('State', 'unknown'),
                'status': service.get('Status', 'unknown'),
                'ports': service.get('Publishers', []),
                'running': service.get('State') == 'running'
            }

        return services_info

    def wait_for_healthy(self, container_name: str, timeout: int = 60) -> bool:
        """
        Espera a que un contenedor esté healthy

        Args:
            container_name: Nombre del contenedor
            timeout: Timeout en segundos

        Returns:
            True si está healthy
        """
        import time

        logger.step(f"Waiting for {container_name} to be healthy...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            health = self.container_health(container_name)

            if health == 'healthy':
                logger.success(f"{container_name} is healthy")
                return True

            time.sleep(2)

        logger.warning(f"{container_name} did not become healthy within {timeout}s")
        return False


# Helper functions

def check_docker_installed() -> bool:
    """
    Verifica si Docker está instalado

    Returns:
        True si Docker está instalado
    """
    try:
        result = subprocess.run(
            ['docker', '--version'],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def check_docker_compose_installed() -> bool:
    """
    Verifica si docker-compose está instalado (v1 o v2)

    Returns:
        True si docker-compose está instalado
    """
    # Intentar docker compose (v2)
    try:
        result = subprocess.run(
            ['docker', 'compose', 'version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return True
    except Exception:
        pass

    # Intentar docker-compose (v1)
    try:
        result = subprocess.run(
            ['docker-compose', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def get_docker_info() -> Dict:
    """
    Obtiene información completa de Docker

    Returns:
        Dict con información de Docker
    """
    manager = DockerManager()

    return {
        'docker_installed': check_docker_installed(),
        'docker_compose_installed': check_docker_compose_installed(),
        'docker_running': manager.is_docker_running(),
        'docker_version': manager.get_docker_version()
    }
