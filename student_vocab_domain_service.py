"""Vocabulary domain rules shared by student-side test flows."""

from __future__ import annotations

import random
import re
import unicodedata
from typing import Any


UNCERTAIN_OPTION = "我不确定"
MIXED_TEST_MODE = "混合模式"
EN_TO_ZH_MODE = "英译中"
ZH_TO_EN_MODE = "中译英"

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
_POS_TOKEN_PATTERN = "|".join(
    re.escape(token) for token in sorted(_POS_ALIASES, key=len, reverse=True)
)
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
_POS_SEPARATORS = " \t\r\n.&/\\-:,;，；、:："
_SPACED_POS_FIXES = (
    (re.compile(r"con\s+j\.", re.IGNORECASE), "conj."),
    (re.compile(r"ad\s+v\.", re.IGNORECASE), "adv."),
    (re.compile(r"ad\s+j\.", re.IGNORECASE), "adj."),
)


def student_display_meaning(raw_meaning: str) -> str:
    text = str(raw_meaning or "").strip()
    if not text:
        return ""

    for pattern, replacement in _SPACED_POS_FIXES:
        text = pattern.sub(replacement, text)

    while text:
        match = _POS_PREFIX_PATTERN.match(text)
        if not match:
            break
        text = text[match.end() :].lstrip(_POS_SEPARATORS)

    text = _POS_ANY_PATTERN.sub(" ", text)
    text = text.replace("&", " ")
    text = re.sub(r"[，；、]\s*[，；、]+", "，", text)
    text = re.sub(r"\s+", " ", text).strip(_POS_SEPARATORS)
    return text or str(raw_meaning or "").strip()


def build_questions_from_vocab_rows(
    vocab_map: dict[int, tuple[str, str]],
    rows: list[dict[str, Any]],
    test_mode: str,
) -> list[dict[str, Any]]:
    all_meanings: list[str] = []
    for _, raw_meaning in vocab_map.values():
        display_meaning = student_display_meaning(raw_meaning)
        if display_meaning and display_meaning not in all_meanings:
            all_meanings.append(display_meaning)

    questions: list[dict[str, Any]] = []
    for row in rows:
        vocab_item_id = row.get("vocab_item_id")
        word, raw_meaning = vocab_map.get(vocab_item_id, ("", ""))
        if not word:
            continue

        meaning = student_display_meaning(raw_meaning)
        if not meaning:
            continue

        one_mode = (
            random.choice([EN_TO_ZH_MODE, ZH_TO_EN_MODE])
            if test_mode == MIXED_TEST_MODE
            else test_mode
        )
        question = {
            "vocab_item_id": vocab_item_id,
            "word": word,
            "meaning": meaning,
            "raw_meaning": raw_meaning,
            "mode": one_mode,
            "source_book_id": row.get("book_id") or row.get("first_source_book_id"),
            "source_unit_id": row.get("unit_id") or row.get("first_source_unit_id"),
        }

        if one_mode == EN_TO_ZH_MODE:
            distractors = [item for item in all_meanings if item and item != meaning]
            random.shuffle(distractors)
            options = [meaning] + distractors[:3]
            options = list(dict.fromkeys(options))
            random.shuffle(options)
            options.append(UNCERTAIN_OPTION)
            question["options"] = options

        questions.append(question)
    return questions


def normalize_test_mode(mode: str) -> str:
    normalized = str(mode or "").strip()
    if normalized == EN_TO_ZH_MODE:
        return EN_TO_ZH_MODE
    if normalized == ZH_TO_EN_MODE:
        return ZH_TO_EN_MODE
    return normalized


def normalize_vocab_answer_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(text or ""))
    normalized = normalized.strip().casefold()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = normalized.strip(
        ".,;:!?\"'()[]{}<>`~，。；：！？“”‘’（）【】《》"
    )
    return normalized


def grade_vocab_test_answer(question: dict[str, Any], user_answer: str) -> tuple[bool, bool]:
    mode = normalize_test_mode(question.get("mode"))
    raw_answer = str(user_answer or "").strip()
    normalized_answer = normalize_vocab_answer_text(raw_answer)
    is_uncertain = normalized_answer == normalize_vocab_answer_text(UNCERTAIN_OPTION)

    if mode == EN_TO_ZH_MODE:
        expected_answer = normalize_vocab_answer_text(question.get("meaning") or "")
        is_correct = (not is_uncertain) and normalized_answer == expected_answer
        return is_correct, is_uncertain

    expected_word = normalize_vocab_answer_text(question.get("word") or "")
    is_correct = normalized_answer == expected_word
    return is_correct, is_uncertain
