from datetime import datetime
from app import db
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    profile_image_url = db.Column(db.String, nullable=True)
    
    role = db.Column(db.String, default='student')
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    mood_logs = db.relationship('MoodLog', backref='user', lazy=True)

class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.String, db.ForeignKey(User.id))
    browser_session_key = db.Column(db.String, nullable=False)
    user = db.relationship(User)

    __table_args__ = (UniqueConstraint(
        'user_id',
        'browser_session_key',
        'provider',
        name='uq_user_browser_session_key_provider',
    ),)

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(10), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    classes = db.relationship('Class', backref='department', lazy=True)
    users = db.relationship('User', backref='department', lazy=True)

class Class(db.Model):
    __tablename__ = 'classes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    section = db.Column(db.String(10), nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    teacher_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    students = db.relationship('User', backref='assigned_class', lazy=True, foreign_keys=[User.class_id])

class MoodLog(db.Model):
    __tablename__ = 'mood_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    text_entry = db.Column(db.Text, nullable=True)
    mood_score = db.Column(db.Integer, nullable=False)
    stress_score = db.Column(db.Integer, nullable=False)
    sentiment_polarity = db.Column(db.Float, nullable=True)
    sentiment_subjectivity = db.Column(db.Float, nullable=True)
    mood_emoji = db.Column(db.String(10), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

class Alert(db.Model):
    __tablename__ = 'alerts'
    id = db.Column(db.Integer, primary_key=True)
    alert_type = db.Column(db.String(50), nullable=False)
    severity = db.Column(db.String(20), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=True)
    message = db.Column(db.Text, nullable=False)
    is_resolved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    resolved_at = db.Column(db.DateTime, nullable=True)
