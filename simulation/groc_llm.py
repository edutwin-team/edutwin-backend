# import os
# from groq import Groq

# client = Groq(api_key=os.environ["GROQ_API_KEY"])


# def generate_quiz_feedback(twin, quiz_result: dict) -> str:
#     prompt = f"""
# Tu es un jumeau numérique d'élève avec ce profil :
# - Niveau : {twin.level}/5
# - Style d'apprentissage : {twin.learning_style}
# - Domaines forts : {twin.strong_domains}
# - Domaines faibles : {twin.weak_domains}

# Tu viens de passer un quiz et voici tes résultats :
# - Score : {quiz_result["simulated_score"]}/100
# - Réponses correctes : {quiz_result["correct"]}/{quiz_result["total"]}
# - Temps passé : {quiz_result["simulated_time_seconds"]} secondes
# - Réussi : {quiz_result["passed"]}

# Donne un feedback court (3-4 phrases) en première personne sur ce quiz.
# Parle de ta perception de difficulté, ce que tu as trouvé facile ou difficile, 
# et si tu recommanderais des améliorations au contenu.
# """
#     response = client.chat.completions.create(
#         model="llama-3.1-8b-instant",
#         messages=[{"role": "user", "content": prompt}],
#         max_tokens=200,
#     )
#     return response.choices[0].message.content or "Aucun feedback pour ce quiz"


# def generate_course_feedback(twin, course, course_result: dict) -> str:
#     prompt = f"""
# Tu es un jumeau numérique d'élève avec ce profil :
# - Niveau : {twin.level}/5
# - Style d'apprentissage : {twin.learning_style}
# - Domaines forts : {twin.strong_domains}
# - Domaines faibles : {twin.weak_domains}

# Tu viens de lire un cours intitulé "{course.title}".
# - Compréhension estimée : {course_result["simulated_score"]}/100
# - Temps de lecture : {course_result["simulated_time_seconds"]} secondes

# Donne un feedback court (3-4 phrases) en première personne sur ce cours.
# Parle de ta compréhension, ce qui était clair ou confus,
# et si tu as des suggestions pour améliorer le contenu.
# """
#     response = client.chat.completions.create(
#         model="llama-3.1-8b-instant",
#         messages=[{"role": "user", "content": prompt}],
#         max_tokens=200,
#     )
#     return response.choices[0].message.content or "Aucun message pour ce cours"
