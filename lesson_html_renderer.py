"""Printable lesson HTML rendering helpers.

This module is intentionally Streamlit-free so the teacher app and student app
can share the same browser-print HTML output without copying UI code.
"""

from html import escape
import re

def _clean_lines(text: str):
    return [line.rstrip() for line in (text or '').splitlines() if line.strip()]


def _remove_part_title_if_needed(text: str, expected_title: str) -> str:
    if not text:
        return ''
    stripped = text.strip()
    if stripped.startswith(expected_title):
        return stripped[len(expected_title):].strip()
    title_index = stripped.find(expected_title)
    if title_index >= 0:
        return stripped[title_index + len(expected_title):].strip()
    return stripped


def parse_part1_table(part1_text: str):
    """
    把 Part 1 / Part 1B 的纯文本解析成表格数据。
    """
    lines = [line.strip() for line in part1_text.splitlines() if line.strip()]
    if len(lines) < 3:
        return []

    rows = []
    for line in lines[2:]:
        parts = line.split("\t")
        if len(parts) >= 4:
            word, ipa, pos, meaning = parts[:4]
            rows.append({"Word": word, "IPA": ipa, "POS": pos, "Meaning": meaning})
    return rows


def parse_part2_to_three_column_rows(part2_text: str):
    """
    把 Part 2 文本解析成三栏练习表格。
    说明文字会自动跳过，只提取真正的编号题目。
    """
    lines = [line.rstrip() for line in part2_text.splitlines() if line.strip()]
    item_rows = []

    for line in lines:
        if line.startswith("Part 2"):
            continue
        if line.startswith("Complete the following"):
            continue
        if line.startswith("Instructions:"):
            continue
        if line.startswith("Write the English word"):
            continue
        if line.startswith("Note:"):
            continue

        parts = line.split(maxsplit=1)
        if len(parts) == 2 and parts[0].isdigit():
            no = int(parts[0])
            prompt_text = parts[1].strip()
            item_rows.append((no, prompt_text))

    if not item_rows:
        return []

    column_count = 3
    column_size = (len(item_rows) + column_count - 1) // column_count
    column_items = [
        item_rows[i * column_size:(i + 1) * column_size]
        for i in range(column_count)
    ]

    table_rows = []
    max_len = max(len(items) for items in column_items)

    for i in range(max_len):
        row_data = {}
        for col_index, items in enumerate(column_items, start=1):
            no, text = ("", "")
            if i < len(items):
                no, text = items[i]

            suffix = "" if col_index == 1 else f"_{col_index}"
            row_data[f"No{suffix}"] = no
            row_data[f"Meaning / Word{suffix}"] = text
            row_data[f"Answer{suffix}"] = ""

        table_rows.append(row_data)

    return table_rows


def _extract_part1_words(parts: dict):
    """
    从 part1 中提取新词列表，用于 Part 3 高亮。
    """
    rows = parse_part1_table(parts.get('part1', ''))
    words = []
    for row in rows:
        word = str(row.get('Word', '')).strip()
        if word:
            words.append(word)
    words = sorted(set(words), key=lambda x: len(x), reverse=True)
    return words


def _highlight_keywords(text: str, keywords):
    """
    在阅读文章中高亮 P1 新词。
    规则：
    1. 只高亮英文完整词边界
    2. 用红色 + 加粗突出
    """
    if not text or not keywords:
        return escape(text or '')

    working_text = text
    placeholder_map = {}
    counter = 0

    for word in keywords:
        if not word:
            continue
        pattern = re.compile(rf'(?<![A-Za-z])({re.escape(word)})(?![A-Za-z])', flags=re.IGNORECASE)

        def _repl(match):
            nonlocal counter
            placeholder = f'§§KW{counter}§§'
            placeholder_map[placeholder] = (
                '<span class="lesson-keyword">'
                f'{escape(match.group(0))}'
                '</span>'
            )
            counter += 1
            return placeholder

        working_text = pattern.sub(_repl, working_text)

    safe_text = escape(working_text)
    for placeholder, html in placeholder_map.items():
        safe_text = safe_text.replace(escape(placeholder), html)
        safe_text = safe_text.replace(placeholder, html)
    return safe_text


