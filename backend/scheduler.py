from database import db, Schedules, CourseSections, Courses, Instructors

def parse_time(time_str):
    # Very simple parser for "10:00 AM" or "14:00"
    # Returns minutes from midnight
    try:
        parts = time_str.strip().split()
        time_part = parts[0]
        h, m = map(int, time_part.split(':'))
        if len(parts) > 1:
            ampm = parts[1].upper()
            if ampm == 'PM' and h != 12: h += 12
            if ampm == 'AM' and h == 12: h = 0
        return h * 60 + m
    except:
        return 0

def times_overlap(s1_start, s1_end, s2_start, s2_end):
    return max(s1_start, s2_start) < min(s1_end, s2_end)

def detect_system_conflicts():
    """
    Checks for:
    1. Room conflicts (same classroom, same day, overlapping time)
    2. Instructor conflicts (same instructor, same day, overlapping time)
    """
    schedules = db.session.query(Schedules, CourseSections).join(CourseSections).all()
    room_conflicts = []
    instructor_conflicts = []
    
    for i in range(len(schedules)):
        for j in range(i + 1, len(schedules)):
            sch1, sec1 = schedules[i]
            sch2, sec2 = schedules[j]
            
            if sch1.day_of_week == sch2.day_of_week:
                t1_start = parse_time(sch1.start_time)
                t1_end = parse_time(sch1.end_time)
                t2_start = parse_time(sch2.start_time)
                t2_end = parse_time(sch2.end_time)
                
                if times_overlap(t1_start, t1_end, t2_start, t2_end):
                    # Room conflict
                    if sch1.classroom == sch2.classroom and sch1.classroom:
                        room_conflicts.append({
                            "schedule_a": sch1.schedule_id,
                            "schedule_b": sch2.schedule_id,
                            "classroom_id": sch1.classroom
                        })
                    
                    # Instructor conflict
                    if sec1.instructor_id == sec2.instructor_id and sec1.instructor_id:
                        instructor_conflicts.append({
                            "schedule_a": sch1.schedule_id,
                            "schedule_b": sch2.schedule_id,
                            "instructor_id": sec1.instructor_id
                        })
    
    return {
        "room_conflicts": room_conflicts,
        "instructor_conflicts": instructor_conflicts
    }

def check_student_conflict(student_id, section_id):
    """
    Returns True if the given section conflicts with ANY of the student's CURRENT enrollments.
    """
    from database import Enrollments
    new_schedules = Schedules.query.filter_by(section_id=section_id).all()
    current_enrollments = Enrollments.query.filter_by(student_id=student_id).all()
    
    for enr in current_enrollments:
        if enr.section_id == section_id: continue # Already enrolled
        existing_schedules = Schedules.query.filter_by(section_id=enr.section_id).all()
        for ns in new_schedules:
            for es in existing_schedules:
                if ns.day_of_week == es.day_of_week:
                    if times_overlap(parse_time(ns.start_time), parse_time(ns.end_time),
                                     parse_time(es.start_time), parse_time(es.end_time)):
                        return True
    return False

def auto_generate_schedule(student_id, course_ids):
    """
    For a list of course_ids, attempts to find one section per course that doesn't conflict.
    Returns list of chosen section_ids.
    """
    from database import Enrollments, CourseSections
    chosen_sections = []
    
    # First, clear existing enrollments for these courses or all? 
    # Usually safer to clear all for 'Regenerate' or just the ones being added.
    # The frontend 'Regenerate' logic suggests starting fresh.
    
    for cid in course_ids:
        sections = CourseSections.query.filter_by(course_id=cid).all()
        found = False
        for sec in sections:
            # Check conflict with what we've already chosen in this loop
            local_conflict = False
            new_schedules = Schedules.query.filter_by(section_id=sec.section_id).all()
            for chosen_id in chosen_sections:
                existing_schedules = Schedules.query.filter_by(section_id=chosen_id).all()
                for ns in new_schedules:
                    for es in existing_schedules:
                        if ns.day_of_week == es.day_of_week:
                            if times_overlap(parse_time(ns.start_time), parse_time(ns.end_time),
                                             parse_time(es.start_time), parse_time(es.end_time)):
                                local_conflict = True
                                break
                    if local_conflict: break
                if local_conflict: break
            
            if not local_conflict:
                chosen_sections.append(sec.section_id)
                found = True
                break
        if not found:
            raise Exception(f"Could not find a non-conflicting section for course ID {cid}")
            
    return chosen_sections
