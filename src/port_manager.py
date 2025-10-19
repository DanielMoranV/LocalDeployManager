"""
Gestión y verificación de puertos
Detecta puertos ocupados, sugiere alternativas, verifica disponibilidad
"""

import socket
import psutil
from typing import List, Dict, Tuple, Optional

from .logger import logger


class PortManager:
    """Manager para verificación y gestión de puertos"""

    def __init__(self):
        """Inicializa el PortManager"""
        pass

    def is_port_available(self, port: int, host: str = '0.0.0.0') -> bool:
        """
        Verifica si un puerto está disponible

        Args:
            port: Número de puerto a verificar
            host: Host a verificar (default: 0.0.0.0)

        Returns:
            True si el puerto está disponible, False si está ocupado
        """
        try:
            # Intentar crear un socket en el puerto
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
                return True
        except OSError:
            return False

    def get_process_using_port(self, port: int) -> Optional[Dict[str, any]]:
        """
        Obtiene información del proceso que está usando un puerto

        Args:
            port: Puerto a verificar

        Returns:
            Dict con info del proceso o None si no hay proceso
        """
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.port == port:
                try:
                    process = psutil.Process(conn.pid)
                    return {
                        'pid': conn.pid,
                        'name': process.name(),
                        'cmdline': ' '.join(process.cmdline()),
                        'status': conn.status,
                    }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    return {
                        'pid': conn.pid,
                        'name': 'Unknown',
                        'cmdline': 'Access Denied',
                        'status': conn.status,
                    }
        return None

    def check_ports(self, ports: List[int]) -> Dict[int, Dict[str, any]]:
        """
        Verifica el estado de múltiples puertos

        Args:
            ports: Lista de puertos a verificar

        Returns:
            Dict con estado de cada puerto
            {
                80: {'available': False, 'process': {...}},
                443: {'available': True, 'process': None}
            }
        """
        results = {}

        for port in ports:
            available = self.is_port_available(port)
            process_info = None if available else self.get_process_using_port(port)

            results[port] = {
                'available': available,
                'process': process_info
            }

        return results

    def suggest_alternative_port(self, desired_port: int, max_attempts: int = 10) -> Optional[int]:
        """
        Sugiere un puerto alternativo si el deseado está ocupado

        Args:
            desired_port: Puerto deseado
            max_attempts: Intentos máximos para encontrar puerto libre

        Returns:
            Puerto alternativo disponible o None
        """
        if self.is_port_available(desired_port):
            return desired_port

        # Intentar puertos incrementales
        for i in range(1, max_attempts + 1):
            alternative = desired_port + i
            if alternative > 65535:  # Max port number
                break

            if self.is_port_available(alternative):
                logger.log_info(f"Port {desired_port} occupied, suggesting {alternative}")
                return alternative

        return None

    def find_free_port_in_range(self, start: int, end: int) -> Optional[int]:
        """
        Encuentra el primer puerto libre en un rango

        Args:
            start: Puerto inicial
            end: Puerto final

        Returns:
            Primer puerto libre o None
        """
        for port in range(start, end + 1):
            if self.is_port_available(port):
                return port
        return None

    def get_default_ports(self, stack: str) -> Dict[str, int]:
        """
        Obtiene los puertos por defecto según el stack

        Args:
            stack: 'laravel-vue' o 'springboot-vue'

        Returns:
            Dict con puertos por defecto
        """
        base_ports = {
            'http': 80,
            'https': 443,
        }

        if stack == 'laravel-vue':
            base_ports['mysql'] = 3306
            base_ports['redis'] = 6379
        elif stack == 'springboot-vue':
            base_ports['postgres'] = 5432
            base_ports['redis'] = 6379
            base_ports['backend'] = 8080

        return base_ports

    def check_and_suggest_ports(self, desired_ports: Dict[str, int]) -> Tuple[Dict[str, int], List[str]]:
        """
        Verifica puertos deseados y sugiere alternativas si es necesario

        Args:
            desired_ports: Dict con puertos deseados {'http': 80, 'https': 443, ...}

        Returns:
            Tupla (puertos_finales, warnings)
        """
        final_ports = {}
        warnings = []

        for service, port in desired_ports.items():
            if self.is_port_available(port):
                final_ports[service] = port
                logger.log_debug(f"Port {port} ({service}) is available")
            else:
                # Buscar alternativa
                alternative = self.suggest_alternative_port(port)
                if alternative:
                    final_ports[service] = alternative
                    warnings.append(
                        f"Port {port} ({service}) is occupied. Using {alternative} instead."
                    )
                    logger.warning(f"Port {port} occupied, using {alternative} for {service}")
                else:
                    # No se encontró alternativa, usar el original y advertir
                    final_ports[service] = port
                    warnings.append(
                        f"Port {port} ({service}) is occupied and no alternative found. "
                        f"This may cause conflicts!"
                    )
                    logger.error(f"Port {port} occupied and no alternative found for {service}")

        return final_ports, warnings

    def display_port_status(self, ports: Dict[str, int]):
        """
        Muestra el estado de puertos en una tabla

        Args:
            ports: Dict con puertos a verificar {'service': port}
        """
        port_status = {}

        for service, port in ports.items():
            available = self.is_port_available(port)
            process = self.get_process_using_port(port) if not available else None

            port_status[service] = {
                'port': port,
                'available': available,
                'process': process
            }

        # Crear tabla
        from rich.table import Table

        table = Table(title="Port Status", show_header=True, header_style="bold cyan")
        table.add_column("Service", style="yellow", width=15)
        table.add_column("Port", style="blue", width=10)
        table.add_column("Status", width=12)
        table.add_column("Process", style="dim", width=30)

        for service, info in port_status.items():
            port = str(info['port'])
            status = "[green]Available[/green]" if info['available'] else "[red]Occupied[/red]"

            process_info = ""
            if info['process']:
                proc = info['process']
                process_info = f"{proc['name']} (PID: {proc['pid']})"

            table.add_row(service, port, status, process_info)

        logger.console.print(table)

    def get_common_service_ports(self) -> Dict[str, int]:
        """
        Retorna puertos comunes de servicios conocidos

        Returns:
            Dict con puertos de servicios comunes
        """
        return {
            'http': 80,
            'https': 443,
            'mysql': 3306,
            'postgres': 5432,
            'redis': 6379,
            'mongodb': 27017,
            'ssh': 22,
            'ftp': 21,
            'smtp': 25,
            'dns': 53,
        }

    def check_docker_ports(self) -> List[int]:
        """
        Obtiene lista de puertos usados por contenedores Docker

        Returns:
            Lista de puertos ocupados por Docker
        """
        docker_ports = []

        try:
            import docker
            client = docker.from_env()
            containers = client.containers.list()

            for container in containers:
                # Obtener puertos del contenedor
                ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
                for container_port, host_bindings in ports.items():
                    if host_bindings:
                        for binding in host_bindings:
                            if binding.get('HostPort'):
                                docker_ports.append(int(binding['HostPort']))

        except ImportError:
            logger.log_warning("Docker library not available for port checking")
        except Exception as e:
            logger.log_debug(f"Error checking Docker ports: {str(e)}")

        return docker_ports

    def validate_port_range(self, port: int) -> Tuple[bool, Optional[str]]:
        """
        Valida que un puerto esté en un rango válido

        Args:
            port: Puerto a validar

        Returns:
            Tupla (is_valid, error_message)
        """
        if port < 1 or port > 65535:
            return False, f"Port {port} is out of valid range (1-65535)"

        # Puertos privilegiados (1-1023) requieren permisos root en Linux
        if port < 1024:
            import platform
            if platform.system() == "Linux":
                # Verificar si estamos ejecutando como root
                import os
                if os.geteuid() != 0:
                    return False, (
                        f"Port {port} requires root privileges on Linux. "
                        f"Consider using a port >= 1024"
                    )

        return True, None

    def get_safe_ports_for_services(self, services: List[str]) -> Dict[str, int]:
        """
        Obtiene puertos seguros (no privilegiados) para servicios

        Args:
            services: Lista de servicios que necesitan puertos

        Returns:
            Dict con puertos asignados a cada servicio
        """
        # Rangos seguros para diferentes servicios
        safe_ranges = {
            'http': (8080, 8090),
            'https': (8443, 8453),
            'mysql': (3306, 3316),
            'postgres': (5432, 5442),
            'redis': (6379, 6389),
            'backend': (8000, 8010),
        }

        assigned_ports = {}

        for service in services:
            if service in safe_ranges:
                start, end = safe_ranges[service]
                port = self.find_free_port_in_range(start, end)
                if port:
                    assigned_ports[service] = port
                else:
                    # Fallback al primer puerto del rango
                    assigned_ports[service] = start
            else:
                # Servicio desconocido, usar rango genérico
                port = self.find_free_port_in_range(8000, 9000)
                assigned_ports[service] = port if port else 8000

        return assigned_ports


# Helper functions

def check_single_port(port: int) -> bool:
    """
    Helper rápido para verificar un solo puerto

    Args:
        port: Puerto a verificar

    Returns:
        True si está disponible
    """
    manager = PortManager()
    return manager.is_port_available(port)


def get_available_ports(stack: str) -> Dict[str, int]:
    """
    Helper para obtener puertos disponibles según stack

    Args:
        stack: 'laravel-vue' o 'springboot-vue'

    Returns:
        Dict con puertos disponibles
    """
    manager = PortManager()
    desired_ports = manager.get_default_ports(stack)
    final_ports, warnings = manager.check_and_suggest_ports(desired_ports)

    # Mostrar warnings si hay
    for warning in warnings:
        logger.warning(warning)

    return final_ports
