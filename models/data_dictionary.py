from app import db
from datetime import datetime

class DataDictionary(db.Model):
    __tablename__ = 'data_dictionary'
    
    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(100), nullable=False)  # 'switches'
    column_name = db.Column(db.String(100), nullable=False)  # 'id_ativo'
    data_type = db.Column(db.String(50))  # 'string', 'integer', 'date'
    description = db.Column(db.Text, nullable=False)
    required = db.Column(db.Boolean, default=False)
    max_length = db.Column(db.Integer)
    example = db.Column(db.String(200))
    category = db.Column(db.String(100))  # 'Identificação', 'Localização', etc.
    
    # Metadados
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'table_name': self.table_name,
            'column_name': self.column_name,
            'data_type': self.data_type,
            'description': self.description,
            'required': self.required,
            'max_length': self.max_length,
            'example': self.example,
            'category': self.category
        }