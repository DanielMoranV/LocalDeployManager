# Local Deploy Manager (LDM)

Sistema de despliegue automatizado para proyectos web en red local. Soporta Laravel+Vue3 y SpringBoot+Vue3 con Docker, Nginx y SSL.

## Características

- Despliegue automatizado con un solo comando
- Soporte para Laravel (PHP 8.2) + Vue 3
- Soporte para SpringBoot (Java 21) + Vue 3
- Configuración automática de Docker Compose, Nginx y SSL
- Certificados HTTPS locales con mkcert
- Sistema de backups automáticos
- Gestión de variables de entorno
- Logs e historial de deploys
- Persistencia de datos entre deploys

## Requisitos del Sistema

### Linux (Recomendado)
- Python 3.10 o superior
- Docker y Docker Compose
- Git
- mkcert (se instalará automáticamente si no existe)

### Windows
- Python 3.10 o superior
- Docker Desktop
- Git
- mkcert

## Instalación

### 1. Clonar el repositorio
```bash
git clone <url-del-repo>
cd LocalDeployManager
```

### 2. Crear entorno virtual (recomendado)
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Hacer ejecutable (Linux/Mac)
```bash
chmod +x deployer.py
```

### 5. Crear alias (opcional pero recomendado)

**Linux/Mac** - Agregar a `~/.bashrc` o `~/.zshrc`:
```bash
alias ldm='/ruta/completa/a/deployer.py'
```

**O crear un symlink:**
```bash
sudo ln -s /ruta/completa/a/deployer.py /usr/local/bin/ldm
```

## Uso Básico

### Ver versión y ayuda
```bash
ldm version
ldm --help
```

### Inicializar un nuevo proyecto
```bash
ldm init \
  --stack laravel-vue \
  --domain miapp.local \
  --backend-repo https://github.com/user/backend.git \
  --frontend-repo https://github.com/user/frontend.git \
  --http-port 80 \
  --https-port 443
```

### Desplegar la aplicación
```bash
ldm deploy
```

### Ver estado de servicios
```bash
ldm status
```

### Ver configuración
```bash
ldm config show
```

## Comandos Disponibles

### Gestión del Proyecto
- `ldm init` - Inicializa un nuevo proyecto
- `ldm deploy` - Despliega la aplicación
- `ldm destroy` - Elimina el proyecto activo
- `ldm status` - Muestra estado de servicios
- `ldm start` - Inicia servicios
- `ldm stop` - Detiene servicios
- `ldm restart [servicio]` - Reinicia servicios

### Configuración
- `ldm config show` - Muestra configuración actual
- `ldm config edit` - Abre .env en editor
- `ldm config regen-keys` - Regenera claves de seguridad

### Backups
- `ldm backup create [--name NOMBRE]` - Crea un backup
- `ldm backup list` - Lista backups disponibles
- `ldm backup restore <id>` - Restaura un backup

### Logs e Historial
- `ldm logs [--follow] [servicio]` - Muestra logs
- `ldm history [show <id>]` - Historial de deploys

### Utilidades
- `ldm check-ports` - Verifica puertos disponibles
- `ldm shell <servicio>` - Abre shell en contenedor
- `ldm version` - Muestra versión

## Estructura de Directorios

```
~/local-deployer/
├── active-project/         # Proyecto activo
│   ├── backend/           # Código backend
│   ├── frontend/          # Código frontend
│   ├── docker-compose.yml
│   └── .project-config.json
├── backups/               # Backups de proyectos
├── logs/                  # Logs del sistema
├── certs/                 # Certificados SSL
├── config.json            # Configuración global
└── templates/             # Templates Docker/Nginx
```

## Ejemplos de Uso

### Proyecto Laravel + Vue
```bash
# Inicializar
ldm init \
  --stack laravel-vue \
  --domain mylaravel.local \
  --backend-repo git@github.com:user/laravel-api.git \
  --frontend-repo git@github.com:user/vue-frontend.git

# Editar variables de entorno si es necesario
ldm config edit

# Desplegar
ldm deploy --seed

# Ver logs
ldm logs --follow laravel
```

### Proyecto SpringBoot + Vue
```bash
# Inicializar
ldm init \
  --stack springboot-vue \
  --domain myspring.local \
  --backend-repo git@github.com:user/springboot-api.git \
  --frontend-repo git@github.com:user/vue-frontend.git

# Desplegar con base de datos fresca
ldm deploy --fresh-db --with-backup

# Ver estado
ldm status
```

## Desarrollo

### Estructura del Código
- `deployer.py` - Punto de entrada principal
- `src/cli.py` - Definición de comandos Click
- `src/logger.py` - Sistema de logging con Rich
- `src/utils.py` - Utilidades generales
- `src/docker_manager.py` - Gestión Docker (Fase 3)
- `src/git_manager.py` - Operaciones Git (Fase 3)
- `src/env_manager.py` - Gestión .env (Fase 2)
- `src/ssl_manager.py` - Certificados SSL (Fase 4)
- `src/port_manager.py` - Verificación puertos (Fase 2)
- `src/backup_manager.py` - Sistema backups (Fase 6)

### Testing
```bash
# Ejecutar con Python directamente
python deployer.py version

# Verificar comandos disponibles
python deployer.py --help
```

## Estado del Desarrollo

### ✅ Fase 1 - Estructura base y CLI (COMPLETO)
- [x] Configuración proyecto Python con Click
- [x] Estructura de directorios
- [x] Comandos básicos (version, help)
- [x] Sistema de logging con Rich

### 🔄 Próximas Fases
- [ ] Fase 2 - Gestión de configuración
- [ ] Fase 3 - Git y Docker
- [ ] Fase 4 - Comando init
- [ ] Fase 5 - Comando deploy
- [ ] Fase 6 - Sistema de backups
- [ ] Fase 7 - Logs e historial
- [ ] Fase 8 - Comandos adicionales
- [ ] Fase 9 - Testing
- [ ] Fase 10 - SpringBoot support

## Contribuir

Este proyecto está en desarrollo activo. Las contribuciones son bienvenidas.

## Licencia

MIT License

## Soporte

Para reportar bugs o solicitar features, abre un issue en el repositorio.
