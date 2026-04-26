import os
import sqlite3

# ==============================
# system_check.py
# 这个文件负责：
# 1. 自动创建数据库中需要的表
# 2. 自动补齐旧版本数据库缺少的字段
# 3. 在程序启动时做一次“系统自检”
#
# 你可以把它理解成：
# “数据库维修员 / 巡检员”
# ==============================

DB_PATH = "database/app.db"


# ------------------------------
# 基础连接工具
# ------------------------------
def get_connection():
    """
    返回一个 SQLite 数据库连接。

    这里顺手确保 database 文件夹存在，
    避免第一次运行时因为目录不存在而报错。
    """
    os.makedirs("database", exist_ok=True)
    return sqlite3.connect(DB_PATH)


# ------------------------------
# 表结构检查工具
# ------------------------------
def get_table_columns(cursor, table_name):
    """
    读取某个表当前已有的字段名。

    用途：
    - 判断旧数据库里是否缺少某个新字段
    - 如果缺少，就通过 ALTER TABLE 补上
    """
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]


# ------------------------------
# students：学生表
# ------------------------------
def ensure_students_table(cursor):
    """
    学生基础信息表。

    当前保存：
    - id
    - name
    - grade
    - login_account
    - login_password（兼容旧版明文密码）
    - login_password_hash
    - memory_score（学生整体记忆参数）
    """
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            grade TEXT NOT NULL,
            login_account TEXT UNIQUE,
            login_password TEXT,
            login_password_hash TEXT,
            memory_score REAL DEFAULT 3.0
        )
    """)

    # 兼容旧版数据库：补学生登录字段和 memory_score 字段
    columns = get_table_columns(cursor, "students")
    if "login_account" not in columns:
        cursor.execute(
            "ALTER TABLE students ADD COLUMN login_account TEXT"
        )
    if "login_password" not in columns:
        cursor.execute(
            "ALTER TABLE students ADD COLUMN login_password TEXT"
        )
    if "login_password_hash" not in columns:
        cursor.execute(
            "ALTER TABLE students ADD COLUMN login_password_hash TEXT"
        )
    if "memory_score" not in columns:
        cursor.execute(
            "ALTER TABLE students ADD COLUMN memory_score REAL DEFAULT 3.0"
        )


# ------------------------------
# lessons：学案主表
# ------------------------------
def ensure_lessons_table(cursor):
    """
    学案主表。

    一份学案会记录：
    - 属于哪个学生
    - 学案类型
    - 难度
    - 主题
    - 完整内容
    - 创建时间
    """
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            lesson_type TEXT,
            difficulty TEXT,
            topic TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


# ------------------------------
# vocab_items：词条主表
# ------------------------------
def ensure_vocab_items_table(cursor):
    """
    词条本体表。

    这里保存“标准词条信息”，比如：
    - lemma
    - normalized_lemma
    - pos
    - ipa
    - 默认释义
    - 例句
    """
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vocab_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lemma TEXT NOT NULL,
            normalized_lemma TEXT NOT NULL UNIQUE,
            pos TEXT,
            ipa_br TEXT,
            ipa_am TEXT,
            default_meaning TEXT,
            example_en TEXT,
            example_zh TEXT,
            audio_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


# ------------------------------
# word_books：词汇书主表
# ------------------------------
def ensure_word_books_table(cursor):
    """
    词汇书主表。

    一条记录代表一本词汇书。
    """
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS word_books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_name TEXT NOT NULL,
            volume_name TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


# ------------------------------
# word_units：词汇书单元表
# ------------------------------
def ensure_word_units_table(cursor):
    """
    词汇书里的单元 / 主题表。

    当前最重要的补字段是：unit_order
    因为你后面很多抽词、排序逻辑会依赖它。
    """
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS word_units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            unit_name TEXT NOT NULL,
            unit_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (book_id) REFERENCES word_books(id)
        )
    """)

    # 兼容旧版数据库：补 unit_order 字段
    columns = get_table_columns(cursor, "word_units")
    if "unit_order" not in columns:
        cursor.execute(
            "ALTER TABLE word_units ADD COLUMN unit_order INTEGER DEFAULT 0"
        )


