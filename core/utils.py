from typing import List, Dict, Tuple, Any
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import requests
import logging
import random 
from twilio.rest import Client 
from .models import WorkoutPlan, DietPlan, UserProfile 
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)


# --- TWILIO SMS UTILITY ---

def generate_otp() -> str:
    """Generates a random 6-digit OTP."""
    return str(random.randint(100000, 999999))

def send_otp(phone: str, otp: str) -> bool:
    """
    Sends an OTP via Twilio SMS.
    
    Args:
        phone (str): The recipient's phone number (expected to be 10 digits for India).
        otp (str): The 6-digit OTP code.
        
    Returns:
        bool: True on successful SMS submission, False otherwise.
    """
    try:
        # Retrieve credentials from Django settings
        ACCOUNT_SID = settings.TWILIO_ACCOUNT_SID
        AUTH_TOKEN = settings.TWILIO_AUTH_TOKEN
        
        # *** FIX APPLIED HERE: Using TWILIO_PHONE_NUMBER as defined in settings.py ***
        FROM_NUMBER = settings.TWILIO_PHONE_NUMBER 
        
        # Critical check to ensure values aren't empty
        if not all([ACCOUNT_SID, AUTH_TOKEN, FROM_NUMBER]):
            logger.error("Twilio credentials are empty. Check settings.py values.")
            return False
            
    except AttributeError:
        # This catches if the settings variables are missing entirely
        logger.error("Twilio settings (SID, Token, or Phone Number) are missing from Django settings.")
        return False

    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    
    # Prepend country code (+91 for India) if not already present
    to_phone = f"+91{phone}" if len(phone) == 10 and not phone.startswith('+') else phone
    
    try:
        message = client.messages.create(
            body=f'Your OTP is {otp}. Do not share with anyone.',
            from_=FROM_NUMBER,
            to=to_phone
        )
        logger.info(f"Twilio SMS sent successfully. Message SID: {message.sid}")
        return True
    except Exception as e:
        # This will catch Twilio API errors (e.g., invalid phone number format)
        logger.error(f"Twilio SMS failed to send to {to_phone}: {e}")
        return False


# --- WORKOUT GENERATION UTILITY ---

WorkoutDict = Dict[str, Any] 

