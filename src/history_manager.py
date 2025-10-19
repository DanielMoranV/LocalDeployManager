"""
Gestión de historial de deploys
Registra y muestra información de deploys realizados
"""

import json
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

from .logger import logger
from .utils import get_active_project_path, load_json_file, save_json_file


class HistoryManager:
    """Manager para historial de deploys"""

    def __init__(self, project_path: Optional[Path] = None):
        """
        Inicializa el HistoryManager

        Args:
            project_path: Path del proyecto (usa proyecto activo si es None)
        """
        if project_path is None:
            self.project_path = get_active_project_path()
        else:
            self.project_path = Path(project_path)

        self.history_file = self.project_path / "deploy-history.json"

    def load_history(self) -> List[Dict]:
        """
        Carga el historial de deploys

        Returns:
            Lista de deploys
        """
        if not self.history_file.exists():
            return []

        try:
            return load_json_file(self.history_file)
        except Exception:
            return []

    def save_history(self, history: List[Dict]) -> bool:
        """
        Guarda el historial

        Args:
            history: Lista de deploys

        Returns:
            True si exitoso
        """
        try:
            return save_json_file(self.history_file, history)
        except Exception as e:
            logger.log_debug(f"Error saving history: {str(e)}")
            return False

    def add_deploy(
        self,
        deploy_type: str,
        success: bool,
        duration: float,
        backend_commit: Optional[str] = None,
        frontend_commit: Optional[str] = None,
        options: Optional[Dict] = None,
        error: Optional[str] = None
    ) -> str:
        """
        Registra un nuevo deploy

        Args:
            deploy_type: Tipo de deploy ('deploy', 'init', etc.)
            success: Si el deploy fue exitoso
            duration: Duración en segundos
            backend_commit: Commit hash del backend
            frontend_commit: Commit hash del frontend
            options: Opciones usadas en el deploy
            error: Mensaje de error si hubo falla

        Returns:
            ID del deploy
        """
        try:
            history = self.load_history()

            # Generar ID
            deploy_id = len(history) + 1

            deploy_entry = {
                "id": deploy_id,
                "type": deploy_type,
                "timestamp": datetime.now().isoformat(),
                "success": success,
                "duration": round(duration, 2),
                "commits": {
                    "backend": backend_commit,
                    "frontend": frontend_commit
                },
                "options": options or {},
                "error": error
            }

            history.append(deploy_entry)
            self.save_history(history)

            return str(deploy_id)

        except Exception as e:
            logger.log_debug(f"Error adding deploy to history: {str(e)}")
            return "unknown"

    def get_deploy(self, deploy_id: int) -> Optional[Dict]:
        """
        Obtiene un deploy específico

        Args:
            deploy_id: ID del deploy

        Returns:
            Dict con info del deploy o None
        """
        history = self.load_history()

        for deploy in history:
            if deploy.get('id') == deploy_id:
                return deploy

        return None

    def get_latest_deploy(self) -> Optional[Dict]:
        """
        Obtiene el último deploy

        Returns:
            Dict con info del deploy o None
        """
        history = self.load_history()

        if not history:
            return None

        return history[-1]

    def get_successful_deploys_count(self) -> int:
        """
        Cuenta deploys exitosos

        Returns:
            Cantidad de deploys exitosos
        """
        history = self.load_history()
        return sum(1 for d in history if d.get('success', False))

    def get_failed_deploys_count(self) -> int:
        """
        Cuenta deploys fallidos

        Returns:
            Cantidad de deploys fallidos
        """
        history = self.load_history()
        return sum(1 for d in history if not d.get('success', False))

    def cleanup_old_entries(self, keep_count: int = 50) -> int:
        """
        Elimina entradas antiguas del historial

        Args:
            keep_count: Cantidad de entradas a mantener

        Returns:
            Cantidad de entradas eliminadas
        """
        try:
            history = self.load_history()

            if len(history) <= keep_count:
                return 0

            # Mantener solo las últimas
            new_history = history[-keep_count:]

            # Reindexar IDs
            for i, entry in enumerate(new_history, start=1):
                entry['id'] = i

            self.save_history(new_history)

            return len(history) - len(new_history)

        except Exception:
            return 0


# Helper functions

def add_deploy_to_history(
    deploy_type: str,
    success: bool,
    duration: float,
    backend_commit: Optional[str] = None,
    frontend_commit: Optional[str] = None,
    options: Optional[Dict] = None,
    error: Optional[str] = None
) -> str:
    """
    Helper para registrar un deploy

    Args:
        deploy_type: Tipo de deploy
        success: Si fue exitoso
        duration: Duración en segundos
        backend_commit: Commit del backend
        frontend_commit: Commit del frontend
        options: Opciones del deploy
        error: Mensaje de error

    Returns:
        ID del deploy
    """
    try:
        manager = HistoryManager()
        return manager.add_deploy(
            deploy_type, success, duration,
            backend_commit, frontend_commit,
            options, error
        )
    except Exception:
        return "unknown"


def get_latest_deploy() -> Optional[Dict]:
    """
    Helper para obtener el último deploy

    Returns:
        Dict con info del deploy
    """
    try:
        manager = HistoryManager()
        return manager.get_latest_deploy()
    except Exception:
        return None


def get_deploy_history() -> List[Dict]:
    """
    Helper para obtener todo el historial

    Returns:
        Lista de deploys
    """
    try:
        manager = HistoryManager()
        return manager.load_history()
    except Exception:
        return []
