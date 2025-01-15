from utils.database import db
from datetime import datetime

class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationship with GPUs through association table
    gpus = db.relationship('GPUListing', secondary='project_gpus', backref=db.backref('projects', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'gpus': [gpu.to_dict() for gpu in self.gpus]
        }

class ProjectGPU(db.Model):
    __tablename__ = 'project_gpus'
    
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), primary_key=True)
    gpu_id = db.Column(db.Integer, db.ForeignKey('gpu_listings.id'), primary_key=True)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
