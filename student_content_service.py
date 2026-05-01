"""Service-layer view models for student content pages."""

from __future__ import annotations

from typing import Any

import db_student as dbs


def build_lessons_page_data(student_id: int, limit: int = 10) -> dict[str, Any]:
    lessons = dbs.get_student_recent_lesson_snapshots(student_id, limit=limit)
    latest_lesson = lessons[0] if lessons else None
    return {
        "lessons": lessons,
        "latest_lesson": latest_lesson,
        "lesson_count": len(lessons),
    }


def build_learned_words_page_data(student_id: int) -> dict[str, Any]:
    summary = dbs.get_student_learned_vocab_summary(student_id)
    lesson_groups = summary.get("lesson_groups", [])
    return {
        "total_unique_words": summary.get("total_unique_words", 0),
        "lesson_groups": lesson_groups,
        "preview_groups": lesson_groups[:3],
        "lesson_group_count": len(lesson_groups),
    }


def build_progress_page_data(student_id: int) -> dict[str, Any]:
    rows = dbs.get_student_book_progress(student_id)
    books = []
    total_learned = 0
    total_vocab = 0
    total_review = 0
    active_book_count = 0

    for row in rows:
        (
            book_id,
            book_name,
            volume_name,
            learned_count,
            total_count,
            mastered_count,
            learning_count,
            review_count,
        ) = row
        label = book_name if not volume_name else f"{book_name}（{volume_name}）"
        ratio = (learned_count / total_count) if total_count else 0.0
        unit_rows = dbs.get_student_unit_progress(student_id, book_id)
        units = [
            {
                "unit_id": unit_id,
                "unit_name": unit_name,
                "unit_order": unit_order,
                "learned_count": unit_learned,
                "total_count": unit_total,
                "ratio": (unit_learned / unit_total) if unit_total else 0.0,
            }
            for unit_id, unit_name, unit_order, unit_learned, unit_total in unit_rows
        ]
        books.append(
            {
                "book_id": book_id,
                "book_name": book_name,
                "volume_name": volume_name,
                "label": label,
                "learned_count": learned_count,
                "total_count": total_count,
                "mastered_count": mastered_count,
                "learning_count": learning_count,
                "review_count": review_count,
                "ratio": ratio,
                "units": units,
            }
        )
        total_learned += learned_count
        total_vocab += total_count
        total_review += review_count
        if total_count > 0:
            active_book_count += 1

    return {
        "books": books,
        "active_book_count": active_book_count,
        "total_learned": total_learned,
        "total_vocab": total_vocab,
        "total_review": total_review,
    }


def build_test_history_page_data(student_id: int, limit: int = 20) -> dict[str, Any]:
    rows = dbs.get_student_vocab_test_records(student_id, limit=limit)
    records = []
    for row in rows:
        (
            test_record_id,
            source_type,
            source_book_id,
            source_unit_id,
            source_label,
            test_type,
            test_mode,
            total_count,
            correct_count,
            accuracy,
            is_synced_to_progress,
            is_wrong_retry_round,
            created_at,
        ) = row
        records.append(
            {
                "test_record_id": test_record_id,
                "source_type": source_type,
                "source_book_id": source_book_id,
                "source_unit_id": source_unit_id,
                "source_label": source_label,
                "test_type": test_type,
                "test_mode": test_mode,
                "total_count": total_count,
                "correct_count": correct_count,
                "accuracy": accuracy,
                "is_synced_to_progress": is_synced_to_progress,
                "is_wrong_retry_round": is_wrong_retry_round,
                "created_at": created_at,
                "retry_tag": " | 错词重测" if is_wrong_retry_round else "",
                "sync_tag": "已同步到学习进度" if is_synced_to_progress else "仅记录未同步",
            }
        )

    latest_record = records[0] if records else None
    return {
        "records": records,
        "latest_record": latest_record,
        "record_count": len(records),
    }


def build_test_feedback_results(test_record_id: int) -> list[dict[str, Any]]:
    item_rows = dbs.get_vocab_test_record_items(test_record_id)
    return [
        {
            "vocab_item_id": vocab_item_id,
            "word": word,
            "meaning": meaning,
            "mode": mode,
            "user_answer": user_answer,
            "is_correct": is_correct,
        }
        for vocab_item_id, word, meaning, mode, user_answer, is_correct in item_rows
    ]
