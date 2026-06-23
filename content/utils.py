import csv
from io import StringIO
from django.db import transaction
from django.http import HttpResponse

from .models import Quiz, Question, Answer
from .constants import QUIZ_HEADER , QUESTION_HEADER,QUESTION_TYPE_TO_FR,QUESTION_TYPE_FROM_ANY,DIFFICULTY_TO_FR,DIFFICULTY_FROM_ANY,BOOL_TO_FR,BOOL_FROM_ANY


# EXCEPTION

class CSVImportError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


# helpers

def _strip_bom(value: str) -> str:
    #Delete  BOM characters 
    
    return value.replace("\ufeff", "").replace("\u200b", "").strip()


def _decode_csv_bytes(raw: bytes) -> str:
# support multiple CSV encodings
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    # add fallback error handling 
    return raw.decode("utf-8", errors="replace")


def _detect_delimiter(text: str) -> str:
# feat: detect CSV separator automatically
    first_line = _strip_bom(text.split("\n")[0]) if "\n" in text else _strip_bom(text[:500])
    return "," if first_line.count(",") > first_line.count(";") else ";"


def _clean_row(row: list) -> list:
# normalize CSV data before parsing
    
    row = [_strip_bom(cell) for cell in row]
    while row and row[-1] == "":
        row.pop()
    return row


def _headers_match(row: list, expected: list) -> bool:

# make header comparison case-insensitive after normalization
    
    return [c.lower() for c in row] == [c.lower() for c in expected]


def _read_rows(file) -> list[list[str]]:

#add unified CSV upload parser with cross-platform support
    if hasattr(file, "seek"):
        file.seek(0)
    raw = file.read()
    text = _decode_csv_bytes(raw)
    delimiter = _detect_delimiter(text)
    reader = csv.reader(StringIO(text), delimiter=delimiter)
    rows = [_clean_row(row) for row in reader]
    return [row for row in rows if row]  #ignore empty lignes


# SAFE PARSERS

def parse_question_type(value: str) -> str:
    return QUESTION_TYPE_FROM_ANY.get(_strip_bom(value).lower(), value)


def parse_difficulty(value: str) -> str:
    return DIFFICULTY_FROM_ANY.get(_strip_bom(value).lower(), value)


def parse_bool(value: str):
    return BOOL_FROM_ANY.get(_strip_bom(value).lower())


def _parse_int(value: str, label: str) -> int:
    try:
        return int(_strip_bom(str(value)).strip())
    except ValueError:
        raise CSVImportError(
            f"La valeur « {value} » pour « {label} » doit être un nombre entier."
        )

# export quiz csv

def export_quiz_to_csv(quiz):

# export quiz to UTF-8 CSV with BOM for Excel compatibility

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{quiz.title}.csv"'

# ensure single UTF-8 BOM in CSV export response
    response.write("\ufeff")

    writer = csv.writer(response, delimiter=";")

    writer.writerow(QUIZ_HEADER)
    writer.writerow([
        quiz.title,
        quiz.description or "",
        quiz.passing_score,
        quiz.time_limit_minutes,
    ])
    writer.writerow([])
    writer.writerow(QUESTION_HEADER)

    for question in quiz.questions.prefetch_related("answers").all():
        for answer in question.answers.all():
            writer.writerow([
                question.text,
                QUESTION_TYPE_TO_FR.get(question.question_type, question.question_type),
                DIFFICULTY_TO_FR.get(question.difficulty_level, question.difficulty_level),
                answer.text,
                BOOL_TO_FR[answer.is_correct],
            ])

    return response


# Import quiz csv

@transaction.atomic
def import_quiz_from_csv(file, user):
    rows = _read_rows(file)

    #Validation 

    if len(rows) < 4:
        raise CSVImportError("Le fichier est vide ou trop court pour être valide.")

    if not _headers_match(rows[0], QUIZ_HEADER):
        raise CSVImportError(
            "La première ligne du fichier est incorrecte. "
            "Vérifiez que vous utilisez bien le modèle fourni et que "
            "les titres de colonnes n'ont pas été modifiés."
        )

    if not _headers_match(rows[2], QUESTION_HEADER):
        raise CSVImportError(
            "La ligne d'en-tête des questions est incorrecte. "
            "Vérifiez que vous utilisez bien le modèle fourni et que "
            "les titres de colonnes n'ont pas été modifiés."
        )

    # ── quiz info

    quiz_row = rows[1]
    if len(quiz_row) < 4:
        raise CSVImportError(
            "La ligne d'informations du quiz (ligne 2) est incomplète. "
            "Elle doit contenir : titre, description, score minimum, temps limite."
        )

    quiz_title = quiz_row[0]
    quiz_description = quiz_row[1]
    passing_score = _parse_int(quiz_row[2], "Score minimum (%)")
    time_limit_minutes = _parse_int(quiz_row[3], "Temps limite (minutes)")



    question_rows = rows[3:]
    if not question_rows:
        raise CSVImportError("Aucune question trouvée dans le fichier.")

    # ── Add quiz in db

    quiz = Quiz.objects.create(
        user=user,
        title=quiz_title,
        description=quiz_description,
        passing_score=passing_score,
        time_limit_minutes=time_limit_minutes,
        source_type="import_file",
    )

    questions_map = {}

    for line_num, row in enumerate(question_rows, start=4):
        if len(row) < 5:
            raise CSVImportError(
                f"Ligne {line_num} : il manque des colonnes "
                f"({len(row)} trouvée(s) sur 5 attendues)."
            )

        question_text = row[0]
        question_type = parse_question_type(row[1])
        difficulty = parse_difficulty(row[2])
        answer_text = row[3]
        is_correct = parse_bool(row[4])

        if not question_text:
            raise CSVImportError(f"Ligne {line_num} : le texte de la question est vide.")

        if is_correct is None:
            raise CSVImportError(
                f"Ligne {line_num} : la colonne « Bonne réponse » doit contenir "
                f"Vrai ou Faux, reçu : « {row[4]} »."
            )

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