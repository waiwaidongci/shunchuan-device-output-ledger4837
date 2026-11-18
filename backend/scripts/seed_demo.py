import json,random
from src.config.database import Base,engine,Session
from src.config.settings import CONFIG
from src.models.identity import User
from src.models.source import Source,Policy,Period
from src.models import run
from src.utils.security import password_hash
from src.services.validation import validate_source

def demo_rows():
 rng=random.Random(42);rows=[]
 for i in range(240):
  total=rng.randint(600,1050);rows.append({'period':'2026-11-'+str(1+i%20).zfill(2),'department':['试制机A','试制机B','试制机C'][i%3],'start':480,'end':1020,'ideal_seconds':25,'total':total,'good':total-rng.randint(10,60),'downtime':[[540,570],[560,590],[950,970]]})
 return rows

def seed():
 Base.metadata.create_all(engine)
 with Session() as db:
  for role in ('admin','analyst','viewer'):
   if not db.query(User).filter_by(email=role+'@demo.local').first():db.add(User(email=role+'@demo.local',role=role,password=password_hash('Demo2026!')))
  rows=demo_rows()
  for name in sorted(set(r['period'] for r in rows)):
   if not db.query(Period).filter_by(name=name).first():db.add(Period(name=name,description='合成演示业务期间，seed=42'))
  for i,data in enumerate(rows):
   validate_source(data);key='demo-'+str(i+1)
   if not db.query(Source).filter_by(natural_key=key).first():db.add(Source(natural_key=key,data=data))
  if not db.query(Policy).filter_by(version=CONFIG['policy']['version']).first():db.add(Policy(version=CONFIG['policy']['version'],data=CONFIG['policy']))
  db.commit();print(json.dumps({'users':db.query(User).count(),'sources':db.query(Source).count(),'policies':db.query(Policy).count(),'periods':db.query(Period).count()},ensure_ascii=False))
if __name__=='__main__':seed()
