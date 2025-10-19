"""
Gestión de backups de proyectos
Maneja creación, listado y restauración de backups
"""

import os
import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from datetime import datetime

from .logger import logger
from .utils import get_base_path, load_json_file, save_json_file
from .models import BackupMetadata


class BackupManager:
    """Manager para backups de proyectos"""

    def __init__(self, backups_dir: Optional[Path] = None):
        """
        Inicializa el BackupManager

        Args:
            backups_dir: Directorio donde guardar backups
        """
        if backups_dir is None:
            self.backups_dir = get_base_path() / "backups"
        else:
            self.backups_dir = Path(backups_dir)

        # Crear directorio si no existe
        self.backups_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(
        self,
        project_path: Path,
        project_config: Dict,
        name: Optional[str] = None,
        include_db: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Crea un backup completo del proyecto

        Args:
            project_path: Path del proyecto activo
            project_config: Configuración del proyecto
            name: Nombre personalizado del backup
            include_db: Si incluir backup de base de datos

        Returns:
            Tupla (success, backup_id)
        """
        try:
            # Generar ID del backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if name:
                backup_id = f"{timestamp}_{name}"
            else:
                backup_id = timestamp

            backup_path = self.backups_dir / backup_id
            backup_path.mkdir(parents=True, exist_ok=True)

            logger.header(f"Creating Backup: {backup_id}")

            # 1. Copiar archivos del proyecto
            logger.step("Backing up project files")

            # Backend
            backend_src = project_path / "backend"
            if backend_src.exists():
                backend_dst = backup_path / "backend"
                shutil.copytree(
                    backend_src,
                    backend_dst,
                    ignore=shutil.ignore_patterns(
                        'node_modules', 'vendor', '.git', 'storage/logs/*',
                        'bootstrap/cache/*', '.env', 'target', '.mvn'
                    )
                )
                logger.success("Backend files backed up")

            # Frontend
            frontend_src = project_path / "frontend"
            if frontend_src.exists():
                frontend_dst = backup_path / "frontend"
                shutil.copytree(
                    frontend_src,
                    frontend_dst,
                    ignore=shutil.ignore_patterns(
                        'node_modules', 'dist', '.git', '.env'
                    )
                )
                logger.success("Frontend files backed up")

            # 2. Copiar archivos de configuración
            logger.step("Backing up configuration files")

            config_files = [
                "docker-compose.yml",
                "nginx.conf",
                "Dockerfile.php",
                "Dockerfile.java",
                ".project-config.json",
                ".credentials.json"
            ]

            for config_file in config_files:
                src_file = project_path / config_file
                if src_file.exists():
                    shutil.copy2(src_file, backup_path / config_file)

            # Copiar .env del backend
            backend_env = project_path / "backend" / ".env"
            if backend_env.exists():
                shutil.copy2(backend_env, backup_path / "backend.env")

            logger.success("Configuration files backed up")

            # 3. Backup de base de datos
            db_backup_file = None
            if include_db:
                logger.step("Backing up database")
                db_success, db_file = self._backup_database(
                    project_config,
                    backup_path
                )
                if db_success:
                    db_backup_file = db_file
                    logger.success(f"Database backed up: {db_file}")
                else:
                    logger.warning("Database backup failed (continuing...)")

            # 4. Crear metadata
            logger.step("Creating backup metadata")
            metadata = self._create_metadata(
                backup_id=backup_id,
                project_config=project_config,
                project_path=project_path,
                db_backup_file=db_backup_file,
                custom_name=name
            )

            metadata_file = backup_path / "backup-metadata.json"
            save_json_file(metadata_file, metadata)
            logger.success("Metadata saved")

            # 5. Calcular tamaño
            total_size = self._get_directory_size(backup_path)
            size_mb = total_size / (1024 * 1024)

            logger.success(f"Backup created successfully: {backup_id}")
            logger.info(f"Location: {backup_path}")
            logger.info(f"Size: {size_mb:.2f} MB")

            return True, backup_id

        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            logger.log_exception(e)

            # Limpiar backup incompleto
            if backup_path.exists():
                shutil.rmtree(backup_path)

            return False, None

    def _backup_database(
        self,
        project_config: Dict,
        backup_path: Path
    ) -> Tuple[bool, Optional[str]]:
        """
        Realiza backup de la base de datos

        Args:
            project_config: Configuración del proyecto
            backup_path: Path donde guardar el backup

        Returns:
            Tupla (success, backup_filename)
        """
        try:
            stack = project_config.get('stack')
            db_config = project_config.get('database', {})

            container_prefix = project_config.get('name', 'ldm')

            if stack == 'laravel-vue':
                # MySQL backup
                container_name = f"{container_prefix}_mysql_1"
                db_name = db_config.get('database', 'laravel_db')
                db_user = 'root'
                db_password = db_config.get('root_password', 'root')

                backup_file = backup_path / "database_backup.sql"

                cmd = [
                    'docker', 'exec', container_name,
                    'mysqldump',
                    '-u', db_user,
                    f'-p{db_password}',
                    db_name
                ]

                with open(backup_file, 'w') as f:
                    result = subprocess.run(
                        cmd,
                        stdout=f,
                        stderr=subprocess.PIPE,
                        text=True
                    )

                if result.returncode == 0:
                    return True, "database_backup.sql"
                else:
                    logger.log_debug(f"mysqldump error: {result.stderr}")
                    return False, None

            elif stack == 'springboot-vue':
                # PostgreSQL backup
                container_name = f"{container_prefix}_postgres_1"
                db_name = db_config.get('database', 'springboot_db')
                db_user = db_config.get('username', 'postgres')

                backup_file = backup_path / "database_backup.sql"

                cmd = [
                    'docker', 'exec', container_name,
                    'pg_dump',
                    '-U', db_user,
                    db_name
                ]

                with open(backup_file, 'w') as f:
                    result = subprocess.run(
                        cmd,
                        stdout=f,
                        stderr=subprocess.PIPE,
                        text=True
                    )

                if result.returncode == 0:
                    return True, "database_backup.sql"
                else:
                    logger.log_debug(f"pg_dump error: {result.stderr}")
                    return False, None

            return False, None

        except Exception as e:
            logger.log_debug(f"Database backup error: {str(e)}")
            return False, None

    def _create_metadata(
        self,
        backup_id: str,
        project_config: Dict,
        project_path: Path,
        db_backup_file: Optional[str],
        custom_name: Optional[str]
    ) -> Dict:
        """
        Crea metadata del backup

        Args:
            backup_id: ID del backup
            project_config: Config del proyecto
            project_path: Path del proyecto
            db_backup_file: Nombre del archivo de DB backup
            custom_name: Nombre personalizado

        Returns:
            Dict con metadata
        """
        # Obtener commits actuales
        backend_commit = None
        frontend_commit = None

        try:
            from .git_manager import GitManager

            backend_path = project_path / "backend"
            if backend_path.exists():
                git_manager = GitManager(backend_path)
                backend_commit = git_manager.get_current_commit_short()

            frontend_path = project_path / "frontend"
            if frontend_path.exists():
                git_manager = GitManager(frontend_path)
                frontend_commit = git_manager.get_current_commit_short()
        except Exception:
            pass

        metadata = {
            "backup_id": backup_id,
            "custom_name": custom_name,
            "timestamp": datetime.now().isoformat(),
            "project": {
                "name": project_config.get('name'),
                "stack": project_config.get('stack'),
                "domain": project_config.get('domain')
            },
            "commits": {
                "backend": backend_commit,
                "frontend": frontend_commit
            },
            "database_backup": db_backup_file is not None,
            "database_backup_file": db_backup_file,
            "files_included": [
                "backend/",
                "frontend/",
                "docker-compose.yml",
                "nginx.conf",
                "backend.env"
            ]
        }

        return metadata

    def _get_directory_size(self, path: Path) -> int:
        """
        Calcula tamaño total de un directorio

        Args:
            path: Path del directorio

        Returns:
            Tamaño en bytes
        """
        total = 0
        try:
            for entry in os.scandir(path):
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat().st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += self._get_directory_size(Path(entry.path))
        except Exception:
            pass
        return total

    def list_backups(self) -> List[Dict]:
        """
        Lista todos los backups disponibles

        Returns:
            Lista de dicts con info de backups
        """
        backups = []

        try:
            if not self.backups_dir.exists():
                return backups

            for backup_dir in sorted(self.backups_dir.iterdir(), reverse=True):
                if not backup_dir.is_dir():
                    continue

                metadata_file = backup_dir / "backup-metadata.json"

                if metadata_file.exists():
                    metadata = load_json_file(metadata_file)

                    # Calcular tamaño
                    size_bytes = self._get_directory_size(backup_dir)
                    size_mb = size_bytes / (1024 * 1024)

                    metadata['size_mb'] = round(size_mb, 2)
                    metadata['path'] = str(backup_dir)

                    backups.append(metadata)
                else:
                    # Backup sin metadata (legacy o corrupto)
                    backups.append({
                        "backup_id": backup_dir.name,
                        "timestamp": None,
                        "project": {},
                        "size_mb": round(self._get_directory_size(backup_dir) / (1024 * 1024), 2),
                        "path": str(backup_dir),
                        "corrupted": True
                    })

        except Exception as e:
            logger.error(f"Error listing backups: {str(e)}")
            logger.log_exception(e)

        return backups

    def get_backup(self, backup_id: str) -> Optional[Dict]:
        """
        Obtiene información de un backup específico

        Args:
            backup_id: ID del backup

        Returns:
            Dict con info del backup o None
        """
        backup_path = self.backups_dir / backup_id

        if not backup_path.exists():
            return None

        metadata_file = backup_path / "backup-metadata.json"

        if not metadata_file.exists():
            return None

        metadata = load_json_file(metadata_file)
        metadata['path'] = str(backup_path)

        return metadata

    def restore_backup(
        self,
        backup_id: str,
        target_path: Path,
        restore_db: bool = True
    ) -> bool:
        """
        Restaura un backup

        Args:
            backup_id: ID del backup a restaurar
            target_path: Path donde restaurar
            restore_db: Si restaurar la base de datos

        Returns:
            True si exitoso
        """
        try:
            backup_path = self.backups_dir / backup_id

            if not backup_path.exists():
                logger.error(f"Backup not found: {backup_id}")
                return False

            metadata_file = backup_path / "backup-metadata.json"
            if not metadata_file.exists():
                logger.error("Backup metadata not found (corrupted backup)")
                return False

            metadata = load_json_file(metadata_file)

            logger.header(f"Restoring Backup: {backup_id}")

            # 1. Restaurar archivos del proyecto
            logger.step("Restoring project files")

            # Backend
            backend_src = backup_path / "backend"
            if backend_src.exists():
                backend_dst = target_path / "backend"
                if backend_dst.exists():
                    shutil.rmtree(backend_dst)
                shutil.copytree(backend_src, backend_dst)
                logger.success("Backend files restored")

            # Frontend
            frontend_src = backup_path / "frontend"
            if frontend_src.exists():
                frontend_dst = target_path / "frontend"
                if frontend_dst.exists():
                    shutil.rmtree(frontend_dst)
                shutil.copytree(frontend_src, frontend_dst)
                logger.success("Frontend files restored")

            # 2. Restaurar configuración
            logger.step("Restoring configuration files")

            config_files = [
                "docker-compose.yml",
                "nginx.conf",
                "Dockerfile.php",
                "Dockerfile.java",
                ".project-config.json",
                ".credentials.json"
            ]

            for config_file in config_files:
                src_file = backup_path / config_file
                if src_file.exists():
                    shutil.copy2(src_file, target_path / config_file)

            # Restaurar .env
            backend_env_src = backup_path / "backend.env"
            if backend_env_src.exists():
                backend_env_dst = target_path / "backend" / ".env"
                shutil.copy2(backend_env_src, backend_env_dst)

            logger.success("Configuration files restored")

            # 3. Restaurar base de datos
            if restore_db and metadata.get('database_backup'):
                logger.step("Restoring database")

                db_file = backup_path / metadata.get('database_backup_file', 'database_backup.sql')

                if db_file.exists():
                    db_success = self._restore_database(
                        metadata['project'],
                        db_file,
                        target_path
                    )

                    if db_success:
                        logger.success("Database restored")
                    else:
                        logger.warning("Database restore failed")
                else:
                    logger.warning("Database backup file not found")

            logger.success(f"Backup restored successfully")
            logger.info(f"Project: {metadata['project']['name']}")
            logger.info(f"Stack: {metadata['project']['stack']}")

            if metadata.get('commits', {}).get('backend'):
                logger.info(f"Backend commit: {metadata['commits']['backend']}")
            if metadata.get('commits', {}).get('frontend'):
                logger.info(f"Frontend commit: {metadata['commits']['frontend']}")

            return True

        except Exception as e:
            logger.error(f"Error restoring backup: {str(e)}")
            logger.log_exception(e)
            return False

    def _restore_database(
        self,
        project_info: Dict,
        db_backup_file: Path,
        project_path: Path
    ) -> bool:
        """
        Restaura base de datos desde backup

        Args:
            project_info: Info del proyecto
            db_backup_file: Path al archivo SQL
            project_path: Path del proyecto

        Returns:
            True si exitoso
        """
        try:
            stack = project_info.get('stack')

            # Leer configuración del proyecto
            config_file = project_path / ".project-config.json"
            if not config_file.exists():
                return False

            project_config = load_json_file(config_file)
            db_config = project_config.get('database', {})
            container_prefix = project_config.get('name', 'ldm')

            if stack == 'laravel-vue':
                # MySQL restore
                container_name = f"{container_prefix}_mysql_1"
                db_name = db_config.get('database', 'laravel_db')
                db_user = 'root'
                db_password = db_config.get('root_password', 'root')

                # Copiar archivo SQL al contenedor
                subprocess.run(
                    ['docker', 'cp', str(db_backup_file), f"{container_name}:/tmp/restore.sql"],
                    check=True
                )

                # Restaurar
                cmd = [
                    'docker', 'exec', container_name,
                    'mysql',
                    '-u', db_user,
                    f'-p{db_password}',
                    db_name,
                    '-e', 'source /tmp/restore.sql'
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)
                return result.returncode == 0

            elif stack == 'springboot-vue':
                # PostgreSQL restore
                container_name = f"{container_prefix}_postgres_1"
                db_name = db_config.get('database', 'springboot_db')
                db_user = db_config.get('username', 'postgres')

                # Copiar archivo SQL al contenedor
                subprocess.run(
                    ['docker', 'cp', str(db_backup_file), f"{container_name}:/tmp/restore.sql"],
                    check=True
                )

                # Restaurar
                cmd = [
                    'docker', 'exec', container_name,
                    'psql',
                    '-U', db_user,
                    '-d', db_name,
                    '-f', '/tmp/restore.sql'
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)
                return result.returncode == 0

            return False

        except Exception as e:
            logger.log_debug(f"Database restore error: {str(e)}")
            return False

    def delete_backup(self, backup_id: str) -> bool:
        """
        Elimina un backup

        Args:
            backup_id: ID del backup

        Returns:
            True si exitoso
        """
        try:
            backup_path = self.backups_dir / backup_id

            if not backup_path.exists():
                logger.error(f"Backup not found: {backup_id}")
                return False

            shutil.rmtree(backup_path)
            logger.success(f"Backup deleted: {backup_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting backup: {str(e)}")
            logger.log_exception(e)
            return False

    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """
        Elimina backups antiguos, manteniendo solo los más recientes

        Args:
            keep_count: Cantidad de backups a mantener

        Returns:
            Cantidad de backups eliminados
        """
        try:
            backups = self.list_backups()

            if len(backups) <= keep_count:
                return 0

            # Ordenar por timestamp (más reciente primero)
            backups.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

            # Eliminar los más antiguos
            deleted_count = 0
            for backup in backups[keep_count:]:
                if self.delete_backup(backup['backup_id']):
                    deleted_count += 1

            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up backups: {str(e)}")
            return 0


# Helper functions

def create_project_backup(
    project_path: Path,
    project_config: Dict,
    name: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Helper para crear un backup del proyecto

    Args:
        project_path: Path del proyecto
        project_config: Configuración del proyecto
        name: Nombre personalizado

    Returns:
        Tupla (success, backup_id)
    """
    manager = BackupManager()
    return manager.create_backup(project_path, project_config, name)


def list_project_backups() -> List[Dict]:
    """
    Helper para listar backups

    Returns:
        Lista de backups
    """
    manager = BackupManager()
    return manager.list_backups()


def restore_project_backup(
    backup_id: str,
    target_path: Path,
    restore_db: bool = True
) -> bool:
    """
    Helper para restaurar un backup

    Args:
        backup_id: ID del backup
        target_path: Path de destino
        restore_db: Si restaurar DB

    Returns:
        True si exitoso
    """
    manager = BackupManager()
    return manager.restore_backup(backup_id, target_path, restore_db)
