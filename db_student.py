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