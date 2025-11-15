from flask import Blueprint

auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')
users_bp = Blueprint('users', __name__, url_prefix='/api/v1/users')
api_keys_bp = Blueprint('api_keys', __name__, url_prefix='/api/v1/api-keys')
pdf_template_bp = Blueprint('pdf_template', __name__, url_prefix='/api/v1/pdf-template')
uploaded_files_bp = Blueprint('uploaded_files', __name__, url_prefix='/api/v1/uploaded-files')
channels_bp = Blueprint('channels', __name__, url_prefix='/api/v1/channels')
media_rationale_bp = Blueprint('media_rationale', __name__, url_prefix='/api/v1/media-rationale')
premium_rationale_bp = Blueprint('premium_rationale', __name__, url_prefix='/api/v1/premium-rationale')
saved_rationale_bp = Blueprint('saved_rationale', __name__, url_prefix='/api/v1/saved-rationale')
activity_logs_bp = Blueprint('activity_logs', __name__, url_prefix='/api/v1/activity-logs')
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/v1/dashboard')

from backend.api import auth, users, api_keys, pdf_template, uploaded_files, channels, media_rationale, premium_rationale, saved_rationale, activity_logs, dashboard, manual_v2

manual_v2_bp = manual_v2.manual_v2_bp
