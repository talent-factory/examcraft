"""
Test data seed script — TF-341 / documentation screenshots

Creates realistic test data for local development and documentation:
  - 8 approved exam questions (5 MC + 3 open)
  - 1 exam in draft status (finalized via the UI during the screenshot run)
  - 2 classes (INF-24a, WI-24b)
  - 12 students, split across the classes
  - 12 submissions with attempts, answers and grades
    (mix of fully_reviewed / partially_reviewed / pending_review)

Prerequisite: just seed (institution + admin must already exist)

Run via: just seed-test-data
"""

import sys
import os
import logging
from datetime import datetime, date, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.auth import Institution, User
from models.question_review import QuestionReview
from models.exam import Exam, ExamQuestion, ExamStatus
from models.student import Student, StudentClass, StudentClassMembership
from models.submission import Submission, Attempt, AttemptAnswer, Grade

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

EXAM_TITLE = "Algorithmen & Datenstrukturen — Semesterprüfung FS 2026"

# 5 MC questions: (text, options, correct_answer, topic)
MC_QUESTIONS = [
    (
        "Was ist die durchschnittliche Zeitkomplexität von Quicksort?",
        ["A) O(n)", "B) O(n log n)", "C) O(n²)", "D) O(log n)"],
        "B) O(n log n)",
        "Sortieralgorithmen",
    ),
    (
        "Welche Datenstruktur verwendet das LIFO-Prinzip?",
        ["A) Queue", "B) Heap", "C) Stack", "D) Linked List"],
        "C) Stack",
        "Datenstrukturen",
    ),
    (
        "Welcher Sortieralgorithmus ist stabil?",
        ["A) Quicksort", "B) Heapsort", "C) Selection Sort", "D) Mergesort"],
        "D) Mergesort",
        "Sortieralgorithmen",
    ),
    (
        "Was ist die Zeitkomplexität der binären Suche im Worst-Case?",
        ["A) O(1)", "B) O(n)", "C) O(log n)", "D) O(n log n)"],
        "C) O(log n)",
        "Suchalgorithmen",
    ),
    (
        "Welche Traversierung eines Binärbaums liefert die Knoten in sortierter Reihenfolge?",
        ["A) Preorder", "B) Postorder", "C) Level-order", "D) Inorder"],
        "D) Inorder",
        "Bäume",
    ),
]

# 3 open questions: (text, model_answer, topic)
OPEN_QUESTIONS = [
    (
        "Erklären Sie den Unterschied zwischen Stack und Queue. Nennen Sie je ein Anwendungsbeispiel.",
        "Stack (LIFO): letztes Element wird zuerst entfernt — Anwendung z.B. Funktionsaufruf-Stack, Undo-Funktion. "
        "Queue (FIFO): erstes Element wird zuerst entfernt — Anwendung z.B. Druckerwarteschlange, BFS-Algorithmus.",
        "Datenstrukturen",
    ),
    (
        "Beschreiben Sie den Ablauf von Bubble Sort und analysieren Sie dessen Zeit- und Speicherkomplexität.",
        "Bubble Sort vergleicht benachbarte Elemente und tauscht sie, wenn sie in falscher Reihenfolge sind. "
        "Pro Durchlauf wird das grösste Element ans Ende gebracht. "
        "Zeitkomplexität: O(n²) im Durchschnitt und Worst-Case, O(n) im Best-Case (bereits sortiert mit Optimierung). "
        "Speicherkomplexität: O(1) — In-Place-Algorithmus.",
        "Sortieralgorithmen",
    ),
    (
        "Was ist ein AVL-Baum? Welchen Vorteil bietet er gegenüber einem gewöhnlichen Binärsuchbaum?",
        "Ein AVL-Baum ist ein selbstbalancierender Binärsuchbaum, bei dem für jeden Knoten die Höhen "
        "des linken und rechten Teilbaums um höchstens 1 differieren. "
        "Vorteil: garantiert O(log n) für Suche, Einfügen und Löschen, da die Baumhöhe immer O(log n) bleibt. "
        "Beim gewöhnlichen BST kann die Höhe im Worst-Case O(n) betragen (entarteter Baum).",
        "Bäume",
    ),
]

