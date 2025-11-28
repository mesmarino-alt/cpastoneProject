from flask import Blueprint

# Define the blueprint with updated template folder path
admin_bp = Blueprint(
    'admin',
    __name__,
    template_folder='../project/admin/templates',
    static_folder='static'
)

# Import routes so they register with admin_bp
from . import routes
