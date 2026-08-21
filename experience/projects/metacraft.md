---
schema_version: 1
last_updated: 2026-08-20
status: validated_public
public_safe: true
project_type: data_quality_toolkit
source_repo: https://github.com/jcval94/MetaCraft
primary_language: Python
---

# MetaCraft

## Summary

MetaCraft is a Python toolkit for **enriching, validating, comparing and transforming metadata/schema definitions** around pandas DataFrames. It uses YAML as a portable schema representation and adds data-quality, drift and AI-assisted research capabilities.

The project is strong evidence for data quality, metadata engineering and reusable analytical tooling.

## Core capabilities

### `update`
Enriches YAML schemas with observed statistics and sketches from a DataFrame.

Documented statistical sketches include:

- t-digest
- HyperLogLog

### `validate`
Checks consistency between a DataFrame and schema definitions, including:

- data types
- ranges
- nullability / missingness

### `compare`
Detects schema drift between schema versions.

### `export_schema`
Converts schema definitions into formats such as:

- Spark
- SQL

### `generate_expectations`
Generates Great Expectations suites from schema/metadata definitions.

### `transform`
Adjusts a DataFrame to conform to schema definitions.

### `quality_report`
Produces a simple data-quality score combining completeness and drift signals.

### `research`
Uses OpenAI integration to explore relationships and anomalies in data/metadata context.

## Engineering features

- YAML files can be read locally or from URLs
- remote ZIP archives containing multiple schemas can be downloaded and processed
- optional local cache
- internal schema representation exposed through editable `metadata.df`
- DataFrame-side edits can be propagated back to YAML
- configurable logging
- reusable OpenAI client / API configuration
- per-call overrides of model parameters

## Technologies / concepts evidenced

- Python
- Pandas
- YAML
- data validation
- data quality
- schema drift
- metadata management
- Spark/SQL schema generation
- Great Expectations
- approximate statistics / sketches
- t-digest
- HyperLogLog / cardinality estimation
- remote resource handling
- OpenAI API integration
- configurable software APIs

## CV positioning

### Data Scientist / Data Platform

> Built a Python metadata and data-quality toolkit supporting schema enrichment, validation, drift detection, Spark/SQL export and Great Expectations generation.

### GenAI + Data Quality

> Integrated OpenAI-assisted analysis into a schema-driven data-quality toolkit while preserving deterministic validation and metadata contracts.

## Usage constraints

- Do not describe MetaCraft as a full enterprise data catalog.
- Do not infer production adoption counts without a public source.
- Treat Great Expectations as demonstrated working integration, but do not claim platform-level administration unless supported elsewhere.
