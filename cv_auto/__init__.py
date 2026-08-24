AUTO_GENERATION_SCHEMA_VERSION = 1
AUTO_GENERATION_PIPELINE_VERSION = 1
# Bump when generation semantics change even if vacancy/evidence content does not.
# Stored entries with an older logic version are reprocessed exactly once.
# v5: Technical Modern + deterministic visual/presentation gates are authoritative.
# v6: Adaptive cost-first review loop caps production at three reviews, uses Luna
#     only as the initial screen, escalates revisions to Terra, and removes Sol
#     from routine automatic generation.
AUTO_GENERATION_LOGIC_VERSION = 6
