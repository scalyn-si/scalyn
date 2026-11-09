"""
Pydantic Data Contracts and Schemas for Agent 2: Target Market Researcher
scalyn.si (GrowWithAI Multi-Agent System)
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, HttpUrl


class BusinessModelType(str, Enum):
    B2B = "B2B"
    B2C = "B2C"
    B2B2C = "B2B2C"
    D2C = "D2C"
    MARKETPLACE = "MARKETPLACE"
    SERVICE_LOCAL = "SERVICE_LOCAL"
    FREELANCE_AGENCY = "FREELANCE_AGENCY"


class SignalSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ClientBrief(BaseModel):
    """
    Standardized upstream brief ingested from Agent 1 (Business Analyst)
    or client onboarding intake.
    """
    startup_name: str = Field(..., description="Name of the startup or small business")
    industry: str = Field(..., description="Industry or niche (e.g. B2B SaaS, Tuition Academy, Home Bakery)")
    business_model: Optional[BusinessModelType] = Field(
        default=None,
        description="Business model type (B2B, B2C, B2B2C, etc.). If None, Agent 2 will infer it."
    )
    product_service_description: str = Field(
        ..., 
        description="Detailed description of what the startup offers, its core solution and features"
    )
    unique_value_proposition: str = Field(
        ..., 
        description="What makes this business uniquely better than alternatives"
    )
    target_city_region: str = Field(
        ..., 
        description="Geographic scope: Local (e.g., Karachi, Lahore), National, or Global (e.g., US/EU remote)"
    )
    primary_goal: str = Field(
        ..., 
        description="Primary growth objective (e.g., First 10 paying pilot clients, Scale monthly revenue by 3x)"
    )
    budget: Optional[str] = Field(
        default="Bootstrapped / Low Budget", 
        description="Available marketing/growth budget or constraints"
    )
    existing_channels: list[str] = Field(
        default_factory=list, 
        description="Channels currently used (e.g., WhatsApp, Instagram, None, Cold Email)"
    )
    pricing_model: Optional[str] = Field(
        default=None, 
        description="Pricing structure (e.g., \$49/mo subscription, \$500 one-off project, PKR 5,000/course)"
    )
    key_competitors: list[str] = Field(
        default_factory=list, 
        description="Known competitors mentioned in upstream brief"
    )
    notes_from_agent_1: Optional[str] = Field(
        default=None, 
        description="Diagnostic observations or operational bottlenecks flagged by Agent 1"
    )
    geographic_scope: Optional[str] = Field(
        default="GLOBAL",
        description="Geographic scope classification: GLOBAL | REGIONAL | LOCAL_CITY"
    )
    target_buyer_personas: list[str] = Field(
        default_factory=list,
        description="Explicit target buyer personas (e.g. Epidemiologists, Clinical Researchers)"
    )


class NeedSignal(BaseModel):
    """
    An observed digital, operational, or behavioral signal indicating pain or buying intent.
    """
    signal_type: str = Field(
        ..., 
        description="Type of signal: e.g., 'operational_bottleneck', 'customer_complaint', 'outdated_presence', 'broken_website', 'hiring_spike', 'tech_stack_gap', 'community_inquiry'"
    )
    description: str = Field(..., description="Concrete description of the observed signal")
    source_snippet: Optional[str] = Field(None, description="Exact quotation or text excerpt evidencing the signal")
    severity: SignalSeverity = Field(SignalSeverity.MEDIUM, description="Urgency / relevance of this signal")


class DiscoveredProspect(BaseModel):
    """
    An individual verified prospect, community member, or business scouted
    via web / social platforms (LinkedIn, X, Reddit, web directories).
    """
    name_or_handle: str = Field(..., description="Full name, company name, or social handle")
    organization: Optional[str] = Field(None, description="Associated company, school, or group name")
    role_or_title: Optional[str] = Field(None, description="Job title, persona role (e.g., Founder, Parent, Student)")
    platform_source: str = Field(
        ..., 
        description="Where prospect was found: 'linkedin', 'x', 'reddit', 'web', 'google_maps', etc."
    )
    verified_url: str = Field(..., description="Direct URL to prospect profile, post, website, or community thread")
    location: Optional[str] = Field(None, description="Geographic location or city if identifiable")
    observed_need_signals: list[NeedSignal] = Field(
        default_factory=list, 
        description="List of concrete verified pain points or need signals"
    )
    match_score: int = Field(
        ..., 
        ge=1, 
        le=10, 
        description="Compatibility score (1-10) evaluating fit with client ICP"
    )
    match_reasoning: str = Field(..., description="Concise rationale explaining why this prospect matches the ICP")
    digital_presence_status: Optional[str] = Field(
        None, 
        description="Audit summary: e.g., 'no_website', 'outdated_socials', 'high_friction_booking', 'active_complainer'"
    )
    personalized_hook_for_sales: str = Field(
        ..., 
        description="Context-rich, non-spammy conversation opener crafted specifically for Agent 5 (Sales Lead)"
    )
    scouted_at: datetime = Field(
        default_factory=datetime.utcnow, 
        description="Timestamp when prospect was discovered and verified"
    )


class IdealCustomerProfile(BaseModel):
    """Structured Ideal Customer Profile (ICP) tailored dynamically to any startup."""
    target_category: str = Field(..., description="Broad target category (e.g., Mid-market D2C Brands, Local Parents)")
    firmographic_or_demographic: dict[str, Any] = Field(
        default_factory=dict, 
        description="Key filters: Company size, revenue range, student grade level, household income tier, etc."
    )
    geographic_focus: str = Field(..., description="Geographic distribution and language preferences")
    key_pain_points: list[str] = Field(
        ..., 
        description="Core burning problems this ICP suffers from without our client's solution"
    )
    buyer_triggers: list[str] = Field(
        ..., 
        description="Specific catalyst events that make them urgently seek solutions right now"
    )
    decision_maker_profiles: list[str] = Field(
        ..., 
        description="Job titles or roles responsible for purchasing decisions"
    )
    anti_persona_signals: list[str] = Field(
        default_factory=list, 
        description="Red flag attributes indicating someone is NOT a good fit (to prevent wasted sales effort)"
    )


class BuyerPersona(BaseModel):
    """In-depth psychological and behavioral archetype."""
    persona_name: str = Field(..., description="Archetype moniker (e.g., 'Frustrated Founder Farhan', 'Anxious Parent Ayesha')")
    title_or_role: str = Field(..., description="Role, title, or life stage")
    context_and_background: str = Field(..., description="Daily environment and organizational context")
    core_frustrations: list[str] = Field(..., description="Top daily blockers and emotional friction points")
    aspirations_and_goals: list[str] = Field(..., description="What success looks like for them in 6-12 months")
    preferred_channels: list[str] = Field(..., description="Where they spend attention (LinkedIn, Reddit, WhatsApp, etc.)")
    common_objections: list[str] = Field(..., description="Likely pushbacks during marketing or sales pitches")
    purchasing_motivation: str = Field(..., description="Primary psychological driver to buy")


class MarketSegment(BaseModel):
    """Ranked market segment opportunity."""
    segment_name: str = Field(..., description="Name of the customer segment")
    rank: int = Field(..., ge=1, description="Priority rank (1 is highest priority)")
    priority_tier: str = Field(
        ..., 
        description="'Tier 1 - Immediate Win', 'Tier 2 - Secondary Growth', or 'Tier 3 - Long-term Scale'"
    )
    estimated_opportunity_size: str = Field(..., description="Qualitative or estimated quantitative market size")
    conversion_readiness: str = Field(..., description="Speed and ease of conversion ('High', 'Medium', 'Low')")
    strategic_rationale: str = Field(..., description="Why this segment should be targeted now")


class CompetitorInsight(BaseModel):
    """Competitor profile and vulnerability mapping."""
    competitor_name: str = Field(..., description="Competitor company or service name")
    website_or_presence: Optional[str] = Field(None, description="Website URL or profile link")
    perceived_strengths: list[str] = Field(default_factory=list, description="What they do reasonably well")
    vulnerabilities_and_complaints: list[str] = Field(
        default_factory=list, 
        description="Frequent customer complaints, feature gaps, or weaknesses observed"
    )
    scalyn_differentiation_angle: str = Field(
        ..., 
        description="The asymmetric wedge our client uses to win deals against them"
    )


class TargetMarketDossier(BaseModel):
    """
    Master Output Payload for Agent 2: Target Market Researcher.
    Consumed directly by Agent 3 (Marketing) and Agent 5 (Sales Lead).
    """
    dossier_id: str = Field(..., description="Unique run/dossier identifier")
    client_brief: ClientBrief = Field(..., description="Echo of client brief ingested")
    business_model_classification: str = Field(..., description="Inferred or verified business model")
    ideal_customer_profile: IdealCustomerProfile = Field(..., description="Tailored ICP definition")
    buyer_personas: list[BuyerPersona] = Field(
        ..., 
        min_length=2, 
        description="2 to 3 detailed, empathetic buyer personas"
    )
    ranked_market_segments: list[MarketSegment] = Field(
        ..., 
        min_length=1, 
        description="Ranked market segment opportunities"
    )
    competitor_landscape: list[CompetitorInsight] = Field(
        default_factory=list, 
        description="Competitor vulnerabilities and differentiation levers"
    )
    discovered_prospects: list[DiscoveredProspect] = Field(
        default_factory=list, 
        description="Scouted, verified prospects exhibiting concrete need signals"
    )
    interview_validation_questions: list[str] = Field(
        ..., 
        min_length=5, 
        description="5-7 non-leading customer discovery questions (The Mom Test style)"
    )
    recommended_channels_for_agent_3: list[str] = Field(
        ..., 
        description="Prioritized distribution channels passed to Agent 3 (Marketing)"
    )
    sales_outreach_recommendations_for_agent_5: list[str] = Field(
        ..., 
        description="Actionable sales tactical advice passed to Agent 5 (Sales Lead)"
    )
    generated_query_plan: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Dynamic multi-channel query matrix generated by QueryPlanner"
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow, 
        description="Timestamp when dossier was finalized"
    )
