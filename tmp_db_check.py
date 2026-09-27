import app
from models import PendingEmailAction

with app.app.app_context():
    items = PendingEmailAction.query.all()
    print('count', len(items))
    for item in items:
        print(item.id, item.email_subject, item.status)
