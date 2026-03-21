import sys, os
from flask import Flask
sys.path.append(os.path.abspath('backend'))
sys.path.append(os.path.abspath('database'))
from database import db, Enrollments, CourseSections, Courses, Instructors, Schedules

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.abspath('database/instance/fload.db')}"
db.init_app(app)

with app.app_context():
    try:
        # Simulate current_user.student_id = 1 (Alice)
        enrolls = Enrollments.query.filter_by(student_id=1).all()
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
        print("Success! Result length:", len(res))
    except Exception as e:
        import traceback
        traceback.print_exc()
