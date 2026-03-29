import sys
import os
import re
import openpyxl
from werkzeug.security import generate_password_hash

# Add project root and backend to sys.path for standalone execution
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT_DIR)
sys.path.append(os.path.join(ROOT_DIR, 'backend'))
sys.path.append(os.path.join(ROOT_DIR, 'database'))

from app import app
from database import db, Students, Courses, Instructors, CourseSections, Schedules, Enrollments, Admins

XLSX_PATH = os.path.join(ROOT_DIR, 'Schedule_Report_Improved_08-03-2026-15-02-40.xlsx')

# Map short day names from Excel to full day names
DAY_MAP = {
    'Sun': 'Sunday',
    'Mon': 'Monday',
    'Tue': 'Tuesday',
    'Wed': 'Wednesday',
    'Thu': 'Thursday',
    'Fri': 'Friday',
    'Sat': 'Saturday',
}

def parse_section_field(section_field):
    """
    Parse 'ACCT 130 - SEC 81' into ('ACCT 130', 'SEC 81').
    Handles edge cases like 'MEDI 401- SEC 81' (no space before dash).
    """
    if not section_field:
        return ('', '')
    # Split on ' - ' or '- ' or ' -'
    parts = re.split(r'\s*-\s*', section_field, maxsplit=1)
    code = parts[0].strip() if len(parts) > 0 else ''
    sec  = parts[1].strip() if len(parts) > 1 else 'SEC 81'
    return code, sec

def parse_time_field(time_str):
    """
    Parse '02:00 PM - 02:50 PM' into ('02:00 PM', '02:50 PM').
    """
    if not time_str:
        return ('', '')
    parts = [p.strip() for p in time_str.split(' - ')]
    start = parts[0] if len(parts) > 0 else ''
    end   = parts[1] if len(parts) > 1 else ''
    return start, end

def parse_days(days_str):
    """
    Parse 'Sun,Tue,Thu' into ['Sunday', 'Tuesday', 'Thursday'].
    """
    if not days_str:
        return []
    return [DAY_MAP.get(d.strip(), d.strip()) for d in days_str.split(',')]

def derive_department(course_code):
    """Extract department prefix from course code, e.g. 'ACCT 130' -> 'ACCT'."""
    return course_code.split()[0] if course_code else 'GEN'

def seed():
    with app.app_context():
        print("Cleaning old data...")
        db.drop_all()
        db.create_all()

        # ── Admin ──────────────────────────────────────────────────────────
        print("Seeding Admin...")
        admin = Admins(username="admin", password_hash=generate_password_hash("admin123"))
        db.session.add(admin)
        db.session.commit()

        # ── Read Excel ─────────────────────────────────────────────────────
        print(f"Reading Excel: {XLSX_PATH}")
        wb = openpyxl.load_workbook(XLSX_PATH)
        ws = wb['Schedule_Report_Improved']

        # ── Pass 1: collect unique courses & sections ──────────────────────
        # course_map:  code -> (name, department)
        # section_map: (code, sec_label) -> list of (days_str, start_time, end_time, room)
        course_map  = {}   # code -> (course_name, department)
        section_map = {}   # (code, sec_label) -> [(day, start, end, room), ...]

        skipped = 0
        for row in ws.iter_rows(min_row=2, values_only=True):
            course_name, section_field, room, days_str, time_str = row

            if not section_field or not course_name:
                skipped += 1
                continue

            code, sec_label = parse_section_field(str(section_field))
            if not code:
                skipped += 1
                continue

            dept = derive_department(code)
            course_map[code] = (str(course_name).strip(), dept)

            start_time, end_time = parse_time_field(str(time_str) if time_str else '')
            days = parse_days(str(days_str) if days_str else '')

            key = (code, sec_label)
            if key not in section_map:
                section_map[key] = []

            for day in days:
                section_map[key].append((day, start_time, end_time, str(room).strip() if room else 'TBA'))

        print(f"  Found {len(course_map)} unique courses, {len(section_map)} sections. Skipped {skipped} blank rows.")

        # ── Insert Courses ─────────────────────────────────────────────────
        print("Seeding Courses...")
        course_id_map = {}  # code -> course_id
        for code, (name, dept) in course_map.items():
            c = Courses(course_code=code, course_name=name, credits=3, department=dept)
            db.session.add(c)
            db.session.flush()   # get c.course_id before commit
            course_id_map[code] = c.course_id
        db.session.commit()

        # ── Insert Sections & Schedules ────────────────────────────────────
        print("Seeding Sections and Schedules...")
        for (code, sec_label), slots in section_map.items():
            cid = course_id_map.get(code)
            if cid is None:
                continue

            section = CourseSections(
                course_id=cid,
                instructor_id=None,
                semester='Spring 2026',
                section_name=sec_label
            )
            db.session.add(section)
            db.session.flush()

            for (day, start, end, room) in slots:
                sched = Schedules(
                    section_id=section.section_id,
                    day_of_week=day,
                    start_time=start,
                    end_time=end,
                    classroom=room
                )
                db.session.add(sched)

        db.session.commit()

        # ── Demo Students (no real student data in Excel) ──────────────────
        print("Seeding demo Students...")
        demo_students = [
            ("Alice Smith",    "alice@uni.edu",   "CS",   3),
            ("Bob Johnson",    "bob@uni.edu",     "EE",   2),
            ("Charlie Brown",  "charlie@uni.edu", "MATH", 4),
            ("Diana Prince",   "diana@uni.edu",   "ACCT", 1),
            ("Ethan Hunt",     "ethan@uni.edu",   "BIO",  2),
        ]
        for name, email, major, year in demo_students:
            s = Students(
                name=name,
                email=email,
                password_hash=generate_password_hash("password123"),
                major_id=major,
                year=year
            )
            db.session.add(s)
        db.session.commit()

        sections_all = CourseSections.query.all()
        students_all = Students.query.all()

        print("Seeding demo Enrollments (3 sections per student)...")
        import random
        random.seed(42)
        for student in students_all:
            chosen = random.sample(sections_all, min(3, len(sections_all)))
            for sec in chosen:
                db.session.add(Enrollments(student_id=student.student_id, section_id=sec.section_id))
        db.session.commit()

        print("Seeding complete!")
        print(f"  Courses   : {Courses.query.count()}")
        print(f"  Sections  : {CourseSections.query.count()}")
        print(f"  Schedules : {Schedules.query.count()}")
        print(f"  Students  : {Students.query.count()}")
        print(f"  Enrollments: {Enrollments.query.count()}")

if __name__ == "__main__":
    seed()
