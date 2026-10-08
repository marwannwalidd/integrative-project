from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from datetime import date, timedelta
import json
import io

from .models import JournalEntry, Mood, Habit, HabitTracking, Reminder, SecuritySettings, Backup
from .forms import (
    RegisterForm, LoginForm, UserProfileForm, JournalEntryForm,
    MoodForm, HabitForm, ReminderForm, SecuritySettingsForm, SearchForm
)


# ─── AUTH ───────────────────────────────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            SecuritySettings.objects.create(user=user)
            login(request, user)
            messages.success(request, f"Welcome, {user.first_name or user.username}! Your account has been created.")
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'daily_journal/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            return redirect('dashboard')
    else:
        form = LoginForm()
    return render(request, 'daily_journal/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')


# ─── DASHBOARD ──────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    user = request.user
    recent_entries = JournalEntry.objects.filter(user=user)[:5]
    total_entries = JournalEntry.objects.filter(user=user).count()

    # Mood stats for last 7 days
    week_ago = timezone.now() - timedelta(days=7)
    recent_moods = Mood.objects.filter(user=user, recorded_at__gte=week_ago)
    mood_counts = {}
    for mood in recent_moods:
        mood_counts[mood.mood_type] = mood_counts.get(mood.mood_type, 0) + 1
    top_mood = max(mood_counts, key=mood_counts.get) if mood_counts else None

    # Habit summary
    habits = Habit.objects.filter(user=user)
    today = date.today()
    habits_done_today = HabitTracking.objects.filter(user=user, date=today, status=True).count()

    # Writing streak
    streak = _calculate_streak(user)

    # Insights
    entries = JournalEntry.objects.filter(user=user)
    total_words = sum(e.word_count() for e in entries)
    avg_words = round(total_words / total_entries, 1) if total_entries > 0 else 0

    hour = timezone.localtime(timezone.now()).hour
    if hour < 12:
        greeting = "morning"
    elif hour < 17:
        greeting = "afternoon"
    else:
        greeting = "evening"

    context = {
        'recent_entries': recent_entries,
        'total_entries': total_entries,
        'top_mood': top_mood,
        'habits': habits,
        'habits_done_today': habits_done_today,
        'streak': streak,
        'total_words': total_words,
        'avg_words': avg_words,
        'today': today,
        'greeting': greeting,
    }
    return render(request, 'daily_journal/dashboard.html', context)


def _calculate_streak(user):
    today = date.today()
    streak = 0
    check_date = today
    while True:
        if JournalEntry.objects.filter(user=user, created_at__date=check_date).exists():
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break
    return streak


# ─── JOURNAL ENTRIES ────────────────────────────────────────────────────────

@login_required
def entry_list(request):
    form = SearchForm(request.GET)
    entries = JournalEntry.objects.filter(user=request.user)

    if form.is_valid():
        query = form.cleaned_data.get('query')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
        if query:
            entries = entries.filter(Q(title__icontains=query) | Q(content__icontains=query))
        if date_from:
            entries = entries.filter(created_at__date__gte=date_from)
        if date_to:
            entries = entries.filter(created_at__date__lte=date_to)

    return render(request, 'daily_journal/entry_list.html', {'entries': entries, 'form': form})


@login_required
def entry_create(request):
    if request.method == 'POST':
        form = JournalEntryForm(request.POST)
        mood_form = MoodForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.save()
            if mood_form.is_valid() and mood_form.cleaned_data.get('mood_type'):
                mood = mood_form.save(commit=False)
                mood.user = request.user
                mood.entry = entry
                mood.save()
            messages.success(request, "Journal entry saved successfully! ✨")
            return redirect('entry_detail', pk=entry.pk)
    else:
        form = JournalEntryForm()
        mood_form = MoodForm()
    return render(request, 'daily_journal/entry_form.html', {
        'form': form, 'mood_form': mood_form, 'action': 'Create'
    })


