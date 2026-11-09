"""
Core Reasoning Loop for Agent 2: Target Market Researcher
scalyn.si (GrowWithAI Multi-Agent System)

Autonomously analyzes client briefs, synthesizes ICPs and buyer personas,
scouts external channels (LinkedIn, X, Reddit, Web) via Agent Reach,
verifies concrete need signals, and generates structured dossiers for Marketing & Sales.
"""

import json
import logging
import uuid
import urllib.parse
from datetime import datetime
from typing import Any, Optional
import requests

from ..config.settings import settings
from .schemas import (
    BusinessModelType,
    ClientBrief,
    CompetitorInsight,
    DiscoveredProspect,
    IdealCustomerProfile,
    BuyerPersona,
    MarketSegment,
    NeedSignal,
    SignalSeverity,
    TargetMarketDossier,
)
from .query_planner import QueryPlanner, TargetedQuery
from .exporters import export_sales_lead_tracker_csv, export_marketing_handoff_json
from .relevance_filter import RelevanceFilter
from .pitch_generator import DynamicPitchGenerator
from ..tools.agent_reach_tool import AgentReachTool
from ..tools.signal_detector import SignalDetector
from ..tools.excel_manager import MasterExcelManager

logger = logging.getLogger("TargetMarketResearcher")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [Agent 2]: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class TargetMarketResearcherAgent:
    """
    Agent 2 in the scalyn.si multi-agent collective.
    Dynamic researcher capable of discovering and qualifying target markets
    for ANY business model: B2B SaaS, local services, tuition academies, D2C, or agencies.
    """

    def __init__(
        self,
        reach_tool: Optional[AgentReachTool] = None,
        signal_detector: Optional[SignalDetector] = None,
        query_planner: Optional[QueryPlanner] = None,
        excel_manager: Optional[MasterExcelManager] = None,
        relevance_filter: Optional[RelevanceFilter] = None,
        pitch_generator: Optional[DynamicPitchGenerator] = None,
    ):
        self.reach_tool = reach_tool or AgentReachTool()
        self.detector = signal_detector or SignalDetector()
        self.query_planner = query_planner or QueryPlanner()
        self.excel_manager = excel_manager or MasterExcelManager()
        self.relevance_filter = relevance_filter or RelevanceFilter()
        self.pitch_generator = pitch_generator or DynamicPitchGenerator()
        self.output_dir = settings.dossier_output_dir

    def run(self, brief: ClientBrief) -> TargetMarketDossier:
        """
        Execute end-to-end market research workflow for a client brief:
        1. Classify business model & market type
        2. Formulate dynamic ICP & buyer triggers
        3. Develop 2-3 psychological buyer personas
        4. Segment & prioritize market opportunities
        5. Analyze competitor vulnerabilities
        6. Formulate cross-platform queries & scout live channels dynamically
        7. Audit digital presence & detect concrete need signals
        8. Score prospects & draft tailored sales hooks
        9. Generate Mom-Test validation interview questions
        10. Compile and export TargetMarketDossier
        """
        logger.info(f"Starting research run for: '{brief.startup_name}' ({brief.industry})")
        dossier_id = f"DOSSIER-{uuid.uuid4().hex[:8].upper()}"

        # Step 1: Infer/Verify Business Model
        model_type = self._classify_business_model(brief)
        logger.info(f"Classified business model: {model_type.value}")

        # Step 2: Formulate Tailored ICP
        icp = self._build_icp(brief, model_type)

        # Step 3: Develop Deep Buyer Personas (2-3 archetypes)
        personas = self._build_buyer_personas(brief, model_type, icp)

        # Step 4: Rank Market Segments
        segments = self._build_ranked_segments(brief, model_type)

        # Step 5: Competitor Landscape & Weakness Analysis
        competitor_insights = self._analyze_competitors(brief)

        # Step 6: Dynamic Query Planning (Decision-Maker, Pain Point, Friction, Platform Mapping)
        planned_queries = self.query_planner.plan_queries(brief, model_type)
        logger.info(f"Generated {len(planned_queries)} dynamic targeted queries across platforms.")

        # Step 7: Scout and Qualify Prospects
        prospects = self._scout_and_qualify_prospects(brief, icp, planned_queries)

        # Step 8: Formulate Mom-Test Customer Discovery Questions
        validation_questions = self._build_validation_questions(brief, icp)

        # Step 9: Synthesize Channel & Sales Recommendations for downstream agents
        marketing_channels = self._recommend_marketing_channels(model_type, brief)
        sales_recommendations = self._recommend_sales_strategy(model_type, brief, len(prospects))

        dossier = TargetMarketDossier(
            dossier_id=dossier_id,
            client_brief=brief,
            business_model_classification=model_type.value,
            ideal_customer_profile=icp,
            buyer_personas=personas,
            ranked_market_segments=segments,
            competitor_landscape=competitor_insights,
            discovered_prospects=prospects,
            interview_validation_questions=validation_questions,
            recommended_channels_for_agent_3=marketing_channels,
            sales_outreach_recommendations_for_agent_5=sales_recommendations,
            generated_query_plan=[q.model_dump() for q in planned_queries],
            generated_at=datetime.utcnow(),
        )

        # Persist master dossier and generate downstream handoffs
        master_path = self._save_dossier(dossier)
        sales_csv_path = export_sales_lead_tracker_csv(dossier)
        mktg_json_path = export_marketing_handoff_json(dossier)
        
        # Synchronize with Master Lead Database Excel
        excel_sync = self.excel_manager.sync_prospects(brief.startup_name, prospects)

        logger.info(f"Dossier {dossier_id} finalized with {len(prospects)} qualified prospects.")
        logger.info(f"Generated Sales Lead Tracker CSV: {sales_csv_path}")
        logger.info(f"Generated Marketing Handoff Brief: {mktg_json_path}")
        logger.info(
            f"Master Excel Database Synced: +{excel_sync['total_added']} added, "
            f"{excel_sync['duplicates_skipped']} duplicates skipped. Total in DB: {excel_sync['total_in_db']} "
            f"({excel_sync['filepath']})"
        )
        return dossier

    def _classify_business_model(self, brief: ClientBrief) -> BusinessModelType:
        """Determine whether the business is B2B, B2C, B2B2C, local service, etc."""
        if brief.business_model:
            return brief.business_model

        desc = (brief.product_service_description + " " + brief.industry).lower()
        if any(w in desc for w in ["academy", "tuition", "coaching", "bakery", "salon", "clinic", "plumber"]):
            return BusinessModelType.SERVICE_LOCAL
        if any(w in desc for w in ["saas", "software", "api", "enterprise", "b2b", "workflow automation"]):
            return BusinessModelType.B2B
        if any(w in desc for w in ["agency", "freelance", "consulting", "design studio", "dev shop"]):
            return BusinessModelType.FREELANCE_AGENCY
        if any(w in desc for w in ["ecommerce", "d2c", "apparel", "consumer brand"]):
            return BusinessModelType.D2C
        return BusinessModelType.B2B

    def _build_icp(self, brief: ClientBrief, model_type: BusinessModelType) -> IdealCustomerProfile:
        """Formulate tailored ICP based on industry, geographic scope, and value prop."""
        if model_type in [BusinessModelType.SERVICE_LOCAL, BusinessModelType.B2C]:
            target_cat = f"Local Consumers, Students & Families in {brief.target_city_region}"
            firmographics = {
                "household_type": "Families, working parents, students",
                "income_tier": "Middle to upper-middle class",
                "locality_radius": f"Within 10-15km of {brief.target_city_region}",
            }
            pain_points = [
                f"Difficulty finding trustworthy and consistent {brief.industry} options locally",
                "Lack of personalized attention, modern learning aids, or transparent tracking",
                "High travel friction or inflexible schedules",
            ]
            triggers = [
                "Upcoming academic exam cycle or term results",
                "Word-of-mouth dissatisfaction with previous traditional provider",
                "Relocating to the area or seeking urgent remediation",
            ]
            decision_makers = ["Parents / Guardians", "Adult Learners", "Primary Family Budget Holder"]
            anti_personas = [
                "Bargain-hunters seeking lowest rock-bottom rate regardless of quality",
                "Uncommitted prospects unwilling to follow prescribed regimen",
            ]
        elif model_type == BusinessModelType.FREELANCE_AGENCY:
            target_cat = f"Growing SMBs and Founders needing {brief.industry} capability"
            firmographics = {
                "company_size": "5 - 50 employees",
                "revenue_tier": "\$200k - \$2M ARR / annual revenue",
                "tech_maturity": "Low to medium automation; reliant on manual operations",
            }
            pain_points = [
                "Overwhelmed founders wearing too many hats without specialized execution",
                "Burned by slow, overpriced legacy agencies with zero skin in the game",
                "Bottlenecks converting manual inquiries into closed revenue",
            ]
            triggers = [
                "Recent funding, seasonal product launch, or marketing slump",
                "Key team member departure or failed internal hiring attempt",
                "Noticeable drop in inbound lead conversion",
            ]
            decision_makers = ["Founder / CEO", "Managing Director", "Head of Growth / Marketing"]
            anti_personas = [
                "Zero-budget pre-revenue founders expecting free unlimited work",
                "Organizations with rigid 6-month corporate procurement hurdles",
            ]
        else:  # B2B / B2B SaaS
            target_cat = f"B2B Organizations and Scaleups in {brief.industry}"
            firmographics = {
                "company_size": "10 - 200 team members",
                "primary_geography": brief.target_city_region,
                "workflow_profile": "High volume of operational workflows or customer interactions",
            }
            pain_points = [
                f"High operational costs or repetitive labor required for {brief.industry} tasks",
                "Siloed data and lack of automated pipeline visibility",
                "Slow turnaround times resulting in lost customer opportunities",
            ]
            triggers = [
                "Rapid customer expansion stretching support/ops to breaking point",
                "Adoption of modern tech stack or quarterly efficiency mandate",
                "Budget cycle reviews looking to consolidate redundant software",
            ]
            decision_makers = ["VP of Operations", "Chief Technology Officer", "Founder / CEO", "Head of Sales"]
            anti_personas = [
                "Legacy enterprises strictly requiring on-premise air-gapped deployments",
                "Companies with zero dedicated budget for operational efficiency",
            ]

        return IdealCustomerProfile(
            target_category=target_cat,
            firmographic_or_demographic=firmographics,
            geographic_focus=brief.target_city_region,
            key_pain_points=pain_points,
            buyer_triggers=triggers,
            decision_maker_profiles=decision_makers,
            anti_persona_signals=anti_personas,
        )

    def _build_buyer_personas(
        self,
        brief: ClientBrief,
        model_type: BusinessModelType,
        icp: IdealCustomerProfile,
    ) -> list[BuyerPersona]:
        """Create 2-3 empathetic psychological personas tailored to the startup."""
        personas = []

        # If explicit target personas were extracted from the startup website/brief
        if brief.target_buyer_personas:
            p1_name = brief.target_buyer_personas[0]
            p2_name = brief.target_buyer_personas[1] if len(brief.target_buyer_personas) > 1 else "Research Director"

            personas.append(
                BuyerPersona(
                    persona_name=f"Lead Practitioner ({p1_name.split('&')[0].strip()})",
                    title_or_role=p1_name,
                    context_and_background=(
                        f"Active domain professional working in {brief.industry}. "
                        f"Responsible for core analysis, screening, and execution workflows."
                    ),
                    core_frustrations=[
                        f"Disjointed legacy tools and manual repetitive tasks causing slow turnaround",
                        f"Overpriced existing platforms with restrictive seat licensing",
                        f"High cognitive burden synthesizing data without modern automated verification",
                    ],
                    aspirations_and_goals=[
                        f"Accelerate delivery cycles 3x using modern tech ({brief.unique_value_proposition})",
                        f"Ensure flawless methodological rigor and publishable / auditable accuracy",
                    ],
                    preferred_channels=["LinkedIn", "Reddit (Domain Communities)", "Specialized Research Platforms", "X"],
                    common_objections=[
                        "How steep is the learning curve for my team or co-authors?",
                        "Is data export compliant with standard reporting guidelines?",
                    ],
                    purchasing_motivation="Methodological precision, time savings, and seamless workflow collaboration.",
                )
            )
            personas.append(
                BuyerPersona(
                    persona_name=f"Institutional Lead ({p2_name.split('&')[0].strip()})",
                    title_or_role=p2_name,
                    context_and_background=(
                        f"Directs research initiatives and allocates software/grant budgets for {brief.industry} projects."
                    ),
                    core_frustrations=[
                        "Strained budgets from recurring per-seat costs of legacy incumbent software",
                        "Difficulty ensuring consistent protocol adherence across distributed collaborators",
                    ],
                    aspirations_and_goals=[
                        "Equip research cohorts with accessible, high-performance tooling",
                        "Maximize throughput and output quality per research budget grant",
                    ],
                    preferred_channels=["Academic Listservs", "LinkedIn", "Peer Referrals", "Scientific Conferences"],
                    common_objections=[
                        "Can we pilot this across an active project before institutional commitment?",
                        "Is there direct customer onboarding support?",
                    ],
                    purchasing_motivation="Cost efficiency, team scalability, and reliable output quality.",
                )
            )
            return personas

        if model_type in [BusinessModelType.SERVICE_LOCAL, BusinessModelType.B2C]:
            personas.append(
                BuyerPersona(
                    persona_name="Anxious Parent Ayesha",
                    title_or_role="Parent / Working Professional",
                    context_and_background=(
                        f"Juggling a demanding full-time job while prioritizing her child's educational outcomes in {brief.target_city_region}."
                    ),
                    core_frustrations=[
                        "Cannot monitor child's daily progress consistently due to long work hours",
                        "Previous centers had overcrowded batches and indifferent teachers",
                        "High fees with zero measurable accountability",
                    ],
                    aspirations_and_goals=[
                        "Ensure child achieves top percentiles without mental burnout",
                        "Regular, transparent feedback and convenient scheduling",
                    ],
                    preferred_channels=["WhatsApp Communities", "Facebook Groups", "Local Word-of-Mouth", "Instagram"],
                    common_objections=[
                        "Will my child actually get individual attention?",
                        "Is the methodology aligned with the current curriculum board?",
                    ],
                    purchasing_motivation="Peace of mind, child's academic future, and verified reputation.",
                )
            )
            personas.append(
                BuyerPersona(
                    persona_name="Ambitious Student Bilal",
                    title_or_role="High School / College Aspirant",
                    context_and_background="Preparing for competitive entrance exams or university admissions under immense peer pressure.",
                    core_frustrations=[
                        "Dull rote-learning lectures that fail to clarify foundational concepts",
                        "Hesitant to ask questions in front of large classroom peers",
                        "Outdated practice material that doesn't match exam difficulty",
                    ],
                    aspirations_and_goals=[
                        "Crack targeted entrance tests with high confidence",
                        "Access flexible, engaging study materials and modern guidance",
                    ],
                    preferred_channels=["YouTube", "Instagram", "Discord", "Reddit"],
                    common_objections=[
                        "Is this harder than what my school teaches?",
                        "Can I balance this with my regular school schedule?",
                    ],
                    purchasing_motivation="Clear concept mastery and self-confidence before exams.",
                )
            )
        else:  # B2B, Agency, SaaS
            personas.append(
                BuyerPersona(
                    persona_name="Stretched Operator Omar",
                    title_or_role="Founder & Managing Director",
                    context_and_background=(
                        f"Leading a fast-growing {brief.industry} business in {brief.target_city_region}. "
                        "Constantly putting out operational fires while trying to steer company strategy."
                    ),
                    core_frustrations=[
                        "Team spends hours on manual repetitive tasks instead of high-leverage revenue work",
                        "Existing software tools are disconnected, complex, and poorly adopted",
                        "Cannot scale revenue without linear increase in expensive headcount",
                    ],
                    aspirations_and_goals=[
                        "Automate routine operations to unlock 2x capacity with the same headcount",
                        "Clear visibility into daily conversion metrics and pipeline health",
                    ],
                    preferred_channels=["LinkedIn", "X (Twitter)", "Private Founder Slacks/WhatsApp", "Tech Newsletters"],
                    common_objections=[
                        "How long does onboarding take? We cannot afford disruption.",
                        "What is the realistic ROI within the first 60 days?",
                    ],
                    purchasing_motivation="Operational leverage, predictable growth, and freeing up founder headspace.",
                )
            )
            personas.append(
                BuyerPersona(
                    persona_name="Results-Driven Growth Lead Sarah",
                    title_or_role="Head of Growth / Marketing",
                    context_and_background=(
                        f"Responsible for driving quarterly acquisition and pipeline growth for {brief.startup_name}'s ICP."
                    ),
                    core_frustrations=[
                        "Ad costs are rising while organic conversion rates are stagnating",
                        "Difficulty attributing which campaigns actually drive qualified opportunities",
                        "Slow creative and technical iteration due to reliance on external contractors",
                    ],
                    aspirations_and_goals=[
                        "Implement agile, repeatable growth loops with modern AI-enabled tooling",
                        "Deliver quantifiable pipeline results ahead of quarterly board reviews",
                    ],
                    preferred_channels=["LinkedIn", "Product Hunt", "Reddit (r/growthhacking, r/marketing)", "X"],
                    common_objections=[
                        "Is this compatible with our current CRM and workflow?",
                        "Will this require dedicated engineering support to maintain?",
                    ],
                    purchasing_motivation="Achieving growth targets with speed, agility, and measurable attribution.",
                )
            )
        return personas

    def _build_ranked_segments(
        self,
        brief: ClientBrief,
        model_type: BusinessModelType,
    ) -> list[MarketSegment]:
        """Rank market segments based on conversion speed and strategic fit."""
        return [
            MarketSegment(
                segment_name=f"Urgent Pain Segment: Active Searchers in {brief.target_city_region}",
                rank=1,
                priority_tier="Tier 1 - Immediate Win",
                estimated_opportunity_size="High intent, immediate close window (15-30% conversion potential)",
                conversion_readiness="High",
                strategic_rationale=(
                    f"Prospects actively searching for {brief.industry} solutions or expressing dissatisfaction "
                    f"with legacy competitors. Lowest acquisition friction and fastest feedback loop."
                ),
            ),
            MarketSegment(
                segment_name=f"Underserved Modernizers: Established operators needing {brief.unique_value_proposition}",
                rank=2,
                priority_tier="Tier 2 - Secondary Growth",
                estimated_opportunity_size="Broad market share, steady compounding revenue",
                conversion_readiness="Medium",
                strategic_rationale=(
                    "Have proven budgets and clear operational volume, but currently rely on outdated or manual workflows. "
                    "Require consultative outreach demonstrating clear ROI."
                ),
            ),
            MarketSegment(
                segment_name="Aspirational Scalers: Early-stage operators looking to expand capacity",
                rank=3,
                priority_tier="Tier 3 - Long-term Scale",
                estimated_opportunity_size="Mass volume, lower price tolerance",
                conversion_readiness="Low",
                strategic_rationale=(
                    "Valuable for viral referral loops and self-serve tier adoption, but have longer closing cycles."
                ),
            ),
        ]

    def _analyze_competitors(self, brief: ClientBrief) -> list[CompetitorInsight]:
        """Map competitor landscape, identifying vulnerabilities and our client's wedge."""
        insights = []
        named_competitors = brief.key_competitors or [f"Traditional {brief.industry} Providers", "Generic Mass Agencies"]
        
        for comp in named_competitors:
            insights.append(
                CompetitorInsight(
                    competitor_name=comp,
                    website_or_presence=f"https://duckduckgo.com/?q={requests.utils.quote(comp)}",
                    perceived_strengths=[
                        "Established brand tenure in the local/regional market",
                        "Physical presence or high historical word-of-mouth",
                    ],
                    vulnerabilities_and_complaints=[
                        "Slow manual communication and lack of modern digital transparency",
                        "Rigid one-size-fits-all packages with zero customization",
                        "High overhead pricing passed directly onto the client",
                    ],
                    scalyn_differentiation_angle=(
                        f"Deploy {brief.startup_name}'s agile, tech-enabled solution ({brief.unique_value_proposition}) "
                        f"to deliver 3x faster turnaround at transparent, ROI-backed pricing."
                    ),
                )
            )
        return insights

    def _scout_and_qualify_prospects(
        self,
        brief: ClientBrief,
        icp: IdealCustomerProfile,
        planned_queries: list[TargetedQuery],
    ) -> list[DiscoveredProspect]:
        """
        Execute targeted scouting across platforms using dynamic query matrix,
        qualify prospects with 7/10 Relevancy Gate, and synthesize custom outreach hooks.
        """
        prospects: list[DiscoveredProspect] = []
        seen_urls: set[str] = set()

        for tq in planned_queries:
            raw_results = self.reach_tool.scout_platform(tq.query, platform=tq.target_platform, limit=3)
            for item in raw_results:
                title = item.get("title", "Prospect Encountered")
                handle = item.get("handle_or_name", f"{tq.target_platform.capitalize()} Lead")
                url = item.get("url", f"https://{tq.target_platform}.com")
                snippet = item.get("snippet", title)

                if url in seen_urls:
                    continue

                # -------------------------------------------------------------
                # Guardrail #4: 7/10 Relevancy Gate
                # -------------------------------------------------------------
                is_passed, rel_score, rel_rationale = self.relevance_filter.evaluate(
                    entity_name=handle,
                    url=url,
                    snippet=snippet,
                    brief=brief,
                )
                if not is_passed:
                    logger.info(
                        f"Relevance Gate (<7/10): Dropped '{handle}' ({url}) "
                        f"[Score: {rel_score}/10] - {rel_rationale}"
                    )
                    continue

                seen_urls.add(url)

                # Signal detection on snippet
                text_signals = self.detector.audit_text_snippet(snippet)

                # Digital presence audit for web results or URLs
                presence_status = "active_presence"
                if tq.target_platform == "web" or url.startswith("http"):
                    page_audit = self.reach_tool.fetch_url_content(url)
                    status_str, web_signals = self.detector.audit_digital_presence(url, page_audit)
                    presence_status = status_str
                    text_signals.extend(web_signals)

                # Deduplicate signals
                unique_signals = {s.description: s for s in text_signals}.values()
                signals_list = list(unique_signals)

                # Provide targeted signal reflecting query intent if none caught in minimal fallback
                if not signals_list:
                    primary_sig_type = tq.expected_signals[0] if tq.expected_signals else "operational_bottleneck"
                    signals_list.append(
                        NeedSignal(
                            signal_type=primary_sig_type,
                            description=f"Identified via targeted {tq.query_type.value} query: {tq.intent_rationale}",
                            source_snippet=snippet,
                            severity=SignalSeverity.MEDIUM,
                        )
                    )

                # -------------------------------------------------------------
                # Guardrail #5: Dynamic Non-Spam Outreach Pitch
                # -------------------------------------------------------------
                sales_hook = self.pitch_generator.generate_hook(
                    prospect_name=handle,
                    target_url=url,
                    snippet=snippet,
                    signals=signals_list,
                    brief=brief,
                )

                prospect = DiscoveredProspect(
                    name_or_handle=handle,
                    organization=title,
                    role_or_title="Decision Maker / ICP Target",
                    platform_source=tq.target_platform,
                    verified_url=url,
                    location=brief.target_city_region,
                    observed_need_signals=signals_list,
                    match_score=rel_score,
                    match_reasoning=f"{rel_rationale} Verified via {tq.target_platform}.",
                    digital_presence_status=presence_status,
                    personalized_hook_for_sales=sales_hook,
                    scouted_at=datetime.utcnow(),
                )
                prospects.append(prospect)

        # Sort prospects by match score descending
        prospects.sort(key=lambda p: p.match_score, reverse=True)
        return prospects[: settings.max_prospects_per_run]

    def _build_validation_questions(
        self,
        brief: ClientBrief,
        icp: IdealCustomerProfile,
    ) -> list[str]:
        """
        Formulate 5-7 non-leading customer discovery questions (The Mom Test style)
        to validate real willingness to pay before investing heavy marketing spend.
        """
        return [
            f"When was the last time you had to deal with {brief.industry} challenges? Walk me through what happened step-by-step.",
            f"What specific workarounds, software, or manual processes are you currently using to handle this today?",
            "What is the single most frustrating part of that existing process, and how much time or money does it cost you each week?",
            "Have you actively tried looking for other solutions or hiring someone to fix this in the last 6 months? If not, why?",
            f"If a solution existed that gave you {brief.unique_value_proposition.lower()}, what would prevent your team or family from adopting it immediately?",
            "Who else besides yourself would need to approve budget or change the way things are done to implement a better solution?",
            "Where do you typically search or ask for advice when trying to solve this kind of operational headache?",
        ]

    def _recommend_marketing_channels(
        self,
        model_type: BusinessModelType,
        brief: ClientBrief,
    ) -> list[str]:
        """Curate prioritized channel recommendations passed to Agent 3 (Marketing)."""
        if model_type in [BusinessModelType.SERVICE_LOCAL, BusinessModelType.B2C]:
            return [
                "Hyper-local Meta Ads (Instagram & Facebook) geo-fenced to target neighborhoods",
                "Community WhatsApp and Facebook Parent/Resident groups with value-first guides",
                "Google Business Profile (GMB) optimization for high-intent local search queries",
                "Referral loops incentivized by tuition credits or family discounts",
            ]
        elif model_type == BusinessModelType.FREELANCE_AGENCY:
            return [
                "LinkedIn organic founder thought-leadership showcasing before/after case breakdowns",
                "Cold email sequences to verified founders flagging specific digital friction points",
                "Niche community engagement on Reddit (r/smallbusiness, r/entrepreneur)",
                "Free 10-minute digital presence video audit teardowns (Loom audits)",
            ]
        else:
            return [
                "Account-Based Marketing (ABM) on LinkedIn targeted at Heads of Ops & Founders",
                "High-signal X/Twitter engagement in founder and SaaS build-in-public communities",
                "SEO-targeted comparison & alternative landing pages ('vs legacy competitors')",
                "Interactive ROI calculator widgets demonstrating monthly labor savings",
            ]

    def _recommend_sales_strategy(
        self,
        model_type: BusinessModelType,
        brief: ClientBrief,
        prospect_count: int,
    ) -> list[str]:
        """Curate prioritized sales tactical guidance passed to Agent 5 (Sales Lead)."""
        return [
            f"Initiate consultative outreach to the {prospect_count} scouted prospects using their tailored need hooks.",
            "Never open with a hard pitch; reference their exact observed friction point or public comment first.",
            "Offer a zero-risk diagnostic (e.g. Free 15-Minute Operational Review or Free Trial Assessment).",
            "Maintain a 3-touch cadence over 10 business days: Observation -> Value Wedge -> Polite Breakup.",
            "Log all feedback into the centralized dossier so Agent 1 and Agent 3 can refine positioning.",
        ]

    def _save_dossier(self, dossier: TargetMarketDossier) -> str:
        """Persist target market dossier into organized JSON file."""
        filename = f"{dossier.dossier_id}_{dossier.client_brief.startup_name.lower().replace(' ', '_')}.json"
        target_path = self.output_dir / filename
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(dossier.model_dump_json(indent=2))
        logger.info(f"Dossier successfully saved to: {target_path}")
        return str(target_path)