def parse_part4_questions_for_display(part4_text: str):
    """
    解析 Part 4，并统一按当前显示顺序从 1 开始编号。
    这样学生做题和老师查题会更清楚。
    """
    raw_text = _remove_part_title_if_needed(part4_text, 'Part 4 Questions')
    if not raw_text:
        return {"questions": [], "answer_line": ""}

    answer_line = ''
    answer_match = re.search(r'(Answer:\s*.+)$', raw_text, flags=re.MULTILINE)
    if answer_match:
        answer_line = answer_match.group(1).strip()
        raw_text = raw_text[:answer_match.start()].strip()

    question_blocks = re.split(r'(?=\n?\d+\.\s)', '\n' + raw_text)
    question_blocks = [block.strip() for block in question_blocks if block.strip()]

    questions = []
    for idx, block in enumerate(question_blocks, start=1):
        lines = _clean_lines(block)
        if not lines:
            continue

        first_line = lines[0]
        m = re.match(r'(\d+)\.\s*(.*)', first_line)
        if not m:
            continue

        original_number = m.group(1)
        q_stem = m.group(2).strip()
        options = {"A": "", "B": "", "C": "", "D": ""}
        current_option = None

        for line in lines[1:]:
            option_match = re.match(r'([A-D])\.\s*(.*)', line)
            if option_match:
                current_option = option_match.group(1)
                options[current_option] = option_match.group(2).strip()
            elif current_option:
                options[current_option] += ' ' + line.strip()
            else:
                q_stem += ' ' + line.strip()

        questions.append(
            {
                'display_number': str(idx),
                'original_number': original_number,
                'stem': q_stem.strip(),
                'options': options,
            }
        )

    answer_pairs = re.findall(r'(\d+)\.([A-D])', answer_line)
    normalized_answer_line = ''
    if answer_pairs:
        rebuilt = []
        for idx, (_old_num, letter) in enumerate(answer_pairs, start=1):
            rebuilt.append(f'{idx}.{letter}')
        normalized_answer_line = 'Answer: ' + ' '.join(rebuilt)

    return {
        'questions': questions,
        'answer_line': normalized_answer_line or answer_line,
    }


def parse_part5_sentences_for_display(part5_text: str):
    raw_text = _remove_part_title_if_needed(part5_text, 'Part 5 Sentence Translation')
    lines = _clean_lines(raw_text)

    items = []
    for line in lines:
        m = re.match(r'(\d+)\.\s*(.*)', line)
        if m:
            items.append(
                {
                    'display_number': str(len(items) + 1),
                    'sentence': m.group(2).strip(),
                    'answer_line_count': 3,
                }
            )
    return items


def parse_part6_structure(part6_text: str):
    raw_text = _remove_part_title_if_needed(part6_text, 'Part 6 Answer Key & Detailed Teaching Analysis')
    if not raw_text:
        return {'answers': [], 'question_blocks': [], 'sentence_blocks': []}

    answers_match = re.search(r'Reading Answers\s*(.*?)(?=Reading Detailed Analysis|$)', raw_text, flags=re.DOTALL)
    detail_match = re.search(r'Reading Detailed Analysis\s*(.*?)(?=Sentence Translation Detailed Analysis|$)', raw_text, flags=re.DOTALL)
    sentence_match = re.search(r'Sentence Translation Detailed Analysis\s*(.*)$', raw_text, flags=re.DOTALL)

    answers_text = answers_match.group(1).strip() if answers_match else ''
    detail_text = detail_match.group(1).strip() if detail_match else ''
    sentence_text = sentence_match.group(1).strip() if sentence_match else ''

    answers = re.findall(r'(\d+)\.\s*([A-D])', answers_text)
    answer_items = [{'number': num, 'answer': ans} for num, ans in answers]
    if not answer_items:
        for line in _clean_lines(answers_text):
            answer_items.append({'number': '', 'answer': line})

    question_blocks = []
    if detail_text:
        blocks = re.split(r'(?=Question\s*\d+)', detail_text, flags=re.IGNORECASE)
        blocks = [b.strip() for b in blocks if b.strip()]
        for block in blocks:
            lines = _clean_lines(block)
            if not lines:
                continue
            title = lines[0]
            body = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ''
            question_blocks.append({'title': title, 'body': body})

    sentence_blocks = []
    if sentence_text:
        blocks = re.split(r'(?=Sentence\s*\d+)', sentence_text, flags=re.IGNORECASE)
        blocks = [b.strip() for b in blocks if b.strip()]
        for block in blocks:
            lines = _clean_lines(block)
            if not lines:
                continue
            title = lines[0]
            body = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ''
            sentence_blocks.append({'title': title, 'body': body})

    return {
        'answers': answer_items,
        'question_blocks': question_blocks,
        'sentence_blocks': sentence_blocks,
        'raw_text': raw_text,
    }


