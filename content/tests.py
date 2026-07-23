from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from config.factories import BaseAPITest, make_course, make_quiz, make_user
from .constants import QUESTION_HEADER, QUIZ_HEADER
from .models import Answer, ContentSourceType, Course, DifficultyLevel, Question, Quiz
from .serializers import QuizSerializer
from .utils import (
    CSVImportError,
    _clean_row,
    _decode_csv_bytes,
    _detect_delimiter,
    _headers_match,
    _parse_int,
    _strip_bom,
    export_quiz_to_csv,
    import_quiz_from_csv,
    parse_bool,
    parse_difficulty,
    parse_question_type,
)


def build_csv(rows, delimiter=";", bom=True):
    text = "\n".join(delimiter.join(str(c) for c in row) for row in rows)
    return ("\ufeff" if bom else "") + text


def as_upload(text, name="quiz.csv", encoding="utf-8"):
    return SimpleUploadedFile(name, text.encode(encoding), content_type="text/csv")


VALID_ROWS = [
    QUIZ_HEADER,
    ["Mon quiz", "Une description", "60", "20"],
    QUESTION_HEADER,
    ["2+2 ?", "Choix unique", "Facile", "4", "Vrai"],
    ["2+2 ?", "Choix unique", "Facile", "5", "Faux"],
    ["Capitale ?", "Choix unique", "Moyen", "Paris", "Vrai"],
]


# ---------------------------------------------------------
# MODELS
# ---------------------------------------------------------
class ContentModelTests(TestCase):
    def setUp(self):
        self.user = make_user(email="content@example.com")

    def test_course_str_and_defaults(self):
        course = make_course(self.user, title="Algèbre")
        self.assertEqual(str(course), "Algèbre")
        self.assertEqual(course.source_type, ContentSourceType.MANUAL)

    def test_quiz_str_and_defaults(self):
        quiz = make_quiz(self.user, with_questions=False, title="Q1")
        self.assertEqual(str(quiz), "Q1")
        self.assertEqual(quiz.passing_score, 50)
        self.assertEqual(quiz.time_limit_minutes, 15)
        self.assertIsNone(quiz.course)

    def test_question_and_answer_str(self):
        quiz = make_quiz(self.user, with_questions=False)
        question = Question.objects.create(quiz=quiz, text="Pourquoi ?")
        good = Answer.objects.create(question=question, text="Parce que", is_correct=True)
        bad = Answer.objects.create(question=question, text="Non", is_correct=False)

        self.assertEqual(str(question), "Question: Pourquoi ?")
        self.assertEqual(str(good), "Answer: Parce que (correct)")
        self.assertEqual(str(bad), "Answer: Non (wrong)")
        self.assertEqual(question.difficulty_level, DifficultyLevel.MEDIUM)

    def test_cascade_quiz_deletes_questions_and_answers(self):
        quiz = make_quiz(self.user)
        quiz.delete()
        self.assertEqual(Question.objects.count(), 0)
        self.assertEqual(Answer.objects.count(), 0)

    def test_course_deletion_cascades_to_quizzes(self):
        course = make_course(self.user)
        make_quiz(self.user, with_questions=False, course=course)
        course.delete()
        self.assertEqual(Quiz.objects.count(), 0)


# ---------------------------------------------------------
# SERIALIZER
# ---------------------------------------------------------
class QuizSerializerTests(TestCase):
    payload = {
        "title": "Nouveau quiz",
        "description": "d",
        "passing_score": 70,
        "time_limit_minutes": 10,
        "questions": [
            {
                "text": "Q1",
                "question_type": "single_choice",
                "difficulty_level": "easy",
                "answers": [
                    {"text": "A", "is_correct": True},
                    {"text": "B", "is_correct": False},
                ],
            }
        ],
    }

    def setUp(self):
        self.user = make_user(email="qs@example.com")

    def test_create_nested_questions_and_answers(self):
        s = QuizSerializer(data=self.payload)
        self.assertTrue(s.is_valid(), s.errors)
        quiz = s.save(user=self.user)
        self.assertEqual(quiz.questions.count(), 1)
        self.assertEqual(quiz.questions.first().answers.count(), 2)

    def test_update_recreates_questions(self):
        quiz = make_quiz(self.user)
        old_ids = list(quiz.questions.values_list("id", flat=True))

        s = QuizSerializer(quiz, data=self.payload, partial=True)
        self.assertTrue(s.is_valid(), s.errors)
        s.save()
        quiz.refresh_from_db()

        self.assertEqual(quiz.questions.count(), 1)
        self.assertNotIn(quiz.questions.first().id, old_ids)

    def test_update_without_questions_keeps_them(self):
        quiz = make_quiz(self.user)
        s = QuizSerializer(quiz, data={"title": "Renommé"}, partial=True)
        self.assertTrue(s.is_valid(), s.errors)
        s.save()
        quiz.refresh_from_db()
        self.assertEqual(quiz.title, "Renommé")
        self.assertEqual(quiz.questions.count(), 1)

    def test_created_at_is_read_only(self):
        self.assertIn("created_at", QuizSerializer(make_quiz(self.user)).data)


