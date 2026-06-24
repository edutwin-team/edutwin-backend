"""
Groq LLM client — the LLM incarnates the DigitalTwin.

Flow for quiz:
  1. _take_quiz()   → LLM answers each question as the twin (structured JSON)
  2. _score_quiz()  → we check answers against is_correct, compute score
  3. _feedback()    → LLM writes a first-person review of its own performance

Flow for course:
  1. _read_course() → LLM reads and evaluates the course as the twin (structured JSON)
"""

import os
import json
import re
from groq import Groq, BadRequestError, RateLimitError

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY is not set. Add it to your .env file.")
        _client = Groq(api_key=api_key)
    return _client


def _chat(prompt: str, max_tokens: int = 1000, temperature: float = 0.5) -> str:
    client = _get_client()
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return (response.choices[0].message.content or "").strip()

    except BadRequestError as e:
        # Vérifie si l'erreur est liée à la taille du contexte
        if (
            "context_length" in str(e).lower()
            or "maximum context length" in str(e).lower()
        ):
            print(
                f"❌ Dépassement de la fenêtre de contexte (prompt + {max_tokens} tokens de sortie)."
            )
            print(f"Détails : {e}")
            # Ici, vous pouvez réduire le prompt ou diminuer max_tokens
        else:
            print(f"❌ Erreur de requête (400) : {e}")
        raise  # ou retournez un message d'erreur personnalisé

    except RateLimitError as e:
        # Cette exception couvre à la fois :
        # - le dépassement de requêtes/min (trop de calls)
        # - le dépassement du quota de tokens (limite journalière/mensuelle atteinte)
        print(f"⛔ Limite de taux ou quota de tokens dépassé(e).")
        print(f"Détails : {e}")
        # Vous pouvez examiner le corps de l'erreur pour plus de précision :
        # if "quota" in str(e).lower(): ...
        raise

    except groq.APIError as e:
        print(f"⚠️ Erreur API générique : {e}")
        raise


def _extract_json(text: str) -> dict | list:
    """Extract first JSON block from LLM output."""
    match = re.search(r"```json\s*([\s\S]*?)```", text)
    if match:
        return json.loads(match.group(1))
    # fallback: try raw parse
    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if match:
        return json.loads(match.group(1))
    raise ValueError(f"No JSON found in LLM output:\n{text}")


# ---------------------------------------------------------------------------
# Quiz simulation
# ---------------------------------------------------------------------------


def _build_twin_profile(twin) -> str:
    b = twin.behavior
    return f"""
Tu incarnes un élève numérique avec ce profil exact :
- Nom : {twin.name}
- Niveau de compréhension : {b.comprehension_level}/100
- Motivation : {b.motivation}/100
- Style d'apprentissage : {b.get_learning_style_display()}
- Vitesse d'apprentissage : {b.learning_speed}/100
- Taux d'erreur habituel : {b.error_rate}/100
- Niveau de fatigue : {b.fatigue_level}/100
- Niveau de stress : {b.stress_level}/100
- Rétention mémorielle : {b.memory_retention}/100
- Persévérance : {b.persistence_level}/100
- Curiosité : {b.curiosity_level}/100
- Autonomie : {b.autonomy_level}/100
Tes réponses doivent être cohérentes avec ce profil.
Un élève fatigué ou stressé fait plus d'erreurs.
Un élève très motivé et curieux lit attentivement les options.
""".strip()


def _build_questions_block(questions) -> str:
    lines = []
    for i, q in enumerate(questions, 1):
        answers = q.answers.all()
        lines.append(f"Q{i} [{q.difficulty_level}]: {q.text}")
        for j, a in enumerate(answers):
            lines.append(f"  {j + 1}. {a.text}")
    return "\n".join(lines)


def take_quiz_as_twin(twin, quiz) -> dict:
    """
    LLM incarnates the twin, answers every question, then gives feedback.

    Returns:
    {
        "answers": [{"question_index": 1, "chosen_index": 2, "reasoning": "..."}],
        "feedback": "...",
        "simulated_time_seconds": int
    }
    """
    questions = list(quiz.questions.prefetch_related("answers").all())
    if not questions:
        raise ValueError(f"Quiz '{quiz.title}' has no questions.")

    profile = _build_twin_profile(twin)
    questions_block = _build_questions_block(questions)

    prompt = f"""
{profile}

Tu vas passer le quiz suivant : "{quiz.title}"
Temps limite : {quiz.time_limit_minutes} minutes.

Voici les questions :
{questions_block}

Réponds en JSON structuré UNIQUEMENT selon ce format (pas de texte avant ni après) :
```json
{{
  "answers": [
    {{
      "question_index": 1,
      "chosen_index": 2,
      "reasoning": "Courte explication de pourquoi tu as choisi cette réponse, en restant cohérent avec ton profil."
    }}
  ],
  "simulated_time_seconds": 300,
  "feedback": "Feedback global en 3-4 phrases à la première personne sur ce quiz : difficulté perçue, ce qui était facile ou difficile, suggestions d'amélioration."
}}
```
Règles :
- chosen_index correspond au numéro de la réponse (1, 2, 3...) dans la liste affichée.
- simulated_time_seconds doit refléter ta vitesse d'apprentissage ({twin.behavior.learning_speed}/100) et le nombre de questions ({len(questions)}).
- Sois cohérent avec ton profil : fatigue={twin.behavior.fatigue_level}, erreur={twin.behavior.error_rate}, compréhension={twin.behavior.comprehension_level}.
""".strip()

    raw = _chat(prompt, max_tokens=1500, temperature=0.6)

    try:
        parsed = _extract_json(raw)
    except (ValueError, json.JSONDecodeError) as e:
        raise ValueError(f"LLM returned invalid JSON: {e}\nRaw output:\n{raw}")

    return {
        "questions": questions,
        "answers": parsed.get("answers", []),
        "feedback": parsed.get("feedback", ""),
        "simulated_time_seconds": int(parsed.get("simulated_time_seconds", 300)),
    }


