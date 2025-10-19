#!/usr/bin/env python3
"""
Script de prueba para funcionalidades de Fase 2
"""

import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent))

from src.env_manager import EnvManager, create_env_from_config
from src.port_manager import PortManager, get_available_ports
from src.models import GlobalConfig, ProjectConfig, PortsConfig, DatabaseConfig
from src.logger import logger


def test_env_manager():
    """Prueba EnvManager"""
    logger.header("Testing EnvManager")

    # Crear un .env de prueba
    test_path = Path("/tmp/test_ldm_env")
    test_path.mkdir(exist_ok=True)

    env_path = test_path / ".env"

    # Test 1: Crear desde template
    logger.step("Test 1: Creating .env from scratch")
    manager = EnvManager(env_path)

    # Crear algunas variables
    manager.set("APP_NAME", "TestApp")
    manager.set("APP_ENV", "local")
    manager.set("DB_HOST", "localhost")
    manager.set("DB_PASSWORD", "secret123")

    logger.success("Variables set successfully")

    # Test 2: Leer variables
    logger.step("Test 2: Reading variables")
    env_vars = manager.load()
    logger.print_config(env_vars, "Loaded Variables")

    # Test 3: Generar claves Laravel
    logger.step("Test 3: Generating Laravel keys")
    laravel_keys = manager.generate_laravel_keys()
    logger.info(f"Generated {len(laravel_keys)} Laravel keys")

    # Test 4: Generar claves SpringBoot
    logger.step("Test 4: Generating SpringBoot keys")
    springboot_keys = manager.generate_springboot_keys()
    logger.info(f"Generated {len(springboot_keys)} SpringBoot keys")

    # Test 5: Validar variables requeridas
    logger.step("Test 5: Validating required variables")
    required = ['APP_NAME', 'APP_ENV', 'DB_HOST', 'DB_PASSWORD']
    is_valid, missing = manager.validate_required(required)

    if is_valid:
        logger.success("All required variables present")
    else:
        logger.error(f"Missing variables: {missing}")

    # Test 6: Backup y restore
    logger.step("Test 6: Testing backup and restore")
    manager.backup()
    manager.set("NEW_VAR", "test")
    manager.restore()
    env_vars_after = manager.load()

    if "NEW_VAR" not in env_vars_after:
        logger.success("Restore worked correctly")
    else:
        logger.error("Restore failed")

    # Limpiar
    import shutil
    shutil.rmtree(test_path)
    logger.success("EnvManager tests completed")


def test_port_manager():
    """Prueba PortManager"""
    logger.header("Testing PortManager")

    manager = PortManager()

    # Test 1: Verificar puerto específico
    logger.step("Test 1: Checking specific port (8080)")
    is_available = manager.is_port_available(8080)
    logger.info(f"Port 8080 available: {is_available}")

    # Test 2: Obtener proceso usando puerto
    logger.step("Test 2: Getting process using port 80")
    process = manager.get_process_using_port(80)
    if process:
        logger.info(f"Port 80 used by: {process['name']} (PID: {process['pid']})")
    else:
        logger.info("Port 80 is available")

    # Test 3: Verificar múltiples puertos
    logger.step("Test 3: Checking multiple ports")
    ports_to_check = [80, 443, 3306, 8080, 9000]
    results = manager.check_ports(ports_to_check)

    for port, info in results.items():
        status = "Available" if info['available'] else "Occupied"
        logger.info(f"Port {port}: {status}")

    # Test 4: Sugerir puerto alternativo
    logger.step("Test 4: Suggesting alternative port for 80")
    alternative = manager.suggest_alternative_port(80)
    if alternative:
        logger.info(f"Alternative port suggested: {alternative}")
    else:
        logger.warning("No alternative port found")

    # Test 5: Puertos por defecto para stacks
    logger.step("Test 5: Default ports for stacks")
    laravel_ports = manager.get_default_ports('laravel-vue')
    logger.print_config(laravel_ports, "Laravel-Vue Default Ports")

    springboot_ports = manager.get_default_ports('springboot-vue')
    logger.print_config(springboot_ports, "SpringBoot-Vue Default Ports")

    # Test 6: Verificar y sugerir puertos
    logger.step("Test 6: Check and suggest ports")
    desired_ports = {'http': 80, 'https': 443, 'mysql': 3306}
    final_ports, warnings = manager.check_and_suggest_ports(desired_ports)

    logger.print_config(final_ports, "Final Ports")
    if warnings:
        for warning in warnings:
            logger.warning(warning)

    logger.success("PortManager tests completed")


def test_pydantic_models():
    """Prueba modelos Pydantic"""
    logger.header("Testing Pydantic Models")

    # Test 1: GlobalConfig
    logger.step("Test 1: GlobalConfig validation")
    try:
        config = GlobalConfig(
            version="1.0.0",
            base_path="~/local-deployer",
            default_stack="laravel-vue"
        )
        logger.success("GlobalConfig validated successfully")
        logger.info(f"Base path expanded: {config.base_path}")
    except Exception as e:
        logger.error(f"GlobalConfig validation failed: {str(e)}")

    # Test 2: PortsConfig
    logger.step("Test 2: PortsConfig validation")
    try:
        ports = PortsConfig(http=8080, https=8443, mysql=3306)
        logger.success("PortsConfig validated successfully")
    except Exception as e:
        logger.error(f"PortsConfig validation failed: {str(e)}")

    # Test 3: PortsConfig con valores inválidos
    logger.step("Test 3: PortsConfig with invalid values")
    try:
        invalid_ports = PortsConfig(http=99999)  # Puerto fuera de rango
        logger.error("Should have failed validation!")
    except Exception as e:
        logger.success(f"Validation correctly failed: {str(e)[:50]}...")

    # Test 4: ProjectConfig
    logger.step("Test 4: ProjectConfig validation")
    try:
        project = ProjectConfig(
            name="test_project",
            stack="laravel-vue",
            domain="test.local",
            backend_repo="https://github.com/user/backend.git",
            frontend_repo="https://github.com/user/frontend.git",
            ports=PortsConfig(),
            database=DatabaseConfig(
                database="testdb",
                username="root",
                password="secret"
            ),
            docker_network="ldm_test_network"
        )
        logger.success("ProjectConfig validated successfully")
        logger.info(f"Docker network: {project.docker_network}")
    except Exception as e:
        logger.error(f"ProjectConfig validation failed: {str(e)}")

    # Test 5: Dominio inválido
    logger.step("Test 5: Invalid domain validation")
    try:
        invalid_project = ProjectConfig(
            name="test",
            stack="laravel-vue",
            domain="invalid domain with spaces",  # Inválido
            backend_repo="https://github.com/user/backend.git",
            frontend_repo="https://github.com/user/frontend.git",
            ports=PortsConfig(),
            database=DatabaseConfig(
                database="testdb",
                username="root",
                password="secret"
            ),
            docker_network="test"
        )
        logger.error("Should have failed domain validation!")
    except Exception as e:
        logger.success(f"Domain validation correctly failed")

    logger.success("Pydantic models tests completed")


def main():
    """Ejecuta todas las pruebas"""
    logger.header("Phase 2 Functionality Tests")

    try:
        test_env_manager()
        logger.print()

        test_port_manager()
        logger.print()

        test_pydantic_models()
        logger.print()

        logger.header("All Tests Completed Successfully!")

    except Exception as e:
        logger.error(f"Tests failed: {str(e)}")
        logger.log_exception(e)
        sys.exit(1)


if __name__ == '__main__':
    main()
