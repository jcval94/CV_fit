from __future__ import annotations

import unittest

from vacancy_pipeline.index import add_chunks, empty_index, retrieve
from vacancy_pipeline.models import VacancyChunk


class VacancyRetrievalPolicyTests(unittest.TestCase):
    def test_source_fit_is_opt_in_not_default_matching_evidence(self) -> None:
        index = empty_index()
        chunks = [
            VacancyChunk(
                chunk_id="vac-test::core",
                vacancy_id="vac-test",
                chunk_type="core",
                text="Role: Data Scientist\nCompany: Example",
                content_hash="core-hash",
                source_paths=["Vacantes/example.json"],
            ),
            VacancyChunk(
                chunk_id="vac-test::source-fit",
                vacancy_id="vac-test",
                chunk_type="source-fit",
                text="Source fit summary: exceptional banking alignment",
                content_hash="fit-hash",
                source_paths=["Vacantes/example.json"],
            ),
        ]
        add_chunks(index, chunks)

        self.assertEqual(retrieve(index, "exceptional banking alignment"), [])
        opt_in = retrieve(index, "exceptional banking alignment", include_source_fit=True)
        self.assertEqual(len(opt_in), 1)
        self.assertEqual(opt_in[0].chunk_type, "source-fit")


if __name__ == "__main__":
    unittest.main()
