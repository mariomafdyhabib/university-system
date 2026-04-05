import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../database')))

from database import db, CourseSections, Schedules, Enrollments
from app import app

with app.app_context():
    print("Starting database migration to split sections by day...")
    
    # 1. Clear all enrollments since section IDs are about to completely change.
    Enrollments.query.delete()
    print("Cleared existing student enrollments.")

    # 2. Find all existing sections
    sections = CourseSections.query.all()
    old_section_ids = [s.section_id for s in sections]
    
    for sec in sections:
        # Get all schedules for this section
        schedules = Schedules.query.filter_by(section_id=sec.section_id).all()
        
        # We will create a NEW section for EVERY schedule based on its day.
        for sched in schedules:
            # e.g., 'SEC 81 (Sun)'
            day_short = sched.day_of_week[:3] if len(sched.day_of_week) >= 3 else sched.day_of_week
            
            # Clean up old "(Sun)" if it somehow already exists before adding a new one
            base_sec_name = sec.section_name
            if ' (' in base_sec_name and base_sec_name.endswith(')'):
                base_sec_name = base_sec_name.split(' (')[0]
                
            new_sec_name = f"{base_sec_name} ({day_short})"
            
            # Check if this precise section already exists somehow
            existing_new_sec = CourseSections.query.filter_by(
                course_id=sec.course_id, section_name=new_sec_name
            ).first()
            
            if not existing_new_sec:
                new_sec = CourseSections(
                    course_id=sec.course_id,
                    instructor_id=sec.instructor_id,
                    section_name=new_sec_name,
                    semester=sec.semester
                )
                db.session.add(new_sec)
                db.session.flush() # get new_sec.section_id
                target_section_id = new_sec.section_id
            else:
                target_section_id = existing_new_sec.section_id
                
            # Move the schedule to point to this single-day section
            sched.section_id = target_section_id
    
    db.session.commit()
    
    # 3. Clean up the original old sections that now have no schedules attached to them
    # Because we reassigned all schedules to NEW section IDs.
    
    # Wait, some old sectons might be the ones we just created if they matched the name exactly.
    # But usually, they didn't. Let's delete any CourseSection that has 0 schedules.
    all_sections_now = CourseSections.query.all()
    deleted_count = 0
    for sec in all_sections_now:
        sch_count = Schedules.query.filter_by(section_id=sec.section_id).count()
        if sch_count == 0:
            db.session.delete(sec)
            deleted_count += 1
            
    db.session.commit()
    
    print(f"Migration complete. Split schedules into new sections and deleted {deleted_count} empty old sections.")
