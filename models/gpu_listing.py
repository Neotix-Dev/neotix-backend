from utils.database import db 
from datetime import datetime, timezone
import math


class Host(db.Model):
    __tablename__ = "hosts"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    url = db.Column(db.String(255), nullable=True)

    def __init__(self, name, description=None, url=None):
        self.name = name
        self.description = description
        self.url = url

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "url": self.url,
        }


class GPUConfiguration(db.Model):
    """Hardware configuration for GPU instances"""

    __tablename__ = "gpu_configurations"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    hash = db.Column(db.String(64), unique=True, nullable=False)  # SHA-256 hash
    gpu_name = db.Column(db.String(255), nullable=True)
    gpu_vendor = db.Column(db.String(50), nullable=True)
    gpu_count = db.Column(db.Integer, nullable=False)
    gpu_memory = db.Column(db.Float, nullable=True)
    cpu = db.Column(db.Integer, nullable=True)
    memory = db.Column(db.Float, nullable=True)
    disk_size = db.Column(db.Float, nullable=True)
    gpu_score = db.Column(db.Float, nullable=True)

    # Relationships
    listings = db.relationship("GPUListing", backref="configuration", lazy="dynamic")
    price_history = db.relationship(
        "GPUPriceHistory", backref="configuration", lazy="dynamic"
    )

    def __init__(
        self, hash, gpu_name, gpu_vendor, gpu_count, gpu_memory, cpu, memory, disk_size
    ):
        self.hash = hash
        self.gpu_name = gpu_name
        self.gpu_vendor = gpu_vendor
        self.gpu_count = gpu_count
        self.gpu_memory = gpu_memory
        self.cpu = cpu
        self.memory = memory
        self.disk_size = disk_size
        self.gpu_score = self.compute_gpu_score()

    def compute_gpu_score(self):
        """Compute a score for the GPU configuration"""
        return GPUListing.compute_gpu_score(
            self.gpu_name, self.gpu_vendor, self.gpu_memory, self.gpu_count
        )

    def to_dict(self):
        return {
            "id": self.id,
            "hash": self.hash,
            "gpu_name": self.gpu_name,
            "gpu_vendor": self.gpu_vendor,
            "gpu_count": self.gpu_count,
            "gpu_memory": self.gpu_memory,
            "cpu": self.cpu,
            "memory": self.memory,
            "disk_size": self.disk_size,
            "gpu_score": self.gpu_score,
        }


