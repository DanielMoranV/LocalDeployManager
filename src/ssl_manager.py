"""
Gestión de certificados SSL locales con mkcert
Maneja instalación, generación y verificación de certificados
"""

import os
import subprocess
import platform
from pathlib import Path
from typing import Optional, Tuple

from .logger import logger
from .utils import command_exists


class SSLManager:
    """Manager para certificados SSL con mkcert"""

    def __init__(self, certs_dir: Optional[Path] = None):
        """
        Inicializa el SSLManager

        Args:
            certs_dir: Directorio donde guardar certificados
        """
        from .utils import get_base_path

        if certs_dir is None:
            self.certs_dir = get_base_path() / "certs"
        else:
            self.certs_dir = Path(certs_dir)

        # Crear directorio si no existe
        self.certs_dir.mkdir(parents=True, exist_ok=True)

    def is_mkcert_installed(self) -> bool:
        """
        Verifica si mkcert está instalado

        Returns:
            True si mkcert está disponible
        """
        return command_exists('mkcert')

    def get_mkcert_version(self) -> Optional[str]:
        """
        Obtiene la versión de mkcert

        Returns:
            String con versión o None
        """
        if not self.is_mkcert_installed():
            return None

        try:
            result = subprocess.run(
                ['mkcert', '-version'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                # Extraer versión del output
                version = result.stdout.strip()
                return version
            return None
        except Exception:
            return None

    def install_mkcert(self) -> bool:
        """
        Intenta instalar mkcert según el sistema operativo

        Returns:
            True si la instalación fue exitosa
        """
        system = platform.system()

        logger.step("Installing mkcert")

        try:
            if system == "Linux":
                # Detectar distribución
                if Path("/etc/debian_version").exists():
                    # Debian/Ubuntu
                    logger.info("Detected Debian/Ubuntu")
                    logger.info("Please run manually:")
                    logger.info("  sudo apt install libnss3-tools")
                    logger.info("  wget https://github.com/FiloSottile/mkcert/releases/latest/download/mkcert-v*-linux-amd64")
                    logger.info("  chmod +x mkcert-v*-linux-amd64")
                    logger.info("  sudo mv mkcert-v*-linux-amd64 /usr/local/bin/mkcert")
                    return False
                elif Path("/etc/redhat-release").exists():
                    # RHEL/CentOS/Fedora
                    logger.info("Detected RHEL/Fedora")
                    logger.info("Please run manually:")
                    logger.info("  sudo dnf install nss-tools")
                    logger.info("  Then download mkcert from GitHub releases")
                    return False
                else:
                    logger.warning("Unknown Linux distribution")
                    return False

            elif system == "Darwin":
                # macOS
                logger.info("Attempting to install via Homebrew")
                result = subprocess.run(
                    ['brew', 'install', 'mkcert'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    logger.success("mkcert installed via Homebrew")
                    return True
                else:
                    logger.error(f"Homebrew install failed: {result.stderr}")
                    return False

            elif system == "Windows":
                # Windows
                logger.info("Please install mkcert manually:")
                logger.info("  Download from: https://github.com/FiloSottile/mkcert/releases")
                logger.info("  Or use Chocolatey: choco install mkcert")
                return False

            else:
                logger.error(f"Unsupported operating system: {system}")
                return False

        except Exception as e:
            logger.error(f"Error installing mkcert: {str(e)}")
            logger.log_exception(e)
            return False

    def install_ca(self) -> bool:
        """
        Instala la CA local de mkcert

        Returns:
            True si exitoso
        """
        if not self.is_mkcert_installed():
            logger.error("mkcert is not installed")
            return False

        try:
            logger.step("Installing mkcert CA")

            result = subprocess.run(
                ['mkcert', '-install'],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                logger.success("mkcert CA installed")
                if result.stdout:
                    logger.log_debug(result.stdout)
                return True
            else:
                logger.error(f"CA installation failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error installing CA: {str(e)}")
            logger.log_exception(e)
            return False

    def generate_certificate(self, domain: str, subdomain: bool = True) -> Tuple[bool, Optional[Path], Optional[Path]]:
        """
        Genera certificado SSL para un dominio

        Args:
            domain: Dominio para el certificado
            subdomain: Si incluir wildcard subdomain (*.domain)

        Returns:
            Tupla (success, cert_path, key_path)
        """
        if not self.is_mkcert_installed():
            logger.error("mkcert is not installed")
            return False, None, None

        try:
            # Crear directorio para el dominio
            domain_dir = self.certs_dir / domain
            domain_dir.mkdir(parents=True, exist_ok=True)

            # Paths de certificados
            cert_path = domain_dir / f"{domain}.pem"
            key_path = domain_dir / f"{domain}-key.pem"

            logger.step(f"Generating SSL certificate for {domain}")

            # Construir comando
            cmd = ['mkcert', '-cert-file', str(cert_path), '-key-file', str(key_path)]

            # Agregar dominios
            if subdomain:
                cmd.extend([domain, f"*.{domain}"])
            else:
                cmd.append(domain)

            # Ejecutar mkcert
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=domain_dir
            )

            if result.returncode == 0:
                logger.success(f"Certificate generated for {domain}")
                logger.info(f"Certificate: {cert_path}")
                logger.info(f"Key: {key_path}")
                return True, cert_path, key_path
            else:
                logger.error(f"Certificate generation failed: {result.stderr}")
                return False, None, None

        except Exception as e:
            logger.error(f"Error generating certificate: {str(e)}")
            logger.log_exception(e)
            return False, None, None

    def certificate_exists(self, domain: str) -> bool:
        """
        Verifica si existe un certificado para un dominio

        Args:
            domain: Dominio a verificar

        Returns:
            True si existe el certificado
        """
        domain_dir = self.certs_dir / domain
        cert_path = domain_dir / f"{domain}.pem"
        key_path = domain_dir / f"{domain}-key.pem"

        return cert_path.exists() and key_path.exists()

    def get_certificate_paths(self, domain: str) -> Tuple[Optional[Path], Optional[Path]]:
        """
        Obtiene los paths de certificado y llave para un dominio

        Args:
            domain: Dominio

        Returns:
            Tupla (cert_path, key_path) o (None, None)
        """
        if self.certificate_exists(domain):
            domain_dir = self.certs_dir / domain
            cert_path = domain_dir / f"{domain}.pem"
            key_path = domain_dir / f"{domain}-key.pem"
            return cert_path, key_path
        return None, None

    def remove_certificate(self, domain: str) -> bool:
        """
        Elimina certificado de un dominio

        Args:
            domain: Dominio

        Returns:
            True si exitoso
        """
        try:
            domain_dir = self.certs_dir / domain

            if not domain_dir.exists():
                logger.info(f"No certificates found for {domain}")
                return True

            logger.step(f"Removing certificates for {domain}")

            import shutil
            shutil.rmtree(domain_dir)

            logger.success(f"Certificates removed for {domain}")
            return True

        except Exception as e:
            logger.error(f"Error removing certificates: {str(e)}")
            logger.log_exception(e)
            return False

    def setup_domain(self, domain: str) -> bool:
        """
        Setup completo de SSL para un dominio

        Args:
            domain: Dominio a configurar

        Returns:
            True si exitoso
        """
        logger.header(f"SSL Setup for {domain}")

        # 1. Verificar mkcert
        if not self.is_mkcert_installed():
            logger.error("mkcert is not installed")
            logger.info("Install mkcert first:")
            self.install_mkcert()
            return False

        version = self.get_mkcert_version()
        if version:
            logger.info(f"mkcert version: {version}")

        # 2. Instalar CA si es necesario
        # mkcert -install es idempotente, se puede ejecutar varias veces
        if not self.install_ca():
            logger.warning("CA installation failed, but continuing...")

        # 3. Generar certificado
        if self.certificate_exists(domain):
            logger.info(f"Certificate already exists for {domain}")
            cert_path, key_path = self.get_certificate_paths(domain)
            logger.info(f"Certificate: {cert_path}")
            logger.info(f"Key: {key_path}")
            return True

        success, cert_path, key_path = self.generate_certificate(domain)

        if success:
            logger.success(f"SSL setup completed for {domain}")
            return True
        else:
            logger.error(f"SSL setup failed for {domain}")
            return False


# Helper functions

def setup_ssl_for_domain(domain: str) -> Tuple[bool, Optional[Path], Optional[Path]]:
    """
    Helper para configurar SSL para un dominio

    Args:
        domain: Dominio

    Returns:
        Tupla (success, cert_path, key_path)
    """
    manager = SSLManager()
    success = manager.setup_domain(domain)

    if success:
        cert_path, key_path = manager.get_certificate_paths(domain)
        return True, cert_path, key_path

    return False, None, None


def check_ssl_requirements() -> bool:
    """
    Verifica que mkcert esté instalado y configurado

    Returns:
        True si todo está listo
    """
    manager = SSLManager()
    return manager.is_mkcert_installed()
