"""
CLI principal usando Click
Define todos los comandos y subcomandos de LDM
"""

import click
import sys
from pathlib import Path

from .logger import logger
from .utils import (
    get_version,
    ensure_base_directories,
    load_config,
    save_config,
    get_default_config,
    project_exists,
    get_project_config,
    get_active_project_path,
    save_project_config
)


# === Grupo principal ===

@click.group()
@click.version_option(version=get_version(), prog_name="LDM")
@click.pass_context
def cli(ctx):
    """
    Local Deploy Manager (LDM)

    Sistema de despliegue automatizado para proyectos web en red local.
    Soporta Laravel+Vue3 y SpringBoot+Vue3 con Docker, Nginx y SSL.
    """
    # Asegurar que existan directorios base
    ensure_base_directories()

    # Guardar contexto
    ctx.ensure_object(dict)
    ctx.obj['CONFIG'] = load_config()


# === Comando: version ===

@cli.command()
def version():
    """Muestra la versión de LDM"""
    version_info = {
        "LDM Version": get_version(),
        "Python": sys.version.split()[0],
    }

    logger.header("LDM Version Information")

    for key, value in version_info.items():
        logger.info(f"{key}: [bold]{value}[/bold]")

    logger.print()


# === Comando: init ===

@cli.command()
@click.option('--stack', type=click.Choice(['laravel-vue', 'springboot-vue']),
              help='Stack tecnológico a usar')
