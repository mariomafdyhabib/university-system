import sys, os
from flask import Flask
sys.path.append(os.path.abspath('backend'))
sys.path.append(os.path.abspath('database'))
from database import db, Schedules

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.abspath('database/instance/fload.db')}"
db.init_app(app)

with app.app_context():
    print(set([s.day_of_week for s in Schedules.query.all()]))
