from utils.database import db 
class Host(db.Model):
    # This is for the host of the gpu listing, the hardware provider
    __tablename__ = 'hosts'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    url = db.Column(db.String(255), nullable=True)  # Made nullable since some hosts might not have URLs

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
    name = db.Column(db.String(255), nullable=False)
    number_of_gpus = db.Column(db.Integer, nullable=True, default=1)
    current_price = db.Column(db.Float, nullable=False)
    price_metric = db.Column(db.String(10), nullable=False)
    price_change = db.Column(db.String(10), nullable=False)
    reliability = db.Column(db.Float, nullable=False)
    flops = db.Column(db.Float, nullable=False)
    vram = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    host_id = db.Column(db.Integer, db.ForeignKey('hosts.id'), nullable=False)
    host = db.relationship('Host', backref='listings')

    def __init__(self, name, number_of_gpus, current_price, price_metric, price_change, reliability, flops, vram, description, image_url, host_id):
        self.name = name
        self.number_of_gpus = number_of_gpus
        self.current_price = current_price
        self.price_metric = price_metric
        self.price_change = price_change
        self.reliability = reliability
        self.flops = flops
        self.vram = vram
        self.description = description
        self.image_url = image_url
        self.host_id = host_id

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'number_of_gpus': self.number_of_gpus,
            'current_price': self.current_price,
            'price_metric': self.price_metric,
            'price_change': self.price_change,
            'reliability': self.reliability,
            'flops': self.flops,
            'vram': self.vram,
            'description': self.description,
            'image_url': self.image_url,
            'host_id': self.host_id,
            'host_name': self.host.name,
            'host_url': self.host.url
        }
