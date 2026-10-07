from datetime import date, datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Case(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    person_name = db.Column(db.String(120), nullable=False)
    case_number = db.Column(db.String(80), nullable=False, unique=True)
    age_when_missing = db.Column(db.Integer)
    missing_since = db.Column(db.Date)
    last_seen = db.Column(db.String(180))
    description = db.Column(db.Text)
    status = db.Column(db.String(30), default="Open", nullable=False)
    closed_at = db.Column(db.Date)
    closure_note = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    images = db.relationship("CaseImage", backref="case", cascade="all, delete-orphan")


class CaseImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    note = db.Column(db.String(240))
    face_count = db.Column(db.Integer)
    subject_age = db.Column(db.Integer)
    case_id = db.Column(db.Integer, db.ForeignKey("case.id"), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
