"""
student_diagnosis_service.py

学生端首次诊断定义与结果判定。
当前版本将词汇模块切换为 Supabase 题库驱动，其余模块仍保持轻量静态题。
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List


LEVEL_DISPLAY = {
    "L1": "L1 超基础生存词",
    "L2": "L2 初中基础高频词",
    "L3": "L3 高中核心 / 高考阅读高频词",
    "L4": "L4 中高频抽象词 / 说明文科普文词",
    "L5": "L5 熟词生义 / 易混词",
}

UNCERTAIN_OPTION = "\u4e0d\u786e\u5b9a"


STATIC_NON_VOCAB_MODULES: List[Dict[str, Any]] = [
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


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _compute_ratio(correct_count: int, total_count: int) -> float:
    if total_count <= 0:
        return 0.0
    return round(correct_count / total_count, 4)


def _score_module(questions: List[Dict[str, Any]], answers: Dict[str, str]) -> int:
    score = 0
    for question in questions:
        if _safe_text(answers.get(question["id"])) == _safe_text(question["answer"]):
            score += 1
    return score


def _build_level_label(ratio: float) -> str:
    if ratio < 0.4:
        return "需要先稳住基础"
    if ratio < 0.75:
        return "已经有基础，可以继续提升"
    return "当前基础比较稳，可以进入进阶训练"


def _build_regular_module_report(module_key: str, score: int, total: int) -> Dict[str, Any]:
    ratio = _compute_ratio(score, total)

    if module_key == "reading":
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
        "ratio": ratio,
        "level_label": _build_level_label(ratio),
        "summary": summary,
        "recommendation": recommendation,
    }


def _build_vocab_module(vocab_questions: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not vocab_questions:
        raise ValueError("首次诊断词汇题库为空，无法生成正式词汇诊断模块。")

    level_counter = Counter(_safe_text(question.get("level")) for question in vocab_questions)
    level_summary = " / ".join(
        f"{level} {level_counter.get(level, 0)} 题"
        for level in ["L1", "L2", "L3", "L4", "L5"]
        if level_counter.get(level, 0)
    )

    questions = []
    for question in vocab_questions:
        item_id = _safe_text(question.get("item_id"))
        prompt = _safe_text(question.get("question_text"))
        options = list(question.get("options") or [])
        answer = _safe_text(question.get("correct_answer"))
        if not item_id or not prompt or not options or not answer:
            raise ValueError(f"题库题目缺少关键字段，无法进入正式诊断：{item_id or 'unknown_item'}")
        questions.append(
            {
                "id": item_id,
                "prompt": prompt,
                "options": options,
                "answer": answer,
                "level": _safe_text(question.get("level")),
                "word": _safe_text(question.get("word")),
                "question_type": _safe_text(question.get("question_type")),
                "diagnostic_tag": _safe_text(question.get("diagnostic_tag")),
                "diagnostic_value": _safe_text(question.get("diagnostic_value")),
                "sentence": _safe_text(question.get("sentence")),
                "explanation": _safe_text(question.get("explanation")),
                "primary_meaning_zh": _safe_text(question.get("primary_meaning_zh")),
                "version": _safe_text(question.get("version")),
                "has_uncertain_option": bool(question.get("has_uncertain_option")),
            }
        )

    return {
        "key": "vocab",
        "title": "词汇基础诊断",
        "short_title": "词汇",
        "intro": "这部分会按 L1-L5 分层抽题，帮助系统判断你的词汇训练起点。题目来自正式首次诊断题库，不是临时静态样题。",
        "focus_points": ["高频词义辨认", "阅读高频词理解", "熟词生义与易混词辨析"],
        "estimated_minutes": 12,
        "question_count_summary": level_summary,
        "questions": questions,
    }


def build_initial_diagnosis_definition(vocab_questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [_build_vocab_module(vocab_questions), *STATIC_NON_VOCAB_MODULES]


def get_initial_diagnosis_definition(vocab_questions: List[Dict[str, Any]] | None = None) -> List[Dict[str, Any]]:
    if vocab_questions is None:
        raise ValueError("首次诊断词汇题库未加载，不能再回退到旧静态词汇题。")
    return build_initial_diagnosis_definition(vocab_questions)


def _build_vocab_diagnostic_result(questions: List[Dict[str, Any]], answers: Dict[str, str]) -> Dict[str, Any]:
    total_count = len(questions)
    correct_count = 0
    uncertain_count = 0

    level_totals = Counter()
    level_correct = Counter()
    question_type_totals = Counter()
    question_type_correct = Counter()

    for question in questions:
        item_id = question["id"]
        level = _safe_text(question.get("level"))
        question_type = _safe_text(question.get("question_type"))
        selected_answer = _safe_text(answers.get(item_id))
        correct_answer = _safe_text(question.get("answer"))

        level_totals[level] += 1
        question_type_totals[question_type] += 1

        if selected_answer == UNCERTAIN_OPTION:
            uncertain_count += 1
        if selected_answer == correct_answer:
            correct_count += 1
            level_correct[level] += 1
            question_type_correct[question_type] += 1

    level_accuracy_map = {
        level: _compute_ratio(level_correct[level], level_totals[level])
        for level in ["L1", "L2", "L3", "L4", "L5"]
        if level_totals[level]
    }
    question_type_accuracy_map = {
        key: _compute_ratio(question_type_correct[key], question_type_totals[key])
        for key in question_type_totals
    }

    high_frequency_total = level_totals["L1"] + level_totals["L2"]
    high_frequency_correct = level_correct["L1"] + level_correct["L2"]
    reading_vocab_total = level_totals["L3"] + level_totals["L4"]
    reading_vocab_correct = level_correct["L3"] + level_correct["L4"]

    high_frequency_accuracy = _compute_ratio(high_frequency_correct, high_frequency_total)
    reading_vocab_accuracy = _compute_ratio(reading_vocab_correct, reading_vocab_total)
    polysemy_accuracy = _compute_ratio(
        question_type_correct["polysemy_context"],
        question_type_totals["polysemy_context"],
    )
    confusable_accuracy = _compute_ratio(
        question_type_correct["confusable_choice"],
        question_type_totals["confusable_choice"],
    )
    uncertain_rate = _compute_ratio(uncertain_count, total_count)
    overall_accuracy = _compute_ratio(correct_count, total_count)

    if level_accuracy_map.get("L1", 0.0) < 0.6:
        estimated_vocab_range = "预计词汇量区间：0-800"
        vocab_level_label = "起步夯基"
        recommended_training_start = LEVEL_DISPLAY["L1"]
    elif level_accuracy_map.get("L2", 0.0) < 0.6:
        estimated_vocab_range = "预计词汇量区间：800-1500"
        vocab_level_label = "基础过渡"
        recommended_training_start = LEVEL_DISPLAY["L2"]
    elif level_accuracy_map.get("L3", 0.0) < 0.55:
        estimated_vocab_range = "预计词汇量区间：1500-2500"
        vocab_level_label = "中阶起点"
        recommended_training_start = LEVEL_DISPLAY["L3"]
    elif level_accuracy_map.get("L4", 0.0) < 0.5:
        estimated_vocab_range = "预计词汇量区间：2500-3500"
        vocab_level_label = "阅读进阶"
        recommended_training_start = LEVEL_DISPLAY["L4"]
    elif level_accuracy_map.get("L5", 0.0) < 0.45:
        estimated_vocab_range = "预计词汇量区间：3500-4500"
        vocab_level_label = "高阶过渡"
        recommended_training_start = LEVEL_DISPLAY["L5"]
    else:
        estimated_vocab_range = "预计词汇量区间：4500+"
        vocab_level_label = "高阶稳定"
        recommended_training_start = "L5 熟词生义与易混词精炼训练"

    if uncertain_rate >= 0.2:
        main_vocab_problem = "词义判断不够确定，说明词汇识别稳定性不足"
    elif question_type_totals["polysemy_context"] and polysemy_accuracy < 0.5:
        main_vocab_problem = "熟词生义语境判断偏弱"
    elif question_type_totals["confusable_choice"] and confusable_accuracy < 0.5:
        main_vocab_problem = "易混词辨析偏弱"
    elif high_frequency_total and high_frequency_accuracy < 0.65:
        main_vocab_problem = "高频核心词掌握还不够稳"
    elif reading_vocab_total and reading_vocab_accuracy < 0.6:
        main_vocab_problem = "阅读高频词储备不足"
    else:
        main_vocab_problem = "需要继续巩固跨层级迁移和细粒度辨义"

    level_breakdown = " / ".join(
        f"{level} {level_correct[level]}/{level_totals[level]}"
        for level in ["L1", "L2", "L3", "L4", "L5"]
        if level_totals[level]
    )
    strengths = []
    risk_flags = []
    recommended_actions = []

    if high_frequency_total and high_frequency_accuracy >= 0.8:
        strengths.append("高频核心词识别比较稳定")
    if reading_vocab_total and reading_vocab_accuracy >= 0.7:
        strengths.append("阅读高频词具备一定储备")
    if question_type_totals["confusable_choice"] and confusable_accuracy >= 0.7:
        strengths.append("易混词辨析表现较稳")
    if question_type_totals["polysemy_context"] and polysemy_accuracy >= 0.6:
        strengths.append("熟词生义语境判断已有基础")
    if uncertain_rate <= 0.08:
        strengths.append("答题确定性较高")

    if not strengths:
        strengths.append("基础识别能力已经建立，但还需要继续拉开层级差异")

    if uncertain_rate >= 0.2:
        risk_flags.append("不确定选项使用偏多，说明词义判断稳定性不足")
        recommended_actions.append("先从高频词短测和错题回看开始，减少看到词但不敢判断的情况")
    if high_frequency_total and high_frequency_accuracy < 0.65:
        risk_flags.append("L1-L2 高频核心词掌握还不够稳")
        recommended_actions.append("优先回到 L1-L2 高频词巩固，先稳住基础词义识别")
    if reading_vocab_total and reading_vocab_accuracy < 0.6:
        risk_flags.append("L3-L4 阅读高频词储备不足")
        recommended_actions.append("增加阅读高频词的语境辨义训练，避免只会孤立记词")
    if question_type_totals["polysemy_context"] and polysemy_accuracy < 0.5:
        risk_flags.append("熟词生义题型偏弱")
        recommended_actions.append("后续训练里单独加入熟词生义语境判断题")
    if question_type_totals["confusable_choice"] and confusable_accuracy < 0.5:
        risk_flags.append("易混词辨析偏弱")
        recommended_actions.append("后续训练里补充近形近义词辨析，减少混淆性错误")

    if not recommended_actions:
        recommended_actions.append("可以从当前推荐层级继续做分层巩固，并逐步提高阅读场景迁移比例")

    if not risk_flags:
        risk_flags.append("当前没有明显单点塌陷，更需要继续扩大词汇覆盖面和迁移使用")

    profile_summary = (
        f"词汇题共答对 {correct_count}/{total_count}，"
        f"高频核心词正确率 {round(high_frequency_accuracy * 100)}%，"
        f"阅读词汇正确率 {round(reading_vocab_accuracy * 100)}%，"
        f"不确定占比 {round(uncertain_rate * 100)}%。"
    )
    summary = (
        f"本轮词汇诊断共答对 {correct_count}/{total_count}，"
        f"分层表现为 {level_breakdown}。"
        f" 不确定选项使用率为 {round(uncertain_rate * 100)}%。"
    )
    recommendation = f"建议从“{recommended_training_start}”开始，优先解决“{main_vocab_problem}”。"

    return {
        "correct_count": correct_count,
        "total_scored_items": total_count,
        "overall_accuracy": overall_accuracy,
        "l1_accuracy": level_accuracy_map.get("L1", 0.0),
        "l2_accuracy": level_accuracy_map.get("L2", 0.0),
        "l3_accuracy": level_accuracy_map.get("L3", 0.0),
        "l4_accuracy": level_accuracy_map.get("L4", 0.0),
        "l5_accuracy": level_accuracy_map.get("L5", 0.0),
        "high_frequency_accuracy": high_frequency_accuracy,
        "reading_vocab_accuracy": reading_vocab_accuracy,
        "polysemy_accuracy": polysemy_accuracy,
        "confusable_accuracy": confusable_accuracy,
        "uncertain_rate": uncertain_rate,
        "estimated_vocab_range": estimated_vocab_range,
        "vocab_level_label": vocab_level_label,
        "main_vocab_problem": main_vocab_problem,
        "recommended_training_start": recommended_training_start,
        "level_accuracy_map": level_accuracy_map,
        "question_type_accuracy_map": question_type_accuracy_map,
        "level_correct_counts": dict(level_correct),
        "level_total_counts": dict(level_totals),
        "question_type_correct_counts": dict(question_type_correct),
        "question_type_total_counts": dict(question_type_totals),
        "strengths": strengths,
        "risk_flags": risk_flags,
        "recommended_actions": recommended_actions,
        "profile_summary": profile_summary,
        "module_report": {
            "score": correct_count,
            "total": total_count,
            "ratio": overall_accuracy,
            "level_label": vocab_level_label,
            "summary": summary,
            "recommendation": recommendation,
            "uncertain_rate": uncertain_rate,
            "estimated_vocab_range": estimated_vocab_range,
            "recommended_training_start": recommended_training_start,
            "main_vocab_problem": main_vocab_problem,
            "level_accuracy_map": level_accuracy_map,
            "question_type_accuracy_map": question_type_accuracy_map,
            "profile_summary": profile_summary,
        },
    }


def evaluate_initial_diagnosis(
    module_answers: Dict[str, Dict[str, str]],
    definition: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    if definition is None:
        raise ValueError("首次诊断定义未加载，无法计算正式诊断结果。")

    scores: Dict[str, int] = {}
    totals: Dict[str, int] = {}
    module_reports: Dict[str, Dict[str, Any]] = {}
    vocab_result: Dict[str, Any] | None = None

    for module in definition:
        key = module["key"]
        answers = module_answers.get(key, {})
        if key == "vocab":
            vocab_result = _build_vocab_diagnostic_result(module["questions"], answers)
            scores[key] = vocab_result["correct_count"]
            totals[key] = vocab_result["total_scored_items"]
            module_reports[key] = {
                "title": module["title"],
                "short_title": module.get("short_title", module["title"]),
                **vocab_result["module_report"],
            }
            continue

        score = _score_module(module["questions"], answers)
        total = len(module["questions"])
        scores[key] = score
        totals[key] = total
        module_reports[key] = {
            "title": module["title"],
            "short_title": module.get("short_title", module["title"]),
            **_build_regular_module_report(key, score, total),
        }

    if vocab_result is None:
        raise ValueError("首次诊断结果缺少词汇模块，无法继续。")

    reading_score = scores.get("reading", 0)
    grammar_score = scores.get("grammar", 0)
    writing_score = scores.get("writing", 0)

    vocab_band = vocab_result["estimated_vocab_range"]
    title_label = vocab_result["vocab_level_label"]

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
        "vocab": f"建议进入的学习轨道：先从 {vocab_result['recommended_training_start']} 开始，做分层词汇巩固与短测。",
        "reading": "建议进入的学习轨道：先从基础阅读理解与信息定位训练开始。",
        "grammar": "建议进入的学习轨道：先从核心语法与句型稳定训练开始。",
        "writing": "建议进入的学习轨道：先从句子表达与短段写作训练开始。",
    }
    growth_focus_map = {
        "vocab": f"当前成长重点：{vocab_result['main_vocab_problem']}。",
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
        f"词汇诊断建议起点：{vocab_result['recommended_training_start']}。",
        f"当前相对更稳的模块是“{module_reports[strongest_module]['short_title']}”，可以把它作为保持信心的支撑点。",
    ]

    summary_text = " ".join(
        [
            overall_summary,
            vocab_band,
            f"词汇问题重点：{vocab_result['main_vocab_problem']}。",
            reading_profile,
            grammar_gap,
            writing_profile,
        ]
    )

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
        "vocab_profile_summary": vocab_result.get("profile_summary", ""),
        "vocab_diagnostic_result": vocab_result,
        "dimensions": {
            "词汇储备": module_reports["vocab"]["summary"],
            "阅读理解": module_reports["reading"]["summary"],
            "语法掌握": module_reports["grammar"]["summary"],
            "写作表达": module_reports["writing"]["summary"],
            "实战发挥": overall_summary,
            "学习执行力": "当前先以能稳定完成每日任务为主要观察点，后续会根据训练完成情况继续更新。",
        },
    }
