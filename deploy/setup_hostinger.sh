#!/bin/bash
# ==============================================================================
# SCRIPT DE INSTALACIÓN Y DESPLIEGUE AUTOMATIZADO EN HOSTINGER VPS
# ==============================================================================
set -e

echo "🚀 Iniciando despliegue de Polymarket M5 Bot en Hostinger VPS..."

# 1. Actualizar sistema e instalar paquetes básicos
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git ufw nginx certbot python3-certbot-nginx

# 2. Instalar Docker si no está presente
if ! command -v docker &> /dev/null; then
    echo "📦 Instalando Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo systemctl enable --now docker
    rm -f get-docker.sh
fi

# 3. Crear archivo .env si no existe
if [ ! -f .env ]; then
    echo "📄 Creando .env desde .env.example..."
    cp .env.example .env
fi

# 4. Desplegar contenedores Docker Compose
echo "🐳 Desplegando stack de Docker (Bot + PostgreSQL + Redis)..."
docker compose up -d --build

# 5. Configurar UFW Firewall
echo "🛡️ Configurando Firewall (UFW)..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

echo "✅ ¡Despliegue en Hostinger VPS completado con éxito!"
echo "Verifica los contenedores ejecutando: docker compose ps"
