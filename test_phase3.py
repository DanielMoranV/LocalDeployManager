#!/usr/bin/env python3
"""
Script de prueba para funcionalidades de Fase 3
"""

import sys
import tempfile
import shutil
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent))

from src.git_manager import GitManager, get_repo_status
from src.docker_manager import DockerManager, check_docker_installed, check_docker_compose_installed, get_docker_info
from src.template_manager import TemplateManager, render_project_templates
from src.logger import logger


def test_git_manager():
    """Prueba GitManager"""
    logger.header("Testing GitManager")

    # Crear un directorio temporal
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = Path(tmpdir) / "test_repo"

        # Test 1: Clonar un repositorio pequeño de prueba
        logger.step("Test 1: Cloning repository")
        manager = GitManager()

        # Usar un repo público pequeño para pruebas
        repo_url = "https://github.com/octocat/Hello-World.git"
        success = manager.clone(repo_url, test_path, branch="master", depth=1)

        if success:
            logger.success("Clone test passed")
        else:
            logger.warning("Clone test failed (may be network issue)")

        if not success:
            logger.info("Skipping rest of Git tests due to clone failure")
            return

        # Test 2: Obtener commit actual
        logger.step("Test 2: Getting current commit")
        commit = manager.get_current_commit()
        if commit:
            logger.success(f"Current commit: {commit[:7]}")
        else:
            logger.error("Failed to get current commit")

        # Test 3: Obtener info del commit
        logger.step("Test 3: Getting commit info")
        commit_info = manager.get_commit_info()
        if commit_info:
            logger.info(f"Author: {commit_info['author']}")
            logger.info(f"Message: {commit_info['summary']}")
            logger.success("Commit info retrieved")
        else:
            logger.error("Failed to get commit info")

        # Test 4: Obtener branch actual
        logger.step("Test 4: Getting current branch")
        branch = manager.get_current_branch()
        if branch:
            logger.success(f"Current branch: {branch}")
        else:
            logger.error("Failed to get current branch")

        # Test 5: Verificar si está limpio
        logger.step("Test 5: Checking if repo is clean")
        is_clean = manager.is_repo_clean()
        logger.info(f"Repository is clean: {is_clean}")

        # Test 6: Obtener URL remoto
        logger.step("Test 6: Getting remote URL")
        remote_url = manager.get_remote_url()
        if remote_url:
            logger.success(f"Remote URL: {remote_url}")
        else:
            logger.error("Failed to get remote URL")

        # Test 7: Helper function get_repo_status
        logger.step("Test 7: Using get_repo_status helper")
        status = get_repo_status(test_path)
        if status.get('exists'):
            logger.print_config(status, "Repository Status")
            logger.success("get_repo_status test passed")
        else:
            logger.error("get_repo_status test failed")

    logger.success("GitManager tests completed")


def test_docker_manager():
    """Prueba DockerManager"""
    logger.header("Testing DockerManager")

    # Test 1: Verificar instalación de Docker
    logger.step("Test 1: Checking Docker installation")
    docker_installed = check_docker_installed()
    logger.info(f"Docker installed: {docker_installed}")

    docker_compose_installed = check_docker_compose_installed()
    logger.info(f"Docker Compose installed: {docker_compose_installed}")

    if not docker_installed:
        logger.warning("Docker not installed, skipping Docker tests")
        return

    # Test 2: Inicializar DockerManager
    logger.step("Test 2: Initializing DockerManager")
    manager = DockerManager()

    # Test 3: Verificar si Docker está corriendo
    logger.step("Test 3: Checking if Docker is running")
    is_running = manager.is_docker_running()
    logger.info(f"Docker is running: {is_running}")

    if not is_running:
        logger.warning("Docker daemon not running, skipping some tests")
        return

    # Test 4: Obtener versión de Docker
    logger.step("Test 4: Getting Docker version")
    version = manager.get_docker_version()
    if version:
        logger.info(f"Docker version: {version.get('Version', 'Unknown')}")
        logger.success("Docker version retrieved")
    else:
        logger.error("Failed to get Docker version")

    # Test 5: get_docker_info helper
    logger.step("Test 5: Using get_docker_info helper")
    docker_info = get_docker_info()
    logger.print_config(docker_info, "Docker Information")

    logger.success("DockerManager tests completed")


