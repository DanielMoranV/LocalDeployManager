#!/bin/bash
# Script de setup para Local Deploy Manager

set -e

echo "=========================================="
echo "  Local Deploy Manager - Setup"
echo "=========================================="
echo ""

# Verificar Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no está instalado"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ Python detectado: $(python3 --version)"

# Verificar versión mínima (3.10)
if [ "$(echo "$PYTHON_VERSION < 3.10" | bc)" -eq 1 ]; then
    echo "⚠️  Se recomienda Python 3.10 o superior (tienes $PYTHON_VERSION)"
fi

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo ""
    echo "▶ Creando entorno virtual..."
    python3 -m venv venv
    echo "✓ Entorno virtual creado"
else
    echo "✓ Entorno virtual ya existe"
fi

# Activar y instalar dependencias
echo ""
echo "▶ Instalando dependencias..."
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt

echo "✓ Dependencias instaladas"

# Hacer ejecutable
chmod +x deployer.py

# Crear directorios base en home
echo ""
echo "▶ Creando directorios en ~/local-deployer..."
mkdir -p ~/local-deployer/{logs,backups,certs,templates}

# Copiar config.json a home si no existe
if [ ! -f ~/local-deployer/config.json ]; then
    cp config.json ~/local-deployer/config.json
    echo "✓ Configuración inicial copiada"
fi

echo ""
echo "=========================================="
echo "  Instalación completada!"
echo "=========================================="
echo ""
echo "Siguiente paso:"
echo ""
echo "  1. Activa el entorno virtual:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Ejecuta LDM:"
echo "     python deployer.py --help"
echo ""
echo "  3. (Opcional) Crea un alias agregando esto a ~/.bashrc o ~/.zshrc:"
echo "     alias ldm='$(pwd)/deployer.py'"
echo ""
echo "  4. Verifica la instalación:"
echo "     python deployer.py version"
echo ""