# 12 students: (external_id, display_name, class_name)
STUDENTS = [
    ("moodle_u101", "Müller A.", "INF-24a"),
    ("moodle_u102", "Huber M.", "INF-24a"),
    ("moodle_u103", "Schmid L.", "INF-24a"),
    ("moodle_u104", "Weber K.", "INF-24a"),
    ("moodle_u105", "Fischer R.", "INF-24a"),
    ("moodle_u106", "Brunner T.", "INF-24a"),
    ("moodle_u107", "Keller S.", "INF-24a"),
    ("moodle_u108", "Meier P.", "INF-24a"),
    ("moodle_u109", "Zimmermann J.", "WI-24b"),
    ("moodle_u110", "Steiner D.", "WI-24b"),
    ("moodle_u111", "Moser C.", "WI-24b"),
    ("moodle_u112", "Baumann F.", "WI-24b"),
]

# Per student: mc_correct (list of bool, 5 MC questions) + open_pts (list of float, 3 open questions)
# grade_status: 'fully_reviewed' | 'partially_reviewed' | 'pending_review'
STUDENT_SCORES = {
    #                        MC                      Open (max 3pt each)    grade_status
    "moodle_u101": {
        "mc": [1, 1, 1, 1, 1],
        "open": [3.0, 3.0, 2.0],
        "status": "fully_reviewed",
    },
    "moodle_u102": {
        "mc": [1, 1, 1, 1, 0],
        "open": [3.0, 2.0, 2.0],
        "status": "fully_reviewed",
    },
    "moodle_u103": {
        "mc": [1, 1, 0, 1, 1],
        "open": [3.0, 2.0, 1.5],
        "status": "fully_reviewed",
    },
    "moodle_u104": {
        "mc": [1, 0, 1, 1, 0],
        "open": [2.0, 2.0, 2.0],
        "status": "fully_reviewed",
    },
    "moodle_u105": {
        "mc": [1, 1, 0, 0, 1],
        "open": [2.0, 2.0, 1.5],
        "status": "fully_reviewed",
    },
    "moodle_u106": {
        "mc": [0, 1, 0, 1, 0],
        "open": [2.0, 1.5, 2.0],
        "status": "partially_reviewed",
    },
    "moodle_u107": {
        "mc": [1, 1, 1, 0, 1],
        "open": [2.0, 2.0, 1.5],
        "status": "partially_reviewed",
    },
    "moodle_u108": {
        "mc": [1, 0, 0, 1, 0],
        "open": [1.5, 1.5, 1.5],
        "status": "partially_reviewed",
    },
    "moodle_u109": {
        "mc": [1, 1, 1, 0, 1],
        "open": [2.5, 2.0, 2.0],
        "status": "partially_reviewed",
    },
    "moodle_u110": {
        "mc": [0, 0, 1, 0, 0],
        "open": [1.5, 1.5, 1.0],
        "status": "pending_review",
    },
    "moodle_u111": {
        "mc": [1, 1, 1, 1, 0],
        "open": [3.0, 2.5, 2.0],
        "status": "pending_review",
    },
    "moodle_u112": {
        "mc": [0, 1, 0, 1, 0],
        "open": [2.0, 1.5, 1.5],
        "status": "pending_review",
    },
}

