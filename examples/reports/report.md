# Ops Daily Report

Current: 6 messages across 1 log file(s).
Error / critical: 3; warning: 1; unknown level: 1.

Baseline: 4 messages across 1 log file(s).
New means absent from this selected baseline snapshot; it does not mean anomalous.

## Input notes

- 1 line(s) in current input did not match a supported header; they are grouped as UNKNOWN without retaining the raw text.

## Message patterns

| Status | Service | Message template | Current | Baseline | Change | Current levels |
| --- | --- | --- | ---: | ---: | ---: | --- |
| new | database | Connection timeout on node 2 | 1 | 0 | \+1 | ERROR 1 |
| recurring | app | Health check failed for shard &lt;\*> after &lt;\*> ms | 2 | 1 | \+1 | ERROR 2 |
| recurring | app | Queue depth &lt;\*> on pool blue | 1 | 1 | \+0 | WARNING 1 |
| new | unknown | Unsupported log line | 1 | 0 | \+1 | UNKNOWN 1 |
| recurring | app | Started serving requests | 1 | 1 | \+0 | INFO 1 |
| absent | app | Disk pressure on node 5 | 0 | 1 | \-1 | \- |

## Method and sharing

Drain3 groups similar message text into templates. Baseline messages are processed first, then current messages; final templates are used for both counts.
Settings: `{'depth': 4, 'sim_th': 0.4, 'max_children': 1000, 'miner_scope': 'per_service', 'shared_pass_order': 'baseline_then_current'}`.
Severity comes from supported log headers. Unsupported lines are counted as UNKNOWN without retaining their raw text.
Template grouping does not diagnose incidents or prove that a new pattern is anomalous. Review templates in all report formats for sensitive text before sharing. No raw log excerpts are intentionally included.
