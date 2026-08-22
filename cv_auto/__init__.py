AUTO_GENERATION_SCHEMA_VERSION = 1
AUTO_GENERATION_PIPELINE_VERSION = 1
# Bump when generation semantics change even if vacancy/evidence content does not.
# Stored entries with an older logic version are reprocessed exactly once.
# v4: presentation semantics changed to Technical Modern + Harvard Executive,
# so v3 bundles must be regenerated once rather than being treated as current.
AUTO_GENERATION_LOGIC_VERSION = 4
