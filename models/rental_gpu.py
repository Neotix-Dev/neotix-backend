from utils.database import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON


class RentalGPU(db.Model):
    """A record of a GPU rental, tracking both current and historical rentals"""

    __tablename__ = "rental_gpus"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    cluster_id = db.Column(db.Integer, db.ForeignKey("clusters.id"), nullable=False)
    gpu_listing_id = db.Column(
        db.Integer, db.ForeignKey("gpu_listings.id"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Configuration and status
    configuration = db.Column(JSON, nullable=False)
    status = db.Column(
        db.String(20), default="pending", nullable=False
    )  # pending, active, completed
    ssh_keys = db.Column(JSON, nullable=True)
    email_enabled = db.Column(db.Boolean, default=True)

    # Timing information
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    cluster = db.relationship("Cluster", back_populates="rental_history")
    gpu_listing = db.relationship("GPUListing")
    user = db.relationship("User", back_populates="rental_gpus", lazy=True)

    def __init__(
        self,
        cluster_id,
        gpu_listing_id,
        user_id,
        configuration,
        ssh_keys=None,
        email_enabled=True,
    ):
        self.cluster_id = cluster_id
        self.gpu_listing_id = gpu_listing_id
        self.user_id = user_id
        self.configuration = configuration
        self.ssh_keys = ssh_keys or []
        self.email_enabled = email_enabled

    def to_dict(self):
        """Convert rental to dictionary representation"""
        gpu = self.gpu_listing
        gpu_config = gpu.configuration if gpu else None
        
        # Format times with UTC timezone
        start_time = self.start_time.strftime('%Y-%m-%dT%H:%M:%S+00:00') if self.start_time else None
        end_time = self.end_time.strftime('%Y-%m-%dT%H:%M:%S+00:00') if self.end_time else None
        created_at = self.created_at.strftime('%Y-%m-%dT%H:%M:%S+00:00') if self.created_at else None
        updated_at = self.updated_at.strftime('%Y-%m-%dT%H:%M:%S+00:00') if self.updated_at else None
        
        return {
            "id": self.id,
            "cluster_id": self.cluster_id,
            "gpu_listing_id": self.gpu_listing_id,
            "user_id": self.user_id,
            "configuration": self.configuration,
            "status": self.status,
            "ssh_keys": self.ssh_keys,
            "email_enabled": self.email_enabled,
            "start_time": start_time,
            "end_time": end_time,
            "created_at": created_at,
            "updated_at": updated_at,
            # Include GPU details
            "gpu_name": gpu_config.gpu_name if gpu_config else None,
            "gpu_vendor": gpu_config.gpu_vendor if gpu_config else None,
            "gpu_memory": gpu_config.gpu_memory if gpu_config else None,
            "gpu_count": gpu_config.gpu_count if gpu_config else None,
            "current_price": gpu.current_price if gpu else None,
            "provider": gpu.host.name if gpu and gpu.host else None,
        }

    @property
    def is_active(self):
        """Check if this rental is currently active"""
        return (
            self.status == "active"
            and self.start_time is not None
            and (self.end_time is None or self.end_time > datetime.utcnow())
        )
