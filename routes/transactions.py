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
        return jsonify([transaction.to_dict() for transaction in transactions]), 200
    except Exception as e:
        print(f"Error getting transactions: {str(e)}")
        return jsonify({"error": "Failed to get transactions"}), 500


def get_or_create_customer(user):
    """Get existing Stripe customer or create a new one"""
    if user.stripe_customer_id:
        try:
            # Verify the customer still exists
            customer = stripe.Customer.retrieve(user.stripe_customer_id)
            if not getattr(customer, "deleted", False):
                return customer
        except stripe.error.InvalidRequestError:
            # Customer was deleted or not found
            pass

    # Create new customer
    customer = stripe.Customer.create(
        email=user.email,
        metadata={
            "user_id": user.id,
            "firebase_uid": user.firebase_uid
        },
        name=f"{user.first_name} {user.last_name}"
    )
    
    # Save customer ID to user
    user.stripe_customer_id = customer.id
    db.session.commit()
    
    return customer


@bp.route("/payment-methods", methods=["GET"])
@auth_required
def get_payment_methods(current_user):
    """Get saved payment methods for the current user"""
    try:
        if not current_user.stripe_customer_id:
            return jsonify([]), 200

        payment_methods = stripe.PaymentMethod.list(
            customer=current_user.stripe_customer_id,
            type="card"
        )
        
        return jsonify([{
            'id': pm.id,
            'brand': pm.card.brand,
            'last4': pm.card.last4,
            'exp_month': pm.card.exp_month,
            'exp_year': pm.card.exp_year
        } for pm in payment_methods.data]), 200
    except Exception as e:
        print(f"Error getting payment methods: {str(e)}")
        return jsonify({"error": "Failed to get payment methods"}), 500


@bp.route("/create-payment-intent", methods=["POST"])
@auth_required
def create_payment_intent(current_user):
    """Create a Stripe PaymentIntent for adding funds"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        amount = data.get("amount")  # Amount in dollars
        payment_method_id = data.get("payment_method_id")  # Optional, for saved payment methods

        if not amount or amount <= 0:
            return jsonify({"error": "Invalid amount"}), 400

        # Get or create Stripe customer
        customer = get_or_create_customer(current_user)

        # Create a PaymentIntent
        intent_data = {
            "amount": int(amount * 100),  # Convert to cents
            "currency": "usd",
            "customer": customer.id,
            "metadata": {"user_id": current_user.id},
        }

        # If using a saved payment method
        if payment_method_id:
            intent_data["payment_method"] = payment_method_id
            intent_data["off_session"] = True
            intent_data["confirm"] = True
        else:
            intent_data["automatic_payment_methods"] = {"enabled": True}
            intent_data["setup_future_usage"] = "off_session"  # Allow saving payment method

        try:
            intent = stripe.PaymentIntent.create(**intent_data)
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

        return jsonify({
            "clientSecret": intent.client_secret,
            "transactionId": transaction.id,
            "requiresAction": intent.status == "requires_action",
            "paymentIntentId": intent.id
        }), 200

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
        save_payment_method = data.get("savePaymentMethod", False)

        if not payment_intent_id:
            return jsonify({"error": "Payment intent ID is required"}), 400

        # Get the payment intent
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            # Verify this payment intent belongs to this customer
            if payment_intent.customer != current_user.stripe_customer_id:
                return jsonify({"error": "Unauthorized"}), 403

            if payment_intent.status != "succeeded":
                return jsonify({"error": "Payment not successful"}), 400

            # If requested, save the payment method
            if save_payment_method and payment_intent.payment_method:
                stripe.PaymentMethod.attach(
                    payment_intent.payment_method,
                    customer=current_user.stripe_customer_id,
                )

        except stripe.error.StripeError as e:
            print(f"Stripe error: {str(e)}")
            return jsonify({"error": str(e)}), 400

        # Get and update the transaction
        transaction = Transaction.query.filter_by(
            stripe_payment_id=payment_intent_id,
            user_id=current_user.id
        ).first()

        if not transaction:
            return jsonify({"error": "Transaction not found"}), 404

        if transaction.status == "completed":
            return jsonify({"error": "Transaction already completed"}), 400

        # Update transaction and user balance
        transaction.status = "completed"
        current_user.balance += transaction.amount
        db.session.commit()

        return jsonify({"message": "Transaction completed successfully"}), 200

    except Exception as e:
        print(f"Error confirming transaction: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Failed to confirm transaction"}), 500
