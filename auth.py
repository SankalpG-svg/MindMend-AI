from functools import wraps
from flask import Blueprint, redirect, url_for, request, render_template
from flask_login import LoginManager, login_user, logout_user, current_user
from app import app, db
from models import User

# Initialize Login Manager
login_manager = LoginManager(app)
login_manager.login_view = 'replit_auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

def make_replit_blueprint():
    # Create a simple blueprint that doesn't use external OAuth
    bp = Blueprint('replit_auth', __name__)

    @bp.route('/login')
    def login():
        # BYPASS: Automatically log in as a local admin user
        user_id = 'local_admin'
        user = User.query.get(user_id)
        
        if not user:
            user = User()
            user.id = user_id
            user.email = 'admin@local.test'
            user.first_name = 'Local'
            user.last_name = 'Admin'
            user.role = 'admin'  # Change this to 'student' or 'teacher' to test other views
            user.profile_image_url = 'https://ui-avatars.com/api/?name=Local+Admin'
            db.session.add(user)
            db.session.commit()
        
        login_user(user)
        return redirect(url_for('index'))

    @bp.route('/logout')
    def logout():
        logout_user()
        return redirect(url_for('index'))

    return bp

# --- Decorators (Keep these so routes.py doesn't break) ---

def require_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('replit_auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def require_role(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('replit_auth.login'))
            
            # Simple role check
            if current_user.role not in roles:
                return render_template("error.html", message="Access denied. You don't have permission to view this page."), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
