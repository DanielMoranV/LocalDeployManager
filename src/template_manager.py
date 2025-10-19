"""
Gestión y renderizado de templates Jinja2
Maneja docker-compose, nginx, Dockerfiles, etc.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound

from .logger import logger
from .utils import get_base_path


class TemplateManager:
    """Manager para renderizado de templates"""

    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Inicializa el TemplateManager

        Args:
            templates_dir: Directorio de templates. Si es None, usa el directorio por defecto
        """
        if templates_dir is None:
            # Usar directorio de templates del proyecto
            self.templates_dir = Path(__file__).parent.parent / "templates"
        else:
            self.templates_dir = Path(templates_dir)

        if not self.templates_dir.exists():
            logger.log_warning(f"Templates directory not found: {self.templates_dir}")

        # Configurar Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )

    def render_template(self, template_path: str, context: Dict[str, Any]) -> Optional[str]:
        """
        Renderiza un template con el contexto dado

        Args:
            template_path: Path relativo al template (ej: 'laravel-vue/docker-compose.yml.j2')
            context: Dict con variables para el template

        Returns:
            String con el template renderizado o None
        """
        try:
            template = self.env.get_template(template_path)
            rendered = template.render(**context)
            logger.log_debug(f"Template {template_path} rendered successfully")
            return rendered

        except TemplateNotFound:
            logger.error(f"Template not found: {template_path}")
            return None
        except Exception as e:
            logger.error(f"Error rendering template {template_path}: {str(e)}")
            logger.log_exception(e)
            return None

    def render_and_save(
        self,
        template_path: str,
        context: Dict[str, Any],
        output_path: Path
    ) -> bool:
        """
        Renderiza un template y lo guarda en un archivo

        Args:
            template_path: Path relativo al template
            context: Dict con variables
            output_path: Path donde guardar el archivo renderizado

        Returns:
            True si exitoso
        """
        rendered = self.render_template(template_path, context)

        if rendered is None:
            return False

        try:
            # Crear directorio si no existe
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Guardar archivo
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(rendered)

            logger.success(f"Template saved to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error saving template to {output_path}: {str(e)}")
            logger.log_exception(e)
            return False

    def get_stack_templates(self, stack: str) -> Dict[str, str]:
        """
        Obtiene la lista de templates para un stack

        Args:
            stack: 'laravel-vue' o 'springboot-vue'

        Returns:
            Dict con nombre -> path relativo de templates
        """
        if stack == 'laravel-vue':
            return {
                'docker-compose': f'{stack}/docker-compose.yml.j2',
                'nginx': f'{stack}/nginx.conf.j2',
                'dockerfile': f'{stack}/Dockerfile.php',
                'env': f'{stack}/.env.template'
            }
        elif stack == 'springboot-vue':
            return {
                'docker-compose': f'{stack}/docker-compose.yml.j2',
                'nginx': f'{stack}/nginx.conf.j2',
                'dockerfile': f'{stack}/Dockerfile.java',
                'env': f'{stack}/.env.template'
            }
        else:
            return {}

    def render_docker_compose(
        self,
        stack: str,
        project_name: str,
        domain: str,
        ports: Dict[str, int],
        db_config: Dict[str, str],
        network_name: str
    ) -> Optional[str]:
        """
        Renderiza el template docker-compose para un stack

        Args:
            stack: 'laravel-vue' o 'springboot-vue'
            project_name: Nombre del proyecto
            domain: Dominio del proyecto
            ports: Dict con puertos
            db_config: Configuración de base de datos
            network_name: Nombre de la red Docker

        Returns:
            String con docker-compose.yml renderizado
        """
        templates = self.get_stack_templates(stack)

        if 'docker-compose' not in templates:
            logger.error(f"No docker-compose template for stack: {stack}")
            return None

        context = {
            'project_name': project_name,
            'domain': domain,
            'ports': ports,
            'db': db_config,
            'network_name': network_name
        }

        return self.render_template(templates['docker-compose'], context)

    def render_nginx_conf(
        self,
        stack: str,
        project_name: str,
        domain: str,
        ports: Dict[str, int]
    ) -> Optional[str]:
        """
        Renderiza el template nginx.conf para un stack

        Args:
            stack: 'laravel-vue' o 'springboot-vue'
            project_name: Nombre del proyecto
            domain: Dominio
            ports: Dict con puertos

        Returns:
            String con nginx.conf renderizado
        """
        templates = self.get_stack_templates(stack)

        if 'nginx' not in templates:
            logger.error(f"No nginx template for stack: {stack}")
            return None

        context = {
            'project_name': project_name,
            'domain': domain,
            'ports': ports
        }

        return self.render_template(templates['nginx'], context)

    def copy_dockerfile(self, stack: str, destination: Path) -> bool:
        """
        Copia el Dockerfile apropiado al destino

        Args:
            stack: 'laravel-vue' o 'springboot-vue'
            destination: Path donde copiar el Dockerfile

        Returns:
            True si exitoso
        """
        templates = self.get_stack_templates(stack)

        if 'dockerfile' not in templates:
            logger.error(f"No Dockerfile for stack: {stack}")
            return False

        try:
            # El Dockerfile no es un template Jinja2, solo copiarlo
            source = self.templates_dir / templates['dockerfile']

            if not source.exists():
                logger.error(f"Dockerfile not found: {source}")
                return False

            import shutil
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Determinar nombre del archivo destino
            if stack == 'laravel-vue':
                dest_file = destination / 'Dockerfile.php'
            else:
                dest_file = destination / 'Dockerfile.java'

            shutil.copy2(source, dest_file)
            logger.success(f"Dockerfile copied to {dest_file}")
            return True

        except Exception as e:
            logger.error(f"Error copying Dockerfile: {str(e)}")
            logger.log_exception(e)
            return False

    def setup_project_docker(
        self,
        project_path: Path,
        stack: str,
        project_name: str,
        domain: str,
        ports: Dict[str, int],
        db_config: Dict[str, str],
        network_name: str
    ) -> bool:
        """
        Configura todos los archivos Docker para un proyecto

        Args:
            project_path: Path del proyecto
            stack: Stack tecnológico
            project_name: Nombre del proyecto
            domain: Dominio
            ports: Puertos
            db_config: Config de DB
            network_name: Nombre de la red

        Returns:
            True si todo fue exitoso
        """
        logger.header(f"Setting up Docker for {project_name}")

        success = True

        # 1. Renderizar docker-compose.yml
        logger.step("Rendering docker-compose.yml")
        compose_content = self.render_docker_compose(
            stack, project_name, domain, ports, db_config, network_name
        )

        if compose_content:
            compose_path = project_path / "docker-compose.yml"
            with open(compose_path, 'w') as f:
                f.write(compose_content)
            logger.success(f"docker-compose.yml created")
        else:
            logger.error("Failed to render docker-compose.yml")
            success = False

        # 2. Renderizar nginx.conf
        logger.step("Rendering nginx.conf")
        nginx_content = self.render_nginx_conf(
            stack, project_name, domain, ports
        )

        if nginx_content:
            nginx_path = project_path / "nginx.conf"
            with open(nginx_path, 'w') as f:
                f.write(nginx_content)
            logger.success(f"nginx.conf created")
        else:
            logger.error("Failed to render nginx.conf")
            success = False

        # 3. Copiar Dockerfile
        logger.step("Copying Dockerfile")
        if not self.copy_dockerfile(stack, project_path):
            logger.error("Failed to copy Dockerfile")
            success = False

        if success:
            logger.success("All Docker files configured successfully")
        else:
            logger.warning("Some Docker files failed to configure")

        return success


# Helper functions

def render_project_templates(
    project_path: Path,
    stack: str,
    project_name: str,
    domain: str,
    ports: Dict[str, int],
    db_config: Dict[str, str],
    network_name: str
) -> bool:
    """
    Helper para renderizar todos los templates de un proyecto

    Args:
        project_path: Path del proyecto
        stack: Stack tecnológico
        project_name: Nombre del proyecto
        domain: Dominio
        ports: Puertos
        db_config: Configuración de DB
        network_name: Nombre de red Docker

    Returns:
        True si exitoso
    """
    manager = TemplateManager()
    return manager.setup_project_docker(
        project_path, stack, project_name, domain,
        ports, db_config, network_name
    )
