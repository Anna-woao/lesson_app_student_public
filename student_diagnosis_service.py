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

LEVEL_TRAINING_LABELS = {
    "L1": "基础日常词补底",
    "L2": "初中高频词巩固",
    "L3": "高中核心词提升",
    "L4": "阅读高频词进阶",
    "L5": "熟词生义与易混词专项",
}

QUESTION_TYPE_STUDENT_LABELS = {
    "en_to_zh_choice": "看英文选中文",
    "en_to_zh": "英文认词",
    "zh_to_en": "中文找英文",
    "confusable_choice": "易混词辨析",
    "polysemy_context": "熟词生义判断",
}

UNCERTAIN_OPTION = "\u6211\u4e0d\u77e5\u9053"


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


def _build_vocab_status_label(ratio: float) -> str:
    if ratio >= 0.85:
        return "较稳"
    if ratio >= 0.7:
        return "有基础"
    return "需要优先补强"


def _build_confidence_label(uncertain_rate: float) -> str:
    if uncertain_rate <= 0.08:
        return "较高"
    if uncertain_rate <= 0.18:
        return "中等"
    return "偏弱"


def _pick_vocab_training_track(level_accuracy_map: Dict[str, float]) -> Dict[str, str]:
    l1 = level_accuracy_map.get("L1", 0.0)
    l2 = level_accuracy_map.get("L2", 0.0)
    l3 = level_accuracy_map.get("L3", 0.0)
    l4 = level_accuracy_map.get("L4", 0.0)
    l5 = level_accuracy_map.get("L5", 0.0)

    if l1 < 0.7:
        return {
            "track": "basic_survival_vocab",
            "label": "基础日常词补底",
            "reason": "一些最基础的日常词还不够稳定，需要先把人物、动作、时间、地点和学校生活词稳住。",
        }
    if l2 < 0.75:
        return {
            "track": "junior_high_frequency_vocab",
            "label": "初中高频词巩固",
            "reason": "基础词已经有一些起点，但常见连接词、基础动词和常用抽象名词还不够稳定。",
        }
    if l3 < 0.75:
        return {
            "track": "senior_high_core_vocab",
            "label": "高中核心词提升",
            "reason": "基础词比较稳，下一步要补高中阅读里经常出现的核心词。",
        }
    if l4 < 0.75:
        return {
            "track": "reading_abstract_vocab",
            "label": "阅读高频词进阶",
            "reason": "普通词汇基础不错，但说明文、科普文和议论文里的抽象词还需要加强。",
        }
    if l5 < 0.75:
        return {
            "track": "polysemy_confusable_special",
            "label": "熟词生义与易混词专项",
            "reason": "词汇量基础已经比较好，现在更容易丢分的是熟词生义和相近词辨析。",
        }
    return {
        "track": "advanced_reading_vocab",
        "label": "高阶阅读词汇巩固",
        "reason": "词汇基础整体比较稳，可以进入更完整的高考阅读和题型训练。",
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
    question_type_accuracy_map_display = {
        QUESTION_TYPE_STUDENT_LABELS.get(key, key): value
        for key, value in question_type_accuracy_map.items()
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
        vocab_level_label = "起步打底"
    elif level_accuracy_map.get("L2", 0.0) < 0.6:
        estimated_vocab_range = "预计词汇量区间：800-1500"
        vocab_level_label = "基础过渡"
    elif level_accuracy_map.get("L3", 0.0) < 0.55:
        estimated_vocab_range = "预计词汇量区间：1500-2500"
        vocab_level_label = "高中起点"
    elif level_accuracy_map.get("L4", 0.0) < 0.5:
        estimated_vocab_range = "预计词汇量区间：2500-3500"
        vocab_level_label = "阅读进阶"
    elif level_accuracy_map.get("L5", 0.0) < 0.45:
        estimated_vocab_range = "预计词汇量区间：3500-4500"
        vocab_level_label = "进阶辨义"
    else:
        estimated_vocab_range = "预计词汇量区间：4500+"
        vocab_level_label = "高阶稳定"

    training_track = _pick_vocab_training_track(level_accuracy_map)
    vocab_training_track = training_track["track"]
    vocab_training_track_label = training_track["label"]
    vocab_training_track_reason = training_track["reason"]
    recommended_training_start = vocab_training_track_label

    if vocab_training_track == "basic_survival_vocab":
        main_vocab_problem = "最基础的日常词还不够稳，容易在人物、动作、时间和学校生活词上丢分。"
    elif vocab_training_track == "junior_high_frequency_vocab":
        main_vocab_problem = "初中阶段最常见的高频词还不够稳，连接词、基础动词和常用抽象名词需要继续巩固。"
    elif vocab_training_track == "senior_high_core_vocab":
        main_vocab_problem = "高中阅读里最常见的核心词还不够稳，读文章时会影响抓关键词。"
    elif vocab_training_track == "reading_abstract_vocab":
        main_vocab_problem = "说明文、科普文和议论文里的抽象词还比较薄弱。"
    elif vocab_training_track == "polysemy_confusable_special":
        main_vocab_problem = "不是单词量明显不够，而是熟词换了意思、或者几个相近词放在一起时容易混。"
    else:
        main_vocab_problem = "整体词汇基础比较稳，下一步更适合继续扩大阅读场景里的词汇稳定度。"

    level_breakdown = " / ".join(
        f"{level} {level_correct[level]}/{level_totals[level]}"
        for level in ["L1", "L2", "L3", "L4", "L5"]
        if level_totals[level]
    )

    strengths = []
    risk_flags = []
    recommended_actions = []

    if high_frequency_accuracy >= 0.8 and reading_vocab_accuracy >= 0.75:
        strengths.append("你已经能比较稳定地认出基础词和高中阅读常见词。")
    elif high_frequency_accuracy >= 0.8:
        strengths.append("你的基础词比较稳，常见高频词大多能认出来。")
    elif reading_vocab_accuracy >= 0.75:
        strengths.append("普通阅读里的大部分关键词，你已经能抓住。")

    if question_type_totals["polysemy_context"] and 0.55 <= polysemy_accuracy < 0.75:
        strengths.append("熟词生义不是完全不会，但还需要练到更稳定。")
    if question_type_totals["confusable_choice"] and confusable_accuracy >= 0.7:
        strengths.append("相近词放在一起时，你已经有一定辨别能力。")
    if uncertain_rate <= 0.08:
        strengths.append("做题时你的把握度比较高，很多题都能直接做出判断。")
    if not strengths:
        strengths.append("你已经有一定词汇基础，接下来重点是把薄弱那一层补稳。")

    if vocab_training_track == "basic_survival_vocab":
        risk_flags.append("基础日常词还不够稳，所以后面的阅读词更难真正用起来。")
        recommended_actions.append("接下来最值得练的是：基础日常词、人物动作词、学校生活词。")
    elif vocab_training_track == "junior_high_frequency_vocab":
        risk_flags.append("常见连接词、基础动词和常用抽象名词还不够稳。")
        recommended_actions.append("接下来最值得练的是：常见连接词、基础动词、常用抽象名词。")
    elif vocab_training_track == "senior_high_core_vocab":
        risk_flags.append("高中阅读核心词还不够稳，会影响抓文章关键词。")
        recommended_actions.append("接下来最值得练的是：高中阅读核心词、常见阅读动词、常见抽象名词。")
    elif vocab_training_track == "reading_abstract_vocab":
        risk_flags.append("说明文、科普文和议论文里的抽象词还会拖慢理解。")
        recommended_actions.append("接下来最值得练的是：说明文/科普文常见词、观点词、过程词、原因结果词。")
    elif vocab_training_track == "polysemy_confusable_special":
        risk_flags.append("你认识的词不少，但在真实阅读里，熟词换义和相近词更容易让你丢分。")
        recommended_actions.append("接下来最值得练的是：熟词生义、相近词辨析、句子中的词义判断。")
    else:
        risk_flags.append("当前没有明显塌层，后面更需要扩大阅读场景里的词汇稳定度。")
        recommended_actions.append("接下来可以进入更完整的高考阅读词汇巩固和题型训练。")

    if uncertain_rate >= 0.2:
        risk_flags.append("“我不知道”选得偏多，说明有些题不是完全不会，而是还不敢稳稳判断。")
        recommended_actions.append("后续训练里要加上短测和错题回看，先把会的词答得更稳。")
    elif uncertain_rate >= 0.1:
        risk_flags.append("你的基础有了，但答题时还可以更果断一些。")

    if vocab_training_track == "polysemy_confusable_special":
        student_explanation = """?????????????????????????????????

????????????
???????????????
????????????????????

???????????
???? + ????????"""
    else:
        student_explanation = f"""?????????????{vocab_training_track_label}????

????{vocab_training_track_reason}"""

    l5_note = ""
    if level_accuracy_map.get("L5", 0.0) < 0.75:
        l5_note = "这个结果说明：你认识的词不少，但在真实阅读里，熟词换义和相近词会让你丢分。"

    profile_summary = (
        f"这次词汇题你答对了 {correct_count}/{total_count}。"
        f" 基础词正确率 {round(high_frequency_accuracy * 100)}%，"
        f" 阅读词正确率 {round(reading_vocab_accuracy * 100)}%，"
        f" “我不知道”占比 {round(uncertain_rate * 100)}%。"
    )
    summary = (
        f"这轮词汇诊断答对 {correct_count}/{total_count}，"
        f"分层表现是 {level_breakdown}。"
    )
    recommendation = f"接下来建议先进入“{vocab_training_track_label}”。{vocab_training_track_reason}"

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
        "vocab_training_track": vocab_training_track,
        "vocab_training_track_label": vocab_training_track_label,
        "vocab_training_track_reason": vocab_training_track_reason,
        "level_accuracy_map": level_accuracy_map,
        "question_type_accuracy_map": question_type_accuracy_map,
        "question_type_accuracy_map_display": question_type_accuracy_map_display,
        "level_correct_counts": dict(level_correct),
        "level_total_counts": dict(level_totals),
        "question_type_correct_counts": dict(question_type_correct),
        "question_type_total_counts": dict(question_type_totals),
        "basic_vocab_status": _build_vocab_status_label(high_frequency_accuracy),
        "reading_vocab_status": _build_vocab_status_label(reading_vocab_accuracy),
        "answer_confidence_label": _build_confidence_label(uncertain_rate),
        "student_explanation": student_explanation,
        "l5_interpretation": l5_note,
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
            "vocab_training_track": vocab_training_track,
            "vocab_training_track_label": vocab_training_track_label,
            "main_vocab_problem": main_vocab_problem,
            "level_accuracy_map": level_accuracy_map,
            "question_type_accuracy_map": question_type_accuracy_map,
            "question_type_accuracy_map_display": question_type_accuracy_map_display,
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
    title_label = vocab_result["vocab_training_track_label"]

    if reading_score <= 1:
        reading_profile = "阅读这部分还需要先从主旨句、细节定位和基础理解开始。"
    elif reading_score <= 3:
        reading_profile = "你已经有基础阅读能力，接下来重点是把抓信息和读懂逻辑练得更稳。"
    else:
        reading_profile = "阅读基础比较稳，可以逐步进入更完整的阅读训练。"

    if grammar_score <= 2:
        grammar_gap = "语法上更需要先稳住时态、主谓一致和基础句型。"
    elif grammar_score <= 4:
        grammar_gap = "基础语法已经有了，但句型运用还需要继续练熟。"
    else:
        grammar_gap = "语法基础比较稳，可以更多放到真实语境里继续巩固。"

    if writing_score <= 1:
        writing_profile = "写作上更适合先从完整句表达和连接词使用开始。"
    elif writing_score <= 3:
        writing_profile = "你已经能组织基础表达，下一步更适合练段落结构。"
    else:
        writing_profile = "写作基础已有起点，可以逐步承接更完整的表达训练。"

    priority_module = min(module_reports, key=lambda key: (module_reports[key]["ratio"], module_reports[key]["score"]))
    strongest_module = max(module_reports, key=lambda key: (module_reports[key]["ratio"], module_reports[key]["score"]))

    suggested_track_map = {
        "vocab": f"建议先进入“{vocab_result['vocab_training_track_label']}”。{vocab_result['vocab_training_track_reason']}",
        "reading": "建议先从基础阅读理解与信息定位训练开始。",
        "grammar": "建议先从核心语法与基础句型稳定训练开始。",
        "writing": "建议先从句子表达与短段写作训练开始。",
    }
    growth_focus_map = {
        "vocab": f"当前最值得优先解决的是：{vocab_result['main_vocab_problem']}",
        "reading": "当前最值得优先解决的是：先把主旨和关键信息读出来。",
        "grammar": "当前最值得优先解决的是：先把基础时态和句型稳住。",
        "writing": "当前最值得优先解决的是：先把完整句和连接表达写顺。",
    }

    average_ratio = sum(scores.values()) / max(sum(totals.values()), 1)
    if average_ratio < 0.45:
        stage_label = "先把基础打稳"
        overall_summary = "你现在最需要的是先把基础节奏稳住，不用急着做太难的综合任务。"
    elif average_ratio < 0.75:
        stage_label = "稳步往上提"
        overall_summary = "你已经有了学习起点，接下来重点是把已有能力练得更稳、更连续。"
    else:
        stage_label = "可以继续进阶"
        overall_summary = "你的基础整体比较稳，可以开始承接更完整的综合训练。"

    next_actions = [
        growth_focus_map[priority_module],
        suggested_track_map[priority_module],
        f"词汇优先训练方向：{vocab_result['vocab_training_track_label']}。",
        f"你当前相对更稳的是“{module_reports[strongest_module]['short_title']}”，可以把它当成保持信心的支点。",
    ]

    summary_parts = [
        overall_summary,
        f"词汇优先训练方向是“{vocab_result['vocab_training_track_label']}”。",
    ]
    if vocab_result.get("l5_interpretation"):
        summary_parts.append(vocab_result["l5_interpretation"])
    summary_text = " ".join(summary_parts)

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
        "vocab_training_track": vocab_result.get("vocab_training_track", ""),
        "vocab_training_track_label": vocab_result.get("vocab_training_track_label", ""),
        "vocab_training_track_reason": vocab_result.get("vocab_training_track_reason", ""),
        "dimensions": {
            "词汇储备": module_reports["vocab"]["summary"],
            "阅读理解": module_reports["reading"]["summary"],
            "语法掌握": module_reports["grammar"]["summary"],
            "写作表达": module_reports["writing"]["summary"],
            "当前阶段": overall_summary,
            "接下来怎么学": suggested_track_map[priority_module],
        },
    }
