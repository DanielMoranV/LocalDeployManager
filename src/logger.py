"""
Sistema de logging para LDM
Maneja tanto output de consola (Rich) como logs a archivo
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint


class LDMLogger:
    """Logger singleton para el sistema"""

    _instance: Optional['LDMLogger'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.console = Console()
            self.log_dir = Path.home() / "local-deployer" / "logs"
            self.log_dir.mkdir(parents=True, exist_ok=True)

            # Configurar logging a archivo
            self.setup_file_logging()
            self.initialized = True

    def setup_file_logging(self, level: str = "INFO"):
        """Configura el logging a archivo"""
        log_file = self.log_dir / "deployer.log"

        # Formato para archivo
        file_formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Handler para archivo con rotación
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(getattr(logging, level))

        # Handler para consola con Rich
        console_handler = RichHandler(
            console=self.console,
            show_time=False,
            show_path=False,
            markup=True
        )
        console_handler.setLevel(logging.WARNING)  # Solo warnings y errores en consola

        # Configurar logger root
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        # Logger específico para LDM
        self.logger = logging.getLogger('LDM')

    # === Métodos para mensajes de consola ===

    def success(self, message: str):
        """Mensaje de éxito con checkmark"""
        self.console.print(f"[green]✓[/green] {message}")
        self.logger.info(f"SUCCESS: {message}")

    def error(self, message: str):
        """Mensaje de error"""
        self.console.print(f"[red]✗[/red] {message}", style="bold red")
        self.logger.error(message)

    def warning(self, message: str):
        """Mensaje de advertencia"""
        self.console.print(f"[yellow]⚠[/yellow]  {message}", style="yellow")
        self.logger.warning(message)

    def info(self, message: str):
        """Mensaje informativo"""
        self.console.print(f"[blue]ℹ[/blue]  {message}")
        self.logger.info(message)

    def step(self, message: str):
        """Paso en un proceso"""
        self.console.print(f"[cyan]▶[/cyan] {message}", style="cyan")
        self.logger.info(f"STEP: {message}")

    def header(self, title: str):
        """Header para secciones"""
        self.console.print()
        self.console.rule(f"[bold blue]{title}[/bold blue]")
        self.console.print()

    def panel(self, content: str, title: str = "", style: str = "blue"):
        """Panel con contenido"""
        panel = Panel(content, title=title, border_style=style)
        self.console.print(panel)

    def table(self, title: str, columns: list, rows: list):
        """Muestra una tabla"""
        table = Table(title=title, show_header=True, header_style="bold cyan")

        for col in columns:
            table.add_column(col)

        for row in rows:
            table.add_row(*row)

        self.console.print(table)

    def progress(self, description: str = "Working..."):
        """Crea una barra de progreso"""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        )

    def spinner(self, text: str):
        """Spinner simple para tareas sin progreso conocido"""
        return self.console.status(f"[cyan]{text}...", spinner="dots")

    def print(self, *args, **kwargs):
        """Print directo a consola"""
        self.console.print(*args, **kwargs)

    def print_config(self, config: dict, title: str = "Configuration"):
        """Imprime configuración de forma legible"""
        table = Table(title=title, show_header=True, header_style="bold cyan")
        table.add_column("Key", style="yellow")
        table.add_column("Value", style="green")

        for key, value in config.items():
            # Ocultar passwords
            if 'password' in key.lower() or 'secret' in key.lower():
                value = "********"
            table.add_row(str(key), str(value))

        self.console.print(table)

    def print_services_status(self, services: dict):
        """Imprime estado de servicios Docker"""
        table = Table(title="Services Status", show_header=True, header_style="bold cyan")
        table.add_column("Service", style="yellow")
        table.add_column("Status", style="white")
        table.add_column("Ports", style="blue")

        for service, info in services.items():
            status_style = "green" if info.get('running') else "red"
            status = "Running" if info.get('running') else "Stopped"
            ports = info.get('ports', 'N/A')

            table.add_row(
                service,
                f"[{status_style}]{status}[/{status_style}]",
                ports
            )

        self.console.print(table)

    # === Logging a archivo ===

    def log_debug(self, message: str):
        """Log debug (solo a archivo)"""
        self.logger.debug(message)

    def log_info(self, message: str):
        """Log info (solo a archivo)"""
        self.logger.info(message)

    def log_warning(self, message: str):
        """Log warning"""
        self.logger.warning(message)

    def log_error(self, message: str):
        """Log error"""
        self.logger.error(message)

    def log_exception(self, exc: Exception):
        """Log excepción con traceback"""
        self.logger.exception(f"Exception occurred: {str(exc)}")


# Instancia global
logger = LDMLogger()


# === Decorador para logging de funciones ===

def log_function(func):
    """Decorador para loguear entrada/salida de funciones"""
    def wrapper(*args, **kwargs):
        logger.log_debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.log_debug(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.log_error(f"{func.__name__} failed: {str(e)}")
            raise
    return wrapper
