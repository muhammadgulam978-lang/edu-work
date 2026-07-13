from math import ceil


# ==========================================================
# CORE HELPERS
# ==========================================================

def clean_text(text):
    return " ".join((text or "").replace("\n", " ").split()).strip()


# ==========================================================
# BUILD ATOMIC CONTENT UNITS (NO LOSS)
# ==========================================================

def build_units(topics):
    """
    Har Topic / SubTopic ka content = 1 unit
    Koi content drop nahi hota
    """
    units = []

    for topic in topics:
        topic_texts = []

        for cb in topic.content_blocks.all():
            if cb.text:
                topic_texts.append(clean_text(cb.text))

        if topic_texts:
            units.append({
                "title": topic.title,
                "content": " ".join(topic_texts)
            })

        for sub in topic.subtopics.all():
            sub_texts = []
            for cb in sub.content_blocks.all():
                if cb.text:
                    sub_texts.append(clean_text(cb.text))

            if sub_texts:
                units.append({
                    "title": sub.title,
                    "content": " ".join(sub_texts)
                })

    return units


# ==========================================================
# DIVIDE COMPLETE LECTURE INTO N PERIODS
# ==========================================================

def divide_units_into_periods(units, total_periods):
    """
    Poora lecture = N equal logical parts
    """
    if total_periods <= 0:
        return []

    periods = [[] for _ in range(total_periods)]

    for index, unit in enumerate(units):
        period_index = index % total_periods
        periods[period_index].append(unit)

    return periods


# ==========================================================
# CONTENT → TASK GENERATORS (STRICTLY CONTENT BASED)
# ==========================================================

def learning_objectives_from_units(units):
    objectives = []
    for u in units:
        objectives.append(f"{u['title']}")
    return objectives


def assessment_from_units(units):
    tasks = []
    for u in units:
        tasks.append(f"Explain: {u['title']}")
    return tasks


def homework_from_units(units):
    tasks = []
    for u in units:
        tasks.append(f"Revise and write notes on: {u['title']}")
    return tasks



def generate_rule_based_lesson_plan(topics, total_periods):
    """
    FINAL ENGINE:
    Poora chapter ÷ N periods
    """
    units = build_units(topics)
    period_groups = divide_units_into_periods(units, total_periods)

    lesson_plan = []

    for i, group in enumerate(period_groups):
        if not group:
            lesson_plan.append({
                "period": i + 1,
                "topic_titles": ["Revision"],
                "main_teaching_content": "",
                "learning_objectives": ["Revision of previous topics"],
                "assessment_tasks": ["Oral questions from previous topics"],
                "homework_tasks": ["Revise previous work"],
                "practice_work": ["Short revision questions"],
                "plenary": ["Summary of previous lesson"]
            })
            continue

        lesson_plan.append({
            "period": i + 1,
            "topic_titles": [u["title"] for u in group],
            "main_teaching_content": " ".join(u["content"] for u in group),
            "learning_objectives": learning_objectives_from_units(group),
            "assessment_tasks": assessment_from_units(group),
            "homework_tasks": homework_from_units(group),
            "practice_work": assessment_from_units(group),
            "plenary": [f"Recap: {u['title']}" for u in group],
        })

    return lesson_plan


# ==========================================================
# BACKWARD COMPATIBILITY
# ==========================================================

generate_lesson_plan = generate_rule_based_lesson_plan
generate_content_based_lesson_plan = generate_rule_based_lesson_plan
