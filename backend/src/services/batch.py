import json,time,traceback
from src.models.source import Source
from src.models.run import Run,Quarantine
from src.services.calculation import calculate
from src.services.validation import inspect_source
from src.services.audit import log
from src.services.report import _checksum
LOCK_TTL=120
def _lock(redis_client,run_id):
 token='worker-'+str(time.time())
 ok=redis_client.set('run-lock:'+str(run_id),token,nx=True,ex=LOCK_TTL)
 return token if ok else None
def _unlock(redis_client,run_id,token):
 try:
  if redis_client.get('run-lock:'+str(run_id))==token.encode(): redis_client.delete('run-lock:'+str(run_id))
 except Exception: traceback.print_exc()
def execute_run(db,redis_client,run_id):
 run=db.get(Run,run_id)
 if not run or run.status!='queued': return
 token=_lock(redis_client,run_id)
 if not token: return
 try:
  run.status='running';db.commit()
  try:
   # 合格记录已在提交阶段隔离分类，这里只对合格快照核算；整批结果一次写入
   run.result=calculate(run.snapshot['sources'],run.snapshot['policy']);run.status='completed';run.error=None
   db.commit()
  except Exception as exc:
   db.rollback();run=db.get(Run,run_id);run.status='failed';run.error=str(exc);db.commit();traceback.print_exc()
 finally: _unlock(redis_client,run_id,token)
def apply_replay(db,redis_client,run_id,affected):
 run=db.get(Run,run_id)
 if not run or run.status!='replaying': return
 token=_lock(redis_client,run_id)
 if not token: return
 try:
  now=time.time();old_version=run.version or 1
  current_rows=[x for x in db.query(Source).order_by(Source.id).all() if x.data.get('period') in affected]
  if not current_rows: raise ValueError('受影响期间底稿缺失，已保留旧版结果')
  new_accepted=[];new_quarantine=[]
  for x in current_rows:
   reasons=inspect_source(x.data)
   if reasons: new_quarantine.append(Quarantine(run_id=run_id,source_id=x.id,period=x.data.get('period'),reasons=reasons,raw=x.data,status='open',created=now))
   else: new_accepted.append(x.data)
  kept=[s for s in run.snapshot['sources'] if s.get('period') not in affected]
  merged_sources=kept+new_accepted
  open_rows=db.query(Quarantine).filter_by(run_id=run_id,status='open').all()
  still_open_elsewhere=[q for q in open_rows if q.period not in affected]
  # 单事务原子切换：快照、结果、校验和、隔离清单与状态同时落地，失败整体回滚保留旧版
  for q in open_rows:
   if q.period in affected:
    q.status='resolved';q.resolved=now;q.resolved_note='v'+str(old_version)+'补放重算，该期间重新分类'
  db.add_all(new_quarantine)
  total=(run.snapshot.get('total_records',0))
  # 受影响期间的记录数以当前底稿为准，未受影响期间保持冻结口径
  old_affected_count=sum(1 for s in run.snapshot['sources'] if s.get('period') in affected)+sum(1 for q in open_rows if q.period in affected)
  snapshot={'policy':run.snapshot['policy'],'sources':merged_sources,'period':run.snapshot['period'],
   'total_records':total-old_affected_count+len(current_rows),
   'accepted_records':len(merged_sources),
   'quarantined_records':len(still_open_elsewhere)+len(new_quarantine),
   'replayed_periods':sorted(set(run.snapshot.get('replayed_periods',[]))|set(affected))}
  result=calculate(merged_sources,run.snapshot['policy'])
  run.snapshot=snapshot;run.result=result;run.checksum=_checksum(snapshot)
  run.version=old_version+1;run.replay_error=None
  run.batch_state='isolated' if (still_open_elsewhere or new_quarantine) else 'reconciled'
  run.status='completed'
  log(db,'worker','run.replay.done',str(run_id)+' v'+str(run.version)+' 期间='+','.join(affected)+' 剩余隔离'+str(snapshot['quarantined_records']))
  db.commit()
 except Exception as exc:
  traceback.print_exc()
  db.rollback()
  # 失败保留旧版：有旧结果则恢复 completed 并记录补放错误；无旧版则回到 failed，绝不写入半成品
  fallback=db.get(Run,run_id)
  if fallback:
   if fallback.result is not None:
    fallback.status='completed';fallback.replay_error='补放失败，已保留v'+str(fallback.version or 1)+'旧版：'+str(exc)
   else:
    fallback.status='failed';fallback.replay_error='补放失败且无旧版结果：'+str(exc)
   db.commit()
 finally: _unlock(redis_client,run_id,token)
