from sqlalchemy import Column,Integer,String,JSON,Text,Float,Boolean
from src.config.database import Base
class Run(Base):
 __tablename__='oeeruns'
 id=Column(Integer,primary_key=True); name=Column(String(120)); status=Column(String(20)); snapshot=Column(JSON); checksum=Column(String(64)); result=Column(JSON); error=Column(Text); created=Column(Float); approved=Column(Boolean,default=False); review=Column(Text,default='')
 # 异常隔离核算：reconciled=全部记录已核对完成；isolated=存在隔离记录未补齐
 batch_state=Column(String(20),default='reconciled'); version=Column(Integer,default=1); replay_error=Column(Text)
class Schedule(Base):
 __tablename__='delivery_schedules'
 id=Column(Integer,primary_key=True); name=Column(String(120)); run_id=Column(Integer); interval_seconds=Column(Integer); next_at=Column(Float); enabled=Column(Boolean,default=True)
class Delivery(Base):
 __tablename__='deliveries'
 id=Column(Integer,primary_key=True); schedule_id=Column(Integer); run_id=Column(Integer); due_key=Column(String(120),unique=True); created=Column(Float); payload=Column(JSON)
class Quarantine(Base):
 # 异常隔离清单：每条被隔离记录独立留痕，重放时按期间替换，绝不丢失或静默丢弃
 __tablename__='quarantine_records'
 id=Column(Integer,primary_key=True); run_id=Column(Integer,index=True); source_id=Column(Integer); period=Column(String(120),index=True)
 reasons=Column(JSON); raw=Column(JSON); status=Column(String(20),default='open'); created=Column(Float); resolved=Column(Float); resolved_note=Column(Text)