@click.option('--domain', required=True, help='Dominio local (ej: miapp.local)')
@click.option('--backend-repo', required=True, help='URL del repositorio backend')
@click.option('--frontend-repo', required=True, help='URL del repositorio frontend')
@click.option('--http-port', type=int, help='Puerto HTTP (default: 80)')
@click.option('--https-port', type=int, help='Puerto HTTPS (default: 443)')
@click.option('--db-port', type=int, help='Puerto de base de datos')
@click.option('--name', help='Nombre del proyecto (default: extraído del dominio)')
@click.pass_context
def init(ctx, stack, domain, backend_repo, frontend_repo, http_port, https_port, db_port, name):
    """
    Inicializa un nuevo proyecto

    Clona los repositorios, genera configuración, certificados SSL
    y prepara el entorno Docker.
    """
    from datetime import datetime
    from .git_manager import GitManager
    from .port_manager import PortManager, get_available_ports
    from .env_manager import create_env_from_config
    from .ssl_manager import SSLManager
    from .template_manager import TemplateManager
    from .docker_manager import check_docker_installed, check_docker_compose_installed
    from .models import ProjectConfig, PortsConfig, DatabaseConfig, CredentialsConfig

    logger.header("LDM Init - Initializing New Project")

    # === 1. VALIDACIONES PREVIAS ===
    logger.step("Running pre-flight checks")

    # Verificar que no exista proyecto activo
    if project_exists():
        logger.error("A project is already active")
        logger.info("Run 'ldm destroy' first to remove it")
        sys.exit(1)

    # Verificar Docker
    if not check_docker_installed():
        logger.error("Docker is not installed")
        logger.info("Please install Docker first: https://docs.docker.com/get-docker/")
        sys.exit(1)

    if not check_docker_compose_installed():
        logger.error("Docker Compose is not installed")
        sys.exit(1)

    # Verificar Git
    from .utils import command_exists
    if not command_exists('git'):
        logger.error("Git is not installed")
        sys.exit(1)

    # Validar dominio
    from .utils import validate_domain, validate_url, normalize_git_url
    if not validate_domain(domain):
        logger.error(f"Invalid domain format: {domain}")
        sys.exit(1)

    # Normalizar y validar URLs
    backend_repo = normalize_git_url(backend_repo)
    frontend_repo = normalize_git_url(frontend_repo)

    if not validate_url(backend_repo):
        logger.error(f"Invalid backend repository URL: {backend_repo}")
        sys.exit(1)

    if not validate_url(frontend_repo):
        logger.error(f"Invalid frontend repository URL: {frontend_repo}")
        sys.exit(1)

    logger.success("Pre-flight checks passed")
    logger.info(f"Backend: {backend_repo}")
    logger.info(f"Frontend: {frontend_repo}")

    # === 2. DETERMINAR CONFIGURACIÓN ===
    logger.step("Determining project configuration")

    # Nombre del proyecto
    if not name:
        name = domain.split('.')[0]

    from .utils import normalize_project_name
    project_name = normalize_project_name(name)
    logger.info(f"Project name: {project_name}")
    logger.info(f"Domain: {domain}")

    # Auto-detectar stack si no se especificó
    if not stack:
        # Intentar detectar del backend repo (simplificado)
        if 'laravel' in backend_repo.lower() or 'php' in backend_repo.lower():
            stack = 'laravel-vue'
        elif 'spring' in backend_repo.lower() or 'java' in backend_repo.lower():
            stack = 'springboot-vue'
        else:
            # Default
            stack = 'laravel-vue'
        logger.info(f"Auto-detected stack: {stack}")
    else:
        logger.info(f"Stack: {stack}")

    # Puertos
    port_manager = PortManager()
    default_ports = port_manager.get_default_ports(stack)

    # Usar puertos especificados o defaults
    if http_port:
        default_ports['http'] = http_port
    if https_port:
        default_ports['https'] = https_port
    if db_port:
        if stack == 'laravel-vue':
            default_ports['mysql'] = db_port
        else:
            default_ports['postgres'] = db_port

    # Verificar y sugerir puertos alternativos
    final_ports, warnings = port_manager.check_and_suggest_ports(default_ports)

    if warnings:
        logger.warning("Port conflicts detected:")
        for warning in warnings:
            logger.warning(f"  {warning}")

    logger.info("Ports assigned:")
    for service, port in final_ports.items():
        logger.info(f"  {service}: {port}")

    # === 3. CLONAR REPOSITORIOS ===
    logger.header("Cloning Repositories")

    active_project_path = get_active_project_path()
    active_project_path.mkdir(parents=True, exist_ok=True)

    backend_path = active_project_path / "backend"
    frontend_path = active_project_path / "frontend"

    # Clonar backend
    logger.step("Cloning backend repository")
    git_backend = GitManager()
    if not git_backend.clone(backend_repo, backend_path, branch="main"):
        # Intentar con master
        logger.info("Trying 'master' branch")
        if not git_backend.clone(backend_repo, backend_path, branch="master"):
            logger.error("Failed to clone backend repository")
            sys.exit(1)

    backend_commit = git_backend.get_current_commit_short()
    logger.success(f"Backend cloned (commit: {backend_commit})")

    # Clonar frontend
    logger.step("Cloning frontend repository")
    git_frontend = GitManager()
    if not git_frontend.clone(frontend_repo, frontend_path, branch="main"):
        logger.info("Trying 'master' branch")
        if not git_frontend.clone(frontend_repo, frontend_path, branch="master"):
            logger.error("Failed to clone frontend repository")
            sys.exit(1)

    frontend_commit = git_frontend.get_current_commit_short()
    logger.success(f"Frontend cloned (commit: {frontend_commit})")

    # === 4. GENERAR CONFIGURACIÓN .env ===
    logger.header("Generating Configuration")

    # Generar credenciales
    from .utils import generate_secure_password, generate_jwt_secret

    db_password = generate_secure_password(32)
    db_root_password = generate_secure_password(32)
    jwt_secret = generate_jwt_secret(64)
    app_key = f"base64:{generate_jwt_secret(32)}" if stack == 'laravel-vue' else None
    encryption_key = generate_jwt_secret(32) if stack == 'springboot-vue' else None

    # Configuración de base de datos
    db_config = {
        'host': 'mysql' if stack == 'laravel-vue' else 'postgres',
        'port': final_ports.get('mysql', 3306) if stack == 'laravel-vue' else final_ports.get('postgres', 5432),
        'database': f"{project_name}_db",
        'username': 'root' if stack == 'laravel-vue' else project_name,
        'password': db_password,
        'root_password': db_root_password
    }

    # Crear .env
    env_path = backend_path / ".env"
    env_manager = create_env_from_config(
        env_path=env_path,
        project_name=project_name,
        domain=domain,
        stack=stack,
        db_config=db_config,
        ports=final_ports
    )

    logger.success(".env file created")

    # === 5. GENERAR CERTIFICADOS SSL ===
    logger.header("Generating SSL Certificates")

    ssl_manager = SSLManager()
    ssl_success = ssl_manager.setup_domain(domain)

    if not ssl_success:
        logger.warning("SSL setup failed, but continuing...")
        logger.info("HTTPS won't work until SSL is configured")

    # === 6. GENERAR ARCHIVOS DOCKER ===
    logger.header("Generating Docker Configuration")

    network_name = f"ldm_{project_name}_network"

    template_manager = TemplateManager()
    docker_success = template_manager.setup_project_docker(
        project_path=active_project_path,
        stack=stack,
        project_name=project_name,
        domain=domain,
        ports=final_ports,
        db_config=db_config,
        network_name=network_name
    )

    if not docker_success:
        logger.error("Failed to generate Docker configuration")
        sys.exit(1)

    # === 7. GUARDAR CONFIGURACIÓN DEL PROYECTO ===
    logger.step("Saving project configuration")

    project_config = {
        'name': project_name,
        'stack': stack,
        'domain': domain,
        'backend_repo': backend_repo,
        'frontend_repo': frontend_repo,
        'ports': final_ports,
        'database': {
            'host': db_config['host'],
            'port': db_config['port'],
            'database': db_config['database'],
            'username': db_config['username'],
            'password': db_config['password'],
            'connection': 'mysql' if stack == 'laravel-vue' else 'postgres'
        },
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'last_deploy': None,
        'docker_network': network_name,
        'ssl_enabled': ssl_success,
        'git_commits': {
            'backend': backend_commit,
            'frontend': frontend_commit
        }
    }

    save_project_config(project_config)
    logger.success("Project configuration saved")

    # === 8. GUARDAR CREDENCIALES ===
    logger.step("Saving credentials")

    credentials = {
        'app_key': app_key,
        'jwt_secret': jwt_secret,
        'db_root_password': db_root_password,
        'db_password': db_password,
        'encryption_key': encryption_key,
        'created_at': datetime.now().isoformat()
    }

    from .utils import save_json_file
    credentials_path = active_project_path / ".credentials.json"
    save_json_file(credentials_path, credentials)
    logger.success("Credentials saved")

    # === 9. OUTPUT FINAL ===
    logger.header("Initialization Complete!")

    logger.success(f"Project '{project_name}' initialized successfully")
    logger.print()

    # Información importante
    logger.panel(
        f"""[green]✓[/green] Project: {project_name}
[green]✓[/green] Stack: {stack}
[green]✓[/green] Domain: {domain}
[green]✓[/green] SSL: {'Enabled' if ssl_success else 'Disabled'}

[yellow]Repositories cloned:[/yellow]
  • Backend: {backend_commit}
  • Frontend: {frontend_commit}

[yellow]Ports:[/yellow]
  • HTTP: {final_ports.get('http')}
  • HTTPS: {final_ports.get('https')}
  • Database: {final_ports.get('mysql') or final_ports.get('postgres')}""",
        title="Project Summary",
        style="blue"
    )

    logger.print()

    # Advertencias de configuración
    if warnings:
        logger.warning("Configuration warnings:")
        for warning in warnings:
            logger.warning(f"  • {warning}")
        logger.print()

    # Instrucciones siguientes
    logger.info("[bold]Next steps:[/bold]")
    logger.info("  1. Review and edit configuration if needed:")
    logger.info(f"     [cyan]ldm config show[/cyan]")
    logger.info(f"     [cyan]vim {active_project_path}/backend/.env[/cyan]")
    logger.info("")
    logger.info("  2. Deploy the application:")
    logger.info(f"     [cyan]ldm deploy[/cyan]")
    logger.info("")
    logger.info(f"  3. Access your application at:")
    logger.info(f"     [cyan]https://{domain}[/cyan]")
    logger.print()

    logger.success("Ready to deploy!")


# === Comando: deploy ===

