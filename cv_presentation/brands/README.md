# Verified company brand profiles

Brand adaptation for CV templates is **grounded input**, not model memory.

A non-Harvard template may use a company profile only when the profile identifies the target company and, for `verified_manual` or `verified_official`, includes both `verified: true` and a traceable `source_url`. If no profile is available, CV_fit renders a neutral ATS-safe fallback and labels the brand as unverified.

The design-review agent receives resolved tokens; it may decide how safely to use those tokens (headings, accents, sidebar) and review legibility/print/ATS quality. It must not invent replacement corporate colors, logos or font families.

Harvard is excluded from brand adaptation: its black/white Times New Roman visual system is locked and only application content changes.

Do not place candidate contact information, credentials, API keys or other private data in this directory.