# ------------------------------
# book_unit_vocab：词汇书-单元-词条映射表
# ------------------------------
def ensure_book_unit_vocab_table(cursor):
    """
    把“某本书 / 某个单元 / 某个词条”绑定起来。

    这里保存：
    - 书内展示词形 surface_word
    - 书内释义 book_meaning
    - 来源行 source_line
    - 顺序 item_order
    """
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS book_unit_vocab (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            unit_id INTEGER,
            vocab_item_id INTEGER NOT NULL,
            surface_word TEXT NOT NULL,
            book_meaning TEXT,
            book_note TEXT,
            source_line TEXT,
            item_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(book_id, unit_id, vocab_item_id),
            FOREIGN KEY (book_id) REFERENCES word_books(id),
            FOREIGN KEY (unit_id) REFERENCES word_units(id),
            FOREIGN KEY (vocab_item_id) REFERENCES vocab_items(id)
        )
    """)

    # 兼容旧版数据库：补 item_order 字段
    columns = get_table_columns(cursor, "book_unit_vocab")
    if "item_order" not in columns:
        cursor.execute(
            "ALTER TABLE book_unit_vocab ADD COLUMN item_order INTEGER DEFAULT 0"
        )


# ------------------------------
# student_vocab_progress：学生词汇学习进度表
# ------------------------------
def ensure_student_vocab_progress_table(cursor):
    """
    学生-单词学习进度表。

    这里是后面复习系统、抽复习词、记忆曲线的核心表。
    """
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_vocab_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            vocab_item_id INTEGER NOT NULL,
            first_source_book_id INTEGER,
            first_source_unit_id INTEGER,
            status TEXT DEFAULT 'learning',
            review_count INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            last_review_time TEXT,
            next_review_time TEXT,
            memory_score REAL DEFAULT 3.0,
            first_learned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, vocab_item_id),
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (vocab_item_id) REFERENCES vocab_items(id),
            FOREIGN KEY (first_source_book_id) REFERENCES word_books(id),
            FOREIGN KEY (first_source_unit_id) REFERENCES word_units(id)
        )
    """)


# ------------------------------
# lesson_vocab_items：学案-词条绑定表
# ------------------------------
def ensure_lesson_vocab_items_table(cursor):
    """
    记录某份学案里用了哪些词。

    word_type 常见值：
    - new
    - review
    """
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lesson_vocab_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER NOT NULL,
            vocab_item_id INTEGER NOT NULL,
            word_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lesson_id) REFERENCES lessons(id),
            FOREIGN KEY (vocab_item_id) REFERENCES vocab_items(id)
        )
    """)


# ------------------------------
# vocab_test_records：词汇检测总记录表
# ------------------------------
def ensure_vocab_test_records_table(cursor):
    """
    保存一整轮词汇检测的总记录。

    例如：
    - 哪个学生
    - 来源是学习进度还是词汇书抽测
    - 检测类型 / 模式
    - 总题数 / 正确数 / 正确率
    - 是否同步到学习进度
    - 是否为错词重测
    """
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vocab_test_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            source_type TEXT,
            source_book_id INTEGER,
            source_unit_id INTEGER,
            source_label TEXT,
            test_type TEXT,
            test_mode TEXT,
            total_count INTEGER DEFAULT 0,
            correct_count INTEGER DEFAULT 0,
            accuracy REAL DEFAULT 0,
            is_synced_to_progress INTEGER DEFAULT 0,
            is_wrong_retry_round INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (source_book_id) REFERENCES word_books(id),
            FOREIGN KEY (source_unit_id) REFERENCES word_units(id)
        )
    """)


