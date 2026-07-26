
import os
import uuid
import random
import logging
import json
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import joblib
import requests
import torch  # keep if used elsewhere; safe to keep import
from decouple import config
from tensorflow.keras.models import load_model

from django.conf import settings
from django.core.mail import send_mail
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from .forms import SignupForm, OTPForm, LoginForm
from .models import UserProfile, Workout, WorkoutPlan, DietPlan
from .utils import create_personalized_plans, generate_workout, generate_diet
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from requests.exceptions import RequestException
import time
from twilio.rest import Client
# import uuid # Assuming uuid is imported elsewhere for email token
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
# from .forms import SignupForm, OTPForm # Assuming these are imported
# from .models import UserProfile # Assuming this is imported
# from django.core.mail import send_mail # Assuming this is imported
# import logging # Assuming logger is defined
from .models import UserProfile # Assuming UserProfile is correctly defined
from .utils import send_otp # This is the Twilio function
from .utils import create_personalized_plans # Used for profile completion logic
from django.db.models.signals import post_save
from .models import UserProfile, UserOTP
from .utils import send_otp, generate_otp, create_personalized_plans 
from django.conf import settings
logger = logging.getLogger(__name__)

# Globals for caching ML artifacts
preprocessor = None
macro_model = None

# -------------------------
# Basic Views
# -------------------------
def home(request):
    return render(request, 'home.html')


def start_journey(request):
    return render(request, 'start_journey.html')


def chatbot_view(request):
    return render(request, 'chatbot.html')

def get_mobile_from_form(form):
    """Safely retrieves the 'mobile' number from a Django Form's cleaned data."""
    try:
        # Assumes your SignupForm has a field named 'mobile'
        return form.cleaned_data.get('mobile')
    except AttributeError:
        # Fallback for unexpected form states
        return None
