from src.services.validation import validate_source,validate_policy
def downtime_minutes(start,end,intervals):
 pieces=sorted((max(start,a),min(end,b)) for a,b in intervals if min(end,b)>max(start,a))
 merged=[]
 for a,b in pieces:
  if merged and a<=merged[-1][1]:merged[-1][1]=max(merged[-1][1],b)
  else:merged.append([a,b])
 return sum(b-a for a,b in merged)
def calculate(sources,policy):
 validate_policy(policy);rows=[];warnings=[];planned=operating=ideal_total=ideal_good=0
 for s in sources:
  validate_source(s);p=s['end']-s['start'];down=downtime_minutes(s['start'],s['end'],s['downtime']);op=p-down
  it=s['total']*s['ideal_seconds']/60;ig=s['good']*s['ideal_seconds']/60
  if op<=0 and s['total']>0:raise ValueError('全部停机班次不得有产量')
  a=op/p;perf=it/op if op else 0;q=s['good']/s['total'] if s['total'] else 0
  if perf>1:warnings.append(s['department']+' '+s['period']+'性能大于1，请复核理想节拍；保留原值')
  rows.append({'日期':s['period'],'设备':s['department'],'计划分钟':p,'去重停机分钟':down,'运行分钟':op,'可用率':a,'性能':perf,'质量率':q,'OEE':ig/p})
  planned+=p;operating+=op;ideal_total+=it;ideal_good+=ig
 return {'summary':{'计划分钟':planned,'运行分钟':operating,'可用率':operating/planned if planned else 0,'性能':ideal_total/operating if operating else 0,'节拍加权质量率':ideal_good/ideal_total if ideal_total else 0,'汇总OEE':ideal_good/planned if planned else 0},'rows':rows,'method':'班次停机区间先裁剪到班次再合并。A=运行/计划；P=理想产出分钟/运行；单班Q=合格/总量。跨节拍汇总Q采用理想产出分钟加权，汇总OEE=合格产出理想分钟/计划分钟，绝不简单平均各班OEE。','warnings':warnings}
