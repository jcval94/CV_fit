---
schema_version: 1
last_updated: 2026-08-20
status: populated
source_priority:
  - public_credential_record
  - linkedin_public_profile
  - user_confirmed_history
usage_policy: "Only status=verified credentials may be automatically promoted into generated CVs. Pending credentials require metadata reconciliation first."
---

# Certifications

Canonical inventory of professional certifications and credentials for José Carlos Del Valle.

The purpose of this file is not to maximize the number of credentials shown on a CV. It is to preserve exact credential names, issuers, dates and identifiers so downstream CV generation can select only the certifications relevant to a vacancy.

## Verified credentials

### CERT-CS50-HARVARDX-2020

- **Credential:** CS50's Introduction to Computer Science
- **Issuer:** HarvardX — An Online Learning Initiative by Harvard University through edX
- **Issued:** July 2020
- **Credential ID:** `1986a0a4d3864cdf94fd71e77d1c2b1e`
- **Status:** verified
- **Category:** Computer Science / Software Foundations
- **CV priority:** high for software-heavy Data Science, ML Engineering and AI roles
- **Source:** public LinkedIn credential record
- **Notes:** LinkedIn also contains a June 2020 CS50 entry for the same course. Treat the two entries as the same learning achievement unless a future reconciliation proves they are distinct credentials.

### CERT-TABLEAU-DESKTOP-SPECIALIST-2020

- **Credential:** Tableau Desktop Specialist
- **Issuer:** Tableau Software
- **Issued:** June 2020
- **Credential ID / legacy badge reference:** `https://www.youracclaim.com/badges/e9fbb7ad-21f2-4d66-bb5c-73019cb70747/linked_i`
- **Status:** verified
- **Category:** Data Visualization / Business Intelligence
- **CV priority:** high when visualization, BI or stakeholder communication is relevant
- **Source:** public LinkedIn credential record

### CERT-PSM-I-2020

- **Credential:** Professional Scrum Master I
- **Issuer:** Scrum.org
- **Issued:** February 2020
- **Status:** verified
- **Category:** Agile / Delivery
- **CV priority:** medium-high for roles requiring project ownership, agile delivery or cross-functional work
- **Source:** public LinkedIn credential record
- **Privacy note:** LinkedIn exposes an email-like value as the credential ID. Do not reproduce that value in generated CVs or public artifacts.

### CERT-IBM-ANALYZING-DATA-PYTHON-2019

- **Credential:** Analyzing Data with Python
- **Issuer:** IBM
- **Issued:** October 2019
- **Credential ID:** `92c5bc10cbe143648237f259ec667c2d`
- **Status:** verified
- **Category:** Python / Data Analysis
- **CV priority:** medium
- **Source:** public LinkedIn credential record

### CERT-IBM-DS-ML-CAPSTONE-2019

- **Credential:** Data Science and Machine Learning Capstone Project
- **Issuer:** IBM
- **Issued:** October 2019
- **Credential ID:** `7551cd1904674ba0aad8d5ade7d1eb5e`
- **Status:** verified
- **Category:** Data Science / Machine Learning
- **CV priority:** medium
- **Source:** public LinkedIn credential record

### CERT-IBM-ML-PYTHON-2019

- **Credential:** Machine Learning with Python: A Practical Introduction
- **Issuer:** IBM
- **Issued:** October 2019
- **Credential ID:** `65985b23a4964c5f85f8682a62e8471f`
- **Status:** verified
- **Category:** Machine Learning / Python
- **CV priority:** medium-high for ML-focused applications
- **Source:** public LinkedIn credential record

### CERT-IBM-PYTHON-DATA-SCIENCE-2019

- **Credential:** Python Data Science
- **Issuer:** IBM
- **Issued:** October 2019
- **Credential ID:** `604110ed243a4c5d924da31f02949a68`
- **Status:** verified
- **Category:** Python / Data Science
- **CV priority:** medium
- **Source:** public LinkedIn credential record

### CERT-IBM-VISUALIZING-DATA-PYTHON-2019

- **Credential:** Visualizing Data with Python
- **Issuer:** IBM
- **Issued:** October 2019
- **Credential ID:** `75ca7e15b6b24dc89ea1cc6798f277aa`
- **Status:** verified
- **Category:** Python / Data Visualization
- **CV priority:** medium
- **Source:** public LinkedIn credential record

### CERT-IBM-PYTHON-101-2019

- **Credential:** Python 101 for Data Science
- **Issuer:** IBM
- **Issued:** September 2019
- **Credential ID:** `e42a19bb06674c849a995272cfa6f42b`
- **Status:** verified
- **Category:** Python / Data Science Foundations
- **CV priority:** low for senior roles; useful only when a vacancy explicitly values formal Python training
- **Source:** public LinkedIn credential record

## Duplicate / related credential records

### CERT-CS50-COURSE-RECORD-2020

- **Credential:** CS50's Introduction to Computer Science
- **Issuer:** CS50
- **Issued:** June 2020
- **Status:** verified_record_but_duplicate_candidate
- **Relationship:** likely represents the same course as `CERT-CS50-HARVARDX-2020`
- **Usage rule:** never count both CS50 records as two independent major certifications in a generated CV

## Known credentials requiring metadata reconciliation

The following credentials are part of the known professional history but should **not** yet be automatically inserted into generated CVs because the exact credential title, issuer, issue date or identifier still needs reconciliation against the original certificate or profile record.

### CERT-PENDING-SALESFORCE-EINSTEIN

- **Known topic:** Salesforce Einstein Analytics
- **Status:** needs_metadata_verification
- **Likely category:** Analytics / BI / Salesforce
- **Action required:** recover exact credential name, issuer and date

### CERT-PENDING-AWS-SAGEMAKER

- **Known topic:** AWS SageMaker
- **Status:** needs_metadata_verification
- **Likely category:** Cloud / Machine Learning
- **Action required:** recover exact course or certification name, issuer and date

### CERT-PENDING-GENAI

- **Known topic:** Applied Generative AI
- **Status:** needs_metadata_verification
- **Likely category:** Generative AI / LLMs
- **Action required:** recover exact credential name, issuer and date

### CERT-PENDING-RUTGERS-SUPPLY-CHAIN

- **Known topic:** Supply Chain
- **Known institution/provider:** Rutgers
- **Status:** needs_metadata_verification
- **Likely category:** Supply Chain / Operations
- **Action required:** recover exact credential name and date

### CERT-PENDING-UC3M-ML

- **Known topic:** Machine Learning
- **Known institution/provider:** Universidad Carlos III de Madrid
- **Status:** needs_metadata_verification
- **Likely category:** Machine Learning
- **Action required:** recover exact credential name and date

## Selection rules for generated CVs

1. Do not list every credential by default.
2. Prefer certifications that reinforce the target role rather than foundational certificates that are already implied by senior experience.
3. For senior Data Science / AI roles, prioritize roughly: role-specific GenAI/ML credential if verified → CS50 → Tableau when relevant → PSM I when delivery/leadership matters → selected IBM ML credential.
4. Never fabricate a credential identifier, issue date, issuer or certification level.
5. Do not describe a course completion certificate as a professional certification unless the issuer explicitly classifies it that way.
6. Do not expose credential identifiers that contain personal contact information.
