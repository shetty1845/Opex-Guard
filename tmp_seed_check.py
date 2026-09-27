from app import app

client = app.test_client()
resp = client.post('/api/seed')
print(resp.status_code)
print(resp.get_data(as_text=True))
