---
schema_version: 3
record_id: project-bbva-data-quality-mlops
record_type: project
status: canonical
last_updated: 2026-08-20
confidence: high
visibility: public
public_safe: true
organization: BBVA México
period: 2024-present
source_refs:
  - SRC-USER-CONFIRMED-2026-08-20
  - SRC-TRAJECTORY-2024-2026-CURATED
---

# Data Quality, MLOps and Analytical Engines

## Summary

This record consolidates production-quality contributions that sit outside a single model: forensic debugging, schema cleanup, code review, distributed-pipeline refactoring, cloud productization and resilient automation.

## Quality and debugging

Evidence supports:

- tracing a false positive from final report back to a typographical/source-data error
- correcting the attribution before an incorrect sanction
- automating column/schema normalization with regular expressions and the PySpark DataFrame API
- improving interoperability and reducing repeat failures

## Code review and MLOps

- reviewed and approved pull requests in critical analytical repositories
- validated PySpark components before integration
- worked with versioned deployment and internal MLOps practices
- used internal deployment frameworks primarily as a user/reviewer rather than claiming framework authorship

## Engine and pipeline refactoring

Evidence supports:

- replacing deprecated input dependencies
- making temporal cutoff logic deterministic
- partitioning a memory-intensive engine to support more frequent execution
- resolving out-of-memory bottlenecks in distributed workloads
- improving traceability through dictionaries and explicit data contracts

## Cloud and production delivery

- helped move a geolocation/data-integration engine from sandbox to production
- coordinated environment approval/certification with development stakeholders
- worked with PySpark and AWS-based analytical execution
- produced reusable master outputs for downstream analytics

No downstream financial recovery metric is currently approved.

## Secure automation

A supporting vendor-validation workstream demonstrates:

- Python/Selenium automation under InfoSec constraints
- local execution when cloud agents were not permitted
- retries, logs, batch processing and CSV outputs
- recognition of later recalibration needs when false positives or operational saturation appeared

## Approved public narratives

> Refactored distributed analytical pipelines affected by deprecated inputs and memory bottlenecks, improving temporal determinism, traceability and execution frequency.

> Resolved production false positives through forensic data lineage and automated PySpark schema normalization.

> Reviewed critical analytical code and supported production deployment of AWS/PySpark data engines in a regulated environment.

## Boundaries

- Do not claim authorship of the internal MLOps framework.
- Do not claim financial recovery impact for geolocation engines without outcome evidence.
- Treat vendor RPA as a useful but recalibration-sensitive solution, not a finished autonomous control system.
