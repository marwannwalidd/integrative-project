from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import JournalEntry, Mood, Habit, HabitTracking, Reminder, SecuritySettings


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=False)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class JournalEntryForm(forms.ModelForm):
    class Meta:
        model = JournalEntry
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Entry title...'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 12, 'placeholder': 'Write your thoughts here...'}),
        }


class MoodForm(forms.ModelForm):
    class Meta:
        model = Mood
        fields = ['mood_type']
        widgets = {
            'mood_type': forms.Select(attrs={'class': 'form-select'}),
        }


class HabitForm(forms.ModelForm):
    class Meta:
        model = Habit
        fields = ['habit_name', 'description']
        widgets = {
            'habit_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Habit name...'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional description...'}),
        }


class ReminderForm(forms.ModelForm):
    class Meta:
        model = Reminder
        fields = ['reminder_time', 'message', 'is_active']
        widgets = {
            'reminder_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'message': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class SecuritySettingsForm(forms.ModelForm):
    confirm_pin = forms.CharField(
        max_length=6, required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm PIN'})
    )

    class Meta:
        model = SecuritySettings
        fields = ['pin_code', 'biometric_enabled']
        widgets = {
            'pin_code': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '4-6 digit PIN', 'maxlength': 6}),
            'biometric_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        pin = cleaned_data.get('pin_code')
        confirm = cleaned_data.get('confirm_pin')
        if pin and pin != confirm:
            raise forms.ValidationError("PIN codes do not match.")
        if pin and not pin.isdigit():
            raise forms.ValidationError("PIN must contain only digits.")
        return cleaned_data


class SearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search entries...'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
