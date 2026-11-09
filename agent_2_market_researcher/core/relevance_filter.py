"""
Relevance Gate & Prospect Verification Engine
scalyn.si (GrowWithAI Multi-Agent System)

Enforces the 7/10 Relevancy Guardrail:
"Is [Entity Name] with URL [URL] a plausible buyer, prospect, or relevant community
for [Startup Name] which sells [Product]? Rate 1-10. If score < 7, REJECT."

Zero junk, zero irrelevant directory entries, zero unrelated domains.
Supports LLM evaluation (Gemini / OpenAI) with high-accuracy semantic fallback.
"""

import json
import logging
import os
import re
import urllib.parse
from typing import Optional
from .schemas import ClientBrief

logger = logging.getLogger("RelevanceFilter")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [RelevanceGate]: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class RelevanceFilter:
    """
    Evaluates discovered prospects against the client startup's ICP and UVP.
    Enforces a strict 7/10 minimum score threshold before allowing prospect inclusion.
    """

    MIN_ACCEPTABLE_SCORE = 7

    def __init__(self):
        self.gemini_key = os.environ.get("GEMINI_API_KEY")

    def evaluate(
        self,
        entity_name: str,
        url: str,
        snippet: str,
        brief: ClientBrief,
    ) -> tuple[bool, int, str]:
        """
        Evaluate if entity is a plausible buyer, target prospect, or relevant community.
        Returns: (is_qualified: bool, score: int, rationale: str)
        """
        # 1. First-pass rule rejection (blacklisted or obviously irrelevant domains)
        netloc = urllib.parse.urlparse(url).netloc.lower()
        if any(b in netloc for b in [
            "britannica.com", "wikipedia.org", "tripadvisor.com", "dictionary",
            "thesaurus", "merriam-webster", "pinterest", "whatsapp.com", "google.com", "bing.com"
        ]):
            return False, 2, f"Disallowed domain: {netloc} is an encyclopedia, directory, or search engine."

        # 2. Try LLM Evaluation if API key exists
        if self.gemini_key:
            llm_res = self._evaluate_with_llm(entity_name, url, snippet, brief)
            if llm_res is not None:
                passed = llm_res[0] >= self.MIN_ACCEPTABLE_SCORE
                return passed, llm_res[0], llm_res[1]

        # 3. Deep Semantic ICP Evaluation Engine
        return self._semantic_scoring(entity_name, url, snippet, brief)

    def _evaluate_with_llm(
        self,
        entity_name: str,
        url: str,
        snippet: str,
        brief: ClientBrief
    ) -> Optional[tuple[int, str]]:
        """Query Gemini API for 1-10 relevance rating."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = f"""
You are a strict B2B Sales Prospect Qualification Auditor.
Evaluate whether this discovered search entity is a plausible buyer, qualified lead, or relevant practitioner community for the client startup.

Client Startup: {brief.startup_name}
What it Sells: {brief.product_service_description}
Unique Value Prop: {brief.unique_value_proposition}
Target Industry: {brief.industry}
Target Buyer Personas: {', '.join(brief.target_buyer_personas or ['Decision Makers'])}

Discovered Prospect:
- Entity / Title: {entity_name}
- Target URL: {url}
- Observed Snippet: {snippet}

Question: Is "{entity_name}" with URL "{url}" a plausible buyer, prospect, or relevant community for {brief.startup_name}?
Rate strictly 1-10. If score < 7, it is REJECTED.

Return strictly JSON in this format:
{{
  "score": <integer from 1 to 10>,
  "reasoning": "<1-2 sentences explaining why this fits or does not fit the ICP>"
}}
"""
            resp = model.generate_content(prompt)
            clean_json = re.sub(r"^```json\s*|\s*```$", "", resp.text.strip())
            data = json.loads(clean_json)
            score = int(data.get("score", 5))
            reasoning = data.get("reasoning", "LLM evaluation")
            return score, reasoning
        except Exception as e:
            logger.debug(f"LLM gate error: {e}. Falling back to semantic scoring engine.")
            return None

    def _semantic_scoring(
        self,
        entity_name: str,
        url: str,
        snippet: str,
        brief: ClientBrief
    ) -> tuple[bool, int, str]:
        """
        High-precision semantic scoring based on keyword alignment,
        buyer intent markers, competitor comparisons, and persona fit.
        """
        combined = f"{entity_name} {url} {snippet}".lower()
        score = 5
        positive_factors = []
        negative_factors = []

        # Check for persona alignment
        if brief.target_buyer_personas:
            for persona in brief.target_buyer_personas:
                p_terms = [w.lower() for w in re.findall(r"\b[A-Za-z]{4,}\b", persona) if w.lower() not in ["teams", "with", "from", "data"]]
                if any(pt in combined for pt in p_terms):
                    score += 2
                    positive_factors.append(f"matches target persona '{persona}'")
                    break

        # Check for industry domain terminology
        niche_terms = [w.lower() for w in re.findall(r"\b[A-Za-z]{4,}\b", brief.industry) if w.lower() not in ["software", "technology", "services"]]
        if any(nt in combined for nt in niche_terms):
            score += 2
            positive_factors.append("contains core industry terminology")

        # Specific domain boosts (e.g. meta-analysis, clinical research, Covidence, PRISMA)
        if any(w in (brief.industry + " " + brief.unique_value_proposition).lower() for w in ["meta-analysis", "systematic review", "prisma"]):
            domain_signals = [
                "meta-analysis", "systematic review", "prisma", "covidence", "rayyan", "revman",
                "distillersr", "forest plot", "evidence synthesis", "cochrane", "biostatistics",
                "screening", "epidemiology", "literature review", "data extraction"
            ]
            matches = [s for s in domain_signals if s in combined]
            if len(matches) >= 2:
                score += 3
                positive_factors.append(f"mentions high-intent signals: {', '.join(matches[:3])}")
            elif len(matches) == 1:
                score += 1
                positive_factors.append(f"mentions domain signal: {matches[0]}")

        # Check for competitor mentions
        if brief.key_competitors:
            for comp in brief.key_competitors:
                if comp.lower() in combined:
                    score += 2
                    positive_factors.append(f"discusses known competitor '{comp}'")
                    break

        # Check for active community / workflow discussions (e.g. Reddit, discussion forums)
        if "reddit.com" in url.lower():
            if any(w in combined for w in ["recommendation", "alternative", "tool", "software", "struggling", "how to", "experience", "pricing"]):
                score += 1
                positive_factors.append("active practitioner workflow thread on Reddit")

        # Check for negative signals / irrelevance
        if any(bad in combined for bad in [
            "hotel", "flight", "tourism", "recipe", "gaming", "movie", "celebrity",
            "weather", "horoscope", "definition", "pronunciation"
        ]):
            score -= 4
            negative_factors.append("contains unrelated consumer topics")

        # Cap score between 1 and 10
        score = max(1, min(10, score))
        passed = score >= self.MIN_ACCEPTABLE_SCORE

        if passed:
            reason = f"Qualified ICP Fit ({score}/10): {'; '.join(positive_factors)}."
        else:
            reason = f"Rejected (< 7/10, scored {score}/10): Insufficient ICP signal alignment."

        return passed, score, reason
