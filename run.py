import sys
import os

# Add backend and database directories to sys.path using absolute paths
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(ROOT_DIR, 'backend'))
sys.path.append(os.path.join(ROOT_DIR, 'database'))

from app import app
from database import db

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
