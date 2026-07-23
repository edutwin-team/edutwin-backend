# Contribuer à EduTwin Backend

## Branches

| Branche | Rôle | Règles |
|---|---|---|
| `main` | Code stable (production) | Jamais de commit direct, PR + review obligatoires |
| `develop` | Intégration continue (dev) | PR uniquement, toujours à jour avant nouvelle feature |
| `feature/nom-EDT-XX` | Une feature/fix par branche | Nom + numéro de ticket Jira |

Exemples : `feature/login-EDT-10`, `feature/api-users-EDT-11`.

## Workflow quotidien

```bash
# 1. Partir d'un develop à jour
git checkout develop && git pull origin develop
git checkout -b feature/ma-feature-EDT-42

# 2. Travailler, commiter (le hook exige EDT-XXX dans le message)
git add .
git commit -m "feat: ajouter formulaire de login EDT-42"
git push -u origin feature/ma-feature-EDT-42

# 3. Si develop avance pendant le dev
git pull origin develop && git push
```

## Pull Requests

- Source `feature/...` → cible `develop` ; titre clair, description = futur message de commit squashé.
- **Squash and Merge** par défaut : 1 PR = 1 commit sur `develop`. Pas de merge commit ni rebase direct.
- Passage `develop` → `main` : PR dédiée, **au moins 1 review approuvée** (branch protection).

## Hooks git

Activer une fois : `git config core.hooksPath hooks`

- `pre-commit` : refuse tout commit contenant un fichier `.env`.
- `commit-msg` : refuse tout message sans référence `EDT-XXX`.

## Éviter les conflits

- Pull `develop` avant chaque nouvelle branche.
- Commits petits et fréquents, mise à jour régulière de sa branche.
- Squash avant merge pour un historique propre.

```
main    ←── PR (review obligatoire)
  ↑
develop ←── PR ← feature/a
          ← PR ← feature/b
```
