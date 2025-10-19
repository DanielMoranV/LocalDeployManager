# Local Deploy Manager (LDM) 🚀

> Sistema CLI profesional para automatizar despliegues de aplicaciones web full-stack en entornos de desarrollo local.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/Docker-Required-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-success.svg)]()

## ✨ Características Principales

- **Despliegue Automatizado**: De código a aplicación corriendo en minutos
- **Multi-Stack**: Laravel+Vue3 y SpringBoot+Vue3 completamente soportados
- **Docker Integrado**: Configuración automática de Docker Compose, Nginx, MySQL/PostgreSQL, Redis
- **HTTPS Local**: Certificados SSL automáticos con mkcert
- **Sistema de Backups**: Backup y restore completo de proyectos y bases de datos
- **Git Integration**: Pull automático, detección de cambios, commits tracking
- **Historial de Deploys**: Registro completo de todos los despliegues
- **CLI Profesional**: Interface rich con colores, tablas y progress bars
- **Cross-Platform**: Linux, macOS y Windows

## 🎯 Casos de Uso

LDM es perfecto para:
- **Desarrollo Local**: Setup rápido de proyectos full-stack
- **Testing**: Entornos aislados con Docker
- **Demos**: Desplegar aplicaciones rápidamente para presentaciones
- **Onboarding**: Nuevos desarrolladores productivos en minutos
- **Múltiples Proyectos**: Cambiar entre proyectos fácilmente

## 📋 Requisitos del Sistema

### Requerido
- **Python**: 3.10 o superior
- **Docker**: 20.10+ y Docker Compose
- **Git**: 2.x o superior

### Opcional
- **mkcert**: Para certificados SSL (se instala automáticamente si falta)

### Por Sistema Operativo

**Linux (Recomendado)**
```bash
sudo apt update
sudo apt install python3 python3-pip docker.io docker-compose git
sudo usermod -aG docker $USER  # Agregar usuario a grupo docker
```

**macOS**
```bash
brew install python3 git docker docker-compose mkcert
```

