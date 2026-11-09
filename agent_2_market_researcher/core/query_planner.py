"""
Dynamic Query & Platform Mapping Engine for Agent 2: Target Market Researcher
scalyn.si (GrowWithAI Multi-Agent System)

Programmatically synthesizes high-intent search queries across 4 distinct types:
1. Decision-Maker / Prospect Search (Boolean for B2B/Research, Community demographic for B2C)
2. Pain-Point & Intent Queries (Intent triggers, workflow frustration)
3. Friction & Digital Gap Queries
4. Channel Mapping (LinkedIn, Reddit, X, Web)

Guardrail Enforced:
- If geographic_scope == GLOBAL: NEVER appends city or country names.
  Targets global research/business communities (e.g. site:reddit.com ("systematic review" OR "meta-analysis") ("Covidence" OR "Rayyan")).
- If geographic_scope == LOCAL_CITY: Only appends the specific target city from the brief.
"""

import re
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field

from .schemas import BusinessModelType, ClientBrief


class QueryType(str, Enum):
    DECISION_MAKER_SEARCH = "decision_maker_search"
    PAIN_POINT_INTENT = "pain_point_intent"
    FRICTION_DIGITAL_GAP = "friction_digital_gap"
    COMPETITOR_ALTERNATIVE = "competitor_alternative"


class TargetedQuery(BaseModel):
    query: str = Field(..., description="Exact formatted search query string or Boolean expression")
    query_type: QueryType = Field(..., description="Category of query")
    target_platform: str = Field(..., description="Optimized scout channel: 'linkedin', 'reddit', 'x', 'web'")
    intent_rationale: str = Field(..., description="Why this query and platform were selected")
    expected_signals: list[str] = Field(default_factory=list, description="Need signals targeted by this query")


