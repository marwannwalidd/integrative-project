from django.contrib import admin
from .models import JournalEntry, Mood, Habit, HabitTracking, Reminder, SecuritySettings, Backup


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'created_at', 'word_count']
    list_filter = ['user', 'created_at']
    search_fields = ['title', 'content', 'user__username']


@admin.register(Mood)
class MoodAdmin(admin.ModelAdmin):
    list_display = ['user', 'mood_type', 'recorded_at']
    list_filter = ['mood_type', 'user']


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ['habit_name', 'user', 'created_at']
    list_filter = ['user']


@admin.register(HabitTracking)
class HabitTrackingAdmin(admin.ModelAdmin):
    list_display = ['habit', 'user', 'date', 'status']
    list_filter = ['status', 'date']


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ['user', 'reminder_time', 'is_active']


@admin.register(SecuritySettings)
class SecuritySettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'biometric_enabled']


@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    list_display = ['user', 'backup_date']
