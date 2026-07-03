from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy import func
from app.models import MealLog, WaterLog, WeightLog, Analytics, User

class AnalyticsEngine:
    @classmethod
    def calculate_and_save_metrics(cls, db: Session, user_id: int) -> Dict[str, Any]:
        """Aggregate user data for the past 7, 30, and 90 days and cache summaries in the analytics table."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"status": "error", "message": "User not found"}

        now = datetime.utcnow().date()
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)

        # 1. Weight logs and trend
        weight_logs = db.query(WeightLog).filter(
            WeightLog.user_id == user_id
        ).order_by(WeightLog.logged_at.asc()).all()

        weight_change = 0.0
        weight_rate_per_week = 0.0
        latest_weight = user.weight or 0.0

        if len(weight_logs) >= 2:
            first_log = weight_logs[0]
            latest_log = weight_logs[-1]
            latest_weight = latest_log.weight
            weight_change = latest_log.weight - first_log.weight
            days_diff = (latest_log.logged_at - first_log.logged_at).days
            if days_diff > 0:
                weight_rate_per_week = (weight_change / days_diff) * 7.0

        # 2. Meal Log Averages (past 7 days)
        weekly_meal_stats = db.query(
            func.avg(MealLog.calories).label("avg_cal"),
            func.avg(MealLog.protein).label("avg_prot"),
            func.avg(MealLog.carbs).label("avg_carb"),
            func.avg(MealLog.fat).label("avg_fat")
        ).filter(
            MealLog.user_id == user_id,
            MealLog.log_date >= seven_days_ago
        ).first()

        avg_cal_weekly = float(weekly_meal_stats.avg_cal or 0.0)
        avg_prot_weekly = float(weekly_meal_stats.avg_prot or 0.0)
        avg_carb_weekly = float(weekly_meal_stats.avg_carb or 0.0)
        avg_fat_weekly = float(weekly_meal_stats.avg_fat or 0.0)

        # 3. Water Log Averages (past 7 days)
        # We group by date to find daily sum first
        daily_water = db.query(
            WaterLog.logged_at,
            func.sum(WaterLog.amount_ml).label("daily_total")
        ).filter(
            WaterLog.user_id == user_id,
            WaterLog.logged_at >= seven_days_ago
        ).group_by(WaterLog.logged_at).all()

        avg_water_weekly = 0.0
        if daily_water:
            avg_water_weekly = sum(w.daily_total for w in daily_water) / len(daily_water)

        # 4. Save to historical analytics table
        metrics = {
            "calories_weekly_avg": avg_cal_weekly,
            "protein_weekly_avg": avg_prot_weekly,
            "carbs_weekly_avg": avg_carb_weekly,
            "fat_weekly_avg": avg_fat_weekly,
            "water_weekly_avg": avg_water_weekly,
            "weight_trend": weight_rate_per_week,
            "latest_weight": latest_weight
        }

        # Clear older cached entries for today to avoid duplicates
        db.query(Analytics).filter(
            Analytics.user_id == user_id,
            Analytics.recorded_at == now
        ).delete()

        # Insert new metrics
        for name, value in metrics.items():
            db_metric = Analytics(
                user_id=user_id,
                metric_name=name,
                metric_value=value,
                recorded_at=now
            )
            db.add(db_metric)
        db.commit()

        # Return full dictionary
        return {
            "user_id": user_id,
            "calculated_at": str(now),
            "targets": {
                "calories": user.target_calories,
                "protein_g": user.target_protein,
                "carbs_g": user.target_carbs,
                "fat_g": user.target_fat
            },
            "averages_7_days": {
                "calories": round(avg_cal_weekly, 2),
                "protein_g": round(avg_prot_weekly, 2),
                "carbs_g": round(avg_carb_weekly, 2),
                "fat_g": round(avg_fat_weekly, 2),
                "water_ml": round(avg_water_weekly, 2)
            },
            "weight_stats": {
                "latest_weight_kg": latest_weight,
                "total_change_kg": round(weight_change, 2),
                "rate_kg_per_week": round(weight_rate_per_week, 2)
            }
        }

    @classmethod
    def get_historical_metrics(cls, db: Session, user_id: int, metric_name: str, limit: int = 30) -> List[Dict[str, Any]]:
        """Fetch cached history of a specific metric."""
        history = db.query(Analytics).filter(
            Analytics.user_id == user_id,
            Analytics.metric_name == metric_name
        ).order_by(Analytics.recorded_at.desc()).limit(limit).all()

        return [
            {"date": str(h.recorded_at), "value": h.metric_value}
            for h in history
        ]