def generate_workout(goal: str, weight: float, target_weight: float) -> List[WorkoutDict]:
    """
    Returns a weekly workout plan (Mon-Sun) with exercise variations based on goal.
    Each entry: {"day": "Monday", "exercise": List[str], "duration": int, "sets": str, "reps": str}
    """
    if not goal:
        return []

    g = goal.strip().capitalize()
    
    if g == "Cut":
        return [
            {"day": "Monday", "exercise": ["HIIT Sprints", "Push-ups", "Bench Press", "Shoulder Press", "Tricep Dips"], "duration": 60, "sets": "3", "reps": "12"},
            {"day": "Tuesday", "exercise": ["Treadmill Run", "Pull-ups", "Barbell Row", "Bicep Curls"], "duration": 50, "sets": "3", "reps": "12"},
            {"day": "Wednesday", "exercise": ["Squats", "Lunges", "Leg Press", "Plank", "Crunches"], "duration": 55, "sets": "3", "reps": "15"},
            {"day": "Thursday", "exercise": ["Cycling", "Mountain Climbers", "Russian Twists", "Leg Raises"], "duration": 45, "sets": "3", "reps": "15"},
            {"day": "Friday", "exercise": ["Deadlifts", "Push-ups", "Overhead Press", "Pull-ups"], "duration": 60, "sets": "3", "reps": "10"},
            {"day": "Saturday", "exercise": ["Jump Rope", "Burpees", "Plank Variations", "Kettlebell Swings"], "duration": 45, "sets": "3", "reps": "12"},
            {"day": "Sunday", "exercise": ["Yoga", "Foam Rolling", "Stretching"], "duration": 30, "sets": "-", "reps": "-"},
        ]
        
    if g == "Bulk":
        return [
            {"day": "Monday", "exercise": ["Bench Press", "Incline Dumbbell Press", "Overhead Press", "Tricep Extensions"], "duration": 75, "sets": "4", "reps": "8-10"},
            {"day": "Tuesday", "exercise": ["Deadlifts", "Pull-ups", "Barbell Row", "Bicep Curls"], "duration": 75, "sets": "4", "reps": "6-8"},
            {"day": "Wednesday", "exercise": ["Squats", "Leg Press", "Lunges", "Calf Raises"], "duration": 80, "sets": "4", "reps": "6-10"},
            {"day": "Thursday", "exercise": ["Incline Press", "Arnold Press", "Skull Crushers"], "duration": 70, "sets": "4", "reps": "8-12"},
            {"day": "Friday", "exercise": ["Lat Pulldown", "Seated Row", "Hammer Curls"], "duration": 70, "sets": "4", "reps": "8-12"},
            {"day": "Saturday", "exercise": ["Front Squats", "Romanian Deadlift", "Hip Thrusts"], "duration": 75, "sets": "4", "reps": "6-10"},
            {"day": "Sunday", "exercise": ["Yoga", "Foam Rolling", "Stretching"], "duration": 30, "sets": "-", "reps": "-"},
        ]
        
    if g in ("Abs", "Abstraining", "Abs training"):
        return [
            {"day": "Monday", "exercise": ["Hanging Leg Raises", "Plank Variations", "Crunches"], "duration": 40, "sets": "3", "reps": "12-20"},
            {"day": "Tuesday", "exercise": ["HIIT Run", "Mountain Climbers", "Russian Twists"], "duration": 45, "sets": "3", "reps": "15-20"},
            {"day": "Wednesday", "exercise": ["Squats", "Lunges", "Core Circuit"], "duration": 50, "sets": "3", "reps": "12-15"},
            {"day": "Thursday", "exercise": ["Push-ups", "Pull-ups", "Plank Holds"], "duration": 45, "sets": "3", "reps": "10-15"},
            {"day": "Friday", "exercise": ["Burpees", "Kettlebell Swings", "V-Ups"], "duration": 45, "sets": "3", "reps": "12-15"},
            {"day": "Saturday", "exercise": ["Core EMOM", "Farmer's Walk", "Bodyweight Circuits"], "duration": 50, "sets": "3", "reps": "12-15"},
            {"day": "Sunday", "exercise": ["Yoga", "Stretching", "Mobility"], "duration": 30, "sets": "-", "reps": "-"},
        ]
        
    # Recomposition / default
    return [
        {"day": "Monday", "exercise": ["Deadlifts", "Pull-ups", "Push-ups"], "duration": 60, "sets": "3", "reps": "8-12"},
        {"day": "Tuesday", "exercise": ["HIIT Run", "Plank", "Mountain Climbers"], "duration": 50, "sets": "3", "reps": "12-15"},
        {"day": "Wednesday", "exercise": ["Squats", "Lunges", "Crunches"], "duration": 55, "sets": "3", "reps": "10-12"},
        {"day": "Thursday", "exercise": ["Push-ups", "Barbell Row", "Shoulder Press"], "duration": 65, "sets": "3", "reps": "8-12"},
        {"day": "Friday", "exercise": ["Burpees", "Russian Twists", "Plank Variations"], "duration": 55, "sets": "3", "reps": "12-15"},
        {"day": "Saturday", "exercise": ["Pull-ups", "Squats", "Push Press"], "duration": 65, "sets": "3", "reps": "8-12"},
        {"day": "Sunday", "exercise": ["Yoga", "Mobility", "Foam Rolling"], "duration": 30, "sets": "-", "reps": "-"},
    ]


# --- DIET GENERATION UTILITY ---

DietDict = Dict[str, Any]

