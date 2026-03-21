import requests

BASE_URL = "http://127.0.0.1:5000"

def test_scheduling_flow():
    session = requests.Session()
    
    # 1. Login
    print("Logging in...")
    login_res = session.post(f"{BASE_URL}/login", json={
        "email": "alice@example.com",
        "password": "password123"
    })
    print(f"Login Status: {login_res.status_code}")
    assert login_res.status_code == 200
    
    # 2. Get Sections
    print("Fetching sections...")
    sections_res = session.get(f"{BASE_URL}/sections")
    sections = sections_res.json()
    print(f"Found {len(sections)} sections")
    assert len(sections) > 0
    
    # 3. Generate Schedule for specific course IDs
    # Find some course IDs
    courses_res = session.get(f"{BASE_URL}/courses")
    courses = courses_res.json()
    course_ids = [c['course_id'] for c in courses[:2]]
    
    print(f"Generating schedule for course IDs: {course_ids}")
    gen_res = session.post(f"{BASE_URL}/generate-schedule", json={
        "course_ids": course_ids
    })
    print(f"Generate Status: {gen_res.status_code}, Msg: {gen_res.json().get('message') or gen_res.json().get('error')}")
    assert gen_res.status_code == 200
    
    # 4. Verify Schedule
    print("Verifying schedule...")
    sch_res = session.get(f"{BASE_URL}/schedule")
    schedule = sch_res.json()
    print(f"Schedule has {len(schedule)} entries")
    assert len(schedule) > 0
    
    # 5. Clear Schedule
    print("Clearing schedule...")
    clear_res = session.post(f"{BASE_URL}/clear-schedule")
    print(f"Clear Status: {clear_res.status_code}")
    assert clear_res.status_code == 200
    
    # 6. Verify empty
    sch_res = session.get(f"{BASE_URL}/schedule")
    assert len(sch_res.json()) == 0
    print("Verification Successful!")

if __name__ == "__main__":
    try:
        test_scheduling_flow()
    except Exception as e:
        print(f"Verification Failed: {e}")
