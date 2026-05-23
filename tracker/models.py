from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    total_xp = models.IntegerField(default=0)
    streak_days = models.IntegerField(default=0)
    last_completed_date = models.DateField(null=True, blank=True)
    language = models.CharField(max_length=2, default='ar', choices=[('ar', 'Arabic'), ('en', 'English')])
    quran_daily_target = models.IntegerField(default=5)
    sleep_target = models.FloatField(default=7.0)
    water_target = models.IntegerField(default=8)
    reading_target = models.IntegerField(default=30)
    coding_target = models.IntegerField(default=60)

    def __str__(self):
        return f"{self.user.username} Profile"

    def get_level(self):
        xp = self.total_xp
        level = 1
        required = 100
        while xp >= required:
            xp -= required
            level += 1
            required = int(required * 1.15)
        return level

    def get_xp_in_level(self):
        xp = self.total_xp
        required = 100
        while xp >= required:
            xp -= required
            required = int(required * 1.15)
        return xp

    def get_xp_for_next_level(self):
        xp = self.total_xp
        required = 100
        while xp >= required:
            xp -= required
            required = int(required * 1.15)
        return required

    def get_next_level_xp(self):
        return self.get_xp_for_next_level()

    def get_level_progress_pct(self):
        in_level = self.get_xp_in_level()
        for_next = self.get_xp_for_next_level()
        if for_next == 0:
            return 100
        return int((in_level / for_next) * 100)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.profile.save()
    except UserProfile.DoesNotExist:
        pass


class DailyProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_progress')
    date = models.DateField()

    # Islamic
    fajr = models.BooleanField(default=False)
    dhuhr = models.BooleanField(default=False)
    asr = models.BooleanField(default=False)
    maghrib = models.BooleanField(default=False)
    isha = models.BooleanField(default=False)
    quran_pages = models.IntegerField(default=0)
    morning_adhkar = models.BooleanField(default=False)
    evening_adhkar = models.BooleanField(default=False)
    qiyam = models.BooleanField(default=False)
    istighfar_count = models.IntegerField(default=0)
    salawat_count = models.IntegerField(default=0)
    matn_memorization = models.BooleanField(default=False)

    # Physical
    workout_done = models.BooleanField(default=False)
    workout_type = models.CharField(max_length=100, blank=True, default='')
    sleep_hours = models.FloatField(default=0.0)
    water_glasses = models.IntegerField(default=0)

    # Knowledge
    reading_minutes = models.IntegerField(default=0)
    books_pages = models.IntegerField(default=0)
    book_name = models.CharField(max_length=200, blank=True, default='')
    reading_notes = models.TextField(blank=True, default='')
    english_minutes = models.IntegerField(default=0)
    english_words = models.IntegerField(default=0)
    learned_something = models.BooleanField(default=False)
    learning_notes = models.TextField(blank=True, default='')

    # Programming
    coding_minutes = models.IntegerField(default=0)
    pomodoros_done = models.IntegerField(default=0)

    class Meta:
        unique_together = ['user', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username} — {self.date}"

    def calculate_xp(self, profile=None):
        xp = 0
        prayers = [self.fajr, self.dhuhr, self.asr, self.maghrib, self.isha]
        xp += sum(20 for p in prayers if p)
        xp += min(self.quran_pages * 10, 100)
        if self.morning_adhkar:
            xp += 15
        if self.evening_adhkar:
            xp += 15
        if self.qiyam:
            xp += 25
        if self.matn_memorization:
            xp += 20
        if self.workout_done:
            xp += 50
        sleep_target = profile.sleep_target if profile else 7.0
        water_target = profile.water_target if profile else 8
        reading_target = profile.reading_target if profile else 30
        coding_target = profile.coding_target if profile else 60
        if self.sleep_hours >= sleep_target:
            xp += 30
        if self.water_glasses >= water_target:
            xp += 20
        if self.reading_minutes >= reading_target:
            xp += 40
        if self.english_minutes >= 20:
            xp += 25
        if self.coding_minutes >= coding_target:
            xp += 50
        if self.pomodoros_done >= 4:
            xp += 30
        return xp

    def completion_pct(self, profile=None):
        total_goals = 10
        achieved = 0
        prayers = [self.fajr, self.dhuhr, self.asr, self.maghrib, self.isha]
        if sum(1 for p in prayers if p) == 5:
            achieved += 1
        quran_target = profile.quran_daily_target if profile else 5
        if self.quran_pages >= quran_target:
            achieved += 1
        if self.morning_adhkar:
            achieved += 1
        if self.evening_adhkar:
            achieved += 1
        if self.workout_done:
            achieved += 1
        sleep_target = profile.sleep_target if profile else 7.0
        if self.sleep_hours >= sleep_target:
            achieved += 1
        water_target = profile.water_target if profile else 8
        if self.water_glasses >= water_target:
            achieved += 1
        reading_target = profile.reading_target if profile else 30
        if self.reading_minutes >= reading_target:
            achieved += 1
        coding_target = profile.coding_target if profile else 60
        if self.coding_minutes >= coding_target:
            achieved += 1
        if self.pomodoros_done >= 4:
            achieved += 1
        return int((achieved / total_goals) * 100)


class CustomTask(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_tasks')
    date = models.DateField()
    label = models.CharField(max_length=200)
    done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username} — {self.label} ({self.date})"


# ── Personal Life OS ──────────────────────────────────────────────────────────

class CustomSection(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_sections')
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=10, default='⭐')
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.user.username} — {self.name}"


class CustomHabit(models.Model):
    TYPE_BOOLEAN = 'boolean'
    TYPE_COUNTER = 'counter'
    TYPE_NUMERIC = 'numeric'
    HABIT_TYPES = [
        (TYPE_BOOLEAN, 'Checkbox'),
        (TYPE_COUNTER, 'Counter'),
        (TYPE_NUMERIC, 'Numeric'),
    ]

    section = models.ForeignKey(CustomSection, on_delete=models.CASCADE, related_name='habits')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_habits')
    name = models.CharField(max_length=200)
    icon = models.CharField(max_length=10, default='✓')
    habit_type = models.CharField(max_length=20, choices=HABIT_TYPES, default=TYPE_BOOLEAN)
    target = models.FloatField(default=1.0)
    unit = models.CharField(max_length=30, blank=True, default='')
    xp_reward = models.IntegerField(default=10)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.user.username} — {self.name}"


class HabitLog(models.Model):
    habit = models.ForeignKey(CustomHabit, on_delete=models.CASCADE, related_name='logs')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='habit_logs')
    date = models.DateField()
    value = models.FloatField(default=0)

    class Meta:
        unique_together = ['habit', 'user', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username} — {self.habit.name} — {self.date}"