# Example student answers (open questions)
STUDENT_OPEN_ANSWERS = {
    "moodle_u101": [
        "Stack arbeitet nach LIFO (Last In First Out) — das zuletzt eingefügte Element wird zuerst entnommen. Beispiel: Browser-Verlauf (Zurück-Schaltfläche). Queue arbeitet nach FIFO (First In First Out) — das zuerst eingefügte Element kommt zuerst heraus. Beispiel: Druckerwarteschlange.",
        "Bubble Sort vergleicht in jedem Durchlauf benachbarte Elemente und tauscht sie, wenn sie falsch geordnet sind. Grössere Elemente 'blubbern' ans Ende. Zeitkomplexität O(n²) im Worst-Case, Speicher O(1).",
        "Ein AVL-Baum ist ein selbstbalancierender BST mit Höhenbalance-Bedingung (|h_links - h_rechts| ≤ 1). Vorteil: garantierte O(log n) Operationen, da Entartung verhindert wird.",
    ],
    "moodle_u102": [
        "Stack = LIFO, Queue = FIFO. Stack-Beispiel: Undo in Texteditoren. Queue-Beispiel: Aufgabenwarteschlange eines Betriebssystems.",
        "Bubble Sort vergleicht Paare und tauscht sie. Worst-Case O(n²), Best-Case O(n) mit Frühausstieg. In-Place-Algorithmus.",
        "AVL-Baum balanciert sich automatisch neu, wenn die Höhendifferenz grösser als 1 wird. Dadurch immer O(log n) statt O(n) im schlimmsten Fall.",
    ],
    "moodle_u103": [
        "Stack (LIFO): Funktioncall-Stack beim Programmieren. Queue (FIFO): Nachrichten in einem Chat.",
        "Bubble Sort tauscht benachbarte Elemente so lange, bis alles sortiert ist. Zeitkomplexität: O(n²). Sehr ineffizient für grosse Arrays.",
        "AVL-Baum = ausgeglichener Binärsuchbaum. Rotationen halten den Baum balanciert. Besser als normaler BST weil keine Entartung möglich.",
    ],
    "moodle_u104": [
        "Stack: LIFO, Beispiel Klammernauswertung. Queue: FIFO, Beispiel Prozessplanung.",
        "Bubble Sort ist ein einfacher Algorithmus der paarweise tauscht. O(n²) Zeitkomplexität, nicht geeignet für grosse Datensätze.",
        "AVL ist ein balancierter Baum. Vorteil: schnellere Suche als unsortierter BST durch garantierte Höhe von O(log n).",
    ],
    "moodle_u105": [
        "Stack = Stapel (oben rein, oben raus). Queue = Warteschlange (hinten rein, vorne raus). Stack-Anwendung: Tiefensuche.",
        "Bubble Sort: O(n²). Vergleicht immer zwei benachbarte Elemente und tauscht sie wenn nötig. Mehrere Durchläufe notwendig.",
        "AVL-Baum hält Balance durch Rotationen aufrecht. Keine Entartung möglich, daher O(log n) garantiert.",
    ],
    "moodle_u106": [
        "Stack LIFO Queue FIFO. Stack z.B. für DFS, Queue für BFS.",
        "Bubble Sort ist langsam O(n²) aber einfach zu implementieren. Tauscht immer Nachbarn.",
        "AVL balanciert automatisch. Besser als BST.",
    ],
    "moodle_u107": [
        "Stack: Last In First Out, Beispiel: Navigationsverlauf im Browser. Queue: First In First Out, Beispiel: Ticketsystem.",
        "Bubble Sort durchläuft die Liste mehrfach und tauscht benachbarte Elemente. Zeitkomplexität O(n²), Speicher O(1).",
        "AVL-Baum garantiert durch Rotationen immer einen balancierten Baum. Suchoperationen in O(log n).",
    ],
    "moodle_u108": [
        "Stack = letztes Element raus. Queue = erstes Element raus.",
        "Bubble Sort tauscht Elemente bis sortiert. Langsam aber einfach.",
        "AVL ist besser als normaler Baum weil er balanciert ist.",
    ],
    "moodle_u109": [
        "Stack arbeitet nach LIFO-Prinzip: Beispiel Undo/Redo-Funktion. Queue nach FIFO: Beispiel Druckaufträge verwalten.",
        "Bubble Sort vergleicht benachbarte Elemente und tauscht bei falscher Reihenfolge. Best-Case O(n), Worst-Case O(n²). Speicher O(1) in-place.",
        "AVL-Baum ist ein balancierter BST mit Höhenbalance ≤ 1. Rotationen halten Balance aufrecht, garantiert O(log n) für alle Operationen.",
    ],
    "moodle_u110": [
        "Stack und Queue sind Datenstrukturen. Stack ist wie ein Stapel, Queue wie eine Schlange.",
        "Bubble Sort sortiert durch Vertauschen. Ist nicht sehr effizient.",
        "AVL-Baum ist eine Art Baum der immer gleich gross ist.",
    ],
    "moodle_u111": [
        "Stack: LIFO-Prinzip — das zuletzt hinzugefügte Element wird zuerst entfernt. Anwendung: Auswertung arithmetischer Ausdrücke. Queue: FIFO-Prinzip — das zuerst hinzugefügte Element verlässt die Struktur zuerst. Anwendung: Ereignisverarbeitung.",
        "Bubble Sort: wiederholtes Durchlaufen der Liste mit Vergleich und Tausch benachbarter Elemente. Zeitkomplexität: O(n²) im Worst-Case, O(n) mit Optimierung im Best-Case. Speicherkomplexität: O(1), in-place.",
        "AVL-Baum: selbstbalancierender BST, Höhendifferenz jedes Knotens ≤ 1. Rotationen (einfach/doppelt) stellen Balance nach Einfügen/Löschen sicher. Vorteil: garantiert O(log n) statt O(n) beim entarteten BST.",
    ],
    "moodle_u112": [
        "Stack = LIFO, Queue = FIFO. Unterschied im Zugriffsprinzip.",
        "Bubble Sort vergleicht Paare. Komplex und langsam für grosse Daten.",
        "AVL-Baum ist ausgeglichen, BST nicht zwingend. AVL schneller bei der Suche.",
    ],
}


