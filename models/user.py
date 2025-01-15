from utils.database import db
from datetime import datetime


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    firebase_uid = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), nullable=False)
    organization = db.Column(db.String(255))
    email_verified = db.Column(db.Boolean, default=False)
    disabled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    first_name = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(255), nullable=False)
    experience_level = db.Column(db.String(50), default="beginner")
    referral_source = db.Column(db.String(50), default="")

    # Relationships with preference models
    # rented_gpus = db.relationship("RentedGPU", backref=db.backref("user", lazy=True))
    # price_alerts = db.relationship("PriceAlert", backref=db.backref("user", lazy=True))
    # selected_gpus = db.relationship("SelectedGPU", backref=db.backref("user", lazy=True))
    # favorite_gpus = db.relationship("FavoriteGPU", backref=db.backref("user", lazy=True))

    # Add projects relationship
    projects = db.relationship('Project', backref='user', lazy=True)

    def __repr__(self):
        return f"<User {self.email}>"

    def to_dict(self):
        return {
            "id": self.id,
            "firebase_uid": self.firebase_uid,
            "email": self.email,
            "organization": self.organization,
            "email_verified": self.email_verified,
            "disabled": self.disabled,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat(),
            "first_name": self.first_name,
            "last_name": self.last_name,
            "experience_level": self.experience_level,
            "referral_source": self.referral_source,
            "projects": [project.to_dict() for project in self.projects]
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
