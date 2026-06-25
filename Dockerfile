# 1. Image de base
FROM python:3.14-slim

# 2. Sécurité : Création d'un utilisateur non-root
# On crée un groupe et un utilisateur 'django' qui n'a pas les droits root
RUN groupadd -r django && useradd -r -g django django

WORKDIR /app

# 3. Installation des dépendances
COPY requirements.txt .
# On installe les dépendances + gunicorn (au cas où il n'est pas dans ton requirements.txt)
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# 4. Copie du code source
COPY . .

# 5. Permissions : On donne le ownership du dossier /app à l'utilisateur 'django'
# C'est CRUCIAL pour que collectstatic puisse écrire dans le dossier staticfiles
RUN chown -R django:django /app

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
# 6. On bascule sur l'utilisateur non-root pour toutes les opérations suivantes
USER django

# 7. Exposition du port (Informatif, Render l'ignore mais c'est une bonne pratique)
EXPOSE 8000

# 8. Commande par défaut
# Note: Render va écraser cette commande avec sa "Start Command", 
# mais c'est très utile si tu veux tester ton image en local en mode prod.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