def seed_questions(db, institution, admin_user):
    logger.info("📝 Seeding Prüfungsfragen…")
    questions = []

    for i, (text, options, correct, topic) in enumerate(MC_QUESTIONS, 1):
        existing = (
            db.query(QuestionReview)
            .filter_by(institution_id=institution.id, question_text=text)
            .first()
        )
        if existing:
            logger.info(f"   ✅ MC-Frage {i} bereits vorhanden")
            questions.append(existing)
            continue
        q = QuestionReview(
            question_text=text,
            question_type="single_choice",
            options=options,
            correct_answer=correct,
            explanation=f"Korrekte Antwort: {correct}",
            difficulty="medium",
            topic=topic,
            language="de",
            review_status="approved",
            institution_id=institution.id,
            created_by=admin_user.id,
            reviewed_by=admin_user.id,
            reviewed_at=datetime.now(timezone.utc),
            confidence_score=0.92,
            bloom_level=2,
            quality_tier="A",
        )
        db.add(q)
        questions.append(q)
        logger.info(f"   ✅ MC-Frage {i}: {text[:60]}…")

    for i, (text, model_answer, topic) in enumerate(OPEN_QUESTIONS, 1):
        existing = (
            db.query(QuestionReview)
            .filter_by(institution_id=institution.id, question_text=text)
            .first()
        )
        if existing:
            logger.info(f"   ✅ Offene Frage {i} bereits vorhanden")
            questions.append(existing)
            continue
        q = QuestionReview(
            question_text=text,
            question_type="open_ended",
            correct_answer=model_answer,
            difficulty="hard",
            topic=topic,
            language="de",
            review_status="approved",
            institution_id=institution.id,
            created_by=admin_user.id,
            reviewed_by=admin_user.id,
            reviewed_at=datetime.now(timezone.utc),
            confidence_score=0.88,
            bloom_level=4,
            quality_tier="A",
        )
        db.add(q)
        questions.append(q)
        logger.info(f"   ✅ Offene Frage {i}: {text[:60]}…")

    db.flush()
    return questions


def seed_exam(db, institution, admin_user, questions):
    logger.info("📋 Seeding Exam…")

    existing = (
        db.query(Exam)
        .filter_by(institution_id=institution.id, title=EXAM_TITLE)
        .first()
    )
    if existing:
        logger.info(f"   ✅ Exam bereits vorhanden (ID {existing.id})")
        return existing

    exam = Exam(
        title=EXAM_TITLE,
        course="Algorithmen & Datenstrukturen",
        exam_date=date(2026, 6, 15),
        time_limit_minutes=90,
        instructions="Alle Hilfsmittel erlaubt ausser elektronische Geräte.",
        passing_percentage=50.0,
        status=ExamStatus.DRAFT.value,
        language="de",
        institution_id=institution.id,
        created_by=admin_user.id,
    )
    db.add(exam)
    db.flush()

    # 5 MC × 1pt + 3 open × 3pt
    mc_pts = 1.0
    open_pts = 3.0
    for pos, q in enumerate(questions, 1):
        pts = mc_pts if q.question_type == "single_choice" else open_pts
        eq = ExamQuestion(
            exam_id=exam.id,
            question_id=q.id,
            position=pos,
            points=pts,
        )
        db.add(eq)

    exam.total_points = sum(
        mc_pts if q.question_type == "single_choice" else open_pts for q in questions
    )
    db.flush()
    logger.info(f"   ✅ Exam '{exam.title}' (ID {exam.id}, {exam.total_points} Punkte)")
    return exam


