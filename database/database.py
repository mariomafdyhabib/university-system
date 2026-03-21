from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Students(db.Model, UserMixin):
    __tablename__ = 'students'
    student_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    major_id = db.Column(db.String(50))
    year = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)

    def get_id(self):
        return str(self.student_id)

class Admins(db.Model, UserMixin):
    __tablename__ = 'admins'
    admin_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def get_id(self):
        return f"a_{self.admin_id}"

class Courses(db.Model):
    __tablename__ = 'courses'
    course_id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20), unique=True, nullable=False)
    course_name = db.Column(db.String(100), nullable=False)
    credits = db.Column(db.Integer, default=3)
    department = db.Column(db.String(50))

class Instructors(db.Model):
    __tablename__ = 'instructors'
    instructor_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

class CourseSections(db.Model):
    __tablename__ = 'course_sections'
    section_id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.course_id'), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('instructors.instructor_id'))
    semester = db.Column(db.String(20))
    section_name = db.Column(db.String(20)) # Added for 'A', 'B'

class Schedules(db.Model):
    __tablename__ = 'schedules'
    schedule_id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey('course_sections.section_id'), nullable=False)
    day_of_week = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.String(20), nullable=False)
    end_time = db.Column(db.String(20), nullable=False)
    classroom = db.Column(db.String(50))

class Enrollments(db.Model):
    __tablename__ = 'enrollments'
    enrollment_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.student_id'), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('course_sections.section_id'), nullable=False)

class CourseScheduleSystem(db.Model):
    __tablename__ = 'course_schedule_system'
    id = db.Column(db.Integer, primary_key=True)
    crn = db.Column(db.String(50))
    course = db.Column(db.String(100))
    section = db.Column(db.String(20))
    day = db.Column(db.String(20))
    time = db.Column(db.String(50))
    room = db.Column(db.String(50))
    instructor = db.Column(db.String(100))

class CourseScheduleStudent(db.Model):
    __tablename__ = 'course_schedule_student'
    id = db.Column(db.Integer, primary_key=True)
    course = db.Column(db.String(100))
    section = db.Column(db.String(20))
    days = db.Column(db.String(50))
    time = db.Column(db.String(50))
    room = db.Column(db.String(50))
    instructor = db.Column(db.String(100))
