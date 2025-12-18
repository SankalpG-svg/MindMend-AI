from flask import session, render_template, request, jsonify, redirect, url_for
from flask_login import current_user
from datetime import datetime, timedelta
from sqlalchemy import func

from app import app, db
from models import User, Department, Class, MoodLog, Alert
from auth import require_login, require_role, make_replit_blueprint
from stress_analyzer import analyze_stress, get_mood_emoji

app.register_blueprint(make_replit_blueprint(), url_prefix="/auth")

@app.before_request
def make_session_permanent():
    session.permanent = True

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    return render_template('landing.html')

@app.route('/student')
@require_login
def student_dashboard():
    logs = MoodLog.query.filter_by(user_id=current_user.id).order_by(MoodLog.created_at.desc()).limit(30).all()
    
    today = datetime.now().date()
    today_log = MoodLog.query.filter(
        MoodLog.user_id == current_user.id,
        func.date(MoodLog.created_at) == today
    ).first()
    
    avg_stress = 0
    if logs:
        avg_stress = sum(log.stress_score for log in logs) / len(logs)
    
    return render_template('student_dashboard.html', 
                         user=current_user, 
                         logs=logs, 
                         today_log=today_log,
                         avg_stress=round(avg_stress))

@app.route('/teacher')
@require_role('teacher', 'admin')
def teacher_dashboard():
    classes = Class.query.filter_by(teacher_id=current_user.id).all()
    
    class_stats = []
    for cls in classes:
        students = User.query.filter_by(class_id=cls.id, role='student').all()
        student_ids = [s.id for s in students]
        
        if student_ids:
            week_ago = datetime.now() - timedelta(days=7)
            logs = MoodLog.query.filter(
                MoodLog.user_id.in_(student_ids),
                MoodLog.created_at >= week_ago
            ).all()
            
            if logs:
                avg_stress = sum(log.stress_score for log in logs) / len(logs)
                high_stress_count = sum(1 for log in logs if log.stress_score >= 70)
            else:
                avg_stress = 0
                high_stress_count = 0
        else:
            avg_stress = 0
            high_stress_count = 0
        
        class_stats.append({
            'class': cls,
            'student_count': len(students),
            'avg_stress': round(avg_stress),
            'high_stress_count': high_stress_count
        })
    
    return render_template('teacher_dashboard.html', 
                         user=current_user, 
                         class_stats=class_stats)

@app.route('/admin')
@require_role('admin')
def admin_dashboard():
    departments = Department.query.all()
    
    dept_stats = []
    for dept in departments:
        students = User.query.filter_by(department_id=dept.id, role='student').all()
        student_ids = [s.id for s in students]
        
        if student_ids:
            week_ago = datetime.now() - timedelta(days=7)
            logs = MoodLog.query.filter(
                MoodLog.user_id.in_(student_ids),
                MoodLog.created_at >= week_ago
            ).all()
            
            if logs:
                avg_stress = sum(log.stress_score for log in logs) / len(logs)
            else:
                avg_stress = 0
        else:
            avg_stress = 0
        
        dept_stats.append({
            'department': dept,
            'student_count': len(students),
            'avg_stress': round(avg_stress)
        })
    
    alerts = Alert.query.filter_by(is_resolved=False).order_by(Alert.created_at.desc()).limit(10).all()
    
    total_users = User.query.count()
    total_logs = MoodLog.query.count()
    
    week_ago = datetime.now() - timedelta(days=7)
    recent_logs = MoodLog.query.filter(MoodLog.created_at >= week_ago).all()
    overall_avg_stress = 0
    if recent_logs:
        overall_avg_stress = sum(log.stress_score for log in recent_logs) / len(recent_logs)
    
    return render_template('admin_dashboard.html', 
                         user=current_user, 
                         dept_stats=dept_stats,
                         alerts=alerts,
                         total_users=total_users,
                         total_logs=total_logs,
                         overall_avg_stress=round(overall_avg_stress))

@app.route('/api/mood/log', methods=['POST'])
@require_login
def log_mood():
    data = request.json
    text_entry = data.get('text', '')
    mood_emoji = data.get('emoji', '')
    
    analysis = analyze_stress(text_entry)
    
    log = MoodLog(
        user_id=current_user.id,
        text_entry=text_entry,
        mood_score=analysis['mood_score'],
        stress_score=analysis['stress_score'],
        sentiment_polarity=analysis['polarity'],
        sentiment_subjectivity=analysis['subjectivity'],
        mood_emoji=mood_emoji or get_mood_emoji(analysis['stress_score'])
    )
    
    db.session.add(log)
    
    if analysis.get('is_high_risk'):
        alert = Alert(
            alert_type='high_risk',
            severity='critical',
            department_id=current_user.department_id,
            class_id=current_user.class_id,
            message=f"High-risk stress pattern detected. Stress score: {analysis['stress_score']}"
        )
        db.session.add(alert)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'stress_score': analysis['stress_score'],
        'mood_score': analysis['mood_score'],
        'analysis': analysis['analysis'],
        'emoji': get_mood_emoji(analysis['stress_score'])
    })

