from utils.database import db
from datetime import datetime


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    firebase_uid = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    email_verified = db.Column(db.Boolean, default=False)
    disabled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    organization = db.Column(db.String(255))
    first_name = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(255), nullable=False)
    experience_level = db.Column(db.String(50), default="beginner")
    referral_source = db.Column(db.String(50), default="")
    balance = db.Column(db.Float, default=0.0)  # User's balance in dollars
    stripe_customer_id = db.Column(db.String(255), unique=True)  # Stripe customer ID for saved payment methods

    # Relationships with preference models
    # rented_gpus = db.relationship("RentedGPU", backref=db.backref("user", lazy=True))
    # price_alerts = db.relationship("PriceAlert", backref=db.backref("user", lazy=True))
    # selected_gpus = db.relationship("SelectedGPU", backref=db.backref("user", lazy=True))
    # favorite_gpus = db.relationship("FavoriteGPU", backref=db.backref("user", lazy=True))

    # Add projects relationship
    projects = db.relationship("Project", backref="user", lazy=True)
    
    # Add transactions relationship
    transactions = db.relationship("Transaction", backref="user", lazy=True)

    def __repr__(self):
        return f"<User {self.email}>"

    def to_dict(self):
        """Convert user object to dictionary"""
        return {
            "id": self.id,
            "firebase_uid": self.firebase_uid,
            "email": self.email,
            "organization": self.organization,
            "email_verified": self.email_verified,
            "disabled": self.disabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "experience_level": self.experience_level,
            "referral_source": self.referral_source,
            "balance": self.balance,
            "stripe_customer_id": self.stripe_customer_id,
            "projects": [project.to_dict() for project in self.projects],
            "transactions": [transaction.to_dict() for transaction in self.transactions]
        }

    @staticmethod
    def from_firebase_user(firebase_user):
        """Create or update user from Firebase user data"""
        return {
            "firebase_uid": firebase_user["uid"],
            "email": firebase_user.get("email"),
            "first_name": firebase_user.get("name", "").split()[0],
            "last_name": " ".join(firebase_user.get("name", "").split()[1:]),
            "email_verified": firebase_user.get("email_verified", False),
            "disabled": firebase_user.get("disabled", False),
        }
