# edutwin-backend

# 📘 Workflow Git pour le projet

## 1. Introduction

Ce document explique le **workflow Git recommandé** pour notre projet.  
Il est conçu pour :

- garder un historique clair et propre  
- éviter les conflits  
- faciliter la collaboration via GitHub et Jira  

---

## 2. Branches principales

### `main`

- Contient uniquement le code **stable**  
- **Jamais de commit direct**  
- Toute modification passe par une **Pull Request** (PR)

### `develop`

- Contient le code **en cours de développement**  
- Toutes les PR des features arrivent ici  
- Toujours mise à jour avant de commencer une nouvelle feature

### `feature/nom-fonction`

- Branches personnelles pour chaque fonctionnalité ou correction
-Ajputer le nom et numéro de ticket jira
- Exemple :  

```text
feature/login-EDT-10
feature/api-users-EDT-11
feature/dashboard-ui-EDT-12
```

## 3. Workflow quotidien

### 1️⃣ Mettre à jour develop avant de commencer

```
# Se placer sur develop
git checkout develop

# Récupérer les dernières modifications
git pull origin develop

# Créer sa branche feature
git checkout -b feature/ma-feature
```

### 2️⃣ Travailler sur la feature

```
# Ajouter les fichiers modifiés
git add .

# Commit avec message clair avec com et numéro de ticket jira
git commit -m "feat: ajouter formulaire de login EDT-15"

# Pousser la branche sur GitHub
git push -u origin feature/ma-feature
```

### 3️⃣ Ouvrir une Pull Request

Branche source → feature/ma-feature

Branche cible → develop

Titre PR clair et description détaillée qui sera le message de commit squashé

### 4️⃣ Mettre à jour sa branche si develop a avancé

Option Merge (simple) :

```
git checkout feature/ma-feature
git pull origin develop
git push
```

5️⃣ Merge de la PR

Squash and Merge par défaut

Chaque PR = 1 commit sur develop

Pas de merge commit ni de rebase direct sur develop

## 4. Fusion vers main (version stable)

Lorsque develop contient des features testées et stables, la fusion vers main doit se faire via une Pull Request selon les règles de protection :

Créer une Pull Request

Branche source : develop

Branche cible : main

Revue obligatoire

Au moins un reviewer doit approuver la Pull Request.

## 5. Conseils pour éviter les conflits

Toujours faire un pull de develop avant de créer une feature branch

Mettre à jour sa branche si develop avance pendant le développement

Faire des commits petits et clairs

Squash les commits avant le merge pour garder l’historique propre

## 8. Résumé visuel

```
main  ←── merge stable finalisé
  ↑
develop ←─ PR ← feature/a
         ← PR ← feature/b
         ← PR ← feature/c
         ← PR ← feature/d
         ← PR ← feature/e
         ← PR ← feature/f

✅ Workflow recommandé :

Feature branch → PR → develop → main

Squash and Merge pour garder un historique propre

Review obligatoire

Ne jamais push directement sur main ou develop
```

## Setup and launch
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
