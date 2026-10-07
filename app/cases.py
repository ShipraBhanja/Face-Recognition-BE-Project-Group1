import secrets
from datetime import date
from pathlib import Path

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app import db
from app.models import Case, CaseImage
from app.services.face_detection import count_faces
from app.services.face_matching import (AGE_DB_COSINE_THRESHOLD, FaceMatchingError,
                                        face_feature, known_age_gap, rank_features,
                                        select_top_matches)

cases = Blueprint("cases", __name__)
ALLOWED = {"jpg", "jpeg", "png", "webp"}


def seven_year_cutoff():
    today = date.today()
    try:
        return today.replace(year=today.year - 7)
    except ValueError:  # 29 February
        return today.replace(year=today.year - 7, day=28)


@cases.get("/")
@login_required
def index():
    older_than_seven = request.args.get("review") == "7plus"
    query = Case.query.filter_by(created_by=current_user.id)
    if older_than_seven:
        cutoff = seven_year_cutoff()
        query = query.filter(Case.status == "Open", Case.missing_since.isnot(None),
                             Case.missing_since <= cutoff)
    records = query.order_by(Case.missing_since.asc().nullslast(), Case.created_at.desc()).all()
    return render_template("cases.html", cases=records, older_than_seven=older_than_seven)


@cases.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        name = request.form.get("person_name", "").strip()
        number = request.form.get("case_number", "").strip()
        if not name or not number:
            flash("Person name and case number are required.", "error")
        elif Case.query.filter_by(case_number=number).first():
            flash("That case number already exists.", "error")
        else:
            record = Case(person_name=name, case_number=number,
                          age_when_missing=request.form.get("age_when_missing", type=int),
                          missing_since=date.fromisoformat(request.form["missing_since"])
                          if request.form.get("missing_since") else None,
                          last_seen=request.form.get("last_seen", "").strip(),
                          description=request.form.get("description", "").strip(),
                          created_by=current_user.id)
            db.session.add(record)
            db.session.commit()
            return redirect(url_for("cases.detail", case_id=record.id))
    return render_template("case_form.html")


@cases.route("/<int:case_id>/edit", methods=["GET", "POST"])
@login_required
def edit(case_id):
    record = Case.query.filter_by(id=case_id, created_by=current_user.id).first_or_404()
    if request.method == "POST":
        record.person_name = request.form.get("person_name", "").strip()
        record.case_number = request.form.get("case_number", "").strip()
        record.age_when_missing = request.form.get("age_when_missing", type=int)
        record.missing_since = date.fromisoformat(request.form["missing_since"]) if request.form.get("missing_since") else None
        record.last_seen = request.form.get("last_seen", "").strip()
        record.description = request.form.get("description", "").strip()
        db.session.commit()
        flash("Person details updated.", "success")
        return redirect(url_for("cases.detail", case_id=record.id))
    return render_template("case_form.html", person=record)


@cases.post("/<int:case_id>/found")
@login_required
def close_as_found(case_id):
    record = Case.query.filter_by(id=case_id, created_by=current_user.id).first_or_404()
    if request.form.get("confirm_found") != "yes":
        flash("Confirm that the person has been found before closing this record.", "error")
    elif record.status != "Open":
        flash("This record is already closed.", "error")
    else:
        record.status = "Closed"
        record.closed_at = date.today()
        record.closure_note = request.form.get("closure_note", "").strip()[:500] or "Person reported found"
        db.session.commit()
        flash("Record closed as found.", "success")
    return redirect(url_for("cases.detail", case_id=record.id))


@cases.post("/<int:case_id>/reopen")
@login_required
def reopen(case_id):
    record = Case.query.filter_by(id=case_id, created_by=current_user.id).first_or_404()
    record.status = "Open"
    record.closed_at = None
    record.closure_note = None
    db.session.commit()
    flash("Record reopened.", "success")
    return redirect(url_for("cases.detail", case_id=record.id))


@cases.get("/<int:case_id>")
@login_required
def detail(case_id):
    record = Case.query.filter_by(id=case_id, created_by=current_user.id).first_or_404()
    return render_template("case_detail.html", case=record, review_cutoff=seven_year_cutoff())