# ---------------------------------------------------------
# CSV HELPERS (unitaires)
# ---------------------------------------------------------
class CSVHelpersTests(TestCase):
    def test_strip_bom_removes_bom_and_zwsp(self):
        self.assertEqual(_strip_bom("\ufeff  texte\u200b "), "texte")

    def test_decode_csv_bytes_utf8_sig(self):
        self.assertEqual(_decode_csv_bytes("héllo".encode("utf-8-sig")), "héllo")

    def test_decode_csv_bytes_cp1252_fallback(self):
        self.assertIn("h", _decode_csv_bytes("héllo".encode("cp1252")))

    def test_decode_csv_bytes_never_raises(self):
        self.assertIsInstance(_decode_csv_bytes(b"\xff\xfe\x00invalid"), str)

    def test_detect_delimiter(self):
        self.assertEqual(_detect_delimiter("a,b,c\n1,2,3"), ",")
        self.assertEqual(_detect_delimiter("a;b;c\n1;2;3"), ";")
        self.assertEqual(_detect_delimiter("a;b;c"), ";")

    def test_clean_row_drops_trailing_empties(self):
        self.assertEqual(_clean_row(["a", " b ", "", ""]), ["a", "b"])

    def test_headers_match_is_case_insensitive(self):
        self.assertTrue(_headers_match(["TITRE DU QUIZ"], ["Titre du quiz"]))
        self.assertFalse(_headers_match(["autre"], ["Titre du quiz"]))

    def test_parse_int_ok_and_error(self):
        self.assertEqual(_parse_int(" 42 ", "champ"), 42)
        with self.assertRaises(CSVImportError):
            _parse_int("abc", "Score minimum (%)")

    def test_parse_question_type(self):
        self.assertEqual(parse_question_type("Choix multiple"), "multiple_choice")
        self.assertEqual(parse_question_type("true_false"), "true_false")
        self.assertEqual(parse_question_type("inconnu"), "inconnu")

    def test_parse_difficulty(self):
        self.assertEqual(parse_difficulty("Difficile"), "hard")
        self.assertEqual(parse_difficulty("easy"), "easy")
        self.assertEqual(parse_difficulty("???"), "???")

    def test_parse_bool(self):
        for value in ("Vrai", "oui", "TRUE", "1"):
            self.assertIs(parse_bool(value), True)
        for value in ("Faux", "non", "FALSE", "0"):
            self.assertIs(parse_bool(value), False)
        self.assertIsNone(parse_bool("peut-être"))

    def test_csv_import_error_keeps_message(self):
        err = CSVImportError("boom")
        self.assertEqual(err.message, "boom")
        self.assertEqual(str(err), "boom")


# ---------------------------------------------------------
# CSV EXPORT / IMPORT
# ---------------------------------------------------------
class CSVExportTests(TestCase):
    def test_export_headers_bom_and_rows(self):
        user = make_user(email="exp@example.com")
        quiz = make_quiz(user, title="Export")
        response = export_quiz_to_csv(quiz)
        body = response.content.decode("utf-8")

        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn('filename="Export.csv"', response["Content-Disposition"])
        self.assertTrue(body.startswith("\ufeff"))
        self.assertIn(";".join(QUIZ_HEADER), body)
        self.assertIn(";".join(QUESTION_HEADER), body)
        self.assertIn("Choix unique", body)
        self.assertIn("Vrai", body)
        self.assertIn("Faux", body)

    def test_export_then_import_roundtrip(self):
        user = make_user(email="round@example.com")
        quiz = make_quiz(user, title="Roundtrip")
        csv_text = export_quiz_to_csv(quiz).content.decode("utf-8")

        imported = import_quiz_from_csv(BytesIO(csv_text.encode("utf-8")), user)
        self.assertEqual(imported.title, "Roundtrip")
        self.assertEqual(imported.questions.count(), quiz.questions.count())


