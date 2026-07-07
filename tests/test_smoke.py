"""Smoke tests for the Google Maps Business Extractor scaffold."""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace

from app.config import AppConfig
from app.exporter import Exporter
from app.models import Business


class ProjectSmokeTests(unittest.TestCase):
    """Verify that the project scaffold behaves predictably."""

    def test_business_to_dict_contains_expected_values(self) -> None:
        """Business.to_dict should serialize every declared field."""

        business = Business(name="Example Co", rating=4.7, reviews=18)
        payload = business.to_dict()

        self.assertEqual(payload["name"], "Example Co")
        self.assertEqual(payload["rating"], 4.7)
        self.assertEqual(payload["reviews"], 18)
        self.assertIn("latitude", payload)

    def test_exporter_creates_output_files(self) -> None:
        """Exporter should create the configured output directory and files."""

        with tempfile.TemporaryDirectory() as temporary_directory:
            config = replace(
                AppConfig.from_env(),
                output_folder=temporary_directory,
            )
            exporter = Exporter(config=config)
            businesses = [Business(name="Sample Business")]

            output_dir = exporter.create_output_directory()
            csv_path = exporter.export_csv(businesses)
            json_path = exporter.export_json(businesses)

            self.assertTrue(output_dir.exists())
            self.assertTrue(csv_path.exists())
            self.assertTrue(json_path.exists())


if __name__ == "__main__":
    unittest.main()
