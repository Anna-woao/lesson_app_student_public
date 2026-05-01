"""学生端 Supabase 数据层（含词汇检测作答）"""

from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import hmac
import random
import re
import secrets
import unicodedata
from typing import Dict, List, Optional, Tuple

import streamlit as st

from supabase_client import get_admin_supabase_client, get_supabase_client
from student_records_data import (
    clear_student_records_cache,
    get_diagnostic_vocab_answers,
    get_latest_diagnostic_vocab_result,
    get_latest_diagnosis_record,
    get_latest_profile_snapshot,
    get_lesson_detail_for_student,
    get_lesson_vocab_bundle_for_student,
    get_lesson_new_vocab_for_student,
    get_student_lesson_snapshot,
    get_student_recent_lesson_snapshots,
    get_student_activity_dates,
    get_student_learned_vocab,
    get_student_learned_vocab_summary,
    get_student_recent_lessons,
    get_student_vocab_test_records,
    get_vocab_test_record_items,
    save_initial_diagnosis_result,
)


PASSWORD_HASH_ITERATIONS = 200_000
VOCAB_IMPORT_CHUNK_SIZE = 200



def _make_password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}${salt}${digest}"


def _check_password_hash(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected_digest = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
    except Exception:
        return False
    return hmac.compare_digest(digest, expected_digest)


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


def _get_admin_supabase_client_required():
    client = get_admin_supabase_client()
    if client is None:
        raise RuntimeError("缺少 SUPABASE_SERVICE_ROLE_KEY，无法执行管理员写操作。")
    return client


def _normalize_lemma(text: str) -> str:
    value = (text or "").strip().lower()
    value = value.replace("’", "'").replace("‘", "'")
    value = re.sub(r"\s+", " ", value)
    return value


def get_all_students():
    supabase = get_supabase_client()
    resp = supabase.table("students").select("id, name, grade").order("id", desc=False).execute()
    rows = resp.data or []
    return [(row["id"], row["name"], row["grade"]) for row in rows]


def get_student_basic_info(student_id: int):
    supabase = get_supabase_client()
    resp = (
        supabase.table("students")
        .select("id, name, grade")
        .eq("id", student_id)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    return rows[0] if rows else None


def authenticate_student(login_account: str, login_password: str):
    account = (login_account or "").strip()
    password = (login_password or "").strip()
    if not account or not password:
        return None

    supabase = get_supabase_client()
    resp = (
        supabase.table("students")
        .select("id, name, grade, login_account, login_password, login_password_hash")
        .eq("login_account", account)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        return None

    row = rows[0]
    password_hash = row.get("login_password_hash") or ""
    legacy_password = row.get("login_password") or ""

    if password_hash:
        if not _check_password_hash(password, password_hash):
            return None
    elif legacy_password:
        if not hmac.compare_digest(password, legacy_password):
            return None
        supabase.table("students").update({
            "login_password_hash": _make_password_hash(password),
            "login_password": None,
        }).eq("id", row["id"]).execute()
    else:
        return None

    return {
        "id": row["id"],
        "name": row.get("name", ""),
        "grade": row.get("grade", ""),
        "login_account": row.get("login_account", ""),
    }


def get_student_login_accounts():
    supabase = _get_admin_supabase_client_required()
    resp = (
        supabase.table("students")
        .select("id, name, grade, login_account, login_password, login_password_hash")
        .order("id", desc=False)
        .execute()
    )
    rows = resp.data or []
    return [
        (
            row["id"],
            row.get("name", ""),
            row.get("grade", ""),
            row.get("login_account", "") or "",
            bool(row.get("login_password_hash") or row.get("login_password")),
        )
        for row in rows
    ]


def update_student_login_account(student_id: int, login_account: str, login_password: str):
    account = (login_account or "").strip()
    password = (login_password or "").strip()
    if not account:
        return False, "账号不能为空。"

    supabase = _get_admin_supabase_client_required()
    duplicate_resp = (
        supabase.table("students")
        .select("id")
        .eq("login_account", account)
        .neq("id", student_id)
        .limit(1)
        .execute()
    )
    if duplicate_resp.data:
        return False, "这个账号已经被其他学生使用。"

    update_payload = {
        "login_account": account,
    }
    if password:
        update_payload["login_password_hash"] = _make_password_hash(password)
        update_payload["login_password"] = None

    supabase.table("students").update(update_payload).eq("id", student_id).execute()
    if password:
        return True, "学生账号已保存，密码已重置。"
    return True, "学生账号已保存，密码未更改。"


def parse_structured_vocab_excel(file_bytes: bytes, source_name: str = ""):
    import vocab_import_service as vis

    return vis.parse_generic_vocab_excel(
        file_bytes,
        {
            "A": "ignore",
            "B": "book_name",
            "C": "volume_name",
            "D": "unit",
            "E": "term",
            "F": "meaning",
            "G": "ipa",
            "H": "note",
        },
        source_name=source_name,
    )


def import_structured_vocab_excel(file_bytes: bytes, source_name: str = ""):
    import vocab_import_service as vis

    parsed = parse_structured_vocab_excel(file_bytes, source_name=source_name)
    return vis.import_parsed_vocab_rows(parsed, source_name=source_name)


@st.cache_data(ttl=20, show_spinner=False)
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
        .select("vocab_item_id, status")
        .eq("student_id", student_id)
        .execute()
    ).data or []
    progress_vocab_ids = [row.get("vocab_item_id") for row in progress_rows if row.get("vocab_item_id") is not None]
    progress_vocab_map = _fetch_vocab_detail_map(progress_vocab_ids)
    progress_by_key = {}
    for row in progress_rows:
        vocab_item_id = row.get("vocab_item_id")
        progress_key = _progress_key_for_vocab(vocab_item_id, progress_vocab_map)
        if progress_key is None:
            continue
        progress_by_key[progress_key] = _merge_progress_status(
            progress_by_key.get(progress_key),
            row.get("status", "learning"),
        )

    buv_rows = _fetch_all_rows(
        supabase.table("book_unit_vocab").select("book_id, vocab_item_id")
    )
    book_vocab_ids = [row.get("vocab_item_id") for row in buv_rows if row.get("vocab_item_id") is not None]
    book_vocab_map_rows = _fetch_vocab_detail_map(book_vocab_ids)
    book_vocab_map = {}
    for row in buv_rows:
        book_id = row.get("book_id")
        vocab_item_id = row.get("vocab_item_id")
        if book_id is None or vocab_item_id is None:
            continue
        progress_key = _progress_key_for_vocab(vocab_item_id, book_vocab_map_rows)
        if progress_key is None:
            continue
        book_vocab_map.setdefault(book_id, set()).add(progress_key)

    result = []
    for book in books:
        book_id = book["id"]
        book_vocab_keys = book_vocab_map.get(book_id, set())
        learned_keys = {progress_key for progress_key in book_vocab_keys if progress_key in progress_by_key}
        mastered_count = sum(1 for progress_key in learned_keys if progress_by_key.get(progress_key) == "mastered")
        learning_count = sum(1 for progress_key in learned_keys if progress_by_key.get(progress_key) == "learning")
        review_count = sum(1 for progress_key in learned_keys if progress_by_key.get(progress_key) == "review")

        result.append((
            book_id,
            book.get("book_name"),
            book.get("volume_name"),
            len(learned_keys),
            len(book_vocab_keys),
            mastered_count,
            learning_count,
            review_count,
        ))
    return result


@st.cache_data(ttl=20, show_spinner=False)
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
    book_vocab_ids = [row.get("vocab_item_id") for row in buv_rows if row.get("vocab_item_id") is not None]
    book_vocab_map_rows = _fetch_vocab_detail_map(book_vocab_ids)

    progress_rows = (
        supabase.table("student_vocab_progress")
        .select("vocab_item_id")
        .eq("student_id", student_id)
        .execute()
    ).data or []
    progress_vocab_ids = [row.get("vocab_item_id") for row in progress_rows if row.get("vocab_item_id") is not None]
    progress_vocab_map = _fetch_vocab_detail_map(progress_vocab_ids)
    learned_vocab_keys = {
        _progress_key_for_vocab(row.get("vocab_item_id"), progress_vocab_map)
        for row in progress_rows
        if row.get("vocab_item_id") is not None
    }
    learned_vocab_keys.discard(None)

    result = []
    for unit in units:
        unit_id = unit["id"]
        total_vocab_keys = {
            _progress_key_for_vocab(row.get("vocab_item_id"), book_vocab_map_rows)
            for row in buv_rows
            if row.get("unit_id") == unit_id and row.get("vocab_item_id") is not None
        }
        total_vocab_keys.discard(None)
        learned_in_unit = {
            progress_key
            for progress_key in total_vocab_keys
            if progress_key in learned_vocab_keys
        }
        result.append((
            unit_id,
            unit.get("unit_name"),
            unit.get("unit_order", 0),
            len(learned_in_unit),
            len(total_vocab_keys),
        ))
    return result



@st.cache_data(ttl=60, show_spinner=False)
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


@st.cache_data(ttl=60, show_spinner=False)
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


def clear_student_progress_cache() -> None:
    get_student_book_progress.clear()
    get_student_unit_progress.clear()
    get_all_word_books.clear()
    get_units_by_book.clear()


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


_POS_ALIASES = {
    "a.": "adj.",
    "adj.": "adj.",
    "ad.": "adv.",
    "adv.": "adv.",
    "n.": "n.",
    "v.": "v.",
    "vi.": "vi.",
    "vt.": "vt.",
    "prep.": "prep.",
    "conj.": "conj.",
    "pron.": "pron.",
    "num.": "num.",
    "art.": "art.",
    "det.": "det.",
    "aux.": "aux.",
    "int.": "int.",
    "phr.": "phr.",
    "abbr.": "abbr.",
}
_POS_TOKEN_PATTERN = "|".join(re.escape(token) for token in sorted(_POS_ALIASES, key=len, reverse=True))
_POS_PREFIX_TOKEN_PATTERN_TEXT = (
    r"linking\.?|modal\.?|prep\.?|conj\.?|pron\.?|abbr\.?|"
    r"num\.?|art\.?|det\.?|aux\.?|adj\.?|adv\.?|phr\.?|"
    r"int\.?|vi\.?|vt\.?|ad\.?|n\.?|v\.?|a\.?"
)
_POS_PREFIX_PATTERN = re.compile(
    rf"^\s*&?\s*({_POS_PREFIX_TOKEN_PATTERN_TEXT})(?=\s|&|[\u4e00-\u9fff]|$)",
    re.IGNORECASE,
)
_POS_ANY_PATTERN = re.compile(rf"&?\s*({_POS_TOKEN_PATTERN})", re.IGNORECASE)
_POS_SEPARATORS = " \t\r\n.&/\\-:,;，,；;、:："
_SPACED_POS_FIXES = (
    (re.compile(r"con\s+j\.", re.IGNORECASE), "conj."),
    (re.compile(r"ad\s+v\.", re.IGNORECASE), "adv."),
    (re.compile(r"ad\s+j\.", re.IGNORECASE), "adj."),
)


def _student_display_meaning(raw_meaning: str) -> str:
    text = str(raw_meaning or "").strip()
    if not text:
        return ""
    for pattern, replacement in _SPACED_POS_FIXES:
        text = pattern.sub(replacement, text)
    while text:
        match = _POS_PREFIX_PATTERN.match(text)
        if not match:
            break
        text = text[match.end():].lstrip(_POS_SEPARATORS)

    # A few imported meanings contain later POS labels glued to Chinese senses
    # ("...因为prep.作为"). Strip labels from display/distractor text.
    text = _POS_ANY_PATTERN.sub("；", text)
    text = text.replace("&", "；")
    text = re.sub(r"[；;]\s*[；;]+", "；", text)
    text = re.sub(r"\s+", " ", text).strip(_POS_SEPARATORS)
    return text or str(raw_meaning or "").strip()


def _fetch_vocab_detail_map(vocab_ids: List[int]) -> Dict[int, dict]:
    supabase = get_supabase_client()
    if not vocab_ids:
        return {}

    rows = []
    deduped_ids = list(dict.fromkeys(vocab_ids))
    batch_size = 500
    for start in range(0, len(deduped_ids), batch_size):
        batch_ids = deduped_ids[start:start + batch_size]
        try:
            batch_rows = (
                supabase.table("vocab_items")
                .select("id, lemma, normalized_lemma, default_meaning")
                .in_("id", batch_ids)
                .execute()
            ).data or []
        except Exception as exc:
            error_text = str(exc)
            if "normalized_lemma" not in error_text and "PGRST204" not in error_text:
                raise
            batch_rows = (
                supabase.table("vocab_items")
                .select("id, lemma, default_meaning")
                .in_("id", batch_ids)
                .execute()
            ).data or []
        rows.extend(batch_rows)

    for row in rows:
        row["normalized_lemma"] = _normalize_lemma(row.get("normalized_lemma") or row.get("lemma") or "")
    return {r["id"]: r for r in rows}


def _progress_key_for_vocab(vocab_item_id: Optional[int], vocab_rows_map: Dict[int, dict]) -> Optional[str]:
    if vocab_item_id is None:
        return None
    vocab_row = vocab_rows_map.get(vocab_item_id, {})
    normalized = (vocab_row.get("normalized_lemma") or "").strip()
    return normalized or f"id:{vocab_item_id}"


def _merge_progress_status(current_status: Optional[str], new_status: Optional[str]) -> str:
    order = {"learning": 1, "review": 2, "mastered": 3}
    current = current_status or "learning"
    incoming = new_status or "learning"
    return incoming if order.get(incoming, 0) >= order.get(current, 0) else current


def _calculate_next_review_days(memory_score: float, review_count: int) -> int:
    if memory_score < 2.5:
        intervals = [1, 2, 4, 7, 14]
    elif memory_score > 4.0:
        intervals = [1, 4, 10, 20, 30]
    else:
        intervals = [1, 3, 7, 14, 30]

    if review_count >= len(intervals):
        return 999
    return intervals[review_count]


def _get_student_progress_rows_map(student_id: int) -> Dict[int, dict]:
    supabase = get_admin_supabase_client() or get_supabase_client()
    rows = (
        supabase.table("student_vocab_progress")
        .select(
            "id, vocab_item_id, first_source_book_id, first_source_unit_id, status, "
            "review_count, error_count, memory_score, first_learned_at, last_review_time, next_review_time"
        )
        .eq("student_id", student_id)
        .execute()
    ).data or []
    return {
        row["vocab_item_id"]: row
        for row in rows
        if row.get("vocab_item_id") is not None
    }


def _upsert_student_vocab_progress(
    student_id: int,
    vocab_item_id: int,
    source_book_id: Optional[int],
    source_unit_id: Optional[int],
    status: str,
    review_count: int,
    error_count: int,
    memory_score: float,
    next_review_time: Optional[str],
):
    supabase = get_admin_supabase_client() or get_supabase_client()
    existing_rows = (
        supabase.table("student_vocab_progress")
        .select("id, first_learned_at")
        .eq("student_id", student_id)
        .eq("vocab_item_id", vocab_item_id)
        .limit(1)
        .execute()
    ).data or []

    now_iso = datetime.utcnow().isoformat()
    if existing_rows:
        update_payload = {
            "status": status,
            "review_count": review_count,
            "error_count": error_count,
            "memory_score": round(memory_score, 2),
            "last_review_time": now_iso,
            "next_review_time": next_review_time,
        }
        if source_book_id:
            update_payload["first_source_book_id"] = source_book_id
        if source_unit_id:
            update_payload["first_source_unit_id"] = source_unit_id
        (
            supabase.table("student_vocab_progress")
            .update(update_payload)
            .eq("id", existing_rows[0]["id"])
            .execute()
        )
        return

    insert_payload = {
        "student_id": student_id,
        "vocab_item_id": vocab_item_id,
        "first_source_book_id": source_book_id,
        "first_source_unit_id": source_unit_id,
        "status": status,
        "review_count": review_count,
        "error_count": error_count,
        "memory_score": round(memory_score, 2),
        "first_learned_at": now_iso,
        "last_review_time": now_iso,
        "next_review_time": next_review_time,
    }
    supabase.table("student_vocab_progress").insert(insert_payload).execute()


def _sync_test_results_to_progress(student_id: int, payload: dict, results: List[dict]) -> bool:
    progress_rows_map = _get_student_progress_rows_map(student_id)
    now = datetime.utcnow()

    for item in results:
        vocab_item_id = item.get("vocab_item_id")
        if vocab_item_id is None:
            continue

        current_row = progress_rows_map.get(vocab_item_id) or {}
        current_status = current_row.get("status", "learning")
        current_review_count = int(current_row.get("review_count") or 0)
        current_error_count = int(current_row.get("error_count") or 0)
        current_memory_score = float(current_row.get("memory_score") or 3.0)

        source_book_id = item.get("source_book_id") or payload.get("source_book_id") or current_row.get("first_source_book_id")
        source_unit_id = item.get("source_unit_id") or payload.get("source_unit_id") or current_row.get("first_source_unit_id")
        is_correct = bool(item.get("is_correct"))

        if payload.get("source_type") == "book":
            if is_correct:
                status = "mastered"
                review_count = max(current_review_count, 3)
                error_count = current_error_count
                memory_score = max(current_memory_score, 4.5)
                next_review_time = None
            else:
                status = "learning"
                review_count = 0
                error_count = current_error_count + 1
                memory_score = max(1.0, current_memory_score - 0.3)
                next_review_time = (now + timedelta(days=1)).isoformat()
        else:
            if is_correct:
                memory_score = min(5.0, current_memory_score + 0.1)
                if payload.get("test_type") == "新词检测":
                    status = "mastered"
                    review_count = max(current_review_count, 3)
                    next_review_time = None
                else:
                    review_count = current_review_count + 1
                    next_days = _calculate_next_review_days(memory_score, review_count)
                    if review_count >= 3:
                        status = "mastered"
                        next_review_time = None
                    else:
                        status = "review"
                        next_review_time = (now + timedelta(days=next_days)).isoformat()
                error_count = current_error_count
            else:
                status = "learning"
                review_count = 0
                error_count = current_error_count + 1
                memory_score = max(1.0, current_memory_score - 0.5)
                next_review_time = (now + timedelta(days=1)).isoformat()

        _upsert_student_vocab_progress(
            student_id=student_id,
            vocab_item_id=vocab_item_id,
            source_book_id=source_book_id,
            source_unit_id=source_unit_id,
            status=status,
            review_count=review_count,
            error_count=error_count,
            memory_score=memory_score,
            next_review_time=next_review_time,
        )

    return True


def build_progress_test(student_id: int, test_type: str, test_mode: str, test_count: int):
    supabase = get_supabase_client()
    if test_type == "\u65b0\u8bcd\u68c0\u6d4b":
        rows = (
            supabase.table("student_vocab_progress")
            .select("vocab_item_id, first_source_book_id, first_source_unit_id, status")
            .eq("student_id", student_id)
            .eq("status", "learning")
            .limit(500)
            .execute()
        ).data or []
    else:
        rows = (
            supabase.table("student_vocab_progress")
            .select("vocab_item_id, first_source_book_id, first_source_unit_id, status, last_review_time")
            .eq("student_id", student_id)
            .order("last_review_time", desc=False)
            .limit(1000)
            .execute()
        ).data or []
    if not rows:
        return False, "\u5f53\u524d\u6ca1\u6709\u53ef\u7528\u7684\u5b66\u4e60\u8fdb\u5ea6\u68c0\u6d4b\u8bcd\u3002"
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

def build_book_test(
    student_id: int,
    book_id: int,
    unit_ids: Optional[List[int]],
    test_mode: str,
    test_count: int,
):
    """
    从词汇书中抽题，支持“整本书”或“多个单元联合检测”。

    参数说明：
    - student_id:
        当前学生 ID（这版先保留，后面如果要做更复杂的个性化抽词还可以继续用）
    - book_id:
        当前选择的词汇书 ID
    - unit_ids:
        None 或 []   -> 表示整本词汇书
        [1, 2, 3]    -> 表示多个单元联合检测
    - test_mode:
        英译中 / 中译英 / 混合模式
    - test_count:
        本轮检测题数
    """
    supabase = get_supabase_client()

    query = supabase.table("book_unit_vocab").select("vocab_item_id, book_id, unit_id")
    query = query.eq("book_id", book_id)

    # ------------------------------
    # 如果传了多个单元，就只从这些单元里抽
    # 如果为空，就默认整本词汇书
    # ------------------------------
    if unit_ids:
        query = query.in_("unit_id", unit_ids)

    rows = _fetch_all_rows(query)
    if not rows:
        return False, "当前范围内没有可用单词。"

    # ------------------------------
    # 去重：
    # 1. 避免同一个词因为出现在多个单元里被重复抽到
    # 2. 这样联合多单元检测时更稳定
    # ------------------------------
    deduped_rows = []
    seen_vocab_ids = set()

    for row in rows:
        vocab_item_id = row.get("vocab_item_id")
        if vocab_item_id is None:
            continue
        if vocab_item_id in seen_vocab_ids:
            continue

        seen_vocab_ids.add(vocab_item_id)
        deduped_rows.append(row)

    random.shuffle(deduped_rows)
    deduped_rows = deduped_rows[:test_count]

    vocab_map = _fetch_vocab_map(
        [row["vocab_item_id"] for row in deduped_rows if row.get("vocab_item_id") is not None]
    )
    questions = _build_questions_from_vocab_map(vocab_map, deduped_rows, test_mode)

    payload = {
        "source_type": "book",
        "source_book_id": book_id,
        # 数据表里目前只有一个 source_unit_id 字段
        # 所以：
        # - 只选了一个单元：正常写这个 unit_id
        # - 选了多个单元 / 整本书：这里先记 None
        "source_unit_id": unit_ids[0] if unit_ids and len(unit_ids) == 1 else None,
        "selected_unit_ids": unit_ids or [],
        "test_type": "词汇书抽词检测",
        "test_mode": test_mode,
        "questions": questions,
    }
    return True, payload


def _build_questions_from_vocab_map(vocab_map, rows, test_mode: str):
    all_meanings = []
    for _, raw_meaning in vocab_map.values():
        display_meaning = _student_display_meaning(raw_meaning)
        if display_meaning and display_meaning not in all_meanings:
            all_meanings.append(display_meaning)
    questions = []

    for row in rows:
        vocab_item_id = row.get("vocab_item_id")
        word, raw_meaning = vocab_map.get(vocab_item_id, ("", ""))
        if not word:
            continue
        meaning = _student_display_meaning(raw_meaning)
        if not meaning:
            continue

        one_mode = random.choice(["英译中", "中译英"]) if test_mode == "混合模式" else test_mode

        q = {
            "vocab_item_id": vocab_item_id,
            "word": word,
            "meaning": meaning,
            "raw_meaning": raw_meaning,
            "mode": one_mode,
            "source_book_id": row.get("book_id") or row.get("first_source_book_id"),
            "source_unit_id": row.get("unit_id") or row.get("first_source_unit_id"),
        }

        if one_mode == "英译中":
            distractors = [m for m in all_meanings if m and m != meaning]
            random.shuffle(distractors)
            options = [meaning] + distractors[:3]
            options = list(dict.fromkeys(options))
            random.shuffle(options)
            options.append("我不确定")
            q["options"] = options

        questions.append(q)

    return questions


def _normalize_test_mode(mode: str) -> str:
    normalized = str(mode or "").strip()
    if normalized == "英译中":
        return "英译中"
    if normalized == "中译英":
        return "中译英"
    return normalized


def _normalize_vocab_answer_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(text or ""))
    normalized = normalized.strip().casefold()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = normalized.strip(".,;:!?\"'()[]{}<>`~，。；：！？“”‘’（）【】《》、")
    return normalized


def _grade_vocab_test_answer(question: dict, user_answer: str) -> tuple[bool, bool]:
    mode = _normalize_test_mode(question.get("mode"))
    raw_answer = str(user_answer or "").strip()
    normalized_answer = _normalize_vocab_answer_text(raw_answer)
    is_uncertain = normalized_answer == _normalize_vocab_answer_text("我不确定")

    if mode == "英译中":
        expected_answer = _normalize_vocab_answer_text(question.get("meaning") or "")
        is_correct = (not is_uncertain) and normalized_answer == expected_answer
        return is_correct, is_uncertain

    expected_word = _normalize_vocab_answer_text(question.get("word") or "")
    is_correct = normalized_answer == expected_word
    return is_correct, is_uncertain


def submit_student_test(student_id: int, payload: dict, user_answers: dict, source_label: str):
    results = []
    score = 0
    total = len(payload["questions"])

    for q in payload["questions"]:
        vocab_item_id = q["vocab_item_id"]
        mode = _normalize_test_mode(q.get("mode"))
        user_answer = str(user_answers.get(vocab_item_id, "") or "").strip()
        is_correct, is_uncertain = _grade_vocab_test_answer(q, user_answer)

        if is_correct:
            score += 1

        results.append({
            "vocab_item_id": q["vocab_item_id"],
            "word": q["word"],
            "meaning": q["meaning"],
            "mode": mode,
            "user_answer": user_answer,
            "is_uncertain": is_uncertain,
            "is_correct": is_correct,
            "source_book_id": q.get("source_book_id"),
            "source_unit_id": q.get("source_unit_id"),
        })

    accuracy = (score / total) if total else 0.0

    test_record_id = None
    persistence_error = None
    sync_error = None
    try:
        supabase = get_admin_supabase_client() or get_supabase_client()
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

        try:
            _sync_test_results_to_progress(student_id, payload, results)
            if test_record_id:
                (
                    supabase.table("vocab_test_records")
                    .update({"is_synced_to_progress": True})
                    .eq("id", test_record_id)
                    .execute()
                )
        except Exception as exc:
            sync_error = str(exc)
    except Exception as exc:
        persistence_error = str(exc)

    if persistence_error is None or sync_error is None:
        clear_student_progress_cache()
        clear_student_records_cache()
        try:
            from student_home_viewmodel import clear_student_home_viewmodel_cache

            clear_student_home_viewmodel_cache()
        except Exception:
            pass

    return {
        "score": score,
        "total": total,
        "accuracy": accuracy,
        "uncertain_count": sum(1 for item in results if item.get("is_uncertain")),
        "results": results,
        "test_record_id": test_record_id,
        "persistence_ok": persistence_error is None,
        "persistence_error": persistence_error,
        "sync_ok": sync_error is None,
        "sync_error": sync_error,
    }



def _fetch_diagnostic_vocab_rows(active_versions=None, *, active_only: bool | None = True):
    from diagnostic_vocab_service import ACTIVE_DIAGNOSTIC_VERSIONS

    versions = tuple(active_versions or ACTIVE_DIAGNOSTIC_VERSIONS)
    # Student-side first diagnosis should not depend on the service role key.
    # The diagnostic bank is treated as read-only public app data for this flow.
    supabase = get_supabase_client()
    query = (
        supabase.table("diagnostic_vocab_items")
        .select(
            "item_id, module, level, word, primary_meaning_zh, part_of_speech, "
            "category, sub_skill, question_type, question_text, correct_answer, "
            "wrong_option_1, wrong_option_2, wrong_option_3, explanation, "
            "diagnostic_tag, diagnostic_value, difficulty_level, grade_level, "
            "frequency_band, source_type, source_note, source_url_primary, "
            "source_url_method, is_anchor, is_active, version, sentence, "
            "notes_for_codex, created_at, updated_at"
        )
        .in_("version", list(versions))
    )
    if active_only is True:
        query = query.eq("is_active", True)
    elif active_only is False:
        query = query.eq("is_active", False)
    response = query.execute()
    return response.data or []


def get_diagnostic_vocab_bank_status(*, active_versions=None):
    from diagnostic_vocab_service import ACTIVE_DIAGNOSTIC_VERSIONS, summarize_diagnostic_vocab_rows

    versions = tuple(active_versions or ACTIVE_DIAGNOSTIC_VERSIONS)
    rows = _fetch_diagnostic_vocab_rows(active_versions=versions, active_only=None)
    summary = summarize_diagnostic_vocab_rows(rows)
    summary["total_count"] = summary.get("total_rows", len(rows))
    summary["active_count"] = sum(1 for row in rows if bool(row.get("is_active")))
    summary["ready_for_diagnosis"] = summary["total_count"] > 0
    return summary


def get_diagnostic_vocab_items_for_test(*, active_versions=None, random_seed: int | None = None):
    from diagnostic_vocab_service import (
        ACTIVE_DIAGNOSTIC_VERSIONS,
        build_diagnostic_question_payload,
        select_diagnostic_items_for_test,
    )

    versions = tuple(active_versions or ACTIVE_DIAGNOSTIC_VERSIONS)
    rows = _fetch_diagnostic_vocab_rows(active_versions=versions)
    selected_rows = select_diagnostic_items_for_test(
        rows,
        active_versions=versions,
        random_seed=random_seed,
    )
    return [build_diagnostic_question_payload(row) for row in selected_rows]


# Temporary student-side preview hook for validating question distribution and option shuffle.
def get_diagnostic_vocab_preview_bundle(*, active_versions=None, random_seed: int | None = None):
    from diagnostic_vocab_service import ACTIVE_DIAGNOSTIC_VERSIONS, build_diagnostic_preview_summary

    versions = tuple(active_versions or ACTIVE_DIAGNOSTIC_VERSIONS)
    questions = get_diagnostic_vocab_items_for_test(
        active_versions=versions,
        random_seed=random_seed,
    )
    return {
        "summary": build_diagnostic_preview_summary(questions),
        "questions": questions,
    }
