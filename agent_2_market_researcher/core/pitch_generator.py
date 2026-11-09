"""
Dynamic Pitch & Outreach Hook Generator for Agent 5 (Sales Lead)
scalyn.si (GrowWithAI Multi-Agent Collective)

Generates customized, conversational, non-spam outreach hooks directly reflecting
the prospect's observed need signals and the client startup's actual UVP.
Zero static templates. Zero legacy exam prep hardcoding.
"""

import logging
import re
from typing import Optional
from .schemas import ClientBrief, NeedSignal, SignalSeverity

logger = logging.getLogger("DynamicPitchGenerator")


class DynamicPitchGenerator:
    """
    Context-aware pitch generator that crafts natural consultative opening hooks
    for Agent 5 (Sales Lead) based on the scouted prospect's actual context.
    """

    def generate_hook(
        self,
        prospect_name: str,
        target_url: str,
        snippet: str,
        signals: list[NeedSignal],
        brief: ClientBrief,
    ) -> str:
        """
        Draft an individualized consultative opening hook tailored to the prospect's situation.
        """
        clean_name = self._format_name(prospect_name)
        uvp_phrase = brief.unique_value_proposition.rstrip(".")
        startup = brief.startup_name

        # 1. Competitor dissatisfaction hook (e.g. Reddit thread about Covidence / Rayyan)
        if brief.key_competitors:
            for comp in brief.key_competitors:
                if comp.lower() in (target_url + " " + snippet).lower():
                    return (
                        f"Hi {clean_name}, noticed your discussion comparing tools like {comp}. "
                        f"We developed {startup} specifically around {uvp_phrase.lower()} to eliminate "
                        f"those exact pricing and workflow hurdles. Happy to show you our interactive workflow if you're exploring alternatives."
                    )

        # 2. Domain-specific hook for Systematic Review / Meta-Analysis
        if any(w in (brief.industry + " " + uvp_phrase).lower() for w in ["meta-analysis", "systematic review", "prisma"]):
            if "reddit.com" in target_url.lower():
                return (
                    f"Hi {clean_name}, saw your Reddit post on systematic review methodology and data synthesis. "
                    f"We built {startup} to deliver {uvp_phrase.lower()}, cutting out weeks of manual dual-screening. "
                    f"Would love to share how teams are streamlining their PRISMA workflow with it."
                )
            else:
                return (
                    f"Hi {clean_name}, came across your work in clinical research and evidence synthesis. "
                    f"At {startup}, we assist research teams by providing {uvp_phrase.lower()}. "
                    f"Would be glad to share how our R-validated workflow accelerates review cycles if relevant."
                )

        # 3. Observed signal-driven hook
        if signals:
            top_signal = max(
                signals,
                key=lambda s: 3 if s.severity == SignalSeverity.CRITICAL else (2 if s.severity == SignalSeverity.HIGH else 1)
            )

            if top_signal.signal_type == "community_inquiry":
                snip_clean = self._clean_snippet(top_signal.source_snippet or snippet)
                return (
                    f"Hi {clean_name}, noticed your inquiry regarding '{snip_clean}'. "
                    f"At {startup}, we help teams solve this by {uvp_phrase.lower()}. "
                    f"Happy to share what has worked well for similar setups if you're still reviewing options."
                )

            if top_signal.signal_type in ["operational_bottleneck", "tech_stack_gap"]:
                return (
                    f"Hi {clean_name}, noticed you're navigating operational workflow friction in your stack. "
                    f"We built {startup} around {uvp_phrase.lower()} to streamline that exact overhead. "
                    f"Thought this might be timely given your current priorities."
                )

            if top_signal.signal_type == "outdated_presence":
                return (
                    f"Hi {clean_name}, came across your public profile while researching active operators in {brief.industry}. "
                    f"We specialize in {uvp_phrase.lower()} to make customer discovery and booking seamless. "
                    f"Would love to share a few low-lift enhancements we identified for {prospect_name}."
                )

        # 4. Clean professional B2B consultative fallback
        return (
            f"Hi {clean_name}, came across your team's initiatives in {brief.industry}. "
            f"We launched {startup} to deliver {uvp_phrase.lower()} — thought this might be a valuable "
            f"addition to your current growth toolkit. Open to a brief 5-minute peer chat?"
        )

    def _format_name(self, raw_name: str) -> str:
        """Sanitize prospect handle or name for a natural greeting."""
        if not raw_name:
            return "there"
        clean = re.sub(r"^(?:u/|r/|@)", "", raw_name).strip()
        # If it's a company or academy, use the first word or whole name
        parts = clean.split()
        if len(parts) > 1 and parts[0].isalpha() and len(parts[0]) > 2:
            return parts[0]
        return clean

    def _clean_snippet(self, snip: str) -> str:
        """Truncate and clean snippet for insertion into outreach message."""
        s = re.sub(r"\s+", " ", snip).strip()
        if len(s) > 55:
            return s[:52] + "..."
        return s
