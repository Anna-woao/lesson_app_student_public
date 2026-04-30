from __future__ import annotations

from datetime import datetime


def format_progress_status_copy(status: str) -> tuple[str, str]:
    mapping = {
        "learning": ("正在学习", "这些词刚进入你的学习进度，先把它们认熟、看稳。"),
        "review": ("进入复习", "这些词已经学过一轮，接下来会按节奏反复巩固。"),
        "mastered": ("阶段掌握", "这些词当前表现稳定，可以先继续往下推进。"),
    }
    return mapping.get(status or "learning", mapping["learning"])


def format_next_review_time(next_review_time: str | None) -> str:
    if not next_review_time:
        return "暂未安排下次复习"
    try:
        normalized = str(next_review_time).replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        return f"建议复习：{dt.strftime('%m-%d %H:%M')}"
    except Exception:
        return f"建议复习：{next_review_time}"


def build_test_result_summary(result: dict) -> tuple[str, str]:
    source_type = result.get("source_type")
    test_type = result.get("test_type")
    accuracy = float(result.get("accuracy") or 0)

    if source_type == "progress" and test_type == "新词检测":
        title = "新词摸底已经完成"
        if accuracy >= 0.8:
            desc = "这批新词里你已经会了不少，可以把更多精力放到还不稳的词上。"
        elif accuracy >= 0.5:
            desc = "你已经有一部分基础，接下来适合把没答稳的词继续推进到学习进度里。"
        else:
            desc = "这批词还比较陌生，先按系统安排逐步学习会更稳。"
        return title, desc

    if source_type == "progress" and test_type == "复习检测":
        title = "已学词复习已经完成"
        if accuracy >= 0.8:
            desc = "你对这批已学词保持得不错，可以继续扩大自己的稳定词汇量。"
        elif accuracy >= 0.5:
            desc = "这批词有些已经稳住了，也有一些需要继续回看，系统会同步调整复习节奏。"
        else:
            desc = "这批已学词里还有不少需要回炉，先把这些词重新巩固一轮会更合适。"
        return title, desc

    if source_type == "book":
        title = "词汇书抽词检测已经完成"
        if accuracy >= 0.8:
            desc = "你对当前词汇书的掌握不错，可以继续往后推进新的内容。"
        elif accuracy >= 0.5:
            desc = "当前词汇书有一部分已经掌握，接下来继续推进和复习会更有效。"
        else:
            desc = "当前词汇书里还有不少词没答稳，先把这一轮基础打牢会更好。"
        return title, desc

    return "本轮检测已完成", "系统已经根据这次作答更新了你的词汇学习状态。"
