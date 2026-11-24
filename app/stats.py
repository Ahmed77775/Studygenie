"""Numbers behind the Stats page. Plain functions over the app's data dict,
with no Tk, so they are easy to test."""

from datetime import date, timedelta

MAX_BOX = 5


def _due_date(card):
    """A card's due date, or None for a new card (or an unreadable date),
    which the app treats as due now."""
    try:
        return date.fromisoformat(card["due"]) if card.get("due") else None
    except (TypeError, ValueError):
        return None


def box_counts(cards):
    """How many cards sit in each Leitner box: {1: n, ..., 5: n}."""
    counts = {box: 0 for box in range(1, MAX_BOX + 1)}
    for card in cards:
        box = min(max(int(card.get("box") or 1), 1), MAX_BOX)
        counts[box] += 1
    return counts


def due_forecast(cards, today, days=7):
    """Cards due on each of the next `days` days, as [(date, count)].
    Overdue and new cards count towards today."""
    counts = [0] * days
    for card in cards:
        due = _due_date(card)
        offset = 0 if due is None else max((due - today).days, 0)
        if offset < days:
            counts[offset] += 1
    return [(today + timedelta(days=i), n) for i, n in enumerate(counts)]


def activity_grid(activity, today, weeks=12):
    """Study minutes laid out like a contribution calendar: a list of
    `weeks` columns (oldest first), each 7 (date, minutes) cells from
    Monday to Sunday. Days after today are None."""
    this_monday = today - timedelta(days=today.weekday())
    start = this_monday - timedelta(weeks=weeks - 1)
    grid = []
    for week in range(weeks):
        column = []
        for weekday in range(7):
            day = start + timedelta(weeks=week, days=weekday)
            column.append(None if day > today else (day, int(activity.get(day.isoformat(), 0) or 0)))
        grid.append(column)
    return grid


def best_streak(activity):
    """Longest run of consecutive days with any study minutes."""
    days = sorted(date.fromisoformat(d) for d, minutes in activity.items() if minutes and _is_iso(d))
    best = run = 0
    previous = None
    for day in days:
        run = run + 1 if previous and (day - previous).days == 1 else 1
        best = max(best, run)
        previous = day
    return best


def _is_iso(value):
    try:
        date.fromisoformat(value)
        return True
    except (TypeError, ValueError):
        return False


def subject_counts(cards):
    """Cards per subject, largest first: [(subject, count)]."""
    counts = {}
    for card in cards:
        subject = card.get("subject") or "General"
        counts[subject] = counts.get(subject, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def summary(data, today):
    """The headline numbers for the top row of the Stats page."""
    cards = data.get("flashcards", [])
    activity = data.get("activity", {})
    scores = data.get("quiz_scores", [])
    days_studied = sum(1 for minutes in activity.values() if minutes)
    return {
        "due_today": due_forecast(cards, today, days=1)[0][1],
        "total_cards": len(cards),
        "mastered": box_counts(cards)[MAX_BOX],
        "study_minutes": int(data.get("study_minutes", 0) or 0),
        "days_studied": days_studied,
        "current_streak": int(data.get("streak_days", 0) or 0),
        "best_streak": max(best_streak(activity), int(data.get("streak_days", 0) or 0)),
        "quizzes": len(scores),
        "quiz_average": round(sum(scores) / len(scores)) if scores else None,
        "quiz_best": max(scores) if scores else None,
    }


def subject_mastery(cards, limit=None):
    """Per-subject progress from flashcard boxes: [(subject, percent, cards)],
    most cards first. A card in box 1 counts 0%, box 5 counts 100%."""
    totals = {}
    for card in cards:
        subject = card.get("subject") or "General"
        box = min(max(int(card.get("box") or 1), 1), MAX_BOX)
        points, count = totals.get(subject, (0.0, 0))
        totals[subject] = (points + (box - 1) / (MAX_BOX - 1), count + 1)
    rows = [(subject, round(100 * points / count), count) for subject, (points, count) in totals.items()]
    rows.sort(key=lambda row: (-row[2], row[0]))
    return rows[:limit] if limit else rows


def _mastery(cards):
    """0-100: box 1 counts 0%, box 5 counts 100%."""
    if not cards:
        return None
    total = sum((min(max(int(c.get("box") or 1), 1), MAX_BOX) - 1) / (MAX_BOX - 1) for c in cards)
    return round(100 * total / len(cards))


def topic_mastery(cards):
    """Named topics with their progress: [(subject, topic, percent, cards)], most cards first."""
    groups = {}
    for card in cards:
        topic = (card.get("topic") or "").strip()
        if topic:
            groups.setdefault(topic.lower(), []).append(card)
    rows = []
    for group in groups.values():
        rows.append((group[0].get("subject") or "General", group[0]["topic"].strip(), _mastery(group), len(group)))
    rows.sort(key=lambda row: (-row[3], row[1].lower()))
    return rows


def topics_mastered(cards, threshold=80):
    return sum(1 for _, _, percent, _ in topic_mastery(cards) if percent >= threshold)


def remember_topic(recent, subject, topic, when, limit=12):
    """Puts (subject, topic) at the front of the recent-topics list, without duplicates."""
    topic = (topic or "").strip()
    if not topic:
        return list(recent or [])
    kept = [entry for entry in (recent or []) if entry.get("topic", "").lower() != topic.lower()]
    return [{"subject": subject or "General", "topic": topic, "at": when}] + kept[:limit - 1]


def todays_focus(data, today):
    """What the learner should continue with, from real data, or None.

    The most recent topic that isn't fully mastered; failing that, the
    subject whose flashcards are least mastered. Returns a dict with
    subject, topic (may be ""), percent (None if no cards yet), cards, due."""
    cards = data.get("flashcards", [])

    def summary(subject, topic, group):
        due = sum(1 for c in group if _card_due(c, today))
        return {"subject": subject, "topic": topic, "percent": _mastery(group), "cards": len(group), "due": due}

    for entry in data.get("recent_topics") or []:
        topic = entry.get("topic", "")
        group = [c for c in cards if (c.get("topic") or "").strip().lower() == topic.lower()]
        result = summary(entry.get("subject") or "General", topic, group)
        if result["percent"] is None or result["percent"] < 100:
            return result
    by_subject = subject_mastery(cards)
    if not by_subject:
        return None
    subject, _, _ = min(by_subject, key=lambda row: (row[1], -row[2]))
    return summary(subject, "", [c for c in cards if (c.get("subject") or "General") == subject])


def _card_due(card, today):
    due = _due_date(card)
    return due is None or due <= today
