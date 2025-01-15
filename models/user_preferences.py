from utils.database import db
from datetime import datetime

class RentedGPU(db.Model):
    __tablename__ = 'rented_gpus'
    
    id = db.Column(db.Integer, primary_key=True)
    gpu_id = db.Column(db.Integer, db.ForeignKey('gpu_listings.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    rental_start = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    rental_end = db.Column(db.DateTime, nullable=True)
    
    # Relationship with GPUListing
    gpu = db.relationship('GPUListing', backref='rentals')

    def to_dict(self):
        return {
            'id': self.gpu.id,
            'name': self.gpu.name,
            'isActive': self.is_active,
            'rentalStart': self.rental_start.isoformat(),
            'rentalEnd': self.rental_end.isoformat() if self.rental_end else None
        }

class PriceAlert(db.Model):
    __tablename__ = 'price_alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    gpu_id = db.Column(db.Integer, db.ForeignKey('gpu_listings.id'), nullable=True)  # Nullable for type-based alerts
    gpu_type = db.Column(db.String(255), nullable=True)  # For type-based alerts
    target_price = db.Column(db.Float, nullable=False)
    is_type_alert = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship with GPUListing (only for individual GPU alerts)
    gpu = db.relationship('GPUListing', backref='price_alerts')

    def to_dict(self):
        alert_id = f"type_{self.gpu_type}" if self.is_type_alert else str(self.gpu_id)
        return {
            alert_id: {
                'targetPrice': self.target_price,
                'isTypeAlert': self.is_type_alert,
                'gpuType': self.gpu_type if self.is_type_alert else None,
                'createdAt': self.created_at.isoformat()
            }
        }

class SelectedGPU(db.Model):
    __tablename__ = 'selected_gpus'
    
    id = db.Column(db.Integer, primary_key=True)
    gpu_id = db.Column(db.Integer, db.ForeignKey('gpu_listings.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    gpu = db.relationship('GPUListing', backref=db.backref('selected_by', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'gpu_id': self.gpu_id,
            'created_at': self.created_at.isoformat(),
            'gpu': self.gpu.to_dict() if self.gpu else None
        }

class FavoriteGPU(db.Model):
    __tablename__ = 'favorite_gpus'
    
    id = db.Column(db.Integer, primary_key=True)
    gpu_id = db.Column(db.Integer, db.ForeignKey('gpu_listings.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship with GPUListing
    gpu = db.relationship('GPUListing', backref='favorites')

    def to_dict(self):
        return {
            'id': self.gpu.id,
            'name': self.gpu.name,
            'host_name': self.gpu.host.name
        }
