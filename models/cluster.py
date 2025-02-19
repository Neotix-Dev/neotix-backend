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

    def deploy_current_gpu(self, ssh_keys=None, email_enabled=True, duration_hours=24):
        """Deploy the current GPU, converting it to a rental"""

        if not self.current_gpu:
            raise ValueError("No GPU assigned to deploy")

        if self.active_rental:
            raise ValueError("Cluster already has an active rental")

        # Get current GPU configuration
        gpu = self.current_gpu
        config = gpu.configuration if gpu else None

        rental_gpu = RentalGPU(
            cluster_id=self.id,
            gpu_listing_id=self.current_gpu_id,
            user_id=self.user_id,
            price=gpu.current_price,
            configuration={
                "gpu_name": config.gpu_name if config else None,
                "gpu_vendor": config.gpu_vendor if config else None,
                "gpu_memory": config.gpu_memory if config else None,
                "gpu_count": config.gpu_count if config else None,
                "cpu": config.cpu if config else None,
                "memory": config.memory if config else None,
                "disk_size": config.disk_size if config else None,
            },
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
