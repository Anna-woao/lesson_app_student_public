from __future__ import annotations

from datetime import datetime, timezone

from lesson_html_renderer import parse_lesson_text_to_parts, parse_part1_table
from supabase_client import get_admin_supabase_client, get_supabase_client


UNCERTAIN_OPTION = "\u6211\u4e0d\u77e5\u9053"


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


def _normalize_vocab_text(text: str) -> str:
    value = (text or "").strip().lower()
    value = value.replace("’", "'").replace("‘", "'")
    value = value.replace("“", '"').replace("”", '"')
    return " ".join(value.split())


def _fetch_vocab_rows_by_lemmas(supabase, lemmas):
    normalized_targets = []
    seen = set()
    for lemma in lemmas:
        normalized = _normalize_vocab_text(lemma)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        normalized_targets.append(normalized)

    if not normalized_targets:
        return {}

    vocab_rows = _fetch_all_rows(
        supabase.table("vocab_items").select(
            "id, lemma, pos, ipa_br, ipa_am, default_meaning, example_en, example_zh"
        )
    )
    matched = {}
    for row in vocab_rows:
        normalized = _normalize_vocab_text(row.get("lemma", ""))
        if normalized and normalized in seen and normalized not in matched:
            matched[normalized] = row
    return matched


def _parse_lesson_vocab_sections(lesson: dict):
    parts = parse_lesson_text_to_parts(lesson.get("content", "") or "")
    parsed = {
        "new": parse_part1_table(parts.get("part1", "") or ""),
        "review": parse_part1_table(parts.get("part1_review", "") or ""),
    }

    section_rows = {}
    for word_type, rows in parsed.items():
        items = []
        seen = set()
        for row in rows:
            lemma = (row.get("Word") or "").strip()
            normalized = _normalize_vocab_text(lemma)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            items.append({
                "lemma": lemma,
                "pos": (row.get("POS") or "").strip(),
                "ipa": (row.get("IPA") or "").strip(),
                "meaning": (row.get("Meaning") or "").strip(),
                "word_type": word_type,
                "normalized_lemma": normalized,
            })
        section_rows[word_type] = items
    return section_rows


def _build_lesson_vocab_bundle(lesson: dict, supabase):
    parsed_sections = _parse_lesson_vocab_sections(lesson)
    vocab_lookup = _fetch_vocab_rows_by_lemmas(
        supabase,
        [item.get("lemma", "") for rows in parsed_sections.values() for item in rows],
    )

    bundle_rows = {"new": [], "review": []}
    all_words = []
    for word_type in ("new", "review"):
        for item in parsed_sections.get(word_type, []):
            vocab_row = vocab_lookup.get(item["normalized_lemma"], {})
            display_row = {
                "id": vocab_row.get("id"),
                "lemma": vocab_row.get("lemma") or item.get("lemma", ""),
                "pos": vocab_row.get("pos") or item.get("pos", ""),
                "ipa_br": vocab_row.get("ipa_br") or item.get("ipa", ""),
                "ipa_am": vocab_row.get("ipa_am") or "",
                "meaning": vocab_row.get("default_meaning") or item.get("meaning", ""),
                "example_en": vocab_row.get("example_en") or "",
                "example_zh": vocab_row.get("example_zh") or "",
                "word_type": word_type,
                "normalized_lemma": item["normalized_lemma"],
            }
            bundle_rows[word_type].append(display_row)
            all_words.append(display_row)

    return {
        "lesson_id": lesson.get("id"),
        "lesson_type": lesson.get("lesson_type", "") or "",
        "topic": lesson.get("topic", "") or "",
        "created_at": lesson.get("created_at", "") or "",
        "new_words": bundle_rows["new"],
        "review_words": bundle_rows["review"],
        "all_words": all_words,
    }