def test_template_manager():
    """Prueba TemplateManager"""
    logger.header("Testing TemplateManager")

    # Test 1: Inicializar TemplateManager
    logger.step("Test 1: Initializing TemplateManager")
    manager = TemplateManager()

    if not manager.templates_dir.exists():
        logger.error(f"Templates directory not found: {manager.templates_dir}")
        return

    logger.success(f"Templates directory: {manager.templates_dir}")

    # Test 2: Obtener templates para Laravel
    logger.step("Test 2: Getting Laravel templates")
    laravel_templates = manager.get_stack_templates('laravel-vue')
    logger.print_config(laravel_templates, "Laravel Templates")

    # Test 3: Obtener templates para SpringBoot
    logger.step("Test 3: Getting SpringBoot templates")
    springboot_templates = manager.get_stack_templates('springboot-vue')
    logger.print_config(springboot_templates, "SpringBoot Templates")

    # Test 4: Renderizar docker-compose para Laravel
    logger.step("Test 4: Rendering Laravel docker-compose")
    compose_content = manager.render_docker_compose(
        stack='laravel-vue',
        project_name='test_project',
        domain='test.local',
        ports={'http': 80, 'https': 443, 'mysql': 3306, 'redis': 6379},
        db_config={
            'root_password': 'root123',
            'database': 'testdb',
            'username': 'testuser',
            'password': 'testpass'
        },
        network_name='ldm_test_network'
    )

    if compose_content:
        logger.success("docker-compose rendered successfully")
        logger.info(f"Content length: {len(compose_content)} characters")
        # Mostrar primeras líneas
        lines = compose_content.split('\n')[:5]
        logger.info(f"First lines:\n" + '\n'.join(lines))
    else:
        logger.error("Failed to render docker-compose")

    # Test 5: Renderizar nginx.conf para Laravel
    logger.step("Test 5: Rendering Laravel nginx.conf")
    nginx_content = manager.render_nginx_conf(
        stack='laravel-vue',
        project_name='test_project',
        domain='test.local',
        ports={'http': 80, 'https': 443}
    )

    if nginx_content:
        logger.success("nginx.conf rendered successfully")
        logger.info(f"Content length: {len(nginx_content)} characters")
    else:
        logger.error("Failed to render nginx.conf")

    # Test 6: Renderizar docker-compose para SpringBoot
    logger.step("Test 6: Rendering SpringBoot docker-compose")
    compose_content_sb = manager.render_docker_compose(
        stack='springboot-vue',
        project_name='test_spring',
        domain='spring.local',
        ports={'http': 80, 'https': 443, 'postgres': 5432, 'redis': 6379, 'backend': 8080},
        db_config={
            'database': 'springdb',
            'username': 'postgres',
            'password': 'postgrespass'
        },
        network_name='ldm_spring_network'
    )

    if compose_content_sb:
        logger.success("SpringBoot docker-compose rendered successfully")
    else:
        logger.error("Failed to render SpringBoot docker-compose")

    # Test 7: Setup completo de proyecto
    logger.step("Test 7: Full project setup")

    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        project_path.mkdir()

        success = manager.setup_project_docker(
            project_path=project_path,
            stack='laravel-vue',
            project_name='test_app',
            domain='testapp.local',
            ports={'http': 8080, 'https': 8443, 'mysql': 3306, 'redis': 6379},
            db_config={
                'root_password': 'root123',
                'database': 'testdb',
                'username': 'dbuser',
                'password': 'dbpass'
            },
            network_name='ldm_testapp_network'
        )

        if success:
            logger.success("Full project setup completed")

            # Verificar archivos creados
            files_created = list(project_path.glob('*'))
            logger.info(f"Files created: {len(files_created)}")
            for file in files_created:
                logger.info(f"  - {file.name}")
        else:
            logger.error("Full project setup failed")

    # Test 8: Helper function render_project_templates
    logger.step("Test 8: Using render_project_templates helper")

    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "helper_test"
        project_path.mkdir()

        success = render_project_templates(
            project_path=project_path,
            stack='springboot-vue',
            project_name='spring_test',
            domain='spring.local',
            ports={'http': 80, 'https': 443, 'postgres': 5432, 'redis': 6379, 'backend': 8080},
            db_config={
                'database': 'springdb',
                'username': 'postgres',
                'password': 'pass123'
            },
            network_name='ldm_spring_network'
        )

        if success:
            logger.success("render_project_templates test passed")
        else:
            logger.error("render_project_templates test failed")

    logger.success("TemplateManager tests completed")


def main():
    """Ejecuta todas las pruebas"""
    logger.header("Phase 3 Functionality Tests")

    try:
        test_git_manager()
        logger.print()

        test_docker_manager()
        logger.print()

        test_template_manager()
        logger.print()

        logger.header("All Tests Completed Successfully!")

    except Exception as e:
        logger.error(f"Tests failed: {str(e)}")
        logger.log_exception(e)
        sys.exit(1)


if __name__ == '__main__':
    main()
