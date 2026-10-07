from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app import db
from app.models import User

auth = Blueprint("auth", __name__)


@auth.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        if len(username) < 3 or len(password) < 12:
            flash("Use a username of at least 3 characters and a password of at least 12.", "error")
        elif User.query.filter_by(username=username).first():
            flash("That username is already registered.", "error")
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("main.dashboard"))
    return render_template("register.html")


@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        user = User.query.filter_by(username=request.form.get("username", "").strip().lower()).first()
        if user and user.check_password(request.form.get("password", "")):
            login_user(user)
            return redirect(request.args.get("next") or url_for("main.dashboard"))
        flash("Username or password is incorrect.", "error")
    return render_template("login.html")


@auth.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
