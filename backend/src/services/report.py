import hashlib,json,time
from fastapi import HTTPException
from src.models.source import Source,Policy
from src.models.run import Run,Quarantine
from src.services.audit import log
from src.services.validation import inspect_source
from src.config.settings import REDIS_URL
import redis
def _checksum(snapshot):
 return hashlib.sha256(json.dumps(snapshot,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def _period_sources(db,period):
 return [x for x in db.query(Source).order_by(Source.id).all() if period=='全部' or x.data.get('period')==period]
def _classify(db,run_id,rows,now):
 # 逐条校验并分类：合格进入核算，异常进入隔离清单（带原因与原始数据），二者之和=输入总数，不丢一条
 accepted=[];quarantined=[]
 for x in rows:
  reasons=inspect_source(x.data)
  if reasons:
   quarantined.append(Quarantine(run_id=run_id,source_id=x.id,period=x.data.get('period'),reasons=reasons,raw=x.data,status='open',created=now))
  else: accepted.append(x.data)
 return accepted,quarantined
def submit(db,user,body):
 policy=db.get(Policy,body.policy_id)
 if not policy: raise HTTPException(404,'口径版本不存在')
 rows=_period_sources(db,body.period)
 if not rows: raise HTTPException(422,'所选期间没有底稿')
 now=time.time()
 obj=Run(name=body.name,status='queued',snapshot={'policy':policy.data,'sources':[],'period':body.period},created=now,approved=False,batch_state='reconciled',version=1)
 db.add(obj);db.flush()
 accepted,quarantined=_classify(db,obj.id,rows,now)
 db.add_all(quarantined)
 snapshot={'policy':policy.data,'sources':accepted,'period':body.period,'total_records':len(rows),'accepted_records':len(accepted),'quarantined_records':len(quarantined)}
 obj.snapshot=snapshot;obj.checksum=_checksum(snapshot);obj.batch_state='isolated' if quarantined else 'reconciled'
 log(db,user.email,'run.queue',body.name+' 合格'+str(len(accepted))+'条/隔离'+str(len(quarantined))+'条')
 db.commit()
 redis.Redis.from_url(REDIS_URL).rpush('report-jobs',json.dumps({'run_id':obj.id,'kind':'run'}))
 return obj
def replay(db,user,run_id,periods=None):
 obj=db.get(Run,run_id)
 if not obj: raise HTTPException(404,'报告不存在')
 if obj.status in ('queued','running','replaying'): raise HTTPException(409,'批次正在处理中，暂不可补放')
 if obj.batch_state!='isolated': raise HTTPException(409,'该批次无待补齐的隔离记录，无需补放')
 # 仅重放受影响期间：默认取当前仍 open 的隔离记录所属期间
 open_q=db.query(Quarantine).filter_by(run_id=run_id,status='open').all()
 affected=sorted({q.period for q in open_q if not periods or q.period in periods})
 if periods:
  unknown=set(periods)-{q.period for q in open_q}
  if unknown: raise HTTPException(422,'所选期间没有待补齐的隔离记录：'+','.join(sorted(unknown)))
 if not affected: raise HTTPException(422,'没有受影响期间需要重放')
 current_rows=[x for x in db.query(Source).order_by(Source.id).all() if x.data.get('period') in affected]
 if not current_rows: raise HTTPException(422,'受影响期间的底稿已不存在，无法补放；请先补录底稿')
 now=time.time()
 # 状态翻转随事务提交：并发读取只能看到旧版（completed）或重放后的新版，看不到中间态
 obj.status='replaying';obj.replay_error=None
 log(db,user.email,'run.replay.start',str(run_id)+' 期间='+','.join(affected))
 db.commit()
 redis.Redis.from_url(REDIS_URL).rpush('report-jobs',json.dumps({'run_id':run_id,'kind':'replay','affected':affected,'source_ids':[x.id for x in current_rows],'queued_at':now}))
 return obj
def reset_stuck(db,user,run_id):
 # 故障恢复：worker 崩溃导致批次卡在处理态时，由负责人恢复到可读状态；补放从未覆盖旧结果，故直接还原状态
 obj=db.get(Run,run_id)
 if not obj: raise HTTPException(404,'报告不存在')
 if obj.status not in ('queued','running','replaying'): raise HTTPException(409,'批次未卡在处理态，无需恢复')
 if obj.status=='queued':
  obj.status='failed';obj.error='排队任务被负责人手动恢复，可重新提交核算'
 elif obj.result is not None:
  obj.status='completed';obj.replay_error='处理中断，已恢复v'+str(obj.version or 1)+'旧版结果，可再次补放'
 else:
  obj.status='failed';obj.error='处理中断且无可用旧版结果，请重新提交核算'
 log(db,user.email,'run.reset',str(run_id)+' '+obj.status);db.commit()
 try: redis.Redis.from_url(REDIS_URL).delete('run-lock:'+str(run_id))
 except Exception: pass
 return obj
def approve(db,user,id,note):
 obj=db.get(Run,id)
 if not obj: raise HTTPException(404,'报告不存在')
 if obj.status!='completed': raise HTTPException(409,'仅可复核已完成报告')
 if obj.batch_state!='reconciled': raise HTTPException(409,'批次尚未完成核对（仍有隔离记录），不得复核')
 if obj.approved: raise HTTPException(409,'报告已经复核')
 obj.approved=True;obj.review=note;log(db,user.email,'run.approve',id);db.commit();return obj
