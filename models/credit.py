from utils.database import db
from datetime import datetime


class Credit(db.Model):
    __tablename__ = "credits"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    balance = db.Column(db.Integer, default=0)  # Store credits in cents
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "balance": self.balance / 100,  # Convert cents to dollars
            "updated_at": self.updated_at.isoformat()
        }


class CreditTransaction(db.Model):
    __tablename__ = "credit_transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)  # Can be positive (purchase) or negative (usage)
    transaction_type = db.Column(db.String(50), nullable=False)  # 'purchase', 'usage', 'refund'
    stripe_payment_id = db.Column(db.String(255))  # For purchases
    gpu_rental_id = db.Column(db.Integer, db.ForeignKey('rented_gpus.id'))  # For usage
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='completed')
    description = db.Column(db.String(255))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "amount": self.amount / 100,  # Convert cents to dollars
            "transaction_type": self.transaction_type,
            "stripe_payment_id": self.stripe_payment_id,
            "gpu_rental_id": self.gpu_rental_id,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "description": self.description
        }