# ------------------------------
# vocab_test_record_items：词汇检测逐题明细表
# ------------------------------
def ensure_vocab_test_record_items_table(cursor):
    """
    保存某一轮词汇检测里的每一道题明细。

    例如：
    - 是哪个词
    - 学生答了什么
    - 对错
    """
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vocab_test_record_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_record_id INTEGER NOT NULL,
            vocab_item_id INTEGER,
            word TEXT,
            meaning TEXT,
            mode TEXT,
            user_answer TEXT,
            is_correct INTEGER DEFAULT 0,
            FOREIGN KEY (test_record_id) REFERENCES vocab_test_records(id),
            FOREIGN KEY (vocab_item_id) REFERENCES vocab_items(id)
        )
    """)


def ensure_diagnostic_vocab_items_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS diagnostic_vocab_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id TEXT NOT NULL UNIQUE,
            module TEXT,
            level TEXT,
            word TEXT,
            primary_meaning_zh TEXT,
            part_of_speech TEXT,
            category TEXT,
            sub_skill TEXT,
            question_type TEXT,
            question_text TEXT,
            correct_answer TEXT,
            wrong_option_1 TEXT,
            wrong_option_2 TEXT,
            wrong_option_3 TEXT,
            explanation TEXT,
            diagnostic_tag TEXT,
            diagnostic_value TEXT,
            difficulty_level TEXT,
            grade_level TEXT,
            frequency_band TEXT,
            source_type TEXT,
            source_note TEXT,
            source_url_primary TEXT,
            source_url_method TEXT,
            is_anchor INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            version TEXT,
            sentence TEXT,
            notes_for_codex TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def ensure_diagnostic_vocab_results_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS diagnostic_vocab_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            diagnostic_id INTEGER NOT NULL UNIQUE,
            student_id INTEGER NOT NULL,
            total_scored_items INTEGER DEFAULT 0,
            correct_count INTEGER DEFAULT 0,
            overall_accuracy REAL DEFAULT 0,
            l1_accuracy REAL DEFAULT 0,
            l2_accuracy REAL DEFAULT 0,
            l3_accuracy REAL DEFAULT 0,
            l4_accuracy REAL DEFAULT 0,
            l5_accuracy REAL DEFAULT 0,
            high_frequency_accuracy REAL DEFAULT 0,
            reading_vocab_accuracy REAL DEFAULT 0,
            polysemy_accuracy REAL DEFAULT 0,
            confusable_accuracy REAL DEFAULT 0,
            uncertain_rate REAL DEFAULT 0,
            estimated_vocab_range TEXT,
            vocab_level_label TEXT,
            main_vocab_problem TEXT,
            recommended_training_start TEXT,
            self_check_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def ensure_diagnostic_vocab_answers_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS diagnostic_vocab_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            diagnostic_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            item_id TEXT NOT NULL,
            selected_answer TEXT,
            is_correct INTEGER DEFAULT 0,
            is_uncertain INTEGER DEFAULT 0,
            time_spent_seconds INTEGER,
            question_type TEXT,
            level TEXT,
            diagnostic_tag TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


# ------------------------------
# 系统自检主入口
# ------------------------------
def run_system_check():
    """
    程序启动时调用一次：
    1. 自动建表
    2. 自动补字段
    3. 如果中途失败就回滚

    注意：
    这个文件里只能保留这一个 run_system_check()。
    不要再出现多个同名版本，否则后定义的版本会覆盖前面的版本。
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        ensure_students_table(cursor)
        ensure_lessons_table(cursor)

        ensure_vocab_items_table(cursor)
        ensure_word_books_table(cursor)
        ensure_word_units_table(cursor)
        ensure_book_unit_vocab_table(cursor)

        ensure_student_vocab_progress_table(cursor)
        ensure_lesson_vocab_items_table(cursor)

        ensure_vocab_test_records_table(cursor)
        ensure_vocab_test_record_items_table(cursor)
        ensure_diagnostic_vocab_items_table(cursor)
        ensure_diagnostic_vocab_results_table(cursor)
        ensure_diagnostic_vocab_answers_table(cursor)

        conn.commit()
        print("✅ 系统自检完成")
        print("✅ 数据库表结构已检查并补齐")
    except Exception as e:
        conn.rollback()
        print("❌ 系统自检失败：", e)
        raise
    finally:
        conn.close()
