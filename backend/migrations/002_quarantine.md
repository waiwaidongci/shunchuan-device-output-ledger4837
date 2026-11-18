# 002 异常隔离核算

## 背景
坏底稿会让整批核算失败，静默跳过又会抬高有效产量。新增逐条校验与异常隔离：合格记录先形成带异常隔离清单的核算批次，异常记录补齐后只重放受影响期间，原子切换、失败保留旧版。

## 结构变更（幂等，启动时由 `src/config/schema.py` 执行）
1. 新表 `quarantine_records`：
   - `id` 主键
   - `run_id` 关联核算批次（索引）
   - `source_id` 隔离时的底稿记录编号
   - `period` 所属业务期间（索引，重放按期间定位）
   - `reasons` JSON 隔离原因数组（按【数量】/【班次时间】/【停机区间】分类）
   - `raw` JSON 原始底稿，保证异常记录不丢失
   - `status` open/resolved
   - `created`/`resolved` 时间戳、`resolved_note` 补放说明
2. `oeeruns` 补列：
   - `batch_state` reconciled/isolated，默认 reconciled
   - `version` 批次结果版本号，默认 1，每次补放成功 +1
   - `replay_error` 最近一次补放失败说明（旧版结果保留）
3. `oeeruns.snapshot` 扩展计数键：`total_records`、`accepted_records`、`quarantined_records`、`replayed_periods`；校验和覆盖全部快照键，来源仍可完整追溯。

## 规则
- 提交时逐条 `inspect_source`，合格+隔离数=输入总数；`isolated` 批次不得复核、不得建立定时交付，worker 也不会自动交付。
- 补放仅重放隔离记录所属期间；单事务更新快照/结果/校验和/隔离清单/版本，失败回滚并保留旧版。
- Redis 锁 `run-lock:{id}` 与状态门控保证并发读取只看到整批落地前或后的结果。

## 升级
已有数据库直接启动后端/worker 即自动补列补表；升级前建议备份。
