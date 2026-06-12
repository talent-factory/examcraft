"""On-the-fly Statistik aus ``submissions`` + ``grades`` + ``attempt_answers``.

Read-only service. Keine eigene Persistenz, kein Cache — Spec 8 hält
Materialized-Views explizit als spätere Optimierung offen, falls die
on-the-fly-Aggregate zu langsam werden.

Arbeitet ausschliesslich auf der Submission ihrem ``graded_attempt``;
nicht-wertende Versuche fliessen nur dann ein, wenn die Spec sie
explizit verlangt (Lerneffekt bei Mehrfach-Versuchen).

Trennschärfe (item discrimination) verwendet Pearson-Korrelation
zwischen Item-Erfolg (0/1) und Gesamtprozent — das ist das Standard-
Verfahren aus der psychometrischen Praxis (Item Analysis 101). Bei
weniger als zwei Submissions oder konstanten Werten gibt der Service
``None`` zurück; das Frontend rendert das als "—" statt einer
irreführenden Zahl.
"""

from __future__ import annotations

import logging
import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from datetime import date

from sqlalchemy.orm import Session

from models.exam import Exam, ExamQuestion
from models.question_review import QuestionReview
from models.student import Student, StudentClass, StudentClassMembership
from models.submission import Attempt, AttemptAnswer, Grade, Submission
from services.grading_scheme_evaluator import is_passing
from services.grading_scheme_resolver import (
    resolve_scheme_config as _resolve_scheme_config,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HistogramBucket:
    """One [from_pct, to_pct) bucket; the last one owns its right edge."""

    from_pct: int
    to_pct: int
    count: int


@dataclass(frozen=True)
class OverviewStats:
    submission_count: int
    fully_reviewed_count: int
    avg_percentage: float | None
    median_percentage: float | None
    min_percentage: float | None
    max_percentage: float | None
    pass_rate: float | None
    avg_duration_seconds: float | None
    histogram: list[HistogramBucket]


@dataclass(frozen=True)
class PerQuestionStat:
    exam_question_id: int
    question_id: int
    position: int
    question_text: str
    question_type: str
    points_max: float
    answered_count: int
    success_rate: float | None
    difficulty: float | None
    discrimination: float | None
    top_wrong_answers: list[tuple[str, int]] = field(default_factory=list)
    learning_effect: float | None = None


@dataclass(frozen=True)
class PerSubmissionStat:
    submission_id: int
    student_id: int
    student_external_id: str
    student_display_name: str | None
    total_points_awarded: float
    total_points_max: float
    percentage: float
    grade_status: str
    per_question: list[dict[str, Any]]
    bloom_mix: dict[int, int]
    topic_heatmap: dict[str, dict[str, float]]


# ---------------------------------------------------------------------------
# Cross-Exam DTOs (TF-336 Subarea B)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StudentSubmissionRecord:
    """One submission's headline data, chronological."""

    submission_id: int
    exam_id: int
    exam_title: str
    exam_date: date | None
    percentage: float
    grade_status: str


@dataclass(frozen=True)
class TopicAggregate:
    """Topic coverage across multiple submissions."""

    topic: str
    points_awarded: float
    points_max: float
    percentage: float


@dataclass(frozen=True)
class ClassMemberPerformance:
    """One student's progress as seen from the class perspective."""

    student_id: int
    external_id: str
    display_name: str | None
    submission_count: int
    avg_percentage: float | None
    submissions: list[StudentSubmissionRecord]


@dataclass(frozen=True)
class ClassExamAggregate:
    """Class-wide aggregate per exam — for the trend chart."""

    exam_id: int
    exam_title: str
    exam_date: date | None
    submission_count: int
    avg_percentage: float | None
    pass_rate: float | None


@dataclass(frozen=True)
class ClassHistoryStats:
    class_id: int
    class_name: str
    member_count: int
    members: list[ClassMemberPerformance]
    exam_aggregates: list[ClassExamAggregate]
    topic_coverage: list[TopicAggregate]


@dataclass(frozen=True)
class StudentClassRef:
    class_id: int
    class_name: str


@dataclass(frozen=True)
class StudentHistoryStats:
    student_id: int
    external_id: str
    display_name: str | None
    submission_count: int
    avg_percentage: float | None
    submissions: list[StudentSubmissionRecord]
    bloom_mix: dict[int, int]
    topic_heatmap: list[TopicAggregate]
    classes: list[StudentClassRef]


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class StatisticsService:
    """Aggregates per Spec Abschnitt 8.

    All public methods are pure functions of (session, exam_id) plus
    optional flags — they never mutate state, so they can be re-run
    after every Review-Action without invalidating anything.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Overview
    # ------------------------------------------------------------------

    def overview(self, *, exam_id: int) -> OverviewStats:
        exam = self._get_exam_or_raise(exam_id)

        submissions: list[Submission] = (
            self.db.query(Submission).filter(Submission.exam_id == exam_id).all()
        )

        if not submissions:
            return OverviewStats(
                submission_count=0,
                fully_reviewed_count=0,
                avg_percentage=None,
                median_percentage=None,
                min_percentage=None,
                max_percentage=None,
                pass_rate=None,
                avg_duration_seconds=None,
                histogram=_empty_histogram(),
            )

        percentages = [float(s.percentage) for s in submissions]
        fully_reviewed = sum(
            1 for s in submissions if s.grade_status == "fully_reviewed"
        )
        passing_pct = float(exam.passing_percentage or 0)

        # ``pass_rate`` honours the grading-scheme's per-step is_passing
        # flag for stepped schemes; linear/linear_segments fall back to
        # ``exam.passing_percentage`` (their canonical threshold). When
        # no scheme is configured at all, the flat threshold remains.
        scheme_config = _resolve_scheme_config(self.db, exam)
        if scheme_config is not None:
            pass_count = sum(
                1
                for p in percentages
                if is_passing(p, scheme_config, passing_percentage=passing_pct)
            )
        else:
            pass_count = sum(1 for p in percentages if p >= passing_pct)

        durations = [
            (a.submitted_at - a.started_at).total_seconds()
            for s in submissions
            if s.graded_attempt_id is not None
            for a in [s.graded_attempt]
            if a is not None and a.started_at is not None and a.submitted_at is not None
        ]

        return OverviewStats(
            submission_count=len(submissions),
            fully_reviewed_count=fully_reviewed,
            avg_percentage=_safe_mean(percentages),
            median_percentage=_safe_median(percentages),
            min_percentage=min(percentages),
            max_percentage=max(percentages),
            pass_rate=pass_count / len(percentages),
            avg_duration_seconds=_safe_mean(durations) if durations else None,
            histogram=_histogram(percentages),
        )

    # ------------------------------------------------------------------
    # Per-question
    # ------------------------------------------------------------------

    def per_question(self, *, exam_id: int) -> list[PerQuestionStat]:
        self._get_exam_or_raise(exam_id)

        exam_questions = (
            self.db.query(ExamQuestion, QuestionReview)
            .join(QuestionReview, QuestionReview.id == ExamQuestion.question_id)
            .filter(ExamQuestion.exam_id == exam_id)
            .order_by(ExamQuestion.position)
            .all()
        )
        if not exam_questions:
            return []

        # One pass over the graded_attempt's answers — joined with
        # submission to expose the total percentage per row for the
        # discrimination calculation. Avoids the N×M nested loop a
        # naive Python join would do.
        rows = (
            self.db.query(
                AttemptAnswer.exam_question_id,
                AttemptAnswer.given_answer,
                Grade.points_awarded,
                Grade.points_max,
                Grade.is_correct,
                Submission.percentage,
                Submission.id.label("submission_id"),
            )
            .join(Grade, Grade.attempt_answer_id == AttemptAnswer.id)
            .join(Attempt, Attempt.id == AttemptAnswer.attempt_id)
            .join(Submission, Submission.id == Attempt.submission_id)
            .filter(
                Submission.exam_id == exam_id,
                Submission.graded_attempt_id == Attempt.id,
            )
            .all()
        )

        by_question: dict[int, list[tuple]] = {}
        for row in rows:
            by_question.setdefault(row.exam_question_id, []).append(row)

        # Pre-compute per-student per-attempt rows for the multi-attempt
        # learning-effect: only students with multiple attempts contribute,
        # so we pair attempts 1→2, 2→3, … per student. Cohort-mean would
        # mix students who only took one attempt with those who retried,
        # silently inflating attempt-1 with non-retriers.
        learning_rows = (
            self.db.query(
                AttemptAnswer.exam_question_id,
                Grade.is_correct,
                Attempt.attempt_number,
                Submission.student_id,
            )
            .join(Grade, Grade.attempt_answer_id == AttemptAnswer.id)
            .join(Attempt, Attempt.id == AttemptAnswer.attempt_id)
            .join(Submission, Submission.id == Attempt.submission_id)
            .filter(Submission.exam_id == exam_id)
            .all()
        )
        # exam_question_id → {student_id → {attempt_number → is_correct}}
        learning_by_question: dict[int, dict[int, dict[int, bool]]] = {}
        for r in learning_rows:
            correct = bool(r.is_correct) if r.is_correct is not None else False
            (
                learning_by_question.setdefault(r.exam_question_id, {}).setdefault(
                    r.student_id, {}
                )[r.attempt_number]
            ) = correct

        out: list[PerQuestionStat] = []
        for eq, qr in exam_questions:
            ans = by_question.get(eq.id, [])
            success, difficulty = _success_and_difficulty(ans, eq.points)
            discrimination = _discrimination(ans)
            top_wrong = (
                _top_wrong_answers(ans) if qr.question_type == "single_choice" else []
            )
            learning = _learning_effect(learning_by_question.get(eq.id, {}))

            out.append(
                PerQuestionStat(
                    exam_question_id=eq.id,
                    question_id=qr.id,
                    position=eq.position,
                    question_text=qr.question_text,
                    question_type=qr.question_type,
                    points_max=float(eq.points),
                    answered_count=len(ans),
                    success_rate=success,
                    difficulty=difficulty,
                    discrimination=discrimination,
                    top_wrong_answers=top_wrong,
                    learning_effect=learning,
                )
            )
        return out

    # ------------------------------------------------------------------
    # Per-submission
    # ------------------------------------------------------------------

    def per_submission(self, *, submission_id: int) -> PerSubmissionStat | None:
        submission = (
            self.db.query(Submission)
            .filter(Submission.id == submission_id)
            .one_or_none()
        )
        if submission is None:
            return None

        student = submission.student
        graded_attempt = submission.graded_attempt
        per_question: list[dict[str, Any]] = []
        bloom_mix: Counter[int] = Counter()
        # topic_heatmap: per-topic {points_awarded, points_max} aggregated
        topic_acc: dict[str, dict[str, float]] = {}

        if graded_attempt is not None:
            answers = (
                self.db.query(AttemptAnswer, Grade, ExamQuestion, QuestionReview)
                .join(Grade, Grade.attempt_answer_id == AttemptAnswer.id)
                .join(ExamQuestion, ExamQuestion.id == AttemptAnswer.exam_question_id)
                .join(QuestionReview, QuestionReview.id == ExamQuestion.question_id)
                .filter(AttemptAnswer.attempt_id == graded_attempt.id)
                .order_by(ExamQuestion.position)
                .all()
            )
            for ans, grade, eq, qr in answers:
                per_question.append(
                    {
                        "position": eq.position,
                        "question_id": qr.id,
                        "question_text": qr.question_text,
                        "topic": qr.topic,
                        "bloom_level": qr.bloom_level,
                        "points_awarded": float(grade.points_awarded),
                        "points_max": float(grade.points_max),
                        "status": grade.status,
                    }
                )
                if qr.bloom_level is not None:
                    bloom_mix[int(qr.bloom_level)] += 1
                bucket = topic_acc.setdefault(
                    qr.topic, {"points_awarded": 0.0, "points_max": 0.0}
                )
                bucket["points_awarded"] += float(grade.points_awarded)
                bucket["points_max"] += float(grade.points_max)

        # Normalise topic heatmap to percentage for ease of frontend use.
        topic_heatmap = {
            topic: {
                "points_awarded": v["points_awarded"],
                "points_max": v["points_max"],
                "percentage": (
                    100.0 * v["points_awarded"] / v["points_max"]
                    if v["points_max"] > 0
                    else 0.0
                ),
            }
            for topic, v in topic_acc.items()
        }

        return PerSubmissionStat(
            submission_id=submission.id,
            student_id=student.id if student else 0,
            student_external_id=student.external_id if student else "",
            student_display_name=student.display_name if student else None,
            total_points_awarded=float(submission.total_points_awarded),
            total_points_max=float(submission.total_points_max),
            percentage=float(submission.percentage),
            grade_status=submission.grade_status,
            per_question=per_question,
            bloom_mix=dict(bloom_mix),
            topic_heatmap=topic_heatmap,
        )

    # ------------------------------------------------------------------
    # Cross-Exam (TF-336 Subarea B)
    # ------------------------------------------------------------------

    def class_history(
        self, *, class_id: int, institution_id: int
    ) -> ClassHistoryStats | None:
        """Klassen-Verlauf: alle Studis × alle Prüfungen.

        Filtert die Submissions auf Studis, die zum Zeitpunkt des
        Aufrufs Mitglied der Klasse sind. Studis, die zwischenzeitlich
        ausgetreten sind, fliessen *nicht* in die Aggregate ein —
        Mitgliedschaft ist hier eine "as of now"-Sicht. Dass das
        retroaktive Daten verändert ist gewollt: das Klassen-Dashboard
        spiegelt die *aktuelle* Zusammensetzung wider, sonst wäre
        Klassenwechsel + Anzeige nicht mehr nachvollziehbar.
        """
        student_class = (
            self.db.query(StudentClass)
            .filter(
                StudentClass.id == class_id,
                StudentClass.institution_id == institution_id,
            )
            .one_or_none()
        )
        if student_class is None:
            return None

        members = (
            self.db.query(Student)
            .join(
                StudentClassMembership, StudentClassMembership.student_id == Student.id
            )
            .filter(StudentClassMembership.class_id == class_id)
            .order_by(Student.display_name.nullslast(), Student.external_id)
            .all()
        )
        student_ids = [s.id for s in members]
        if not student_ids:
            return ClassHistoryStats(
                class_id=class_id,
                class_name=student_class.name,
                member_count=0,
                members=[],
                exam_aggregates=[],
                topic_coverage=[],
            )

        submission_rows = (
            self.db.query(Submission, Exam)
            .join(Exam, Exam.id == Submission.exam_id)
            .filter(
                Submission.student_id.in_(student_ids),
                Exam.institution_id == institution_id,
            )
            .order_by(Exam.exam_date.nullslast(), Exam.id, Submission.student_id)
            .all()
        )

        # Per-student aggregation
        by_student: dict[int, list[StudentSubmissionRecord]] = {
            sid: [] for sid in student_ids
        }
        for submission, exam in submission_rows:
            by_student[submission.student_id].append(
                StudentSubmissionRecord(
                    submission_id=submission.id,
                    exam_id=exam.id,
                    exam_title=exam.title,
                    exam_date=exam.exam_date,
                    percentage=float(submission.percentage),
                    grade_status=submission.grade_status,
                )
            )

        member_perf = []
        for student in members:
            recs = by_student.get(student.id, [])
            avg = _safe_mean([r.percentage for r in recs])
            member_perf.append(
                ClassMemberPerformance(
                    student_id=student.id,
                    external_id=student.external_id,
                    display_name=student.display_name,
                    submission_count=len(recs),
                    avg_percentage=avg,
                    submissions=recs,
                )
            )

        # Per-exam aggregate (across this class's members only)
        exam_buckets: dict[int, list[Submission]] = {}
        exam_metadata: dict[int, Exam] = {}
        for submission, exam in submission_rows:
            exam_buckets.setdefault(exam.id, []).append(submission)
            exam_metadata[exam.id] = exam

        exam_aggregates: list[ClassExamAggregate] = []
        for exam_id, subs in sorted(
            exam_buckets.items(),
            key=lambda kv: (
                exam_metadata[kv[0]].exam_date or date.max,
                kv[0],
            ),
        ):
            exam = exam_metadata[exam_id]
            percentages = [float(s.percentage) for s in subs]
            scheme_config = _resolve_scheme_config(self.db, exam)
            passing_pct = float(exam.passing_percentage or 0)
            if scheme_config is not None:
                pass_count = sum(
                    1
                    for p in percentages
                    if is_passing(p, scheme_config, passing_percentage=passing_pct)
                )
            else:
                pass_count = sum(1 for p in percentages if p >= passing_pct)
            exam_aggregates.append(
                ClassExamAggregate(
                    exam_id=exam.id,
                    exam_title=exam.title,
                    exam_date=exam.exam_date,
                    submission_count=len(subs),
                    avg_percentage=_safe_mean(percentages),
                    pass_rate=pass_count / len(percentages) if percentages else None,
                )
            )

        # Topic coverage across the class — sum points across all
        # graded attempts of this class's members.
        topic_coverage = self._aggregate_topic_coverage(
            submission_ids=[
                s.id for s, _ in submission_rows if s.graded_attempt_id is not None
            ]
        )

        return ClassHistoryStats(
            class_id=class_id,
            class_name=student_class.name,
            member_count=len(members),
            members=member_perf,
            exam_aggregates=exam_aggregates,
            topic_coverage=topic_coverage,
        )

    def student_history(
        self, *, student_id: int, institution_id: int
    ) -> StudentHistoryStats | None:
        """Studi-Verlauf: alle Submissions chronologisch + Bloom + Topic."""
        student = (
            self.db.query(Student)
            .filter(
                Student.id == student_id,
                Student.institution_id == institution_id,
            )
            .one_or_none()
        )
        if student is None:
            return None

        submission_rows = (
            self.db.query(Submission, Exam)
            .join(Exam, Exam.id == Submission.exam_id)
            .filter(
                Submission.student_id == student_id,
                Exam.institution_id == institution_id,
            )
            .order_by(Exam.exam_date.nullslast(), Exam.id)
            .all()
        )

        records = [
            StudentSubmissionRecord(
                submission_id=submission.id,
                exam_id=exam.id,
                exam_title=exam.title,
                exam_date=exam.exam_date,
                percentage=float(submission.percentage),
                grade_status=submission.grade_status,
            )
            for submission, exam in submission_rows
        ]

        graded_submission_ids = [
            s.id for s, _ in submission_rows if s.graded_attempt_id is not None
        ]
        topic_coverage = self._aggregate_topic_coverage(
            submission_ids=graded_submission_ids
        )

        # Bloom-Mix aggregated across all answered questions in graded
        # attempts. Bloom levels live on the QuestionReview master.
        bloom_rows = (
            self.db.query(QuestionReview.bloom_level)
            .join(ExamQuestion, ExamQuestion.question_id == QuestionReview.id)
            .join(AttemptAnswer, AttemptAnswer.exam_question_id == ExamQuestion.id)
            .join(Attempt, Attempt.id == AttemptAnswer.attempt_id)
            .join(Submission, Submission.id == Attempt.submission_id)
            .filter(
                Submission.student_id == student_id,
                Submission.graded_attempt_id == Attempt.id,
                QuestionReview.bloom_level.isnot(None),
            )
            .all()
        )
        bloom_mix: Counter[int] = Counter()
        for (level,) in bloom_rows:
            if level is not None:
                bloom_mix[int(level)] += 1

        classes = (
            self.db.query(StudentClass)
            .join(
                StudentClassMembership,
                StudentClassMembership.class_id == StudentClass.id,
            )
            .filter(
                StudentClassMembership.student_id == student_id,
                StudentClass.institution_id == institution_id,
            )
            .order_by(StudentClass.name)
            .all()
        )

        avg = _safe_mean([r.percentage for r in records])
        return StudentHistoryStats(
            student_id=student.id,
            external_id=student.external_id,
            display_name=student.display_name,
            submission_count=len(records),
            avg_percentage=avg,
            submissions=records,
            bloom_mix=dict(bloom_mix),
            topic_heatmap=topic_coverage,
            classes=[
                StudentClassRef(class_id=c.id, class_name=c.name) for c in classes
            ],
        )

    def _aggregate_topic_coverage(
        self, *, submission_ids: list[int]
    ) -> list[TopicAggregate]:
        """Sum (points_awarded, points_max) per topic over graded answers."""
        if not submission_ids:
            return []
        rows = (
            self.db.query(
                QuestionReview.topic,
                Grade.points_awarded,
                Grade.points_max,
            )
            .join(ExamQuestion, ExamQuestion.question_id == QuestionReview.id)
            .join(AttemptAnswer, AttemptAnswer.exam_question_id == ExamQuestion.id)
            .join(Grade, Grade.attempt_answer_id == AttemptAnswer.id)
            .join(Attempt, Attempt.id == AttemptAnswer.attempt_id)
            .join(Submission, Submission.id == Attempt.submission_id)
            .filter(
                Submission.id.in_(submission_ids),
                Submission.graded_attempt_id == Attempt.id,
            )
            .all()
        )
        acc: dict[str, dict[str, float]] = {}
        for topic, points_awarded, points_max in rows:
            key = topic or "—"
            bucket = acc.setdefault(key, {"awarded": 0.0, "max": 0.0})
            bucket["awarded"] += float(points_awarded or 0.0)
            bucket["max"] += float(points_max or 0.0)
        return sorted(
            (
                TopicAggregate(
                    topic=topic,
                    points_awarded=v["awarded"],
                    points_max=v["max"],
                    percentage=(
                        100.0 * v["awarded"] / v["max"] if v["max"] > 0 else 0.0
                    ),
                )
                for topic, v in acc.items()
            ),
            key=lambda t: t.topic,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_exam_or_raise(self, exam_id: int) -> Exam:
        exam = self.db.query(Exam).filter(Exam.id == exam_id).one_or_none()
        if exam is None:
            raise ValueError(f"Exam {exam_id} nicht gefunden")
        return exam


# ---------------------------------------------------------------------------
# Pure helpers — kept module-level for unit-test access
# ---------------------------------------------------------------------------


def _safe_mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _safe_median(values: list[float]) -> float | None:
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return (s[mid - 1] + s[mid]) / 2.0 if n % 2 == 0 else s[mid]


def _empty_histogram() -> list[HistogramBucket]:
    # 10 buckets of 10 % each. The last bucket owns 100 % so a perfect
    # score doesn't fall into a non-existent ``[100, 110)`` slot.
    return [
        HistogramBucket(from_pct=i, to_pct=i + 10, count=0) for i in range(0, 100, 10)
    ]


def _histogram(values: list[float]) -> list[HistogramBucket]:
    buckets = _empty_histogram()
    if not values:
        return buckets
    counts = [0] * len(buckets)
    for v in values:
        clamped = max(0.0, min(100.0, v))
        index = min(int(clamped // 10), len(buckets) - 1)
        counts[index] += 1
    return [
        HistogramBucket(from_pct=b.from_pct, to_pct=b.to_pct, count=c)
        for b, c in zip(buckets, counts)
    ]


def _success_and_difficulty(
    rows: list, points_max: float
) -> tuple[float | None, float | None]:
    """Spec 8: ``success_rate`` = mean(points_awarded / points_max);
    ``difficulty`` = share of "completely correct" answers (1.0 means
    full points, partial credit doesn't count as "correct" for the
    Schwierigkeits-Index).
    """
    if not rows:
        return None, None
    fractions = []
    fully_correct = 0
    for r in rows:
        max_for_row = float(r.points_max) if r.points_max else float(points_max)
        if max_for_row <= 0:
            continue
        frac = float(r.points_awarded) / max_for_row
        fractions.append(frac)
        if frac >= 0.999:
            fully_correct += 1
    if not fractions:
        return 0.0, 0.0
    return sum(fractions) / len(fractions), fully_correct / len(fractions)


def _discrimination(rows: list) -> float | None:
    """Pearson correlation between item-success-fraction and the
    submission's overall percentage. Returns ``None`` when fewer than
    two distinct submissions exist or when one of the series is constant
    (correlation would divide by zero).
    """
    pairs: list[tuple[float, float]] = []
    for r in rows:
        max_for_row = float(r.points_max) if r.points_max else 0.0
        if max_for_row <= 0:
            continue
        item_frac = float(r.points_awarded) / max_for_row
        pairs.append((item_frac, float(r.percentage)))

    if len(pairs) < 2:
        return None

    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denom_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    denom_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if denom_x == 0 or denom_y == 0:
        return None
    return num / (denom_x * denom_y)


def _top_wrong_answers(rows: list, top_n: int = 3) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for r in rows:
        if r.is_correct is False and r.given_answer:
            counter[str(r.given_answer)] += 1
    return counter.most_common(top_n)


def _learning_effect(
    per_student: dict[int, dict[int, bool]],
) -> float | None:
    """Per-student paired delta across consecutive attempts.

    Argument shape: ``{student_id: {attempt_number: is_correct}}`` — one
    boolean per (student, attempt) for a single question.

    Only students with two or more attempts on this question contribute.
    For each such student we compute the per-question correctness delta
    between consecutive sorted attempts (1→2, 2→3, …). The result is
    the mean of those per-student deltas.

    The naive cohort-mean (mean@N+1 minus mean@N over *all* students)
    drifted because a student who only ever took attempt 1 inflated
    the attempt-1 cohort and never appeared in attempt 2. Pairing by
    student is the psychometric-clean comparison.

    Returns ``None`` when no student has multiple attempts.
    """
    deltas: list[float] = []
    for attempts in per_student.values():
        if len(attempts) < 2:
            continue
        ordered_keys = sorted(attempts.keys())
        for prev, curr in zip(ordered_keys, ordered_keys[1:]):
            deltas.append(float(attempts[curr]) - float(attempts[prev]))
    if not deltas:
        return None
    return sum(deltas) / len(deltas)
