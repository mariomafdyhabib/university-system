import sys, os
from flask import Flask
sys.path.append(os.path.abspath('backend'))
sys.path.append(os.path.abspath('database'))
from database import db, Schedules

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.abspath('database/instance/fload.db')}"
db.init_app(app)

with app.app_context():
    def parse(s):
        parts = s.split()
        h, m = map(int, parts[0].split(':'))
        if parts[1] == 'PM' and h != 12: h += 12
        if parts[1] == 'AM' and h == 12: h = 0
        return h * 60 + m

    l = []
    for s in Schedules.query.all():
        try:
            l.append((parse(s.start_time), parse(s.end_time)))
        except: pass
    if l:
        print(f"Min Start: {min(i[0] for i in l)}")
        print(f"Max End: {max(i[1] for i in l)}")