def seed_classes_and_students(db, institution):
    logger.info("🎓 Seeding Klassen und Studierende…")

    classes = {}
    for name in ["INF-24a", "WI-24b"]:
        existing = (
            db.query(StudentClass)
            .filter_by(institution_id=institution.id, name=name)
            .first()
        )
        if existing:
            logger.info(f"   ✅ Klasse {name} bereits vorhanden")
            classes[name] = existing
        else:
            sc = StudentClass(institution_id=institution.id, name=name)
            db.add(sc)
            db.flush()
            classes[name] = sc
            logger.info(f"   ✅ Klasse {name} erstellt")

    students = {}
    for ext_id, display_name, class_name in STUDENTS:
        existing = (
            db.query(Student)
            .filter_by(institution_id=institution.id, external_id=ext_id)
            .first()
        )
        if existing:
            students[ext_id] = existing
            logger.info(f"   ✅ Studierender {display_name} bereits vorhanden")
            continue

        s = Student(
            institution_id=institution.id,
            external_id=ext_id,
            display_name=display_name,
        )
        db.add(s)
        db.flush()

        membership = StudentClassMembership(
            student_id=s.id,
            class_id=classes[class_name].id,
        )
        db.add(membership)
        students[ext_id] = s
        logger.info(f"   ✅ {display_name} ({ext_id}) → {class_name}")

    db.flush()
    return students


def seed_submissions(db, institution, exam, students):
    logger.info("📊 Seeding Submissions, Attempts und Noten…")

    exam_questions = (
        db.query(ExamQuestion)
        .filter_by(exam_id=exam.id)
        .order_by(ExamQuestion.position)
        .all()
    )

    # Filter by question type instead of slicing by index — robust against
    # deviating order/count. mc_correct has 5, open_pts has 3 entries per student.
    mc_questions = [
        eq for eq in exam_questions if eq.question.question_type == "single_choice"
    ]
    open_questions = [
        eq for eq in exam_questions if eq.question.question_type == "open_ended"
    ]
    if len(mc_questions) != 5 or len(open_questions) != 3:
        raise ValueError(
            f"Erwartet 5 MC- und 3 offene Fragen im Exam '{exam.title}', gefunden: "
            f"{len(mc_questions)} MC / {len(open_questions)} offen. Prüfe seed_questions()."
        )
    if not exam.total_points:
        raise ValueError(
            f"Exam {exam.id} hat keine total_points gesetzt — "
            f"Prozentberechnung nicht möglich. Prüfe seed_exam()."
        )

    for ext_id, display_name, _ in STUDENTS:
        student = students[ext_id]
        scores = STUDENT_SCORES[ext_id]
        mc_correct = scores["mc"]  # list of 0/1
        open_pts_awarded = scores["open"]  # list of floats
        grade_status = scores["status"]

        # Skip if submission already exists
        existing = (
            db.query(Submission)
            .filter_by(exam_id=exam.id, student_id=student.id)
            .first()
        )
        if existing:
            logger.info(f"   ✅ Submission für {display_name} bereits vorhanden")
            continue

        # Calculate totals (mc_questions / open_questions were validated above)
        mc_total = sum(mc_correct)
        open_total = sum(open_pts_awarded)
        total_awarded = float(mc_total) + open_total
        total_max = exam.total_points
        percentage = round(total_awarded / total_max * 100, 1)

        submission = Submission(
            exam_id=exam.id,
            student_id=student.id,
            scoring_strategy="latest",
            total_points_awarded=total_awarded,
            total_points_max=total_max,
            percentage=percentage,
            grade_status=grade_status,
        )
        db.add(submission)
        db.flush()

        attempt = Attempt(
            submission_id=submission.id,
            institution_id=institution.id,
            attempt_number=1,
            source="moodle_csv",
            source_attempt_id=f"csv_{ext_id}_exam{exam.id}_1",
            submitted_at=datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc),
        )
        db.add(attempt)
        db.flush()

        open_answers = STUDENT_OPEN_ANSWERS.get(ext_id)
        if open_answers is None:
            logger.warning(
                f"   ⚠️  Keine offenen Antworten für {ext_id} hinterlegt — "
                f"verwende leere Platzhalter."
            )
            open_answers = [""] * 3

        for i, eq in enumerate(mc_questions):
            is_correct = bool(mc_correct[i])
            given = eq.question.correct_answer if is_correct else eq.question.options[0]
            aa = AttemptAnswer(
                attempt_id=attempt.id,
                exam_question_id=eq.id,
                given_answer=given,
                moodle_points_awarded=eq.points if is_correct else 0.0,
            )
            db.add(aa)
            db.flush()

            grade_st = _grade_status_for(grade_status, "mc")
            grade = Grade(
                attempt_answer_id=aa.id,
                points_awarded=eq.points if is_correct else 0.0,
                points_max=eq.points,
                status=grade_st,
                is_correct=is_correct,
                llm_confidence=0.98 if is_correct else 0.95,
                llm_rationale="Antwort stimmt mit korrekter Lösung überein."
                if is_correct
                else "Antwort entspricht keiner korrekten Option.",
            )
            db.add(grade)

        for i, eq in enumerate(open_questions):
            pts = open_pts_awarded[i]
            answer_text = open_answers[i] if i < len(open_answers) else ""
            aa = AttemptAnswer(
                attempt_id=attempt.id,
                exam_question_id=eq.id,
                given_answer=answer_text,
            )
            db.add(aa)
            db.flush()

            grade_st = _grade_status_for(grade_status, "open", index=i)
            grade = Grade(
                attempt_answer_id=aa.id,
                points_awarded=pts,
                points_max=eq.points,
                status=grade_st,
                is_correct=pts >= eq.points * 0.5,
                llm_confidence=0.82,
                llm_rationale=_open_rationale(pts, eq.points),
                llm_matched_aspects=[
                    "Korrekte Terminologie",
                    "Nachvollziehbare Erklärung",
                ]
                if pts >= 2.0
                else ["Teilweise korrekt"],
                llm_missing_aspects=[]
                if pts >= eq.points
                else ["Beispiel fehlt" if pts >= 2.0 else "Kernkonzept unvollständig"],
            )
            db.add(grade)

        db.flush()
        logger.info(
            f"   ✅ {display_name}: {total_awarded}/{total_max}pt "
            f"({percentage}%) [{grade_status}]"
        )

    db.commit()