@cli.command()
@click.option('--fresh-db', is_flag=True, help='Recrear base de datos desde cero')
@click.option('--seed', is_flag=True, help='Ejecutar seeders después de migraciones')
@click.option('--with-backup', is_flag=True, help='Crear backup antes de deployar')
@click.option('--no-pull', is_flag=True, help='No hacer git pull')
@click.option('--no-deps', is_flag=True, help='No instalar dependencias')
@click.option('--no-build', is_flag=True, help='No compilar frontend')
@click.pass_context
def deploy(ctx, fresh_db, seed, with_backup, no_pull, no_deps, no_build):
    """
    Despliega la aplicación

    Hace pull de cambios, instala dependencias, compila frontend,
    ejecuta migraciones y reinicia servicios.
    """
    import time
    from datetime import datetime
    from pathlib import Path
    from .git_manager import GitManager
    from .docker_manager import DockerManager

    start_time = time.time()
    logger.header("LDM Deploy - Deploying Application")

    # === 1. VALIDACIONES PRE-DEPLOY ===
    if not project_exists():
        logger.error("No active project. Run 'ldm init' first.")
        sys.exit(1)

    project_config = get_project_config()
    if not project_config:
        logger.error("Failed to load project configuration")
        sys.exit(1)

    project_name = project_config['name']
    stack = project_config['stack']
    domain = project_config['domain']

    logger.info(f"Project: {project_name}")
    logger.info(f"Stack: {stack}")
    logger.info(f"Domain: {domain}")
    logger.print()

    active_project_path = get_active_project_path()
    backend_path = active_project_path / "backend"
    frontend_path = active_project_path / "frontend"
    compose_file = active_project_path / "docker-compose.yml"

    # Verificar que existan los directorios
    if not backend_path.exists() or not frontend_path.exists():
        logger.error("Backend or frontend directory not found")
        sys.exit(1)

    if not compose_file.exists():
        logger.error("docker-compose.yml not found")
        sys.exit(1)

    # === 2. BACKUP (OPCIONAL) ===
    if with_backup:
        logger.header("Creating Backup")
        # TODO: Implementar en Fase 6
        logger.warning("Backup feature will be implemented in Phase 6")
        logger.info("Continuing without backup...")
        logger.print()

    # === 3. GIT PULL ===
    changes_detected = False
    backend_commit_old = project_config.get('git_commits', {}).get('backend', 'unknown')
    frontend_commit_old = project_config.get('git_commits', {}).get('frontend', 'unknown')

    if not no_pull:
        logger.header("Pulling Latest Changes")

        # Pull backend
        logger.step("Pulling backend repository")
        git_backend = GitManager(backend_path)
        if git_backend.pull():
            backend_commit_new = git_backend.get_current_commit_short()
            if backend_commit_new != backend_commit_old:
                changes_detected = True
                logger.success(f"Backend updated: {backend_commit_old} → {backend_commit_new}")
            else:
                logger.info("Backend already up to date")
        else:
            logger.warning("Backend pull failed, using current version")

        # Pull frontend
        logger.step("Pulling frontend repository")
        git_frontend = GitManager(frontend_path)
        if git_frontend.pull():
            frontend_commit_new = git_frontend.get_current_commit_short()
            if frontend_commit_new != frontend_commit_old:
                changes_detected = True
                logger.success(f"Frontend updated: {frontend_commit_old} → {frontend_commit_new}")
            else:
                logger.info("Frontend already up to date")
        else:
            logger.warning("Frontend pull failed, using current version")

        logger.print()
    else:
        logger.info("Skipping git pull (--no-pull)")
        backend_commit_new = backend_commit_old
        frontend_commit_new = frontend_commit_old

    # === 4. INSTALAR DEPENDENCIAS ===
    if not no_deps:
        logger.header("Installing Dependencies")

        docker_manager = DockerManager(compose_file)

        if stack == 'laravel-vue':
            # Composer install
            logger.step("Installing Composer dependencies")
            success, output = docker_manager.compose_exec(
                'php',
                ['composer', 'install', '--optimize-autoloader', '--no-dev']
            )
            if success:
                logger.success("Composer dependencies installed")
            else:
                logger.warning("Composer install failed (container may not be running yet)")

        elif stack == 'springboot-vue':
            # Maven install
            logger.step("Installing Maven dependencies")
            success, output = docker_manager.compose_exec(
                'springboot',
                ['./mvnw', 'dependency:resolve']
            )
            if success:
                logger.success("Maven dependencies resolved")
            else:
                logger.warning("Maven install failed (will be done during build)")

        # NPM install para frontend
        logger.step("Installing NPM dependencies")
        import subprocess
        result = subprocess.run(
            ['npm', 'install'],
            cwd=frontend_path,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logger.success("NPM dependencies installed")
        else:
            logger.error(f"NPM install failed: {result.stderr}")
            sys.exit(1)

        logger.print()
    else:
        logger.info("Skipping dependencies installation (--no-deps)")

    # === 5. BUILD FRONTEND ===
    if not no_build:
        logger.header("Building Frontend")

        logger.step("Running npm run build")
        with logger.spinner("Building Vue application"):
            result = subprocess.run(
                ['npm', 'run', 'build'],
                cwd=frontend_path,
                capture_output=True,
                text=True
            )

        if result.returncode != 0:
            logger.error(f"Frontend build failed: {result.stderr}")
            sys.exit(1)

        logger.success("Frontend build completed")

        # Copiar dist a la ubicación correcta
        dist_path = frontend_path / "dist"
        if not dist_path.exists():
            logger.error("dist/ directory not found after build")
            sys.exit(1)

        logger.step("Copying build to backend")
        import shutil

        if stack == 'laravel-vue':
            # Laravel: copiar a public/app
            target_path = backend_path / "public" / "app"
            if target_path.exists():
                shutil.rmtree(target_path)
            shutil.copytree(dist_path, target_path)
            logger.success(f"Frontend copied to public/app")

        elif stack == 'springboot-vue':
            # SpringBoot: copiar a src/main/resources/static
            target_path = backend_path / "src" / "main" / "resources" / "static"
            target_path.parent.mkdir(parents=True, exist_ok=True)
            if target_path.exists():
                shutil.rmtree(target_path)
            shutil.copytree(dist_path, target_path)
            logger.success(f"Frontend copied to resources/static")

        logger.print()
    else:
        logger.info("Skipping frontend build (--no-build)")

    # === 6. DOCKER COMPOSE UP ===
    logger.header("Starting Docker Services")

    docker_manager = DockerManager(compose_file)

    # Verificar si ya están corriendo
    services_status = docker_manager.compose_ps()
    running_services = [s for s in services_status if s.get('State') == 'running'] if services_status else []

    if running_services:
        logger.info(f"{len(running_services)} services already running")
        logger.step("Rebuilding and restarting services")
        build_flag = True
    else:
        logger.step("Starting services for the first time")
        build_flag = True

    # Docker compose up
    if not docker_manager.compose_up(detached=True, build=build_flag):
        logger.error("Docker Compose up failed")
        sys.exit(1)

    logger.success("Docker services started")
    logger.print()

    # === 7. ESPERAR SERVICIOS HEALTHY ===
    logger.header("Waiting for Services")

    db_container = f"{project_name}_mysql" if stack == 'laravel-vue' else f"{project_name}_postgres"

    logger.step(f"Waiting for database ({db_container})")
    if not docker_manager.wait_for_healthy(db_container, timeout=60):
        logger.warning("Database health check timeout, but continuing...")

    logger.print()

    # === 8. MIGRACIONES ===
    logger.header("Running Database Migrations")

    if stack == 'laravel-vue':
        # Laravel migrations
        if fresh_db:
            logger.step("Running migrate:fresh")
            success, output = docker_manager.compose_exec(
                'php',
                ['php', 'artisan', 'migrate:fresh', '--force']
            )
        else:
            logger.step("Running migrate")
            success, output = docker_manager.compose_exec(
                'php',
                ['php', 'artisan', 'migrate', '--force']
            )

        if success:
            logger.success("Migrations completed")
            if output:
                logger.log_debug(f"Migration output: {output}")
        else:
            logger.error(f"Migrations failed: {output}")
            sys.exit(1)

        # Seeders
        if seed:
            logger.step("Running database seeders")
            success, output = docker_manager.compose_exec(
                'php',
                ['php', 'artisan', 'db:seed', '--force']
            )
            if success:
                logger.success("Seeders completed")
            else:
                logger.warning(f"Seeders failed: {output}")

    elif stack == 'springboot-vue':
        # SpringBoot usa JPA auto-update
        logger.info("SpringBoot migrations handled by JPA (spring.jpa.hibernate.ddl-auto=update)")

    logger.print()

    # === 9. OPTIMIZACIONES ===
    logger.header("Running Optimizations")

    if stack == 'laravel-vue':
        logger.step("Clearing and caching Laravel configuration")

        commands = [
            (['php', 'artisan', 'config:cache'], 'Config cache'),
            (['php', 'artisan', 'route:cache'], 'Route cache'),
            (['php', 'artisan', 'view:cache'], 'View cache'),
        ]

        for cmd, description in commands:
            success, output = docker_manager.compose_exec('php', cmd)
            if success:
                logger.success(f"{description} completed")
            else:
                logger.warning(f"{description} failed: {output}")

    elif stack == 'springboot-vue':
        logger.info("SpringBoot optimizations handled by JVM")

    logger.print()

    # === 10. VERIFICACIÓN FINAL ===
    logger.header("Verifying Deployment")

    services_status = docker_manager.get_services_status()
    if services_status:
        logger.print_services_status(services_status)

    all_running = all(s.get('running', False) for s in services_status.values())

    if all_running:
        logger.success("All services are running")
    else:
        logger.warning("Some services are not running")

    logger.print()

    # === 11. ACTUALIZAR CONFIGURACIÓN ===
    logger.step("Updating project configuration")

    project_config['updated_at'] = datetime.now().isoformat()
    project_config['last_deploy'] = datetime.now().isoformat()
    project_config['git_commits'] = {
        'backend': backend_commit_new,
        'frontend': frontend_commit_new
    }

    save_project_config(project_config)
    logger.success("Configuration updated")
    logger.print()

    # === 12. RESUMEN FINAL ===
    duration = time.time() - start_time

    logger.header("Deploy Complete!")

    logger.panel(
        f"""[green]✓[/green] Project: {project_name}
[green]✓[/green] Stack: {stack}
[green]✓[/green] Duration: {duration:.1f}s

[yellow]Git Commits:[/yellow]
  • Backend: {backend_commit_new}
  • Frontend: {frontend_commit_new}

[yellow]Services:[/yellow]
  • All services running: {all_running}

[yellow]Changes:[/yellow]
  • New commits pulled: {changes_detected}
  • Fresh database: {fresh_db}
  • Seeded: {seed}""",
        title="Deploy Summary",
        style="green"
    )

    logger.print()
    logger.info(f"[bold]Access your application at:[/bold]")
    logger.info(f"  [cyan]https://{domain}[/cyan]")
    logger.print()

    # === 13. REGISTRAR EN HISTORIAL ===
    try:
        from .history_manager import add_deploy_to_history
        add_deploy_to_history(
            deploy_type='deploy',
            success=True,
            duration=duration,
            backend_commit=backend_commit_new,
            frontend_commit=frontend_commit_new,
            options={
                'fresh_db': fresh_db,
                'seed': seed,
                'with_backup': with_backup,
                'no_pull': no_pull,
                'no_deps': no_deps,
                'no_build': no_build
            }
        )
    except Exception as e:
        logger.log_debug(f"Failed to record deploy in history: {str(e)}")

    logger.success("Deploy successful!")


# === Grupo: config ===

@cli.group()
def config():
    """Gestiona la configuración del proyecto"""
    pass


@config.command('show')
def config_show():
    """Muestra la configuración actual"""
    if not project_exists():
        logger.error("No hay proyecto activo")
        sys.exit(1)

    project_config = get_project_config()
    if project_config:
        logger.print_config(project_config, "Project Configuration")
    else:
        logger.error("No se pudo cargar la configuración")


@config.command('edit')
@click.option('--project', is_flag=True, help='Edit project configuration instead of .env')
def config_edit(project):
    """Abre el archivo de configuración en el editor"""
    import subprocess
    import os

    if not project_exists():
        logger.error("No active project")
        sys.exit(1)

    active_project_path = get_active_project_path()

    if project:
        # Editar .project-config.json
        config_file = active_project_path / ".project-config.json"
        file_type = "project configuration"
    else:
        # Editar .env del backend
        config_file = active_project_path / "backend" / ".env"
        file_type = "environment configuration"

    if not config_file.exists():
        logger.error(f"Configuration file not found: {config_file}")
        sys.exit(1)

    # Determinar editor
    editor = os.environ.get('EDITOR', os.environ.get('VISUAL', 'nano'))

    logger.info(f"Opening {file_type} with {editor}...")
    logger.info(f"File: {config_file}")
    logger.print()

    try:
        subprocess.run([editor, str(config_file)])
        logger.success("Configuration file closed")
        logger.info("Restart services to apply changes: ldm restart")
    except FileNotFoundError:
        logger.error(f"Editor '{editor}' not found")
        logger.info(f"Set EDITOR environment variable or edit manually:")
        logger.info(f"  {config_file}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error opening editor: {str(e)}")
        sys.exit(1)


@config.command('regen-keys')
@click.confirmation_option(prompt='⚠️  This will regenerate security keys. Continue?')
def config_regen_keys():
    """Regenera APP_KEY y JWT_SECRET"""
    from .env_manager import EnvManager
    from .utils import generate_secure_password

    if not project_exists():
        logger.error("No active project")
        sys.exit(1)

    active_project_path = get_active_project_path()
    project_config = get_project_config()

    if not project_config:
        logger.error("Project configuration not found")
        sys.exit(1)

    stack = project_config.get('stack')
    env_path = active_project_path / "backend" / ".env"

    if not env_path.exists():
        logger.error(".env file not found")
        sys.exit(1)

    logger.header("Regenerating Security Keys")

    env_manager = EnvManager(env_path)

    try:
        if stack == 'laravel-vue':
            # Generar nuevo APP_KEY (Laravel format)
            import base64
            import secrets
            app_key = 'base64:' + base64.b64encode(secrets.token_bytes(32)).decode()

            # Generar nuevo JWT_SECRET
            jwt_secret = generate_secure_password(64)

            logger.step("Generating new keys")
            env_manager.set('APP_KEY', app_key)
            env_manager.set('JWT_SECRET', jwt_secret)

            logger.success("APP_KEY regenerated")
            logger.success("JWT_SECRET regenerated")

        elif stack == 'springboot-vue':
            # Generar nuevo JWT_SECRET para SpringBoot
            jwt_secret = generate_secure_password(64)

            logger.step("Generating new JWT secret")
            env_manager.set('JWT_SECRET', jwt_secret)

            logger.success("JWT_SECRET regenerated")

        logger.print()
        logger.panel(
            "[yellow]⚠️  Important:[/yellow]\n\n"
            "• Existing sessions will be invalidated\n"
            "• Users will need to log in again\n"
            "• Restart services to apply changes:\n"
            "  [cyan]ldm restart[/cyan]",
            title="Keys Regenerated",
            style="yellow"
        )

    except Exception as e:
        logger.error(f"Error regenerating keys: {str(e)}")
        logger.log_exception(e)
        sys.exit(1)


# === Comando: status ===

@cli.command()
def status():
    """Muestra el estado de los servicios Docker"""
    from .docker_manager import DockerManager

    if not project_exists():
        logger.error("No active project")
        sys.exit(1)

    project_config = get_project_config()
    if not project_config:
        logger.error("Failed to load project configuration")
        sys.exit(1)

    project_name = project_config['name']
    stack = project_config['stack']
    domain = project_config['domain']

    logger.header(f"Project Status: {project_name}")

    active_project_path = get_active_project_path()
    compose_file = active_project_path / "docker-compose.yml"

    if not compose_file.exists():
        logger.error("docker-compose.yml not found")
        sys.exit(1)

    docker_manager = DockerManager(compose_file)

    # Obtener estado de servicios
    services_status = docker_manager.get_services_status()

    if not services_status:
        logger.warning("No services found or Docker is not running")
        sys.exit(1)

    # Mostrar tabla de servicios
    logger.print_services_status(services_status)
    logger.print()

    # Información adicional
    running_count = sum(1 for s in services_status.values() if s.get('running'))
    total_count = len(services_status)

    logger.info(f"Stack: {stack}")
    logger.info(f"Domain: {domain}")
    logger.info(f"Services: {running_count}/{total_count} running")

    # Info de último deploy
    last_deploy = project_config.get('last_deploy')
    if last_deploy:
        from datetime import datetime
        deploy_dt = datetime.fromisoformat(last_deploy)
        logger.info(f"Last deploy: {deploy_dt.strftime('%Y-%m-%d %H:%M:%S')}")

    logger.print()

    if running_count == total_count:
        logger.success("All services are running")
        logger.info(f"Access: [cyan]https://{domain}[/cyan]")
    elif running_count > 0:
        logger.warning(f"{total_count - running_count} service(s) not running")
        logger.info("Run 'ldm start' to start all services")
    else:
        logger.error("No services are running")
        logger.info("Run 'ldm start' to start services")


# === Comando: start ===

@cli.command()
def start():
    """Inicia todos los servicios"""
    from .docker_manager import DockerManager

    if not project_exists():
        logger.error("No active project")
        sys.exit(1)

    logger.header("Starting Services")

    active_project_path = get_active_project_path()
    compose_file = active_project_path / "docker-compose.yml"

    if not compose_file.exists():
        logger.error("docker-compose.yml not found")
        sys.exit(1)

    docker_manager = DockerManager(compose_file)

    # Docker compose up
    logger.step("Starting Docker Compose services")
    if docker_manager.compose_up(detached=True, build=False):
        logger.success("Services started successfully")

        # Mostrar estado
        logger.print()
        services_status = docker_manager.get_services_status()
        if services_status:
            logger.print_services_status(services_status)

        project_config = get_project_config()
        if project_config:
            domain = project_config.get('domain')
            logger.print()
            logger.info(f"Access: [cyan]https://{domain}[/cyan]")
    else:
        logger.error("Failed to start services")
        sys.exit(1)


# === Comando: stop ===

@cli.command()
def stop():
    """Detiene todos los servicios"""
    from .docker_manager import DockerManager

    if not project_exists():
        logger.error("No active project")
        sys.exit(1)

    logger.header("Stopping Services")

    active_project_path = get_active_project_path()
    compose_file = active_project_path / "docker-compose.yml"

    if not compose_file.exists():
        logger.error("docker-compose.yml not found")
        sys.exit(1)

    docker_manager = DockerManager(compose_file)

    # Docker compose down
    logger.step("Stopping Docker Compose services")
    if docker_manager.compose_down(remove_volumes=False):
        logger.success("Services stopped successfully")
        logger.info("Data volumes preserved")
        logger.info("Run 'ldm start' to restart services")
    else:
        logger.error("Failed to stop services")
        sys.exit(1)


# === Comando: restart ===

@cli.command()
@click.argument('service', required=False)
def restart(service):
    """Reinicia servicios (todo o uno específico)"""
    from .docker_manager import DockerManager

    if not project_exists():
        logger.error("No active project")
        sys.exit(1)

    active_project_path = get_active_project_path()
    compose_file = active_project_path / "docker-compose.yml"

    if not compose_file.exists():
        logger.error("docker-compose.yml not found")
        sys.exit(1)

    docker_manager = DockerManager(compose_file)

    if service:
        logger.header(f"Restarting Service: {service}")
        logger.step(f"Restarting {service}")

        if docker_manager.compose_restart(services=[service]):
            logger.success(f"{service} restarted successfully")
        else:
            logger.error(f"Failed to restart {service}")
            sys.exit(1)
    else:
        logger.header("Restarting All Services")
        logger.step("Restarting all services")

        if docker_manager.compose_restart():
            logger.success("All services restarted successfully")

            # Mostrar estado
            logger.print()
            services_status = docker_manager.get_services_status()
            if services_status:
                logger.print_services_status(services_status)
        else:
            logger.error("Failed to restart services")
            sys.exit(1)


# === Comando: destroy ===

@cli.command()
@click.option('--remove-volumes', is_flag=True, help='También eliminar volúmenes de datos')
@click.confirmation_option(prompt='Are you sure you want to destroy the active project?')
def destroy(remove_volumes):
    """Elimina el proyecto activo y sus contenedores"""
    from .docker_manager import DockerManager
    import shutil

    if not project_exists():
        logger.error("No active project")
        sys.exit(1)

    project_config = get_project_config()
    project_name = project_config['name'] if project_config else 'unknown'

    logger.header(f"Destroying Project: {project_name}")
    logger.warning("This action cannot be undone!")
    logger.print()

    active_project_path = get_active_project_path()
    compose_file = active_project_path / "docker-compose.yml"

    # 1. Detener y eliminar contenedores
    if compose_file.exists():
        logger.step("Stopping and removing Docker services")
        docker_manager = DockerManager(compose_file)

        if docker_manager.compose_down(remove_volumes=remove_volumes):
            logger.success("Docker services removed")
        else:
            logger.warning("Failed to remove Docker services")

    # 2. Eliminar directorio del proyecto
    if active_project_path.exists():
        logger.step(f"Removing project directory: {active_project_path}")

        try:
            shutil.rmtree(active_project_path)
            logger.success("Project directory removed")
        except Exception as e:
            logger.error(f"Failed to remove directory: {str(e)}")
            sys.exit(1)

    logger.print()
    logger.success(f"Project '{project_name}' destroyed successfully")

    if remove_volumes:
        logger.warning("Data volumes were also removed")
    else:
        logger.info("Data volumes preserved (use --remove-volumes to delete them)")

    logger.info("You can now initialize a new project with 'ldm init'")


# === Grupo: backup ===

@cli.group()
def backup():
    """Gestiona backups del proyecto"""
    pass


@backup.command('create')
@click.option('--name', help='Nombre personalizado para el backup')
@click.option('--no-db', is_flag=True, help='No incluir backup de base de datos')
def backup_create(name, no_db):
    """Crea un nuevo backup del proyecto activo"""
    from .backup_manager import BackupManager

    if not project_exists():
        logger.error("No active project")
        sys.exit(1)

    active_project_path = get_active_project_path()
    project_config = get_project_config()

    if not project_config:
        logger.error("Project configuration not found")
        sys.exit(1)

    # Crear backup
    backup_manager = BackupManager()
    success, backup_id = backup_manager.create_backup(
        project_path=active_project_path,
        project_config=project_config,
        name=name,
        include_db=not no_db
    )

    if success:
        logger.print()
        logger.panel(
            f"[green]✓[/green] Backup created successfully\n\n"
            f"Backup ID: [cyan]{backup_id}[/cyan]\n\n"
            f"To restore this backup:\n"
            f"  [yellow]ldm backup restore {backup_id}[/yellow]",
            title="Backup Complete"
        )
    else:
        logger.error("Backup creation failed")
        sys.exit(1)


@backup.command('list')
def backup_list():
    """Lista todos los backups disponibles"""
    from .backup_manager import BackupManager
    from rich.table import Table

    backup_manager = BackupManager()
    backups = backup_manager.list_backups()

    if not backups:
        logger.info("No backups found")
        logger.info("Create a backup with: ldm backup create")
        return

    logger.header(f"Available Backups ({len(backups)})")

    # Crear tabla
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Backup ID", style="cyan")
    table.add_column("Date/Time", style="white")
    table.add_column("Project", style="yellow")
    table.add_column("Stack", style="magenta")
    table.add_column("Size", style="green", justify="right")
    table.add_column("DB", justify="center")

    for backup in backups:
        backup_id = backup.get('backup_id', 'unknown')

        # Formatear timestamp
        timestamp = backup.get('timestamp', '')
        if timestamp:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(timestamp)
                timestamp_str = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                timestamp_str = timestamp[:16] if len(timestamp) > 16 else timestamp
        else:
            timestamp_str = "unknown"

        project_name = backup.get('project', {}).get('name', 'unknown')
        stack = backup.get('project', {}).get('stack', 'unknown')
        size_mb = backup.get('size_mb', 0)
        has_db = "✓" if backup.get('database_backup', False) else "✗"

        table.add_row(
            backup_id,
            timestamp_str,
            project_name,
            stack,
            f"{size_mb:.2f} MB",
            has_db
        )

    logger.print(table)
    logger.print()
    logger.info("To restore a backup: ldm backup restore <backup-id>")


@backup.command('restore')
@click.argument('backup_id')
@click.option('--no-db', is_flag=True, help='No restaurar base de datos')
@click.confirmation_option(
    prompt='⚠️  This will overwrite the current project. Continue?'
)
def backup_restore(backup_id, no_db):
    """Restaura un backup específico"""
    from .backup_manager import BackupManager
    from .docker_manager import DockerManager

    if not project_exists():
        logger.error("No active project")
        sys.exit(1)

    active_project_path = get_active_project_path()

    # Verificar que el backup existe
    backup_manager = BackupManager()
    backup_info = backup_manager.get_backup(backup_id)

    if not backup_info:
        logger.error(f"Backup not found: {backup_id}")
        logger.info("List available backups with: ldm backup list")
        sys.exit(1)

    # Mostrar info del backup
    logger.header(f"Restoring Backup: {backup_id}")
    logger.info(f"Project: {backup_info.get('project', {}).get('name', 'unknown')}")
    logger.info(f"Stack: {backup_info.get('project', {}).get('stack', 'unknown')}")
    logger.info(f"Date: {backup_info.get('timestamp', 'unknown')[:16]}")
    logger.print()

    # Detener servicios si están corriendo
    compose_file = active_project_path / "docker-compose.yml"
    if compose_file.exists():
        logger.step("Stopping services")
        docker_manager = DockerManager(compose_file)
        docker_manager.compose_down(remove_volumes=False)
        logger.success("Services stopped")

    # Restaurar backup
    success = backup_manager.restore_backup(
        backup_id=backup_id,
        target_path=active_project_path,
        restore_db=not no_db
    )

    if success:
        logger.print()
        logger.panel(
            f"[green]✓[/green] Backup restored successfully\n\n"
            f"Start services with:\n"
            f"  [yellow]ldm start[/yellow]",
            title="Restore Complete"
        )
    else:
        logger.error("Backup restore failed")
        sys.exit(1)


# === Comando: logs ===

@cli.command()
@click.option('--follow', '-f', is_flag=True, help='Seguir logs en tiempo real')
@click.option('--tail', type=int, default=100, help='Número de líneas a mostrar')
@click.argument('service', required=False)
def logs(follow, tail, service):
    """Muestra logs de servicios Docker"""
    from .docker_manager import DockerManager

    if not project_exists():
        logger.error("No active project")
        sys.exit(1)

    active_project_path = get_active_project_path()
    compose_file = active_project_path / "docker-compose.yml"

    if not compose_file.exists():
        logger.error("docker-compose.yml not found")
        sys.exit(1)

    docker_manager = DockerManager(compose_file)

    if service:
        logger.info(f"Showing logs for: {service}")
    else:
        logger.info("Showing logs for all services")

    if follow:
        logger.info("Following logs (Ctrl+C to stop)...")
    else:
        logger.info(f"Last {tail} lines")

    logger.print()

    # Mostrar logs
    docker_manager.compose_logs(service=service, follow=follow, tail=tail)


# === Comando: shell ===

@cli.command()
@click.argument('service')
@click.option('--shell', default=None, help='Shell a usar (default: /bin/sh o /bin/bash)')
def shell(service, shell):
    """Abre una shell interactiva en un contenedor"""
    from .docker_manager import DockerManager
    import subprocess

    if not project_exists():
        logger.error("No active project")
        sys.exit(1)

    active_project_path = get_active_project_path()
    compose_file = active_project_path / "docker-compose.yml"

    if not compose_file.exists():
        logger.error("docker-compose.yml not found")
        sys.exit(1)

    docker_manager = DockerManager(compose_file)

    # Verificar que el servicio existe en compose_ps
    logger.step(f"Checking service: {service}")
    services = docker_manager.compose_ps()

    if not services:
        logger.error("No services running")
        logger.info("Start services with: ldm start")
        sys.exit(1)

    # Verificar que el servicio solicitado existe
    service_names = [s.get('service') for s in services]
    if service not in service_names:
        logger.error(f"Service '{service}' not found")
        logger.info(f"Available services: {', '.join(service_names)}")
        sys.exit(1)

    # Verificar que el servicio está corriendo
    service_info = next((s for s in services if s.get('service') == service), None)
    if service_info and service_info.get('state') != 'running':
        logger.error(f"Service '{service}' is not running (state: {service_info.get('state')})")
        logger.info("Start services with: ldm start")
        sys.exit(1)

    logger.success(f"Opening shell in: {service}")

    # Determinar shell a usar
    if shell is None:
        # Intentar determinar shell disponible
        # Primero intentamos bash, luego sh
        logger.info("Detecting available shell...")
        shell = '/bin/bash'

    logger.info(f"Using shell: {shell}")
    logger.info("Type 'exit' to close the shell\n")

    try:
        # Detectar comando de Docker Compose
        compose_cmd = docker_manager.compose_cmd

        # Ejecutar docker compose exec sin -T para permitir interactividad
        cmd = compose_cmd + [
            '-f', str(compose_file),
            'exec',
            service,
            shell
        ]

        # Ejecutar con subprocess.run sin capture_output para mantener interactividad
        result = subprocess.run(
            cmd,
            cwd=compose_file.parent
        )

        if result.returncode != 0:
            # Si bash falló, intentar con sh
            if shell == '/bin/bash':
                logger.warning("Bash not available, trying /bin/sh...")
                cmd[-1] = '/bin/sh'
                result = subprocess.run(
                    cmd,
                    cwd=compose_file.parent
                )

                if result.returncode != 0:
                    logger.error("Failed to open shell")
                    sys.exit(1)

        logger.success("Shell session closed")

    except KeyboardInterrupt:
        logger.info("\nShell session interrupted")
    except Exception as e:
        logger.error(f"Error opening shell: {str(e)}")
        logger.log_exception(e)
        sys.exit(1)


# === Comando: history ===

@cli.command()
@click.argument('deploy_id', required=False, type=int)
@click.option('--limit', type=int, default=20, help='Cantidad de deploys a mostrar')
def history(deploy_id, limit):
    """Muestra historial de deploys"""
    from .history_manager import HistoryManager
    from rich.table import Table
    from datetime import datetime

    if not project_exists():
        logger.error("No active project")
        sys.exit(1)

    history_manager = HistoryManager()

    # Si se especifica un ID, mostrar detalles
    if deploy_id:
        deploy = history_manager.get_deploy(deploy_id)

        if not deploy:
            logger.error(f"Deploy #{deploy_id} not found")
            sys.exit(1)

        logger.header(f"Deploy #{deploy_id} Details")

        # Formatear timestamp
        timestamp = deploy.get('timestamp', '')
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                timestamp_str = timestamp
        else:
            timestamp_str = "unknown"

        success = deploy.get('success', False)
        status_str = "[green]✓ Success[/green]" if success else "[red]✗ Failed[/red]"

        info = f"""[yellow]Type:[/yellow] {deploy.get('type', 'unknown')}
[yellow]Status:[/yellow] {status_str}
[yellow]Timestamp:[/yellow] {timestamp_str}
[yellow]Duration:[/yellow] {deploy.get('duration', 0):.1f}s

[yellow]Git Commits:[/yellow]
  • Backend: {deploy.get('commits', {}).get('backend', 'N/A')}
  • Frontend: {deploy.get('commits', {}).get('frontend', 'N/A')}"""

        options = deploy.get('options', {})
        if options:
            info += "\n\n[yellow]Options:[/yellow]"
            for key, value in options.items():
                if value:
                    info += f"\n  • {key}: {value}"

        error = deploy.get('error')
        if error:
            info += f"\n\n[red]Error:[/red] {error}"

        logger.panel(info, title=f"Deploy #{deploy_id}")
        return

    # Mostrar lista de deploys
    history_list = history_manager.load_history()

    if not history_list:
        logger.info("No deploy history found")
        logger.info("Deploy history is recorded automatically with each deploy")
        return

    # Limitar cantidad
    history_list = history_list[-limit:]

    logger.header(f"Deploy History (last {len(history_list)} deploys)")

    # Crear tabla
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("ID", style="cyan", width=5)
    table.add_column("Date/Time", style="white")
    table.add_column("Type", style="yellow")
    table.add_column("Duration", style="magenta", justify="right")
    table.add_column("Status", justify="center")
    table.add_column("Backend", style="dim")
    table.add_column("Frontend", style="dim")

    for deploy in history_list:
        deploy_id_str = str(deploy.get('id', '?'))

        # Formatear timestamp
        timestamp = deploy.get('timestamp', '')
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                timestamp_str = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                timestamp_str = timestamp[:16] if len(timestamp) > 16 else timestamp
        else:
            timestamp_str = "unknown"

        deploy_type = deploy.get('type', 'unknown')
        duration = f"{deploy.get('duration', 0):.1f}s"

        success = deploy.get('success', False)
        status = "✓" if success else "✗"
        status_color = "green" if success else "red"

        backend_commit = deploy.get('commits', {}).get('backend', 'N/A')
        if backend_commit and len(backend_commit) > 7:
            backend_commit = backend_commit[:7]

        frontend_commit = deploy.get('commits', {}).get('frontend', 'N/A')
        if frontend_commit and len(frontend_commit) > 7:
            frontend_commit = frontend_commit[:7]

        table.add_row(
            deploy_id_str,
            timestamp_str,
            deploy_type,
            duration,
            f"[{status_color}]{status}[/{status_color}]",
            backend_commit,
            frontend_commit
        )

    logger.print(table)
    logger.print()

    # Estadísticas
    total = len(history_manager.load_history())
    successful = history_manager.get_successful_deploys_count()
    failed = history_manager.get_failed_deploys_count()

    logger.info(f"Total deploys: {total} ([green]{successful} successful[/green], [red]{failed} failed[/red])")
    logger.info("View deploy details: ldm history <id>")


# === Comando: check-ports ===

@cli.command('check-ports')
@click.option('--port', type=int, multiple=True, help='Puertos específicos a verificar')
@click.option('--stack', type=click.Choice(['laravel-vue', 'springboot-vue']),
              help='Verificar puertos por defecto del stack')
@click.pass_context
def check_ports(ctx, port, stack):
    """Verifica disponibilidad de puertos"""
    from .port_manager import PortManager

    logger.header("Port Availability Check")

    manager = PortManager()

    # Determinar qué puertos verificar
    ports_to_check = {}

    if port:
        # Puertos específicos proporcionados por el usuario
        for p in port:
            ports_to_check[f"port_{p}"] = p
    elif stack:
        # Puertos por defecto del stack
        ports_to_check = manager.get_default_ports(stack)
        logger.info(f"Checking default ports for stack: {stack}")
    elif project_exists():
        # Si hay proyecto activo, usar sus puertos
        project_config = get_project_config()
        if project_config:
            stack_type = project_config.get('stack', 'laravel-vue')
            ports_to_check = manager.get_default_ports(stack_type)
            logger.info(f"Checking ports for active project ({stack_type})")
    else:
        # Por defecto, verificar puertos comunes
        ports_to_check = manager.get_common_service_ports()
        logger.info("Checking common service ports")

    # Mostrar tabla con estado
    manager.display_port_status(ports_to_check)

    # Resumen
    available_count = sum(1 for p in ports_to_check.values()
                         if manager.is_port_available(p))
    total_count = len(ports_to_check)

    logger.print()
    if available_count == total_count:
        logger.success(f"All {total_count} ports are available!")
    else:
        occupied = total_count - available_count
        logger.warning(f"{occupied} out of {total_count} ports are occupied")


# === Comando: shell ===

@cli.command()
@click.argument('service')
def shell(service):
    """Abre una shell en un contenedor específico"""
    if not project_exists():
        logger.error("No hay proyecto activo")
        sys.exit(1)

    # TODO: Implementar en Fase 8
    logger.warning("Comando 'shell' será implementado en Fase 8")


# === Punto de entrada ===

def main():
    """Punto de entrada principal"""
    cli(obj={})


if __name__ == '__main__':
    main()
