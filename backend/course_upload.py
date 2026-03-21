import pandas as pd
import os
from database import db, CourseScheduleSystem, CourseScheduleStudent

def process_upload(file_path):
    """
    Parses CSV or Excel and stores in CourseScheduleSystem.
    Then rebuilds CourseScheduleStudent for the student view.
    """
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        # Clear old data
        db.session.query(CourseScheduleSystem).delete()
        db.session.query(CourseScheduleStudent).delete()
        
        rows_added = 0
        for _, row in df.iterrows():
            # Basic cleaning/mapping
            # Assuming columns: CRN, Course, Section, Day, Time, Room, Instructor
            new_row = CourseScheduleSystem(
                crn=str(row.get('CRN', '')),
                course=str(row.get('Course', '')),
                section=str(row.get('Section', '')),
                day=str(row.get('Day', '')),
                time=str(row.get('Time', '')),
                room=str(row.get('Room', '')),
                instructor=str(row.get('Instructor', ''))
            )
            db.session.add(new_row)
            rows_added += 1
        
        db.session.commit()
        
        # Rebuild course_schedule_student (grouped by course/section)
        # Simplified grouping for this example
        system_data = CourseScheduleSystem.query.all()
        grouped = {}
        for r in system_data:
            key = (r.course, r.section)
            if key not in grouped:
                grouped[key] = {
                    'days': [],
                    'time': r.time,
                    'room': r.room,
                    'instructor': r.instructor
                }
            if r.day not in grouped[key]['days']:
                grouped[key]['days'].append(r.day)
        
        for (course, section), info in grouped.items():
            days_str = ",".join(info['days'])
            student_row = CourseScheduleStudent(
                course=course,
                section=section,
                days=days_str,
                time=info['time'],
                room=info['room'],
                instructor=info['instructor']
            )
            db.session.add(student_row)
        
        db.session.commit()
        return rows_added
    except Exception as e:
        db.session.rollback()
        raise e