def _grade_status_for(submission_status: str, q_type: str, index: int = 0) -> str:
    """Map submission grade_status + question type to individual Grade.status."""
    if submission_status == "fully_reviewed":
        return "approved"
    if submission_status == "partially_reviewed":
        # MC approved, open questions: first one approved, rest proposed
        if q_type == "mc":
            return "approved"
        return "approved" if index == 0 else "proposed"
    # pending_review → all proposed
    return "proposed"


def _open_rationale(pts: float, max_pts: float) -> str:
    ratio = pts / max_pts
    if ratio >= 0.9:
        return "Vollständige und präzise Antwort mit korrekten Beispielen."
    if ratio >= 0.6:
        return "Antwort deckt die wesentlichen Punkte ab, Beispiel unvollständig."
    if ratio >= 0.4:
        return "Grundverständnis erkennbar, aber wichtige Aspekte fehlen."
    return "Antwort zeigt nur oberflächliches Verständnis des Konzepts."


def main():
    print("\n" + "=" * 60)
    print("🧪 ExamCraft AI — Test-Daten Seeding")
    print("=" * 60 + "\n")

    db = SessionLocal()
    try:
        institution = db.query(Institution).filter_by(slug="talent-factory").first()
        if not institution:
            logger.error("❌ Institution 'talent-factory' nicht gefunden.")
            logger.error("   Führe zuerst 'just seed' aus.")
            sys.exit(1)

        admin_user = db.query(User).filter_by(email="admin@talent-factory.ch").first()
        if not admin_user:
            logger.error("❌ Admin-User nicht gefunden.")
            logger.error("   Führe zuerst 'just seed' aus.")
            sys.exit(1)

        questions = seed_questions(db, institution, admin_user)
        exam = seed_exam(db, institution, admin_user, questions)
        students = seed_classes_and_students(db, institution)
        seed_submissions(db, institution, exam, students)

        print("\n" + "=" * 60)
        print("✅ Test-Daten Seeding abgeschlossen!")
        print("=" * 60)
        print("\n📋 Erstellt:")
        print(f"   Exam:        '{EXAM_TITLE}'")
        print(f"   Fragen:      {len(questions)} (5 MC + 3 offen, je 14pt total)")
        print("   Klassen:     INF-24a (8 Stud.) / WI-24b (4 Stud.)")
        print("   Studierende: 12")
        print("   Submissions: 12 (5 fully / 4 partially / 3 pending reviewed)")
        print()

    except Exception as e:
        logger.error(f"\n❌ Fehler: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
