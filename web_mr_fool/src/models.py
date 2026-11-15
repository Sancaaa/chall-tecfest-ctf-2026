"""
models.py: Database models for Mr. Fool CTF.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()


class Player(db.Model):
    __tablename__ = 'players'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed = db.Column(db.Text, default='[]')

    def get_completed(self):
        import json
        return json.loads(self.completed) if self.completed else []

    def add_completed(self, seq_id):
        completed = self.get_completed()
        if seq_id not in completed:
            completed.append(seq_id)
            import json
            self.completed = json.dumps(completed)


class PotionToken(db.Model):
    __tablename__ = 'potion_tokens'
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.String(36), db.ForeignKey('players.id'), nullable=False)
    sequence = db.Column(db.String(4), nullable=False)
    token = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Spell(db.Model):
    """S7 Magician spells model for mass assignment vulnerability."""
    __tablename__ = 'spells'
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.String(36), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    spell_type = db.Column(db.String(64), nullable=False, default='cantrip')
    approved = db.Column(db.Boolean, default=False)
    secret_code = db.Column(db.String(128), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Joke(db.Model):
    """S8 Clown jokes table targeted by SQL injection."""
    __tablename__ = 'jokes'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(64), nullable=False, default='anonymous')


class PotionSecret(db.Model):
    """S8 Clown hidden table exfiltrated via UNION-based SQLi."""
    __tablename__ = 'potion_secrets'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    secret_code = db.Column(db.String(128), nullable=False)

