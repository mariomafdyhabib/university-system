import sys
import os
from flask import Flask, request, jsonify, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Add parent and database directory to sys.path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../database')))

from database import db, Students, Admins, Courses, Enrollments, CourseSections, Schedules, Instructors, Majors, CourseScheduleSystem, CourseScheduleStudent
import scheduler
import course_upload
from admin_routes import admin_bp

import io
import pandas as pd
from fpdf import FPDF
from flask import send_file

# Calculate absolute paths for robustness
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')
DATABASE_FILE = os.path.join(BASE_DIR, 'database', 'instance', 'fload.db')

# Ensure directories exist for the database if we're creating it
os.makedirs(os.path.dirname(DATABASE_FILE), exist_ok=True)

app = Flask(__name__, static_folder=FRONTEND_DIR, template_folder=FRONTEND_DIR, static_url_path='')
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_FILE}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
app.register_blueprint(admin_bp)

@app.after_request
def no_cache(response):
    """Prevent browser from caching HTML/JS/CSS during development."""
    if response.content_type.startswith(('text/html', 'application/javascript', 'text/css')):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response


login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    if user_id.startswith('a_'):
        return Admins.query.get(int(user_id[2:]))
    return Students.query.get(int(user_id))

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    if not data or not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({'error': 'Missing required fields'}), 400
    
    if Students.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400

    hashed_password = generate_password_hash(data['password'])
    new_student = Students(
        name=data['name'],
        email=data['email'],
        password_hash=hashed_password,
        major_id=data.get('major_id'),
        year=data.get('year')
    )
    db.session.add(new_student)
    db.session.commit()
    login_user(new_student)
    return jsonify({'message': 'Registration successful', 'role': 'student'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    student = Students.query.filter_by(email=data.get('email')).first()
    
    if student and check_password_hash(student.password_hash, data.get('password')):
        login_user(student)
        return jsonify({'message': 'Logged in', 'role': 'student'}), 200
        
    return jsonify({'error': 'Invalid email or password'}), 401
    
@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out'})

@app.route('/majors', methods=['GET'])
def get_majors():
    majors = Majors.query.all()
    if not majors:
        # Initialize from courses if empty
        depts = db.session.query(Courses.department).distinct().all()
        for d in depts:
            if d[0]:
                new_major = Majors(name=d[0])
                db.session.add(new_major)
        db.session.commit()
        majors = Majors.query.all()
    
    return jsonify([{'id': m.major_id, 'name': m.name} for m in majors])

@app.route('/courses', methods=['GET'])
@login_required
def courses():
    courses_query = Courses.query.all()
    out = []
    for c in courses_query:
        out.append({
            'course_id': c.course_id,
            'course_code': c.course_code,
            'course_name': c.course_name,
            'credits': c.credits,
            'department': c.department
        })
    return jsonify(out)

@app.route('/sections', methods=['GET'])
@login_required
def get_all_sections():
    try:
        sections = CourseSections.query.all()
        res = []
        for sec in sections:
            crs = Courses.query.get(sec.course_id)
            inst = Instructors.query.get(sec.instructor_id) if sec.instructor_id else None
            schs = Schedules.query.filter_by(section_id=sec.section_id).all()
            
            sch_list = [{
                "day_of_week": s.day_of_week,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "classroom": s.classroom
            } for s in schs]
            
            res.append({
                "section_id": sec.section_id,
                "course_id": crs.course_id if crs else None,
                "course_code": crs.course_code if crs else "Unknown",
                "course_name": crs.course_name if crs else "Unknown",
                "instructor": inst.name if inst else "TBD",
                "semester": sec.semester,
                "section_name": sec.section_name,
                "schedules": sch_list
            })
        return jsonify(res)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

def _get_schedule_details(section_ids):
    res = []
    for sid in section_ids:
        sec = CourseSections.query.get(sid)
        if not sec: continue
        crs = Courses.query.get(sec.course_id)
        inst = Instructors.query.get(sec.instructor_id) if sec.instructor_id else None
        schs = Schedules.query.filter_by(section_id=sec.section_id).all()
        for s in schs:
            res.append({
                "section_id": sec.section_id,
                "course_id": crs.course_id if crs else None,
                "course_code": crs.course_code if crs else "Unknown",
                "course_name": crs.course_name if crs else "Unknown",
                "instructor": inst.name if inst else "TBD",
                "day_of_week": s.day_of_week,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "classroom": s.classroom
            })
    return res

@app.route('/generate-schedule', methods=['POST'])
@login_required
def generate_schedule():
    data = request.json
    from scheduler import generate_schedule_variants
    
    try:
        if 'course_ids' in data and data['course_ids']:
            course_ids = [int(cid) for cid in data['course_ids']]
            if len(course_ids) > 5:
                return jsonify({"error": "Maximum 5 courses allowed."}), 400
            variants = generate_schedule_variants(current_user.student_id, course_ids)
            
            result = {
                "condensed": {
                    "section_ids": variants['condensed'],
                    "entries": _get_schedule_details(variants['condensed'])
                },
                "spread": {
                    "section_ids": variants['spread'],
                    "entries": _get_schedule_details(variants['spread'])
                },
                "moderate": {
                    "section_ids": variants['moderate'],
                    "entries": _get_schedule_details(variants['moderate'])
                }
            }
            return jsonify(result)
        else:
            return jsonify({"error": "No courses provided"}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 400

@app.route('/confirm-schedule', methods=['POST'])
@login_required
def confirm_schedule():
    data = request.json
    section_ids = data.get('section_ids')
    if not section_ids:
        return jsonify({"error": "No sections provided"}), 400
    
    try:
        # Clear existing enrollments
        Enrollments.query.filter_by(student_id=current_user.student_id).delete()
        
        for sid in section_ids:
            enr = Enrollments(student_id=current_user.student_id, section_id=sid)
            db.session.add(enr)
        
        db.session.commit()
        return jsonify({"message": "Schedule confirmed and enrolled successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/schedule', methods=['GET'])
@login_required
def get_schedule():
    try:
        enrolls = Enrollments.query.filter_by(student_id=current_user.student_id).all()
        res = []
        for enr in enrolls:
            sec = CourseSections.query.get(enr.section_id)
            if not sec: continue
            crs = Courses.query.get(sec.course_id)
            inst = Instructors.query.get(sec.instructor_id) if sec.instructor_id else None
            schs = Schedules.query.filter_by(section_id=sec.section_id).all()
            
            for s in schs:
                res.append({
                    "enrollment_id": enr.enrollment_id,
                    "section_id": sec.section_id,
                    "course_id": crs.course_id if crs else None,
                    "course_code": crs.course_code if crs else "Unknown",
                    "course_name": crs.course_name if crs else "Unknown",
                    "instructor": inst.name if inst else "TBD",
                    "day_of_week": s.day_of_week,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "classroom": s.classroom
                })
        return jsonify(res)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/edit-schedule', methods=['POST'])
@login_required
def edit_schedule():
    data = request.json
    action = data.get('action')
    from scheduler import check_student_conflict
    
    if action == 'delete':
        enr = Enrollments.query.get(data.get('enrollment_id'))
        if enr and enr.student_id == current_user.student_id:
            db.session.delete(enr)
            db.session.commit()
            return jsonify({"message": "Removed from schedule"})
            
    elif action == 'replace':
        enr = Enrollments.query.get(data.get('enrollment_id'))
        new_sec_id = int(data.get('new_section_id'))
        
        if enr and enr.student_id == current_user.student_id:
            # Check for conflict with OTHER enrollments
            if check_student_conflict(current_user.student_id, new_sec_id):
                return jsonify({"error": "Time conflict detected. This change is not allowed."}), 400
            
            enr.section_id = new_sec_id
            db.session.commit()
            return jsonify({"message": "Schedule updated"})
            
    return jsonify({"error": "Invalid action or non-existent enrollment"}), 400

@app.route('/clear-schedule', methods=['POST'])
@login_required
def clear_schedule():
    Enrollments.query.filter_by(student_id=current_user.student_id).delete()
    db.session.commit()
    return jsonify({"message": "Schedule cleared"})

@app.route('/schedule/export/pdf', methods=['GET'])
@login_required
def export_pdf():
    try:
        enrolls = Enrollments.query.filter_by(student_id=current_user.student_id).all()
        unique_section_ids = {enr.section_id for enr in enrolls}
        data = []
        for sec_id in unique_section_ids:
            sec = CourseSections.query.get(sec_id)
            if not sec: continue
            crs = Courses.query.get(sec.course_id)
            schs = Schedules.query.filter_by(section_id=sec.section_id).all()
            for s in schs:
                data.append({
                    "Course": f"{crs.course_code} - {crs.course_name}",
                    "Day": s.day_of_week,
                    "Time": f"{s.start_time} - {s.end_time}",
                    "Room": s.classroom
                })
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "International University of Kuwait (IUK)", ln=True, align='C')
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Student Weekly Schedule", ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(80, 10, "Course", border=1)
        pdf.cell(30, 10, "Day", border=1)
        pdf.cell(50, 10, "Time", border=1)
        pdf.cell(30, 10, "Room", border=1)
        pdf.ln()
        
        pdf.set_font("Arial", '', 10)
        for item in data:
            pdf.cell(80, 10, item["Course"], border=1)
            pdf.cell(30, 10, item["Day"], border=1)
            pdf.cell(50, 10, item["Time"], border=1)
            pdf.cell(30, 10, item["Room"], border=1)
            pdf.ln()
            
        output = io.BytesIO(pdf.output())
        output.seek(0)
        
        return send_file(output, as_attachment=True, download_name="schedule.pdf", mimetype="application/pdf")
    except Exception as e:
        return jsonify({"error": f"PDF Export Failed: {str(e)}"}), 500

@app.route('/schedule/export/excel', methods=['GET'])
@login_required
def export_excel():
    try:
        enrolls = Enrollments.query.filter_by(student_id=current_user.student_id).all()
        unique_section_ids = {enr.section_id for enr in enrolls}
        data = []
        for sec_id in unique_section_ids:
            sec = CourseSections.query.get(sec_id)
            if not sec: continue
            crs = Courses.query.get(sec.course_id)
            schs = Schedules.query.filter_by(section_id=sec.section_id).all()
            for s in schs:
                data.append({
                    "Course Code": crs.course_code,
                    "Course Name": crs.course_name,
                    "Day": s.day_of_week,
                    "Start Time": s.start_time,
                    "End Time": s.end_time,
                    "Classroom": s.classroom
                })
        
        if not data:
            return jsonify({"error": "No schedule records found to export"}), 400

        df = pd.DataFrame(data)
        output = io.BytesIO()
        # Use a more explicit writer close pattern for broader compatibility
        writer = pd.ExcelWriter(output, engine='openpyxl')
        df.to_excel(writer, index=False, sheet_name='My Schedule')
        writer.close()
        output.seek(0)
        
        return send_file(output, as_attachment=True, download_name="schedule.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Excel Export Failed: {str(e)}"}), 500

# HTML Pages Routes
@app.route('/')
def index():
    return send_from_directory(app.template_folder, 'index.html')

@app.route('/login-page')
@app.route('/login.html')
def login_page():
    return send_from_directory(app.template_folder, 'login.html')

@app.route('/register-page')
@app.route('/register.html')
def register_page():
    return send_from_directory(app.template_folder, 'register.html')

@app.route('/student-dashboard')
@app.route('/student_dashboard.html')
def student_dashboard():
    return send_from_directory(app.template_folder, 'student_dashboard.html')

@app.route('/admin')
@app.route('/admin.html')
def admin_page():
    return send_from_directory(app.template_folder, 'admin.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
