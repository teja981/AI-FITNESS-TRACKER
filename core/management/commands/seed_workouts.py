from django.core.management.base import BaseCommand
from core.models import Workout  # replace 'core' with your app name if different

class Command(BaseCommand):
    help = "Seed database with weekly workouts for each goal"

    def handle(self, *args, **options):
        workouts_data = {
            "cut": {
                "Monday": [("Bench Press", 4, 12), ("Push Ups", 3, 15)],
                "Tuesday": [("Deadlift", 4, 8), ("Pull Ups", 3, 10)],
                "Wednesday": [("Squats", 4, 10), ("Lunges", 3, 12)],
                "Thursday": [("Overhead Press", 4, 10), ("Lateral Raises", 3, 15)],
                "Friday": [("Bicep Curls", 3, 12), ("Tricep Dips", 3, 12)],
                "Saturday": [("Plank", 3, 60), ("Russian Twists", 3, 20)],
                "Sunday": []
            },
            "bulk": {
                "Monday": [("Bench Press (Heavy)", 5, 5), ("Incline Dumbbell Press", 4, 8)],
                "Tuesday": [("Deadlift (Heavy)", 5, 5), ("Barbell Row", 4, 8)],
                "Wednesday": [("Squats (Heavy)", 5, 5), ("Leg Press", 4, 10)],
                "Thursday": [("Overhead Press (Heavy)", 5, 5), ("Arnold Press", 4, 8)],
                "Friday": [("Barbell Curls", 4, 10), ("Close Grip Bench", 4, 8)],
                "Saturday": [("Hanging Leg Raises", 4, 12), ("Ab Rollouts", 3, 10)],
                "Sunday": []
            },
            "recomposition": {
                "Monday": [("Flat Bench", 4, 10), ("Dips", 3, 12)],
                "Tuesday": [("Romanian Deadlift", 4, 10), ("Chin Ups", 3, 12)],
                "Wednesday": [("Front Squat", 4, 8), ("Walking Lunges", 3, 12)],
                "Thursday": [("Military Press", 4, 8), ("Face Pulls", 3, 15)],
                "Friday": [("Hammer Curls", 3, 12), ("Overhead Tricep Extension", 3, 12)],
                "Saturday": [("Cable Crunch", 3, 15), ("Mountain Climbers", 3, 20)],
                "Sunday": []
            },
            "abs": {
                "Monday": [("Plank", 3, 60), ("Sit Ups", 3, 15)],
                "Tuesday": [("Hanging Knee Raises", 3, 12), ("Russian Twists", 3, 20)],
                "Wednesday": [("Leg Raises", 3, 15), ("Flutter Kicks", 3, 30)],
                "Thursday": [("Ab Rollouts", 3, 10), ("Side Plank", 3, 45)],
                "Friday": [("Bicycle Crunches", 3, 20), ("Toe Touches", 3, 15)],
                "Saturday": [("Mountain Climbers", 3, 20), ("V Ups", 3, 15)],
                "Sunday": []
            }
        }

        # Map full names to your model's choice fields
        DAY_MAP = {
            "Monday": "mon",
            "Tuesday": "tue",
            "Wednesday": "wed",
            "Thursday": "thu",
            "Friday": "fri",
            "Saturday": "sat",
            "Sunday": "sun"
        }

        GOAL_MAP = {
            "cut": "cut",
            "bulk": "bulk",
            "recomposition": "recomp",
            "abs": "abs"
        }

        for goal, days in workouts_data.items():
            db_goal = GOAL_MAP[goal]
            for day, exercises in days.items():
                db_day = DAY_MAP[day]
                for name, sets, reps in exercises:
                    obj, created = Workout.objects.get_or_create(
                        goal=db_goal,
                        day_of_week=db_day,
                        exercise=name,
                        defaults={
                            "sets": str(sets),
                            "reps": str(reps)
                        }
                    )
                    if created:
                        self.stdout.write(f"Added {name} for {goal} on {day}")

        self.stdout.write(self.style.SUCCESS("✅ Workouts seeded successfully!"))
