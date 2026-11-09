"""
Signal Detector & Digital-Presence Auditor
Audits prospects, social text snippets, and websites to detect concrete need signals,
operational friction, and customer complaints.
"""

import re
from typing import Any, Optional
from ..core.schemas import NeedSignal, SignalSeverity


class SignalDetector:
    """
    Auditor for discovering concrete need signals and digital friction points.
    Detects 5 universal friction signals:
    1. Technical Gaps (No SSL, missing mobile viewport)
    2. Manual Workflow Bottlenecks (DM for price, screenshot of payment, call to book)
    3. Stale Presence (Copyright/dates older than 2024)
    4. Broken / Missing Web Links (HTTP 404, timeouts, site offline)
    5. Contact Friction (No direct email/WhatsApp links, high-effort forms)
    """

    OPERATIONAL_BOTTLENECK_KEYWORDS = [
        "manual", "manually", "spreadsheet", "excel sheet", "data entry",
        "wasting time", "hours every day", "overwhelmed", "bottleneck",
        "paperwork", "answering calls all day", "answering dms", "can't keep up",
        "administrative burden", "repetitive task"
    ]

    COMPLAINT_KEYWORDS = [
        "unresponsive", "never replied", "ghosted", "bad service", "poor communication",
        "too expensive", "waste of money", "cancelled my subscription", "hate when they",
        "still waiting", "disappointed", "frustrated", "buggy", "broken", "terrible support"
    ]

    INQUIRY_KEYWORDS = [
        "any recommendations", "looking for a", "can anyone recommend", "does anyone know",
        "need a good", "who offers", "alternative to", "tired of", "switching from"
    ]

    HIRING_SPIKE_KEYWORDS = [
        "we are hiring", "looking for an intern", "hiring virtual assistant", "hiring sdr",
        "need a marketer", "seeking sales lead", "expanding our team"
    ]

    MANUAL_WORKFLOW_PATTERNS = [
        "dm for price", "dm for prices", "dm to order", "inbox for price",
        "inbox for prices", "call to book", "call to book appointment",
        "whatsapp screenshot of payment", "send screenshot of payment",
        "screenshot to confirm", "call for appointment", "whatsapp to order",
        "dm us on instagram", "replying manually"
    ]

    def audit_text_snippet(self, text: str) -> list[NeedSignal]:
        """
        Analyze a post, tweet, forum thread, or bio for concrete need signals.
        """
        signals: list[NeedSignal] = []
        text_lower = text.lower()

        # 1. Operational Bottlenecks
        matched_ops = [kw for kw in self.OPERATIONAL_BOTTLENECK_KEYWORDS if kw in text_lower]
        if matched_ops:
            snippet = self._extract_context(text, matched_ops[0])
            signals.append(
                NeedSignal(
                    signal_type="operational_bottleneck",
                    description=f"Exhibits manual process friction or resource constraints (detected: '{matched_ops[0]}').",
                    source_snippet=snippet,
                    severity=SignalSeverity.HIGH if len(matched_ops) > 1 else SignalSeverity.MEDIUM,
                )
            )

        # 2. Manual Workflow Patterns (DM for price, payment screenshots, etc.)
        matched_manual = [p for p in self.MANUAL_WORKFLOW_PATTERNS if p in text_lower]
        if matched_manual:
            snippet = self._extract_context(text, matched_manual[0])
            signals.append(
                NeedSignal(
                    signal_type="operational_bottleneck",
                    description=f"High-friction manual ordering/booking workflow detected ('{matched_manual[0]}') with no self-serve automation.",
                    source_snippet=snippet,
                    severity=SignalSeverity.HIGH,
                )
            )

        # 3. Competitor / Service Dissatisfaction
        matched_complaints = [kw for kw in self.COMPLAINT_KEYWORDS if kw in text_lower]
        if matched_complaints:
            snippet = self._extract_context(text, matched_complaints[0])
            signals.append(
                NeedSignal(
                    signal_type="customer_complaint",
                    description=f"Actively complaining about existing solutions or vendors (detected: '{matched_complaints[0]}').",
                    source_snippet=snippet,
                    severity=SignalSeverity.HIGH,
                )
            )

        # 4. Active Search / Community Inquiries
        matched_inquiries = [kw for kw in self.INQUIRY_KEYWORDS if kw in text_lower]
        if matched_inquiries:
            snippet = self._extract_context(text, matched_inquiries[0])
            signals.append(
                NeedSignal(
                    signal_type="community_inquiry",
                    description=f"Actively seeking vendor/tool recommendations (detected: '{matched_inquiries[0]}').",
                    source_snippet=snippet,
                    severity=SignalSeverity.CRITICAL,
                )
            )

        # 5. Hiring Spikes
        matched_hiring = [kw for kw in self.HIRING_SPIKE_KEYWORDS if kw in text_lower]
        if matched_hiring:
            snippet = self._extract_context(text, matched_hiring[0])
            signals.append(
                NeedSignal(
                    signal_type="hiring_spike",
                    description=f"Hiring or expanding manual headcount to solve capacity (detected: '{matched_hiring[0]}').",
                    source_snippet=snippet,
                    severity=SignalSeverity.MEDIUM,
                )
            )

        return signals

    def audit_digital_presence(
        self,
        url: str,
        page_data: Optional[dict[str, Any]] = None
    ) -> tuple[str, list[NeedSignal]]:
        """
        Audit a website or public business URL for digital friction and outdated presence.
        Evaluates 5 universal friction signals:
        1. Technical Gaps (SSL, Viewport)
        2. Manual Workflow Bottlenecks
        3. Stale Presence (Copyright < 2024)
        4. Broken / Missing Web Links (404/Offline)
        5. Contact Friction (No direct email/WhatsApp links)
        """
        signals: list[NeedSignal] = []
        statuses: list[str] = []

        # -------------------------------------------------------------
        # SIGNAL 1: Technical Gaps - SSL Check & Mobile Viewport Check
        # -------------------------------------------------------------
        if url.startswith("http://") and not url.startswith("https://"):
            signals.append(
                NeedSignal(
                    signal_type="technical_gap",
                    description="Website lacks SSL encryption (running on unsecure HTTP), creating browser warnings for visitors.",
                    source_snippet=url,
                    severity=SignalSeverity.HIGH,
                )
            )
            statuses.append("no_ssl")

        # -------------------------------------------------------------
        # SIGNAL 4: Broken / Missing Web Links (Site Offline or 404/500)
        # -------------------------------------------------------------
        if not page_data or not page_data.get("is_live", True):
            status_code = page_data.get("status_code") if page_data else None
            error_msg = page_data.get("error", "Connection failed") if page_data else "No response"
            signals.append(
                NeedSignal(
                    signal_type="broken_website",
                    description=f"No active digital home: Target web link is unreachable or returning error status ({status_code or error_msg}).",
                    source_snippet=url,
                    severity=SignalSeverity.CRITICAL,
                )
            )
            return "no_active_digital_home", signals

        text = page_data.get("text_content", "")
        text_lower = text.lower()

        # Check mobile viewport tag
        if page_data.get("has_viewport") is False:
            signals.append(
                NeedSignal(
                    signal_type="technical_gap",
                    description="Missing mobile viewport meta tag, causing distorted mobile rendering and visitor drop-off.",
                    source_snippet="<meta name='viewport'> not found",
                    severity=SignalSeverity.HIGH,
                )
            )
            statuses.append("no_mobile_viewport")

        # -------------------------------------------------------------
        # SIGNAL 2: Manual Workflow Bottlenecks
        # -------------------------------------------------------------
        matched_friction = [p for p in self.MANUAL_WORKFLOW_PATTERNS if p in text_lower]
        if matched_friction:
            snippet = self._extract_context(text, matched_friction[0])
            signals.append(
                NeedSignal(
                    signal_type="operational_bottleneck",
                    description=f"High-friction manual ordering or booking flow detected ('{matched_friction[0]}') without automated self-serve scheduling/purchasing.",
                    source_snippet=snippet,
                    severity=SignalSeverity.HIGH,
                )
            )
            statuses.append("high_friction_booking")

        # -------------------------------------------------------------
        # SIGNAL 3: Stale Presence (Copyright or Dates Older Than 2024)
        # -------------------------------------------------------------
        copyright_match = re.search(r"(?:©|copyright|&copy;|\(c\))\s*(?:20\d\d\s*[-–—/]\s*)?(20[0-2][0-3])", text, re.IGNORECASE)
        if copyright_match:
            year = int(copyright_match.group(1))
            signals.append(
                NeedSignal(
                    signal_type="outdated_presence",
                    description=f"Stale digital presence: Copyright or last updated year ({year}) is older than 2024, indicating neglected web assets.",
                    source_snippet=copyright_match.group(0),
                    severity=SignalSeverity.MEDIUM,
                )
            )
            statuses.append("outdated_content")

        # -------------------------------------------------------------
        # SIGNAL 5: Contact Friction (No Direct Email or WhatsApp Links)
        # -------------------------------------------------------------
        has_direct_email = page_data.get("has_direct_email", True)
        has_direct_wa = page_data.get("has_direct_whatsapp", True)
        has_direct_tel = page_data.get("has_direct_tel", True)

        if not has_direct_email and not has_direct_wa and not has_direct_tel:
            signals.append(
                NeedSignal(
                    signal_type="contact_friction",
                    description="High contact friction: Reaching the business requires high-effort steps (no direct click-to-email, tel, or WhatsApp link found on landing page).",
                    source_snippet="Direct contact triggers absent",
                    severity=SignalSeverity.MEDIUM,
                )
            )
            statuses.append("high_contact_friction")

        # Audit general text snippets for operational bottlenecks or complaints
        text_signals = self.audit_text_snippet(text[:3000])
        signals.extend(text_signals)

        status_str = "_".join(statuses) if statuses else "active_presence"
        return status_str, signals

    def calculate_match_score(
        self,
        signals: list[NeedSignal],
        has_verified_url: bool = True,
        base_score: int = 5
    ) -> int:
        """
        Calculate qualification match score (1 to 10) based on observed signals.
        """
        score = base_score
        if not has_verified_url:
            score -= 2

        for signal in signals:
            if signal.severity == SignalSeverity.CRITICAL:
                score += 3
            elif signal.severity == SignalSeverity.HIGH:
                score += 2
            elif signal.severity == SignalSeverity.MEDIUM:
                score += 1

        return max(1, min(10, score))

    def generate_personalized_hook(
        self,
        prospect_name: str,
        signals: list[NeedSignal],
        client_name: str,
        unique_value_prop: str
    ) -> str:
        """
        Draft a high-relevance, consultative opening hook tailored for Agent 5 (Sales Lead).
        Avoids generic spam; directly anchors on the primary observed friction signal.
        """
        if not signals:
            return (
                f"Hi {prospect_name}, noticed your recent growth initiatives in the space. "
                f"We built {client_name} specifically to solve {unique_value_prop.lower()} — thought this might be relevant to your current pipeline."
            )

        top_signal = max(
            signals,
            key=lambda s: 3 if s.severity == SignalSeverity.CRITICAL else (2 if s.severity == SignalSeverity.HIGH else 1)
        )

        if top_signal.signal_type == "community_inquiry":
            return (
                f"Hi {prospect_name}, saw your question regarding '{top_signal.source_snippet or 'solutions in this space'}'. "
                f"At {client_name}, we help teams address exactly this by {unique_value_prop.lower()}. Happy to share how we solved this without high retainers."
            )
        elif top_signal.signal_type == "operational_bottleneck":
            return (
                f"Hi {prospect_name}, noticed you're managing substantial manual workflows around '{top_signal.source_snippet or 'daily operations'}'. "
                f"We developed {client_name} to eliminate this friction entirely ({unique_value_prop.lower()}). Would love to send a 2-minute breakdown of how."
            )
        elif top_signal.signal_type == "customer_complaint":
            return (
                f"Hi {prospect_name}, saw your feedback regarding frustrations with current tooling ({top_signal.description}). "
                f"{client_name} was engineered specifically to fix those reliability gaps with {unique_value_prop.lower()}. Open to taking a quick look?"
            )
        elif top_signal.signal_type == "outdated_presence":
            return (
                f"Hi {prospect_name}, came across your profile and noticed potential to modernize your customer onboarding flow ({top_signal.description}). "
                f"{client_name} helps automate this end-to-end ({unique_value_prop.lower()}) to unlock higher conversion with zero extra team hours."
            )
        elif top_signal.signal_type == "technical_gap":
            return (
                f"Hi {prospect_name}, noticed technical gaps on your digital portal ({top_signal.description}) that might be causing prospect drop-offs. "
                f"We built {client_name} to give modern businesses seamless, conversion-optimized infrastructure ({unique_value_prop.lower()})."
            )
        elif top_signal.signal_type == "contact_friction":
            return (
                f"Hi {prospect_name}, saw your site is losing potential inquiries due to high contact friction ({top_signal.description}). "
                f"{client_name} automates seamless customer intake ({unique_value_prop.lower()}) so you capture 100% of interested leads."
            )
        elif top_signal.signal_type == "broken_website":
            return (
                f"Hi {prospect_name}, noticed your public web home is currently unreachable ({top_signal.description}). "
                f"{client_name} helps operators establish high-converting digital channels ({unique_value_prop.lower()})."
            )
        else:
            return (
                f"Hi {prospect_name}, noticed your focus on scaling operations. "
                f"We designed {client_name} to assist teams with {unique_value_prop.lower()}."
            )

    def _extract_context(self, full_text: str, keyword: str, window: int = 60) -> str:
        """Extract a snippet of text surrounding a matched keyword."""
        idx = full_text.lower().find(keyword.lower())
        if idx == -1:
            return keyword
        start = max(0, idx - window)
        end = min(len(full_text), idx + len(keyword) + window)
        snippet = full_text[start:end].replace("\n", " ").strip()
        return f"...{snippet}..."
