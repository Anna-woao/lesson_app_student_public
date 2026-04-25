"""
student_diagnosis_service.py

学生端首次诊断 MVP 的题目定义与结果判定。
当前先覆盖四个模块：
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
            "short_title": "词汇",
            "intro": "先用几道基础词汇题确认你当前更适合从哪个词汇难度起步，不追求偏题怪题，只看常见核心词。",
            "focus_points": ["常见高频词义辨认", "基础词汇理解速度", "是否需要先做词汇巩固"],
            "estimated_minutes": 3,
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
                {
                    "id": "vocab_7",
                    "prompt": "prevent 的意思更接近哪一项？",
                    "options": ["阻止", "解释", "发现", "允许"],
                    "answer": "阻止",
                },
                {
                    "id": "vocab_8",
                    "prompt": "effective 的意思更接近哪一项？",
                    "options": ["有效的", "陌生的", "有限的", "重复的"],
                    "answer": "有效的",
                },
            ],
        },
        {
            "key": "reading",
            "title": "阅读理解诊断",
            "short_title": "阅读",
            "intro": "这部分先看你抓主旨、定位细节和理解作者意图的基础能力，不追求篇幅长，只确认阅读起点。",
            "focus_points": ["主旨概括", "细节定位", "句间逻辑理解"],
            "estimated_minutes": 4,
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
                {
                    "id": "reading_4",
                    "prompt": "下列哪项最符合作者的态度？",
                    "options": ["重视持续执行", "只看天赋高低", "反对制定计划", "主张超长时间学习"],
                    "answer": "重视持续执行",
                },
            ],
        },
        {
            "key": "grammar",
            "title": "语法基础诊断",
            "short_title": "语法",
            "intro": "先看常见基础语法点，帮助系统判断你当前最需要补哪一块，重点放在时态、主谓一致和基础句型。",
            "focus_points": ["主谓一致", "基础时态", "条件句和句型稳定性"],
            "estimated_minutes": 3,
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
                {
                    "id": "grammar_5",
                    "prompt": "My parents ____ very busy this week.",
                    "options": ["is", "are", "was", "be"],
                    "answer": "are",
                },
                {
                    "id": "grammar_6",
                    "prompt": "He has lived here ____ three years.",
                    "options": ["in", "for", "at", "since"],
                    "answer": "for",
                },
            ],
        },
        {
            "key": "writing",
            "title": "写作基础诊断",
            "short_title": "写作",
            "intro": "写作部分先从句子表达和结构意识开始，不追求长文，只判断你是否已经具备稳定表达的起点。",
            "focus_points": ["完整句表达", "段落组织意识", "连接词使用"],
            "estimated_minutes": 3,
            "questions": [
                {
                    "id": "writing_1",
                    "prompt": "下面哪一句更适合作为英语作文里的完整句子？",
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
                {
                    "id": "writing_4",
                    "prompt": "下面哪一句更适合作为段落开头句？",
                    "options": [
                        "There are many reasons why regular reading is helpful.",
                        "And that is why.",
                        "Because I think so.",
                        "Very important and useful.",
                    ],
                    "answer": "There are many reasons why regular reading is helpful.",
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


def _build_level_label(ratio: float) -> str:
    if ratio < 0.4:
        return "需要先稳住基础"
    if ratio < 0.75:
        return "已经有基础，可继续提升"
    return "当前基础比较稳，可以进入进阶训练"


def _build_module_report(module_key: str, score: int, total: int) -> Dict[str, Any]:
    ratio = score / total if total else 0

    if module_key == "vocab":
        if ratio < 0.4:
            summary = "常见核心词识别还不够稳定，后续任务需要先用高频词巩固把地基垫稳。"
            recommendation = "先做核心词巩固 + 轻量检测，优先把常见词看熟、用熟。"
        elif ratio < 0.75:
            summary = "基础词汇已经有一定储备，但遇到稍微抽象一点的词还需要继续积累。"
            recommendation = "继续做分层词汇训练，并穿插短测，帮助词义辨认更稳定。"
        else:
            summary = "常见核心词掌握较稳，可以把词汇训练更多放到巩固和迁移使用上。"
            recommendation = "后续可以减少纯识记比例，增加阅读场景里的词汇运用。"
    elif module_key == "reading":
        if ratio < 0.4:
            summary = "主旨和细节抓取都还比较吃力，阅读训练需要先从信息定位和基础理解开始。"
            recommendation = "先做短篇阅读理解训练，重点练主旨句、关键信息和题干定位。"
        elif ratio < 0.75:
            summary = "已经有一定阅读理解能力，但稳定性还不够，细节和逻辑题仍需继续训练。"
            recommendation = "继续做基础到中等难度阅读，边练定位，边练句间逻辑。"
        else:
            summary = "阅读理解基础较稳，已经具备承接更完整阅读任务的能力。"
            recommendation = "可以逐步加入更综合的阅读任务，提升稳定性和速度。"
    elif module_key == "grammar":
        if ratio < 0.4:
            summary = "基础时态和句型还不够稳定，语法练习应先回到核心规则和常见句式。"
            recommendation = "先做基础语法巩固，重点练时态、主谓一致和常见句型。"
        elif ratio < 0.75:
            summary = "语法基础已建立，但在综合运用时仍可能出现不稳定。"
            recommendation = "继续做基础语法训练，并加入小段语境中的句型判断。"
        else:
            summary = "基础语法掌握较稳，可以逐步进入更综合的语法运用训练。"
            recommendation = "后续可以把语法训练和阅读、写作里的真实语境结合起来。"
    else:
        if ratio < 0.4:
            summary = "完整句表达和段落组织意识还比较薄弱，写作训练应先从句子层打底。"
            recommendation = "先做句子表达和连接词训练，再逐步过渡到短段写作。"
        elif ratio < 0.75:
            summary = "已经有基础表达能力，但段落组织和表达稳定性还要继续打磨。"
            recommendation = "继续做句子到短段训练，重点提升结构清晰度和衔接。"
        else:
            summary = "写作基础较稳，已经具备承接更完整表达任务的起点。"
            recommendation = "可以逐步加入更完整的短文表达训练。"

    return {
        "score": score,
        "total": total,
        "ratio": round(ratio, 4),
        "level_label": _build_level_label(ratio),
        "summary": summary,
        "recommendation": recommendation,
    }


def evaluate_initial_diagnosis(module_answers: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
    definition = get_initial_diagnosis_definition()
    scores: Dict[str, int] = {}
    totals: Dict[str, int] = {}
    module_reports: Dict[str, Dict[str, Any]] = {}

    for module in definition:
        key = module["key"]
        score = _score_module(module["questions"], module_answers.get(key, {}))
        total = len(module["questions"])
        scores[key] = score
        totals[key] = total
        module_reports[key] = {
            "title": module["title"],
            "short_title": module.get("short_title", module["title"]),
            **_build_module_report(key, score, total),
        }

    vocab_score = scores["vocab"]
    reading_score = scores["reading"]
    grammar_score = scores["grammar"]
    writing_score = scores["writing"]

    if vocab_score <= 3:
        vocab_band = "当前估计词汇量约 1000-1500"
        title_label = "启程学员"
    elif vocab_score <= 6:
        vocab_band = "当前估计词汇量约 1500-2500"
        title_label = "稳步前进"
    else:
        vocab_band = "当前估计词汇量约 2500-3500"
        title_label = "持续进阶"

    if reading_score <= 1:
        reading_profile = "当前阅读能力画像：能抓到少量明显信息，建议先从基础阅读理解和定位训练开始。"
    elif reading_score <= 3:
        reading_profile = "当前阅读能力画像：已经具备基础理解能力，适合进入稳步提升训练。"
    else:
        reading_profile = "当前阅读能力画像：能较稳定抓住主旨和细节，可以逐步挑战更综合的阅读任务。"

    if grammar_score <= 2:
        grammar_gap = "当前语法基础缺口：时态、主谓一致和基础句型还需要重点巩固。"
    elif grammar_score <= 4:
        grammar_gap = "当前语法基础缺口：基础语法已建立，但句型稳定性还需要继续练习。"
    else:
        grammar_gap = "当前语法基础缺口：基础语法比较稳，可以逐步进入综合运用。"

    if writing_score <= 1:
        writing_profile = "当前写作基础：更适合先从完整句表达和连接词使用开始。"
    elif writing_score <= 3:
        writing_profile = "当前写作基础：已能组织基础表达，下一步适合强化段落结构。"
    else:
        writing_profile = "当前写作基础：具备基础结构意识，可以开始承接更完整的表达训练。"

    priority_module = min(module_reports, key=lambda key: (module_reports[key]["ratio"], module_reports[key]["score"]))
    strongest_module = max(module_reports, key=lambda key: (module_reports[key]["ratio"], module_reports[key]["score"]))

    suggested_track_map = {
        "vocab": "建议进入的学习轨道：先从词汇巩固与轻量检测开始。",
        "reading": "建议进入的学习轨道：先从基础阅读理解与信息定位训练开始。",
        "grammar": "建议进入的学习轨道：先从核心语法与句型稳定训练开始。",
        "writing": "建议进入的学习轨道：先从句子表达与短段写作训练开始。",
    }
    growth_focus_map = {
        "vocab": "当前成长重点：先把常见核心词认稳、用稳。",
        "reading": "当前成长重点：先把主旨和关键信息读出来。",
        "grammar": "当前成长重点：先把基础时态和句型搭稳。",
        "writing": "当前成长重点：先把完整句和连接表达写顺。",
    }

    average_ratio = sum(scores.values()) / max(sum(totals.values()), 1)
    if average_ratio < 0.45:
        stage_label = "准备起步"
        overall_summary = "你现在最需要的是先建立稳定的基础节奏，不必急着做太难的综合任务。"
    elif average_ratio < 0.75:
        stage_label = "稳步提升"
        overall_summary = "你已经具备基础起点，接下来重点是把已有能力练得更稳、更连续。"
    else:
        stage_label = "持续进阶"
        overall_summary = "你的基础已经比较稳，可以开始承接更完整的综合训练。"

    next_actions = [
        growth_focus_map[priority_module],
        suggested_track_map[priority_module],
        f"当前相对更稳的模块是“{module_reports[strongest_module]['short_title']}”，可以把它作为保持信心的支撑点。",
    ]

    summary_text = " ".join([
        overall_summary,
        vocab_band,
        reading_profile,
        grammar_gap,
        writing_profile,
    ])

    return {
        "scores": scores,
        "totals": totals,
        "module_reports": module_reports,
        "priority_module": priority_module,
        "strongest_module": strongest_module,
        "overall_accuracy": round(average_ratio, 4),
        "overall_summary": overall_summary,
        "vocab_band": vocab_band,
        "reading_profile": reading_profile,
        "grammar_gap": grammar_gap,
        "writing_profile": writing_profile,
        "suggested_track": suggested_track_map[priority_module],
        "growth_focus": growth_focus_map[priority_module],
        "title_label": title_label,
        "stage_label": stage_label,
        "summary_text": summary_text,
        "next_actions": next_actions,
        "dimensions": {
            "词汇储备": module_reports["vocab"]["summary"],
            "阅读理解": module_reports["reading"]["summary"],
            "语法掌握": module_reports["grammar"]["summary"],
            "写作表达": module_reports["writing"]["summary"],
            "实战发挥": overall_summary,
            "学习执行力": "当前先以能稳定完成每日任务为主要观察点，后续会根据训练完成情况继续更新。",
        },
    }
