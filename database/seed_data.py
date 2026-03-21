import sys
import os
import random
from werkzeug.security import generate_password_hash

# Add project root and backend to sys.path for standalone execution
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT_DIR)
sys.path.append(os.path.join(ROOT_DIR, 'backend'))
sys.path.append(os.path.join(ROOT_DIR, 'database'))

from app import app
from database import db, Students, Courses, Instructors, CourseSections, Schedules, Enrollments, Admins

def seed():
    with app.app_context():
        print("Cleaning old data...")
        db.drop_all()
        db.create_all()

        print("Seeding Admins...")
        admin = Admins(username="admin", password_hash=generate_password_hash("admin123"))
        db.session.add(admin)

        print("Seeding Students...")
        students_data = [
            ("Alice Smith", "alice@example.com", "CS", 3),
            ("Bob Johnson", "bob@example.com", "ME", 2),
            ("Charlie Brown", "charlie@example.com", "EE", 4),
            ("Diana Prince", "diana@example.com", "CS", 1),
            ("Ethan Hunt", "ethan@example.com", "MATH", 2),
            ("Fiona Gallagher", "fiona@example.com", "BIO", 3),
            ("George Clooney", "george@example.com", "PHYS", 4),
            ("Hannah Montana", "hannah@example.com", "ART", 1),
            ("Ian McKellen", "ian@example.com", "CS", 2),
            ("Julia Roberts", "julia@example.com", "MATH", 3),
        ]
        students = []
        for name, email, major, year in students_data:
            s = Students(name=name, email=email, password_hash=generate_password_hash("password123"), major_id=major, year=year)
            db.session.add(s)
            students.append(s)

        print("Seeding Instructors...")
        instructors_data = ["Dr. Alan Turing", "Dr. Grace Hopper", "Dr. Ada Lovelace", "Dr. Richard Feynman", "Dr. Marie Curie", "Dr. Albert Einstein"]
        instructors = []
        for name in instructors_data:
            i = Instructors(name=name)
            db.session.add(i)
            instructors.append(i)
        
        db.session.commit() # Commit to get IDs

        print("Seeding Courses...")
        courses_data = [
            ("CS101", "Intro to Programming", 3, "CS"),
            ("CS102", "Data Structures", 4, "CS"),
            ("MATH201", "Calculus I", 3, "MATH"),
            ("MATH202", "Calculus II", 3, "MATH"),
            ("PHYS101", "General Physics I", 4, "PHYS"),
            ("BIO101", "Intro to Biology", 3, "BIO"),
            ("EE101", "Circuit Analysis", 3, "EE"),
            ("ME101", "Thermodynamics", 3, "ME"),
        ]
        courses = []
        for code, name, credits, dept in courses_data:
            c = Courses(course_code=code, course_name=name, credits=credits, department=dept)
            db.session.add(c)
            courses.append(c)
        
        db.session.commit()

        print("Seeding Sections and Schedules...")
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        rooms = ["A101", "B202", "C303", "D404", "E505"]
        
        for course in courses:
            for letter in ["A", "B"]:
                section = CourseSections(course_id=course.course_id, instructor_id=random.choice(instructors).instructor_id, semester="Spring 2026", section_name=letter)
                db.session.add(section)
                db.session.commit()

                # Add 2 slots per section
                day1 = random.choice(days)
                day2 = random.choice([d for d in days if d != day1])
                room = random.choice(rooms)
                
                s1 = Schedules(section_id=section.section_id, day_of_week=day1, start_time="10:00 AM", end_time="11:30 AM", classroom=room)
                s2 = Schedules(section_id=section.section_id, day_of_week=day2, start_time="10:00 AM", end_time="11:30 AM", classroom=room)
                db.session.add(s1)
                db.session.add(s2)

        print("Seeding Enrollments...")
        sections = CourseSections.query.all()
        for student in students:
            # Enroll in 3 random sections
            chosen = random.sample(sections, 3)
            for sec in chosen:
                enr = Enrollments(student_id=student.student_id, section_id=sec.section_id)
                db.session.add(enr)

        db.session.commit()
        print("Seeding complete!")

if __name__ == "__main__":
    seed()
