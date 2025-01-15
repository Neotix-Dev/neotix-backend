from utils.database import db 
from datetime import datetime

class Host(db.Model):
    __tablename__ = 'hosts'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)  # This will store the provider name
    description = db.Column(db.Text, nullable=False)
    url = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'url': self.url
        }

class GPUListing(db.Model):
    __tablename__ = 'gpu_listings'

    id = db.Column(db.Integer, primary_key=True)
    instance_name = db.Column(db.String(255), nullable=False)
    gpu_name = db.Column(db.String(255), nullable=True)
    gpu_vendor = db.Column(db.String(50), nullable=True)  # NVIDIA, AMD, or GOOGLE
    gpu_count = db.Column(db.Integer, nullable=False)
    gpu_memory = db.Column(db.Float, nullable=True)  # in GB
    current_price = db.Column(db.Float, nullable=False)  # Lowest current price
    price_change = db.Column(db.String(10), nullable=False, default="0%")
    cpu = db.Column(db.Integer, nullable=True)
    memory = db.Column(db.Float, nullable=True)  # in GB
    disk_size = db.Column(db.Float, nullable=True)  # in GB
    host_id = db.Column(db.Integer, db.ForeignKey('hosts.id'), nullable=False)
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    host = db.relationship('Host', backref='listings')
    price_points = db.relationship('GPUPricePoint', backref='gpu', lazy='dynamic')
    price_history = db.relationship('GPUPriceHistory', backref='gpu', lazy='dynamic')

    def __init__(self, instance_name, gpu_name, gpu_vendor, gpu_count, gpu_memory, 
                 current_price, cpu, memory, disk_size, host_id):
        self.instance_name = instance_name
        self.gpu_name = gpu_name
        self.gpu_vendor = gpu_vendor
        self.gpu_count = gpu_count
        self.gpu_memory = gpu_memory
        self.current_price = current_price
        self.cpu = cpu
        self.memory = memory
        self.disk_size = disk_size
        self.host_id = host_id
        self.last_updated = datetime.utcnow()

    def to_dict(self):
        return {
            'id': self.id,
            'instance_name': self.instance_name,
            'gpu_name': self.gpu_name,
            'gpu_vendor': self.gpu_vendor,
            'gpu_count': self.gpu_count,
            'gpu_memory': self.gpu_memory,
            'current_price': self.current_price,
            'price_change': self.price_change,
            'cpu': self.cpu,
            'memory': self.memory,
            'disk_size': self.disk_size,
            'provider': self.host.name,
            'last_updated': self.last_updated.isoformat()
        }

class GPUPricePoint(db.Model):
    """Real-time price points for each GPU instance in different regions"""
    __tablename__ = 'gpu_price_points'

    id = db.Column(db.Integer, primary_key=True)
    gpu_listing_id = db.Column(db.Integer, db.ForeignKey('gpu_listings.id'), nullable=False)
    price = db.Column(db.Float, nullable=False)
    location = db.Column(db.String(255), nullable=False)
    spot = db.Column(db.Boolean, default=False)
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'price': self.price,
            'location': self.location,
            'spot': self.spot,
            'last_updated': self.last_updated.isoformat()
        }

class GPUPriceHistory(db.Model):
    """Historical price records for each GPU instance"""
    __tablename__ = 'gpu_price_history'

    id = db.Column(db.Integer, primary_key=True)
    gpu_listing_id = db.Column(db.Integer, db.ForeignKey('gpu_listings.id'), nullable=False)
    price = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    location = db.Column(db.String(255), nullable=False)
    spot = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'price': self.price,
            'date': self.date.isoformat(),
            'location': self.location,
            'spot': self.spot
        }
