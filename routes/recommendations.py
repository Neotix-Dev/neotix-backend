from flask import Blueprint, jsonify, g
from models.user import User
from models.transaction import Transaction
from models.cluster import Cluster
from models.rental_gpu import RentalGPU
from middleware.auth import require_auth
from utils.database import db
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import logging

bp = Blueprint("recommendations", __name__)


@bp.route("", methods=["GET"])
@bp.route("/", methods=["GET"])
@require_auth()
def get_recommendations():
    """Get personalized recommendations based on user's activity and usage patterns"""
    try:
        # Get the user
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Initialize recommendations list
        recommendations = []
        
        # Get current date for reference
        now = datetime.utcnow()
        
        # Get active clusters for the user
        active_clusters = Cluster.query.filter_by(user_id=user.id).all()
        active_rentals = RentalGPU.query.join(Cluster).filter(
            Cluster.user_id == user.id,
            RentalGPU.is_active == True
        ).all()
        
        # 1. Check for cost optimization opportunities (low utilization GPUs)
        low_util_gpus = [r for r in active_rentals if r.last_utilization < 30]  # Using 30% as threshold
        if len(low_util_gpus) >= 2:
            # If multiple GPUs have low utilization, recommend optimization
            recommendations.append({
                "id": "cost_opt_1",
                "type": "cost_saving",
                "title": f"Optimize your {low_util_gpus[0].gpu_listing.gpu_name} usage",
                "description": f"Running {len(low_util_gpus)} GPUs at low utilization. Consider downgrading to save up to 40% on costs.",
                "action_text": "View optimization options",
                "action_url": "/recommendations/optimize",
                "impact": {"value": 40, "unit": "percent", "direction": "decrease"},
                "priority": "high"
            })
        
        # 2. Check for performance optimization (memory-constrained jobs)
        memory_constrained = False
        for rental in active_rentals:
            if rental.last_memory_usage > 90:  # >90% memory usage
                memory_constrained = True
                break
                
        if memory_constrained:
            recommendations.append({
                "id": "perf_opt_1",
                "type": "performance",
                "title": "Upgrade memory for better performance",
                "description": "Your training jobs are memory-constrained. Adding more RAM could reduce training time by 35%.",
                "action_text": "View upgrade options",
                "action_url": "/recommendations/upgrade",
                "impact": {"value": 35, "unit": "percent", "direction": "increase"},
                "priority": "medium"
            })
        
        # 3. Check spending patterns with on-demand model
        # Get transactions from last 30 days
        thirty_days_ago = now - timedelta(days=30)
        recent_transactions = Transaction.query.filter(
            Transaction.user_id == user.id,
            Transaction.created_at >= thirty_days_ago,
            Transaction.transaction_type == "rental"
        ).all()
        
        total_spent = sum(t.amount for t in recent_transactions if t.amount < 0)
        
        # If spending is high, recommend reserved instances
        if total_spent > 500:  # $500 threshold for example
            recommendations.append({
                "id": "cost_opt_2",
                "type": "cost_saving",
                "title": "Consider reserved instances for cost savings",
                "description": f"You've spent ${abs(total_spent):.2f} in the last 30 days on on-demand rentals. Switch to reserved instances to save up to 60%.",
                "action_text": "View reserved plans",
                "action_url": "/recommendations/reserved",
                "impact": {"value": 60, "unit": "percent", "direction": "decrease"},
                "priority": "high"
            })
        
        # 4. Check for newer GPU availability that might be suited for the user's workloads
        # This would ideally check what types of workloads the user is running
        # For the example, we'll just recommend A100 GPUs if they're not using any
        user_using_a100 = any(r.gpu_listing and "A100" in r.gpu_listing.gpu_name for r in active_rentals)
        
        if not user_using_a100:
            recommendations.append({
                "id": "avail_1",
                "type": "availability",
                "title": "A100 GPUs now available in your region",
                "description": "NVIDIA A100 GPUs are now available with our on-demand billing model. Perfect for large training jobs.",
                "action_text": "Deploy an A100 cluster",
                "action_url": "/clusters/new?gpu=a100",
                "impact": {"value": 0, "unit": "", "direction": ""},
                "priority": "low"
            })
            
        # 5. If the user has no active clusters but has used them before, suggest creating one
        if len(active_clusters) == 0 and len(recent_transactions) > 0:
            recommendations.append({
                "id": "usage_1",
                "type": "usage",
                "title": "Resume your AI training",
                "description": "You don't have any active clusters. Deploy a new one to continue your work.",
                "action_text": "Deploy a cluster",
                "action_url": "/clusters/new",
                "impact": {"value": 0, "unit": "", "direction": ""},
                "priority": "medium"
            })
            
        # Return the recommendations, sorted by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 3))
        
        return jsonify({
            "recommendations": recommendations,
            "last_refreshed": now.isoformat()
        }), 200

    except Exception as e:
        logging.error(f"Error in get_recommendations: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/dismiss/<recommendation_id>", methods=["POST"])
@require_auth()
def dismiss_recommendation(recommendation_id):
    """Dismiss a recommendation so it won't be shown again"""
    try:
        # Get the user
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        # In a real implementation, this would store the dismissed recommendation ID
        # in a database table associated with the user
        # For this example, we'll just return success
        
        return jsonify({
            "message": f"Recommendation {recommendation_id} dismissed successfully",
            "success": True
        }), 200
        
    except Exception as e:
        logging.error(f"Error in dismiss_recommendation: {str(e)}")
        return jsonify({"error": str(e)}), 500
