"""
Gestión de operaciones Git
Maneja clonado, pull, commits, branches, etc.
"""

import os
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from git import Repo, GitCommandError, InvalidGitRepositoryError
from git.remote import RemoteProgress

from .logger import logger


class GitProgressPrinter(RemoteProgress):
    """Progress printer para operaciones Git con Rich"""

    def __init__(self):
        super().__init__()
        self.progress = None

    def update(self, op_code, cur_count, max_count=None, message=''):
        """Actualiza el progreso"""
        if max_count and self.progress:
            percentage = (cur_count / max_count) * 100 if max_count else 0
            self.progress.update(self.task, completed=percentage)


class GitManager:
    """Manager para operaciones Git"""

    def __init__(self, repo_path: Optional[Path] = None):
        """
        Inicializa el GitManager

        Args:
            repo_path: Path al repositorio. Si es None, no se carga repo.
        """
        self.repo_path = Path(repo_path) if repo_path else None
        self.repo = None

        if self.repo_path and self.repo_path.exists():
            try:
                self.repo = Repo(str(self.repo_path))
            except InvalidGitRepositoryError:
                logger.log_warning(f"{self.repo_path} is not a Git repository")

    def clone(
        self,
        repo_url: str,
        destination: Path,
        branch: str = "main",
        depth: Optional[int] = None
    ) -> bool:
        """
        Clona un repositorio

        Args:
            repo_url: URL del repositorio
            destination: Path de destino
            branch: Branch a clonar (default: main)
            depth: Profundidad del clone (None = completo)

        Returns:
            True si exitoso, False si falla
        """
        try:
            logger.step(f"Cloning repository from {repo_url}")
            logger.info(f"Branch: {branch}")
            logger.info(f"Destination: {destination}")

            # Crear directorio padre si no existe
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Opciones de clonado
            clone_kwargs = {
                'branch': branch,
                'progress': GitProgressPrinter()
            }

            if depth:
                clone_kwargs['depth'] = depth

            # Clonar
            with logger.spinner(f"Cloning {repo_url}"):
                self.repo = Repo.clone_from(
                    repo_url,
                    str(destination),
                    **clone_kwargs
                )

            self.repo_path = destination
            logger.success(f"Repository cloned successfully to {destination}")
            return True

        except GitCommandError as e:
            logger.error(f"Git clone failed: {str(e)}")
            logger.log_exception(e)
            return False

        except Exception as e:
            logger.error(f"Unexpected error during clone: {str(e)}")
            logger.log_exception(e)
            return False

    def pull(self, remote: str = "origin", branch: Optional[str] = None) -> bool:
        """
        Hace pull de cambios del remoto

        Args:
            remote: Nombre del remoto (default: origin)
            branch: Branch específico (None = branch actual)

        Returns:
            True si exitoso, False si falla
        """
        if not self.repo:
            logger.error("No repository loaded")
            return False

        try:
            current_branch = self.repo.active_branch.name
            target_branch = branch or current_branch

            logger.step(f"Pulling changes from {remote}/{target_branch}")

            # Hacer pull
            with logger.spinner(f"Pulling from {remote}"):
                pull_info = self.repo.remotes[remote].pull(target_branch)

            # Verificar resultado
            if pull_info:
                info = pull_info[0]
                if info.flags & info.ERROR:
                    logger.error(f"Pull failed: {info.note}")
                    return False

                if info.flags & info.HEAD_UPTODATE:
                    logger.info("Already up to date")
                else:
                    logger.success(f"Pull completed: {info.commit}")

            return True

        except GitCommandError as e:
            logger.error(f"Git pull failed: {str(e)}")
            logger.log_exception(e)
            return False

        except Exception as e:
            logger.error(f"Unexpected error during pull: {str(e)}")
            logger.log_exception(e)
            return False

    def get_current_commit(self) -> Optional[str]:
        """
        Obtiene el hash del commit actual

        Returns:
            Hash del commit o None
        """
        if not self.repo:
            return None

        try:
            return str(self.repo.head.commit.hexsha)
        except Exception as e:
            logger.log_error(f"Error getting current commit: {str(e)}")
            return None

    def get_current_commit_short(self) -> Optional[str]:
        """
        Obtiene el hash corto del commit actual

        Returns:
            Hash corto (7 chars) o None
        """
        full_hash = self.get_current_commit()
        return full_hash[:7] if full_hash else None

    def get_commit_info(self, commit_hash: Optional[str] = None) -> Optional[Dict]:
        """
        Obtiene información detallada de un commit

        Args:
            commit_hash: Hash del commit (None = HEAD)

        Returns:
            Dict con info del commit o None
        """
        if not self.repo:
            return None

        try:
            commit = self.repo.head.commit if not commit_hash else self.repo.commit(commit_hash)

            return {
                'hash': str(commit.hexsha),
                'hash_short': str(commit.hexsha)[:7],
                'author': str(commit.author),
                'author_email': commit.author.email,
                'date': commit.committed_datetime,
                'message': commit.message.strip(),
                'summary': commit.summary,
            }

        except Exception as e:
            logger.log_error(f"Error getting commit info: {str(e)}")
            return None

    def get_changes_since_commit(self, commit_hash: str) -> List[str]:
        """
        Obtiene lista de archivos cambiados desde un commit

        Args:
            commit_hash: Hash del commit base

        Returns:
            Lista de paths de archivos cambiados
        """
        if not self.repo:
            return []

        try:
            old_commit = self.repo.commit(commit_hash)
            current_commit = self.repo.head.commit

            diffs = old_commit.diff(current_commit)

            changed_files = []
            for diff in diffs:
                if diff.a_path:
                    changed_files.append(diff.a_path)
                if diff.b_path and diff.b_path != diff.a_path:
                    changed_files.append(diff.b_path)

            return list(set(changed_files))

        except Exception as e:
            logger.log_error(f"Error getting changes: {str(e)}")
            return []

    def get_current_branch(self) -> Optional[str]:
        """
        Obtiene el nombre del branch actual

        Returns:
            Nombre del branch o None
        """
        if not self.repo:
            return None

        try:
            return str(self.repo.active_branch.name)
        except Exception as e:
            logger.log_error(f"Error getting current branch: {str(e)}")
            return None

    def checkout_branch(self, branch: str, create: bool = False) -> bool:
        """
        Cambia a un branch

        Args:
            branch: Nombre del branch
            create: Si es True, crea el branch si no existe

        Returns:
            True si exitoso
        """
        if not self.repo:
            logger.error("No repository loaded")
            return False

        try:
            if create and branch not in self.repo.heads:
                logger.step(f"Creating branch: {branch}")
                self.repo.create_head(branch)

            logger.step(f"Checking out branch: {branch}")
            self.repo.heads[branch].checkout()
            logger.success(f"Now on branch: {branch}")
            return True

        except Exception as e:
            logger.error(f"Error checking out branch: {str(e)}")
            logger.log_exception(e)
            return False

    def has_uncommitted_changes(self) -> bool:
        """
        Verifica si hay cambios sin commitear

        Returns:
            True si hay cambios sin commitear
        """
        if not self.repo:
            return False

        try:
            return self.repo.is_dirty(untracked_files=True)
        except Exception:
            return False

    def get_uncommitted_changes(self) -> Dict[str, List[str]]:
        """
        Obtiene lista de cambios sin commitear

        Returns:
            Dict con 'modified', 'added', 'deleted', 'untracked'
        """
        if not self.repo:
            return {'modified': [], 'added': [], 'deleted': [], 'untracked': []}

        try:
            changes = {
                'modified': [item.a_path for item in self.repo.index.diff(None)],
                'added': [item.a_path for item in self.repo.index.diff('HEAD').iter_change_type('A')],
                'deleted': [item.a_path for item in self.repo.index.diff('HEAD').iter_change_type('D')],
                'untracked': self.repo.untracked_files
            }
            return changes

        except Exception as e:
            logger.log_error(f"Error getting uncommitted changes: {str(e)}")
            return {'modified': [], 'added': [], 'deleted': [], 'untracked': []}

    def get_remote_url(self, remote: str = "origin") -> Optional[str]:
        """
        Obtiene la URL del remoto

        Args:
            remote: Nombre del remoto

        Returns:
            URL del remoto o None
        """
        if not self.repo:
            return None

        try:
            return str(self.repo.remotes[remote].url)
        except Exception:
            return None

    def fetch(self, remote: str = "origin") -> bool:
        """
        Hace fetch del remoto

        Args:
            remote: Nombre del remoto

        Returns:
            True si exitoso
        """
        if not self.repo:
            logger.error("No repository loaded")
            return False

        try:
            logger.step(f"Fetching from {remote}")
            self.repo.remotes[remote].fetch()
            logger.success(f"Fetch completed from {remote}")
            return True

        except Exception as e:
            logger.error(f"Error fetching: {str(e)}")
            logger.log_exception(e)
            return False

    def get_commits_ahead_behind(self, remote: str = "origin") -> Tuple[int, int]:
        """
        Obtiene número de commits adelante/atrás del remoto

        Args:
            remote: Nombre del remoto

        Returns:
            Tupla (commits_ahead, commits_behind)
        """
        if not self.repo:
            return (0, 0)

        try:
            current_branch = self.repo.active_branch.name
            remote_branch = f"{remote}/{current_branch}"

            # Fetch primero
            self.repo.remotes[remote].fetch()

            # Contar commits
            commits_ahead = len(list(self.repo.iter_commits(f"{remote_branch}..HEAD")))
            commits_behind = len(list(self.repo.iter_commits(f"HEAD..{remote_branch}")))

            return (commits_ahead, commits_behind)

        except Exception as e:
            logger.log_error(f"Error getting commits ahead/behind: {str(e)}")
            return (0, 0)

    def reset_hard(self, commit: str = "HEAD") -> bool:
        """
        Hace reset --hard a un commit (PELIGROSO)

        Args:
            commit: Commit al que hacer reset

        Returns:
            True si exitoso
        """
        if not self.repo:
            logger.error("No repository loaded")
            return False

        try:
            logger.warning(f"DESTRUCTIVE: Resetting hard to {commit}")
            self.repo.head.reset(commit, index=True, working_tree=True)
            logger.success(f"Reset to {commit}")
            return True

        except Exception as e:
            logger.error(f"Error resetting: {str(e)}")
            logger.log_exception(e)
            return False

    def stash(self, message: Optional[str] = None) -> bool:
        """
        Hace stash de cambios

        Args:
            message: Mensaje del stash

        Returns:
            True si exitoso
        """
        if not self.repo:
            logger.error("No repository loaded")
            return False

        try:
            if not self.has_uncommitted_changes():
                logger.info("No changes to stash")
                return True

            logger.step("Stashing changes")
            self.repo.git.stash('save', message or 'LDM auto-stash')
            logger.success("Changes stashed")
            return True

        except Exception as e:
            logger.error(f"Error stashing: {str(e)}")
            logger.log_exception(e)
            return False

    def stash_pop(self) -> bool:
        """
        Aplica el último stash

        Returns:
            True si exitoso
        """
        if not self.repo:
            logger.error("No repository loaded")
            return False

        try:
            logger.step("Applying stash")
            self.repo.git.stash('pop')
            logger.success("Stash applied")
            return True

        except Exception as e:
            logger.error(f"Error applying stash: {str(e)}")
            logger.log_exception(e)
            return False

    def is_repo_clean(self) -> bool:
        """
        Verifica si el repositorio está limpio (sin cambios)

        Returns:
            True si está limpio
        """
        return not self.has_uncommitted_changes()

    def exists(self) -> bool:
        """Verifica si el repositorio existe"""
        return self.repo is not None