**Windows**
- Python 3.10+ desde [python.org](https://www.python.org/)
- Docker Desktop desde [docker.com](https://www.docker.com/)
- Git desde [git-scm.com](https://git-scm.com/)

## 🚀 Instalación

### Opción 1: Instalación Rápida (Recomendada)

```bash
# Clonar repositorio
git clone https://github.com/DanielMoranV/LocalDeployManager.git
cd LocalDeployManager

# Ejecutar script de instalación
./setup.sh

# Activar entorno virtual
source venv/bin/activate

# Verificar instalación
ldm version
```

### Opción 2: Instalación Manual

```bash
# Clonar repositorio
git clone https://github.com/DanielMoranV/LocalDeployManager.git
cd LocalDeployManager

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Hacer ejecutable
chmod +x deployer.py  # Linux/Mac

# Crear alias global (opcional)
echo "alias ldm='$(pwd)/deployer.py'" >> ~/.bashrc
source ~/.bashrc
```

## 📚 Guía de Uso Rápida

### 1. Inicializar un Proyecto

```bash
ldm init \
  --stack laravel-vue \
  --domain myapp.local \
  --backend-repo git@github.com:user/laravel-api.git \
  --frontend-repo git@github.com:user/vue-frontend.git
```

**Opciones disponibles**:
- `--stack`: `laravel-vue` o `springboot-vue`
- `--domain`: Dominio local (ej: myapp.local)
- `--backend-repo`: URL del repositorio backend
- `--frontend-repo`: URL del repositorio frontend
- `--http-port`: Puerto HTTP (default: 80)
- `--https-port`: Puerto HTTPS (default: 443)
- `--name`: Nombre del proyecto (default: auto-generado)

### 2. Desplegar la Aplicación

```bash
# Deploy básico
ldm deploy

# Deploy con opciones
ldm deploy --fresh-db --seed --with-backup
```

**Opciones de deploy**:
- `--fresh-db`: Recrear base de datos desde cero
- `--seed`: Ejecutar seeders después de migraciones
- `--with-backup`: Crear backup antes de deployar
- `--no-pull`: No hacer git pull
- `--no-deps`: No instalar dependencias
- `--no-build`: No compilar frontend

### 3. Gestionar Servicios

```bash
# Ver estado
ldm status

# Iniciar servicios
ldm start

# Detener servicios
ldm stop

# Reiniciar todos los servicios
ldm restart

# Reiniciar servicio específico
ldm restart nginx
ldm restart php
ldm restart mysql
```

### 4. Debugging y Logs

```bash
# Ver logs de todos los servicios
ldm logs

# Seguir logs en tiempo real
ldm logs --follow

# Ver logs de un servicio específico
ldm logs nginx
ldm logs php --tail 50

# Acceder a shell de contenedor
ldm shell php
ldm shell mysql
```

### 5. Backups

```bash
# Crear backup
ldm backup create

# Crear backup con nombre
ldm backup create --name "before-migration"

# Listar backups
ldm backup list

# Restaurar backup
ldm backup restore 20251019_143000
```

### 6. Historial

```bash
# Ver historial de deploys
ldm history

# Ver últimos 10 deploys
ldm history --limit 10

# Ver detalles de un deploy
ldm history 5
```

## 📖 Comandos Completos

### Gestión de Proyectos

| Comando | Descripción |
|---------|-------------|
| `ldm init` | Inicializa nuevo proyecto |
| `ldm deploy` | Despliega la aplicación |
| `ldm status` | Muestra estado de servicios |
| `ldm start` | Inicia todos los servicios |
| `ldm stop` | Detiene servicios (preserva datos) |
| `ldm restart [service]` | Reinicia servicios |
| `ldm destroy` | Elimina proyecto completo |

### Configuración

| Comando | Descripción |
|---------|-------------|
| `ldm config show` | Muestra configuración actual |
| `ldm config edit` | Abre .env en editor |
| `ldm config edit --project` | Edita config del proyecto |
| `ldm config regen-keys` | Regenera claves de seguridad |

### Backups y Historial

| Comando | Descripción |
|---------|-------------|
| `ldm backup create [--name]` | Crea backup |
| `ldm backup list` | Lista backups |
| `ldm backup restore <id>` | Restaura backup |
| `ldm history` | Historial de deploys |
| `ldm history <id>` | Detalles de un deploy |

### Logs y Debugging

| Comando | Descripción |
|---------|-------------|
| `ldm logs [service]` | Muestra logs |
| `ldm logs -f [service]` | Logs en tiempo real |
| `ldm logs --tail N [service]` | Últimas N líneas |
| `ldm shell <service>` | Shell interactivo |

### Utilidades

| Comando | Descripción |
|---------|-------------|
| `ldm check-ports` | Verifica puertos |
| `ldm version` | Muestra versión |
| `ldm --help` | Ayuda general |
| `ldm <comando> --help` | Ayuda de comando |

## 🏗️ Arquitectura del Proyecto

### Estructura de Directorios

```
LocalDeployManager/
├── deployer.py              # Punto de entrada
├── requirements.txt         # Dependencias Python
├── setup.sh                 # Script de instalación
├── config.json              # Configuración global
│
├── src/                     # Código fuente (4766 líneas)
│   ├── cli.py               # Comandos CLI (~1600 líneas)
│   ├── logger.py            # Sistema de logging
│   ├── utils.py             # Utilidades generales
│   ├── models.py            # Modelos Pydantic
│   ├── env_manager.py       # Gestión .env
│   ├── port_manager.py      # Verificación puertos
│   ├── git_manager.py       # Operaciones Git
│   ├── docker_manager.py    # Gestión Docker
│   ├── template_manager.py  # Renderizado templates
│   ├── ssl_manager.py       # Certificados SSL
│   ├── backup_manager.py    # Sistema de backups
│   └── history_manager.py   # Historial de deploys
│
├── templates/               # Templates Jinja2
│   ├── laravel-vue/
│   │   ├── docker-compose.yml.j2
│   │   ├── nginx.conf.j2
│   │   ├── Dockerfile.php
│   │   └── .env.template
│   └── springboot-vue/
│       ├── docker-compose.yml.j2
│       ├── nginx.conf.j2
│       ├── Dockerfile.java
│       └── .env.template
│
├── test_phase2.py           # Tests Fase 2
├── test_phase3.py           # Tests Fase 3
│
└── docs/                    # Documentación
    ├── FASE1_RESUMEN.md
    ├── FASE2_RESUMEN.md
    ├── FASE3_RESUMEN.md
    ├── FASE8_RESUMEN.md
    └── PROYECTO_RESUMEN.md
```

### Directorio de Usuario (Runtime)

```
~/local-deployer/
├── active-project/          # Proyecto activo
│   ├── backend/             # Código backend (Git)
│   ├── frontend/            # Código frontend (Git)
│   ├── docker-compose.yml   # Generado por LDM
│   ├── nginx.conf           # Generado por LDM
│   ├── Dockerfile.php|java  # Copiado por LDM
│   ├── .project-config.json # Metadata del proyecto
│   ├── .credentials.json    # Credenciales (DB, etc.)
│   └── deploy-history.json  # Historial de deploys
│
├── backups/                 # Backups de proyectos
│   └── 20251019_143000/
│       ├── backend/
│       ├── frontend/
│       ├── database_backup.sql
│       └── backup-metadata.json
│
├── logs/                    # Logs del sistema
│   └── deployer.log
│
├── certs/                   # Certificados SSL
│   └── myapp.local/
│       ├── myapp.local.pem
│       └── myapp.local-key.pem
│
└── config.json              # Configuración global
```

## 🔥 Ejemplos Completos

### Ejemplo 1: Proyecto Laravel + Vue

```bash
# 1. Inicializar proyecto
ldm init \
  --stack laravel-vue \
  --domain laravel-shop.local \
  --backend-repo git@github.com:company/shop-api.git \
  --frontend-repo git@github.com:company/shop-frontend.git

# 2. Revisar configuración generada
ldm config show

# 3. Editar .env si es necesario
ldm config edit

# 4. Desplegar con seed de datos
ldm deploy --seed

# 5. Ver estado
ldm status

# 6. Acceder a la aplicación
# https://laravel-shop.local

# 7. Ver logs
ldm logs -f php

# 8. Ejecutar comandos artisan
ldm shell php
php artisan migrate:status
php artisan cache:clear
exit

# 9. Crear backup antes de cambios importantes
ldm backup create --name "before-refactor"

# 10. Ver historial de deploys
ldm history
```

### Ejemplo 2: Proyecto SpringBoot + Vue

```bash
# 1. Inicializar
ldm init \
  --stack springboot-vue \
  --domain spring-api.local \
  --backend-repo git@github.com:company/api.git \
  --frontend-repo git@github.com:company/admin-panel.git

# 2. Deploy con base de datos fresca
ldm deploy --fresh-db --with-backup

# 3. Ver logs de todos los servicios
ldm logs

# 4. Acceder a PostgreSQL
ldm shell postgres
psql -U postgres -d springboot_db
\dt
\q
exit

# 5. Reiniciar backend después de cambios
ldm restart springboot

# 6. Ver historial
ldm history --limit 5
```

### Ejemplo 3: Workflow de Desarrollo

```bash
# Día 1: Setup inicial
ldm init --stack laravel-vue --domain myapp.local \
  --backend-repo <url> --frontend-repo <url>
ldm deploy --seed

# Día 2-N: Desarrollo
# ... hacer cambios en código ...
ldm deploy  # Pull + build + migrate + restart

# Crear backup antes de cambios importantes
ldm backup create --name "before-big-feature"

# Ver logs en tiempo real mientras desarrollas
ldm logs -f

# Acceder a contenedores cuando necesitas
ldm shell php
ldm shell mysql

# Ver historial de deploys
ldm history

# Fin del día: detener servicios
ldm stop
```

## 🛠️ Tecnologías Utilizadas

### Core
- **Python 3.10+**: Lenguaje principal
- **Click**: Framework CLI
- **Rich**: Terminal UI (colores, tablas, progress bars)
- **Pydantic**: Validación de datos

### Gestión de Datos
- **python-dotenv**: Gestión .env
- **PyYAML**: Parsing YAML
- **GitPython**: Operaciones Git

### Infraestructura
- **Docker**: Containerización
- **Docker Compose**: Orquestación de servicios
- **Nginx**: Web server y reverse proxy
- **mkcert**: Certificados SSL locales

### Stacks Soportados

#### Laravel + Vue
- PHP 8.2 (FPM Alpine)
- Laravel 10.x
- MySQL 8.0
- Redis Alpine
- Nginx
- Vue 3 + Vite
- Composer + NPM

#### SpringBoot + Vue
- Java 21 (Eclipse Temurin)
- SpringBoot 3.x
- PostgreSQL 16
- Redis Alpine
- Nginx
- Vue 3 + Vite
- Maven + NPM

## ⚙️ Configuración Avanzada

### Variables de Entorno

Las variables se generan automáticamente durante `ldm init`, pero puedes editarlas:

```bash
ldm config edit
```

**Variables Clave (Laravel)**:
- `APP_KEY`: Clave de encriptación Laravel
- `JWT_SECRET`: Secreto para tokens JWT
- `DB_HOST`, `DB_DATABASE`, `DB_USERNAME`, `DB_PASSWORD`
- `REDIS_HOST`, `REDIS_PORT`

**Variables Clave (SpringBoot)**:
- `SPRING_DATASOURCE_URL`
- `SPRING_DATASOURCE_USERNAME`, `SPRING_DATASOURCE_PASSWORD`
- `JWT_SECRET`
- `REDIS_HOST`, `REDIS_PORT`

### Puertos Personalizados

```bash
ldm init \
  --stack laravel-vue \
  --domain myapp.local \
  --http-port 8080 \
  --https-port 8443 \
  --backend-repo <url> \
  --frontend-repo <url>
```

### Regenerar Claves de Seguridad

```bash
ldm config regen-keys
```

Esto regenera:
- `APP_KEY` (Laravel)
- `JWT_SECRET`

⚠️ **Nota**: Esto invalidará sesiones existentes.

## 📊 Estadísticas del Proyecto

- **Líneas de Código**: ~4766 líneas Python
- **Módulos**: 12 archivos Python
- **Templates**: 8 templates (Docker, Nginx, Dockerfiles)
- **Tests**: 40+ tests automatizados
- **Comandos**: 16 comandos CLI funcionales
- **Fases Completadas**: 9/10 (90%)

## 🐛 Troubleshooting

### Problema: Puerto ocupado

```bash
# Ver puertos ocupados
ldm check-ports

# Liberar puerto o usar puerto alternativo
ldm init --http-port 8080 --https-port 8443 ...
```

### Problema: Docker no está corriendo

```bash
# Linux
sudo systemctl start docker

# macOS/Windows
# Iniciar Docker Desktop
```

### Problema: mkcert no instalado

```bash
# Linux (Ubuntu/Debian)
sudo apt install libnss3-tools
wget https://github.com/FiloSottile/mkcert/releases/latest/download/mkcert-v*-linux-amd64
chmod +x mkcert-v*-linux-amd64
sudo mv mkcert-v*-linux-amd64 /usr/local/bin/mkcert

# macOS
brew install mkcert

# Windows
choco install mkcert
```

### Problema: Servicios no inician

```bash
# Ver logs para diagnosticar
ldm logs

# Verificar estado detallado
ldm status

# Reconstruir contenedores
ldm destroy
ldm init ...
ldm deploy
```

### Problema: Base de datos corrupta

```bash
# Restaurar desde backup
ldm backup list
ldm backup restore <backup-id>

# O recrear desde cero
ldm deploy --fresh-db --seed
```

## 🤝 Contribuir

Las contribuciones son bienvenidas! Por favor:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo `LICENSE` para más detalles.

## 👥 Autores

- **Desarrollo Principal** - [Daniel Moran Vilchez](https://github.com/DanielMoranV)

## 🙏 Agradecimientos

- Click y Rich por excelentes librerías CLI
- Docker por simplificar deployments
- mkcert por certificados SSL locales fáciles
- Comunidad open source

## 📞 Soporte

- **Issues**: [GitHub Issues](https://github.com/DanielMoranV/LocalDeployManager/issues)
- **Documentación**: Ver carpeta `docs/`
- **Email**: tu-email@ejemplo.com

---

**Made with ❤️ for developers who value their time**

*De horas de configuración manual a minutos de automatización* ⚡