@cases.post("/<int:case_id>/images")
@login_required
def upload(case_id):
    record = Case.query.filter_by(id=case_id, created_by=current_user.id).first_or_404()
    file = request.files.get("image")
    note = request.form.get("note", "").strip()
    subject_age = request.form.get("subject_age", type=int)
    if request.form.get("subject_age", "").strip() and (subject_age is None or not 0 <= subject_age <= 120):
        flash("Photo age must be a whole number from 0 to 120.", "error")
        return redirect(url_for("cases.detail", case_id=case_id))
    if not file or not file.filename:
        flash("Choose an image first.", "error")
    elif "." not in file.filename or file.filename.rsplit(".", 1)[1].lower() not in ALLOWED:
        flash("Use a JPG, PNG or WebP image.", "error")
    else:
        suffix = file.filename.rsplit(".", 1)[1].lower()
        filename = f"{secrets.token_hex(16)}.{suffix}"
        target = Path(current_app.config["UPLOAD_FOLDER"]) / filename
        file.save(target)
        try:
            faces = count_faces(target)
        except Exception:
            target.unlink(missing_ok=True)
            flash("Image could not be processed. Try a different file.", "error")
        else:
            db.session.add(CaseImage(filename=secure_filename(filename), note=note,
                                     face_count=faces, subject_age=subject_age, case_id=record.id))
            db.session.commit()
            flash(f"Image saved. Haar cascade detected {faces} face(s); this is not identity recognition.", "success")
    return redirect(url_for("cases.detail", case_id=case_id))


@cases.post("/<int:case_id>/delete")
@login_required
def delete(case_id):
    record = Case.query.filter_by(id=case_id, created_by=current_user.id).first_or_404()
    if request.form.get("confirm_delete") != "yes":
        flash("Confirm deletion to remove this person entry.", "error")
        return redirect(url_for("cases.detail", case_id=case_id))

    upload_dir = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    image_paths = []
    for photo in record.images:
        image_path = (upload_dir / photo.filename).resolve()
        if image_path.parent == upload_dir:
            image_paths.append(image_path)

    db.session.delete(record)
    db.session.commit()
    for image_path in image_paths:
        image_path.unlink(missing_ok=True)
    flash("Person entry and its saved photos were deleted.", "success")
    return redirect(url_for("cases.index"))


@cases.get("/images/<path:filename>")
@login_required
def image(filename):
    owned_image = (CaseImage.query.join(Case).filter(
        CaseImage.filename == filename, Case.created_by == current_user.id
    ).first())
    if not owned_image:
        abort(404)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


@cases.route("/match", methods=["GET", "POST"])
@login_required
def match():
    results = None
    uploaded_name = None
    query_age = None
    minimum_gap = None
    top_k = 10
    open_people = []
    if request.method == "POST":
        query_age = request.form.get("query_age", type=int)
        minimum_gap = request.form.get("minimum_gap", type=int)
        top_k = request.form.get("top_k", 10, type=int)
        if top_k is None or not 1 <= top_k <= 100:
            flash("Top K must be between 1 and 100. Using 10.", "error")
            top_k = 10
        if query_age is not None and not 0 <= query_age <= 120:
            flash("Query age must be between 0 and 120.", "error")
            query_age = None
        if minimum_gap is not None and not 0 <= minimum_gap <= 120:
            flash("Minimum age gap must be between 0 and 120 years.", "error")
            minimum_gap = None
        file = request.files.get("query_image")
        if not file or not file.filename or "." not in file.filename or file.filename.rsplit(".", 1)[1].lower() not in ALLOWED:
            flash("Choose a JPG, PNG or WebP photo.", "error")
        else:
            suffix = file.filename.rsplit(".", 1)[1].lower()
            query_path = Path(current_app.config["UPLOAD_FOLDER"]) / f"query-{secrets.token_hex(12)}.{suffix}"
            file.save(query_path)
            try:
                query = face_feature(query_path)
                candidates = []
                photos = (CaseImage.query.join(Case)
                          .filter(Case.created_by == current_user.id).all())
                for photo in photos:
                    age_gap = known_age_gap(query_age, photo.subject_age)
                    if minimum_gap and age_gap is not None and age_gap < minimum_gap:
                        continue
                    try:
                        vector = face_feature(Path(current_app.config["UPLOAD_FOLDER"]) / photo.filename)
                    except FaceMatchingError:
                        continue
                    candidates.append((f"{photo.case.person_name} · {photo.case.case_number}",
                                       url_for("cases.image", filename=photo.filename), vector,
                                       photo.subject_age, age_gap))
                ranked = rank_features(query, [row[:3] for row in candidates])
                # Attach age metadata in the same score-sorted order as the feature rows.
                metadata = {(row[0], row[1]): row[3:] for row in candidates}
                results = select_top_matches(ranked, k=top_k,
                                             threshold=AGE_DB_COSINE_THRESHOLD)
                for result in results:
                    result["reference_age"], result["age_gap"] = metadata[(result["label"], result["image_url"])]
                uploaded_name = file.filename
                if not results:
                    open_people = (Case.query.filter_by(created_by=current_user.id, status="Open")
                                   .order_by(Case.missing_since.asc().nullslast(), Case.person_name.asc())
                                   .all())
            except (FaceMatchingError, RuntimeError) as exc:
                flash(str(exc), "error")
            finally:
                query_path.unlink(missing_ok=True)
    return render_template("match.html", results=results, uploaded_name=uploaded_name,
                           query_age=query_age, minimum_gap=minimum_gap,
                           top_k=top_k, open_people=open_people)
