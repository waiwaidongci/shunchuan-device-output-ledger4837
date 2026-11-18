// API实体字段约定：来源{id,natural_key,data}、口径{id,version,data}、报告{id,status,snapshot,checksum,result,approved,batch_state,version,replay_error}、隔离{id,run_id,period,source_id,reasons,raw,status,resolved}、计划{next_at,enabled}。
export const ENTITY_KEYS=['sources','policies','runs','schedules','deliveries'];