# Helper functions

def clone_repository(url: str, destination: Path, branch: str = "main") -> Optional[GitManager]:
    """
    Helper para clonar un repositorio

    Args:
        url: URL del repositorio
        destination: Path de destino
        branch: Branch a clonar

    Returns:
        GitManager del repo clonado o None
    """
    manager = GitManager()
    success = manager.clone(url, destination, branch)

    if success:
        return manager
    return None


def pull_repository(repo_path: Path) -> bool:
    """
    Helper para hacer pull de un repositorio

    Args:
        repo_path: Path al repositorio

    Returns:
        True si exitoso
    """
    manager = GitManager(repo_path)
    return manager.pull()


def get_repo_status(repo_path: Path) -> Dict:
    """
    Helper para obtener estado completo del repositorio

    Args:
        repo_path: Path al repositorio

    Returns:
        Dict con estado del repo
    """
    manager = GitManager(repo_path)

    if not manager.exists():
        return {'exists': False}

    commit_info = manager.get_commit_info()
    uncommitted = manager.get_uncommitted_changes()

    return {
        'exists': True,
        'path': str(repo_path),
        'branch': manager.get_current_branch(),
        'commit': commit_info,
        'remote_url': manager.get_remote_url(),
        'has_uncommitted_changes': manager.has_uncommitted_changes(),
        'uncommitted_changes': uncommitted,
        'is_clean': manager.is_repo_clean()
    }
