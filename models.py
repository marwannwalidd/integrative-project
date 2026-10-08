from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class JournalEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='journal_entries')
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Journal Entries'

    def __str__(self):
        return f"{self.title} - {self.user.username}"

    def word_count(self):
        return len(self.content.split()) if self.content else 0


class Mood(models.Model):
    MOOD_CHOICES = [
        ('happy', '😊 Happy'),
        ('sad', '😢 Sad'),
        ('anxious', '😰 Anxious'),
        ('calm', '😌 Calm'),
        ('excited', '🤩 Excited'),
        ('angry', '😠 Angry'),
        ('grateful', '🙏 Grateful'),
        ('tired', '😴 Tired'),
        ('neutral', '😐 Neutral'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='moods')
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='moods', null=True, blank=True)
    mood_type = models.CharField(max_length=50, choices=MOOD_CHOICES)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']

    def __str__(self):
        return f"{self.user.username} - {self.mood_type} - {self.recorded_at.date()}"


class Habit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='habits')
    habit_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.habit_name} - {self.user.username}"

    def completion_rate(self):
        total = self.tracking_logs.count()
        if total == 0:
            return 0
        completed = self.tracking_logs.filter(status=True).count()
        return round((completed / total) * 100, 1)


class HabitTracking(models.Model):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='tracking_logs')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='habit_tracking')
    date = models.DateField(default=timezone.now)
    status = models.BooleanField(default=False)

    class Meta:
        unique_together = ('habit', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.habit.habit_name} - {self.date} - {'Done' if self.status else 'Pending'}"


class Reminder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reminders')
    reminder_time = models.TimeField()
    message = models.CharField(max_length=255, default="Time to write in your journal!")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - {self.reminder_time}"


class SecuritySettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='security_settings')
    pin_code = models.CharField(max_length=6, blank=True, null=True)
    biometric_enabled = models.BooleanField(default=False)

    def __str__(self):
        return f"Security settings for {self.user.username}"


class Backup(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='backups')
    backup_date = models.DateTimeField(auto_now_add=True)
    file_path = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ['-backup_date']

    def __str__(self):
        return f"Backup for {self.user.username} on {self.backup_date.date()}"
