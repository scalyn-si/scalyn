"""
Unit & Integration Tests for Agent 2: Target Market Researcher
scalyn.si (GrowWithAI Multi-Agent System)
"""

import json
import unittest
from datetime import datetime

from agent_2_market_researcher.core.schemas import (
    BusinessModelType,
    ClientBrief,
    NeedSignal,
    SignalSeverity,
    TargetMarketDossier,
)
from agent_2_market_researcher.core.query_planner import QueryPlanner, QueryType
from agent_2_market_researcher.tools.signal_detector import SignalDetector
from agent_2_market_researcher.tools.agent_reach_tool import AgentReachTool
from agent_2_market_researcher.core.researcher_agent import TargetMarketResearcherAgent


class TestMarketResearcher(unittest.TestCase):
    def setUp(self):
        self.detector = SignalDetector()
        self.reach_tool = AgentReachTool()
        self.planner = QueryPlanner()
        self.agent = TargetMarketResearcherAgent(
            reach_tool=self.reach_tool,
            signal_detector=self.detector,
            query_planner=self.planner,
        )

    def test_client_brief_validation(self):
        """Test ClientBrief instantiation and defaults."""
        brief = ClientBrief(
            startup_name="Apex Tuition Hub",
            industry="Tuition Academy",
            product_service_description="Hybrid STEM coaching for high schoolers with AI-driven personalized homework grading.",
            unique_value_proposition="Personalized weekly mastery reports and 1-on-1 doubt clearing under 15 minutes.",
            target_city_region="Lahore, Pakistan",
            primary_goal="Acquire 100 new active students for upcoming academic session",
        )
        self.assertEqual(brief.startup_name, "Apex Tuition Hub")
        self.assertIn("Lahore", brief.target_city_region)
        self.assertEqual(brief.budget, "Bootstrapped / Low Budget")

    def test_signal_detector_operational_bottleneck(self):
        """Verify detection of manual operational bottlenecks."""
        snippet = "We are wasting hours every day on spreadsheet data entry and paperwork. It's a huge bottleneck."
        signals = self.detector.audit_text_snippet(snippet)
        self.assertTrue(len(signals) > 0)
        ops_signal = next((s for s in signals if s.signal_type == "operational_bottleneck"), None)
        self.assertIsNotNone(ops_signal)
        self.assertIn("manual process friction", ops_signal.description)

    def test_signal_detector_complaint(self):
        """Verify detection of customer dissatisfaction with competitors."""
        snippet = "Switched to this service but their support was unresponsive and terrible support. Frustrated!"
        signals = self.detector.audit_text_snippet(snippet)
        self.assertTrue(len(signals) > 0)
        complaint = next((s for s in signals if s.signal_type == "customer_complaint"), None)
        self.assertIsNotNone(complaint)
        self.assertEqual(complaint.severity, SignalSeverity.HIGH)

    def test_signal_detector_inquiry(self):
        """Verify detection of high-intent buying inquiries."""
        snippet = "Can anyone recommend a reliable tuition center or tutor in Gulberg for O-Levels?"
        signals = self.detector.audit_text_snippet(snippet)
        inquiry = next((s for s in signals if s.signal_type == "community_inquiry"), None)
        self.assertIsNotNone(inquiry)
        self.assertEqual(inquiry.severity, SignalSeverity.CRITICAL)

    def test_5_universal_friction_signals(self):
        """
        Verify all 5 universal friction signals:
        1. Technical Gaps (No SSL, missing mobile viewport)
        2. Manual Workflow Bottlenecks (DM for price, screenshot of payment)
        3. Stale Presence (Copyright < 2024)
        4. Broken / Missing Web Links (HTTP 404 / site offline)
        5. Contact Friction (No direct email/WhatsApp links)
        """
        # Signal 1, 2, 3, 5: Live page with multiple friction points
        url = "http://clinic-example.co.uk"  # Non-SSL (Signal 1)
        mock_page = {
            "is_live": True,
            "has_viewport": False,            # Missing viewport (Signal 1)
            "has_direct_email": False,        # Missing direct email (Signal 5)
            "has_direct_whatsapp": False,     # Missing WhatsApp (Signal 5)
            "has_direct_tel": False,          # Missing phone link (Signal 5)
            "text_content": (
                "Welcome to our private clinic. "
                "Please DM for price or send WhatsApp screenshot of payment to confirm booking. " # Signal 2
                "© 2021 All Rights Reserved."                                                     # Signal 3
            ),
        }
        status, signals = self.detector.audit_digital_presence(url, mock_page)

        # Check Signal 1: Technical Gaps
        self.assertIn("no_ssl", status)
        self.assertIn("no_mobile_viewport", status)
        tech_signals = [s for s in signals if s.signal_type == "technical_gap"]
        self.assertGreaterEqual(len(tech_signals), 2)

        # Check Signal 2: Manual Workflow
        self.assertIn("high_friction_booking", status)
        manual_signals = [s for s in signals if s.signal_type == "operational_bottleneck"]
        self.assertGreaterEqual(len(manual_signals), 1)

        # Check Signal 3: Stale Presence
        self.assertIn("outdated_content", status)
        stale_signals = [s for s in signals if s.signal_type == "outdated_presence"]
        self.assertGreaterEqual(len(stale_signals), 1)

        # Check Signal 5: Contact Friction
        self.assertIn("high_contact_friction", status)
        contact_signals = [s for s in signals if s.signal_type == "contact_friction"]
        self.assertGreaterEqual(len(contact_signals), 1)

        # Check Signal 4: Broken / Offline Link
        broken_url = "https://dead-link-store.com"
        broken_page = {"is_live": False, "status_code": 404, "error": "Not Found"}
        broken_status, broken_signals = self.detector.audit_digital_presence(broken_url, broken_page)
        self.assertEqual(broken_status, "no_active_digital_home")
        self.assertTrue(any(s.signal_type == "broken_website" for s in broken_signals))

    def test_dynamic_query_planner_b2b(self):
        """Verify dynamic QueryPlanner synthesizes all 4 query types for B2B."""
        brief = ClientBrief(
            startup_name="OpsFlow AI",
            industry="B2B SaaS / Supply Chain Ops",
            business_model=BusinessModelType.B2B,
            product_service_description="AI-native inventory forecasting and purchase order automation.",
            unique_value_proposition="Eliminates stockouts and manual spreadsheet reconciliation.",
            target_city_region="United States / Remote E-commerce",
            primary_goal="Acquire 15 paying B2B merchant pilots",
            key_competitors=["Cin7", "InventoryPlanner"],
            notes_from_agent_1="Founders waste hours manually updating inventory sheets.",
        )
        queries = self.planner.plan_queries(brief, BusinessModelType.B2B)
        self.assertGreaterEqual(len(queries), 5)

        # 1. Decision-Maker / Company Search (LinkedIn Boolean)
        dm_queries = [q for q in queries if q.query_type == QueryType.DECISION_MAKER_SEARCH]
        self.assertGreaterEqual(len(dm_queries), 2)
        self.assertTrue(any("site:linkedin.com/in" in q.query for q in dm_queries))
        self.assertTrue(any("site:linkedin.com/company" in q.query for q in dm_queries))

        # 2. Pain-Point & Intent Queries (Reddit / X)
        intent_queries = [q for q in queries if q.query_type == QueryType.PAIN_POINT_INTENT]
        self.assertGreaterEqual(len(intent_queries), 2)
        self.assertTrue(any(q.target_platform in ["reddit", "x"] for q in intent_queries))

        # 3. Competitor Alternative Queries
        comp_queries = [q for q in queries if q.query_type == QueryType.COMPETITOR_ALTERNATIVE]
        self.assertGreaterEqual(len(comp_queries), 1)
        self.assertTrue(any("Cin7" in q.query for q in comp_queries))

        # 4. Friction & Digital Gap Queries (Web)
        gap_queries = [q for q in queries if q.query_type == QueryType.FRICTION_DIGITAL_GAP]
        self.assertGreaterEqual(len(gap_queries), 1)
        self.assertTrue(any("DM to order" in q.query or "call to book" in q.query for q in gap_queries))

    def test_dynamic_query_planner_b2c(self):
        """Verify dynamic QueryPlanner synthesizes demographic and community queries for B2C."""
        brief = ClientBrief(
            startup_name="Apex Academy",
            industry="Tuition Academy",
            business_model=BusinessModelType.SERVICE_LOCAL,
            product_service_description="O/A-Levels coaching center.",
            unique_value_proposition="Small cohorts of max 8 students.",
            target_city_region="Lahore (DHA, Gulberg)",
            primary_goal="Enroll 50 students",
        )
        queries = self.planner.plan_queries(brief, BusinessModelType.SERVICE_LOCAL)
        self.assertGreaterEqual(len(queries), 4)
        dm_queries = [q for q in queries if q.query_type == QueryType.DECISION_MAKER_SEARCH]
        self.assertTrue(any("parents" in q.query or "residents" in q.query for q in dm_queries))

    def test_match_score_calculation(self):
        """Verify match score scaling between 1 and 10."""
        crit_signal = NeedSignal(
            signal_type="community_inquiry",
            description="Actively seeking solution",
            severity=SignalSeverity.CRITICAL,
        )
        score = self.detector.calculate_match_score([crit_signal], has_verified_url=True)
        self.assertGreaterEqual(score, 7)
        self.assertLessEqual(score, 10)

    def test_personalized_sales_hook_generation(self):
        """Ensure sales hooks are tailored and non-spammy."""
        signal = NeedSignal(
            signal_type="contact_friction",
            description="No direct phone or WhatsApp on landing page",
            source_snippet="inquiry form only",
            severity=SignalSeverity.HIGH,
        )
        hook = self.detector.generate_personalized_hook(
            prospect_name="Dr. Arshad",
            signals=[signal],
            client_name="Vanguard Automations",
            unique_value_prop="automated 24/7 patient inquiry capture",
        )
        self.assertIn("Dr. Arshad", hook)
        self.assertIn("Vanguard Automations", hook)
        self.assertIn("friction", hook.lower())

    def test_end_to_end_researcher_run(self):
        """Execute complete market research run on sample brief with QueryPlanner integration."""
        brief = ClientBrief(
            startup_name="WorkPulse B2B",
            industry="B2B SaaS / Workforce Ops",
            business_model=BusinessModelType.B2B,
            product_service_description="AI-driven shift management and payroll compliance software for mid-sized logistics companies.",
            unique_value_proposition="Reduces payroll reconciliation time from 3 days to 15 minutes with zero error rate.",
            target_city_region="National / North America Remote",
            primary_goal="Close 10 enterprise pilot accounts within 90 days",
            budget="\$5,000/month growth budget",
            key_competitors=["Deel", "Rippling", "Manual Excel"],
        )

        dossier = self.agent.run(brief)

        self.assertIsInstance(dossier, TargetMarketDossier)
        self.assertTrue(dossier.dossier_id.startswith("DOSSIER-"))
        self.assertEqual(dossier.business_model_classification, "B2B")
        self.assertGreaterEqual(len(dossier.buyer_personas), 2)
        self.assertGreaterEqual(len(dossier.ranked_market_segments), 1)
        self.assertGreaterEqual(len(dossier.interview_validation_questions), 5)
        self.assertGreater(len(dossier.discovered_prospects), 0)
        self.assertGreater(len(dossier.recommended_channels_for_agent_3), 0)
        self.assertGreater(len(dossier.sales_outreach_recommendations_for_agent_5), 0)
        self.assertGreater(len(dossier.generated_query_plan), 0)

        # JSON serialization validation
        json_output = dossier.model_dump_json()
        parsed = json.loads(json_output)
        self.assertEqual(parsed["dossier_id"], dossier.dossier_id)
        self.assertIn("generated_query_plan", parsed)

        # Exporters verification
        from pathlib import Path
        csv_file = Path(self.agent.output_dir) / "lead_tracker_workpulse_b2b.csv"
        mktg_file = Path(self.agent.output_dir) / "marketing_brief_workpulse_b2b.json"
        self.assertTrue(csv_file.exists(), "lead_tracker CSV was not generated")
        self.assertTrue(mktg_file.exists(), "marketing_brief JSON was not generated")
        self.assertGreater(csv_file.stat().st_size, 100)
        self.assertGreater(mktg_file.stat().st_size, 100)


if __name__ == "__main__":
    unittest.main()
