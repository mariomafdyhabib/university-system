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

def generate_schedule_variants(student_id, course_ids):
    """
    Finds all valid combinations of sections for the given course_ids.
    Returns 3 options: Condensed, Spread, Moderate.
    """
    from database import CourseSections, Schedules
    
    # 1. Fetch all sections and their schedules for the requested courses
    course_sections_data = {}
    for cid in course_ids:
        secs = CourseSections.query.filter_by(course_id=cid).all()
        sec_list = []
        for s in secs:
            schs = Schedules.query.filter_by(section_id=s.section_id).all()
            sch_details = [{
                'day': sch.day_of_week,
                'start': parse_time(sch.start_time),
                'end': parse_time(sch.end_time)
            } for sch in schs]
            sec_list.append({
                'section_id': s.section_id,
                'schedules': sch_details
            })
        course_sections_data[cid] = sec_list

    # 2. Backtracking to find all valid combinations
    all_valid_combinations = []
    course_id_list = list(course_sections_data.keys())

    def find_combinations(index, current_sections, current_schedules):
        if index == len(course_id_list):
            all_valid_combinations.append(list(current_sections))
            return

        cid = course_id_list[index]
        for sec in course_sections_data[cid]:
            # Check for conflict with already chosen sections
            conflict = False
            for ns in sec['schedules']:
                for es in current_schedules:
                    if ns['day'] == es['day']:
                        if times_overlap(ns['start'], ns['end'], es['start'], es['end']):
                            conflict = True
                            break
                if conflict: break
            
            if not conflict:
                find_combinations(
                    index + 1, 
                    current_sections + [sec['section_id']], 
                    current_schedules + sec['schedules']
                )

    find_combinations(0, [], [])

    if not all_valid_combinations:
        raise Exception("Could not find any non-conflicting combination of sections for these courses.")

    # 3. Score and pick variants
    def evaluate_schedule(section_ids):
        # We need the schedule details to calculate metrics
        schedules = []
        for sid in section_ids:
            schs = Schedules.query.filter_by(section_id=sid).all()
            for sch in schs:
                schedules.append({
                    'day': sch.day_of_week,
                    'start': parse_time(sch.start_time),
                    'end': parse_time(sch.end_time)
                })
        
        days = {}
        for s in schedules:
            if s['day'] not in days:
                days[s['day']] = {'min': s['start'], 'max': s['end']}
            else:
                days[s['day']]['min'] = min(days[s['day']]['min'], s['start'])
                days[s['day']]['max'] = max(days[s['day']]['max'], s['end'])
        
        num_days = len(days)
        total_span = sum(d['max'] - d['min'] for d in days.values())
        return num_days, total_span

    # Score all combinations
    scored_combinations = []
    for combo in all_valid_combinations:
        num_days, total_span = evaluate_schedule(combo)
        scored_combinations.append({
            'section_ids': combo,
            'num_days': num_days,
            'total_span': total_span
        })

    # Sort for variants
    # Condensed: Min days, then min total_span
    condensed = sorted(scored_combinations, key=lambda x: (x['num_days'], x['total_span']))[0]
    
    # Spread: Max days, then max total_span (or just max total_span)
    spread = sorted(scored_combinations, key=lambda x: (x['num_days'], x['total_span']), reverse=True)[0]
    
    # Moderate: Middle of the list after sorting by days
    sorted_by_days = sorted(scored_combinations, key=lambda x: x['num_days'])
    moderate = sorted_by_days[len(sorted_by_days) // 2]

    return {
        "condensed": condensed['section_ids'],
        "spread": spread['section_ids'],
        "moderate": moderate['section_ids']
    }

def auto_generate_schedule(student_id, course_ids):
    """
    Backward compatibility or simple default.
    """
    variants = generate_schedule_variants(student_id, course_ids)
    return variants['moderate']
