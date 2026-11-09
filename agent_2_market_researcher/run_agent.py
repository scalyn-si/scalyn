"""
Runner Script for Agent 2: Target Market Researcher
scalyn.si (GrowWithAI Multi-Agent Collective)

Executes dynamic market scouting across sample briefs or live Agent 1 handoff files:
1. Ingests raw JSON briefs from Agent 1 (Business Analyst).
2. Generates master TargetMarketDossier JSON payload.
3. Automatically exports lead_tracker_<startup>.csv for Agent 5 (Sales Lead).
4. Automatically exports marketing_brief_<startup>.json for Agent 3 (Marketing Agent).
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_2_market_researcher.config.settings import settings
from agent_2_market_researcher.core.schemas import (
    BusinessModelType,
    ClientBrief,
)
from agent_2_market_researcher.core.researcher_agent import TargetMarketResearcherAgent
from agent_2_market_researcher.core.exporters import (
    _get_clean_slug,
    export_sales_lead_tracker_csv,
    export_marketing_handoff_json,
)
from agent_2_market_researcher.tools.agent_reach_tool import AgentReachTool

# Predefined startup briefs illustrating universal dynamic research capability
SAMPLE_BRIEFS: dict[str, ClientBrief] = {
    "b2b_saas": ClientBrief(
        startup_name="OpsFlow AI",
        industry="B2B SaaS / Supply Chain Ops",
        business_model=BusinessModelType.B2B,
        product_service_description=(
            "AI-native inventory forecasting and automated purchase order dispatch system for mid-market e-commerce merchants."
        ),
        unique_value_proposition=(
            "Predicts stockouts 2 weeks ahead with 94% accuracy and generates automated vendor POs without human intervention."
        ),
        target_city_region="United States / Remote E-commerce Brands",
        primary_goal="Acquire 15 paying B2B merchant pilots at $299/mo",
        budget="$2,500/month initial acquisition budget",
        existing_channels=["LinkedIn Founder Posts", "Cold Email"],
        pricing_model="$299/month base + usage tier",
        key_competitors=["InventoryPlanner", "Cin7", "Manual Excel Sheets"],
        notes_from_agent_1=(
            "Merchant founders spend 12+ hours weekly reconciling spreadsheets; stockouts cause average 18% quarterly revenue leak."
        ),
    ),
    "tuition_academy": ClientBrief(
        startup_name="Qraft Education (Sindh Exam Prep)",
        industry="Tuition Academy / Supplementary Education",
        business_model=BusinessModelType.SERVICE_LOCAL,
        product_service_description=(
            "AI-powered exam prep, paper generator, and hybrid O/A Level tuition coaching for Sindh and Cambridge board students."
        ),
        unique_value_proposition=(
            "Instant past paper generation, exam diagnostic mock analytics, and personalized mentoring for coaching centres and students across Karachi and Sindh."
        ),
        target_city_region="Karachi & Sindh, Pakistan",
        primary_goal="Partner with 50 leading coaching centers and tuition academies across Karachi",
        budget="PKR 80,000 / month hyper-local marketing budget",
        existing_channels=["WhatsApp Groups", "Local Word of Mouth"],
        pricing_model="PKR 12,000 / subject / month",
        key_competitors=["Anees Hussain", "Adamjee Coaching", "KIPS Karachi", "Practical Centre"],
        notes_from_agent_1=(
            "Coaching centres and tuition academies in Sindh struggle with manual paper setting, overcrowded batches, and lack of automated student performance analytics."
        ),
    ),
    "digital_agency": ClientBrief(
        startup_name="Vanguard Automations",
        industry="Boutique Digital & AI Automation Agency",
        business_model=BusinessModelType.FREELANCE_AGENCY,
        product_service_description=(
            "Custom workflow automation, CRM pipeline setup, and AI customer support chatbots for dental clinics and legal firms."
        ),
        unique_value_proposition=(
            "Guaranteed 3x faster patient/client inquiry response time and 30 hours of monthly administrative overhead saved in 14 days."
        ),
        target_city_region="UK & UAE Regional Private Clinics",
        primary_goal="Sign 4 recurring retainer clients at £1,500/month",
        budget="$1,000/month targeted outreach budget",
        existing_channels=["Cold LinkedIn Messages", "Email"],
        pricing_model="£2,000 setup + £750/month maintenance",
        key_competitors=["Generic Local Marketing Agencies", "Freelance Upwork Contractors"],
        notes_from_agent_1=(
            "Clinics lose up to 40% of patient inquiries because receptionists cannot answer phone calls and WhatsApp messages simultaneously."
        ),
    ),
    "home_bakery": ClientBrief(
        startup_name="Crumb & Crust Artisanal",
        industry="Home Bakery & Specialty Confectionery",
        business_model=BusinessModelType.D2C,
        product_service_description=(
            "Artisanal slow-fermented sourdough breads, organic babkas, and customized celebration pastries delivered fresh."
        ),
        unique_value_proposition=(
            "100% organic locally sourced ingredients, 36-hour wild yeast fermentation, zero chemical preservatives, fresh morning delivery."
        ),
        target_city_region="Karachi (Clifton & DHA)",
        primary_goal="Build a recurring weekly bread subscription base of 120 households",
        budget="PKR 45,000 / month Instagram & tasting booth budget",
        existing_channels=["Instagram Page", "WhatsApp Catalog"],
        pricing_model="PKR 800 - 1,500 per loaf / PKR 4,000 celebration cakes",
        key_competitors=["Auntie Anne's Commercial Bakeries", "Local Supermarkets", "Espresso / Del Frio"],
        notes_from_agent_1=(
            "Commercial bread has preservatives causing gluten sensitivity; customers want wholesome artisan sourdough with simple online ordering."
        ),
    ),
}


def load_agent1_brief(file_path: str) -> ClientBrief:
    """
    Ingest raw JSON diagnosis or onboarding brief from Agent 1 (Business Analyst).
    Maps flexible structures into a validated ClientBrief contract.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Agent 1 input file not found: {file_path}")

    with open(path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # Support modular structures from Agent 1 (e.g. client_info + business_diagnosis)
    data = {}
    if isinstance(raw_data, dict):
        for sub_key in ["client_info", "client_profile", "business_diagnosis", "diagnosis", "client_brief", "brief"]:
            if isinstance(raw_data.get(sub_key), dict):
                data.update(raw_data[sub_key])
        for k, v in raw_data.items():
            if not isinstance(v, dict):
                data[k] = v
    if not data:
        data = raw_data

    startup_name = data.get("startup_name") or data.get("business_name") or data.get("client_name") or "Startup Client"
    industry = data.get("industry") or data.get("niche") or data.get("sector") or "General Business"
    desc = (
        data.get("product_service_description")
        or data.get("description")
        or data.get("offering")
        or data.get("value_prop")
        or "Digital and operational business services."
    )
    uvp = (
        data.get("unique_value_proposition")
        or data.get("uvp")
        or data.get("value_proposition")
        or "Delivers 3x faster execution with modern AI-enabled systems."
    )
    region = data.get("target_city_region") or data.get("target_region") or data.get("location") or "Global Remote"
    goal = data.get("primary_goal") or data.get("growth_goal") or data.get("objective") or "Acquire first 25 qualified customers"
    budget = data.get("budget") or "Bootstrapped / Low Budget"
    channels = data.get("existing_channels") or []
    pricing = data.get("pricing_model") or data.get("pricing")
    competitors = data.get("key_competitors") or data.get("competitors") or []
    notes = data.get("notes_from_agent_1") or data.get("operational_bottlenecks") or data.get("diagnosis")

    # Ingest business model if provided
    bm_val = data.get("business_model")
    business_model = None
    if bm_val:
        try:
            business_model = BusinessModelType(bm_val)
        except ValueError:
            business_model = None

    return ClientBrief(
        startup_name=startup_name,
        industry=industry,
        business_model=business_model,
        product_service_description=desc,
        unique_value_proposition=uvp,
        target_city_region=region,
        primary_goal=goal,
        budget=budget,
        existing_channels=channels,
        pricing_model=pricing,
        key_competitors=competitors,
        notes_from_agent_1=notes,
    )


def print_dossier_summary(dossier):
    """Render a clean terminal executive report of the market research dossier."""
    brief = dossier.client_brief
    slug = _get_clean_slug(brief.startup_name)

    print("\n" + "=" * 80)
    print(f"🎯 TARGET MARKET RESEARCH DOSSIER [{dossier.dossier_id}]")
    print(f"Startup: {brief.startup_name} | Industry: {brief.industry}")
    print(f"Classified Business Model: {dossier.business_model_classification}")
    print(f"Target Region: {brief.target_city_region}")
    print("=" * 80)

    print("\n📌 1. IDEAL CUSTOMER PROFILE (ICP)")
    print(f"   Target Category: {dossier.ideal_customer_profile.target_category}")
    print(f"   Key Pain Points:")
    for p in dossier.ideal_customer_profile.key_pain_points:
        print(f"     • {p}")
    print(f"   Urgent Buyer Triggers:")
    for t in dossier.ideal_customer_profile.buyer_triggers:
        print(f"     ⚡ {t}")

    print("\n👤 2. BUYER PERSONAS")
    for persona in dossier.buyer_personas:
        print(f"   [{persona.persona_name}] - {persona.title_or_role}")
        print(f"     Context: {persona.context_and_background}")
        print(f"     Core Frustrations: {', '.join(persona.core_frustrations[:2])}")
        print(f"     Preferred Channels: {', '.join(persona.preferred_channels)}")
        print(f"     Buying Motivation: {persona.purchasing_motivation}")

    print("\n📊 3. RANKED MARKET SEGMENTS")
    for seg in dossier.ranked_market_segments:
        print(f"   Rank #{seg.rank}: {seg.segment_name} ({seg.priority_tier})")
        print(f"     Readiness: {seg.conversion_readiness} | Rationale: {seg.strategic_rationale[:90]}...")

    if dossier.generated_query_plan:
        print(f"\n🧠 DYNAMIC QUERY MATRIX ({len(dossier.generated_query_plan)} Queries Generated by QueryPlanner)")
        for q_item in dossier.generated_query_plan[:5]:
            print(f"   [{q_item.get('target_platform', '').upper()}] ({q_item.get('query_type', '')}):")
            print(f"     Query: {q_item.get('query', '')}")
            print(f"     Rationale: {q_item.get('intent_rationale', '')}")

    print(f"\n🔍 4. SCOUTED PROSPECTS WITH NEED SIGNALS ({len(dossier.discovered_prospects)} Verified)")
    for i, prospect in enumerate(dossier.discovered_prospects[:4], 1):
        print(f"\n   Lead #{i}: {prospect.name_or_handle} [{prospect.platform_source.upper()}] (Match Score: {prospect.match_score}/10)")
        print(f"     Verified URL: {prospect.verified_url}")
        print(f"     Observed Signals: {[s.description for s in prospect.observed_need_signals]}")
        print(f"     Tailored Hook for Agent 5 (Sales): \"{prospect.personalized_hook_for_sales}\"")

    print("\n❓ 5. MOM-TEST CUSTOMER DISCOVERY VALIDATION QUESTIONS")
    for idx, q in enumerate(dossier.interview_validation_questions, 1):
        print(f"   {idx}. {q}")

    # Paths for all generated handoffs
    master_dossier_file = settings.dossier_output_dir / f"{dossier.dossier_id}_{slug}.json"
    sales_lead_file = settings.dossier_output_dir / f"lead_tracker_{slug}.csv"
    marketing_brief_file = settings.dossier_output_dir / f"marketing_brief_{slug}.json"
    master_excel_file = settings.dossier_output_dir / "master_lead_database.xlsx"

    print("\n📦 MULTI-AGENT HANDOFF ARTIFACTS GENERATED:")
    print(f"   • Master Market Dossier (Agent 2 Core):   {master_dossier_file}")
    print(f"   • Lead Tracker CRM CSV (Agent 5 Sales):    {sales_lead_file}")
    print(f"   • Strategic Brief (Agent 3 Marketing):     {marketing_brief_file}")
    print(f"   • Master Lead Database (Persistent Excel): {master_excel_file}")

    print("\n" + "=" * 80)
    print("✅ Research execution complete. Multi-agent handoff bridge updated.\n")


def main():
    parser = argparse.ArgumentParser(description="Run scalyn.si Agent 2: Target Market Researcher")
    parser.add_argument(
        "--brief",
        choices=list(SAMPLE_BRIEFS.keys()) + ["all"],
        default="b2b_saas",
        help="Choose a sample startup brief to scout (default: b2b_saas)",
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default=None,
        help="Path to raw JSON brief ingested from Agent 1 (Business Analyst)",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="Website URL of your startup (e.g. https://my-startup.com) to autonomously explore and scout",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Run agent-reach environment and tool diagnostics",
    )
    args = parser.parse_args()

    agent = TargetMarketResearcherAgent()

    if args.doctor:
        print("\n🩺 Running Agent-Reach Environment Diagnostics...")
        reach = AgentReachTool()
        doctor_report = reach.run_doctor()
        print(json.dumps(doctor_report, indent=2))
        return

    if args.input_file:
        print(f"\n>>> INGESTING UPSTREAM BRIEF FROM AGENT 1: '{args.input_file}' <<<")
        brief = load_agent1_brief(args.input_file)
        dossier = agent.run(brief)
        print_dossier_summary(dossier)
        return

    if args.url:
        print(f"\n>>> AUTONOMOUSLY EXPLORING STARTUP WEBSITE: '{args.url}' <<<")
        from agent_2_market_researcher.tools.site_ingestor import SemanticSiteIngestor
        ingestor = SemanticSiteIngestor()
        brief = ingestor.convert_to_client_brief(args.url)
        print(f"   • Extracted Startup: {brief.startup_name}")
        print(f"   • Detected Vertical:  {brief.industry} ({brief.business_model.value})")
        print(f"   • Geographic Scope:   {brief.geographic_scope}")
        if brief.target_buyer_personas:
            print(f"   • Target Personas:    {', '.join(brief.target_buyer_personas[:3])}")
        if brief.key_competitors:
            print(f"   • Known Competitors:  {', '.join(brief.key_competitors[:4])}")
        print(f"   • Value Proposition:  {brief.unique_value_proposition}")
        print(f"   • Target Region:      {brief.target_city_region}\n")
        dossier = agent.run(brief)
        print_dossier_summary(dossier)
        return

    if args.brief == "all":
        for key, brief in SAMPLE_BRIEFS.items():
            print(f"\n>>> EXECUTING BRIEF: {key.upper()} <<<")
            dossier = agent.run(brief)
            print_dossier_summary(dossier)
    else:
        brief = SAMPLE_BRIEFS[args.brief]
        dossier = agent.run(brief)
        print_dossier_summary(dossier)


if __name__ == "__main__":
    main()