def generate_diet(goal: str, weight: float, target_weight: float) -> List[DietDict]:
    """
    Returns a flat list of meals for Monday->Sunday for the chosen goal.
    """
    g = (goal or "").strip().capitalize()

    # Calculation logic from your original code (Keeping it but it's not used below)
    try:
        calorie_diff = (float(target_weight or 0) - float(weight or 0)) * 50
        base_calories = int(2000 + calorie_diff)
    except (TypeError, ValueError):
        base_calories = 2000

    # CUT plan (full week)
    if g == "Cut":
        return [
            {"day": "Monday", "meal_time": "Breakfast", "items": "Oats + Egg Whites + Fruit", "calories": 400, "protein": 25, "carbs": 50, "fat": 8},
            {"day": "Monday", "meal_time": "Lunch", "items": "Grilled Chicken + Brown Rice + Veggies", "calories": 600, "protein": 45, "carbs": 60, "fat": 12},
            {"day": "Monday", "meal_time": "Snack", "items": "Protein Shake + Almonds", "calories": 200, "protein": 20, "carbs": 10, "fat": 8},
            {"day": "Monday", "meal_time": "Dinner", "items": "Salmon + Quinoa + Broccoli", "calories": 500, "protein": 40, "carbs": 40, "fat": 15},

            {"day": "Tuesday", "meal_time": "Breakfast", "items": "Smoothie (Spinach, Banana, Protein Powder)", "calories": 350, "protein": 30, "carbs": 40, "fat": 6},
            {"day": "Tuesday", "meal_time": "Lunch", "items": "Turkey Wrap + Salad", "calories": 550, "protein": 38, "carbs": 55, "fat": 10},
            {"day": "Tuesday", "meal_time": "Snack", "items": "Greek Yogurt + Berries", "calories": 180, "protein": 15, "carbs": 20, "fat": 5},
            {"day": "Tuesday", "meal_time": "Dinner", "items": "Chicken + Sweet Potato + Beans", "calories": 520, "protein": 42, "carbs": 45, "fat": 12},

            {"day": "Wednesday", "meal_time": "Breakfast", "items": "Scrambled Eggs + Spinach + Whole Wheat Toast", "calories": 370, "protein": 28, "carbs": 30, "fat": 12},
            {"day": "Wednesday", "meal_time": "Lunch", "items": "Grilled Fish + Couscous + Veggies", "calories": 580, "protein": 42, "carbs": 55, "fat": 14},
            {"day": "Wednesday", "meal_time": "Snack", "items": "Protein Bar + Apple", "calories": 210, "protein": 18, "carbs": 25, "fat": 6},
            {"day": "Wednesday", "meal_time": "Dinner", "items": "Chicken + Quinoa + Broccoli", "calories": 500, "protein": 40, "carbs": 45, "fat": 10},

            {"day": "Thursday", "meal_time": "Breakfast", "items": "Protein Pancakes + Blueberries", "calories": 400, "protein": 32, "carbs": 45, "fat": 9},
            {"day": "Thursday", "meal_time": "Lunch", "items": "Beef Stir Fry + Brown Rice", "calories": 600, "protein": 45, "carbs": 60, "fat": 15},
            {"day": "Thursday", "meal_time": "Snack", "items": "Cottage Cheese + Walnuts", "calories": 190, "protein": 15, "carbs": 12, "fat": 8},
            {"day": "Thursday", "meal_time": "Dinner", "items": "Grilled Salmon + Asparagus", "calories": 510, "protein": 42, "carbs": 38, "fat": 14},

            {"day": "Friday", "meal_time": "Breakfast", "items": "Greek Yogurt + Granola + Berries", "calories": 380, "protein": 25, "carbs": 40, "fat": 9},
            {"day": "Friday", "meal_time": "Lunch", "items": "Chicken Salad + Quinoa", "calories": 570, "protein": 40, "carbs": 50, "fat": 14},
            {"day": "Friday", "meal_time": "Snack", "items": "Protein Shake + Banana", "calories": 220, "protein": 22, "carbs": 30, "fat": 4},
            {"day": "Friday", "meal_time": "Dinner", "items": "Turkey + Sweet Potato + Broccoli", "calories": 520, "protein": 42, "carbs": 48, "fat": 12},

            {"day": "Saturday", "meal_time": "Breakfast", "items": "Oatmeal + Whey Protein + Nuts", "calories": 420, "protein": 30, "carbs": 50, "fat": 10},
            {"day": "Saturday", "meal_time": "Lunch", "items": "Grilled Chicken + Rice + Veggies", "calories": 590, "protein": 44, "carbs": 55, "fat": 13},
            {"day": "Saturday", "meal_time": "Snack", "items": "Boiled Eggs + Almonds", "calories": 200, "protein": 18, "carbs": 8, "fat": 10},
            {"day": "Saturday", "meal_time": "Dinner", "items": "Fish + Quinoa + Salad", "calories": 530, "protein": 41, "carbs": 42, "fat": 14},

            {"day": "Sunday", "meal_time": "Breakfast", "items": "Smoothie Bowl (Berries, Banana, Protein)", "calories": 360, "protein": 28, "carbs": 45, "fat": 8},
            {"day": "Sunday", "meal_time": "Lunch", "items": "Turkey + Couscous + Vegetables", "calories": 570, "protein": 40, "carbs": 52, "fat": 14},
            {"day": "Sunday", "meal_time": "Snack", "items": "Protein Shake + Nuts", "calories": 210, "protein": 20, "carbs": 12, "fat": 9},
            {"day": "Sunday", "meal_time": "Dinner", "items": "Beef + Brown Rice + Broccoli", "calories": 540, "protein": 45, "carbs": 50, "fat": 15},
        ]

    # BULK plan (full week)
    if g == "Bulk":
        bulk_week = {
            "Monday": {
                "Breakfast": {"items": "Omelette + Whole Wheat Bread + Peanut Butter", "calories": 600, "protein": 35, "carbs": 70, "fat": 20},
                "Lunch": {"items": "Chicken Breast + Rice + Avocado", "calories": 800, "protein": 55, "carbs": 85, "fat": 22},
                "Snack": {"items": "Protein Shake + Nuts", "calories": 300, "protein": 25, "carbs": 20, "fat": 12},
                "Dinner": {"items": "Beef + Sweet Potato + Veggies", "calories": 700, "protein": 50, "carbs": 65, "fat": 18},
            },
            "Tuesday": {
                "Breakfast": {"items": "Protein Shake + Oats + Banana", "calories": 650, "protein": 40, "carbs": 80, "fat": 15},
                "Lunch": {"items": "Turkey Burger + Rice", "calories": 780, "protein": 52, "carbs": 82, "fat": 20},
                "Snack": {"items": "Cottage Cheese + Fruits", "calories": 250, "protein": 20, "carbs": 25, "fat": 8},
                "Dinner": {"items": "Fish + Pasta + Olive Oil", "calories": 720, "protein": 48, "carbs": 70, "fat": 22},
            },
            "Wednesday": {
                "Breakfast": {"items": "Scrambled Eggs + Avocado Toast", "calories": 680, "protein": 38, "carbs": 65, "fat": 22},
                "Lunch": {"items": "Grilled Chicken + Brown Rice + Veggies", "calories": 820, "protein": 58, "carbs": 85, "fat": 20},
                "Snack": {"items": "Protein Bar + Milk", "calories": 310, "protein": 25, "carbs": 30, "fat": 9},
                "Dinner": {"items": "Steak + Mashed Potatoes + Beans", "calories": 750, "protein": 52, "carbs": 72, "fat": 21},
            },
            "Thursday": {
                "Breakfast": {"items": "Pancakes + Syrup + Protein Shake", "calories": 700, "protein": 35, "carbs": 90, "fat": 18},
                "Lunch": {"items": "Beef Burrito Bowl", "calories": 830, "protein": 55, "carbs": 88, "fat": 22},
                "Snack": {"items": "Greek Yogurt + Granola + Honey", "calories": 320, "protein": 22, "carbs": 40, "fat": 9},
                "Dinner": {"items": "Salmon + Rice + Veggies", "calories": 740, "protein": 50, "carbs": 70, "fat": 20},
            },
            "Friday": {
                "Breakfast": {"items": "French Toast + Peanut Butter + Banana", "calories": 690, "protein": 36, "carbs": 80, "fat": 20},
                "Lunch": {"items": "Chicken Pasta + Olive Oil", "calories": 810, "protein": 52, "carbs": 90, "fat": 22},
                "Snack": {"items": "Protein Shake + Nuts", "calories": 320, "protein": 25, "carbs": 22, "fat": 12},
                "Dinner": {"items": "Lamb + Couscous + Salad", "calories": 730, "protein": 50, "carbs": 68, "fat": 21},
            },
            "Saturday": {
                "Breakfast": {"items": "Egg Sandwich + Avocado", "calories": 670, "protein": 38, "carbs": 65, "fat": 21},
                "Lunch": {"items": "Turkey + Rice + Veggies", "calories": 800, "protein": 55, "carbs": 85, "fat": 20},
                "Snack": {"items": "Smoothie (Milk, Banana, Protein)", "calories": 330, "protein": 28, "carbs": 38, "fat": 9},
                "Dinner": {"items": "Chicken Curry + Rice", "calories": 740, "protein": 52, "carbs": 75, "fat": 21},
            },
            "Sunday": {
                "Breakfast": {"items": "Bagel + Cream Cheese + Eggs", "calories": 680, "protein": 36, "carbs": 78, "fat": 20},
                "Lunch": {"items": "Fish + Brown Rice + Veggies", "calories": 810, "protein": 55, "carbs": 85, "fat": 21},
                "Snack": {"items": "Cottage Cheese + Nuts", "calories": 310, "protein": 24, "carbs": 28, "fat": 10},
                "Dinner": {"items": "Beef + Potatoes + Salad", "calories": 750, "protein": 52, "carbs": 72, "fat": 22},
            },
        }
        return [{"day": d, "meal_time": mt, **vals} for d, meals in bulk_week.items() for mt, vals in meals.items()]

    # ABS plan (full week)
    if g == "Abs":
        abs_week = {
            "Monday": {
                "Breakfast": {"items": "Egg Whites + Oats + Banana", "calories": 400, "protein": 28, "carbs": 45, "fat": 8},
                "Lunch": {"items": "Grilled Fish + Quinoa + Veggies", "calories": 600, "protein": 45, "carbs": 55, "fat": 12},
                "Snack": {"items": "Greek Yogurt + Nuts", "calories": 200, "protein": 18, "carbs": 20, "fat": 7},
                "Dinner": {"items": "Chicken + Sweet Potato + Broccoli", "calories": 550, "protein": 42, "carbs": 48, "fat": 12},
            },
            "Tuesday": {
                "Breakfast": {"items": "Smoothie (Berries, Protein, Spinach)", "calories": 380, "protein": 30, "carbs": 42, "fat": 7},
                "Lunch": {"items": "Turkey Salad + Brown Rice", "calories": 590, "protein": 42, "carbs": 55, "fat": 14},
                "Snack": {"items": "Protein Shake + Apple", "calories": 210, "protein": 20, "carbs": 25, "fat": 5},
                "Dinner": {"items": "Fish + Veggies + Couscous", "calories": 540, "protein": 42, "carbs": 50, "fat": 13},
            },
            "Wednesday": {
                "Breakfast": {"items": "Oatmeal + Whey Protein + Blueberries", "calories": 410, "protein": 30, "carbs": 50, "fat": 9},
                "Lunch": {"items": "Chicken Wrap + Salad", "calories": 570, "protein": 40, "carbs": 50, "fat": 12},
                "Snack": {"items": "Cottage Cheese + Almonds", "calories": 200, "protein": 16, "carbs": 18, "fat": 8},
                "Dinner": {"items": "Grilled Salmon + Quinoa", "calories": 560, "protein": 45, "carbs": 48, "fat": 14},
            },
            "Thursday": {
                "Breakfast": {"items": "Protein Pancakes + Strawberries", "calories": 390, "protein": 30, "carbs": 45, "fat": 8},
                "Lunch": {"items": "Chicken Breast + Veggies + Brown Rice", "calories": 600, "protein": 44, "carbs": 55, "fat": 14},
                "Snack": {"items": "Protein Bar + Nuts", "calories": 220, "protein": 20, "carbs": 18, "fat": 9},
                "Dinner": {"items": "Beef Stir Fry + Vegetables", "calories": 570, "protein": 42, "carbs": 50, "fat": 13},
            },
            "Friday": {
                "Breakfast": {"items": "Scrambled Eggs + Spinach + Toast", "calories": 400, "protein": 28, "carbs": 35, "fat": 11},
                "Lunch": {"items": "Fish Tacos + Salad", "calories": 590, "protein": 42, "carbs": 52, "fat": 15},
                "Snack": {"items": "Greek Yogurt + Fruit", "calories": 190, "protein": 15, "carbs": 22, "fat": 6},
                "Dinner": {"items": "Chicken + Quinoa + Broccoli", "calories": 560, "protein": 42, "carbs": 48, "fat": 13},
            },
            "Saturday": {
                "Breakfast": {"items": "Smoothie Bowl (Banana, Protein, Almonds)", "calories": 380, "protein": 28, "carbs": 42, "fat": 8},
                "Lunch": {"items": "Grilled Chicken + Veggies + Brown Rice", "calories": 600, "protein": 45, "carbs": 55, "fat": 14},
                "Snack": {"items": "Boiled Eggs + Nuts", "calories": 200, "protein": 18, "carbs": 8, "fat": 10},
                "Dinner": {"items": "Fish + Salad + Quinoa", "calories": 540, "protein": 42, "carbs": 50, "fat": 12},
            },
            "Sunday": {
                "Breakfast": {"items": "Oats + Protein Powder + Berries", "calories": 400, "protein": 30, "carbs": 45, "fat": 9},
                "Lunch": {"items": "Chicken Salad + Sweet Potato", "calories": 580, "protein": 42, "carbs": 52, "fat": 14},
                "Snack": {"items": "Protein Shake + Walnuts", "calories": 210, "protein": 20, "carbs": 10, "fat": 10},
                "Dinner": {"items": "Grilled Salmon + Rice + Veggies", "calories": 560, "protein": 45, "carbs": 50, "fat": 13},
            },
        }
        return [{"day": d, "meal_time": mt, **vals} for d, meals in abs_week.items() for mt, vals in meals.items()]

    # RECOMPOSITION plan (full week)
    if g == "Recomposition":
        recompo_week = {
            "Monday": {
                "Breakfast": {"items": "Oats + Whey Protein + Banana", "calories": 420, "protein": 30, "carbs": 50, "fat": 9},
                "Lunch": {"items": "Grilled Chicken + Brown Rice + Veggies", "calories": 620, "protein": 45, "carbs": 60, "fat": 14},
                "Snack": {"items": "Protein Bar + Almonds", "calories": 230, "protein": 20, "carbs": 18, "fat": 8},
                "Dinner": {"items": "Salmon + Quinoa + Spinach", "calories": 560, "protein": 45, "carbs": 48, "fat": 12},
            },
            "Tuesday": {
                "Breakfast": {"items": "Eggs + Toast + Avocado", "calories": 410, "protein": 28, "carbs": 38, "fat": 14},
                "Lunch": {"items": "Turkey Wrap + Salad", "calories": 590, "protein": 40, "carbs": 55, "fat": 15},
                "Snack": {"items": "Greek Yogurt + Walnuts", "calories": 210, "protein": 18, "carbs": 15, "fat": 9},
                "Dinner": {"items": "Chicken + Sweet Potato + Broccoli", "calories": 570, "protein": 42, "carbs": 50, "fat": 14},
            },
            "Wednesday": {
                "Breakfast": {"items": "Smoothie (Spinach, Protein, Berries)", "calories": 390, "protein": 30, "carbs": 42, "fat": 8},
                "Lunch": {"items": "Grilled Fish + Couscous + Salad", "calories": 610, "protein": 45, "carbs": 55, "fat": 15},
                "Snack": {"items": "Protein Shake + Nuts", "calories": 220, "protein": 20, "carbs": 10, "fat": 10},
                "Dinner": {"items": "Beef + Vegetables + Rice", "calories": 580, "protein": 45, "carbs": 50, "fat": 14},
            },
            "Thursday": {
                "Breakfast": {"items": "Scrambled Eggs + Spinach + Toast", "calories": 400, "protein": 28, "carbs": 35, "fat": 11},
                "Lunch": {"items": "Chicken Salad + Sweet Potato", "calories": 590, "protein": 42, "carbs": 52, "fat": 14},
                "Snack": {"items": "Boiled Eggs + Almonds", "calories": 210, "protein": 18, "carbs": 8, "fat": 10},
                "Dinner": {"items": "Fish + Quinoa + Veggies", "calories": 570, "protein": 45, "carbs": 48, "fat": 13},
            },
            "Friday": {
                "Breakfast": {"items": "Oats + Protein + Blueberries", "calories": 410, "protein": 30, "carbs": 50, "fat": 9},
                "Lunch": {"items": "Turkey + Rice + Veggies", "calories": 600, "protein": 42, "carbs": 55, "fat": 14},
                "Snack": {"items": "Protein Bar + Fruit", "calories": 220, "protein": 20, "carbs": 22, "fat": 7},
                "Dinner": {"items": "Grilled Salmon + Sweet Potato", "calories": 580, "protein": 45, "carbs": 50, "fat": 14},
            },
            "Saturday": {
                "Breakfast": {"items": "Smoothie Bowl (Banana, Protein, Almonds)", "calories": 390, "protein": 28, "carbs": 42, "fat": 8},
                "Lunch": {"items": "Grilled Chicken + Brown Rice + Salad", "calories": 620, "protein": 45, "carbs": 60, "fat": 14},
                "Snack": {"items": "Cottage Cheese + Berries", "calories": 200, "protein": 18, "carbs": 15, "fat": 7},
                "Dinner": {"items": "Beef + Quinoa + Broccoli", "calories": 590, "protein": 45, "carbs": 50, "fat": 14},
            },
            "Sunday": {
                "Breakfast": {"items": "Protein Pancakes + Strawberries", "calories": 400, "protein": 30, "carbs": 45, "fat": 9},
                "Lunch": {"items": "Fish + Couscous + Veggies", "calories": 610, "protein": 45, "carbs": 55, "fat": 15},
                "Snack": {"items": "Greek Yogurt + Nuts", "calories": 210, "protein": 18, "carbs": 15, "fat": 9},
                "Dinner": {"items": "Chicken + Sweet Potato + Salad", "calories": 570, "protein": 42, "carbs": 50, "fat": 13},
            },
        }
        return [{"day": d, "meal_time": mt, **vals} for d, meals in recompo_week.items() for mt, vals in meals.items()]

    return []


