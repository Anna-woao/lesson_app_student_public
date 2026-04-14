"""学生端 Supabase 数据层（含词汇检测作答）"""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple

from supabase_client import get_supabase_client


def _fetch_all_rows(query_builder, page_size: int = 1000):
    start = 0
    all_rows = []
    while True:
        resp = query_builder.range(start, start + page_size - 1).execute()
        rows = resp.data or []
        all_rows.extend(rows)
        if len(rows) < page_size:
            break
        start += page_size
    return all_rows


def get_all_students():
    supabase = get_supabase_client()
    resp = supabase.table("students").select("id, name, grade").order("id", desc=False).execute()
    rows = resp.data or []
    return [(row["id"], row["name"], row["grade"]) for row in rows]


def get_student_recent_lessons(student_id: int, limit: int = 10):
    supabase = get_supabase_client()
    resp = (
        supabase.table("lessons")
        .select("id, lesson_type, difficulty, topic, created_at")
        .eq("student_id", student_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = resp.data or []
    return [(r["id"], r.get("lesson_type"), r.get("difficulty"), r.get("topic"), r.get("created_at")) for r in rows]


def get_lesson_detail_for_student(student_id: int, lesson_id: int):
    supabase = get_supabase_client()
    resp = (
        supabase.table("lessons")
        .select("id, lesson_type, difficulty, topic, content, created_at")
        .eq("student_id", student_id)
        .eq("id", lesson_id)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    return rows[0] if rows else None


def get_student_learned_vocab(student_id: int, limit: int = 200):
    supabase = get_supabase_client()
    prog = (
        supabase.table("student_vocab_progress")
        .select("vocab_item_id, status, review_count, error_count, memory_score, first_learned_at, last_review_time, next_review_time")
        .eq("student_id", student_id)
        .order("first_learned_at", desc=True)
        .limit(limit)
        .execute()
    )
    progress_rows = prog.data or []
    vocab_ids = [row["vocab_item_id"] for row in progress_rows if row.get("vocab_item_id") is not None]
    vocab_map = {}
    if vocab_ids:
        vocab_rows = (
            supabase.table("vocab_items")
            .select("id, lemma, default_meaning")
            .in_("id", vocab_ids)
            .execute()
        ).data or []
        vocab_map = {r["id"]: (r.get("lemma", ""), r.get("default_meaning", "") or "") for r in vocab_rows}

    result = []
    for row in progress_rows:
        vocab_item_id = row.get("vocab_item_id")
        lemma, meaning = vocab_map.get(vocab_item_id, ("", ""))
        if lemma:
            result.append((
                lemma,
                meaning,
                row.get("status", "learning"),
                row.get("review_count", 0),
                row.get("error_count", 0),
                row.get("memory_score", 3.0),
                row.get("first_learned_at"),
                row.get("last_review_time"),
                row.get("next_review_time"),
            ))
    return result


def get_student_book_progress(student_id: int):
    supabase = get_supabase_client()
    books = (
        supabase.table("word_books")
        .select("id, book_name, volume_name")
        .order("id", desc=False)
        .execute()
    ).data or []

    progress_rows = (
        supabase.table("student_vocab_progress")
        .select("vocab_item_id, first_source_book_id, first_source_unit_id, status")
        .eq("student_id", student_id)
        .execute()
    ).data or []

    result = []
    for book in books:
        book_id = book["id"]
        total_resp = (
            supabase.table("book_unit_vocab")
            .select("id", count="exact")
            .eq("book_id", book_id)
            .execute()
        )
        total_count = total_resp.count or 0

        learned_rows = [r for r in progress_rows if r.get("first_source_book_id") == book_id]
        learned_ids = {r["vocab_item_id"] for r in learned_rows if r.get("vocab_item_id") is not None}

        mastered_count = len({r["vocab_item_id"] for r in learned_rows if r.get("status") == "mastered"})
        learning_count = len({r["vocab_item_id"] for r in learned_rows if r.get("status") == "learning"})
        review_count = len({r["vocab_item_id"] for r in learned_rows if r.get("status") == "review"})

        result.append((
            book_id,
            book.get("book_name"),
            book.get("volume_name"),
            len(learned_ids),
            total_count,
            mastered_count,
            learning_count,
            review_count,
        ))
    return result


def get_student_unit_progress(student_id: int, book_id: int):
    supabase = get_supabase_client()
    units = (
        supabase.table("word_units")
        .select("id, unit_name, unit_order")
        .eq("book_id", book_id)
        .order("unit_order", desc=False)
        .execute()
    ).data or []

    buv_rows = _fetch_all_rows(
        supabase.table("book_unit_vocab").select("unit_id, vocab_item_id").eq("book_id", book_id)
    )

    progress_rows = (
        supabase.table("student_vocab_progress")
        .select("vocab_item_id, first_source_book_id, first_source_unit_id")
        .eq("student_id", student_id)
        .eq("first_source_book_id", book_id)
        .execute()
    ).data or []

    vocab_to_units = {}
    for row in buv_rows:
        unit_id = row.get("unit_id")
        vocab_item_id = row.get("vocab_item_id")
        if unit_id is None or vocab_item_id is None:
            continue
        vocab_to_units.setdefault(vocab_item_id, set()).add(unit_id)

    normalized_progress = []
    for row in progress_rows:
        vocab_item_id = row.get("vocab_item_id")
        unit_id = row.get("first_source_unit_id")
        if unit_id is None and vocab_item_id in vocab_to_units and len(vocab_to_units[vocab_item_id]) == 1:
            unit_id = list(vocab_to_units[vocab_item_id])[0]
        normalized_progress.append((vocab_item_id, unit_id))

    result = []
    for unit in units:
        unit_id = unit["id"]
        total_vocab_ids = {
            row["vocab_item_id"]
            for row in buv_rows
            if row.get("unit_id") == unit_id and row.get("vocab_item_id") is not None
        }
        learned_vocab_ids = {
            vocab_item_id
            for vocab_item_id, learned_unit_id in normalized_progress
            if learned_unit_id == unit_id and vocab_item_id is not None
        }
        result.append((
            unit_id,
            unit.get("unit_name"),
            unit.get("unit_order", 0),
            len(learned_vocab_ids),
            len(total_vocab_ids),
        ))
    return result


def get_student_vocab_test_records(student_id: int, limit: int = 20):
    supabase = get_supabase_client()
    response = (
        supabase.table("vocab_test_records")
        .select("""
            id,
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
            created_at
        """)
        .eq("student_id", student_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = response.data or []
    return [
        (
            row["id"],
            row.get("source_type"),
            row.get("source_book_id"),
            row.get("source_unit_id"),
            row.get("source_label"),
            row.get("test_type"),
            row.get("test_mode"),
            row.get("total_count"),
            row.get("correct_count"),
            row.get("accuracy"),
            row.get("is_synced_to_progress"),
            row.get("is_wrong_retry_round"),
            row.get("created_at"),
        )
        for row in rows
    ]


def get_vocab_test_record_items(test_record_id: int):
    supabase = get_supabase_client()
    response = (
        supabase.table("vocab_test_record_items")
        .select("vocab_item_id, word, meaning, mode, user_answer, is_correct")
        .eq("test_record_id", test_record_id)
        .order("id", desc=False)
        .execute()
    )
    rows = response.data or []
    return [
        (
            row.get("vocab_item_id"),
            row.get("word"),
            row.get("meaning"),
            row.get("mode"),
            row.get("user_answer"),
            row.get("is_correct"),
        )
        for row in rows
    ]


def get_all_word_books():
    supabase = get_supabase_client()
    rows = (
        supabase.table("word_books")
        .select("id, book_name, volume_name")
        .order("id", desc=False)
        .execute()
    ).data or []
    result = []
    for row in rows:
        label = row["book_name"] if not row.get("volume_name") else f"{row['book_name']}（{row['volume_name']}）"
        result.append((row["id"], label))
    return result


def get_units_by_book(book_id: int):
    supabase = get_supabase_client()
    rows = (
        supabase.table("word_units")
        .select("id, unit_name, unit_order")
        .eq("book_id", book_id)
        .order("unit_order", desc=False)
        .execute()
    ).data or []
    return [(r["id"], r["unit_name"], r.get("unit_order", 0)) for r in rows]


def _fetch_vocab_map(vocab_ids: List[int]) -> Dict[int, Tuple[str, str]]:
    supabase = get_supabase_client()
    if not vocab_ids:
        return {}
    rows = (
        supabase.table("vocab_items")
        .select("id, lemma, default_meaning")
        .in_("id", vocab_ids)
        .execute()
    ).data or []
    return {r["id"]: (r.get("lemma", ""), r.get("default_meaning", "") or "") for r in rows}


def build_progress_test(student_id: int, test_type: str, test_mode: str, test_count: int):
    supabase = get_supabase_client()
    status_filter = "learning" if test_type == "新词检测" else "review"
    rows = (
        supabase.table("student_vocab_progress")
        .select("vocab_item_id, first_source_book_id, first_source_unit_id, status")
        .eq("student_id", student_id)
        .eq("status", status_filter)
        .limit(500)
        .execute()
    ).data or []
    if not rows:
        return False, "当前没有可用的学习进度检测词。"
    random.shuffle(rows)
    rows = rows[:test_count]

    vocab_map = _fetch_vocab_map([r["vocab_item_id"] for r in rows if r.get("vocab_item_id") is not None])
    questions = _build_questions_from_vocab_map(vocab_map, rows, test_mode)
    payload = {
        "source_type": "progress",
        "source_book_id": None,
        "source_unit_id": None,
        "test_type": test_type,
        "test_mode": test_mode,
        "questions": questions,
    }
    return True, payload


def build_book_test(student_id: int, book_id: int, unit_id: Optional[int], test_mode: str, test_count: int):
    supabase = get_supabase_client()
    query = supabase.table("book_unit_vocab").select("vocab_item_id, book_id, unit_id")
    query = query.eq("book_id", book_id)
    if unit_id is not None:
        query = query.eq("unit_id", unit_id)

    rows = _fetch_all_rows(query)
    if not rows:
        return False, "当前范围内没有可用单词。"
    random.shuffle(rows)
    rows = rows[:test_count]

    vocab_map = _fetch_vocab_map([r["vocab_item_id"] for r in rows if r.get("vocab_item_id") is not None])
    questions = _build_questions_from_vocab_map(vocab_map, rows, test_mode)
    payload = {
        "source_type": "book",
        "source_book_id": book_id,
        "source_unit_id": unit_id,
        "test_type": "词汇书抽词检测",
        "test_mode": test_mode,
        "questions": questions,
    }
    return True, payload


def _build_questions_from_vocab_map(vocab_map, rows, test_mode: str):
    all_meanings = [meaning for _, meaning in vocab_map.values() if meaning]
    questions = []

    for row in rows:
        vocab_item_id = row.get("vocab_item_id")
        word, meaning = vocab_map.get(vocab_item_id, ("", ""))
        if not word:
            continue

        one_mode = random.choice(["英译中", "中译英"]) if test_mode == "混合模式" else test_mode

        q = {
            "vocab_item_id": vocab_item_id,
            "word": word,
            "meaning": meaning,
            "mode": one_mode,
        }

        if one_mode == "英译中":
            distractors = [m for m in all_meanings if m and m != meaning]
            random.shuffle(distractors)
            options = [meaning] + distractors[:3]
            random.shuffle(options)
            q["options"] = options

        questions.append(q)

    return questions


def submit_student_test(student_id: int, payload: dict, user_answers: dict, source_label: str):
    results = []
    score = 0
    total = len(payload["questions"])

    for q in payload["questions"]:
        vocab_item_id = q["vocab_item_id"]
        mode = q["mode"]
        user_answer = user_answers.get(vocab_item_id, "")
        if mode == "英译中":
            is_correct = (user_answer or "").strip() == (q["meaning"] or "").strip()
        else:
            is_correct = (user_answer or "").strip().lower() == (q["word"] or "").strip().lower()

        if is_correct:
            score += 1

        results.append({
            "vocab_item_id": vocab_item_id,
            "word": q["word"],
            "meaning": q["meaning"],
            "mode": mode,
            "user_answer": user_answer,
            "is_correct": is_correct,
        })

    accuracy = (score / total) if total else 0.0

    test_record_id = None
    try:
        supabase = get_supabase_client()
        record_resp = (
            supabase.table("vocab_test_records")
            .insert({
                "student_id": student_id,
                "source_type": payload.get("source_type"),
                "source_book_id": payload.get("source_book_id"),
                "source_unit_id": payload.get("source_unit_id"),
                "source_label": source_label,
                "test_type": payload.get("test_type"),
                "test_mode": payload.get("test_mode"),
                "total_count": total,
                "correct_count": score,
                "accuracy": accuracy,
                "is_synced_to_progress": False,
                "is_wrong_retry_round": False,
            })
            .execute()
        )
        record_rows = record_resp.data or []
        if record_rows:
            test_record_id = record_rows[0]["id"]

        if test_record_id:
            item_payloads = []
            for r in results:
                item_payloads.append({
                    "test_record_id": test_record_id,
                    "vocab_item_id": r["vocab_item_id"],
                    "word": r["word"],
                    "meaning": r["meaning"],
                    "mode": r["mode"],
                    "user_answer": r["user_answer"],
                    "is_correct": r["is_correct"],
                })
            if item_payloads:
                supabase.table("vocab_test_record_items").insert(item_payloads).execute()
    except Exception:
        pass

    return {
        "score": score,
        "total": total,
        "accuracy": accuracy,
        "results": results,
        "test_record_id": test_record_id,
    }