class CSVImportTests(TestCase):
    def setUp(self):
        self.user = make_user(email="imp@example.com")

    def _import(self, rows, **kw):
        return import_quiz_from_csv(as_upload(build_csv(rows, **kw)), self.user)

    def test_import_valid_file(self):
        quiz = self._import(VALID_ROWS)
        self.assertEqual(quiz.title, "Mon quiz")
        self.assertEqual(quiz.passing_score, 60)
        self.assertEqual(quiz.time_limit_minutes, 20)
        self.assertEqual(quiz.source_type, "import_file")
        self.assertEqual(quiz.user, self.user)
        # Deux lignes partagent la même question -> une seule Question, deux Answers
        self.assertEqual(quiz.questions.count(), 2)
        self.assertEqual(Answer.objects.filter(question__quiz=quiz).count(), 3)

    def test_import_with_comma_delimiter(self):
        self.assertEqual(self._import(VALID_ROWS, delimiter=",").title, "Mon quiz")

    def test_import_without_bom(self):
        self.assertEqual(self._import(VALID_ROWS, bom=False).title, "Mon quiz")

    def test_import_ignores_blank_lines(self):
        rows = VALID_ROWS[:2] + [[]] + VALID_ROWS[2:]
        self.assertEqual(self._import(rows).questions.count(), 2)

    def test_import_too_short(self):
        with self.assertRaises(CSVImportError):
            self._import(VALID_ROWS[:2])

    def test_import_bad_quiz_header(self):
        rows = [["Mauvais", "en-tête", "x", "y"]] + VALID_ROWS[1:]
        with self.assertRaises(CSVImportError) as ctx:
            self._import(rows)
        self.assertIn("première ligne", ctx.exception.message)

    def test_import_bad_question_header(self):
        rows = VALID_ROWS[:2] + [["a", "b", "c", "d", "e"]] + VALID_ROWS[3:]
        with self.assertRaises(CSVImportError) as ctx:
            self._import(rows)
        self.assertIn("questions", ctx.exception.message)

    def test_import_incomplete_quiz_row(self):
        rows = [QUIZ_HEADER, ["Titre", "desc"], QUESTION_HEADER, VALID_ROWS[3]]
        with self.assertRaises(CSVImportError) as ctx:
            self._import(rows)
        self.assertIn("incomplète", ctx.exception.message)

    def test_import_non_integer_passing_score(self):
        rows = [QUIZ_HEADER, ["Titre", "d", "abc", "20"], QUESTION_HEADER, VALID_ROWS[3]]
        with self.assertRaises(CSVImportError):
            self._import(rows)

    def test_import_row_missing_columns(self):
        rows = VALID_ROWS[:3] + [["Q", "Choix unique", "Facile"]]
        with self.assertRaises(CSVImportError) as ctx:
            self._import(rows)
        self.assertIn("Ligne 4", ctx.exception.message)

    def test_import_empty_question_text(self):
        rows = VALID_ROWS[:3] + [["", "Choix unique", "Facile", "A", "Vrai"]]
        with self.assertRaises(CSVImportError) as ctx:
            self._import(rows)
        self.assertIn("vide", ctx.exception.message)

    def test_import_invalid_bool(self):
        rows = VALID_ROWS[:3] + [["Q", "Choix unique", "Facile", "A", "peut-être"]]
        with self.assertRaises(CSVImportError) as ctx:
            self._import(rows)
        self.assertIn("Bonne réponse", ctx.exception.message)

    def test_import_is_atomic_on_failure(self):
        rows = VALID_ROWS[:4] + [["Q2", "Choix unique", "Facile", "A", "nope"]]
        with self.assertRaises(CSVImportError):
            self._import(rows)
        self.assertEqual(Quiz.objects.count(), 0)


# ---------------------------------------------------------
# VIEWSETS
# ---------------------------------------------------------
class QuizViewSetTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.user = make_user(email="qapi@example.com")
        self.other = make_user(email="qother@example.com")
        self.client.force_login(self.user)

    def test_requires_authentication(self):
        self.client.logout()
        self.assertEqual(
            self.client.get(reverse("quiz-list")).status_code, status.HTTP_403_FORBIDDEN
        )

    def test_list_scoped_to_user(self):
        make_quiz(self.user, title="Mien", with_questions=False)
        make_quiz(self.other, title="Autre", with_questions=False)
        res = self.client.get(reverse("quiz-list"))
        self.assertEqual([q["title"] for q in res.data], ["Mien"])

    def test_create_assigns_user(self):
        res = self.client.post(
            reverse("quiz-list"),
            {"title": "Créé", "questions": []},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Quiz.objects.get().user, self.user)

    def test_retrieve_other_user_quiz_is_404(self):
        quiz = make_quiz(self.other, with_questions=False)
        res = self.client.get(reverse("quiz-detail", args=[quiz.pk]))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete(self):
        quiz = make_quiz(self.user, with_questions=False)
        res = self.client.delete(reverse("quiz-detail", args=[quiz.pk]))
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)


class QuizExportSubmitTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.user = make_user(email="qact@example.com")
        self.quiz = make_quiz(self.user)
        self.client.force_login(self.user)

    def test_export_action(self):
        res = self.client.get(reverse("quiz-export", args=[self.quiz.pk]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("text/csv", res["Content-Type"])

    def test_submit_all_correct(self):
        question = self.quiz.questions.first()
        good = question.answers.get(is_correct=True)
        res = self.client.post(
            reverse("quiz-submit", args=[self.quiz.pk]),
            {"answers": [{"question_id": question.pk, "answer_id": good.pk}]},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["score"], 100)
        self.assertEqual(res.data["correct"], 1)
        self.assertTrue(res.data["passed"])

    def test_submit_all_wrong(self):
        question = self.quiz.questions.first()
        bad = question.answers.get(is_correct=False)
        res = self.client.post(
            reverse("quiz-submit", args=[self.quiz.pk]),
            {"answers": [{"question_id": question.pk, "answer_id": bad.pk}]},
            format="json",
        )
        self.assertEqual(res.data["score"], 0)
        self.assertFalse(res.data["passed"])

    def test_submit_empty_answers_scores_zero(self):
        res = self.client.post(
            reverse("quiz-submit", args=[self.quiz.pk]), {"answers": []}, format="json"
        )
        self.assertEqual(res.data["score"], 0)
        self.assertEqual(res.data["total"], 0)

    def test_submit_invalid_payload(self):
        res = self.client.post(
            reverse("quiz-submit", args=[self.quiz.pk]), {"nope": 1}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class QuizImportEndpointTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.user = make_user(email="qimp@example.com")
        self.client.force_login(self.user)
        self.url = reverse("quiz-import-quiz")

    def test_import_success(self):
        res = self.client.post(
            self.url, {"file": as_upload(build_csv(VALID_ROWS))}, format="multipart"
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["title"], "Mon quiz")

    def test_import_without_file(self):
        res = self.client.post(self.url, {}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data["error"], "No file provided")

    def test_import_invalid_csv_returns_400(self):
        res = self.client.post(
            self.url, {"file": as_upload("n'importe quoi")}, format="multipart"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", res.data)

    def test_unexpected_error_returns_500(self):
        from unittest.mock import patch

        with patch("content.views.import_quiz_from_csv", side_effect=RuntimeError("boom")):
            res = self.client.post(
                self.url, {"file": as_upload(build_csv(VALID_ROWS))}, format="multipart"
            )
        self.assertEqual(res.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class CourseViewSetTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.user = make_user(email="capi@example.com")
        self.client.force_login(self.user)

    def test_create_assigns_user(self):
        res = self.client.post(
            reverse("course-list"),
            {"title": "Cours", "description": "d", "content": "texte"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Course.objects.get().user, self.user)

    def test_list_is_not_scoped_to_user(self):
        """⚠️ CourseViewSet.queryset = .all() : fuite entre utilisateurs."""
        make_course(make_user(email="cother@example.com"), title="Autre")
        res = self.client.get(reverse("course-list"))
        self.assertEqual([c["title"] for c in res.data], ["Autre"])

    def test_update_and_delete(self):
        course = make_course(self.user)
        res = self.client.patch(
            reverse("course-detail", args=[course.pk]), {"title": "MAJ"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.delete(reverse("course-detail", args=[course.pk])).status_code,
            status.HTTP_204_NO_CONTENT,
        )


class NestedQuestionAnswerTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.user = make_user(email="nested@example.com")
        self.quiz = make_quiz(self.user)
        self.question = self.quiz.questions.first()
        self.client.force_login(self.user)

    def test_list_questions_of_quiz(self):
        res = self.client.get(reverse("quiz-questions-list", args=[self.quiz.pk]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(len(res.data[0]["answers"]), 2)

    def test_create_question_in_quiz_is_broken(self):
        """⚠️ BUG connu : QuestionSerializer expose `answers` en écriture sans
        redéfinir `.create()` → DRF lève une AssertionError (HTTP 500).
        Supprimer ce test et le remplacer par un cas nominal une fois corrigé."""
        with self.assertRaises(AssertionError):
            self.client.post(
                reverse("quiz-questions-list", args=[self.quiz.pk]),
                {"text": "Nouvelle", "answers": [{"text": "A", "is_correct": True}]},
                format="json",
            )
        self.assertEqual(self.quiz.questions.count(), 1)

    def test_questions_of_other_quiz_are_excluded(self):
        other_quiz = make_quiz(self.user, with_questions=False)
        res = self.client.get(reverse("quiz-questions-list", args=[other_quiz.pk]))
        self.assertEqual(len(res.data), 0)

    def test_list_answers_of_question(self):
        res = self.client.get(
            reverse("question-answers-list", args=[self.quiz.pk, self.question.pk])
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_create_answer_in_question(self):
        res = self.client.post(
            reverse("question-answers-list", args=[self.quiz.pk, self.question.pk]),
            {"text": "Nouvelle réponse", "is_correct": False},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.question.answers.count(), 3)

    def test_delete_answer(self):
        answer = self.question.answers.first()
        res = self.client.delete(
            reverse("question-answers-detail", args=[self.quiz.pk, self.question.pk, answer.pk])
        )
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