def get_lesson_vocab_bundle_for_student(student_id: int, lesson_id: int):
    supabase = get_supabase_client()
    lesson_resp = (
        supabase.table("lessons")
        .select("id, lesson_type, topic, content, created_at")
        .eq("student_id", student_id)
        .eq("id", lesson_id)
        .limit(1)
        .execute()
    )
    rows = lesson_resp.data or []
    if not rows:
        return None
    return _build_lesson_vocab_bundle(rows[0], supabase)


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
    bundle = get_lesson_vocab_bundle_for_student(student_id, lesson_id)
    if not bundle:
        return []
    return bundle.get("new_words", [])

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

    vocab_rows = _fetch_all_rows(
        supabase.table("vocab_items")
        .select("id, lemma, default_meaning")
        .in_("id", progress_vocab_ids)
    )
    learned_by_normalized = {}
    vocab_map = {}
    for row in vocab_rows:
        vocab_item_id = row["id"]
        vocab_map[vocab_item_id] = {
            "id": vocab_item_id,
            "lemma": row.get("lemma", ""),
            "meaning": row.get("default_meaning", "") or "",
        }
        normalized = _normalize_vocab_text(row.get("lemma", ""))
        if normalized and normalized not in learned_by_normalized:
            learned_by_normalized[normalized] = vocab_map[vocab_item_id]

    lesson_rows = _fetch_all_rows(
        supabase.table("lessons")
        .select("id, lesson_type, topic, content, created_at")
        .eq("student_id", student_id)
        .order("created_at", desc=True)
    )

    lesson_groups = []
    linked_vocab_ids = set()
    for lesson in lesson_rows:
        bundle = _build_lesson_vocab_bundle(lesson, supabase)
        vocab_list = []
        seen_vocab_ids = set()
        for word in bundle.get("all_words", []):
            vocab = learned_by_normalized.get(word.get("normalized_lemma", ""))
            if not vocab:
                continue
            vocab_item_id = vocab.get("id")
            if vocab_item_id in seen_vocab_ids:
                continue
            seen_vocab_ids.add(vocab_item_id)
            linked_vocab_ids.add(vocab_item_id)
            vocab_list.append({
                "lemma": vocab.get("lemma", ""),
                "meaning": vocab.get("meaning", "") or "",
            })

        if not vocab_list:
            continue

        lesson_groups.append({
            "lesson_id": bundle.get("lesson_id"),
            "lesson_type": bundle.get("lesson_type", ""),
            "topic": bundle.get("topic", ""),
            "created_at": bundle.get("created_at", ""),
            "word_count": len(vocab_list),
            "words": vocab_list,
            "new_word_count": len(bundle.get("new_words", [])),
            "review_word_count": len(bundle.get("review_words", [])),
        })

    ungrouped_words = []
    for vocab_item_id in progress_vocab_ids:
        if vocab_item_id in linked_vocab_ids:
            continue
        vocab = vocab_map.get(vocab_item_id)
        if not vocab or not vocab.get("lemma"):
            continue
        ungrouped_words.append({
            "lemma": vocab.get("lemma", ""),
            "meaning": vocab.get("meaning", "") or "",
        })

    if ungrouped_words:
        lesson_groups.append({
            "lesson_id": None,
            "lesson_type": "未关联学案",
            "topic": "这些词已经进入学习记录，但暂时还没能匹配到具体学案。",
            "created_at": "",
            "word_count": len(ungrouped_words),
            "words": ungrouped_words,
            "new_word_count": 0,
            "review_word_count": 0,
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


def get_latest_diagnostic_vocab_result(student_id: int):
    supabase = get_admin_supabase_client() or get_supabase_client()
    try:
        resp = (
            supabase.table("diagnostic_vocab_results")
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


def get_diagnostic_vocab_answers(diagnostic_id: int):
    supabase = get_admin_supabase_client() or get_supabase_client()
    try:
        resp = (
            supabase.table("diagnostic_vocab_answers")
            .select("*")
            .eq("diagnostic_id", diagnostic_id)
            .order("id", desc=False)
            .execute()
        )
    except Exception:
        return []
    return resp.data or []


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_missing_table_error(exc: Exception, table_name: str) -> bool:
    text = str(exc)
    return "PGRST205" in text and table_name in text


def _build_diagnostic_vocab_result_payload(student_id: int, diagnostic_id: int, diagnosis_result: dict, diagnostic_meta: dict | None = None):
    vocab_result = diagnosis_result.get("vocab_diagnostic_result") or {}
    diagnostic_meta = diagnostic_meta or {}
    return {
        "diagnostic_id": diagnostic_id,
        "student_id": student_id,
        "total_scored_items": vocab_result.get("total_scored_items", 0),
        "correct_count": vocab_result.get("correct_count", 0),
        "overall_accuracy": vocab_result.get("overall_accuracy", 0.0),
        "l1_accuracy": vocab_result.get("l1_accuracy", 0.0),
        "l2_accuracy": vocab_result.get("l2_accuracy", 0.0),
        "l3_accuracy": vocab_result.get("l3_accuracy", 0.0),
        "l4_accuracy": vocab_result.get("l4_accuracy", 0.0),
        "l5_accuracy": vocab_result.get("l5_accuracy", 0.0),
        "high_frequency_accuracy": vocab_result.get("high_frequency_accuracy", 0.0),
        "reading_vocab_accuracy": vocab_result.get("reading_vocab_accuracy", 0.0),
        "polysemy_accuracy": vocab_result.get("polysemy_accuracy", 0.0),
        "confusable_accuracy": vocab_result.get("confusable_accuracy", 0.0),
        "uncertain_rate": vocab_result.get("uncertain_rate", 0.0),
        "estimated_vocab_range": vocab_result.get("estimated_vocab_range", ""),
        "vocab_level_label": vocab_result.get("vocab_level_label", ""),
        "main_vocab_problem": vocab_result.get("main_vocab_problem", ""),
        "recommended_training_start": vocab_result.get("recommended_training_start", ""),
        "self_check_json": {
            "strengths": vocab_result.get("strengths", []),
            "risk_flags": vocab_result.get("risk_flags", []),
            "recommended_actions": vocab_result.get("recommended_actions", []),
            "level_accuracy_map": vocab_result.get("level_accuracy_map", {}),
            "question_type_accuracy_map": vocab_result.get("question_type_accuracy_map", {}),
            "level_correct_counts": vocab_result.get("level_correct_counts", {}),
            "level_total_counts": vocab_result.get("level_total_counts", {}),
            "question_type_correct_counts": vocab_result.get("question_type_correct_counts", {}),
            "question_type_total_counts": vocab_result.get("question_type_total_counts", {}),
            "question_timing_supported": False,
            "timing_note": "Current first-diagnosis UI is module-level. Per-question timing is reserved but not yet captured.",
            "diagnostic_meta": diagnostic_meta,
        },
        "updated_at": _now_iso(),
    }


def _build_diagnostic_vocab_answer_rows(
    *,
    student_id: int,
    diagnostic_id: int,
    definition: list[dict],
    module_answers: dict,
):
    vocab_module = next((module for module in definition if module.get("key") == "vocab"), None)
    if not vocab_module:
        return []

    answers = module_answers.get("vocab", {}) or {}
    rows = []
    for question in vocab_module.get("questions", []):
        selected_answer = answers.get(question["id"])
        if not selected_answer:
            continue
        correct_answer = question.get("answer")
        rows.append(
            {
                "diagnostic_id": diagnostic_id,
                "student_id": student_id,
                "item_id": question.get("id"),
                "selected_answer": selected_answer,
                "is_correct": selected_answer == correct_answer,
                "is_uncertain": selected_answer == UNCERTAIN_OPTION,
                # The current UI submits the whole vocab module in one form, so
                # per-question timing is intentionally left null instead of faking precision.
                "time_spent_seconds": None,
                "question_type": question.get("question_type"),
                "level": question.get("level"),
                "diagnostic_tag": question.get("diagnostic_tag"),
            }
        )
    return rows


def save_initial_diagnosis_result(
    student_id: int,
    diagnosis_result: dict,
    *,
    module_answers: dict | None = None,
    definition: list[dict] | None = None,
    diagnostic_meta: dict | None = None,
):
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

    vocab_result_record = None
    vocab_answer_rows = []
    if record_id and diagnosis_result.get("vocab_diagnostic_result"):
        vocab_result_payload = _build_diagnostic_vocab_result_payload(
            student_id,
            record_id,
            diagnosis_result,
            diagnostic_meta=diagnostic_meta,
        )
        try:
            vocab_result_resp = (
                supabase.table("diagnostic_vocab_results")
                .upsert(vocab_result_payload, on_conflict="diagnostic_id")
                .execute()
            )
        except Exception as exc:
            if _is_missing_table_error(exc, "diagnostic_vocab_results"):
                raise RuntimeError(
                    "Supabase 缺少 diagnostic_vocab_results 表。请先执行 "
                    "D:/lesson_app_student_public/supabase_initial_diagnosis_migration.sql 中新增的词汇诊断结果迁移 SQL。"
                ) from exc
            raise
        vocab_result_rows = vocab_result_resp.data or []
        vocab_result_record = vocab_result_rows[0] if vocab_result_rows else None

        if definition is not None and module_answers is not None:
            vocab_answer_rows = _build_diagnostic_vocab_answer_rows(
                student_id=student_id,
                diagnostic_id=record_id,
                definition=definition,
                module_answers=module_answers,
            )
            if vocab_answer_rows:
                try:
                    (
                        supabase.table("diagnostic_vocab_answers")
                        .delete()
                        .eq("diagnostic_id", record_id)
                        .execute()
                    )
                    supabase.table("diagnostic_vocab_answers").insert(vocab_answer_rows).execute()
                except Exception as exc:
                    if _is_missing_table_error(exc, "diagnostic_vocab_answers"):
                        raise RuntimeError(
                            "Supabase 缺少 diagnostic_vocab_answers 表。请先执行 "
                            "D:/lesson_app_student_public/supabase_initial_diagnosis_migration.sql 中新增的词汇答题记录迁移 SQL。"
                        ) from exc
                    raise

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
            "vocab_profile_summary": diagnosis_result.get("vocab_profile_summary", ""),
            "vocab_diagnostic_result": diagnosis_result.get("vocab_diagnostic_result", {}),
            "module_reports": diagnosis_result.get("module_reports", {}),
            "priority_module": diagnosis_result.get("priority_module"),
            "strongest_module": diagnosis_result.get("strongest_module"),
            "overall_accuracy": diagnosis_result.get("overall_accuracy"),
            "overall_summary": diagnosis_result.get("overall_summary"),
            "next_actions": diagnosis_result.get("next_actions", []),
            "diagnostic_meta": diagnostic_meta or {},
        },
    }
    snapshot_resp = supabase.table("student_profile_snapshots").insert(snapshot_payload).execute()
    snapshot_rows = snapshot_resp.data or []
    snapshot = snapshot_rows[0] if snapshot_rows else None

    return {
        "record": record,
        "vocab_result": vocab_result_record,
        "vocab_answers_saved_count": len(vocab_answer_rows),
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
