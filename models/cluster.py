from utils.database import db
from datetime import datetime
from models.gpu_listing import GPUListing

class Cluster(db.Model):
    __tablename__ = "clusters"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # One-to-one relationship with RentalGPU
    rental_gpu = db.relationship('RentalGPU', backref=db.backref('cluster', uselist=False), uselist=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'user_id': self.user_id,
            'rental_gpu': self.rental_gpu.to_dict() if self.rental_gpu else None
        }

class RentalGPU(GPUListing):
    """A GPU listing that can be rented with additional rental-specific attributes"""
    __tablename__ = 'rental_gpus'
    
    id = db.Column(db.Integer, db.ForeignKey('gpu_listings.id'), primary_key=True)
    cluster_id = db.Column(db.Integer, db.ForeignKey('clusters.id'), unique=True)
    ssh_keys = db.Column(db.JSON, nullable=True)  # Store multiple SSH keys as JSON
    email_enabled = db.Column(db.Boolean, default=True)
    rented = db.Column(db.Boolean, default=False)
    rental_start = db.Column(db.DateTime, nullable=True)
    rental_end = db.Column(db.DateTime, nullable=True)
    
    # Many-to-many relationship with users who have access
    users_with_access = db.relationship(
        'User',
        secondary='rental_gpu_users',
        backref=db.backref('accessible_gpus', lazy='dynamic')
    )

    __mapper_args__ = {
        'polymorphic_identity': 'rental_gpu',
    }

    def to_dict(self):
        base_dict = super().to_dict()
        rental_dict = {
            'ssh_keys': self.ssh_keys,
            'email_enabled': self.email_enabled,
            'rented': self.rented,
            'rental_start': self.rental_start.isoformat() if self.rental_start else None,
            'rental_end': self.rental_end.isoformat() if self.rental_end else None,
            'users_with_access': [user.id for user in self.users_with_access]
        }
        return {**base_dict, **rental_dict}

# Association table for RentalGPU and User many-to-many relationship
rental_gpu_users = db.Table('rental_gpu_users',
    db.Column('rental_gpu_id', db.Integer, db.ForeignKey('rental_gpus.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('added_at', db.DateTime, default=datetime.utcnow)
)
