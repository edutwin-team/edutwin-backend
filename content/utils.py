import csv
from io import StringIO
from django.db import transaction
from django.http import HttpResponse

from .models import Quiz, Question, Answer
from .constants import QUESTION_HEADER,QUIZ_HEADER,QUESTION_TYPE_TO_FR,QUESTION_TYPE_FROM_FR,DIFFICULTY_TO_FR,DIFFICULTY_FROM_FR,BOOL_TO_FR,BOOL_FROM_FR

class CSVImportError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)

# SAFE PARSERS

def parse_question_type(value: str):
    value = (value or "").strip()
    return QUESTION_TYPE_FROM_FR.get(value, value)


def parse_difficulty(value: str):
    value = (value or "").strip()
    return DIFFICULTY_FROM_FR.get(value, value)


def parse_bool(value: str):
    value = (value or "").strip().lower()
    return BOOL_FROM_FR.get(value)


##handles csv files re-saved from Excel, Numbers, or Google Sheets,
# which may change encoding and add trailing empty columns.

def _decode_csv_bytes(raw_bytes: bytes) -> str:
#attempts to decode the CSV using common encodings.
#falls back to replacing invalid characters instead of raising an error.

    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("utf-8", errors="replace")


def _clean_row(row):

#strips whitespace from each cell and removes empty trailing columns
#(e.g. extra ';' added by Excel that creates empty columns and breaks header validation).

    row = [cell.strip() for cell in row]
    while row and row[-1] == "":
        row.pop()
    return row


def _read_csv_rows(file) -> list:
    if hasattr(file, "seek"):
        file.seek(0)
    raw_bytes = file.read()
    text = _decode_csv_bytes(raw_bytes)
    reader = csv.reader(StringIO(text), delimiter=";")
    rows = [_clean_row(row) for row in reader]
    return [row for row in rows if row]


#export csv

def export_quiz_to_csv(quiz):
    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = f'attachment; filename="{quiz.title}.csv"'

# explicitly adds a BOM so Excel opens the file correctly with proper accents,
# while still remaining compatible with utf-8-sig during re-import.
    response.write("\ufeff")

    writer = csv.writer(response, delimiter=";")

    # Quiz info
    writer.writerow(QUIZ_HEADER)
    writer.writerow([
        quiz.title,
        quiz.description or "",
        quiz.passing_score,
        quiz.time_limit_minutes,
    ])

    writer.writerow([])

    # Questions
    writer.writerow(QUESTION_HEADER)

    for question in quiz.questions.all():
        for answer in question.answers.all():
            writer.writerow([
                question.text,
                QUESTION_TYPE_TO_FR.get(question.question_type, question.question_type),
                DIFFICULTY_TO_FR.get(question.difficulty_level, question.difficulty_level),
                answer.text,
                BOOL_TO_FR.get(answer.is_correct),
            ])

    return response


#import csv

@transaction.atomic
def import_quiz_from_csv(file, user):
    rows = _read_csv_rows(file)

    if len(rows) < 4:
        raise CSVImportError("Le fichier CSV est invalide.")

    # Validate quiz header
    if rows[0] != QUIZ_HEADER:
        raise CSVImportError("Header du quiz invalide.")

    quiz_row = rows[1]

    if len(quiz_row) < 4:
        raise CSVImportError("Informations du quiz incomplètes.")

    quiz_title = quiz_row[0]
    quiz_description = quiz_row[1]

    try:
        passing_score = int(quiz_row[2])
        time_limit_minutes = int(quiz_row[3])
    except ValueError:
        raise CSVImportError("Score ou temps invalide.")

    # Validate question header
    if rows[2] != QUESTION_HEADER:
        raise CSVImportError("Header des questions invalide.")

    question_rows = rows[3:]

    if not question_rows:
        raise CSVImportError("Aucune question trouvée.")

    quiz = Quiz.objects.create(
        user=user,
        title=quiz_title,
        description=quiz_description,
        passing_score=passing_score,
        time_limit_minutes=time_limit_minutes,
        source_type="import_file",
    )

    questions_map = {}

    for row in question_rows:
        if len(row) < 5:
            raise CSVImportError("Ligne invalide dans les questions.")

        question_text = row[0]
        question_type = parse_question_type(row[1])
        difficulty = parse_difficulty(row[2])
        answer_text = row[3]
        is_correct = parse_bool(row[4])

        if not question_text:
            raise CSVImportError("Question vide.")

        if is_correct is None:
            raise CSVImportError("Bonne réponse invalide (Vrai/Faux).")

        question_key = (question_text, question_type, difficulty)

        if question_key not in questions_map:
            question = Question.objects.create(
                quiz=quiz,
                text=question_text,
                question_type=question_type,
                difficulty_level=difficulty,
            )
            questions_map[question_key] = question

        Answer.objects.create(
            question=questions_map[question_key],
            text=answer_text,
            is_correct=is_correct,
        )

    return quiz