class GPUListing(db.Model):
    __tablename__ = "gpu_listings"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    instance_name = db.Column(db.String(255), nullable=False)
    configuration_id = db.Column(
        db.Integer, db.ForeignKey("gpu_configurations.id"), nullable=False
    )
    current_price = db.Column(db.Float, nullable=False)
    price_change = db.Column(db.String(10), nullable=False, default="0%")
    host_id = db.Column(db.Integer, db.ForeignKey('hosts.id'), nullable=False)
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))

    # Relationships
    host = db.relationship("Host", backref="listings")
    price_points = db.relationship("GPUPricePoint", backref="gpu", lazy="dynamic")

    def __init__(self, instance_name, configuration_id, current_price, host_id):
        self.instance_name = instance_name
        self.configuration_id = configuration_id
        self.current_price = current_price
        self.host_id = host_id
        self.last_updated = datetime.now(timezone.utc)

    @staticmethod
    def compute_gpu_score(gpu_name, gpu_vendor, gpu_memory, gpu_count):
        """Compute a score for the GPU based on various factors including performance and value."""
        if not gpu_name or not gpu_memory or not gpu_count:
            return 0.0

        # Base score from VRAM and count
        # VRAM is important but shouldn't be linear - logarithmic scaling
        memory_score = 20 * math.log2(gpu_memory + 1)  # +1 to avoid log(0)
        count_score = 10 * math.log2(
            gpu_count + 1
        )  # Diminishing returns for multiple GPUs
        base_score = memory_score + count_score

        # Vendor multiplier - adjusted to be more balanced
        vendor_multiplier = {
            "NVIDIA": 1.0,  # NVIDIA still preferred for ML workloads
            "AMD": 0.9,  # AMD improved but still slightly behind in ML
            "GOOGLE": 0.95,  # Cloud GPUs are well optimized
        }.get(gpu_vendor, 0.85)

        # Architecture multiplier based on GPU generation
        # Newer architectures should have higher multipliers
        gpu_name = gpu_name.upper()
        arch_multiplier = 1.0

        # Latest Data Center GPUs
        if "H100" in gpu_name:
            arch_multiplier = 2.0
        elif "A100" in gpu_name:
            arch_multiplier = 1.8
        # Consumer GPUs - newer should have higher multipliers
        elif "RTX" in gpu_name:
            if "40" in gpu_name:
                arch_multiplier = 1.7
            elif "30" in gpu_name:
                arch_multiplier = 1.5
            elif "20" in gpu_name:
                arch_multiplier = 1.3
        # Older Data Center GPUs
        elif "V100" in gpu_name:
            arch_multiplier = 1.4
        elif "T4" in gpu_name:
            arch_multiplier = 1.2
        elif "P100" in gpu_name:
            arch_multiplier = 1.1
        elif "K80" in gpu_name:
            arch_multiplier = 0.9

        # Memory type multiplier - adjusted to be more subtle
        memory_multiplier = 1.0
        if "HBM" in gpu_name:
            memory_multiplier = 1.15
        elif any(x in gpu_name for x in ["A100", "H100", "V100"]):  # These use HBM2
            memory_multiplier = 1.15
        elif "4090" in gpu_name or "3090" in gpu_name:  # These use GDDR6X
            memory_multiplier = 1.1

        # Calculate raw score
        raw_score = base_score * vendor_multiplier * arch_multiplier * memory_multiplier

        # Normalize to 60-100 range
        # Map raw_score to 60-100 range using sigmoid function for smooth scaling
        min_score = 60
        max_score = 100
        normalized_score = min_score + (max_score - min_score) * (
            2 / (1 + math.exp(-raw_score / 50)) - 1
        )

        # Ensure score stays within bounds
        final_score = max(min_score, min(max_score, normalized_score))

        return round(final_score, 1)

    def update_gpu_score(self):
        """Update the GPU score for this listing."""
        config = self.configuration
        config.gpu_score = self.compute_gpu_score(
            config.gpu_name, config.gpu_vendor, config.gpu_memory, config.gpu_count
        )

    # Property getters for direct access to configuration attributes
    @property
    def gpu_name(self):
        return self.configuration.gpu_name if self.configuration else None
        
    @property
    def gpu_vendor(self):
        return self.configuration.gpu_vendor if self.configuration else None
        
    @property
    def gpu_count(self):
        return self.configuration.gpu_count if self.configuration else None
        
    @property
    def gpu_memory(self):
        return self.configuration.gpu_memory if self.configuration else None
        
    @property
    def gpu_score(self):
        return self.configuration.gpu_score if self.configuration else None
        
    @property
    def cpu(self):
        return self.configuration.cpu if self.configuration else None
        
    @property
    def memory(self):
        return self.configuration.memory if self.configuration else None
        
    @property
    def disk_size(self):
        return self.configuration.disk_size if self.configuration else None
    
    def to_dict(self):
        """Convert GPU listing to dictionary representation"""
        host = self.host
        
        return {
            "id": self.id,
            "instance_name": self.instance_name,
            "gpu_name": self.gpu_name,
            "gpu_vendor": self.gpu_vendor,
            "gpu_count": self.gpu_count,
            "gpu_memory": self.gpu_memory,
            "current_price": self.current_price,
            "gpu_score": self.gpu_score,
            "price_change": self.price_change,
            "cpu": self.cpu,
            "memory": self.memory,
            "disk_size": self.disk_size,
            "provider": host.name if host else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }


class GPUPricePoint(db.Model):
    """Real-time price points for each GPU instance in different regions"""

    __tablename__ = "gpu_price_points"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    gpu_listing_id = db.Column(
        db.Integer, db.ForeignKey("gpu_listings.id"), nullable=False
    )
    price = db.Column(db.Float, nullable=False)
    location = db.Column(db.String(255), nullable=False)
    spot = db.Column(db.Boolean, default=False)
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "price": self.price,
            "location": self.location,
            "spot": self.spot,
            "last_updated": self.last_updated.isoformat(),
        }


class GPUPriceHistory(db.Model):
    """Historical price records for each GPU configuration"""

    __tablename__ = "gpu_price_history"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    configuration_id = db.Column(
        db.Integer, db.ForeignKey("gpu_configurations.id"), nullable=False
    )
    price = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
    location = db.Column(db.String(255), nullable=False)
    spot = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "price": self.price,
            "date": self.date.isoformat(),
            "location": self.location,
            "spot": self.spot,
        }
