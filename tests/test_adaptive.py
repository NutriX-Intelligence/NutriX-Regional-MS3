import unittest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app import models
from app.services.adaptive_planner import AdaptivePlanner

class TestAdaptivePlanner(unittest.TestCase):
    def setUp(self):
        # Create in-memory database
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        # Target user: goal 'fat loss', target_calories 2000
        self.user = models.User(
            name="Bob",
            email="bob@example.com",
            age=30,
            gender="male",
            height=180.0,
            weight=90.0,
            activity_level="sedentary",
            goal="fat loss",
            target_calories=2000.0,
            target_protein=150.0,
            target_carbs=200.0,
            target_fat=66.67
        )
        self.db.add(self.user)
        self.db.flush()

        # Seed adherence logs for the last 7 days (all True = high adherence)
        today = datetime.utcnow().date()
        for i in range(7):
            p = models.GeneratedMealPlan(
                user_id=self.user.id,
                plan_date=today - timedelta(days=i),
                adherence=True
            )
            self.db.add(p)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_low_adherence_no_adjustment(self):
        # Change adherence logs to False (low adherence)
        plans = self.db.query(models.GeneratedMealPlan).filter(models.GeneratedMealPlan.user_id == self.user.id).all()
        for p in plans:
            p.adherence = False
        self.db.commit()

        # Seed two weight logs showing no weight loss
        today = datetime.utcnow().date()
        self.db.add(models.WeightLog(user_id=self.user.id, weight=90.0, logged_at=today - timedelta(days=10)))
        self.db.add(models.WeightLog(user_id=self.user.id, weight=90.0, logged_at=today))
        self.db.commit()

        # Run planner
        res = AdaptivePlanner.track_and_adjust(self.db, self.user.id)
        self.assertEqual(res["status"], "warning")
        self.assertEqual(self.user.target_calories, 2000.0) # Unchanged

    def test_fat_loss_stalled_reduction(self):
        # Adherence is high (all True from setup)
        # Seed two weight logs showing weight stayed the same (90.0kg -> 90.0kg over 10 days)
        today = datetime.utcnow().date()
        self.db.add(models.WeightLog(user_id=self.user.id, weight=90.0, logged_at=today - timedelta(days=10)))
        self.db.add(models.WeightLog(user_id=self.user.id, weight=90.0, logged_at=today))
        self.db.commit()

        # Run planner - weight loss stalled, calorie target should be reduced by 150 kcal
        res = AdaptivePlanner.track_and_adjust(self.db, self.user.id)
        
        self.assertEqual(res["status"], "adjusted")
        self.assertEqual(res["new_calories"], 1850.0)
        self.assertEqual(self.user.target_calories, 1850.0)

        # Macros should also be re-split (fat loss: 30% Protein / 40% Carbs / 30% Fat)
        # Protein: 1850 * 0.3 / 4 = 138.75
        # Carbs: 1850 * 0.4 / 4 = 185.0
        # Fat: 1850 * 0.3 / 9 = 61.67
        self.assertAlmostEqual(self.user.target_protein, 138.75, places=2)
        self.assertAlmostEqual(self.user.target_carbs, 185.0, places=2)
        self.assertAlmostEqual(self.user.target_fat, 61.67, places=2)

    def test_weight_gain_stalled_increase(self):
        # Change goal to weight gain
        self.user.goal = "weight gain"
        self.user.target_calories = 2500.0
        self.db.commit()

        # Seed weight logs showing weight stayed same (90.0kg -> 90.0kg over 10 days)
        today = datetime.utcnow().date()
        self.db.add(models.WeightLog(user_id=self.user.id, weight=90.0, logged_at=today - timedelta(days=10)))
        self.db.add(models.WeightLog(user_id=self.user.id, weight=90.0, logged_at=today))
        self.db.commit()

        # Run planner - weight gain stalled, calorie target should increase by 200 kcal
        res = AdaptivePlanner.track_and_adjust(self.db, self.user.id)
        
        self.assertEqual(res["status"], "adjusted")
        self.assertEqual(res["new_calories"], 2700.0)
        self.assertEqual(self.user.target_calories, 2700.0)

if __name__ == "__main__":
    unittest.main()
