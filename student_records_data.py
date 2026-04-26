from __future__ import annotations

from supabase_client import get_admin_supabase_client, get_supabase_client


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


def get_lesson_new_vocab_for_student(student_id: int, lesson_id: int):
    supabase = get_supabase_client()
    lesson_resp = (
        supabase.table("lessons")
        .select("id")
        .eq("student_id", student_id)
        .eq("id", lesson_id)
        .limit(1)
        .execute()
    )
    if not (lesson_resp.data or []):
        return []

    link_rows = (
        supabase.table("lesson_vocab_items")
        .select("vocab_item_id, word_type")
        .eq("lesson_id", lesson_id)
        .execute()
    ).data or []

    new_vocab_ids = []
    seen_ids = set()
    for row in link_rows:
        word_type = (row.get("word_type") or "").strip().lower()
        vocab_item_id = row.get("vocab_item_id")
        if word_type not in {"new", "鏂拌瘝"} or vocab_item_id is None:
            continue
        if vocab_item_id in seen_ids:
            continue
        seen_ids.add(vocab_item_id)
        new_vocab_ids.append(vocab_item_id)

    if not new_vocab_ids:
        return []

    vocab_rows = (
        supabase.table("vocab_items")
        .select("id, lemma, pos, ipa_br, ipa_am, default_meaning, example_en, example_zh")
        .in_("id", new_vocab_ids)
        .execute()
    ).data or []
    vocab_map = {row["id"]: row for row in vocab_rows}

    result = []
    for vocab_item_id in new_vocab_ids:
        row = vocab_map.get(vocab_item_id)
        if not row:
            continue
        result.append({
            "id": vocab_item_id,
            "lemma": row.get("lemma", ""),
            "pos": row.get("pos", ""),
            "ipa_br": row.get("ipa_br", ""),
            "ipa_am": row.get("ipa_am", ""),
            "meaning": row.get("default_meaning", "") or "",
            "example_en": row.get("example_en", "") or "",
            "example_zh": row.get("example_zh", "") or "",
        })
    return result


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


def get_student_learned_vocab_summary(student_id: int):
    supabase = get_supabase_client()
    progress_rows = _fetch_all_rows(
        supabase.table("student_vocab_progress")
        .select("vocab_item_id, status, review_count, error_count, memory_score, first_learned_at")
        .eq("student_id", student_id)
        .order("first_learned_at", desc=True)
    )

    progress_vocab_ids = []
    seen_progress_vocab_ids = set()
    for row in progress_rows:
        vocab_item_id = row.get("vocab_item_id")
        if vocab_item_id is None or vocab_item_id in seen_progress_vocab_ids:
            continue
        seen_progress_vocab_ids.add(vocab_item_id)
        progress_vocab_ids.append(vocab_item_id)

    if not progress_vocab_ids:
        return {"total_unique_words": 0, "lesson_groups": []}

    lesson_rows = (
        supabase.table("lessons")
        .select("id, lesson_type, topic, created_at")
        .eq("student_id", student_id)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    ).data or []

    lesson_ids = [row["id"] for row in lesson_rows if row.get("id") is not None]
    lesson_vocab_ids = {}
    linked_vocab_ids = set()

    if lesson_ids:
        link_rows = (
            supabase.table("lesson_vocab_items")
            .select("lesson_id, vocab_item_id, word_type")
            .in_("lesson_id", lesson_ids)
            .execute()
        ).data or []

        progress_vocab_id_set = set(progress_vocab_ids)
        for row in link_rows:
            lesson_id = row.get("lesson_id")
            vocab_item_id = row.get("vocab_item_id")
            if lesson_id is None or vocab_item_id is None:
                continue
            if vocab_item_id not in progress_vocab_id_set:
                continue
            lesson_vocab_ids.setdefault(lesson_id, [])
            if vocab_item_id in lesson_vocab_ids[lesson_id]:
                continue
            lesson_vocab_ids[lesson_id].append(vocab_item_id)
            linked_vocab_ids.add(vocab_item_id)

    vocab_map = {}
    if progress_vocab_ids:
        vocab_rows = (
            supabase.table("vocab_items")
            .select("id, lemma, default_meaning")
            .in_("id", progress_vocab_ids)
            .execute()
        ).data or []
        vocab_map = {
            row["id"]: {
                "lemma": row.get("lemma", ""),
                "meaning": row.get("default_meaning", "") or "",
            }
            for row in vocab_rows
        }

    lesson_groups = []
    for lesson in lesson_rows:
        lesson_id = lesson.get("id")
        vocab_list = []
        for vocab_item_id in lesson_vocab_ids.get(lesson_id, []):
            vocab = vocab_map.get(vocab_item_id)
            if not vocab or not vocab.get("lemma"):
                continue
            vocab_list.append(vocab)

        if not vocab_list:
            continue

        lesson_groups.append({
            "lesson_id": lesson_id,
            "lesson_type": lesson.get("lesson_type", ""),
            "topic": lesson.get("topic", ""),
            "created_at": lesson.get("created_at", ""),
            "word_count": len(vocab_list),
            "words": vocab_list,
        })

    ungrouped_words = []
    for vocab_item_id in progress_vocab_ids:
        if vocab_item_id in linked_vocab_ids:
            continue
        vocab = vocab_map.get(vocab_item_id)
        if not vocab or not vocab.get("lemma"):
            continue
        ungrouped_words.append(vocab)

    if ungrouped_words:
        lesson_groups.append({
            "lesson_id": None,
            "lesson_type": "鏈綊妗ｅ埌瀛︽",
            "topic": "杩欎簺璇嶅凡缁忚鍏ュ涔犺繘搴︼紝浣嗘殏鏃舵病鏈夊叧鑱斿埌鍏蜂綋瀛︽",
            "created_at": "",
            "word_count": len(ungrouped_words),
            "words": ungrouped_words,
        })

    return {
        "total_unique_words": len(progress_vocab_ids),
        "lesson_groups": lesson_groups,
    }


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


