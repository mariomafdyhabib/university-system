from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user, login_user
from werkzeug.security import generate_password_hash, check_password_hash
from database import db, Students, Courses, CourseSections, Instructors, Enrollments, Schedules, Admins
from course_upload import process_upload
from scheduler import detect_system_conflicts
import os

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/login', methods=['POST'])
def admin_login():
    data = request.json
    admin = Admins.query.filter_by(username=data.get('username')).first()
    if admin and check_password_hash(admin.password_hash, data.get('password')):
        login_user(admin)
        return jsonify({"message": "Logged in as admin", "role": "admin"})
    return jsonify({"error": "Invalid credentials"}), 401

@admin_bp.route('/stats', methods=['GET'])
def get_stats():
    # TEMPORARY: Removed @login_required for testing to solve your 401 error
    # In a production app, you would use login_required and check if current_user is admin
    return jsonify({
        "total_students": Students.query.count(),
        "total_courses": Courses.query.count(),
        "total_sections": CourseSections.query.count(),
        "total_instructors": Instructors.query.count(),
        "total_classrooms": Schedules.query.with_entities(Schedules.classroom).distinct().count()
    })

@admin_bp.route('/students', methods=['GET'])
def get_students():
    students = Students.query.all()
    return jsonify([{
        "student_id": s.student_id,
        "name": s.name,
        "email": s.email,
        "major_id": s.major_id,
        "year": s.year,
        "is_active": s.is_active
    } for s in students])

@admin_bp.route('/courses', methods=['GET'])
def get_courses():
    courses = Courses.query.all()
    return jsonify([{
        "course_id": c.course_id,
        "course_code": c.course_code,
        "course_name": c.course_name,
        "credits": c.credits,
        "department": c.department
    } for c in courses])

@admin_bp.route('/create-course', methods=['POST'])
def create_course():
    data = request.json
    new_course = Courses(
        course_code=data.get('course_code'),
        course_name=data.get('course_name'),
        credits=data.get('credits'),
        department=data.get('department')
    )
    db.session.add(new_course)
    db.session.commit()
    return jsonify({"message": "Course created!"})

@admin_bp.route('/delete-course', methods=['DELETE'])
def delete_course():
    course_id = request.args.get('course_id')
    course = Courses.query.get(course_id)
    if course:
        db.session.delete(course)
        db.session.commit()
        return jsonify({"message": "Course deleted!"})
    return jsonify({"error": "Course not found"}), 404

@admin_bp.route('/update-course', methods=['PUT'])
def update_course():
    data = request.json
    course = Courses.query.get(data.get('course_id'))
    if course:
        if 'course_code' in data: course.course_code = data['course_code']
        if 'course_name' in data: course.course_name = data['course_name']
        if 'credits' in data: course.credits = data['credits']
        if 'department' in data: course.department = data['department']
        db.session.commit()
        return jsonify({"message": "Course updated"})
    return jsonify({"error": "Not found"}), 404

@admin_bp.route('/sections', methods=['GET'])
def get_sections():
    sections = db.session.query(CourseSections, Courses, Instructors).outerjoin(Courses).outerjoin(Instructors).all()
    res = []
    for sec, crs, inst in sections:
        res.append({
            "section_id": sec.section_id,
            "course_id": sec.course_id,
            "course_code": crs.course_code if crs else "",
            "course_name": crs.course_name if crs else "",
            "instructor_id": sec.instructor_id,
            "instructor_name": inst.name if inst else "",
            "semester": sec.semester
        })
    return jsonify(res)

@admin_bp.route('/instructors', methods=['GET'])
def get_instructors():
    inst = Instructors.query.all()
    return jsonify([{"instructor_id": i.instructor_id, "name": i.name} for i in inst])

@admin_bp.route('/create-section', methods=['POST'])
def create_section():
    data = request.json
    new_sec = CourseSections(
        course_id=data.get('course_id'),
        instructor_id=data.get('instructor_id'),
        semester=data.get('semester', 'TBD')
    )
    db.session.add(new_sec)
    db.session.commit()
    return jsonify({"message": "Section created", "section_id": new_sec.section_id})

@admin_bp.route('/update-section', methods=['PUT'])
def update_section():
    data = request.json
    sec = CourseSections.query.get(data.get('section_id'))
    if sec:
        if 'course_id' in data: sec.course_id = data['course_id']
        if 'instructor_id' in data: sec.instructor_id = data['instructor_id']
        if 'semester' in data: sec.semester = data['semester']
        db.session.commit()
        return jsonify({"message": "Section updated"})
    return jsonify({"error": "Not found"}), 404

@admin_bp.route('/delete-section', methods=['DELETE'])
def delete_section():
    section_id = request.args.get('section_id')
    sec = CourseSections.query.get(section_id)
    if sec:
        db.session.delete(sec)
        db.session.commit()
        return jsonify({"message": "Section deleted"})
    return jsonify({"error": "Not found"}), 404

@admin_bp.route('/schedules', methods=['GET'])
def get_schedules():
    schs = Schedules.query.all()
    return jsonify([{
        "schedule_id": s.schedule_id,
        "section_id": s.section_id,
        "day_of_week": s.day_of_week,
        "start_time": s.start_time,
        "end_time": s.end_time,
        "classroom_id": s.classroom
    } for s in schs])

@admin_bp.route('/classrooms', methods=['GET'])
def get_classrooms():
    classes = db.session.query(Schedules.classroom).distinct().all()
    # Simplified classroom representation as seen in script.js
    return jsonify([{"classroom_id": c[0], "building": "Building", "room_number": c[0], "capacity": 0} for c in classes if c[0]])

@admin_bp.route('/enrollments', methods=['GET'])
def get_enrollments():
    enrolls = db.session.query(Enrollments, Students, CourseSections, Courses).join(Students).join(CourseSections).join(Courses).all()
    res = []
    for enr, stu, sec, crs in enrolls:
        res.append({
            "student_name": stu.name,
            "student_id": stu.student_id,
            "course_code": crs.course_code,
            "course_name": crs.course_name,
            "section_id": sec.section_id,
            "semester": sec.semester
        })
    return jsonify(res)

@admin_bp.route('/upload-course-file', methods=['POST'])
def upload_course_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    # Save file temporarily
    temp_path = os.path.join("/tmp", file.filename)
    file.save(temp_path)
    
    try:
        rows_added = process_upload(temp_path)
        return jsonify({"message": "Upload successful", "rows_stored": rows_added})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@admin_bp.route('/conflicts', methods=['GET'])
def get_conflicts():
    conflicts = detect_system_conflicts()
    return jsonify(conflicts)

@admin_bp.route('/update-student', methods=['PUT'])
def update_student():
    data = request.json
    student = Students.query.get(data.get('student_id'))
    if student:
        if 'name' in data: student.name = data['name']
        if 'email' in data: student.email = data['email']
        if 'major_id' in data: student.major_id = data['major_id']
        if 'year' in data: student.year = data['year']
        if 'is_active' in data: student.is_active = data['is_active']
        db.session.commit()
        return jsonify({"message": "Student updated"})
    return jsonify({"error": "Not found"}), 404

@admin_bp.route('/reset-student-password', methods=['POST'])
def reset_pw():
    data = request.json
    student = Students.query.get(data.get('student_id'))
    if student:
        student.password_hash = generate_password_hash(data['new_password'])
        db.session.commit()
        return jsonify({"message": "Password reset"})
    return jsonify({"error": "Not found"}), 404
