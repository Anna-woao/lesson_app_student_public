"""
student_diagnosis_service.py

学生端首次诊断 MVP 的题目定义与结果判定。
当前先做四个模块：
- 词汇
- 阅读
- 语法基础
- 写作基础
"""

from __future__ import annotations

from typing import Any, Dict, List


def get_initial_diagnosis_definition() -> List[Dict[str, Any]]:
    return [
        {
            "key": "vocab",
            "title": "词汇基础诊断",
            "intro": "先用几道轻量词汇题，帮助系统判断你目前更适合从哪个词汇难度开始。",
            "questions": [
                {
                    "id": "vocab_1",
                    "prompt": "challenge 的意思更接近哪一项？",
                    "options": ["挑战", "安静", "地图", "节日"],
                    "answer": "挑战",
                },
                {
                    "id": "vocab_2",
                    "prompt": "improve 的意思更接近哪一项？",
                    "options": ["忘记", "提高", "等待", "搬运"],
                    "answer": "提高",
                },
                {
                    "id": "vocab_3",
                    "prompt": "available 的意思更接近哪一项？",
                    "options": ["可获得的", "昂贵的", "危险的", "传统的"],
                    "answer": "可获得的",
                },
                {
                    "id": "vocab_4",
                    "prompt": "ancient 的意思更接近哪一项？",
                    "options": ["现代的", "古老的", "潮湿的", "友好的"],
                    "answer": "古老的",
                },
                {
                    "id": "vocab_5",
                    "prompt": "solution 的意思更接近哪一项？",
                    "options": ["办法", "消息", "习惯", "争论"],
                    "answer": "办法",
                },
                {
                    "id": "vocab_6",
                    "prompt": "confident 的意思更接近哪一项？",
                    "options": ["疲惫的", "自信的", "拥挤的", "严格的"],
                    "answer": "自信的",
                },
            ],
        },
        {
            "key": "reading",
            "title": "阅读理解诊断",
            "intro": "这一小段阅读主要看你获取信息、概括主旨和理解细节的能力。",
            "passage": (
                "Many students think progress only comes from long hours of study. "
                "In fact, short but focused practice often works better. "
                "When learners review key ideas regularly, they remember more and feel less stressed. "
                "That is why a simple daily plan can be more useful than a perfect plan that is never followed."
            ),
            "questions": [
                {
                    "id": "reading_1",
                    "prompt": "这段文字最主要想说明什么？",
                    "options": [
                        "学习时间越长越有效",
                        "短而专注的练习常常更有效",
                        "学生应该放弃日常计划",
                        "压力能帮助学生记忆",
                    ],
                    "answer": "短而专注的练习常常更有效",
                },
                {
                    "id": "reading_2",
                    "prompt": "作者为什么提到 daily plan？",
                    "options": [
                        "为了说明简单且能坚持的计划更有用",
                        "为了比较不同学校的课程",
                        "为了介绍新的考试制度",
                        "为了提醒学生早点睡觉",
                    ],
                    "answer": "为了说明简单且能坚持的计划更有用",
                },
                {
                    "id": "reading_3",
                    "prompt": "根据文章，regular review 可能带来什么结果？",
                    "options": [
                        "记得更多，也更轻松",
                        "作业会立刻消失",
                        "阅读速度一定翻倍",
                        "不再需要老师帮助",
                    ],
                    "answer": "记得更多，也更轻松",
                },
            ],
        },
        {
            "key": "grammar",
            "title": "语法基础诊断",
            "intro": "这部分先看常见基础语法点，帮助系统判断你目前最需要补哪一块。",
            "questions": [
                {
                    "id": "grammar_1",
                    "prompt": "She ____ to school every day.",
                    "options": ["go", "goes", "going", "gone"],
                    "answer": "goes",
                },
                {
                    "id": "grammar_2",
                    "prompt": "Yesterday we ____ a movie after dinner.",
                    "options": ["watch", "watches", "watched", "watching"],
                    "answer": "watched",
                },
                {
                    "id": "grammar_3",
                    "prompt": "If it rains tomorrow, we ____ at home.",
                    "options": ["stay", "stays", "will stay", "stayed"],
                    "answer": "will stay",
                },
                {
                    "id": "grammar_4",
                    "prompt": "The book ____ on the desk is mine.",
                    "options": ["is", "are", "was", "were"],
                    "answer": "is",
                },
            ],
        },
        {
            "key": "writing",
            "title": "写作基础诊断",
            "intro": "写作基础先从句子表达和结构意识开始，不追求长文，只判断当前起点。",
            "questions": [
                {
                    "id": "writing_1",
                    "prompt": "下面哪一句更适合作为英语作文的完整句子？",
                    "options": [
                        "Because I was tired.",
                        "I was tired, so I went to bed early.",
                        "And very tired.",
                        "Went to bed early because.",
                    ],
                    "answer": "I was tired, so I went to bed early.",
                },
                {
                    "id": "writing_2",
                    "prompt": "写一段英语短文时，哪种顺序通常更清楚？",
                    "options": [
                        "想到哪写到哪",
                        "先中心句，再补充细节",
                        "只列单词，不写句子",
                        "每句都换主题",
                    ],
                    "answer": "先中心句，再补充细节",
                },
                {
                    "id": "writing_3",
                    "prompt": "如果想让句子连接更自然，下面哪类词更有帮助？",
                    "options": ["连接词", "感叹词", "缩写词", "专有名词"],
                    "answer": "连接词",
                },
            ],
        },
    ]


