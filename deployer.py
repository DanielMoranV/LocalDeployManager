#!/usr/bin/env python3
"""
Local Deploy Manager (LDM)
Punto de entrada principal de la aplicación
"""

import sys
from pathlib import Path

# Agregar el directorio actual al path para imports
sys.path.insert(0, str(Path(__file__).parent))

from src.cli import main

if __name__ == '__main__':
    main()