@app.route('/api/mood/history')
@require_login
def get_mood_history():
    days = request.args.get('days', 30, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    logs = MoodLog.query.filter(
        MoodLog.user_id == current_user.id,
        MoodLog.created_at >= start_date
    ).order_by(MoodLog.created_at.asc()).all()
    
    return jsonify({
        'logs': [{
            'date': log.created_at.strftime('%Y-%m-%d'),
            'stress_score': log.stress_score,
            'mood_score': log.mood_score,
            'emoji': log.mood_emoji
        } for log in logs]
    })

@app.route('/api/class/<int:class_id>/stats')
@require_role('teacher', 'admin')
def get_class_stats(class_id):
    cls = Class.query.get_or_404(class_id)
    
    if current_user.role == 'teacher' and cls.teacher_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    students = User.query.filter_by(class_id=class_id, role='student').all()
    student_ids = [s.id for s in students]
    
    days = request.args.get('days', 7, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    daily_stats = []
    for i in range(days):
        date = (datetime.now() - timedelta(days=days-1-i)).date()
        logs = MoodLog.query.filter(
            MoodLog.user_id.in_(student_ids),
            func.date(MoodLog.created_at) == date
        ).all()
        
        if logs:
            avg_stress = sum(log.stress_score for log in logs) / len(logs)
        else:
            avg_stress = 0
        
        daily_stats.append({
            'date': date.strftime('%Y-%m-%d'),
            'avg_stress': round(avg_stress),
            'log_count': len(logs)
        })
    
    return jsonify({'stats': daily_stats})

@app.route('/api/admin/department/<int:dept_id>/stats')
@require_role('admin')
def get_department_stats(dept_id):
    dept = Department.query.get_or_404(dept_id)
    students = User.query.filter_by(department_id=dept_id, role='student').all()
    student_ids = [s.id for s in students]
    
    days = request.args.get('days', 7, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    daily_stats = []
    for i in range(days):
        date = (datetime.now() - timedelta(days=days-1-i)).date()
        logs = MoodLog.query.filter(
            MoodLog.user_id.in_(student_ids),
            func.date(MoodLog.created_at) == date
        ).all()
        
        if logs:
            avg_stress = sum(log.stress_score for log in logs) / len(logs)
        else:
            avg_stress = 0
        
        daily_stats.append({
            'date': date.strftime('%Y-%m-%d'),
            'avg_stress': round(avg_stress),
            'log_count': len(logs)
        })
    
    return jsonify({'department': dept.name, 'stats': daily_stats})

@app.route('/api/admin/alerts/<int:alert_id>/resolve', methods=['POST'])
@require_role('admin')
def resolve_alert(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    alert.is_resolved = True
    alert.resolved_at = datetime.now()
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/analyze', methods=['POST'])
@require_login
def analyze_text():
    data = request.json
    text = data.get('text', '')
    analysis = analyze_stress(text)
    return jsonify(analysis)

@app.route('/settings')
@require_login
def settings():
    departments = Department.query.all()
    classes = Class.query.all()
    return render_template('settings.html', 
                         user=current_user, 
                         departments=departments,
                         classes=classes)

@app.route('/api/user/update', methods=['POST'])
@require_login
def update_user():
    data = request.json
    
    if 'department_id' in data:
        current_user.department_id = data['department_id'] if data['department_id'] else None
    if 'class_id' in data:
        current_user.class_id = data['class_id'] if data['class_id'] else None
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/admin/user/<user_id>/role', methods=['POST'])
@require_role('admin')
def update_user_role(user_id):
    data = request.json
    user = User.query.get_or_404(user_id)
    
    if data.get('role') in ['student', 'teacher', 'admin']:
        user.role = data['role']
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'error': 'Invalid role'}), 400

@app.route('/admin/users')
@require_role('admin')
def admin_users():
    users = User.query.all()
    departments = Department.query.all()
    classes = Class.query.all()
    return render_template('admin_users.html', 
                         user=current_user,
                         users=users,
                         departments=departments,
                         classes=classes)

@app.route('/admin/setup')
@require_role('admin')
def admin_setup():
    departments = Department.query.all()
    classes = Class.query.all()
    return render_template('admin_setup.html',
                         user=current_user,
                         departments=departments,
                         classes=classes)

@app.route('/api/admin/department', methods=['POST'])
@require_role('admin')
def create_department():
    data = request.json
    dept = Department(
        name=data['name'],
        code=data['code']
    )
    db.session.add(dept)
    db.session.commit()
    return jsonify({'success': True, 'id': dept.id})

@app.route('/api/admin/class', methods=['POST'])
@require_role('admin')
def create_class():
    data = request.json
    cls = Class(
        name=data['name'],
        year=data['year'],
        section=data.get('section'),
        department_id=data['department_id'],
        teacher_id=data.get('teacher_id')
    )
    db.session.add(cls)
    db.session.commit()
    return jsonify({'success': True, 'id': cls.id})

def seed_demo_data():
    if Department.query.count() == 0:
        departments = [
            Department(name='Computer Science', code='CS'),
            Department(name='Mechanical Engineering', code='ME'),
            Department(name='Electrical Engineering', code='EE'),
            Department(name='Civil Engineering', code='CE')
        ]
        for dept in departments:
            db.session.add(dept)
        db.session.commit()
        
        cs_dept = Department.query.filter_by(code='CS').first()
        classes = [
            Class(name='CS Year 1 Section A', year=1, section='A', department_id=cs_dept.id),
            Class(name='CS Year 2 Section A', year=2, section='A', department_id=cs_dept.id),
            Class(name='CS Year 3 Section A', year=3, section='A', department_id=cs_dept.id)
        ]
        for cls in classes:
            db.session.add(cls)
        db.session.commit()

with app.app_context():
    seed_demo_data()
