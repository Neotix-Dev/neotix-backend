from utils.database import db
from datetime import datetime
from models.gpu_listing import GPUListing
from models.rental_gpu import RentalGPU
from datetime import timedelta


class Cluster(db.Model):
    __tablename__ = "clusters"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    current_gpu_id = db.Column(
        db.Integer, db.ForeignKey("gpu_listings.id"), nullable=True
    )

    # Relationship with current GPU
    current_gpu = db.relationship("GPUListing", foreign_keys=[current_gpu_id])

    # Relationship with RentalGPU - one cluster can have many rentals (history)
    rental_history = db.relationship(
        "RentalGPU",
        back_populates="cluster",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    @property
    def active_rental(self):
        """Get the currently active GPU rental for this cluster, if any"""
        now = datetime.utcnow()
        return self.rental_history.filter(
            db.and_(
                RentalGPU.status == "active",
                db.or_(RentalGPU.end_time.is_(None), RentalGPU.end_time > now),
            )
        ).first()

    def deploy_current_gpu(self, ssh_keys=None, email_enabled=True, duration_hours=24, config=None):
        """Deploy the current GPU, converting it to a rental"""

        if not self.current_gpu:
            raise ValueError("No GPU assigned to deploy")

        if self.active_rental:
            raise ValueError("Cluster already has an active rental")

        # Get current GPU configuration
        gpu = self.current_gpu
        gpu_config = gpu.configuration if gpu else None

        # Merge GPU config with user config
        base_config = {
            "gpu_name": gpu_config.gpu_name if gpu_config else None,
            "gpu_vendor": gpu_config.gpu_vendor if gpu_config else None,
            "gpu_memory": gpu_config.gpu_memory if gpu_config else None,
            "gpu_count": gpu_config.gpu_count if gpu_config else None,
            "cpu": gpu_config.cpu if gpu_config else None,
            "memory": gpu_config.memory if gpu_config else None,
            "disk_size": gpu_config.disk_size if gpu_config else None,
        }

        # Update with user config if provided
        if config:
            base_config.update(config)

        rental_gpu = RentalGPU(
            cluster_id=self.id,
            gpu_listing_id=self.current_gpu_id,
            user_id=self.user_id,
            price=gpu.current_price,
            configuration=base_config,
            ssh_keys=ssh_keys or [],
            email_enabled=email_enabled,
        )

        rental_gpu.status = "active"
        # Use UTC for both start and end time
        now = datetime.utcnow()
        rental_gpu.start_time = now.replace(tzinfo=None)  # Ensure no timezone info
        rental_gpu.end_time = (now + timedelta(hours=duration_hours)).replace(
            tzinfo=None
        )  # Ensure no timezone info

        # Clear the current GPU since it's now a rental
        # self.current_gpu_id = None

        return rental_gpu

    def to_dict(self):
        """Convert cluster to dictionary representation"""
        active_rental = self.active_rental
        current_gpu = self.current_gpu.to_dict() if self.current_gpu else None
        rental_history = [
            rental.to_dict()
            for rental in self.rental_history.order_by(RentalGPU.start_time.desc())
        ]

        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "user_id": self.user_id,
            "current_gpu": current_gpu,
            "rental_gpu": active_rental.to_dict() if active_rental else None,
            "rental_history": rental_history,
        }
