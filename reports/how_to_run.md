# Setup and Execution Guide (A to Z)

Follow these steps to set up and run the AI College Scheduler Smart System on your local machine.

## Prerequisites
- **Python 3.10 or higher**
- **pip** (Python package installer)
- **SQLite3** (usually comes with Python)

## Step 1: Clone and Environment Setup
Create a virtual environment to isolate the project dependencies:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

## Step 2: Install Dependencies
Install the required Python packages:

```bash
pip install flask flask-sqlalchemy flask-login pandas openpyxl werkzeug reportlab
```

## Step 3: Initialize and Seed Database
The project includes a seeding script to populate the database with realistic test data for evaluation.

```bash
# Ensure you are in the project root
./venv/bin/python3 database/seed_data.py
```
This will create `database/instance/fload.db` and add default students, courses, instructors, and an admin account.

## Step 4: Run the Application
Start the Flask development server:

```bash
./venv/bin/python3 run.py
```
The server should now be running at `http://127.0.0.1:5000`.

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
