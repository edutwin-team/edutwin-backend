#!/bin/bash

# Script d'entrée pour Render
# Ce script s'exécute au démarrage du conteneur

echo "🚀 Démarrage du service backend EduTwin..."

# 1. Appliquer les migrations de base de données
echo "🗄️  Application des migrations..."
python manage.py migrate --noinput

# 2. Collecter les fichiers statiques
echo "📦 Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

# 3. Lancer le serveur Gunicorn
echo "🌐 Démarrage de Gunicorn sur le port $PORT..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2