def score_quiz_answers(questions, llm_answers: list) -> dict:
    """
    Compare LLM-chosen answers against is_correct flags.
    Returns score dict compatible with SimulationResult model.
    """
    correct_count = 0
    total = len(questions)

    for i, q in enumerate(questions, 1):
        answers = list(q.answers.all())
        # find what LLM chose for this question
        chosen = next(
            (a for a in llm_answers if a.get("question_index") == i),
            None,
        )
        if not chosen:
            continue

        chosen_idx = chosen.get("chosen_index", 0) - 1  # convert to 0-based
        if 0 <= chosen_idx < len(answers):
            if answers[chosen_idx].is_correct:
                correct_count += 1

    simulated_score = round((correct_count / total) * 100, 1) if total else 0.0
    passed = simulated_score >= quiz_passing_score_from_context(questions)

    return {
        "simulated_score": simulated_score,
        "correct": correct_count,
        "total": total,
        "passed": passed,
    }


def quiz_passing_score_from_context(questions) -> int:
    """Fallback — actual passing_score is passed in views.py."""
    return 50


def simulate_quiz_with_llm(twin, quiz) -> dict:
    """
    Full pipeline: LLM takes quiz → score computed → result dict returned.
    This replaces engine.simulate_quiz() entirely.
    """
    llm_result = take_quiz_as_twin(twin, quiz)

    score_data = score_quiz_answers(
        llm_result["questions"],
        llm_result["answers"],
    )
    # Override passed with actual passing_score
    score_data["passed"] = score_data["simulated_score"] >= quiz.passing_score

    b = twin.behavior
    return {
        **score_data,
        "simulated_time_seconds": llm_result["simulated_time_seconds"],
        "feedback": llm_result["feedback"],
        "llm_answers": llm_result["answers"],  # detailed per-question reasoning
        "behavior_snapshot": {
            "comprehension_level": b.comprehension_level,
            "motivation": b.motivation,
            "attention_level": b.attention_level,
            "memory_retention": b.memory_retention,
            "error_rate": b.error_rate,
            "fatigue_level": b.fatigue_level,
            "stress_level": b.stress_level,
            "learning_speed": b.learning_speed,
            "learning_style": b.learning_style,
            "persistence_level": b.persistence_level,
            "curiosity_level": b.curiosity_level,
        },
    }


# ---------------------------------------------------------------------------
# Course simulation
# ---------------------------------------------------------------------------


def simulate_course_with_llm(twin, course) -> dict:
    """
    LLM reads the course as the twin and gives a comprehension + feedback report.
    """
    profile = _build_twin_profile(twin)
    word_count = len(course.content.split()) if course.content else 0

    prompt = f"""
{profile}

Tu viens de lire le cours suivant : "{course.title}"

Contenu du cours :
\"\"\"
{course.content[:3000]}
\"\"\"

Réponds en JSON structuré UNIQUEMENT selon ce format :
```json
{{
  "comprehension_score": 72,
  "simulated_time_seconds": 240,
  "feedback": "Feedback en 3-4 phrases à la première personne : compréhension globale, ce qui était clair ou confus, suggestions d'amélioration du contenu."
}}
```
Règles :
- comprehension_score entre 0 et 100, cohérent avec ton profil (compréhension={twin.behavior.comprehension_level}, fatigue={twin.behavior.fatigue_level}).
- simulated_time_seconds basé sur ta vitesse de lecture ({twin.behavior.learning_speed}/100) et la longueur du cours ({word_count} mots).
""".strip()

    raw = _chat(prompt, max_tokens=600, temperature=0.6)

    try:
        parsed = _extract_json(raw)
    except (ValueError, json.JSONDecodeError) as e:
        raise ValueError(f"LLM returned invalid JSON: {e}\nRaw:\n{raw}")

    b = twin.behavior
    return {
        "simulated_score": float(parsed.get("comprehension_score", 50)),
        "simulated_time_seconds": int(parsed.get("simulated_time_seconds", 300)),
        "feedback": parsed.get("feedback", ""),
        "behavior_snapshot": {
            "comprehension_level": b.comprehension_level,
            "motivation": b.motivation,
            "attention_level": b.attention_level,
            "curiosity_level": b.curiosity_level,
            "fatigue_level": b.fatigue_level,
        },
    }
