# db_student.py

'''学生端数据库读取文件

这个文件只负责“学生前台需要读取的数据”，不负责后台写入和管理操作。

为什么单独做这个文件：
1. 学生端 public repo 不应该继续带着后台整套数据库逻辑
2. 这样后面迁移到 Supabase / Postgres 时，会更容易替换
3. 也能减少 public repo 暴露不必要函数
'''

import sqlite3

DB_PATH = "database/app.db"


# =========================================
# 一、基础连接
# =========================================
def get_connection():
    """
    返回一个 SQLite 数据库连接
    学生端当前还是先沿用本地 SQLite
    后面再迁移到 Supabase / Postgres
    """
    return sqlite3.connect(DB_PATH)


# =========================================
# 二、学生身份选择
# =========================================
def get_all_students():
    """
    获取所有学生

    返回：
    [(id, name, grade), ...]
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, grade
        FROM students
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()
    conn.close()
    return rows


# =========================================
# 三、学案读取
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
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            lesson_type,
            difficulty,
            topic,
            created_at
        FROM lessons
        WHERE student_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT ?
    """, (student_id, limit))

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_lesson_detail_for_student(student_id, lesson_id):
    """
    获取某个学生名下某一份学案的完整信息

    这样写的好处：
    1. 学生端只能读取自己的学案
    2. 后面即使做正式登录，也能继续复用这个接口
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            lesson_type,
            difficulty,
            topic,
            content,
            created_at
        FROM lessons
        WHERE id = ? AND student_id = ?
        LIMIT 1
    """, (lesson_id, student_id))

    row = cursor.fetchone()
    conn.close()
    return row


# =========================================
# 四、学生已学单词
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
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            vi.lemma,
            COALESCE(buv.book_meaning, vi.default_meaning, '') AS meaning,
            svp.status,
            svp.review_count,
            svp.error_count,
            svp.memory_score,
            svp.first_learned_at,
            svp.last_review_time,
            svp.next_review_time
        FROM student_vocab_progress svp
        JOIN vocab_items vi
            ON svp.vocab_item_id = vi.id
        LEFT JOIN book_unit_vocab buv
            ON buv.vocab_item_id = svp.vocab_item_id
           AND buv.book_id = svp.first_source_book_id
           AND (
                buv.unit_id = svp.first_source_unit_id
                OR (buv.unit_id IS NULL AND svp.first_source_unit_id IS NULL)
           )
        WHERE svp.student_id = ?
        ORDER BY svp.first_learned_at DESC, svp.id DESC
    """, (student_id,))

    rows = cursor.fetchall()
    conn.close()
    return rows


# =========================================
# 五、学习进度
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
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            wb.id,
            wb.book_name,
            wb.volume_name,
            COUNT(DISTINCT svp.vocab_item_id) AS learned_count,
            COUNT(DISTINCT buv_all.vocab_item_id) AS total_count,
            COUNT(DISTINCT CASE WHEN svp.status = 'mastered' THEN svp.vocab_item_id END) AS mastered_count,
            COUNT(DISTINCT CASE WHEN svp.status = 'learning' THEN svp.vocab_item_id END) AS learning_count,
            COUNT(DISTINCT CASE WHEN svp.status = 'review' THEN svp.vocab_item_id END) AS review_count
        FROM word_books wb
        LEFT JOIN student_vocab_progress svp
            ON wb.id = svp.first_source_book_id
           AND svp.student_id = ?
        LEFT JOIN book_unit_vocab buv_all
            ON wb.id = buv_all.book_id
        GROUP BY wb.id, wb.book_name, wb.volume_name
        ORDER BY wb.id DESC
    """, (student_id,))

    rows = cursor.fetchall()
    conn.close()
    return rows


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
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            wu.id,
            wu.unit_name,
            wu.unit_order,
            COUNT(DISTINCT CASE WHEN svp.student_id = ? THEN svp.vocab_item_id END) AS learned_count,
            COUNT(DISTINCT buv.vocab_item_id) AS total_count
        FROM word_units wu
        LEFT JOIN book_unit_vocab buv
            ON wu.id = buv.unit_id
        LEFT JOIN student_vocab_progress svp
            ON svp.first_source_unit_id = wu.id
           AND svp.first_source_book_id = wu.book_id
           AND svp.vocab_item_id = buv.vocab_item_id
           AND svp.student_id = ?
        WHERE wu.book_id = ?
        GROUP BY wu.id, wu.unit_name, wu.unit_order
        ORDER BY wu.unit_order ASC, wu.id ASC
    """, (student_id, student_id, book_id))

    rows = cursor.fetchall()
    conn.close()
    return rows


# =========================================
# 六、词汇检测记录
# =========================================
def get_student_vocab_test_records(student_id, limit=20):
    """
    获取某个学生最近的词汇检测记录
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
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
        FROM vocab_test_records
        WHERE student_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT ?
    """, (student_id, limit))

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_vocab_test_record_items(test_record_id):
    """
    获取某一轮检测的逐题明细
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            vocab_item_id,
            word,
            meaning,
            mode,
            user_answer,
            is_correct
        FROM vocab_test_record_items
        WHERE test_record_id = ?
        ORDER BY id ASC
    """, (test_record_id,))

    rows = cursor.fetchall()
    conn.close()
    return rows