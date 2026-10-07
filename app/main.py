from flask import Blueprint, render_template
from flask_login import current_user, login_required

from app.models import Case

main = Blueprint("main", __name__)


@main.get("/")
def home():
    return render_template("home.html")


@main.get("/dashboard")
@login_required
def dashboard():
    records = Case.query.filter_by(created_by=current_user.id).order_by(Case.created_at.desc()).limit(5).all()
    total = Case.query.count()
    return render_template("dashboard.html", cases=records, total=total)