def parse_part7_structure(part7_text: str):
    raw_text = _remove_part_title_if_needed(part7_text, 'Part 7 Full Passage Translation & Key Language Notes')
    if not raw_text:
        return {'translation_paragraphs': [], 'note_blocks': []}

    trans_match = re.search(r'Full Passage Translation\s*(.*?)(?=Key Language Notes|$)', raw_text, flags=re.DOTALL)
    notes_match = re.search(r'Key Language Notes\s*(.*)$', raw_text, flags=re.DOTALL)

    trans_text = trans_match.group(1).strip() if trans_match else ''
    notes_text = notes_match.group(1).strip() if notes_match else ''

    translation_paragraphs = [p.strip() for p in re.split(r'\n\s*\n', trans_text) if p.strip()]
    if not translation_paragraphs:
        translation_paragraphs = _clean_lines(trans_text)

    note_blocks = []
    if notes_text:
        blocks = re.split(r'(?=Note\s*\d+)', notes_text, flags=re.IGNORECASE)
        blocks = [b.strip() for b in blocks if b.strip()]
        for block in blocks:
            lines = _clean_lines(block)
            if not lines:
                continue
            title = lines[0]
            body = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ''
            note_blocks.append({'title': title, 'body': body})

    return {
        'translation_paragraphs': translation_paragraphs,
        'note_blocks': note_blocks,
        'raw_text': raw_text,
    }


