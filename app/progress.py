"""Gamification: study minutes, XP, levels, streaks and badges.

The class using this mixin provides the UI hooks it calls:
refresh_status(), celebrate(title, subtitle) and after(ms, callback)."""

from datetime import date


class ProgressMixin:
    """Gamification: study minutes, XP, levels, streaks and badges."""

    def add_study_minutes(self, minutes):
        key = self.today_key()
        self.data["study_minutes"] += minutes
        self.data["activity"][key] = self.activity_today() + minutes
        self.save_data()
        self.update_streak()
        self.add_xp(minutes * 2)

    # ------------------------- gamification ------------------------------

    def xp_for_level(self, level):
        return 100 + (level - 1) * 60

    LEVEL_TITLES = ((1, "Beginner", "🌱"), (2, "Explorer", "🧭"), (3, "Learner", "📘"),
                    (4, "Achiever", "🎯"), (5, "Scholar", "🧠"), (7, "Expert", "🔬"),
                    (10, "Master", "🏆"), (15, "Genius", "💡"), (20, "Legend", "👑"))

    def level_title(self, level, with_icon=False):
        """The name for a level, e.g. 5 -> 'Scholar' (or 'Scholar 🧠')."""
        title, icon = "Beginner", "🌱"
        for minimum, name, emoji in self.LEVEL_TITLES:
            if level >= minimum:
                title, icon = name, emoji
        return f"{title} {icon}" if with_icon else title

    def total_xp(self):
        """All XP ever earned: every completed level plus progress in this one."""
        return sum(self.xp_for_level(lvl) for lvl in range(1, self.data["level"])) + self.data["xp"]

    # Daily counters for Today's Quest. They live in one small dict that
    # resets itself when the date changes.

    def bump_today(self, kind, amount=1):
        log = self.data.get("today_log") or {}
        if log.get("date") != self.today_key():
            log = {"date": self.today_key()}
        log[kind] = log.get(kind, 0) + amount
        self.data["today_log"] = log

    def today_count(self, kind):
        log = self.data.get("today_log") or {}
        return log.get(kind, 0) if log.get("date") == self.today_key() else 0

    def daily_quests(self):
        """Today's quests as (label, done, target) tuples."""
        goal = max(1, int(self.data.get("daily_goal", 60)))
        return (
            (f"Focus for {goal} minutes", min(self.activity_today(), goal), goal),
            ("Review 10 flashcards", min(self.today_count("cards"), 10), 10),
            ("Finish a quiz or study a photo", min(self.today_count("quizzes") + self.today_count("photos"), 1), 1),
        )

    def add_xp(self, amount, announce=True):
        self.data["xp"] += amount
        leveled_up = False
        while self.data["xp"] >= self.xp_for_level(self.data["level"]):
            self.data["xp"] -= self.xp_for_level(self.data["level"])
            self.data["level"] += 1
            leveled_up = True
        self.save_data()
        self.refresh_status()
        newly_unlocked = self.check_badges()
        if not announce:
            return
        if leveled_up:
            self.celebrate(f"Level {self.data['level']}!", "You've earned enough XP to level up. Keep going!")
        elif newly_unlocked:
            badge = newly_unlocked[0]
            self.celebrate(f"{badge['icon']} Achievement unlocked: {badge['name']}", badge["desc"])
            if len(newly_unlocked) > 1:
                for extra in newly_unlocked[1:]:
                    self.after(1300, lambda b=extra: self.celebrate(
                        f"{b['icon']} Achievement unlocked: {b['name']}", b["desc"]))

    def track_subject(self, subject):
        """Remembers that the student engaged with this subject at least
        once, so the 'Subject Explorer' / 'All-Rounder' badges can unlock."""
        subjects = self.data.setdefault("subjects_used", [])
        if subject and subject not in subjects:
            subjects.append(subject)
            self.save_data()

    def check_badges(self):
        unlocked = set(self.data["badges"])
        newly = []
        for badge in self.BADGES:
            if badge["id"] not in unlocked and badge["check"](self.data):
                self.data["badges"].append(badge["id"])
                newly.append(badge)
        if newly:
            self.save_data()
        return newly

    def update_streak(self):
        today = date.today()
        last = self.data.get("last_active_date")
        if last:
            last_date = date.fromisoformat(last)
            delta = (today - last_date).days
            if delta == 0:
                return
            elif delta == 1:
                self.data["streak_days"] += 1
            else:
                self.data["streak_days"] = 1
        else:
            self.data["streak_days"] = 1
        self.data["last_active_date"] = today.isoformat()
        self.save_data()
