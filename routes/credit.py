from flask import Blueprint, jsonify, request, g, current_app
from models.credit import Credit, CreditTransaction
from models.user import User
from utils.database import db
from middleware.auth import require_auth
import stripe
from datetime import datetime

bp = Blueprint("credit", __name__, url_prefix="/api/credit")

# Initialize Stripe with your secret key
stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]


@bp.route("/balance", methods=["GET"])
@require_auth()
def get_balance():
    """Get user's credit balance"""
    user = User.query.filter_by(firebase_uid=g.user_id).first()
    if not user or not user.credit:
        return jsonify({"balance": 0}), 200

    return (
        jsonify(
            {
                "balance": user.credit.balance / 100,  # Convert cents to dollars
                "updated_at": user.credit.updated_at.isoformat(),
            }
        ),
        200,
    )


@bp.route("/purchase", methods=["POST"])
@require_auth()
def create_purchase():
    """Create a credit purchase intent"""
    try:
        data = request.get_json()
        amount = int(float(data["amount"]) * 100)  # Convert dollars to cents

        if amount < 100:  # Minimum $1
            return jsonify({"error": "Minimum purchase amount is $1"}), 400

        user = User.query.filter_by(firebase_uid=g.user_id).first()

        # Create or get Stripe customer
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email, metadata={"firebase_uid": user.firebase_uid}
            )
            user.stripe_customer_id = customer.id
            db.session.commit()

        # Create payment intent
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency="usd",
            customer=user.stripe_customer_id,
            metadata={"type": "credit_purchase", "user_id": user.id},
        )

        return (
            jsonify({"client_secret": intent.client_secret, "amount": amount / 100}),
            200,
        )

    except Exception as e:
        current_app.logger.error(f"Error creating purchase: {str(e)}")
        return jsonify({"error": "Failed to create purchase"}), 500


@bp.route("/webhook", methods=["POST"])
def stripe_webhook():
    """Handle Stripe webhook events"""
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, current_app.config["STRIPE_WEBHOOK_SECRET"]
        )
    except Exception as e:
        return jsonify({"error": "Invalid webhook"}), 400

    if event.type == "payment_intent.succeeded":
        payment_intent = event.data.object

        if payment_intent.metadata.get("type") == "credit_purchase":
            user_id = int(payment_intent.metadata.get("user_id"))
            amount = payment_intent.amount  # Amount in cents

            try:
                # Start transaction
                user = User.query.get(user_id)
                if not user:
                    raise Exception(f"User {user_id} not found")

                # Create or update credit balance
                if not user.credit:
                    credit = Credit(user_id=user.id, balance=amount)
                    db.session.add(credit)
                else:
                    user.credit.balance += amount

                # Record transaction
                transaction = CreditTransaction(
                    user_id=user.id,
                    amount=amount,
                    transaction_type="purchase",
                    stripe_payment_id=payment_intent.id,
                    description=f"Credit purchase of ${amount/100:.2f}",
                )
                db.session.add(transaction)
                db.session.commit()

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error processing payment: {str(e)}")
                return jsonify({"error": "Failed to process payment"}), 500

    return jsonify({"status": "success"}), 200


@bp.route("/transactions", methods=["GET"])
@require_auth()
def get_transactions():
    """Get user's credit transactions"""
    user = User.query.filter_by(firebase_uid=g.user_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    transactions = (
        CreditTransaction.query.filter_by(user_id=user.id)
        .order_by(CreditTransaction.created_at.desc())
        .paginate(page=page, per_page=per_page)
    )

    return (
        jsonify(
            {
                "transactions": [tx.to_dict() for tx in transactions.items],
                "total": transactions.total,
                "pages": transactions.pages,
                "current_page": transactions.page,
            }
        ),
        200,
    )


@bp.route("/use", methods=["POST"])
@require_auth()
def use_credits():
    """Use credits for GPU rental"""
    try:
        data = request.get_json()
        amount = int(float(data["amount"]) * 100)  # Convert dollars to cents
        gpu_rental_id = data.get("gpu_rental_id")

        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user or not user.credit:
            return jsonify({"error": "No credits available"}), 400

        if user.credit.balance < amount:
            return jsonify({"error": "Insufficient credits"}), 400

        # Deduct credits and record transaction
        user.credit.balance -= amount
        transaction = CreditTransaction(
            user_id=user.id,
            amount=-amount,  # Negative amount for usage
            transaction_type="usage",
            gpu_rental_id=gpu_rental_id,
            description=f"GPU rental charge of ${amount/100:.2f}",
        )
        db.session.add(transaction)
        db.session.commit()

        return (
            jsonify(
                {
                    "success": True,
                    "remaining_balance": user.credit.balance / 100,
                    "transaction_id": transaction.id,
                }
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error using credits: {str(e)}")
        return jsonify({"error": "Failed to process credit usage"}), 500