def get_student_activity_dates(student_id: int, days: int = 30):
    supabase = get_supabase_client()
    lesson_rows = (
        supabase.table("lessons")
        .select("created_at")
        .eq("student_id", student_id)
        .order("created_at", desc=True)
        .limit(max(days * 3, 30))
        .execute()
    ).data or []

    test_rows = (
        supabase.table("vocab_test_records")
        .select("created_at")
        .eq("student_id", student_id)
        .order("created_at", desc=True)
        .limit(max(days * 3, 30))
        .execute()
    ).data or []

    activity_dates = set()
    for row in lesson_rows + test_rows:
        created_at = row.get("created_at")
        if created_at:
            activity_dates.add(str(created_at)[:10])

    return sorted(activity_dates, reverse=True)[:days]


def get_latest_diagnosis_record(student_id: int):
    supabase = get_admin_supabase_client() or get_supabase_client()
    try:
        resp = (
            supabase.table("student_diagnostic_records")
            .select("*")
            .eq("student_id", student_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception:
        return None
    rows = resp.data or []
    return rows[0] if rows else None


def get_latest_profile_snapshot(student_id: int):
    supabase = get_admin_supabase_client() or get_supabase_client()
    try:
        resp = (
            supabase.table("student_profile_snapshots")
            .select("*")
            .eq("student_id", student_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception:
        return None
    rows = resp.data or []
    return rows[0] if rows else None


def save_initial_diagnosis_result(student_id: int, diagnosis_result: dict):
    supabase = get_admin_supabase_client() or get_supabase_client()

    record_payload = {
        "student_id": student_id,
        "diagnosis_type": "initial_mvp",
        "vocab_band": diagnosis_result.get("vocab_band"),
        "reading_profile": diagnosis_result.get("reading_profile"),
        "grammar_gap": diagnosis_result.get("grammar_gap"),
        "writing_profile": diagnosis_result.get("writing_profile"),
        "suggested_track": diagnosis_result.get("suggested_track"),
        "module_scores": diagnosis_result.get("scores", {}),
        "module_totals": diagnosis_result.get("totals", {}),
    }
    record_resp = supabase.table("student_diagnostic_records").insert(record_payload).execute()
    record_rows = record_resp.data or []
    record = record_rows[0] if record_rows else None
    record_id = record.get("id") if record else None

    snapshot_payload = {
        "student_id": student_id,
        "source_record_id": record_id,
        "source_type": "initial_diagnosis",
        "title_label": diagnosis_result.get("title_label"),
        "stage_label": diagnosis_result.get("stage_label"),
        "growth_focus": diagnosis_result.get("growth_focus"),
        "summary_text": diagnosis_result.get("summary_text"),
        "profile_payload": {
            "dimensions": diagnosis_result.get("dimensions", {}),
            "suggested_track": diagnosis_result.get("suggested_track"),
            "vocab_band": diagnosis_result.get("vocab_band"),
            "reading_profile": diagnosis_result.get("reading_profile"),
            "grammar_gap": diagnosis_result.get("grammar_gap"),
            "writing_profile": diagnosis_result.get("writing_profile"),
            "vocab_diagnostic_result": diagnosis_result.get("vocab_diagnostic_result", {}),
            "module_reports": diagnosis_result.get("module_reports", {}),
            "priority_module": diagnosis_result.get("priority_module"),
            "strongest_module": diagnosis_result.get("strongest_module"),
            "overall_accuracy": diagnosis_result.get("overall_accuracy"),
            "overall_summary": diagnosis_result.get("overall_summary"),
            "next_actions": diagnosis_result.get("next_actions", []),
        },
    }
    snapshot_resp = supabase.table("student_profile_snapshots").insert(snapshot_payload).execute()
    snapshot_rows = snapshot_resp.data or []
    snapshot = snapshot_rows[0] if snapshot_rows else None

    return {
        "record": record,
        "snapshot": snapshot,
    }


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
