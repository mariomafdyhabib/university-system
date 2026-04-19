import sys
import os
from flask import Flask, request, jsonify, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Add parent and database directory to sys.path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../database')))

from database import db, Students, Admins, Courses, Enrollments, CourseSections, Schedules, Instructors, Majors, Colleges, CourseScheduleSystem, CourseScheduleStudent
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

@app.route('/reports/<path:path>')
def send_report(path):
    return send_from_directory(os.path.join(BASE_DIR, 'reports'), path)



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
        college_id=data.get('college_id'),
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

@app.route('/colleges', methods=['GET'])
def get_colleges():
    colleges = Colleges.query.all()
    if not colleges:
        _initialize_colleges_and_majors()
        colleges = Colleges.query.all()
    return jsonify([{'id': c.college_id, 'name': c.name} for c in colleges])

@app.route('/majors', methods=['GET'])
def get_majors():
    college_id = request.args.get('college_id')
    query = Majors.query
    if college_id:
        query = query.filter_by(college_id=int(college_id))
    
    majors = query.all()
    if not majors and not college_id:
        _initialize_colleges_and_majors()
        majors = Majors.query.all()
    
    return jsonify([{'id': m.major_id, 'name': m.name} for m in majors])

def _initialize_colleges_and_majors():
    data = {
        "College of Engineering": [
            "Industrial Engineering",
            "Biomedical Engineering",
            "Electrical & Computer Engineering",
            "Computer Science & Cyber Security",
            "Architecture & Design",
            "Civil & Architectural Engineering"
        ],
        "College of Business": [
            "Accounting",
            "Information Systems",
            "Finance & FinTech",
            "Supply Chain Management & Logistics",
            "Banking & Investment Management",
            "Healthcare Management",
            "Marketing"
        ],
        "College of Arts": [
            "English Language",
            "Communication Sciences & Disorders",
            "Media",
            "Sociology & Social Services"
        ]
    }
    
    for c_name, m_list in data.items():
        college = Colleges.query.filter_by(name=c_name).first()
        if not college:
            college = Colleges(name=c_name)
            db.session.add(college)
            db.session.commit()
        
        for m_name in m_list:
            major = Majors.query.filter_by(name=m_name).first()
            if not major:
                major = Majors(name=m_name, college_id=college.college_id)
                db.session.add(major)
    
    db.session.commit()

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
                "section_name": sec.section_name or "",
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
        # Group by section exactly like the frontend
        section_map = {}
        abbr_map = {
            "sat": "Saturday", "sun": "Sunday", "mon": "Monday",
            "tue": "Tuesday", "wed": "Wednesday", "thu": "Thursday",
            "fri": "Friday"
        }
        table_days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]

        for enr in enrolls:
            sec = CourseSections.query.get(enr.section_id)
            if not sec: continue
            crs = Courses.query.get(sec.course_id)
            schs = Schedules.query.filter_by(section_id=sec.section_id).all()
            
            key = str(sec.section_id)
            if key not in section_map:
                section_map[key] = {
                    "code": crs.course_code,
                    "name": crs.course_name,
                    "section": sec.section_name or "",
                    "classroom": "",
                    "days": {d: "" for d in table_days}
                }
            
            for s in schs:
                section_map[key]["classroom"] = s.classroom or section_map[key]["classroom"]
                days_arr = [d.strip().lower() for d in (s.day_of_week or "").split(",")]
                for d in days_arr:
                    full_day = abbr_map.get(d, d.capitalize())
                    if full_day in table_days:
                        section_map[key]["days"][full_day] = f"{s.start_time} - {s.end_time}"
        
        pdf = FPDF(orientation='L', unit='mm', format='A4') # Landscape for more space
        pdf.add_page()
        
        # Header
        pdf.set_fill_color(30, 41, 59) # Dark blue/slate
        pdf.rect(0, 0, 297, 40, 'F') # 297 is A4 Landscape width
        
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 24)
        pdf.cell(0, 15, "IUK University", ln=True, align='C')
        pdf.set_font("Arial", '', 14)
        pdf.cell(0, 5, "International University of Kuwait", ln=True, align='C')
        pdf.cell(0, 10, "Student Weekly Timetable Grid", ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"Issued to: {current_user.name}", ln=True)
        pdf.ln(2)

        # Table Header
        # Adjusted widths for Landscape (Total ~277mm available)
        w_code = 35
        w_name = 55
        w_loc = 25
        w_day = 32 # 5 days * 32 = 160
        # Total: 35+55+25+160 = 275mm
        
        pdf.set_fill_color(30, 41, 59) # Header background
        pdf.set_text_color(255, 255, 255) # Header text
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(w_code, 12, " Course & Sec", border=1, fill=True)
        pdf.cell(w_name, 12, " Course Name", border=1, fill=True)
        pdf.cell(w_loc, 12, " Location", border=1, fill=True)
        for d in table_days:
            pdf.cell(w_day, 12, f" {d.upper()}", border=1, fill=True, align='C')
        pdf.ln()

        # Reset text color for body
        pdf.set_text_color(0, 0, 0)
        
        # Table Body
        pdf.set_font("Arial", '', 8)
        fill = False
        sorted_sections = sorted(section_map.values(), key=lambda x: (x['code'], x['section']))
        for sec_data in sorted_sections:
            pdf.set_fill_color(248, 250, 252) if fill else pdf.set_fill_color(255, 255, 255)
            
            # Course & Sec
            label = f"{sec_data['code']}"
            if sec_data['section']: label += f" - {sec_data['section']}"
            
            # Use multi_cell for long names if needed, but for simplicity we'll use cell
            # or custom height
            h = 15
            
            curr_x = pdf.get_x()
            curr_y = pdf.get_y()
            
            pdf.cell(w_code, h, f" {label}", border=1, fill=True)
            pdf.cell(w_name, h, f" {sec_data['name'][:30]}", border=1, fill=True)
            pdf.cell(w_loc, h, f" {sec_data['classroom']}", border=1, fill=True)
            
            for d in table_days:
                time_str = sec_data["days"][d]
                if time_str:
                    pdf.set_font("Arial", 'B', 7)
                    pdf.cell(w_day, h, time_str, border=1, fill=True, align='C')
                    pdf.set_font("Arial", '', 8)
                else:
                    pdf.cell(w_day, h, "", border=1, fill=True)
            
            pdf.ln()
            fill = not fill
            
        # Footer
        pdf.set_y(-25)
        pdf.set_font("Arial", 'I', 8)
        pdf.set_text_color(160, 160, 160)
        pdf.cell(0, 10, "International University of Kuwait - Official AI Generated Schedule", ln=True, align='C')
            
        output = io.BytesIO(pdf.output())
        output.seek(0)
        
        return send_file(output, as_attachment=True, download_name=f"Schedule_Grid_{current_user.name.replace(' ', '_')}.pdf", mimetype="application/pdf")
    except Exception as e:
        import traceback
        traceback.print_exc()
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
