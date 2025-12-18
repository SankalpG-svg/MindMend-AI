from functools import wraps
from flask import Blueprint, redirect, url_for, request, render_template, render_template_string
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
        # Instead of auto-login, show a simple selection screen
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Select Role - Local Mode</title>
            <style>
                body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #f0f2f5; }
                .card { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; }
                h1 { margin-bottom: 1.5rem; color: #333; }
                .btn { display: block; width: 200px; padding: 12px; margin: 10px auto; text-decoration: none; color: white; border-radius: 6px; font-weight: bold; transition: opacity 0.2s; }
                .btn:hover { opacity: 0.9; }
                .student { background-color: #4CAF50; }
                .teacher { background-color: #2196F3; }
                .admin { background-color: #f44336; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>Select Login Role</h1>
                <p>You are in Local Developer Mode.</p>
                <a href="/auth/select/student" class="btn student">Login as Student</a>
                <a href="/auth/select/teacher" class="btn teacher">Login as Teacher</a>
                <a href="/auth/select/admin" class="btn admin">Login as Admin</a>
            </div>
        </body>
        </html>
        """
        return render_template_string(html)

    @bp.route('/select/<role>')
    def select_role(role):
        if role not in ['student', 'teacher', 'admin']:
            return "Invalid role", 400

        # Create a unique ID for each role so their data doesn't mix
        # e.g., 'local_student', 'local_teacher'
        user_id = f'local_{role}'
        
        user = User.query.get(user_id)
        if not user:
            user = User()
            user.id = user_id
            user.email = f'{role}@mindmend.local'
            user.first_name = 'Test'
            user.last_name = role.capitalize()
            user.profile_image_url = f'https://ui-avatars.com/api/?name=Test+{role}&background=random'
        
        # Force the correct role every time
        user.role = role
        
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('index'))

    @bp.route('/logout')
    def logout():
        logout_user()
        return redirect(url_for('index'))

    return bp

# --- Decorators ---

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
            
            if current_user.role not in roles:
                return render_template("error.html", message="Access denied. You don't have permission to view this page."), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator