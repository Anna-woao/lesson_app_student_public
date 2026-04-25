"""
student_home_viewmodel.py

公开学生端首页聚合层。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import db_student as dbs


@dataclass
class StudentTaskCard:
    title: str
    eta: str
    description: str
    target_section: str
    is_primary: bool = False


@dataclass
class StudentHistorySummary:
    recent_lessons_count: int
    learned_vocab_count: int
    active_book_count: int
    test_record_count: int


@dataclass
class StudentHomeViewModel:
    student_name: str
    title_label: str
    stage_label: str
    primary_task: str
    primary_task_eta: str
    weekly_completion_ratio: float
    streak_days: int
    unlocked_modules: List[str]
    growth_feedback: str
    current_task_cards: List[Dict[str, Any]]
    history_task_cards: List[Dict[str, Any]]
    history_summary: Dict[str, int]


def _safe_parse_date(raw_value: Any) -> Optional[date]:
    if not raw_value:
        return None

    text = str(raw_value).strip()
    if not text:
        return None

    normalized = text.replace("T", " ")
    candidates = [
        normalized[:10],
        normalized[:19],
        normalized,
    ]

    for candidate in candidates:
        try:
            if len(candidate) == 10:
                return datetime.strptime(candidate, "%Y-%m-%d").date()
            return datetime.strptime(candidate, "%Y-%m-%d %H:%M:%S").date()
        except ValueError:
            continue
    return None


def _build_title_label(learned_vocab_count: int) -> str:
    if learned_vocab_count >= 200:
        return "成长领航者"
    if learned_vocab_count >= 80:
        return "持续进阶"
    if learned_vocab_count >= 20:
        return "稳步前进"
    return "启程学员"


def _build_stage_label(latest_accuracy: Optional[float]) -> str:
    if latest_accuracy is None:
        return "准备起步"
    if latest_accuracy < 0.6:
        return "夯实基础"
    if latest_accuracy < 0.85:
        return "稳定提升"
    return "持续进阶"


def _build_growth_feedback(latest_accuracy: Optional[float]) -> str:
    if latest_accuracy is None:
        return "今天适合先做一次轻量检测，找到最合适的起点。"
    if latest_accuracy < 0.6:
        return "你已经开始建立基础了，先把今天这一小步走稳。"
    if latest_accuracy < 0.85:
        return "最近状态在变稳，继续保持会看到更明显进步。"
    return "这段时间发挥不错，可以开始挑战更进一步的内容。"


def _build_unlocked_modules(
    has_recent_lessons: bool,
    has_test_records: bool,
    has_learned_vocab: bool,
) -> List[str]:
    modules: List[str] = []
    if has_recent_lessons:
        modules.append("学案训练")
    if has_test_records:
        modules.append("词汇检测")
    if has_learned_vocab:
        modules.append("学习进度")
    return modules


def _calculate_streak_days(activity_dates: List[date], today: date) -> int:
    if not activity_dates:
        return 0

    remaining = set(activity_dates)
    streak = 0
    cursor_day = today

    while cursor_day in remaining:
        streak += 1
        cursor_day -= timedelta(days=1)

    return streak


def _calculate_weekly_completion_ratio(activity_dates: List[date], today: date) -> float:
    week_start = today - timedelta(days=today.weekday())
    week_dates = {item for item in activity_dates if item >= week_start}
    return min(len(week_dates) / 5.0, 1.0)


def _append_task_card(cards: List[StudentTaskCard], card: StudentTaskCard) -> None:
    existing_titles = {item.title for item in cards}
    if card.title not in existing_titles and len(cards) < 3:
        cards.append(card)


def _build_history_task_cards(
    recent_lessons: List[Any],
    learned_vocab_count: int,
    book_progress: List[Any],
    test_records: List[Any],
) -> List[StudentTaskCard]:
    cards: List[StudentTaskCard] = []
    if recent_lessons:
        latest_lesson = recent_lessons[0]
        cards.append(
            StudentTaskCard(
                title="已完成学案",
                eta=f"{len(recent_lessons)} 份可回看",
                description=f"最近一份：{latest_lesson[3] or latest_lesson[1] or '继续回看'}。",
                target_section="recent_lessons",
            )
        )
    if learned_vocab_count > 0:
        cards.append(
            StudentTaskCard(
                title="已学单词",
                eta=f"{learned_vocab_count} 个已记录",
                description="这里可以回看已经接触过的词汇和当前积累。",
                target_section="learned_words",
            )
        )
    if test_records:
        latest_record = test_records[0]
        cards.append(
            StudentTaskCard(
                title="历史检测记录",
                eta=f"{len(test_records)} 条记录",
                description=f"最近一次：{latest_record[8]}/{latest_record[7]}，可回看表现变化。",
                target_section="test_history",
            )
        )
    elif book_progress:
        cards.append(
            StudentTaskCard(
                title="学习进度回看",
                eta=f"{sum(1 for row in book_progress if row[4] > 0)} 本词书",
                description="已经推进过的词书和单元进度会在这里持续累计。",
                target_section="progress",
            )
        )

    return cards[:3]


def build_student_home_viewmodel(student: Dict[str, Any]) -> Dict[str, Any]:
    student_id = student["id"]
    recent_lessons = dbs.get_student_recent_lessons(student_id, limit=5)
    learned_summary = dbs.get_student_learned_vocab_summary(student_id)
    book_progress = dbs.get_student_book_progress(student_id)
    test_records = dbs.get_student_vocab_test_records(student_id, limit=10)
    activity_dates_raw = dbs.get_student_activity_dates(student_id, days=30)
    latest_diagnosis = dbs.get_latest_diagnosis_record(student_id)
    latest_snapshot = dbs.get_latest_profile_snapshot(student_id)

    learned_vocab_count = learned_summary.get("total_unique_words", 0)
    latest_accuracy = test_records[0][9] if test_records else None
    has_recent_lessons = bool(recent_lessons)
    has_test_records = bool(test_records)
    has_learned_vocab = learned_vocab_count > 0
    has_review_items = any(row[7] > 0 for row in book_progress)
    has_unfinished_book = any(row[4] > 0 and row[3] < row[4] for row in book_progress)
    has_diagnosis = latest_diagnosis is not None

    if not has_diagnosis:
        primary_card = StudentTaskCard(
            title="完成首次诊断",
            eta="8-12 分钟",
            description="先用一轮轻量诊断找到更适合你的起点，后面的任务会更贴合你当前状态。",
            target_section="initial_diagnosis",
            is_primary=True,
        )
    elif not has_test_records:
        primary_card = StudentTaskCard(
            title="完成一次词汇检测",
            eta="10 分钟",
            description="先用一次轻量检测找到更适合你的起点。",
            target_section="vocab_test",
            is_primary=True,
        )
    elif has_review_items:
        primary_card = StudentTaskCard(
            title="完成今日复习巩固",
            eta="15 分钟",
            description="把需要回看的内容先稳一稳，今天会更轻松。",
            target_section="progress",
            is_primary=True,
        )
    elif has_unfinished_book:
        primary_card = StudentTaskCard(
            title="继续当前词书训练",
            eta="20 分钟",
            description="顺着当前进度继续推进，保持今天的学习节奏。",
            target_section="progress",
            is_primary=True,
        )
    elif has_recent_lessons:
        primary_card = StudentTaskCard(
            title="回看最近学案并完成练习",
            eta="15 分钟",
            description="把最近一次学案再过一遍，巩固今天最重要的内容。",
            target_section="recent_lessons",
            is_primary=True,
        )
    else:
        primary_card = StudentTaskCard(
            title="开始今天的成长之旅",
            eta="10 分钟",
            description="先从一小步开始，系统会陪你慢慢进入状态。",
            target_section="vocab_test",
            is_primary=True,
        )

    current_task_cards: List[StudentTaskCard] = [primary_card]
    if has_diagnosis and has_recent_lessons:
        latest_lesson = recent_lessons[0]
        _append_task_card(
            current_task_cards,
            StudentTaskCard(
                title="回看最近学案",
                eta="15 分钟",
                description=f"最近学案：{latest_lesson[3] or latest_lesson[1] or '继续练习'}。",
                target_section="recent_lessons",
            ),
        )
    if has_diagnosis and has_review_items:
        _append_task_card(
            current_task_cards,
            StudentTaskCard(
                title="查看待复习进度",
                eta="15 分钟",
                description="先处理需要复习的内容，会更容易看到进步。",
                target_section="progress",
            ),
        )
    if has_diagnosis and has_test_records:
        latest_record = test_records[0]
        _append_task_card(
            current_task_cards,
            StudentTaskCard(
                title="回看最近一次检测",
                eta="10 分钟",
                description=(
                    f"最近一次表现：{latest_record[8]}/{latest_record[7]}，"
                    f"再看一眼会更清楚下一步。"
                ),
                target_section="test_history",
            ),
        )

    activity_dates = [
        parsed_date
        for parsed_date in (_safe_parse_date(item) for item in activity_dates_raw)
        if parsed_date is not None
    ]
    today = date.today()

    history_summary = StudentHistorySummary(
        recent_lessons_count=len(recent_lessons),
        learned_vocab_count=learned_vocab_count,
        active_book_count=sum(1 for row in book_progress if row[4] > 0),
        test_record_count=len(test_records),
    )
    title_label = (latest_snapshot or {}).get("title_label") or _build_title_label(learned_vocab_count)
    stage_label = (latest_snapshot or {}).get("stage_label") or _build_stage_label(latest_accuracy)
    growth_feedback = (latest_snapshot or {}).get("summary_text") or _build_growth_feedback(latest_accuracy)
    viewmodel = StudentHomeViewModel(
        student_name=student.get("name", "同学"),
        title_label=title_label,
        stage_label=stage_label,
        primary_task=primary_card.title,
        primary_task_eta=primary_card.eta,
        weekly_completion_ratio=_calculate_weekly_completion_ratio(activity_dates, today),
        streak_days=_calculate_streak_days(activity_dates, today),
        unlocked_modules=_build_unlocked_modules(
            has_recent_lessons=has_recent_lessons,
            has_test_records=has_test_records or has_diagnosis,
            has_learned_vocab=has_learned_vocab or has_diagnosis,
        ),
        growth_feedback=growth_feedback,
        current_task_cards=[asdict(card) for card in current_task_cards],
        history_task_cards=[
            asdict(card)
            for card in _build_history_task_cards(
                recent_lessons=recent_lessons,
                learned_vocab_count=learned_vocab_count,
                book_progress=book_progress,
                test_records=test_records,
            )
        ],
        history_summary=asdict(history_summary),
    )
    return asdict(viewmodel)
