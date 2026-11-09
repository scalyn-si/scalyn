"""
Handoff Exporters for Agent 2: Target Market Researcher
scalyn.si (GrowWithAI Multi-Agent Collective)

Exports research intelligence into specialized formats for downstream teammates:
1. Agent 5 (Sales Lead): lead_tracker_<startup>.csv (formatted CRM / Google Sheets lead list)
2. Agent 3 (Marketing Agent): marketing_brief_<startup>.json (strategic positioning & campaign brief)
"""

import csv
import json
from pathlib import Path
from typing import Optional

from ..config.settings import settings
from .schemas import TargetMarketDossier


def _get_clean_slug(startup_name: str) -> str:
    """Generate a clean filesystem slug from startup name."""
    clean = "".join(c if c.isalnum() else "_" for c in startup_name.lower())
    return "_".join(filter(None, clean.split("_")))


def _infer_outreach_channel(platform_source: str, digital_status: Optional[str] = None) -> str:
    """Infer the optimal sales outreach mechanism based on platform source and audit."""
    src = platform_source.lower()
    if src == "linkedin":
        return "LinkedIn InMail / Direct Message"
    elif src == "reddit":
        return "Reddit DM (Consultative / Value-First)"
    elif src == "x":
        return "X (Twitter) DM / Public Mention"
    elif src == "web":
        if digital_status and "high_contact_friction" in digital_status:
            return "Website Inquiry Form / Founder Email"
        return "Cold Email / WhatsApp Direct"
    return "Direct Social Outreach"


def export_sales_lead_tracker_csv(
    dossier: TargetMarketDossier,
    output_path: Optional[str] = None
) -> str:
    """
    Export all discovered prospects into a structured CSV for Agent 5 (Sales Lead).
    Ready for immediate import into Google Sheets, Airtable, or CRM.
    """
    slug = _get_clean_slug(dossier.client_brief.startup_name)
    target_file = Path(output_path) if output_path else settings.dossier_output_dir / f"lead_tracker_{slug}.csv"
    target_file.parent.mkdir(parents=True, exist_ok=True)

    headers = [
        "Lead ID",
        "Prospect / Organization",
        "Target Role",
        "Platform Source",
        "Verified URL",
        "Match Score (1-10)",
        "Primary Need Signals",
        "Personalized Sales Hook",
        "Outreach Channel",
        "Outreach Status",
        "Next Follow-Up Date",
        "Discovery Date",
    ]

    rows = []
    for i, prospect in enumerate(dossier.discovered_prospects, 1):
        lead_id = f"LEAD-{i:03d}"
        
        # Semicolon-separated list of need signal descriptions
        signals_str = "; ".join(s.description for s in prospect.observed_need_signals)
        
        # Target role or inferred role
        role = prospect.role_or_title or "Decision Maker"
        
        # Prospect display name / org
        prospect_display = f"{prospect.name_or_handle}"
        if prospect.organization and prospect.organization != prospect.name_or_handle:
            prospect_display += f" ({prospect.organization})"

        channel = _infer_outreach_channel(prospect.platform_source, prospect.digital_presence_status)
        discovery_date = prospect.scouted_at.strftime("%Y-%m-%d %H:%M:%S")

        rows.append([
            lead_id,
            prospect_display,
            role,
            prospect.platform_source.upper(),
            prospect.verified_url,
            prospect.match_score,
            signals_str,
            prospect.personalized_hook_for_sales,
            channel,
            "Not Contacted",  # Default status for Agent 5
            "",               # Blank for Sales Lead to populate
            discovery_date,
        ])

    with open(target_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    return str(target_file)


def export_marketing_handoff_json(
    dossier: TargetMarketDossier,
    output_path: Optional[str] = None
) -> str:
    """
    Extract and package the core strategic intelligence required by Agent 3 (Marketing Agent).
    Outputs a clean, rich marketing_brief_<startup>.json.
    """
    slug = _get_clean_slug(dossier.client_brief.startup_name)
    target_file = Path(output_path) if output_path else settings.dossier_output_dir / f"marketing_brief_{slug}.json"
    target_file.parent.mkdir(parents=True, exist_ok=True)

    brief = dossier.client_brief
    icp = dossier.ideal_customer_profile

    marketing_payload = {
        "handoff_metadata": {
            "source_agent": "Agent 2: Target Market Researcher",
            "recipient_agent": "Agent 3: Marketing Agent",
            "dossier_id": dossier.dossier_id,
            "generated_at": dossier.generated_at.isoformat(),
            "startup_name": brief.startup_name,
        },
        "target_business_model": dossier.business_model_classification,
        "primary_value_proposition": brief.unique_value_proposition,
        "target_geography": brief.target_city_region,
        "primary_growth_goal": brief.primary_goal,
        "marketing_budget_constraints": brief.budget,
        "ideal_customer_profile_summary": {
            "category": icp.target_category,
            "geographic_focus": icp.geographic_focus,
            "firmographic_or_demographic": icp.firmographic_or_demographic,
            "decision_maker_profiles": icp.decision_maker_profiles,
            "anti_persona_signals": icp.anti_persona_signals,
        },
        "detailed_buyer_personas": [
            {
                "persona_name": p.persona_name,
                "title_or_role": p.title_or_role,
                "context": p.context_and_background,
                "core_frustrations": p.core_frustrations,
                "aspirations_and_goals": p.aspirations_and_goals,
                "preferred_channels": p.preferred_channels,
                "common_objections": p.common_objections,
                "purchasing_motivation": p.purchasing_motivation,
            }
            for p in dossier.buyer_personas
        ],
        "ranked_market_segments": [
            {
                "rank": s.rank,
                "segment_name": s.segment_name,
                "priority_tier": s.priority_tier,
                "estimated_opportunity": s.estimated_opportunity_size,
                "conversion_readiness": s.conversion_readiness,
                "strategic_rationale": s.strategic_rationale,
            }
            for s in dossier.ranked_market_segments
        ],
        "top_buyer_pain_points_and_triggers": {
            "core_pain_points": icp.key_pain_points,
            "urgent_buyer_triggers": icp.buyer_triggers,
        },
        "recommended_marketing_channels": dossier.recommended_channels_for_agent_3,
        "competitor_gaps_to_exploit": [
            {
                "competitor": c.competitor_name,
                "perceived_strengths": c.perceived_strengths,
                "vulnerabilities": c.vulnerabilities_and_complaints,
                "scalyn_differentiation_angle": c.scalyn_differentiation_angle,
            }
            for c in dossier.competitor_landscape
        ],
        "interview_validation_questions_for_testing": dossier.interview_validation_questions,
    }

    with open(target_file, mode="w", encoding="utf-8") as f:
        json.dump(marketing_payload, f, indent=2, ensure_ascii=False)

    return str(target_file)
