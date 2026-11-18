import {esc,time} from '../utils/format.js';import {BATCH} from '../constants/enums.js';
// 异常隔离清单：展示隔离原因、补放状态；editor（admin/analyst）可发起按期间补放
export function quarantinePanel(run,items,role){
 const open=(items||[]).filter(q=>q.status==='open');
 let head=`<div class="quarantine ${run.batch_state==='isolated'?'is-open':''}"><div class="quarantine-head"><h2>异常隔离清单</h2><span class="batch ${esc(run.batch_state)}">${esc(BATCH[run.batch_state]||run.batch_state)} · v${run.version||1}</span></div>`;
 if(run.replay_error)head+='<p class="error">'+esc(run.replay_error)+'</p>';
 if(!items||!items.length)return head+'<p class="empty">本批次无隔离记录，全部底稿均通过逐条校验。</p></div>';
 const rows=items.map(q=>({编号:q.id,期间:q.period,底稿编号:q.source_id,隔离原因:(q.reasons||[]).join('；'),状态:q.status==='open'?'待补齐':'已补放 '+time(q.resolved),原始底稿:JSON.stringify(q.raw)}));
 const cols=['编号','期间','底稿编号','隔离原因','状态','原始底稿'];
 const table='<div class="table-wrap"><table><thead><tr>'+cols.map(k=>'<th>'+esc(k)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr class="'+(r.状态.startsWith('待')?'q-open':'q-resolved')+'">'+cols.map(k=>'<td>'+esc(r[k])+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>';
 const periods=[...new Set(open.map(q=>q.period))];
 let actions='';
 if(open.length&&role!=='viewer'){
  actions=`<form id="replay-form" data-id="${run.id}"><label>补放期间（默认全部待补齐期间）<select name="period"><option value="">全部受影响期间</option>${periods.map(p=>'<option>'+esc(p)+'</option>').join('')}</select></label><button ${run.status==='replaying'?'disabled':''}>${run.status==='replaying'?'补放重算中…':'补齐底稿后按期间补放重算'}</button><span class="hint">仅重放受影响期间，成功后原子切换；失败保留 v${run.version||1} 旧版结果</span></form>`;
 }
 const summary=`<p class="hint">输入 ${run.snapshot.total_records??'?'} 条 = 合格 ${run.snapshot.accepted_records??'?'} 条 + 隔离 ${run.snapshot.quarantined_records??'?'} 条；异常记录全部留痕，不静默丢弃。待补齐 ${open.length} 条，涉及 ${periods.length} 个期间。</p>`;
 return head+summary+table+actions+'</div>';
}
