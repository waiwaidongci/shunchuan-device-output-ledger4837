import math
from src.config.settings import CONFIG
def number(value,name,minimum=0,integer=False):
 if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<minimum or (integer and int(value)!=value): raise ValueError(name+'数值不合法')
 return value
def validate_source(d):
 # 严格底稿写入校验：任一不合法直接拒绝，不落库
 errors=inspect_source(d)
 if errors: raise ValueError('；'.join(errors))
def inspect_source(d):
 # 异常隔离逐条校验：收集该记录全部问题，按数量/班次/停机分类，绝不静默丢弃
 errors=[]
 if not isinstance(d,dict): return ['底稿必须是字段对象']
 if set(d)!=set(CONFIG['fields']): return ['底稿字段必须与业务字段一致']
 for key in ('period','department'):
  if not isinstance(d.get(key),str) or not 1<=len(d.get(key,''))<=100: errors.append('【班次时间】'+key+'不能为空或过长')
 def num(key,name,**kw):
  try: number(d[key],name,**kw)
  except Exception as exc: errors.append('【数量】'+str(exc))
 num('start','开始分钟',integer=True);num('end','结束分钟',integer=True)
 if isinstance(d.get('start'),int) and isinstance(d.get('end'),int):
  if not d['start']<d['end']<=2880: errors.append('【班次时间】班次必须为正时长且不超过两日')
 num('ideal_seconds','理想秒/件',minimum=0.001);num('total','产量',integer=True);num('good','合格数',integer=True)
 if isinstance(d.get('good'),int) and isinstance(d.get('total'),int) and d['good']>d['total']: errors.append('【数量】合格数不可大于总产量')
 down=d.get('downtime')
 if not isinstance(down,list) or len(down)>100: errors.append('【停机区间】停机区间需为数组且最多100段')
 else:
  seen=set()
  for idx,pair in enumerate(down):
   tag='【停机区间】第'+str(idx+1)+'段'
   if not isinstance(pair,list) or len(pair)!=2: errors.append(tag+'必须是两个分钟数');continue
   try: number(pair[0],'停机起点');number(pair[1],'停机终点')
   except Exception as exc: errors.append(tag+str(exc));continue
   if pair[1]<=pair[0]: errors.append(tag+'停机结束需晚于开始')
   if pair[0]<0 or pair[1]>2880: errors.append(tag+'分钟数需落在0至2880范围内')
   if (pair[0],pair[1]) in seen: errors.append(tag+'与其他区间完全重复')
   seen.add((pair[0],pair[1]))
   # 班次区间存在时做跨班裁剪检查：越界停机会被算法裁剪，提示补齐而非静默吞掉
   if isinstance(d.get('start'),int) and isinstance(d.get('end'),int) and d['start']<d['end'] and (pair[0]<d['start'] or pair[1]>d['end']):
    errors.append(tag+'超出班次范围（'+str(d['start'])+'-'+str(d['end'])+'），请核对班次时间或停机区间')
 # 跨字段口径：全部停机班次不得有产量（与核算算法同口径，提前隔离）
 if not errors or all(not e.startswith('【停机区间】停机区间需为数组') for e in errors):
  if isinstance(d.get('start'),int) and isinstance(d.get('end'),int) and d['start']<d['end'] and isinstance(down,list):
   try:
    from src.services.calculation import downtime_minutes
    if d['end']-d['start']<=downtime_minutes(d['start'],d['end'],down) and isinstance(d.get('total'),int) and d['total']>0:
     errors.append('【数量】全部停机班次不得有产量')
   except Exception: pass
 return errors
def validate_policy(d):
 if not isinstance(d,dict) or not isinstance(d.get('version'),str) or not 2<=len(d['version'])<=120: raise ValueError('口径版本名不合法')
 if not isinstance(d.get('definition'),str) or not d['definition']: raise ValueError('核算说明不能为空')
