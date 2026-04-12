# db_student.py

'''学生端数据库读取文件（Supabase 版）

这个文件只负责“学生前台需要读取的数据”，
不负责后台写入和管理操作。

当前目标：
1. 先把学生端从 SQLite 切到 Supabase
2. 保持函数名尽量不变，减少 student_app.py 改动
3. 先跑通“读取链路”，后面再继续做权限收紧和登录隔离
'''

from supabase_client import get_supabase_client


# =========================================
# 一、学生身份选择
# =========================================
def get_all_students():
    """
    获取所有学生

    返回：
    [(id, name, grade), ...]
    """
    supabase = get_supabase_client()

    response = (
        supabase.table("students")
        .select("id, name, grade")
        .order("id", desc=True)
        .execute()
    )

    rows = response.data or []
    return [(row["id"], row["name"], row["grade"]) for row in rows]


# =========================================
# 二、学案读取
# =========================================
def get_recent_lessons_by_student(student_id, limit=5):
    """
    获取某个学生最近几份学案

    返回：
    [
        (lesson_id, lesson_type, difficulty, topic, created_at),
        ...
    ]
    """
    supabase = get_supabase_client()

    response = (
        supabase.table("lessons")
        .select("id, lesson_type, difficulty, topic, created_at")
        .eq("student_id", student_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    rows = response.data or []
    return [
        (
            row["id"],
            row.get("lesson_type"),
            row.get("difficulty"),
            row.get("topic"),
            row.get("created_at"),
        )
        for row in rows
    ]


def get_lesson_detail_for_student(student_id, lesson_id):
    """
    获取某个学生名下某一份学案的完整信息
    """
    supabase = get_supabase_client()

    response = (
        supabase.table("lessons")
        .select("id, lesson_type, difficulty, topic, content, created_at")
        .eq("student_id", student_id)
        .eq("id", lesson_id)
        .limit(1)
        .execute()
    )

    rows = response.data or []
    if not rows:
        return None

    row = rows[0]
    return (
        row["id"],
        row.get("lesson_type"),
        row.get("difficulty"),
        row.get("topic"),
        row.get("content"),
        row.get("created_at"),
    )


# =========================================
# 三、学生已学单词
# =========================================
def get_student_learned_vocab(student_id):
    """
    获取某个学生的已学单词列表

    返回：
    [
        (
            lemma,
            meaning,
            status,
            review_count,
            error_count,
            memory_score,
            first_learned_at,
            last_review_time,
            next_review_time
        ),
        ...
    ]
    """
    supabase = get_supabase_client()

    # 先查 student_vocab_progress
    progress_resp = (
        supabase.table("student_vocab_progress")
        .select("""
            vocab_item_id,
            first_source_book_id,
            first_source_unit_id,
            status,
            review_count,
            error_count,
            memory_score,
            first_learned_at,
            last_review_time,
            next_review_time
        """)
        .eq("student_id", student_id)
        .order("first_learned_at", desc=True)
        .execute()
    )
    progress_rows = progress_resp.data or []

    if not progress_rows:
        return []

    vocab_item_ids = [row["vocab_item_id"] for row in progress_rows if row.get("vocab_item_id") is not None]
    if not vocab_item_ids:
        return []

    # 查 vocab_items
    vocab_resp = (
        supabase.table("vocab_items")
        .select("id, lemma, default_meaning")
        .filter("id", "in", f"({','.join(map(str, vocab_item_ids))})")
        .execute()
    )
    vocab_rows = vocab_resp.data or []
    vocab_map = {row["id"]: row for row in vocab_rows}

    # 查 book_unit_vocab，尽量还原学生第一次学这个词时的 book_meaning
    buv_resp = (
        supabase.table("book_unit_vocab")
        .select("book_id, unit_id, vocab_item_id, book_meaning")
        .filter("vocab_item_id", "in", f"({','.join(map(str, vocab_item_ids))})")
        .execute()
    )
    buv_rows = buv_resp.data or []

    result = []
    for p in progress_rows:
        vocab_item_id = p["vocab_item_id"]
        vocab_info = vocab_map.get(vocab_item_id, {})
        lemma = vocab_info.get("lemma", "")
        default_meaning = vocab_info.get("default_meaning", "")

        matched_book_meaning = None
        for buv in buv_rows:
            if (
                buv.get("vocab_item_id") == vocab_item_id
                and buv.get("book_id") == p.get("first_source_book_id")
                and buv.get("unit_id") == p.get("first_source_unit_id")
            ):
                matched_book_meaning = buv.get("book_meaning")
                break

        meaning = matched_book_meaning or default_meaning or ""

        result.append(
            (
                lemma,
                meaning,
                p.get("status"),
                p.get("review_count"),
                p.get("error_count"),
                p.get("memory_score"),
                p.get("first_learned_at"),
                p.get("last_review_time"),
                p.get("next_review_time"),
            )
        )

    return result


# =========================================
# 四、学习进度
# =========================================
def get_student_book_progress(student_id):
    """
    获取某个学生在各个词汇书中的学习进度

    返回：
    [
        (
            book_id,
            book_name,
            volume_name,
            learned_count,
            total_count,
            mastered_count,
            learning_count,
            review_count
        ),
        ...
    ]
    """
    supabase = get_supabase_client()

    books_resp = (
        supabase.table("word_books")
        .select("id, book_name, volume_name")
        .order("id", desc=True)
        .execute()
    )
    books = books_resp.data or []

    progress_resp = (
        supabase.table("student_vocab_progress")
        .select("vocab_item_id, first_source_book_id, status")
        .eq("student_id", student_id)
        .execute()
    )
    progress_rows = progress_resp.data or []

    buv_resp = (
        supabase.table("book_unit_vocab")
        .select("book_id, vocab_item_id")
        .execute()
    )
    buv_rows = buv_resp.data or []

    result = []

    for book in books:
        book_id = book["id"]
        book_name = book.get("book_name")
        volume_name = book.get("volume_name")

        total_vocab_ids = {
            row["vocab_item_id"]
            for row in buv_rows
            if row.get("book_id") == book_id and row.get("vocab_item_id") is not None
        }

        learned_rows = [
            row for row in progress_rows
            if row.get("first_source_book_id") == book_id
        ]

        learned_vocab_ids = {row["vocab_item_id"] for row in learned_rows if row.get("vocab_item_id") is not None}

        mastered_count = len({row["vocab_item_id"] for row in learned_rows if row.get("status") == "mastered"})
        learning_count = len({row["vocab_item_id"] for row in learned_rows if row.get("status") == "learning"})
        review_count = len({row["vocab_item_id"] for row in learned_rows if row.get("status") == "review"})

        result.append(
            (
                book_id,
                book_name,
                volume_name,
                len(learned_vocab_ids),
                len(total_vocab_ids),
                mastered_count,
                learning_count,
                review_count,
            )
        )

    return result


def get_student_unit_progress(student_id, book_id):
    """
    获取某个学生在某本词汇书各单元中的学习进度

    返回：
    [
        (
            unit_id,
            unit_name,
            unit_order,
            learned_count,
            total_count
        ),
        ...
    ]
    """
    supabase = get_supabase_client()

    units_resp = (
        supabase.table("word_units")
        .select("id, unit_name, unit_order")
        .eq("book_id", book_id)
        .order("unit_order", desc=False)
        .execute()
    )
    units = units_resp.data or []

    buv_resp = (
        supabase.table("book_unit_vocab")
        .select("unit_id, vocab_item_id")
        .eq("book_id", book_id)
        .execute()
    )
    buv_rows = buv_resp.data or []

    progress_resp = (
        supabase.table("student_vocab_progress")
        .select("vocab_item_id, first_source_book_id, first_source_unit_id")
        .eq("student_id", student_id)
        .eq("first_source_book_id", book_id)
        .execute()
    )
    progress_rows = progress_resp.data or []

    result = []

    for unit in units:
        unit_id = unit["id"]

        total_vocab_ids = {
            row["vocab_item_id"]
            for row in buv_rows
            if row.get("unit_id") == unit_id and row.get("vocab_item_id") is not None
        }

        learned_vocab_ids = {
            row["vocab_item_id"]
            for row in progress_rows
            if row.get("first_source_unit_id") == unit_id and row.get("vocab_item_id") is not None
        }

        result.append(
            (
                unit_id,
                unit.get("unit_name"),
                unit.get("unit_order", 0),
                len(learned_vocab_ids),
                len(total_vocab_ids),
            )
        )

    return result


# =========================================
# 五、词汇检测记录
# =========================================
def get_student_vocab_test_records(student_id, limit=20):
    """
    获取某个学生最近的词汇检测记录
    """
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


def get_vocab_test_record_items(test_record_id):
    """
    获取某一轮检测的逐题明细
    """
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

# =========================================
# 六、覆盖修复：大词汇书统计 / 单元进度 / 学生端自测支持
# =========================================
import random
import re


def _count_book_vocab_exact(book_id: int) -> int:
    supabase = get_supabase_client()
    resp = (
        supabase.table("book_unit_vocab")
        .select("id", count="exact")
        .eq("book_id", book_id)
        .execute()
    )
    return resp.count or 0


def _count_unit_vocab_exact(unit_id: int) -> int:
    supabase = get_supabase_client()
    resp = (
        supabase.table("book_unit_vocab")
        .select("id", count="exact")
        .eq("unit_id", unit_id)
        .execute()
    )
    return resp.count or 0


def _fetch_all_book_unit_vocab_rows(book_id: int, unit_id=None, columns: str = "unit_id, vocab_item_id, surface_word, book_meaning, item_order"):
    supabase = get_supabase_client()
    start = 0
    page_size = 1000
    rows = []

    while True:
        query = (
            supabase.table("book_unit_vocab")
            .select(columns)
            .eq("book_id", book_id)
            .range(start, start + page_size - 1)
        )
        if unit_id is not None:
            query = query.eq("unit_id", unit_id)

        page = query.execute().data or []
        rows.extend(page)
        if len(page) < page_size:
            break
        start += page_size

    return rows


def get_all_word_books():
    supabase = get_supabase_client()
    rows = (
        supabase.table("word_books")
        .select("id, book_name, volume_name, description")
        .order("id", desc=True)
        .execute()
        .data
        or []
    )
    return [(row["id"], row.get("book_name"), row.get("volume_name"), row.get("description")) for row in rows]


def get_units_by_book(book_id):
    supabase = get_supabase_client()
    rows = (
        supabase.table("word_units")
        .select("id, unit_name, unit_order")
        .eq("book_id", book_id)
        .order("unit_order", desc=False)
        .execute()
        .data
        or []
    )
    return [(row["id"], row.get("unit_name"), row.get("unit_order", 0)) for row in rows]


def get_student_learned_vocab(student_id):
    supabase = get_supabase_client()

    progress_rows = (
        supabase.table("student_vocab_progress")
        .select(
            """
            vocab_item_id,
            first_source_book_id,
            first_source_unit_id,
            status,
            review_count,
            error_count,
            memory_score,
            first_learned_at,
            last_review_time,
            next_review_time
            """
        )
        .eq("student_id", student_id)
        .order("first_learned_at", desc=True)
        .execute()
        .data
        or []
    )
    if not progress_rows:
        return []

    vocab_item_ids = [row["vocab_item_id"] for row in progress_rows if row.get("vocab_item_id") is not None]
    if not vocab_item_ids:
        return []

    vocab_rows = (
        supabase.table("vocab_items")
        .select("id, lemma, default_meaning")
        .in_("id", vocab_item_ids)
        .execute()
        .data
        or []
    )
    vocab_map = {row["id"]: row for row in vocab_rows}

    buv_rows = (
        supabase.table("book_unit_vocab")
        .select("book_id, unit_id, vocab_item_id, book_meaning")
        .in_("vocab_item_id", vocab_item_ids)
        .execute()
        .data
        or []
    )

    result = []
    for p in progress_rows:
        vocab_item_id = p.get("vocab_item_id")
        vocab_info = vocab_map.get(vocab_item_id, {})
        lemma = vocab_info.get("lemma", "")
        default_meaning = vocab_info.get("default_meaning", "")

        matched_book_meaning = None
        # 先按书+单元精确匹配
        for buv in buv_rows:
            if (
                buv.get("vocab_item_id") == vocab_item_id
                and buv.get("book_id") == p.get("first_source_book_id")
                and buv.get("unit_id") == p.get("first_source_unit_id")
            ):
                matched_book_meaning = buv.get("book_meaning")
                break
        # 如果 first_source_unit_id 为空，就退回到书级匹配
        if matched_book_meaning is None:
            for buv in buv_rows:
                if (
                    buv.get("vocab_item_id") == vocab_item_id
                    and buv.get("book_id") == p.get("first_source_book_id")
                ):
                    matched_book_meaning = buv.get("book_meaning")
                    break

        meaning = matched_book_meaning or default_meaning or ""
        result.append(
            (
                lemma,
                meaning,
                p.get("status"),
                p.get("review_count"),
                p.get("error_count"),
                p.get("memory_score"),
                p.get("first_learned_at"),
                p.get("last_review_time"),
                p.get("next_review_time"),
            )
        )
    return result


def get_student_book_progress(student_id):
    supabase = get_supabase_client()
    books = (
        supabase.table("word_books")
        .select("id, book_name, volume_name")
        .order("id", desc=True)
        .execute()
        .data
        or []
    )
    progress_rows = (
        supabase.table("student_vocab_progress")
        .select("vocab_item_id, first_source_book_id, status")
        .eq("student_id", student_id)
        .execute()
        .data
        or []
    )

    result = []
    for book in books:
        book_id = book["id"]
        learned_rows = [row for row in progress_rows if row.get("first_source_book_id") == book_id]
        learned_vocab_ids = {row["vocab_item_id"] for row in learned_rows if row.get("vocab_item_id") is not None}
        mastered_count = len({row["vocab_item_id"] for row in learned_rows if row.get("status") == "mastered"})
        learning_count = len({row["vocab_item_id"] for row in learned_rows if row.get("status") == "learning"})
        review_count = len({row["vocab_item_id"] for row in learned_rows if row.get("status") == "review"})
        result.append(
            (
                book_id,
                book.get("book_name"),
                book.get("volume_name"),
                len(learned_vocab_ids),
                _count_book_vocab_exact(book_id),
                mastered_count,
                learning_count,
                review_count,
            )
        )
    return result


def get_student_unit_progress(student_id, book_id):
    supabase = get_supabase_client()
    units = (
        supabase.table("word_units")
        .select("id, unit_name, unit_order")
        .eq("book_id", book_id)
        .order("unit_order", desc=False)
        .execute()
        .data
        or []
    )

    buv_rows = _fetch_all_book_unit_vocab_rows(book_id, columns="unit_id, vocab_item_id")
    membership_map = {}
    for row in buv_rows:
        vocab_item_id = row.get("vocab_item_id")
        unit_id = row.get("unit_id")
        if vocab_item_id is None or unit_id is None:
            continue
        membership_map.setdefault(vocab_item_id, set()).add(unit_id)

    progress_rows = (
        supabase.table("student_vocab_progress")
        .select("vocab_item_id, first_source_book_id, first_source_unit_id")
        .eq("student_id", student_id)
        .eq("first_source_book_id", book_id)
        .execute()
        .data
        or []
    )

    learned_by_unit = {unit["id"]: set() for unit in units}
    for row in progress_rows:
        vocab_item_id = row.get("vocab_item_id")
        source_unit_id = row.get("first_source_unit_id")
        if vocab_item_id is None:
            continue
        if source_unit_id in learned_by_unit:
            learned_by_unit[source_unit_id].add(vocab_item_id)
            continue
        candidate_units = membership_map.get(vocab_item_id, set())
        if len(candidate_units) == 1:
            inferred_unit_id = next(iter(candidate_units))
            if inferred_unit_id in learned_by_unit:
                learned_by_unit[inferred_unit_id].add(vocab_item_id)

    result = []
    for unit in units:
        unit_id = unit["id"]
        result.append(
            (
                unit_id,
                unit.get("unit_name"),
                unit.get("unit_order", 0),
                len(learned_by_unit.get(unit_id, set())),
                _count_unit_vocab_exact(unit_id),
            )
        )
    return result


def get_progress_test_pool(student_id, count=15):
    supabase = get_supabase_client()
    progress_rows = (
        supabase.table("student_vocab_progress")
        .select("vocab_item_id, first_source_book_id, first_source_unit_id, first_learned_at")
        .eq("student_id", student_id)
        .order("first_learned_at", desc=True)
        .execute()
        .data
        or []
    )
    if not progress_rows:
        return []

    random.shuffle(progress_rows)
    selected = progress_rows[:count]
    vocab_item_ids = [row["vocab_item_id"] for row in selected if row.get("vocab_item_id") is not None]
    vocab_rows = (
        supabase.table("vocab_items")
        .select("id, lemma, default_meaning")
        .in_("id", vocab_item_ids)
        .execute()
        .data
        or []
    )
    vocab_map = {row["id"]: row for row in vocab_rows}
    buv_rows = (
        supabase.table("book_unit_vocab")
        .select("book_id, unit_id, vocab_item_id, book_meaning")
        .in_("vocab_item_id", vocab_item_ids)
        .execute()
        .data
        or []
    )

    result = []
    for row in selected:
        vocab_item_id = row.get("vocab_item_id")
        if vocab_item_id is None:
            continue
        vocab_info = vocab_map.get(vocab_item_id, {})
        lemma = vocab_info.get("lemma", "")
        meaning = vocab_info.get("default_meaning", "")
        for buv in buv_rows:
            if (
                buv.get("vocab_item_id") == vocab_item_id
                and buv.get("book_id") == row.get("first_source_book_id")
                and (row.get("first_source_unit_id") is None or buv.get("unit_id") == row.get("first_source_unit_id"))
            ):
                meaning = buv.get("book_meaning") or meaning
                break
        result.append((vocab_item_id, lemma, meaning))
    return result


def get_book_vocab_for_test(book_id, unit_id=None, count=15, random_mode=True):
    rows = _fetch_all_book_unit_vocab_rows(book_id, unit_id=unit_id, columns="unit_id, vocab_item_id, surface_word, book_meaning, item_order")
    if not rows:
        return []
    if random_mode:
        random.shuffle(rows)
    else:
        rows = sorted(rows, key=lambda r: (r.get("item_order") or 0, r.get("id") or 0))
    selected = rows[:count]
    return [
        (
            row.get("vocab_item_id"),
            row.get("surface_word") or "",
            row.get("book_meaning") or "",
        )
        for row in selected
        if row.get("vocab_item_id") is not None
    ]


def try_save_student_test_result(
    student_id,
    source_type,
    source_book_id,
    source_unit_id,
    source_label,
    test_type,
    test_mode,
    results,
):
    """学生端尝试写入检测记录。

    注意：
    1. 当前学生端使用 publishable key。
    2. 如果 RLS 还没有开放 insert，这里会自动失败并返回 False。
    3. 页面会继续展示成绩，不会因为写入失败而中断。
    """
    supabase = get_supabase_client()
    total_count = len(results)
    correct_count = sum(1 for r in results if r.get("is_correct"))
    accuracy = (correct_count / total_count) if total_count else 0

    try:
        record_resp = (
            supabase.table("vocab_test_records")
            .insert(
                {
                    "student_id": student_id,
                    "source_type": source_type,
                    "source_book_id": source_book_id,
                    "source_unit_id": source_unit_id,
                    "source_label": source_label,
                    "test_type": test_type,
                    "test_mode": test_mode,
                    "total_count": total_count,
                    "correct_count": correct_count,
                    "accuracy": accuracy,
                    "is_synced_to_progress": False,
                    "is_wrong_retry_round": False,
                }
            )
            .execute()
        )
        record_rows = record_resp.data or []
        if not record_rows:
            return False, "学生端检测结果暂未写入数据库。"
        record_id = record_rows[0]["id"]

        item_payloads = []
        for row in results:
            item_payloads.append(
                {
                    "test_record_id": record_id,
                    "vocab_item_id": row.get("vocab_item_id"),
                    "word": row.get("word"),
                    "meaning": row.get("meaning"),
                    "mode": row.get("mode"),
                    "user_answer": row.get("user_answer"),
                    "is_correct": row.get("is_correct", False),
                }
            )
        if item_payloads:
            supabase.table("vocab_test_record_items").insert(item_payloads).execute()
        return True, "检测结果已写入数据库。"
    except Exception:
        return False, "学生端检测已完成，但当前 RLS 可能未开放写入，所以没有保存到数据库。"
