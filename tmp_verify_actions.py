from app import app
from models import ActionQueue

with app.app_context():
    pending = ActionQueue.query.filter_by(status='pending').count()
    approved = ActionQueue.query.filter_by(status='approved').count()
    print('pending', pending)
    print('approved', approved)
    for item in ActionQueue.query.order_by(ActionQueue.id.desc()).limit(5).all():
        print(item.id, item.title, item.status, item.payload_json)
