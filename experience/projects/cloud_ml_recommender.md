---
schema_version: 3
record_id: project-cloud-ml-recommender
record_type: project
last_updated: 2026-08-20
status: validated_public
confidence: high
visibility: public
public_safe: true
project_type: cloud_ml_deployment
source_repo: https://github.com/jcval94/cloud_function
primary_language: Python
cloud: Google Cloud
source_refs:
  - SRC-GITHUB-JCVAL94-PUBLIC
  - SRC-PORTFOLIO-PUBLIC-2026-08
---

# Cloud ML Recommender

## Summary

Public Google Cloud Function implementation for serving a text-based TV-series recommendation workflow. The project combines cloud-hosted model artifacts, Transformer embeddings, a Keras model, cosine similarity and OpenAI-assisted translation behind an HTTP-triggered serverless function.

This repository provides direct evidence that José Carlos has implemented **cloud model serving and end-to-end ML inference plumbing**, not only offline modeling.

## Deployment evidence

The public deployment script uses Google Cloud Functions Gen2 with:

- Python 3.10 runtime
- HTTP trigger
- `us-central1`
- explicit CPU / memory allocation
- explicit timeout configuration
- environment-variable based OpenAI credential injection

The exact infrastructure settings are implementation details and should not normally be shown on a CV.

## ML inference workflow

The public code demonstrates a pipeline that:

1. receives request data through an HTTP function
2. translates Spanish text to English through OpenAI when required
3. loads model/data artifacts from Google Cloud Storage
4. loads a Keras model
5. loads a Transformer tokenizer/model
6. generates text embeddings
7. predicts genre-score representations
8. computes cosine similarity against stored series representations
9. returns top recommendations in JSON-friendly structures
10. translates recommendation text back to Spanish

## Technologies evidenced

- Google Cloud Functions Gen2
- Google Cloud Storage
- Python
- Flask request/JSON patterns
- TensorFlow / Keras
- Hugging Face Transformers
- BERT / TinyBERT-style text embeddings
- scikit-learn cosine similarity
- Pandas / NumPy
- OpenAI API
- model artifact loading
- logging
- exception handling / fallback paths
- HTTP model serving

## Production-minded patterns

The code contains:

- explicit logging setup
- staged exception handling for artifact/model loading
- local temporary-file handling
- fallbacks when local Transformer loading fails
- batch embedding generation
- separation between representation generation, similarity ranking and output formatting

## CV positioning

### ML Engineer / Production Data Scientist

> Implemented a serverless ML recommendation endpoint on Google Cloud Functions, integrating Cloud Storage model artifacts, Transformer embeddings, Keras inference, similarity ranking and OpenAI-assisted language handling.

### End-to-End Data Scientist

> Built the inference path from HTTP request through cloud artifact loading, NLP embeddings and model scoring to ranked recommendation output.

## Usage constraints

- Do not imply Kubernetes or container-orchestration ownership from this project; it is a serverless Cloud Functions deployment.
- Do not expose bucket names, environment values or deployment internals in generated CVs.
- Do not describe the recommender as a production commercial service unless deployment/adoption evidence is separately confirmed.
