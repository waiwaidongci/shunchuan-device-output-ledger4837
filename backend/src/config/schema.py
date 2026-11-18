from sqlalchemy import text,inspect
from src.config.database import engine
def upgrade_schema():
 # SQLAlchemy create_all 只补新表；已存在的 oeeruns 表需幂等补列，失败不阻断启动
 from src.models import identity,source,run
 run.Base.metadata.create_all(engine)
 inspector=inspect(engine)
 existing={c['name'] for c in inspector.get_columns('oeeruns')}
 additions={'batch_state':"VARCHAR(20) DEFAULT 'reconciled'",'version':'INTEGER DEFAULT 1','replay_error':'TEXT'}
 with engine.begin() as conn:
  for name,ddl in additions.items():
   if name not in existing:
    conn.execute(text('ALTER TABLE oeeruns ADD COLUMN '+name+' '+ddl))
