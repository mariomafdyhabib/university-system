# Setup and Execution Guide (A to Z)

Follow these steps to set up and run the AI College Scheduler Smart System on your local machine.

## Prerequisites
- **Python 3.10 or higher**
- **pip** (Python package installer)
- **SQLite3** (usually comes with Python)
- **PowerShell** (for Windows commands below)

## Step 1: Clone and Environment Setup
Create a virtual environment to isolate the project dependencies:

```bash
python -m venv venv
```

### Activate Virtual Environment

#### Windows (PowerShell)
```powershell
venv\Scripts\activate
```

If PowerShell blocks activation with an execution policy error, run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
venv\Scripts\activate
```

#### macOS/Linux
```bash
source venv/bin/activate
```

## Step 2: Install Dependencies
Install the required Python packages:

```bash
pip install flask flask-sqlalchemy flask-login pandas openpyxl werkzeug reportlab fpdf2
```

`fpdf2` is required because the backend imports `FPDF`.

## Step 3: Initialize and Seed Database
The project includes a seeding script to populate the database with realistic test data for evaluation.

```bash
# Ensure you are in the project root
python database/seed_data.py
```

Important:
- The seeder expects an Excel file named `Schedule_Report_Improved_08-03-2026-15-02-40.xlsx` in the project root.
- If the file is missing, seeding fails with `FileNotFoundError`.

This will create/update `instance/fload.db` and add default students, courses, instructors, sections, schedules, enrollments, and an admin account.

## Step 4: Run the Application
Start the Flask development server:

```bash
python run.py
```
The server should now be running at `http://127.0.0.1:5000`.

## Quick Troubleshooting
- `python3` not found on Windows: use `python` instead.
- `source` is not recognized in PowerShell: use `venv\Scripts\activate`.
- `No module named 'fpdf'`: install `fpdf2` with pip.
- `./venv/bin/python...` not recognized on Windows: use `python ...` commands.

## Step 5: Accessing the Dashboards

### Student Dashboard
- **URL**: `http://127.0.0.1:5000/` (Landing page) -> Click "Student Login".
- **Test Credentials**:
    - Email: `alice@example.com`
    - Password: `password123`

### Admin Dashboard
- **URL**: `http://127.0.0.1:5000/admin.html`
- **Credentials**:
    - Username: `admin`
    - Password: `admin123`

## Directory Structure Overview
- `backend/`: Core logic, API routes, and Flask app.
- `frontend/`: HTML, CSS, and JS assets.
- `database/`: SQLAlchemy models, seeding scripts, and SQLite database.
- `reports/`: Documentation and project guides.