def get_part_table_style():
    """
    返回 Part 1 / Part 2 和长文本预览共用的 CSS。
    """
    return """
    <style>
    body {
        color: #222222;
        font-size: 17px;
        line-height: 1.7;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }

    .lesson-table-wrap {
        width: 100%;
        overflow-x: auto;
        box-sizing: border-box;
        margin: 8px 0 6px 0;
        border: 1px solid #d9d9d9;
        border-radius: 10px;
        background: #ffffff;
    }

    .lesson-table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
        box-sizing: border-box;
        font-size: 18px;
        color: #222222;
    }

    .lesson-table thead th {
        background: #f5f7fb;
        color: #1f2d3d;
        font-weight: 700;
        text-align: center;
        border: 1px solid #d9d9d9;
        padding: 12px 10px;
        line-height: 1.3;
    }

    .lesson-table tbody td {
        border: 1px solid #d9d9d9;
        padding: 14px 12px;
        line-height: 1.45;
        vertical-align: middle;
        word-break: break-word;
        white-space: normal;
    }

    .lesson-table tbody td.center {
        text-align: center;
    }

    .lesson-table tbody td.answer-cell {
        background: #fcfcfc;
    }

    .lesson-table tbody tr:nth-child(even) {
        background: #fafafa;
    }

    .lesson-note-box {
        border: 1px solid #d9d9d9;
        border-radius: 10px;
        background: #ffffff;
        padding: 14px 16px;
        margin: 8px 0 14px 0;
    }

    .lesson-section-title {
        font-size: 18px;
        font-weight: 700;
        color: #1f2d3d;
        margin: 4px 0 12px 0;
    }

    .lesson-subtitle {
        font-size: 16px;
        font-weight: 700;
        color: #304f75;
        margin: 14px 0 10px 0;
    }

    .lesson-answer-chip {
        display: inline-block;
        margin: 4px 8px 4px 0;
        padding: 6px 10px;
        border-radius: 999px;
        background: #eef4ff;
        color: #24406a;
        font-weight: 700;
        font-size: 14px;
    }

    .lesson-keyword {
        color: #c62828;
        font-weight: 700;
    }

    .lesson-passage {
        border: 1px solid #d9d9d9;
        border-radius: 10px;
        background: #ffffff;
        padding: 18px 22px;
    }

    .lesson-passage p {
        margin: 0 0 18px 0;
        line-height: 2.25;
        font-size: 18px;
    }

    .lesson-qa-card, .lesson-note-card {
        border: 1px solid #dde5f0;
        border-radius: 8px;
        background: #ffffff;
        padding: 14px 16px;
        margin: 10px 0 14px 0;
    }

    .teaching-shell {
        border: 1px solid #d9e0eb;
        border-radius: 8px;
        background: #ffffff;
        padding: 16px;
        margin: 8px 0 16px 0;
    }

    .teaching-hero {
        border: 1px solid #d7e4f2;
        border-radius: 8px;
        background: #f7fbff;
        padding: 14px 16px;
        margin-bottom: 14px;
    }

    .teaching-hero-title {
        color: #16324f;
        font-size: 18px;
        font-weight: 800;
        margin-bottom: 6px;
    }

    .teaching-hero-subtitle {
        color: #607086;
        line-height: 1.7;
        font-size: 14px;
    }

    .teaching-band {
        border-radius: 8px;
        padding: 10px 12px;
        margin: 18px 0 12px 0;
        font-size: 16px;
        font-weight: 800;
        color: #19324d;
        border: 1px solid #dbe7f5;
        background: #f6f9fd;
    }

    .teaching-band.green {
        border-color: #d7eadf;
        background: #f6fbf8;
        color: #23543a;
    }

    .teaching-band.amber {
        border-color: #f1dfbf;
        background: #fffaf0;
        color: #6c4a12;
    }

    .answer-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(86px, 1fr));
        gap: 8px;
        margin: 8px 0 10px 0;
    }

    .answer-tile {
        border: 1px solid #dbe7f5;
        border-radius: 8px;
        background: #f8fbff;
        padding: 9px 10px;
        text-align: center;
        color: #1f2d3d;
        font-weight: 800;
    }

    .analysis-card {
        border: 1px solid #dce6f2;
        border-radius: 8px;
        background: #ffffff;
        margin: 10px 0 14px 0;
        overflow: hidden;
    }

    .analysis-card-header {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 12px 14px;
        background: #f7fbff;
        border-bottom: 1px solid #e5edf7;
    }

    .analysis-card-header.amber {
        background: #fffaf0;
        border-bottom-color: #f1dfbf;
    }

    .analysis-badge {
        min-width: 30px;
        height: 30px;
        border-radius: 8px;
        background: #24406a;
        color: #ffffff;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 13px;
    }

    .analysis-badge.amber {
        background: #8a5d15;
    }

    .analysis-title {
        font-weight: 800;
        color: #1f2d3d;
        font-size: 16px;
    }

    .analysis-card-body {
        padding: 12px 14px 14px 14px;
    }

    .analysis-point {
        display: grid;
        grid-template-columns: 7px 1fr;
        column-gap: 10px;
        align-items: start;
        margin: 8px 0;
        line-height: 1.85;
        color: #253241;
        font-size: 16px;
    }

    .analysis-dot {
        width: 7px;
        height: 7px;
        border-radius: 8px;
        background: #7ca1c7;
        margin-top: 12px;
    }

    .analysis-point.heading {
        font-weight: 800;
        color: #24406a;
        margin-top: 12px;
    }

    .analysis-point.heading .analysis-dot {
        background: #24406a;
    }

    .translation-card {
        border: 1px solid #d7eadf;
        border-radius: 8px;
        background: #fbfefc;
        padding: 14px 16px;
        margin: 10px 0 14px 0;
    }

    .translation-label {
        color: #23543a;
        font-weight: 800;
        font-size: 14px;
        margin-bottom: 6px;
    }

    .translation-body {
        color: #243124;
        line-height: 2;
        font-size: 17px;
    }

    .lesson-qa-title {
        font-size: 16px;
        font-weight: 700;
        color: #1f2d3d;
        margin-bottom: 8px;
    }

    .lesson-mono {
        white-space: pre-wrap;
        line-height: 1.9;
        font-size: 16px;
        color: #222222;
    }

    .translation-item {
        border: 1px solid #d9d9d9;
        border-radius: 10px;
        background: #ffffff;
        padding: 14px 16px;
        margin: 10px 0 16px 0;
    }

    .translation-item .translation-sentence {
        line-height: 1.9;
        font-size: 17px;
        margin-bottom: 12px;
    }

    .answer-writing-line {
        border-bottom: 1px dashed #8f9fb5;
        height: 28px;
        margin-bottom: 10px;
    }

    .part2-intro {
        border: 1px solid #d9e0eb;
        background: #f8fbff;
        border-radius: 10px;
        padding: 12px 14px;
        line-height: 1.75;
        margin-bottom: 12px;
    }

    @media print {
        html, body {
            width: auto;
            margin: 0;
            padding: 0;
            background: #ffffff !important;
            color: #111111;
            font-size: 9.5pt;
            line-height: 1.42;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }

        .lesson-note-box,
        .lesson-passage,
        .lesson-qa-card,
        .lesson-note-card,
        .teaching-shell,
        .teaching-hero,
        .analysis-card,
        .translation-card,
        .translation-item,
        .part2-intro,
        .lesson-table-wrap {
            break-inside: auto !important;
            page-break-inside: auto !important;
            box-shadow: none !important;
            margin-top: 0;
            margin-bottom: 8px;
            overflow: visible !important;
        }

        .lesson-table {
            width: 100% !important;
            font-size: 9.5pt;
            line-height: 1.25;
        }

        .lesson-table thead th {
            padding: 6px 5px;
            line-height: 1.2;
        }

        .lesson-table tbody td {
            padding: 7px 6px;
            line-height: 1.28;
        }

        .lesson-table tbody td.answer-cell {
            min-width: 0;
        }

        .lesson-section-title,
        .lesson-subtitle,
        .teaching-band,
        .analysis-card-header,
        .translation-label,
        .lesson-qa-title {
            break-after: avoid;
            page-break-after: avoid;
            break-inside: avoid;
            page-break-inside: avoid;
        }

        .lesson-table tr,
        .answer-tile,
        .analysis-point,
        .answer-writing-line {
            break-inside: avoid;
            page-break-inside: avoid;
        }

        .lesson-passage {
            padding: 10px 12px;
        }

        .lesson-passage p {
            line-height: 1.65;
            font-size: 10pt;
            margin: 0 0 10px 0;
        }

        .lesson-qa-card,
        .lesson-note-card,
        .teaching-shell,
        .teaching-hero,
        .analysis-card,
        .translation-card,
        .translation-item,
        .part2-intro {
            padding: 10px 12px;
        }

        .analysis-card-header {
            padding: 8px 10px;
        }

        .analysis-card-body {
            padding: 8px 10px;
        }

        .analysis-point {
            margin: 4px 0;
            line-height: 1.45;
            font-size: 9.5pt;
        }

        .translation-body {
            line-height: 1.55;
            font-size: 10pt;
        }

        .answer-grid {
            grid-template-columns: repeat(4, 1fr);
            gap: 6px;
        }

        .answer-writing-line {
            height: 18px;
            margin-bottom: 5px;
        }
    }
    </style>
    """


