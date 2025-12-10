# routes/admin_tools.py (protected)
from flask import Blueprint, flash, redirect, url_for
from flask_login import login_required

from commands.run_matching import run_matching_job

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/run-matching')
@login_required
def run_matching():
    count = run_matching_job()
    flash(f"Matching job inserted {count} new matches.", "info")
    return redirect(url_for('admin.dashboard'))
