# core/models.py

from django.db import models
# Using Django's default User model, as per your original file
from django.contrib.auth.models import User 
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta

# -----------------------
# Choices
# -----------------------
GOAL_CHOICES = [
    ('Cut', 'Cut'),
    ('Bulk', 'Bulk'),
    ('Recomposition', 'Recomposition'),
    ('Abs', 'Abs Training'),
    ('Maintain', 'Maintain'),
]

DAY_CHOICES = [
    ('Monday', 'Monday'),
    ('Tuesday', 'Tuesday'),
    ('Wednesday', 'Wednesday'),
    ('Thursday', 'Thursday'),
    ('Friday', 'Friday'),
    ('Saturday', 'Saturday'),
    ('Sunday', 'Sunday'),
]

GENDER_CHOICES = [
    ('Male', 'Male'),
    ('Female', 'Female'),
    ('Other', 'Other'),
]

VERIFICATION_METHODS = [
    ('email', 'Email'),
    ('mobile', 'Mobile'),
]

# -----------------------
# User Profile (CRITICAL FIX applied here)
# -----------------------
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    name = models.CharField(max_length=100, blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    
    # CRITICAL FIX: Removed unique=True. Unverified accounts can temporarily share a number.
    mobile = models.CharField(max_length=15, blank=True, null=True) 
    
    height = models.FloatField(blank=True, null=True, help_text="Height in cm")
    weight = models.FloatField(blank=True, null=True, help_text="Current weight in kg")
    target_weight = models.FloatField(blank=True, null=True, help_text="Target weight in kg")
    calories = models.FloatField(default=0.0)
    protein = models.FloatField(default=0.0)
    carbs = models.FloatField(default=0.0)
    fat = models.FloatField(default=0.0)
    calories_burned = models.FloatField(default=0.0)
    goal = models.CharField(max_length=50, choices=GOAL_CHOICES, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    weekly_weight_data = models.JSONField(default=list, help_text="Historical weight and calories burned per day")
    
    # Verification Fields
    is_verified = models.BooleanField(default=False)
    verification_method = models.CharField(max_length=10, choices=VERIFICATION_METHODS, default='email')
    otp = models.CharField(max_length=6, blank=True, null=True)
    email_token = models.CharField(max_length=64, blank=True, null=True)
    otp_timestamp = models.DateTimeField(null=True, blank=True) # Added for OTP expiry check

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def calculate_bmi(self):
        if self.weight and self.height and self.height > 0:
            height_m = self.height / 100
            return round(self.weight / (height_m ** 2), 2)
        return 0.0

    def is_otp_expired(self):
        """Checks if the OTP is older than 5 minutes."""
        if self.otp_timestamp:
            return (timezone.now() - self.otp_timestamp) > timedelta(minutes=5)
        return True


# -----------------------
# User OTP Model (Kept as separate model as per your original code)
# -----------------------
class UserOTP(models.Model):
    phone = models.CharField(max_length=15, unique=True)
    otp = models.CharField(max_length=6)
    timestamp = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        """Checks if the OTP is older than 5 minutes."""
        return timezone.now() > self.timestamp + timedelta(minutes=5)
    
    def __str__(self):
        return f"OTP for {self.phone}"


# -----------------------
# Signal to create/update profile
# -----------------------
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        # NOTE: You MUST set is_active=False on the User object during creation in your form/view
        UserProfile.objects.create(user=instance)
    else:
        # Safely get or create profile
        UserProfile.objects.get_or_create(user=instance)


# -----------------------
# Normal / Predefined Workouts
# -----------------------
class Workout(models.Model):
    goal = models.CharField(max_length=20, choices=GOAL_CHOICES)
    day_of_week = models.CharField(max_length=10, choices=DAY_CHOICES)
    exercise = models.CharField(max_length=100)
    sets = models.CharField(max_length=50)
    reps = models.CharField(max_length=50)

    class Meta:
        unique_together = ('goal', 'day_of_week', 'exercise')
        ordering = ['goal', 'day_of_week']

    def __str__(self):
        return f"{self.get_goal_display()} - {self.exercise} ({self.get_day_of_week_display()})"

# -----------------------
# Personalized Workout Plan per User
# -----------------------
class WorkoutPlan(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='workout_plans')
    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    exercise = models.CharField(max_length=100)
    sets = models.CharField(max_length=50)
    reps = models.CharField(max_length=50)
    goal = models.CharField(max_length=20, choices=GOAL_CHOICES)
    duration = models.IntegerField(help_text="Duration in minutes", default=30)

    class Meta:
        unique_together = ('user_profile', 'goal', 'day', 'exercise')
        ordering = ['user_profile', 'goal', 'day']

    def __str__(self):
        return f"{self.user_profile.user.username} - {self.exercise} ({self.day})"

# -----------------------
# Personalized Diet Plan per User
# -----------------------
class DietPlan(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='diet_plans')
    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    meal_time = models.CharField(max_length=20)
    items = models.TextField()
    calories = models.IntegerField()
    protein = models.FloatField()
    carbs = models.FloatField()
    fat = models.FloatField()
    goal = models.CharField(max_length=20, choices=GOAL_CHOICES)

    class Meta:
        unique_together = ('user_profile', 'goal', 'day', 'meal_time')
        ordering = ['user_profile', 'goal', 'day']

    def __str__(self):
        return f"{self.user_profile.user.username} - {self.goal} - {self.day} - {self.meal_time}"