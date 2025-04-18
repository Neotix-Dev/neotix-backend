from flask import Blueprint, jsonify, g
from models.user import User
from models.transaction import Transaction
from models.cluster import Cluster
from models.rental_gpu import RentalGPU
from middleware.auth import require_auth
from utils.database import db
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from decimal import Decimal

bp = Blueprint("financial_dashboard", __name__)


@bp.route("", methods=["GET"])
@bp.route("/", methods=["GET"])
@require_auth()
def get_financial_dashboard():
    """Get comprehensive financial data for the dashboard"""
    try:
        # Get the user
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Get current date and first day of month
        now = datetime.utcnow()
        first_day_of_month = datetime(now.year, now.month, 1)
        first_day_of_prev_month = (first_day_of_month - timedelta(days=1)).replace(day=1)
        
        # Calculate date ranges for different periods
        last_7_days = now - timedelta(days=7)
        last_30_days = now - timedelta(days=30)
        last_90_days = now - timedelta(days=90)
        
        # Get user's current balance
        current_balance = user.balance
        
        # Get current month's costs
        current_month_costs = db.session.query(
            func.sum(Transaction.amount * -1).label('total')
        ).filter(
            Transaction.user_id == user.id,
            Transaction.created_at >= first_day_of_month,
            Transaction.amount < 0  # Only count negative transactions (expenses)
        ).scalar() or 0.0
        
        # Get previous month's costs
        previous_month_costs = db.session.query(
            func.sum(Transaction.amount * -1).label('total')
        ).filter(
            Transaction.user_id == user.id,
            Transaction.created_at >= first_day_of_prev_month,
            Transaction.created_at < first_day_of_month,
            Transaction.amount < 0  # Only count negative transactions (expenses)
        ).scalar() or 0.0
        
        # Calculate month-over-month change percentage
        if previous_month_costs > 0:
            mom_change_percentage = ((current_month_costs - previous_month_costs) / previous_month_costs) * 100
        else:
            mom_change_percentage = 100 if current_month_costs > 0 else 0
            
        # Get spending by time periods
        spending_7_days = db.session.query(
            func.sum(Transaction.amount * -1).label('total')
        ).filter(
            Transaction.user_id == user.id,
            Transaction.created_at >= last_7_days,
            Transaction.amount < 0
        ).scalar() or 0.0
        
        spending_30_days = db.session.query(
            func.sum(Transaction.amount * -1).label('total')
        ).filter(
            Transaction.user_id == user.id,
            Transaction.created_at >= last_30_days,
            Transaction.amount < 0
        ).scalar() or 0.0
        
        spending_90_days = db.session.query(
            func.sum(Transaction.amount * -1).label('total')
        ).filter(
            Transaction.user_id == user.id,
            Transaction.created_at >= last_90_days,
            Transaction.amount < 0
        ).scalar() or 0.0
        
        # Get daily spending for the last 30 days for trend analysis
        daily_spending_query = db.session.query(
            func.date(Transaction.created_at).label('date'),
            func.sum(Transaction.amount * -1).label('total')
        ).filter(
            Transaction.user_id == user.id,
            Transaction.created_at >= last_30_days,
            Transaction.amount < 0
        ).group_by(func.date(Transaction.created_at))
        
        daily_spending = []
        for date, total in daily_spending_query:
            daily_spending.append({
                'date': date.isoformat(),
                'amount': float(total)
            })
        
        # Sort by date
        daily_spending.sort(key=lambda x: x['date'])
        
        # Get top spending categories (based on transaction descriptions)
        top_spending_categories = db.session.query(
            Transaction.description,
            func.sum(Transaction.amount * -1).label('total')
        ).filter(
            Transaction.user_id == user.id,
            Transaction.created_at >= last_30_days,
            Transaction.amount < 0
        ).group_by(Transaction.description).order_by(desc('total')).limit(5).all()
        
        categories = []
        for description, total in top_spending_categories:
            # Skip if description is None
            if description is None:
                continue
                
            # Extract category from description
            # Example: "GPU Rental: A100 - 2 hours" -> "GPU Rental"
            category = description.split(':')[0] if ':' in description else description
            categories.append({
                'category': category,
                'amount': float(total)
            })
        
        # Get active rentals with ongoing costs
        active_rentals = db.session.query(RentalGPU).join(Cluster).filter(
            Cluster.user_id == user.id,
            RentalGPU.status == 'active',
            RentalGPU.start_time.isnot(None),
            RentalGPU.end_time.is_(None)
        ).all()
        
        active_costs = 0.0
        for rental in active_rentals:
            gpu = rental.gpu_listing
            if gpu and rental.start_time:
                # Calculate ongoing cost
                start_time = rental.start_time
                running_seconds = (now - start_time).total_seconds()
                running_hours = running_seconds / 3600
                hourly_rate = float(gpu.current_price) if gpu.current_price else 0.0
                
                # Apply tax and fees consistent with deployment
                base_cost = Decimal(str(running_hours * hourly_rate))
                tax_rate = Decimal('0.08')  # 8% tax
                platform_fee_rate = Decimal('0.05')  # 5% platform fee
                
                tax_amount = base_cost * tax_rate
                platform_fee_amount = base_cost * platform_fee_rate
                total_cost = float(base_cost + tax_amount + platform_fee_amount)
                
                active_costs += total_cost
        
        # Compile the response
        response = {
            'timestamp': now.isoformat(),
            'current_balance': float(current_balance),
            'current_month': {
                'costs': float(current_month_costs),
                'month_over_month_percentage': float(mom_change_percentage)
            },
            'spending_periods': {
                'last_7_days': float(spending_7_days),
                'last_30_days': float(spending_30_days),
                'last_90_days': float(spending_90_days)
            },
            'daily_spending_trend': daily_spending,
            'top_spending_categories': categories,
            'active_costs': float(active_costs)
        }
        
        return jsonify(response), 200

    except Exception as e:
        print(f"Error in get_financial_dashboard: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/budget", methods=["GET"])
@require_auth()
def get_user_budget():
    """Get user's budget settings and status"""
    try:
        # Get the user
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        # For now, return placeholder data
        # In a real implementation, this would be stored in a user_budget table
        now = datetime.utcnow()
        first_day_of_month = datetime(now.year, now.month, 1)
        
        # Get current month's costs
        current_month_costs = db.session.query(
            func.sum(Transaction.amount * -1).label('total')
        ).filter(
            Transaction.user_id == user.id,
            Transaction.created_at >= first_day_of_month,
            Transaction.amount < 0  # Only count negative transactions (expenses)
        ).scalar() or 0.0
        
        placeholder_budget = 500.0  # 500 USD monthly budget
        budget_used_percentage = (current_month_costs / placeholder_budget) * 100 if placeholder_budget > 0 else 0
        
        response = {
            'monthly_budget': placeholder_budget,
            'current_usage': float(current_month_costs),
            'percentage_used': float(budget_used_percentage),
            'remaining_budget': float(max(0, placeholder_budget - current_month_costs)),
            'budget_alerts': [
                {
                    'threshold': 50,
                    'triggered': budget_used_percentage >= 50,
                    'message': 'You have used 50% of your monthly budget'
                },
                {
                    'threshold': 80,
                    'triggered': budget_used_percentage >= 80,
                    'message': 'You have used 80% of your monthly budget'
                },
                {
                    'threshold': 100,
                    'triggered': budget_used_percentage >= 100,
                    'message': 'You have exceeded your monthly budget'
                }
            ]
        }
        
        return jsonify(response), 200

    except Exception as e:
        print(f"Error in get_user_budget: {str(e)}")
        return jsonify({"error": str(e)}), 500
