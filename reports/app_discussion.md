# AI College Scheduler - Application Discussion

This report provides an overview of the AI College Scheduler Smart System, its features, architecture, and the logic behind its core functionalities.

## 1. Application Overview
The AI College Scheduler is designed to help students and administrators manage course schedules efficiently. It leverages AI-driven conflict detection and automated schedule generation to solve traditional scheduling problems.

## 2. Core Features

### Student Dashboard
- **Course Selection**: Browse and select from available courses.
- **AI Schedule Generation**: Automated generation of conflict-free weekly timetables.
- **Interactive Timetable**: Modern CSS Grid visualization with drag-and-drop capabilities.
- **Exports**: Ability to download schedules in PDF and Excel formats.
- **AI Chatbot**: A helper bot to assist with scheduling questions.

### Admin Dashboard
- **System Stats**: Real-time overview of students, courses, sections, and instructors.
- **Master Data Management**: Full CRUD operations for courses, sections, and users.
- **File Uploads**: Batch import master schedules from CSV and Excel files.
- **Conflict Detection**: Automated scanning for room double-bookings and instructor overlaps.

## 3. Architecture

### Backend (Python/Flask)
- **Framework**: Flask serves as the web server and API layer.
- **Blueprint Pattern**: Used for clean separation of admin and student routes.
- **Authentication**: Flask-Login manages secure sessions.

### Database (SQLAlchemy/SQLite)
- **Model-Driven Design**: Detailed schemas for Students, Admins, Courses, Sections, and Schedules.
- **Data Integrity**: Foreign key constraints ensure consistency between courses and enrollments.

### Frontend (HTML/CSS/JS)
- **Modern UI**: A premium design system using Glassmorphism, CSS Grids, and responsive layouts.
- **Dynamic UX**: Vanilla JavaScript handles API interactions, DOM manipulation, and drag-and-drop logic.

## 4. Key Algorithms

### Conflict detection (`scheduler.py`)
The system analyzes time slots for every section to identify:
1. **Room Conflicts**: Multiple classes assigned to the same room at the same time.
2. **Instructor Conflicts**: An instructor assigned to multiple classes simultaneously.

The algorithm uses a robust time-parsing logic that handles 12-hour and 24-hour formats and detects any overlap between start and end times.

### Course Upload (`course_upload.py`)
Handles complex batch imports by:
1. Clearing legacy schedule tables.
2. Normalizing inconsistent day/time formats from CSV/Excel.
3. Building a simplified student-facing view for the dashboard.
