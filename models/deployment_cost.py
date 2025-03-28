from utils.database import db
from datetime import datetime

class DeploymentCost(db.Model):
    __tablename__ = "deployment_costs"

    id = db.Column(db.Integer, primary_key=True)
    rental_gpu_id = db.Column(db.Integer, db.ForeignKey("rental_gpus.id"), nullable=False)
    transaction_id = db.Column(db.Integer, db.ForeignKey("transactions.id"), nullable=False)
    base_cost = db.Column(db.Float, nullable=False)
    tax_rate = db.Column(db.Float, nullable=False)
    tax_amount = db.Column(db.Float, nullable=False)
    platform_fee_rate = db.Column(db.Float, nullable=False)
    platform_fee_amount = db.Column(db.Float, nullable=False)
    total_cost = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "rental_gpu_id": self.rental_gpu_id,
            "transaction_id": self.transaction_id,
            "base_cost": self.base_cost,
            "tax_rate": self.tax_rate,
            "tax_amount": self.tax_amount,
            "platform_fee_rate": self.platform_fee_rate,
            "platform_fee_amount": self.platform_fee_amount,
            "total_cost": self.total_cost,
            "created_at": self.created_at.isoformat()
        }
