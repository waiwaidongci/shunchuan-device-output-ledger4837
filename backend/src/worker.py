import time,json,traceback
from pathlib import Path
import redis
from src.config.database import Base,engine,Session
from src.config.settings import REDIS_URL
from src.models import identity,source,run
from src.models.run import Run
from src.services.batch import execute_run,apply_replay
from src.services.delivery import tick
from src.config.schema import upgrade_schema
upgrade_schema()
r=redis.Redis.from_url(REDIS_URL)
while True:
 Path('/tmp/worker-heartbeat').write_text(str(time.time()))
 try:
  item=r.lpop('report-jobs')
  if item:
   payload=json.loads(item)
   # 兼容旧版纯id消息
   if isinstance(payload,int): payload={'run_id':payload,'kind':'run'}
   with Session() as db:
    if payload.get('kind')=='replay': apply_replay(db,r,payload['run_id'],payload.get('affected',[]))
    else: execute_run(db,r,payload['run_id'])
  with Session() as db: tick(db)
 except Exception: traceback.print_exc()
 time.sleep(1)
