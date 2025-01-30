from flask import Blueprint, request, jsonify
from models.transaction import Transaction
from models.user import User
from utils.database import db
from middleware.auth import auth_required
import stripe
import os
from flask_cors import cross_origin

bp = Blueprint("transactions", __name__)

# Initialize Stripe with your secret key
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")


@bp.route("/", methods=["GET"])
@auth_required
def get_transactions(current_user):
    """Get all transactions for the current user"""
    try:
        transactions = (
            Transaction.query.filter_by(user_id=current_user.id)
            .order_by(Transaction.created_at.desc())
            .all()
        )
        print(transactions)
        return jsonify([transaction.to_dict() for transaction in transactions]), 200
    except Exception as e:
        print(f"Error getting transactions: {str(e)}")
        return jsonify({"error": "Failed to get transactions"}), 500


@bp.route("/create-payment-intent", methods=["POST"])
@auth_required
def create_payment_intent(current_user):
    """Create a Stripe PaymentIntent for adding funds"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        amount = data.get("amount")  # Amount in dollars

        if not amount or amount <= 0:
            return jsonify({"error": "Invalid amount"}), 400

        # Create a PaymentIntent with the order amount and currency
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency="usd",
                metadata={"user_id": current_user.id},
                automatic_payment_methods={
                    "enabled": True
                },  # Enable automatic payment methods
            )
        except stripe.error.StripeError as e:
            print(f"Stripe error: {str(e)}")
            return jsonify({"error": str(e)}), 400

        # Create a pending transaction
        transaction = Transaction(
            user_id=current_user.id,
            amount=amount,
            stripe_payment_id=intent.id,
            description=f"Add ${amount} to balance",
        )
        db.session.add(transaction)
        db.session.commit()

        # Return only the necessary data
        return (
            jsonify(
                {"clientSecret": intent.client_secret, "transactionId": transaction.id}
            ),
            200,
        )
    except Exception as e:
        print(f"Error creating payment intent: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Failed to create payment intent"}), 500


@bp.route("/confirm", methods=["POST"])
@auth_required
def confirm_transaction(current_user):
    """Confirm a successful transaction and update user's balance"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        payment_intent_id = data.get("paymentIntentId")

        if not payment_intent_id:
            return jsonify({"error": "Payment intent ID is required"}), 400

        # Get the transaction
        transaction = Transaction.query.filter_by(
            stripe_payment_id=payment_intent_id, user_id=current_user.id
        ).first()

        if not transaction:
            return jsonify({"error": "Transaction not found"}), 404

        try:
            # Verify payment intent status
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        except stripe.error.StripeError as e:
            print(f"Stripe error: {str(e)}")
            transaction.status = "failed"
            db.session.commit()
            return jsonify({"error": str(e)}), 400

        if payment_intent.status != "succeeded":
            transaction.status = "failed"
            db.session.commit()
            return jsonify({"error": "Payment has not succeeded"}), 400

        # Update transaction status and user balance
        transaction.status = "completed"
        current_user.balance += transaction.amount
        db.session.commit()

        return (
            jsonify(
                {
                    "message": "Payment confirmed successfully",
                    "transaction": transaction.to_dict(),
                    "newBalance": current_user.balance,
                }
            ),
            200,
        )
    except Exception as e:
        print(f"Error confirming transaction: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Failed to confirm transaction"}), 500