class QueryPlanner:
    """
    Context-aware query generator and channel mapper.
    Translates any ClientBrief into platform-specific intelligence scouting queries.
    Strictly observes geographic scope: GLOBAL vs. LOCAL_CITY.
    """

    def plan_queries(
        self,
        brief: ClientBrief,
        model_type: BusinessModelType
    ) -> list[TargetedQuery]:
        """
        Generate a multi-platform query matrix covering all 4 query types
        with context-aware geographic constraints.
        """
        queries: list[TargetedQuery] = []
        niche = self._extract_core_niche(brief.industry)
        pain_term = self._extract_primary_pain(brief)

        # Detect geographic scope
        is_global = self._is_global_scope(brief)
        city_suffix = "" if is_global else f' "{self._extract_clean_city(brief.target_city_region)}"'

        # -------------------------------------------------------------
        # TYPE 1: Decision-Maker / Company Search
        # -------------------------------------------------------------
        if model_type in [BusinessModelType.B2B, BusinessModelType.FREELANCE_AGENCY, BusinessModelType.B2B2C]:
            # Determine persona roles
            if brief.target_buyer_personas:
                # Use explicit personas from brief
                first_few = [p.split('&')[0].strip() for p in brief.target_buyer_personas[:3]]
                roles_boolean = " OR ".join([f'"{r}"' for r in first_few])
            else:
                roles_boolean = '"Founder" OR "CEO" OR "Head of Operations" OR "Director" OR "Lead Researcher"'

            if is_global:
                # Global Boolean search (Zero city names)
                queries.append(
                    TargetedQuery(
                        query=f'site:linkedin.com/in ({roles_boolean}) "{niche}"',
                        query_type=QueryType.DECISION_MAKER_SEARCH,
                        target_platform="linkedin",
                        intent_rationale=f"Identify global {niche} decision makers, researchers, and operators on LinkedIn.",
                        expected_signals=["operational_bottleneck", "hiring_spike"],
                    )
                )
                queries.append(
                    TargetedQuery(
                        query=f'site:linkedin.com/company "{niche}"',
                        query_type=QueryType.DECISION_MAKER_SEARCH,
                        target_platform="linkedin",
                        intent_rationale=f"Discover organizations and specialized teams operating globally in {niche}.",
                        expected_signals=["hiring_spike", "operational_bottleneck"],
                    )
                )
            else:
                # Local / Regional Boolean search with specific target city
                queries.append(
                    TargetedQuery(
                        query=f'site:linkedin.com/in ({roles_boolean}) "{niche}"{city_suffix}',
                        query_type=QueryType.DECISION_MAKER_SEARCH,
                        target_platform="linkedin",
                        intent_rationale=f"Identify local operators and leaders in {niche} located in {brief.target_city_region}.",
                        expected_signals=["operational_bottleneck", "hiring_spike"],
                    )
                )
                queries.append(
                    TargetedQuery(
                        query=f'site:linkedin.com/company "{niche}"{city_suffix}',
                        query_type=QueryType.DECISION_MAKER_SEARCH,
                        target_platform="linkedin",
                        intent_rationale=f"Discover local businesses and centers in {brief.target_city_region}.",
                        expected_signals=["hiring_spike", "operational_bottleneck"],
                    )
                )
        else:
            # B2C / Community Demographic Queries
            if is_global:
                queries.append(
                    TargetedQuery(
                        query=f'site:reddit.com "{niche}" ("community" OR "recommendations" OR "experience")',
                        query_type=QueryType.DECISION_MAKER_SEARCH,
                        target_platform="reddit",
                        intent_rationale=f"Identify active global user discussions and consumer sentiments in {niche}.",
                        expected_signals=["community_inquiry", "customer_complaint"],
                    )
                )
            else:
                queries.append(
                    TargetedQuery(
                        query=f'site:reddit.com{city_suffix} "{niche}"',
                        query_type=QueryType.DECISION_MAKER_SEARCH,
                        target_platform="reddit",
                        intent_rationale=f"Identify local community threads and feedback in {brief.target_city_region}.",
                        expected_signals=["community_inquiry", "customer_complaint"],
                    )
                )

        # -------------------------------------------------------------
        # TYPE 2: Pain-Point & Intent Queries (Reddit / X)
        # -------------------------------------------------------------
        if is_global:
            # Global community complaints and discussions
            queries.append(
                TargetedQuery(
                    query=f'site:reddit.com "{niche}" ("{pain_term}" OR "struggling with" OR "manual")',
                    query_type=QueryType.PAIN_POINT_INTENT,
                    target_platform="reddit",
                    intent_rationale=f"Detect global practitioner pain points, bottlenecks, and complaints in {niche}.",
                    expected_signals=["operational_bottleneck", "customer_complaint"],
                )
            )
            queries.append(
                TargetedQuery(
                    query=f'site:reddit.com "{niche}" ("looking for recommendations" OR "best tool" OR "software")',
                    query_type=QueryType.PAIN_POINT_INTENT,
                    target_platform="reddit",
                    intent_rationale=f"Capture high-intent buyers actively seeking {niche} software recommendations.",
                    expected_signals=["community_inquiry"],
                )
            )
            queries.append(
                TargetedQuery(
                    query=f'"{niche}" ("need a better" OR "recommendation" OR "tool") software',
                    query_type=QueryType.PAIN_POINT_INTENT,
                    target_platform="x",
                    intent_rationale="Monitor real-time frustration posts and tool recommendations on X (Twitter).",
                    expected_signals=["community_inquiry", "customer_complaint"],
                )
            )
        else:
            queries.append(
                TargetedQuery(
                    query=f'"{pain_term}" OR "struggling with" "{niche}"{city_suffix}',
                    query_type=QueryType.PAIN_POINT_INTENT,
                    target_platform="reddit",
                    intent_rationale=f"Detect local customer pain points in {brief.target_city_region}.",
                    expected_signals=["operational_bottleneck", "customer_complaint"],
                )
            )
            queries.append(
                TargetedQuery(
                    query=f'"looking for recommendations" "{niche}"{city_suffix}',
                    query_type=QueryType.PAIN_POINT_INTENT,
                    target_platform="reddit",
                    intent_rationale=f"Detect local recommendation inquiries in {brief.target_city_region}.",
                    expected_signals=["community_inquiry"],
                )
            )

        # -------------------------------------------------------------
        # TYPE 3: Competitor Dissatisfaction & Alternatives
        # -------------------------------------------------------------
        if brief.key_competitors:
            top_comp = brief.key_competitors[0]
            other_comps = " OR ".join([f'"{c}"' for c in brief.key_competitors[:3]])

            # e.g. site:reddit.com ("systematic review" OR "meta-analysis") ("Covidence" OR "Rayyan")
            queries.append(
                TargetedQuery(
                    query=f'site:reddit.com ("{niche}" OR "{brief.startup_name}") ({other_comps})',
                    query_type=QueryType.COMPETITOR_ALTERNATIVE,
                    target_platform="reddit",
                    intent_rationale=f"Target global practitioner communities comparing {other_comps}.",
                    expected_signals=["customer_complaint", "community_inquiry"],
                )
            )
            queries.append(
                TargetedQuery(
                    query=f'site:reddit.com ("alternative to {top_comp}" OR "tired of {top_comp}" OR "{top_comp} too expensive" OR "issues with {top_comp}")',
                    query_type=QueryType.COMPETITOR_ALTERNATIVE,
                    target_platform="reddit",
                    intent_rationale=f"Intercept dissatisfied switchers looking for alternatives to {top_comp}.",
                    expected_signals=["customer_complaint", "operational_bottleneck"],
                )
            )

        # -------------------------------------------------------------
        # TYPE 4: Friction & Digital Gap Queries (Web)
        # -------------------------------------------------------------
        if is_global:
            queries.append(
                TargetedQuery(
                    query=f'"{niche}" software platform tools ("research" OR "clinical" OR "teams")',
                    query_type=QueryType.FRICTION_DIGITAL_GAP,
                    target_platform="web",
                    intent_rationale=f"Identify active teams, laboratories, or practitioners using legacy {niche} tools.",
                    expected_signals=["outdated_presence", "operational_bottleneck"],
                )
            )
        else:
            queries.append(
                TargetedQuery(
                    query=f'"{niche}" in{city_suffix} ("DM to order" OR "call to book" OR "whatsapp to order" OR "inbox for price")',
                    query_type=QueryType.FRICTION_DIGITAL_GAP,
                    target_platform="web",
                    intent_rationale="Find businesses with high-friction manual ordering workflows for digital auditing.",
                    expected_signals=["outdated_presence", "operational_bottleneck"],
                )
            )

        return queries

    def _is_global_scope(self, brief: ClientBrief) -> bool:
        """Determine whether the brief has a GLOBAL scope."""
        scope = getattr(brief, "geographic_scope", None)
        if scope and scope.upper() == "GLOBAL":
            return True
        if scope and scope.upper() in ["LOCAL_CITY", "REGIONAL"]:
            return False

        region_str = (brief.target_city_region or "").lower()
        if any(w in region_str for w in ["global", "remote", "worldwide", "international", "academic & healthcare"]):
            return True
        if any(w in region_str for w in ["karachi", "lahore", "islamabad", "rawalpindi", "sindh", "pakistan"]):
            return False
        return True

    def _extract_core_niche(self, industry_raw: str) -> str:
        """Sanitize and extract the core industry keyword."""
        # Check for specific high-value phrases
        raw_lower = industry_raw.lower()
        if "meta-analysis" in raw_lower or "systematic review" in raw_lower:
            return "meta-analysis"
        if "supply chain" in raw_lower or "inventory" in raw_lower:
            return "inventory management"
        if "dental" in raw_lower or "clinic" in raw_lower:
            return "dental clinic"
        if "exam" in raw_lower or "tuition" in raw_lower:
            return "exam prep"
        if "bakery" in raw_lower or "sourdough" in raw_lower:
            return "artisan bakery"

        parts = re.split(r"[/,&]", industry_raw)
        primary = parts[0].strip()
        cleaned = re.sub(r"\b(b2b|b2c|d2c|boutique|specialty|custom)\b", "", primary, flags=re.IGNORECASE).strip()
        return cleaned if cleaned else industry_raw.strip()

    def _extract_clean_city(self, region_raw: str) -> str:
        """Extract clean city name for local targeting."""
        match = re.match(r"^([^,(]+)", region_raw)
        if match:
            clean = match.group(1).strip()
            # If region is Karachi & Sindh, simplify to Karachi
            if "&" in clean:
                clean = clean.split("&")[0].strip()
            return clean
        return region_raw.strip()

    def _extract_primary_pain(self, brief: ClientBrief) -> str:
        """Infer high-relevance pain phrase from upstream brief notes or description."""
        combined = f"{brief.notes_from_agent_1 or ''} {brief.unique_value_proposition} {brief.product_service_description}".lower()
        if any(w in combined for w in ["meta-analysis", "prisma", "screening", "data extraction", "covidence"]):
            return "manual data extraction systematic review"
        if any(w in combined for w in ["spreadsheet", "excel", "inventory", "stockout"]):
            return "manual spreadsheets inventory"
        if any(w in combined for w in ["inquiry", "patient", "receptionist", "phone call"]):
            return "missed patient inquiries"
        if any(w in combined for w in ["overcrowded", "rote", "homework", "exam"]):
            return "manual paper setting mock exams"
        if any(w in combined for w in ["preservative", "fresh", "sourdough", "ferment"]):
            return "fresh artisan sourdough delivery"
        return "manual repetitive workflow"