# --- PLAN CREATION UTILITY ---

def create_personalized_plans(user: Any) -> Tuple[bool, str]:
    """
    Creates and saves WorkoutPlan and DietPlan entries for a user's profile.
    """
    profile = getattr(user, "profile", None)
    
    if not profile:
        return False, "User has no profile object."

    if not profile.goal or profile.weight is None or profile.target_weight is None:
        return False, "Profile incomplete (goal/weight/target_weight needed)."

    try:
        # Clear old plans to avoid duplicates or stale data
        WorkoutPlan.objects.filter(user_profile=profile).delete()
        DietPlan.objects.filter(user_profile=profile).delete()

        # 1. Create Workout Plans
        workouts = generate_workout(profile.goal, profile.weight, profile.target_weight)
        workout_plans_to_create = []
        for w in workouts:
            # Ensure exercise is a string for database
            exercise_str = ", ".join(w.get("exercise")) if isinstance(w.get("exercise"), (list, tuple)) else w.get("exercise")

            workout_plans_to_create.append(
                WorkoutPlan(
                    user_profile=profile,
                    goal=profile.goal,
                    day=w.get("day"),
                    exercise=exercise_str,
                    duration=w.get("duration"),
                    sets=w.get("sets"),
                    reps=w.get("reps"),
                )
            )
        WorkoutPlan.objects.bulk_create(workout_plans_to_create)

        # 2. Create Diet Plans
        diets = generate_diet(profile.goal, profile.weight, profile.target_weight)
        diet_plans_to_create = []
        for d in diets:
            diet_plans_to_create.append(
                DietPlan(
                    user_profile=profile,
                    goal=profile.goal,
                    day=d.get("day"),
                    meal_time=d.get("meal_time"),
                    items=d.get("items"),
                    calories=d.get("calories"),
                    protein=d.get("protein"),
                    carbs=d.get("carbs"),
                    fat=d.get("fat"),
                )
            )
        DietPlan.objects.bulk_create(diet_plans_to_create)

        return True, "Personalized plans created successfully."
    except Exception as e:
        logger.error(f"Failed to create personalized plans for user {user}: {e}")
        return False, f"An internal error occurred while generating plans: {str(e)}"