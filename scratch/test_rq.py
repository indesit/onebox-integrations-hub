from redis import Redis
from rq import Queue
import uuid

redis_conn = Redis(host='localhost', port=6379, db=0)
q = Queue('default', connection=redis_conn)

def test_func():
    return "Hello"

job = q.enqueue(test_func)
print(f"Job enqueued: {job.id}")