def _score_module(questions: List[Dict[str, Any]], answers: Dict[str, str]) -> int:
    score = 0
    for question in questions:
        if (answers.get(question["id"]) or "").strip() == question["answer"]:
            score += 1
    return score


def evaluate_initial_diagnosis(module_answers: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
    definition = get_initial_diagnosis_definition()
    scores: Dict[str, int] = {}
    totals: Dict[str, int] = {}

    for module in definition:
        key = module["key"]
        scores[key] = _score_module(module["questions"], module_answers.get(key, {}))
        totals[key] = len(module["questions"])

    vocab_score = scores["vocab"]
    reading_score = scores["reading"]
    grammar_score = scores["grammar"]
    writing_score = scores["writing"]

    if vocab_score <= 2:
        vocab_band = "当前估计词汇量约 1000-1500"
        title_label = "启程学员"
    elif vocab_score <= 4:
        vocab_band = "当前估计词汇量约 1500-2500"
        title_label = "稳步前进"
    else:
        vocab_band = "当前估计词汇量约 2500-3500"
        title_label = "持续进阶"

    if reading_score <= 1:
        reading_profile = "当前阅读能力画像：可以抓住部分明显信息，适合先做基础理解训练。"
    elif reading_score == 2:
        reading_profile = "当前阅读能力画像：已经具备基础理解能力，适合进入稳步提升训练。"
    else:
        reading_profile = "当前阅读能力画像：能较稳定抓住主旨和细节，可以逐步挑战更综合的阅读任务。"

    if grammar_score <= 1:
        grammar_gap = "当前语法基础缺口：时态与基础句型还需要重点巩固。"
    elif grammar_score == 2:
        grammar_gap = "当前语法基础缺口：基础语法已建立，但在句型稳定性上还需要练习。"
    else:
        grammar_gap = "当前语法基础缺口：基础语法较稳，可以逐步进入综合运用。"

    if writing_score <= 1:
        writing_profile = "当前写作基础：更适合先从完整句表达与连接词使用开始。"
    elif writing_score == 2:
        writing_profile = "当前写作基础：已经能组织基础表达，下一步适合强化段落结构。"
    else:
        writing_profile = "当前写作基础：具备基本结构意识，可以开始做更完整的表达训练。"

    lowest_module = min(scores, key=scores.get)
    suggested_track_map = {
        "vocab": "建议进入的学习轨道：先从词汇巩固与轻量检测开始。",
        "reading": "建议进入的学习轨道：先从基础阅读理解与信息定位训练开始。",
        "grammar": "建议进入的学习轨道：先从核心语法与句型稳定训练开始。",
        "writing": "建议进入的学习轨道：先从句子表达与短段写作训练开始。",
    }
    growth_focus_map = {
        "vocab": "当前成长重点：先把常见核心词汇认稳、用稳。",
        "reading": "当前成长重点：先把主旨和关键信息读出来。",
        "grammar": "当前成长重点：先把基础时态和句型搭稳。",
        "writing": "当前成长重点：先把完整句和连接表达写顺。",
    }

    average_ratio = sum(scores.values()) / max(sum(totals.values()), 1)
    if average_ratio < 0.45:
        stage_label = "准备起步"
    elif average_ratio < 0.75:
        stage_label = "稳步提升"
    else:
        stage_label = "持续进阶"

    summary_text = " ".join([
        vocab_band,
        reading_profile,
        grammar_gap,
        writing_profile,
        suggested_track_map[lowest_module],
    ])

    return {
        "scores": scores,
        "totals": totals,
        "vocab_band": vocab_band,
        "reading_profile": reading_profile,
        "grammar_gap": grammar_gap,
        "writing_profile": writing_profile,
        "suggested_track": suggested_track_map[lowest_module],
        "growth_focus": growth_focus_map[lowest_module],
        "title_label": title_label,
        "stage_label": stage_label,
        "summary_text": summary_text,
        "dimensions": {
            "词汇储备": vocab_band,
            "阅读理解": reading_profile,
            "语法掌握": grammar_gap,
            "写作表达": writing_profile,
            "实战发挥": suggested_track_map[lowest_module],
            "学习执行力": "当前先以能稳定完成每日任务为主要观察点。",
        },
    }
