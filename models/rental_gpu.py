from utils.database import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON
from utils.aws_utils import AWSManager
from typing import Dict
import time


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
    instance_id = db.Column(db.String(50), nullable=True)
    instance_details = db.Column(JSON, nullable=True)

    # Timing information
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    price = db.Column(db.Float, nullable=False)
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
        price,
        ssh_keys=None,
        email_enabled=True,
        instance_id=None,
        instance_details=None,
    ):
        self.cluster_id = cluster_id
        self.gpu_listing_id = gpu_listing_id
        self.user_id = user_id
        self.configuration = configuration
        self.price = price
        self.ssh_keys = ssh_keys or []
        self.email_enabled = email_enabled
        self.instance_id = instance_id
        self.instance_details = instance_details

    def update_status(self):
        """Update the rental status based on current time"""
        now = datetime.utcnow()
        if self.end_time and now > self.end_time:
            self.status = "completed"
            db.session.commit()
        return self.status

    def to_dict(self):
        """Convert rental to dictionary representation"""
        gpu = self.gpu_listing
        gpu_config = gpu.configuration if gpu else None

        # Format times with UTC timezone
        start_time = (
            self.start_time.strftime("%Y-%m-%dT%H:%M:%S+00:00")
            if self.start_time
            else None
        )
        end_time = (
            self.end_time.strftime("%Y-%m-%dT%H:%M:%S+00:00") if self.end_time else None
        )
        created_at = (
            self.created_at.strftime("%Y-%m-%dT%H:%M:%S+00:00")
            if self.created_at
            else None
        )
        updated_at = (
            self.updated_at.strftime("%Y-%m-%dT%H:%M:%S+00:00")
            if self.updated_at
            else None
        )

        return {
            "id": self.id,
            "cluster_id": self.cluster_id,
            "gpu_listing_id": self.gpu_listing_id,
            "user_id": self.user_id,
            "configuration": self.configuration,
            "status": self.update_status(),  # Get current status
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
            "price": self.price,
            "provider": gpu.host.name if gpu and gpu.host else None,
            "instance_id": self.instance_id,
            "instance_details": self.instance_details,
        }

    @property
    def is_active(self):
        """Check if this rental is currently active"""
        # For on-demand rentals, end_time is always None until terminated
        # A rental is active if status is 'active' and it has a start time
        return self.status == "active" and self.start_time is not None

    def deploy_aws_instance(self):
        """Deploy an AWS instance during cluster deployment."""
        from utils.aws_utils import AWSManager

        aws = AWSManager()
        
        # Generate a unique key name for this rental
        key_name = f"neotix-{self.id}-{int(time.time())}"

        try:
            print(f"Starting AWS instance provisioning for rental: {self.id}")
            print(f"Configuration: {self.configuration}")
            print(f"GPU Listing: {self.gpu_listing.to_dict() if self.gpu_listing else None}")

            # Create key pair first
            key_pair = aws.create_key_pair(key_name)
            private_key = key_pair['KeyMaterial']

            # Launch instance
            instance_id, instance_details = aws.launch_gpu_instance(
                gpu_config=self.configuration,
                key_name=key_name,
            )

            # Store SSH key and instance details
            self.ssh_keys = [{
                'private_key': private_key,
                'instance_id': instance_id,
                'instance_ip': instance_details['instance_ip'],
                'instance_dns': instance_details['instance_dns'],
                'instance_type': instance_details['instance_type']
            }]
            db.session.commit()

            return instance_details

        except Exception as e:
            print(f"Error provisioning AWS instance: {str(e)}")
            # Clean up key pair if it was created
            if 'key_pair' in locals():
                aws.delete_key_pair(key_name)
            raise

    def get_ssh_key(self):
        """Get SSH key and connection details for an existing instance."""
        if not self.ssh_keys or len(self.ssh_keys) == 0:
            raise Exception("No SSH keys found. Please deploy the instance first.")

        from utils.aws_utils import AWSManager
        aws = AWSManager()
        
        # Get instance details
        instance_id = self.ssh_keys[0].get('instance_id')
        if not instance_id:
            raise Exception("No instance ID found. Please deploy the instance first.")

        instance = aws.get_instance_by_id(instance_id)
        if not instance:
            raise Exception("Instance not found or not running. Please deploy a new instance.")

        return {
            'ssh_key': self.ssh_keys[0]['private_key'],
            'connection_details': {
                'instance_ip': instance.public_ip_address,
                'instance_dns': instance.public_dns_name,
                'instance_type': instance.instance_type,
                'gpu_configuration': self.configuration
            }
        }

    def terminate_aws_instance(self) -> None:
        """
        Terminate the AWS EC2 instance associated with this rental.
        """
        if self.instance_id:
            aws = AWSManager()
            aws.terminate_instance(self.instance_id)
            self.status = "completed"
            self.end_time = datetime.utcnow()
            db.session.commit()