def build_part1_html_table(rows):
    html_parts = ['<div class="lesson-table-wrap">']
    html_parts.append(
        """
    <table class="lesson-table">
        <colgroup>
            <col style="width: 20%;">
            <col style="width: 24%;">
            <col style="width: 8%;">
            <col style="width: 48%;">
        </colgroup>
        <thead>
            <tr>
                <th>Word</th>
                <th>IPA</th>
                <th>POS</th>
                <th>Meaning</th>
            </tr>
        </thead>
        <tbody>
    """
    )

    for row in rows:
        word = escape(str(row.get("Word", "")))
        ipa = escape(str(row.get("IPA", "")))
        pos = escape(str(row.get("POS", "")))
        meaning = escape(str(row.get("Meaning", "")))
        html_parts.append(
            f"""
        <tr>
            <td>{word}</td>
            <td>{ipa}</td>
            <td class="center">{pos}</td>
            <td>{meaning}</td>
        </tr>
        """
        )

    html_parts.append("""
        </tbody>
    </table>
    </div>
    """)
    return ''.join(html_parts)


LESSON_PART_TITLES = (
    ("part1_review", "Part 1B Personal Review Words"),
    ("part1", "Part 1 Key Vocabulary"),
    ("part2", "Part 2 Vocabulary Consolidation Practice"),
    ("part3", "Part 3 Reading Passage"),
    ("part4", "Part 4 Questions"),
    ("part5", "Part 5 Sentence Translation"),
    ("part6", "Part 6 Answer Key & Detailed Teaching Analysis"),
    ("part7", "Part 7 Full Passage Translation & Key Language Notes"),
)


def parse_lesson_text_to_parts(content: str) -> dict:
    """
    把 lessons.content 里保存的整份纯文本学案拆回 part1-part7。

    管理端保存时使用 generator.assemble_full_lesson()，各模块以固定 Part 标题开头。
    学生端导出网页版时需要先拆回 parts，才能复用教师端完全相同的 HTML 渲染器。
    """
    text = (content or "").strip()
    if not text:
        return {}

    title_to_key = {title: key for key, title in LESSON_PART_TITLES}
    title_pattern = "|".join(re.escape(title) for _key, title in LESSON_PART_TITLES)
    matches = list(re.finditer(rf"(?m)^\s*({title_pattern})\s*$", text))
    if not matches:
        return {"raw": text}

    parts = {}
    for index, match in enumerate(matches):
        title = match.group(1)
        key = title_to_key.get(title)
        if not key:
            continue
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        part_text = text[start:end].strip()
        if part_text:
            parts[key] = part_text
    return parts


