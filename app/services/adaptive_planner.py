from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import User, WeightLog, GeneratedMealPlan

class AdaptivePlanner:
    @classmethod
    def track_and_adjust(cls, db: Session, user_id: int) -> dict:
        """Analyze weight logs and meal plan adherence, and automatically adjust user targets if needed.
        
        Returns:
            Dict containing analysis results and adjustments made.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"status": "error", "message": "User not found"}

        # 1. Check Adherence in the last 7 days
        seven_days_ago = datetime.utcnow().date() - timedelta(days=7)
        plans = db.query(GeneratedMealPlan).filter(
            GeneratedMealPlan.user_id == user_id,
            GeneratedMealPlan.plan_date >= seven_days_ago
        ).all()

        adhered_days = 0
        logged_days = 0
        for p in plans:
            if p.adherence is not None:
                logged_days += 1
                if p.adherence:
                    adhered_days += 1

        adherence_rate = (adhered_days / logged_days) if logged_days > 0 else 0.0

        # 2. Check Weight logs in the last 14 days to calculate trend
        fourteen_days_ago = datetime.utcnow().date() - timedelta(days=14)
        weight_logs = db.query(WeightLog).filter(
            WeightLog.user_id == user_id,
            WeightLog.logged_at >= fourteen_days_ago
        ).order_by(WeightLog.logged_at.asc()).all()

        if len(weight_logs) < 2:
            return {
                "status": "info",
                "message": "Not enough weight logs to calculate trend. Need at least 2 logs in the last 14 days.",
                "adherence_rate": adherence_rate,
                "current_calories": user.target_calories
            }

        # Calculate weight change rate per week
        first_log = weight_logs[0]
        latest_log = weight_logs[-1]
        
        weight_diff = latest_log.weight - first_log.weight
        days_diff = (latest_log.logged_at - first_log.logged_at).days
        
        if days_diff <= 0:
            return {
                "status": "info",
                "message": "Weight logs are on the same day. Cannot calculate trend.",
                "adherence_rate": adherence_rate,
                "current_calories": user.target_calories
            }
            
        weight_change_per_week = (weight_diff / days_diff) * 7.0

        # 3. Decision Matrix based on Goal
        # Only adjust if adherence is high enough (e.g. >= 70%)
        # If adherence is low, warning the user is better than changing targets.
        adjustment = 0.0
        reason = ""
        goal_lower = user.goal.lower()

        if adherence_rate < 0.70:
            reason = f"Adherence is low ({adherence_rate:.1%}). Try to follow the plan more closely before adjusting targets."
            return {
                "status": "warning",
                "message": reason,
                "adherence_rate": adherence_rate,
                "weight_change_per_week": round(weight_change_per_week, 2),
                "current_calories": user.target_calories
            }

        # Target weekly change ranges:
        # fat loss: -0.5 to -1.0 kg/week
        # weight gain: +0.25 to +0.5 kg/week
        # muscle gain: +0.15 to +0.3 kg/week
        # maintenance: -0.2 to +0.2 kg/week
        if goal_lower == "fat loss":
            if weight_change_per_week > -0.20:
                # Weight loss stalled
                adjustment = -150.0
                reason = f"Weight loss stalled ({weight_change_per_week:+.2f} kg/week). Calorie target reduced by 150 kcal."
            elif weight_change_per_week < -1.50:
                # Losing weight too fast
                adjustment = 150.0
                reason = f"Weight loss too rapid ({weight_change_per_week:.2f} kg/week). Calorie target increased by 150 kcal for safety."
        elif goal_lower in ["weight gain", "muscle gain"]:
            if weight_change_per_week < 0.10:
                # Weight gain stalled
                adjustment = 200.0
                reason = f"Weight gain stalled ({weight_change_per_week:+.2f} kg/week). Calorie target increased by 200 kcal."
            elif weight_change_per_week > 0.80:
                # Gaining too fast
                adjustment = -150.0
                reason = f"Weight gain too rapid ({weight_change_per_week:+.2f} kg/week). Calorie target reduced by 150 kcal."
        else: # maintenance
            if weight_change_per_week > 0.40:
                adjustment = -100.0
                reason = f"Weight increasing on maintenance ({weight_change_per_week:+.2f} kg/week). Calorie target reduced by 100 kcal."
            elif weight_change_per_week < -0.40:
                adjustment = 100.0
                reason = f"Weight decreasing on maintenance ({weight_change_per_week:+.2f} kg/week). Calorie target increased by 100 kcal."

        # Apply adjustments if needed
        if adjustment != 0.0:
            old_calories = user.target_calories
            new_calories = old_calories + adjustment
            
            # Enforce safety floors based on gender
            min_calories = 1500.0 if (user.gender or "").lower() == "male" else 1200.0
            if new_calories < min_calories:
                new_calories = min_calories
                reason += f" (Capped at safety limit of {min_calories} kcal)"

            # Update User Targets
            user.target_calories = round(new_calories, 2)
            
            # Recalculate macro splits in grams
            if goal_lower == "fat loss":
                p_pct, c_pct, f_pct = 0.30, 0.40, 0.30
            elif goal_lower == "weight gain":
                p_pct, c_pct, f_pct = 0.25, 0.50, 0.25
            elif goal_lower == "muscle gain":
                p_pct, c_pct, f_pct = 0.30, 0.45, 0.25
            else: # maintenance
                p_pct, c_pct, f_pct = 0.25, 0.45, 0.30

            user.target_protein = round((user.target_calories * p_pct) / 4.0, 2)
            user.target_carbs = round((user.target_calories * c_pct) / 4.0, 2)
            user.target_fat = round((user.target_calories * f_pct) / 9.0, 2)
            
            db.commit()
            
            return {
                "status": "adjusted",
                "message": reason,
                "adherence_rate": adherence_rate,
                "weight_change_per_week": round(weight_change_per_week, 2),
                "old_calories": old_calories,
                "new_calories": user.target_calories,
                "new_protein_g": user.target_protein,
                "new_carbs_g": user.target_carbs,
                "new_fat_g": user.target_fat
            }

        return {
            "status": "stable",
            "message": "Weight and progress are on track. No calorie adjustment needed.",
            "adherence_rate": adherence_rate,
            "weight_change_per_week": round(weight_change_per_week, 2),
            "current_calories": user.target_calories
        }
