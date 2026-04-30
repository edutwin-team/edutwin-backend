# Titre + 1 phrase de description

Projet EDUTWIN, jumeau numérique d'élèves, évaluation de contenus pédagogiques.

## Stack — les technos choisies

Python 3.14
Postgres 17.6.1.111 (SUPABASE)

0.acLoading
0. excute git hooks:

   ```bash
   git config core.hooksPath hooks
   ```

1. Create a virtual environment:

   ```bash
   python -m venv .venv
   ```

1. Activate the virtual environment:

   - **Linux/macOS:**

     ```bash
     source .venv/bin/activate
     ```

   - **Windows (PowerShell / Command Prompt):**

     ```bash
     .venv\Scripts\activate
     ```

1. Install dependencies:

   ```bash
     pip install -r requirements.txt
   ```

1. Apply database migrations:

   ```bash
   python manage.py migrate
   ```

1. Run the Django development server:

   ```bash
   python manage.py runserver
   ```

   ```

The API will be available at `http://127.0.0.1:8000`.

To consult the OpenAPI documentation, visit `http://127.0.0.1:8000/api/docs/`.

## Tester — commande pour les tests

Implémenter pytest

## Architecture — lien vers docs/

Consulter: (/docs/architecture.md)

## Auteur — toi

Quentin GOUTTAYA