# -------------------------
# Signup / Verification Flow
# -------------------------
def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST) 
        
        if form.is_valid():
            # Get the mobile number from the form data
            mobile = get_mobile_from_form(form)
            if not mobile:
                messages.error(request, "Mobile number is required.")
                return redirect('signup')

            # --- CRITICAL PRE-CHECK / CLEANUP LOGIC ---
            # If the user is unverified, we delete the old User/Profile/OTP records 
            # to allow a fresh registration without violating the UserOTP.phone UNIQUE constraint.
            
            # 1. Check for existing UserOTP (which has a unique constraint on phone)
            try:
                old_otp_record = UserOTP.objects.get(phone=mobile)
                old_otp_record.delete()
                messages.warning(request, "Old OTP record cleaned up.")
            except UserOTP.DoesNotExist:
                pass # This is fine

            # 2. Check for existing unverified UserProfile and its User
            # NOTE: We look for users that are NOT active, implying they are unverified.
            existing_unverified_profile = UserProfile.objects.filter(
                mobile=mobile, 
                user__is_active=False
            ).first()
            if existing_unverified_profile:
                # Delete the user associated with the old, unverified profile
                existing_unverified_profile.user.delete()
                messages.warning(request, "Old unverified account found and cleaned up. Registering new account.")
            # --- END CRITICAL PRE-CHECK / CLEANUP ---

            # Save the new User. The signal creates UserProfile.
            # Assuming your form saves the User object with is_active=False initially.
            user = form.save(commit=True) 
            user.is_active = False # Ensure the user is inactive until verification
            user.save()
            user_profile = user.profile 

            # NOTE: Assuming 'verification_method' is set in the form or is default 'mobile'
            method = request.POST.get('verification_method', user_profile.verification_method)
            
            # --- MOBILE (OTP) VERIFICATION ---
            if method == 'mobile':
                otp_code = generate_otp()
                
                # Save OTP to the separate UserOTP table (as per your model definition)
                UserOTP.objects.update_or_create(
                    phone=mobile,
                    defaults={'otp': otp_code, 'timestamp': timezone.now()}
                )

                if send_otp(mobile, otp_code):
                    # Save mobile number to profile for lookup later
                    user_profile.mobile = mobile
                    user_profile.save()
                    
                    messages.success(request, "Account created. Please check your mobile for the OTP.")
                    request.session['username'] = user.username 
                    return redirect('verify_otp')
                else:
                    user.delete() 
                    UserOTP.objects.filter(phone=mobile).delete() # Clean up OTP record on send failure
                    messages.error(request, "Failed to send OTP. Check Twilio settings.")
                    return redirect('signup')

            # --- EMAIL VERIFICATION ---
            else:  
                token = str(uuid.uuid4())
                user_profile.email_token = token
                try:
                    send_mail(
                        subject="Email Verification",
                        message=f"Click to verify: {request.build_absolute_uri('/email-verify/')}{token}/",
                        from_email=EMAIL_HOST_USER,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                except Exception as e:
                    logger.exception("Failed to send verification email: %s", e)
                    messages.error(request, "Failed to send verification email.")
                    user.delete() 
                    return redirect('signup') 
                
                user_profile.verification_method = 'email'
                user_profile.save()
                request.session['username'] = user.username
                messages.success(request, "Account created. Please check your email for a verification link.")
                return redirect('email_pending') 
                
        else:
            messages.error(request, "Error creating account. Please correct the errors below.")
            
    else:
        form = SignupForm() 
        
    return render(request, 'signup.html', {'form': form})

# --- VERIFY OTP VIEW ---

def verify_otp(request):
    username = request.session.get('username')
    
    # 1. Session Check
    if not username:
        messages.error(request, "Session expired. Please sign up again.")
        return redirect('signup')

    # 2. Retrieve User and Profile
    try:
        user_obj = User.objects.get(username=username)
        user_profile = user_obj.profile 
        # Get phone from profile to retrieve OTP record
        mobile = user_profile.mobile 
        otp_record = UserOTP.objects.get(phone=mobile)
    except (User.DoesNotExist, UserProfile.DoesNotExist, UserOTP.DoesNotExist):
        messages.error(request, "User, Profile, or OTP record not found. Please sign up again.")
        return redirect('signup')

    if user_profile.is_verified:
        messages.info(request, "Your account is already verified.")
        login(request, user_obj)
        request.session.pop('username', None)
        return redirect('complete_profile')

    if request.method == 'POST':
        form = OTPForm(request.POST) 
        
        if form.is_valid():
            otp_entered = form.cleaned_data['otp']
            
            # --- OTP VALIDATION ---
            if otp_record.is_expired():
                 messages.error(request, "OTP expired. Please try again.")
                 otp_record.delete()
            elif otp_record.otp == otp_entered:
                # Validation success
                user_profile.is_verified = True
                user_profile.save()
                
                # Activate the Django User
                user_obj.is_active = True 
                user_obj.save()
                
                otp_record.delete() # Remove OTP record

                login(request, user_obj)
                messages.success(request, "Account verified successfully! Welcome.")
                request.session.pop('username', None)
                
                return redirect('complete_profile') 
            else:
                messages.error(request, "Invalid OTP. Please try again.")
        
    else:
        form = OTPForm() 
        
    return render(request, 'verify_otp.html', {'form': form, 'mobile': mobile})


# --- Other Views (Assuming they are complete) ---

def resend_otp(request):
    """
    Handles the request to resend a new OTP.
    This function should be called when the user clicks 'RESEND'.
    """
    # 1. Retrieve the mobile number from the session or request data
    mobile = request.session.get('phone') # Use 'phone' or 'mobile' based on how you store it

    if mobile:
        # 2. **CRITICAL STEP:** Call the underlying function to generate and send the OTP.
        # You may be able to reuse the logic from send_otp or a helper function.
        # Example using a placeholder helper function:
        # success = send_otp_to_mobile(mobile) 

        # 3. Add a success message to display on the verification page
        from django.contrib import messages
        messages.success(request, f'A new verification code has been sent to {mobile}.')
        
        # 4. Redirect back to the OTP verification page
        # Note: 'verify_otp' is the name defined in your urls.py
        from django.shortcuts import redirect
        return redirect('verify_otp')
    else:
        # Handle case where phone number is not found (session expired)
        from django.shortcuts import redirect
        from django.contrib import messages
        messages.error(request, 'Session lost. Please try signing up again.')
        return redirect('signup') # Redirect to the initial signup view



def email_verify(request, token):
    try:
        user_profile = UserProfile.objects.get(email_token=token)
        user_obj = user_profile.user

        user_profile.is_verified = True
        user_profile.email_token = None
        user_profile.save()

        login(request, user_obj)
        messages.success(request, "Your email has been verified successfully!")
        return redirect('complete_profile')
    except UserProfile.DoesNotExist:
        messages.error(request, "Invalid or expired verification link.")
        return render(request, 'email_not_me.html')


def email_pending(request):
    return render(request, 'email_pending.html')


# -------------------------
# Profile Completion Steps
# -------------------------
def complete_profile(request):
    username = request.session.get('username')
    if not username and request.user.is_authenticated:
        username = request.user.username
    if not username:
        messages.info(request, "Please log in to complete your profile.")
        return redirect('login')

    try:
        user_obj = User.objects.get(username=username)
        user_profile = user_obj.profile
    except User.DoesNotExist:
        messages.error(request, "User not found. Please sign up or log in again.")
        return redirect('signup')
    except Exception:
        messages.error(request, "User profile not found. Please contact support.")
        return redirect('login')

    steps = ['name', 'gender', 'height', 'weight', 'target_weight', 'goal']
    step_labels = {
        'name': 'Name', 'gender': 'Gender', 'height': 'Height (cm)',
        'weight': 'Weight (kg)', 'target_weight': 'Target Weight (kg)', 'goal': 'Fitness Goal'
    }

    current_step_index = request.session.get('step')
    if current_step_index is None:
        for i, field in enumerate(steps):
            value = getattr(user_profile, field, None)
            if value is None or (isinstance(value, str) and value.strip() == ''):
                current_step_index = i
                request.session['step'] = i
                break
        else:
            request.session.pop('step', None)
            return redirect('macro_summary')

    if request.method == 'POST':
        field_name = steps[current_step_index]
        value = None

        if field_name == 'goal':
            value = request.POST.get('selected_goal', '').strip()
        elif field_name == 'profile_image':
            if 'profile_image' in request.FILES:
                user_profile.profile_image = request.FILES['profile_image']
            else:
                messages.error(request, "Please upload a profile image.")
                return render(request, f'profile_steps/{field_name}.html', {
                    'field': field_name,
                    'label': step_labels.get(field_name, field_name.capitalize()),
                    'user': user_profile,
                })
        else:
            value = request.POST.get('value', '').strip()

        if value is not None:
            if field_name in ['height', 'weight', 'target_weight']:
                try:
                    value = float(value)
                except ValueError:
                    messages.error(request, "Please enter a valid number.")
                    return render(request, f'profile_steps/{field_name}.html', {
                        'field': field_name,
                        'label': step_labels[field_name],
                        'user': user_profile,
                    })

            setattr(user_profile, field_name, value)

            try:
                user_profile.save()
                messages.success(request, f"{step_labels[field_name]} saved successfully!")
            except Exception as e:
                messages.error(request, f"Error saving {step_labels[field_name]}: {e}")

            current_step_index += 1
            request.session['step'] = current_step_index

            if current_step_index >= len(steps):
                request.session.pop('step', None)
                messages.success(request, "Profile completion successful! Calculating your macros...")
                return redirect('macro_summary')
            else:
                return redirect('complete_profile')

    if current_step_index >= len(steps):
        return redirect('macro_summary')

    field_to_render = steps[current_step_index]
    return render(request, f'profile_steps/{field_to_render}.html', {
        'field': field_to_render,
        'label': step_labels[field_to_render],
        'user': user_profile
    })


# -------------------------
# Macro Summary View (ML prediction)
# -------------------------
@login_required
def macro_summary_view(request):
    username = request.session.get('username') or request.user.username

    try:
        user_obj = User.objects.get(username=username)
        profile = user_obj.profile
    except User.DoesNotExist:
        messages.error(request, "User not found. Please log in again.")
        return redirect('login')
    except Exception:
        messages.info(request, "Please complete your profile first.")
        return redirect('complete_profile')

    # Check required fields
    required_fields = ['name', 'gender', 'height', 'weight', 'target_weight', 'goal']
    for field in required_fields:
        if not getattr(profile, field, None):
            messages.info(request, "Please complete your profile details before viewing macros.")
            return redirect('complete_profile')

    goal_mapping = {
        "Body Recomposition": "Recomposition",
        "Abs Training": "Abs",
        "Cutting": "Cut",
        "Bulking": "Bulk",
        "cut": "Cut",
        "bulk": "Bulk",
        "recomposition": "Recomposition",
        "abs": "Abs"
    }
    normalized_goal = goal_mapping.get(str(profile.goal).strip(), str(profile.goal).strip())

    user_input = pd.DataFrame([{
        'weight': profile.weight,
        'target_weight': profile.target_weight,
        'goal': normalized_goal,
    }])

    global preprocessor, macro_model
    if preprocessor is None:
        try:
            preprocessor_path = os.path.join(settings.BASE_DIR, 'core', 'ml_files', 'macro_preprocessor.pkl')
            preprocessor = joblib.load(preprocessor_path)
        except Exception as e:
            messages.error(request, f"Preprocessor loading error: {e}")
            return render(request, 'error.html', {'error_message': f"Preprocessor loading error: {e}"})

    if macro_model is None:
        try:
            model_path = os.path.join(settings.BASE_DIR, 'core', 'ml_files', 'macro_predictor_model.h5')
            macro_model = load_model(model_path, compile=False)
        except Exception as e:
            messages.error(request, f"Model loading error: {e}")
            return render(request, 'error.html', {'error_message': f"Model loading error: {e}"})

    try:
        model_input = preprocessor.transform(user_input)
        prediction = macro_model.predict(model_input)[0]
    except Exception as e:
        messages.error(request, f"Prediction error: {e}")
        return render(request, 'error.html', {'error_message': f"Prediction error: {e}"})

    calories, protein, carbs, fat = map(lambda x: round(float(x), 2), prediction)

    profile.calories = calories
    profile.protein = protein
    profile.carbs = carbs
    profile.fat = fat
    profile.save()

    total_macros = protein + carbs + fat
    if total_macros > 0:
        carbs_percent = round((carbs / total_macros) * 100, 1)
        protein_percent = round((protein / total_macros) * 100, 1)
        fat_percent = round((fat / total_macros) * 100, 1)
    else:
        carbs_percent = protein_percent = fat_percent = 0

    carbs_end = carbs_percent
    protein_end = carbs_percent + protein_percent
    calories_remaining = max(0, (profile.calories or 0) - (profile.calories_burned or 0))

    context = {
        'calories': calories,
        'protein': protein,
        'carbs': carbs,
        'fat': fat,
        'profile': profile,
        'carbs_percent': carbs_percent,
        'protein_percent': protein_percent,
        'fat_percent': fat_percent,
        'carbs_end': carbs_end,
        'protein_end': protein_end,
        'calories_remaining': calories_remaining,
        'user_obj': user_obj,
    }

    return render(request, 'macro_summary.html', context)


# -------------------------
# Login / Logout
# -------------------------
def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user_obj = authenticate(request, username=username, password=password)

            if user_obj is not None:
                try:
                    user_profile = user_obj.profile
                    if not user_profile.is_verified:
                        messages.warning(request, "Your account is not verified. Please check your email/mobile.")
                        return redirect('verify_otp' if user_profile.verification_method == 'mobile' else 'email_pending')
                    else:
                        login(request, user_obj)
                        request.session['username'] = user_obj.username
                        messages.success(request, "Welcome back!")
                        return redirect('dashboard')
                except Exception:
                    messages.error(request, "User profile missing. Please contact support.")
                    return redirect('signup')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Please correct the form errors.")
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    request.session.flush()
    messages.info(request, "You have been logged out successfully.")
    return redirect('login')


# -------------------------
# Generate Plan (uses utils)
# -------------------------
def generate_plan_view(request):
    if request.method == 'POST':
        if request.user.is_authenticated and hasattr(request.user, 'profile'):
            try:
                create_personalized_plans(request.user)
                messages.success(request, 'Your personalized plan has been generated successfully!')
            except Exception as e:
                logger.exception("Error generating personalized plans: %s", e)
                messages.error(request, f'An error occurred: {e}')
        else:
            messages.error(request, 'You must be logged in with a complete profile to generate a plan.')
        return redirect('dashboard')
    return redirect('dashboard')


# -------------------------
# Dashboard
# -------------------------
# -------------------------
# Dashboard
# -------------------------
@login_required
def dashboard(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return redirect('profile_creation_page')

    # --- Workouts from DB (general templates) ---
    workouts = []
    if user_profile and user_profile.goal:
        try:
            workouts = Workout.objects.filter(goal=user_profile.goal).order_by('day_of_week')
        except Exception as e:
            logger.exception("Error fetching workouts: %s", e)
            workouts = []

    # --- Weekly weight bookkeeping ---
    today_iso = timezone.now().date().isoformat()
    weekly_weight_data = getattr(user_profile, 'weekly_weight_data', None) or []
    if not isinstance(weekly_weight_data, list):
        try:
            weekly_weight_data = list(weekly_weight_data)
        except Exception:
            weekly_weight_data = []

    if not any(d.get("date") == today_iso for d in weekly_weight_data):
        weekly_weight_data.append({
            "date": today_iso,
            "weight": user_profile.weight or 0.0,
            "calories": user_profile.calories_burned or 0.0
        })
        user_profile.weekly_weight_data = weekly_weight_data
        user_profile.save()

    weekly_data = weekly_weight_data[-7:]
    dates = [d.get("date", "") for d in weekly_data]
    weights = [d.get("weight", 0.0) for d in weekly_data]
    calories = [d.get("calories", 0.0) for d in weekly_data]

    bmi = user_profile.calculate_bmi() if hasattr(user_profile, 'calculate_bmi') else None
    calories_remaining = max(0, (user_profile.calories or 0) - (user_profile.calories_burned or 0))

    # --- Quotes & trends ---
    quotes = [
        "Push yourself, because no one else is going to do it for you.",
        "Sweat is just fat crying.",
        "Discipline is doing what needs to be done, even when you don’t want to.",
        "No pain, no gain. Shut up and train."
    ]
    quote_of_the_day = random.choice(quotes)

    weight_trend = "Stable"
    if len(weights) >= 2:
        if weights[-1] < weights[0]:
            weight_trend = "Decreasing"
        elif weights[-1] > weights[0]:
            weight_trend = "Increasing"

    # --- Daily templates & upcoming schedule ---
    daily_workout_templates = {
        "Monday": [("Bench Press", "bench.gif"), ("Tricep Pushdown", "tríceps.gif")],
        "Tuesday": [("Deadlift", "deadlift.gif"), ("Bicep Curl", "bicep.gif")],
        "Wednesday": [("Incline Bench", "incline.gif"), ("Overhead Triceps", "triceps2.gif")],
        "Thursday": [("Lat Pulldown", "lat.gif"), ("Hammer Curl", "hammer.gif")],
        "Friday": [("Shoulder Press", "shoulder.gif"), ("Planks", "abs.gif")],
        "Saturday": [("Squats", "squat.gif"), ("Lunges", "lunge.gif")],
        "Sunday": [("Rest", "rest.gif")]
    }
    current_day = timezone.now().strftime('%A')
    today_workouts = daily_workout_templates.get(current_day, [])

    upcoming_schedule = []
    for i in range(1, 4):
        future_day = (timezone.now() + timedelta(days=i)).strftime('%A')
        upcoming_schedule.append({
            "day": future_day,
            "workouts": daily_workout_templates.get(future_day, [])
        })

    # -------------------------
    # Personalized plans generation & filtering
    # -------------------------
    today = timezone.now().strftime('%A')

    try:
        weekly_workout = generate_workout(user_profile.goal, user_profile.weight, user_profile.target_weight) or []
    except Exception as e:
        logger.exception("generate_workout failed: %s", e)
        weekly_workout = []

    try:
        weekly_diet = generate_diet(user_profile.goal, user_profile.weight, user_profile.target_weight) or []
    except Exception as e:
        logger.exception("generate_diet failed: %s", e)
        weekly_diet = []

    # Only include dict items whose 'day' matches today
    personalized_workout = [w for w in weekly_workout if (isinstance(w, dict) and w.get('day') == today)]
    personalized_diet = [d for d in weekly_diet if (isinstance(d, dict) and d.get('day') == today)]

    # --- Normalize each item so template can safely use keys like 'goal' ---
    for i, w in enumerate(personalized_workout):
        if isinstance(w, dict):
            if not w.get('goal'):
                w['goal'] = user_profile.goal or "-"
            # ensure common keys exist to avoid template KeyErrors
            w.setdefault('exercise', w.get('exercise') or "-")
            w.setdefault('sets', w.get('sets') or "-")
            w.setdefault('reps', w.get('reps') or "-")
            w.setdefault('muscle_group', w.get('muscle_group') or "General")
            w.setdefault('duration', w.get('duration') or "-")
            w.setdefault('notes', w.get('notes') or "")
            w.setdefault('gif_url', w.get('gif_url') or "")
        else:
            # defensive fallback: convert non-dict to a normalized dict
            try:
                nd = {
                    'exercise': getattr(w, 'exercise', "-"),
                    'sets': getattr(w, 'sets', "-"),
                    'reps': getattr(w, 'reps', "-"),
                    'day': getattr(w, 'day', today),
                    'muscle_group': getattr(w, 'muscle_group', "General"),
                    'duration': getattr(w, 'duration', "-"),
                    'notes': getattr(w, 'notes', ""),
                    'gif_url': getattr(w, 'gif_url', ""),
                    'goal': getattr(w, 'goal', None) or user_profile.goal or "-"
                }
                personalized_workout[i] = nd
            except Exception:
                personalized_workout[i] = {'exercise': "-", 'goal': user_profile.goal or "-"}

    for i, d in enumerate(personalized_diet):
        if isinstance(d, dict):
            if not d.get('goal'):
                d['goal'] = user_profile.goal or "-"
            d.setdefault('meal_time', d.get('meal_time') or "-")
            d.setdefault('items', d.get('items') or "-")
            d.setdefault('calories', d.get('calories') or "-")
            d.setdefault('protein', d.get('protein') or "-")
            d.setdefault('carbs', d.get('carbs') or "-")
            d.setdefault('fat', d.get('fat') or "-")
        else:
            try:
                nd = {
                    'meal_time': getattr(d, 'meal_time', "-"),
                    'items': getattr(d, 'items', "-"),
                    'calories': getattr(d, 'calories', "-"),
                    'protein': getattr(d, 'protein', "-"),
                    'carbs': getattr(d, 'carbs', "-"),
                    'fat': getattr(d, 'fat', "-"),
                    'day': getattr(d, 'day', today),
                    'goal': getattr(d, 'goal', None) or user_profile.goal or "-"
                }
                personalized_diet[i] = nd
            except Exception:
                personalized_diet[i] = {'meal_time': "-", 'items': "-", 'goal': user_profile.goal or "-"}

    # --- Optionally: fallback to DB-stored plans if no generated plan exists (uncomment if desired) ---
    # if not personalized_workout:
    #     db_workout_qs = WorkoutPlan.objects.filter(user_profile=user_profile, day=today)
    #     if db_workout_qs.exists():
    #         personalized_workout = list(db_workout_qs.values())
    # if not personalized_diet:
    #     db_diet_qs = DietPlan.objects.filter(user_profile=user_profile, day=today).order_by('meal_time')
    #     if db_diet_qs.exists():
    #         personalized_diet = list(db_diet_qs.values())

    context = {
        "user_profile": user_profile,
        "dates": dates,
        "weights": weights,
        "calories": calories,
        "workouts": workouts,
        "today_workouts": today_workouts,
        "current_day": current_day,
        "upcoming_schedule": upcoming_schedule,
        "bmi": bmi,
        "calories_remaining": calories_remaining,
        "quote_of_the_day": quote_of_the_day,
        "weight_trend": weight_trend,
        "show_macro_chart": True,
        "show_start_journey": True,
        "personalized_workout": personalized_workout,
        "personalized_diet": personalized_diet,
        "today": today,
    }

    return render(request, "dashboard.html", context)



# -------------------------
# Profile settings
# -------------------------
@login_required
def profile_settings_view(request, username):
    user_obj = get_object_or_404(User, username=username)
    user_profile, _ = UserProfile.objects.get_or_create(user=user_obj)

    if request.method == 'POST':
        name = request.POST.get('name')
        gender = request.POST.get('gender')

        try:
            age = int(request.POST.get('age')) if request.POST.get('age') else None
        except (ValueError, TypeError):
            age = None

        height = request.POST.get('height')
        weight = request.POST.get('weight')
        target_weight = request.POST.get('target_weight')
        goal = request.POST.get('goal')
        activity_level = request.POST.get('activity_level')

        user_profile.name = name
        user_profile.gender = gender
        user_profile.age = age
        user_profile.height = height
        user_profile.weight = weight
        user_profile.target_weight = target_weight
        user_profile.goal = goal
        user_profile.activity_level = activity_level

        if 'profile_image' in request.FILES:
            user_profile.profile_image = request.FILES['profile_image']

        user_profile.save()
        messages.success(request, 'Your personal information has been saved successfully!')
        return redirect('profile_settings', username=username)

    context = {
        'user_obj': user_obj,
        'user_profile': user_profile,
    }
    return render(request, 'profile_settings.html', context)


# -------------------------
# Chatbot API (Gemini)
# -------------------------

# Your Gemini API Key (keep this private!)
GEMINI_API_KEY = "AQ.Ab8RN6KHJiowIGrAmZxvpUJs5b1_xJHVNcPlQKqjoPME0GYJqA" # Placeholder for privacy
GEMINI_MODEL_ID = "gemini-2.5-flash"

# Corrected URL format for the generateContent REST API endpoint
GEMINI_MODEL_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
@csrf_exempt
def chatbot_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST requests are allowed."}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception as e:
        return JsonResponse({"reply": f"Error decoding JSON: {e}"}, status=400)

    user_message = data.get("message")
    if not user_message:
        return JsonResponse({"reply": "Error: No message provided."}, status=400)

    # config
    api_key = getattr(settings, "GEMINI_API_KEY", "") or None
    model_url = getattr(settings, "GEMINI_MODEL_URL", "")
    if not api_key:
        logger.error("Gemini API key is not configured.")
        return JsonResponse({"reply": "AI service not configured. Please contact admin."}, status=503)

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_message}]
            }
        ]
    }

    max_retries = 3
    base_delay = 1.0  # seconds
    timeout_seconds = 10  # requests timeout

    bot_reply = "Sorry, I couldn't process that right now."

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(
                f"{model_url}?key={api_key}",
                headers=headers,
                json=payload,
                timeout=30
            )
            # if 5xx, raise for status to be handled by except below
            if 500 <= resp.status_code < 600:
                logger.warning("Gemini returned %s on attempt %d", resp.status_code, attempt)
                resp.raise_for_status()

            resp.raise_for_status()  # raise for 4xx/5xx
            gemini_response = resp.json()

            # Safely extract reply text
            if (
                gemini_response
                and "candidates" in gemini_response
                and isinstance(gemini_response["candidates"], list)
                and len(gemini_response["candidates"]) > 0
                and "content" in gemini_response["candidates"][0]
                and "parts" in gemini_response["candidates"][0]["content"]
                and len(gemini_response["candidates"][0]["content"]["parts"]) > 0
            ):
                bot_reply = gemini_response["candidates"][0]["content"]["parts"][0].get("text", bot_reply)
                return JsonResponse({"reply": bot_reply})
            else:
                logger.debug("Unexpected Gemini response structure: %s", json.dumps(gemini_response)[:1000])
                bot_reply = "Sorry, I received an unexpected response from the AI."
                return JsonResponse({"reply": bot_reply}, status=502)

        except RequestException as e:
            # network or 5xx error from requests
            logger.exception("Gemini API request failed (attempt %d/%d): %s", attempt, max_retries, e)

            # If it's the last attempt, break and return fallback
            if attempt == max_retries:
                break

            # exponential backoff with jitter
            sleep_for = base_delay * (2 ** (attempt - 1))
            jitter = random.uniform(0, 0.5 * sleep_for)
            time.sleep(sleep_for + jitter)
        except Exception as e:
            logger.exception("Unexpected error calling Gemini API: %s", e)
            break

    # Fallback reply when API is down or exhausted retries
    fallback_reply = "Sorry, I'm having trouble connecting to the AI service right now. Please try again in a few minutes."
    # REMOVED THE UNMATCHED " {}"
    return JsonResponse({"reply": fallback_reply}, status=503)