def build_downloadable_lesson_html(parts: dict, title: str = "英语学案") -> str:
    body_html = build_full_lesson_preview_html(parts)
    if not body_html and parts.get("raw"):
        body_html = f'<pre class="lesson-mono">{escape(str(parts["raw"]))}</pre>'

    safe_title = escape(title or "英语学案")
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{safe_title}</title>
  {get_part_table_style()}
  <style>
    @page {{ size: A4; margin: 12mm; }}
    body {{ margin: 0; padding: 0; background: #ffffff; }}
    .print-wrap {{ width: auto; max-width: none; margin: 0; padding: 0; }}
  </style>
</head>
<body>
  <main class="print-wrap">
    {body_html}
  </main>
</body>
</html>"""


def build_part2_html_table(rows):
    intro_html = """
    <div class="part2-intro">
        <div class="lesson-section-title">Part 2 Vocabulary Consolidation Practice</div>
        <div>
            Complete the following guided vocabulary consolidation practice. Write the corresponding
            English word or Chinese meaning. New words are practised 6 times each, and personal review
            words are revisited 2 times each.
        </div>
    </div>
    """

    html_parts = [intro_html, '<div class="lesson-table-wrap">']
    html_parts.append(
        """
    <table class="lesson-table">
        <colgroup>
            <col style="width: 4.2%;">
            <col style="width: 15.8%;">
            <col style="width: 13.3%;">
            <col style="width: 4.2%;">
            <col style="width: 15.8%;">
            <col style="width: 13.3%;">
            <col style="width: 4.2%;">
            <col style="width: 15.8%;">
            <col style="width: 13.4%;">
        </colgroup>
        <thead>
            <tr>
                <th>No</th>
                <th>Meaning / Word</th>
                <th>Answer</th>
                <th>No</th>
                <th>Meaning / Word</th>
                <th>Answer</th>
                <th>No</th>
                <th>Meaning / Word</th>
                <th>Answer</th>
            </tr>
        </thead>
        <tbody>
    """
    )

    for row in rows:
        left_no = escape(str(row.get('No', '')))
        left_text = escape(str(row.get('Meaning / Word', '')))
        left_answer = escape(str(row.get('Answer', '')))
        middle_no = escape(str(row.get('No_2', '')))
        middle_text = escape(str(row.get('Meaning / Word_2', '')))
        middle_answer = escape(str(row.get('Answer_2', '')))
        right_no = escape(str(row.get('No_3', '')))
        right_text = escape(str(row.get('Meaning / Word_3', '')))
        right_answer = escape(str(row.get('Answer_3', '')))
        html_parts.append(
            f"""
        <tr>
            <td class="center">{left_no}</td>
            <td>{left_text}</td>
            <td class="answer-cell">{left_answer}</td>
            <td class="center">{middle_no}</td>
            <td>{middle_text}</td>
            <td class="answer-cell">{middle_answer}</td>
            <td class="center">{right_no}</td>
            <td>{right_text}</td>
            <td class="answer-cell">{right_answer}</td>
        </tr>
        """
        )

    html_parts.append("""
        </tbody>
    </table>
    </div>
    """)
    return ''.join(html_parts)


def build_part3_html(passage_text: str, highlight_words):
    clean_text = _remove_part_title_if_needed(passage_text, 'Part 3 Reading Passage')
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', clean_text) if p.strip()]
    if not paragraphs:
        paragraphs = _clean_lines(clean_text)

    paragraph_html = []
    for para in paragraphs:
        paragraph_html.append(f"<p>{_highlight_keywords(para, highlight_words)}</p>")

    return f"""
    <div class="lesson-note-box">
        <div class="lesson-section-title">Part 3 Reading Passage</div>
        <div style="color:#607086; margin-bottom:12px; line-height:1.7;">
            建议学生在阅读时直接在文章旁边标注：生词释义、关键句结构和句子翻译。为了方便批注，正文行距已加大。
        </div>
        <div class="lesson-passage">
            {''.join(paragraph_html)}
        </div>
    </div>
    """


def build_part4_html(part4_text: str):
    parsed = parse_part4_questions_for_display(part4_text)
    html_parts = ['<div class="lesson-note-box">', '<div class="lesson-section-title">Part 4 Questions</div>']
    html_parts.append('<div style="color:#607086; margin-bottom:12px;">题号统一按当前题目顺序从 1 开始编号，便于学生作答与老师讲解。</div>')

    for q in parsed['questions']:
        html_parts.append(f'<div class="lesson-qa-card"><div class="lesson-qa-title">Question {escape(q["display_number"])}.</div>')
        html_parts.append(f'<div style="line-height:1.9; margin-bottom:10px;">{escape(q["stem"])}</div>')
        for option_key in ['A','B','C','D']:
            option_text = escape(q['options'].get(option_key, ''))
            html_parts.append(f'<div style="line-height:1.85; margin:4px 0;"><strong>{option_key}.</strong> {option_text}</div>')
        html_parts.append('</div>')

    if parsed['answer_line']:
        html_parts.append(f'<div class="lesson-subtitle">Answer Key</div><div class="lesson-note-box" style="background:#f8fbff;">{escape(parsed["answer_line"])}</div>')

    html_parts.append('</div>')
    return ''.join(html_parts)


def build_part5_html(part5_text: str):
    items = parse_part5_sentences_for_display(part5_text)
    html_parts = ['<div class="lesson-note-box">', '<div class="lesson-section-title">Part 5 Sentence Translation</div>']
    html_parts.append('<div style="color:#607086; margin-bottom:12px; line-height:1.7;">请先独立完成翻译，再对照 Part 6 查看答案与讲解。每题下方已预留作答区域。</div>')

    for item in items:
        html_parts.append(f'<div class="translation-item"><div class="lesson-qa-title">Sentence {escape(item["display_number"])}.</div>')
        html_parts.append(f'<div class="translation-sentence">{escape(item["sentence"])}</div>')
        for _ in range(item.get('answer_line_count', 3)):
            html_parts.append('<div class="answer-writing-line"></div>')
        html_parts.append('</div>')

    html_parts.append('</div>')
    return ''.join(html_parts)


def _body_to_html_preserve_lines(text: str) -> str:
    cleaned = _clean_teaching_text(text or '')
    safe = escape(cleaned)
    safe = safe.replace('\n', '<br>')
    return f'<div class="lesson-mono">{safe}</div>'


def _clean_teaching_text(text: str) -> str:
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text or '')
    text = text.replace('**', '')
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)
    text = text.replace('---', '')
    return text.strip()


def _is_noise_line(line: str) -> bool:
    stripped = _clean_teaching_text(line).strip()
    return not stripped or stripped in {'*', '**', '-', '---'}


def _strip_list_marker(line: str) -> str:
    return re.sub(r'^\s*\d+\.\s*', '', line).strip()


def _is_micro_heading(line: str) -> bool:
    cleaned = _strip_list_marker(_clean_teaching_text(line))
    return bool(
        re.match(
            r'^(题目问的是|关键词|原文定位|正确答案|我们来对照|参考翻译|原句|句子主干|结构拆分|结构分析|翻译难点|翻译重点|原文片段|中文意思|讲解|为什么难|应该怎么理解)',
            cleaned,
        )
    )


def _format_block_title(title: str, prefix: str) -> str:
    cleaned = re.sub(r'\s+', ' ', _clean_teaching_text(title)).strip()
    return f'{prefix} {cleaned}' if cleaned else prefix


def _block_number(title: str, fallback: int) -> str:
    match = re.search(r'(\d+)', title or '')
    return match.group(1) if match else str(fallback)


def _analysis_lines_to_html(body: str) -> str:
    lines = []
    for raw_line in (body or '').splitlines():
        if _is_noise_line(raw_line):
            continue
        line = _clean_teaching_text(raw_line)
        if not line:
            continue
        css = 'analysis-point heading' if _is_micro_heading(line) else 'analysis-point'
        text = escape(_strip_list_marker(line))
        lines.append(
            f'<div class="{css}"><span class="analysis-dot"></span><span>{text}</span></div>'
        )

    if not lines:
        lines.append('<div class="analysis-point"><span class="analysis-dot"></span><span>暂无可展示的讲解内容。</span></div>')
    return ''.join(lines)


def _analysis_card_html(title: str, body: str, index: int, theme: str = 'blue', prefix: str = 'Question') -> str:
    amber = ' amber' if theme == 'amber' else ''
    badge = escape(_block_number(title, index))
    display_title = escape(_format_block_title(title, prefix))
    return (
        '<div class="analysis-card">'
        f'<div class="analysis-card-header{amber}">'
        f'<span class="analysis-badge{amber}">{badge}</span>'
        f'<span class="analysis-title">{display_title}</span>'
        '</div>'
        f'<div class="analysis-card-body">{_analysis_lines_to_html(body)}</div>'
        '</div>'
    )


def _clean_translation_label(text: str) -> str:
    cleaned = _clean_teaching_text(text)
    return re.sub(r'^第\s*([一二三四五六七八九十]+)\s*段\s*[:：]\s*', '', cleaned).strip()


def build_part6_html(part6_text: str):
    parsed = parse_part6_structure(part6_text)
    html_parts = ['<div class="teaching-shell">']
    html_parts.append(
        '<div class="teaching-hero">'
        '<div class="teaching-hero-title">Part 6 Answer Key & Detailed Teaching Analysis</div>'
        '<div class="teaching-hero-subtitle">先看答案，再按题目和句子分块复盘。每张卡只处理一个学习点，阅读压力会小很多。</div>'
        '</div>'
    )

    html_parts.append('<div class="teaching-band">✓ Reading Answers</div>')
    if parsed['answers']:
        html_parts.append('<div class="answer-grid">')
        for item in parsed['answers']:
            label = f"{item['number']}. {item['answer']}" if item['number'] else item['answer']
            html_parts.append(f'<div class="answer-tile">{escape(label)}</div>')
        html_parts.append('</div>')
    else:
        html_parts.append('<div class="analysis-card"><div class="analysis-card-body">当前未识别到答案区。</div></div>')

    html_parts.append('<div class="teaching-band">◆ Reading Detailed Analysis</div>')
    if parsed['question_blocks']:
        for idx, block in enumerate(parsed['question_blocks'], start=1):
            if _is_noise_line(block.get('title', '')) and _is_noise_line(block.get('body', '')):
                continue
            html_parts.append(_analysis_card_html(block['title'], block['body'], idx, theme='blue', prefix='Question'))
    else:
        html_parts.append('<div class="analysis-card"><div class="analysis-card-body">当前未识别到逐题解析结构，以下为原始内容。</div></div>')
        html_parts.append(_body_to_html_preserve_lines(parsed.get('raw_text', '')))

    html_parts.append('<div class="teaching-band amber">✦ Sentence Translation Detailed Analysis</div>')
    if parsed['sentence_blocks']:
        for idx, block in enumerate(parsed['sentence_blocks'], start=1):
            if _is_noise_line(block.get('title', '')) and _is_noise_line(block.get('body', '')):
                continue
            html_parts.append(_analysis_card_html(block['title'], block['body'], idx, theme='amber', prefix='Sentence'))
    else:
        html_parts.append('<div class="analysis-card"><div class="analysis-card-body">当前未识别到逐句翻译讲解结构。</div></div>')

    html_parts.append('</div>')
    return ''.join(html_parts)


def build_part7_html(part7_text: str):
    parsed = parse_part7_structure(part7_text)
    html_parts = ['<div class="teaching-shell">']
    html_parts.append(
        '<div class="teaching-hero">'
        '<div class="teaching-hero-title">Part 7 Full Passage Translation & Key Language Notes</div>'
        '<div class="teaching-hero-subtitle">先读分段译文，再看语言点卡片。每个 Note 只聚焦一个表达或结构。</div>'
        '</div>'
    )
    html_parts.append('<div class="teaching-band green">◇ Full Passage Translation</div>')
    for idx, para in enumerate(parsed['translation_paragraphs'], start=1):
        cleaned = _clean_translation_label(para)
        if not cleaned:
            continue
        html_parts.append(
            '<div class="translation-card">'
            f'<div class="translation-label">Paragraph {idx}</div>'
            f'<div class="translation-body">{escape(cleaned)}</div>'
            '</div>'
        )
    html_parts.append('<div class="teaching-band amber">★ Key Language Notes</div>')
    for idx, block in enumerate(parsed['note_blocks'], start=1):
        if _is_noise_line(block.get('title', '')) and _is_noise_line(block.get('body', '')):
            continue
        html_parts.append(_analysis_card_html(block['title'], block['body'], idx, theme='amber', prefix='Note'))
    html_parts.append('</div>')
    return ''.join(html_parts)

def build_full_lesson_preview_html(parts: dict):
    html_parts = []
    highlight_words = _extract_part1_words(parts)

    if 'part1' in parts and parts['part1']:
        rows = parse_part1_table(parts['part1'])
        if rows:
            html_parts.append('<h3>Part 1 Key Vocabulary</h3>')
            html_parts.append(build_part1_html_table(rows))

    if 'part1_review' in parts and parts['part1_review']:
        rows = parse_part1_table(parts['part1_review'])
        if rows:
            html_parts.append("<h3 style='margin-top:24px;'>Part 1B Personal Review Words</h3>")
            html_parts.append(build_part1_html_table(rows))

    if 'part2' in parts and parts['part2']:
        rows = parse_part2_to_three_column_rows(parts['part2'])
        if rows:
            html_parts.append("<h3 style='margin-top:24px;'>Part 2 Vocabulary Consolidation Practice</h3>")
            html_parts.append(build_part2_html_table(rows))

    if 'part3' in parts and parts['part3']:
        html_parts.append("<h3 style='margin-top:24px;'>Part 3 Reading Passage</h3>")
        html_parts.append(build_part3_html(parts['part3'], highlight_words))

    if 'part4' in parts and parts['part4']:
        html_parts.append("<h3 style='margin-top:24px;'>Part 4 Questions</h3>")
        html_parts.append(build_part4_html(parts['part4']))

    if 'part5' in parts and parts['part5']:
        html_parts.append("<h3 style='margin-top:24px;'>Part 5 Sentence Translation</h3>")
        html_parts.append(build_part5_html(parts['part5']))

    if 'part6' in parts and parts['part6']:
        html_parts.append("<h3 style='margin-top:24px;'>Part 6 Answer Key & Detailed Teaching Analysis</h3>")
        html_parts.append(build_part6_html(parts['part6']))

    if 'part7' in parts and parts['part7']:
        html_parts.append("<h3 style='margin-top:24px;'>Part 7 Full Passage Translation & Key Language Notes</h3>")
        html_parts.append(build_part7_html(parts['part7']))

    return ''.join(html_parts)

