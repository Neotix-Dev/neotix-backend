from datetime import datetime
from utils.database import db
from enum import Enum

class APIKeyPermission(Enum):
    READ = 'read'      # Can only read market data
    ADMIN = 'admin'    # Full access including key management

class APIKey(db.Model):
    __tablename__ = 'api_keys'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)  # Name/description of the key
    permission = db.Column(db.String(20), nullable=False, default=APIKeyPermission.READ.value)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    def __init__(self, key, name, permission=APIKeyPermission.READ):
        self.key = key
        self.name = name
        self.permission = permission.value
        
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'key': self.key,  # Only show in creation response
            'permission': self.permission,
            'created_at': self.created_at.isoformat(),
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'is_active': self.is_active
        }
