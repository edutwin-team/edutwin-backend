QUIZ_HEADER = [
    "Titre du quiz",
    "Description",
    "Score minimum (%)",
    "Temps limite (minutes)",
]

QUESTION_HEADER = [
    "Question",
    "Type de question",
    "Difficulté",
    "Réponse",
    "Bonne réponse",
]

QUESTION_TYPE_TO_FR = {
    "single_choice":   "Choix unique",
    "multiple_choice": "Choix multiple",
    "true_false":      "Vrai / Faux",
}

QUESTION_TYPE_FROM_ANY = {
    "choix unique": "single_choice",
    "choix multiple": "multiple_choice",
    "vrai / faux": "true_false",
    "single_choice": "single_choice",
    "multiple_choice": "multiple_choice",
    "true_false": "true_false",
}

DIFFICULTY_TO_FR = {
    "easy": "Facile",
    "medium": "Moyen",
    "hard": "Difficile",
}

DIFFICULTY_FROM_ANY = {
    "facile": "easy",
    "moyen": "medium",
    "difficile": "hard",
    "easy": "easy",
    "medium": "medium",
    "hard": "hard",
}

BOOL_TO_FR = {
    True:  "Vrai",
    False: "Faux",
}

BOOL_FROM_ANY = {
    "vrai": True,
    "oui":  True,
    "true": True,
    "1":  True,
    "faux": False,
    "non":  False,
    "false": False,
    "0": False,
}