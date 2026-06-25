#!/bin/bash

# ---------------------------------------------------------
# Script de démarrage pour l'environnement de développement
# ---------------------------------------------------------

# 1. Injection des variables UID et GID
# C'est crucial pour que le conteneur Docker ait les mêmes droits
# que ton utilisateur local sur les fichiers montés (volume .:/app).
export UID=$(id -u)
export GID=$(id -g)

echo "🚀 Démarrage de l'environnement EduTwin (DEV)..."
echo "👤 Utilisation de l'UID: $UID et GID: $GID"
echo "---------------------------------------------------"

# 2. Nettoyage (optionnel mais recommandé)
# Arrête et supprime les anciens conteneurs pour éviter les conflits
docker compose down

# 3. Build et lancement
# --build force la reconstruction de l'image si le Dockerfile ou requirements.txt a changé
docker compose up --build

# Note : Si tu préfères lancer en arrière-plan (mode détaché), remplace la ligne ci-dessus par :
# docker compose up --build -d
# echo "✅ Conteneurs lancés en arrière-plan. Tape 'docker compose logs -f' pour voir les logs."
