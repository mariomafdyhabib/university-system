import os
import sys
import pandas as pd

# Path setup to import backend models
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT_DIR)
sys.path.append(os.path.join(ROOT_DIR, 'backend'))

from backend.app import app
from database import db, Courses, Instructors, CourseSections, Schedules, Enrollments, Students

def seed_from_excel(file_path):
    print(f"Reading {file_path}...")
    df = pd.read_excel(file_path)
    
    with app.app_context():
        print("Clearing old data...")
        Schedules.query.delete()
        CourseSections.query.delete()
        Courses.query.delete()
        # Not clearing Instructors or Students to be safe, or we can clear Instructors
        Instructors.query.delete()
        Enrollments.query.delete()
        db.session.commit()

        print("Seeding new data...")
        
        # 1. Create a dummy instructor since the Excel doesn't have one
        staff = Instructors(name="Staff")
        db.session.add(staff)
        db.session.flush()

        # 2. Iterate through Excel to build Courses and Sections
        # Columns: ['Course', 'Course Section', 'Room', 'Day Name', 'Time']
        added_courses = {} # name -> course_id
        added_sections = {} # (course_name, section_name) -> section_id
        
        for index, row in df.iterrows():
            c_name = str(row.get('Course', '')).strip()
            sec_name = str(row.get('Course Section', '')).strip()
            room = str(row.get('Room', '')).strip()
            day = str(row.get('Day Name', '')).strip()
            time_str = str(row.get('Time', '')).strip() # e.g., "02:00 PM - 02:50 PM"
            
            if not c_name or pd.isna(c_name):
                continue
                
            # Create course if not exists
            if c_name not in added_courses:
                # Generate a short code from initials
                code = "".join(word[0] for word in c_name.split() if word.isalnum()).upper()[:4] + str(len(added_courses)+100)
                crs = Courses(course_code=code, course_name=c_name, credits=3, department="General")
                db.session.add(crs)
                db.session.flush()
                added_courses[c_name] = crs.course_id
                
            c_id = added_courses[c_name]
            
            # Create section if not exists
            sec_key = (c_name, sec_name)
            if sec_key not in added_sections:
                sec = CourseSections(course_id=c_id, instructor_id=staff.instructor_id, semester="Fall 2026", section_name=sec_name)
                db.session.add(sec)
                db.session.flush()
                added_sections[sec_key] = sec.section_id
                
            s_id = added_sections[sec_key]
            
            # Create schedule
            if time_str and '-' in time_str:
                start_t, end_t = [t.strip() for t in time_str.split('-')]
                sch = Schedules(section_id=s_id, day_of_week=day, start_time=start_t, end_time=end_t, classroom=room)
                db.session.add(sch)
                
        db.session.commit()
        print(f"Successfully seeded {len(added_courses)} courses and {len(added_sections)} sections.")

if __name__ == "__main__":
    excel_file = os.path.join(ROOT_DIR, 'Schedule_Report_Improved_08-03-2026-15-02-40.xlsx')
    seed_from_excel(excel_file)