@login_required
def entry_detail(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
    mood = entry.moods.first()
    return render(request, 'daily_journal/entry_detail.html', {'entry': entry, 'mood': mood})


@login_required
def entry_edit(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
    mood = entry.moods.first()
    if request.method == 'POST':
        form = JournalEntryForm(request.POST, instance=entry)
        mood_form = MoodForm(request.POST, instance=mood)
        if form.is_valid():
            form.save()
            if mood_form.is_valid():
                if mood:
                    mood_form.save()
                elif mood_form.cleaned_data.get('mood_type'):
                    new_mood = mood_form.save(commit=False)
                    new_mood.user = request.user
                    new_mood.entry = entry
                    new_mood.save()
            messages.success(request, "Journal entry updated successfully!")
            return redirect('entry_detail', pk=entry.pk)
    else:
        form = JournalEntryForm(instance=entry)
        mood_form = MoodForm(instance=mood)
    return render(request, 'daily_journal/entry_form.html', {
        'form': form, 'mood_form': mood_form, 'action': 'Edit', 'entry': entry
    })


@login_required
def entry_delete(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
    if request.method == 'POST':
        entry.delete()
        messages.success(request, "Journal entry deleted.")
        return redirect('entry_list')
    return render(request, 'daily_journal/entry_confirm_delete.html', {'entry': entry})


# ─── MOOD ───────────────────────────────────────────────────────────────────

@login_required
def mood_tracker(request):
    moods = Mood.objects.filter(user=request.user)[:30]
    # Weekly mood breakdown
    week_ago = timezone.now() - timedelta(days=7)
    week_moods = Mood.objects.filter(user=request.user, recorded_at__gte=week_ago)
    mood_stats = {}
    for m in week_moods:
        mood_stats[m.mood_type] = mood_stats.get(m.mood_type, 0) + 1
    mood_json = json.dumps(mood_stats)

    if request.method == 'POST':
        form = MoodForm(request.POST)
        if form.is_valid():
            mood = form.save(commit=False)
            mood.user = request.user
            mood.save()
            messages.success(request, "Mood logged!")
            return redirect('mood_tracker')
    else:
        form = MoodForm()
    return render(request, 'daily_journal/mood_tracker.html', {
        'moods': moods, 'form': form, 'mood_stats': mood_json, 'mood_stats_dict': mood_stats
    })


# ─── HABITS ─────────────────────────────────────────────────────────────────

@login_required
def habit_list(request):
    habits = Habit.objects.filter(user=request.user)
    today = date.today()
    habit_data = []
    for habit in habits:
        tracking = HabitTracking.objects.filter(habit=habit, date=today).first()
        habit_data.append({'habit': habit, 'done_today': tracking.status if tracking else False, 'tracking': tracking})
    return render(request, 'daily_journal/habit_list.html', {'habit_data': habit_data})


@login_required
def habit_create(request):
    if request.method == 'POST':
        form = HabitForm(request.POST)
        if form.is_valid():
            habit = form.save(commit=False)
            habit.user = request.user
            habit.save()
            messages.success(request, f"Habit '{habit.habit_name}' created!")
            return redirect('habit_list')
    else:
        form = HabitForm()
    return render(request, 'daily_journal/habit_form.html', {'form': form, 'action': 'Create'})


@login_required
def habit_toggle(request, pk):
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    today = date.today()
    tracking, created = HabitTracking.objects.get_or_create(
        habit=habit, user=request.user, date=today,
        defaults={'status': False}
    )
    tracking.status = not tracking.status
    tracking.save()
    return redirect('habit_list')


@login_required
def habit_delete(request, pk):
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    if request.method == 'POST':
        habit.delete()
        messages.success(request, "Habit deleted.")
    return redirect('habit_list')


# ─── REMINDERS ──────────────────────────────────────────────────────────────

@login_required
def reminder_list(request):
    reminders = Reminder.objects.filter(user=request.user)
    return render(request, 'daily_journal/reminder_list.html', {'reminders': reminders})


@login_required
def reminder_create(request):
    if request.method == 'POST':
        form = ReminderForm(request.POST)
        if form.is_valid():
            reminder = form.save(commit=False)
            reminder.user = request.user
            reminder.save()
            messages.success(request, "Reminder set!")
            return redirect('reminder_list')
    else:
        form = ReminderForm()
    return render(request, 'daily_journal/reminder_form.html', {'form': form, 'action': 'Create'})


@login_required
def reminder_delete(request, pk):
    reminder = get_object_or_404(Reminder, pk=pk, user=request.user)
    if request.method == 'POST':
        reminder.delete()
        messages.success(request, "Reminder deleted.")
    return redirect('reminder_list')


# ─── PROFILE & SECURITY ─────────────────────────────────────────────────────

@login_required
def profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated!")
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'daily_journal/profile.html', {'form': form})


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password changed successfully!")
            return redirect('profile')
    else:
        form = PasswordChangeForm(request.user)
        for field in form.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
    return render(request, 'daily_journal/change_password.html', {'form': form})


@login_required
def delete_account(request):
    if request.method == 'POST':
        request.user.delete()
        messages.success(request, "Your account has been deleted.")
        return redirect('login')
    return render(request, 'daily_journal/delete_account.html')


@login_required
def security_settings(request):
    settings_obj, _ = SecuritySettings.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = SecuritySettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Security settings updated!")
            return redirect('security_settings')
    else:
        form = SecuritySettingsForm(instance=settings_obj)
    return render(request, 'daily_journal/security_settings.html', {'form': form})


# ─── EXPORT & BACKUP ────────────────────────────────────────────────────────

@login_required
def export_txt(request):
    entries = JournalEntry.objects.filter(user=request.user)
    content = f"Daily Journal Export\nUser: {request.user.username}\n"
    content += f"Exported: {timezone.now().strftime('%Y-%m-%d %H:%M')}\n"
    content += "=" * 50 + "\n\n"
    for entry in entries:
        content += f"Title: {entry.title}\n"
        content += f"Date: {entry.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        content += f"Content:\n{entry.content}\n"
        content += "-" * 40 + "\n\n"
    response = HttpResponse(content, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="my_journal.txt"'
    return response


@login_required
def backup_data(request):
    if request.method == 'POST':
        Backup.objects.create(user=request.user, file_path='backup')
        messages.success(request, "Backup created successfully!")
        return redirect('dashboard')
    return redirect('dashboard')


# ─── INSIGHTS ───────────────────────────────────────────────────────────────

@login_required
def insights(request):
    user = request.user
    entries = JournalEntry.objects.filter(user=user)
    total = entries.count()
    total_words = sum(e.word_count() for e in entries)
    avg_words = round(total_words / total, 1) if total > 0 else 0

    # Entries per day of week
    from collections import defaultdict
    days_count = defaultdict(int)
    for e in entries:
        day = e.created_at.strftime('%A')
        days_count[day] += 1
    days_json = json.dumps(dict(days_count))

    # Mood distribution
    moods = Mood.objects.filter(user=user)
    mood_dist = defaultdict(int)
    for m in moods:
        mood_dist[m.mood_type] += 1
    mood_json = json.dumps(dict(mood_dist))

    # Monthly entries for last 6 months
    monthly = defaultdict(int)
    six_months_ago = timezone.now() - timedelta(days=180)
    for e in entries.filter(created_at__gte=six_months_ago):
        month = e.created_at.strftime('%b %Y')
        monthly[month] += 1
    monthly_json = json.dumps(dict(monthly))

    context = {
        'total': total,
        'total_words': total_words,
        'avg_words': avg_words,
        'streak': _calculate_streak(user),
        'days_json': days_json,
        'mood_json': mood_json,
        'monthly_json': monthly_json,
    }
    return render(request, 'daily_journal/insights.html', context)
