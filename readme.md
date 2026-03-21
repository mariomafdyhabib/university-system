Main Features
1. Authentication
Handles login and registration.
Routes:
POST /register
POST /login
POST /admin/login
POST /logout
Uses:
Flask-Login
Werkzeug password hashing
2. Course Data API
Returns course and section data to the frontend.
Routes:
GET /courses
GET /sections
It supports two data sources:
 1️⃣ Normal database tables
 2️⃣ Uploaded schedule file
3. AI Schedule Generation
Endpoint:
POST /generate-schedule
Two modes:
Mode 1 — Upload Based
Uses:
CourseScheduleSystem
Steps:
student selects sections
       ↓
system loads uploaded schedule
       ↓
detect time conflicts
       ↓
save enrollment
Uses functions from scheduler.py.
Mode 2 — Database Based
Uses OR-Tools optimization:
requested courses
     ↓
get sections
     ↓
detect conflicts
     ↓
AI selects best sections
     ↓
store enrollments
4. Schedule View
Endpoint:
GET /schedule
Returns a student's timetable.
5. Edit Schedule
Endpoint:
POST /edit-schedule
Supports:
delete course
replace section
Before replacement it checks time conflicts.
6. Export Schedule
Endpoints:
GET /schedule/export/pdf
GET /schedule/export/excel
Uses:
reportlab → PDF
openpyxl → Excel
7. Course Recommendations
GET /recommendations
Uses:
recommendation.py
(not included in your upload)
8. Chatbot
Endpoint:
POST /chatbot
Uses the file:
chatbot.py




database.py — Database Models
What it does
Defines all database tables using SQLAlchemy ORM.
This file is the data structure of the entire system.
Main Tables
Students
Students
Fields:
student_id
name
email
password_hash
major_id
year
is_active
Courses
Courses
Example:
CS101
Calculus I
Physics
Course Sections
CourseSections
Example:
CS101 Section A
CS101 Section B
Each section has an instructor.
Schedule
Schedules
Stores:
day_of_week
start_time
end_time
classroom
Example:
Monday
10:00 - 12:00
Room A101
Enrollment
Enrollments
Links students to sections.
Constraints:
student cannot enroll twice
Upload Tables
Raw uploaded schedule
course_schedule_system
Example row:
CRN: 1234
Course: Math
Section: A
Day: Sunday
Time: 10-12
Student view
course_schedule_student
Groups rows into readable format.
Example:
Sun,Tue
10:00 - 12:00
Math A
Admin table
Admins
Used for admin login.









scheduler.py — AI Schedule Generator
What it does
This file contains the AI scheduling algorithm.
It uses:
Google OR-Tools
Constraint Programming
Core Concept
Each section is treated as a variable:
x_i = 1 → section selected
x_i = 0 → section not selected
Constraints
One section per course
sum(sections for course) = 1
No time conflicts
If two sections overlap:
x_i + x_j ≤ 1
Objective
Maximize:
number of courses scheduled
Conflict Detection
Function:
detect_conflicts()
Rule:
same day AND
(start1 < end2 AND end1 > start2)
Gap Optimization
After the solver runs, it improves the schedule.
Goal:
minimize gaps between classes
Example:
Bad schedule:
9–10
2–3
Gap = 4 hours
Better schedule:
9–10
10–11
Gap = 0



course_upload.py — Upload Course Schedule Files
What it does
Allows admins to upload:
CSV
Excel (.xlsx)
containing course schedules.
Upload Flow
Admin uploads file
       ↓
parse CSV / Excel
       ↓
clean data
       ↓
store in database
       ↓
build student-friendly table
Data Cleaning
Normalize days
Example:
sun → Sunday
mon → Monday
Convert time
Example:
2:00 PM → 14:00
Tables affected
Replace:
course_schedule_system
Rebuild:
course_schedule_student
Grouping Logic
Rows like:
Sun 10-12
Tue 10-12
Become:
Sun,Tue 10-12






admin_routes.py — Admin API
What it does
Defines all admin management APIs.
Accessible only if:
current_user.user_type == "admin"
Admin Capabilities
Students
GET /admin/students
PUT /admin/update-student
POST /admin/reset-student-password
Courses
GET /admin/courses
POST /admin/create-course
PUT /admin/update-course
DELETE /admin/delete-course
Sections
POST /admin/create-section
PUT /admin/update-section
DELETE /admin/delete-section
Instructors
POST /admin/create-instructor
PUT /admin/update-instructor
DELETE /admin/delete-instructor
Classrooms
POST /admin/create-classroom
PUT /admin/update-classroom
DELETE /admin/delete-classroom
Schedules
POST /admin/create-schedule
PUT /admin/update-schedule
DELETE /admin/delete-schedule
Upload Course Schedule
POST /admin/upload-course-file
Uses:
process_upload()
from course_upload.py.
Detect System Conflicts
GET /admin/conflicts
Detects:
room conflicts
instructor conflicts
Example:
Room A101 used by two classes at same time





chatbot.py — Simple Helper Bot
What it does
Very simple FAQ chatbot.
It checks keywords.
Example:
if "schedule" → show schedule help
if "conflict" → explain conflicts
Example code logic:
if "schedule" in message:
   return schedule help

if "conflict" in message:
   return conflict explanation
Otherwise:
"I'm a simple helper bot"
This is a placeholder for future AI chatbot.





How All Files Work Together
Frontend
  │
  ▼
app.py  (Flask server)
  │
  ├── database.py → database models
  │
  ├── scheduler.py → AI schedule generator
  │
  ├── course_upload.py → parse Excel/CSV
  │
  ├── admin_routes.py → admin management APIs
  │
  └── chatbot.py → simple assistant



Overall System Architecture


                    Frontend
                           │
                          ▼
                       Flask API
                         app.py
                              │
  ┌──────────┼───────────┐
  ▼                        ▼                           ▼
database.py     scheduler.py           course_upload.py
  │                              │                            │
  ▼                            ▼                           ▼
MySQL         /         SQLite                 Excel/CSV

