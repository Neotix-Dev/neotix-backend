from utils.database import db
from datetime import datetime

class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)  # Amount in dollars
    stripe_payment_id = db.Column(db.String(255), unique=True)
    status = db.Column(db.String(50), default="pending")  # pending, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.String(255))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "amount": self.amount,
            "stripe_payment_id": self.stripe_payment_id,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "description": self.description
        }
