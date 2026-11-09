"""Regression coverage for dashboard actions and live-site ingestion."""

import re
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from agent_2_market_researcher.tools.agent_reach_tool import AgentReachTool
from agent_2_market_researcher.tools.site_ingestor import SemanticSiteIngestor


class TestLiveFeatures(unittest.TestCase):
    def test_unreachable_site_does_not_invent_a_profile(self):
        with patch("requests.get", side_effect=requests.ConnectionError("DNS failed")):
            with self.assertRaisesRegex(ValueError, "Could not crawl"):
                SemanticSiteIngestor().ingest("missing.invalid")

    def test_http_error_does_not_extract_error_page(self):
        response = Mock()
        response.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        with patch("requests.get", return_value=response):
            with self.assertRaisesRegex(ValueError, "403 Forbidden"):
                SemanticSiteIngestor().ingest("https://example.com")

    def test_spa_bundle_extraction_runs_before_scripts_are_removed(self):
        response = Mock(url="https://example.com", text='<div id="root"></div><script src="/assets/index.js"></script>')
        ingestor = SemanticSiteIngestor()
        with patch("requests.get", return_value=response), patch.object(
            ingestor, "_extract_spa_bundle_text", return_value="Inventory forecasting and purchase order automation"
        ) as bundle, patch.object(ingestor, "_try_llm_extraction", return_value=None):
            profile = ingestor.ingest("example.com")
        bundle.assert_called_once()
        self.assertIn("Supply Chain", profile.industry_vertical)

    def test_empty_site_reports_no_readable_content(self):
        response = Mock(url="https://example.com", text="<html><title>App</title><body></body></html>")
        with patch("requests.get", return_value=response):
            with self.assertRaisesRegex(ValueError, "no readable content"):
                SemanticSiteIngestor().ingest("example.com")

    def test_business_homepages_are_eligible_search_results(self):
        tool = AgentReachTool()
        self.assertFalse(tool._is_junk_url("https://academy.example/"))
        self.assertFalse(tool._is_junk_url("https://academy.example/home"))
        self.assertTrue(tool._is_junk_url("https://academy.example/login"))

    def test_social_queries_keep_site_restrictions(self):
        tool = AgentReachTool()
        self.assertIn("site:linkedin.com/in", tool._clean_search_query('site:linkedin.com/in ("Founder" OR "CEO")', "linkedin"))
        self.assertIn("site:reddit.com", tool._clean_search_query("inventory tools", "reddit"))

    def test_search_preserves_role_alternatives_and_phrases(self):
        query = 'site:linkedin.com/in ("Founder" OR "CEO") "inventory management"'
        self.assertEqual(AgentReachTool()._clean_search_query(query, "linkedin"), query)

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed to validate dashboard JavaScript")
    def test_dashboard_javascript_parses(self):
        html = (Path(__file__).parents[1] / "web" / "dashboard.html").read_text(encoding="utf-8")
        for script in re.findall(r"<script\b[^>]*>(.*?)</script>", html, re.S):
            if script.strip():
                result = subprocess.run(["node", "--check"], input=script, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
