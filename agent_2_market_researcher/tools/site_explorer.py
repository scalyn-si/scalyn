"""
Startup Website Explorer & Brief Extractor
Autonomously crawls and extracts core business intelligence from ANY startup website URL.
Extracts: Startup Name, Value Proposition, Business Model, Industry, Location, Offerings.
Converts any live website URL into a structured ClientBrief for Agent 2 market scouting.
"""

import logging
import re
import urllib.parse
from typing import Any, Optional
import requests
from bs4 import BeautifulSoup

from ..core.schemas import BusinessModelType, ClientBrief

logger = logging.getLogger("SiteExplorer")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [SiteExplorer]: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class StartupSiteExplorer:
    """
    Crawls a startup's public website and extracts its positioning, value proposition,
    industry vertical, and business model to auto-generate a target market research brief.
    """

    def __init__(self, user_agent: Optional[str] = None, timeout: int = 12):
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36 (scalyn.si-SiteScout/1.0)"
        )
        self.timeout = timeout

    def explore_url(self, raw_url: str) -> dict[str, Any]:
        """
        Fetch and parse public HTML from raw_url, extracting structured business signals.
        """
        url = raw_url.strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        logger.info(f"Initiating autonomous web exploration for startup URL: {url}")

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            resp = requests.get(url, headers=headers, timeout=self.timeout, allow_redirects=True)
            html_text = resp.text
            final_url = resp.url
        except Exception as e:
            logger.warning(f"Live fetch failed for {url} ({e}). Generating domain-inferred profile.")
            return self._fallback_inferred_profile(url, error=str(e))

        soup = BeautifulSoup(html_text, "html.parser")

        # 1. Extract OpenGraph & Meta Data
        og_title = self._get_meta(soup, "property", "og:title")
        og_desc = self._get_meta(soup, "property", "og:description")
        og_site_name = self._get_meta(soup, "property", "og:site_name")
        meta_desc = self._get_meta(soup, "name", "description")

        raw_title = soup.title.string.strip() if (soup.title and soup.title.string) else ""
        
        # 2. Extract Headings (H1, H2) for Core Value Props
        h1_tags = [h.get_text(strip=True) for h in soup.find_all("h1") if h.get_text(strip=True)]
        h2_tags = [h.get_text(strip=True) for h in soup.find_all("h2") if h.get_text(strip=True)]

        # 3. Clean Text & Content Analysis
        for script_or_style in soup(["script", "style", "noscript", "svg"]):
            script_or_style.decompose()

        all_text = " ".join(soup.stripped_strings)
        text_sample = all_text[:8000].lower()

        # 4. Infer Startup Name
        domain = urllib.parse.urlparse(final_url).netloc
        domain_name = re.sub(r"^(www\.)?", "", domain).split(".")[0].capitalize()

        startup_name = og_site_name or domain_name
        if raw_title:
            # Common patterns: "Startup Name | Tagline" or "Startup Name - Subtitle"
            parts = re.split(r"[\-|–|—|•|:]", raw_title)
            if parts and len(parts[0].strip()) > 1:
                candidate = parts[0].strip()
                if len(candidate) <= 30:
                    startup_name = candidate

        # 5. Infer Business Model
        b2b_score = 0
        b2c_score = 0

        b2b_keywords = [
            "enterprise", "b2b", "teams", "api", "dashboard", "compliance", "saas",
            "organizations", "roi", "book a demo", "schedule demo", "request demo",
            "retainer", "agencies", "integrations", "workflows", "clients"
        ]
        b2c_keywords = [
            "students", "parents", "tuition", "classes", "patient", "patients",
            "cakes", "bakery", "shop now", "order now", "cart", "checkout", "menu",
            "delicious", "lifestyle", "app for ios", "fitness", "workout", "workout plans"
        ]

        for kw in b2b_keywords:
            if kw in text_sample:
                b2b_score += 1
        for kw in b2c_keywords:
            if kw in text_sample:
                b2c_score += 1

        business_model = BusinessModelType.B2B if b2b_score >= b2c_score else BusinessModelType.B2C

        # 6. Infer Industry Vertical
        industry = self._detect_industry(text_sample, raw_title + " " + (og_desc or meta_desc or ""))

        # 7. Formulate Value Proposition & Description
        description = og_desc or meta_desc
        if not description and h1_tags:
            description = h1_tags[0]
            if len(h1_tags) > 1:
                description += ". " + h1_tags[1]
        if not description:
            description = f"Autonomous solutions and specialized services provided by {startup_name}."

        uvp = ""
        if h1_tags:
            uvp = h1_tags[0]
        elif h2_tags:
            uvp = h2_tags[0]
        else:
            uvp = description

        # 8. Detect Location Clues (Pakistan / US / UK / Global)
        region = self._detect_location(text_sample, all_text)

        # 9. Inferred Pricing / Goal
        pricing = "Custom Pricing / Inquire for Rates"
        if "free trial" in text_sample:
            pricing = "Freemium / Free Trial Available"
        elif "monthly" in text_sample or "/mo" in text_sample or "per month" in text_sample:
            pricing = "Monthly Subscription"
        elif "retainer" in text_sample:
            pricing = "Monthly Retainer"
        elif "pkr" in text_sample or "rs." in text_sample:
            pricing = "Local Currency Pricing (PKR)"

        goal = f"Acquire high-intent {business_model.value} clients and upscale brand visibility"

        return {
            "status": "success",
            "url": final_url,
            "startup_name": startup_name,
            "business_model": business_model.value,
            "industry": industry,
            "target_city_region": region,
            "product_service_description": description[:300],
            "unique_value_proposition": uvp[:200],
            "primary_goal": goal,
            "pricing_model": pricing,
            "extracted_meta": {
                "title": raw_title,
                "meta_description": meta_desc,
                "og_title": og_title,
                "og_description": og_desc,
                "h1_tags": h1_tags[:3],
                "h2_tags": h2_tags[:3],
            }
        }

    def convert_to_client_brief(self, raw_url: str) -> ClientBrief:
        """
        Explores the URL and returns a validated Pydantic ClientBrief ready for Agent 2 scouting.
        """
        data = self.explore_url(raw_url)
        model_str = data.get("business_model", "B2B")
        model_enum = BusinessModelType.B2B if model_str == "B2B" else BusinessModelType.B2C

        return ClientBrief(
            startup_name=data.get("startup_name", "My Startup"),
            industry=data.get("industry", "Technology & Digital Services"),
            business_model=model_enum,
            product_service_description=data.get("product_service_description", "Specialized products and services."),
            unique_value_proposition=data.get("unique_value_proposition", "High impact value proposition."),
            target_city_region=data.get("target_city_region", "Global / Remote"),
            primary_goal=data.get("primary_goal", "Acquire qualified leads and expand market reach"),
            pricing_model=data.get("pricing_model", "Custom Pricing"),
            notes_from_agent_1=f"Brief auto-extracted from live website exploration: {raw_url}"
        )

    def _get_meta(self, soup: BeautifulSoup, attr_name: str, attr_val: str) -> str:
        tag = soup.find("meta", attrs={attr_name: attr_val})
        if tag and tag.get("content"):
            return tag["content"].strip()
        return ""

    def _detect_industry(self, text: str, meta_str: str) -> str:
        combined = (text + " " + meta_str).lower()
        if any(w in combined for w in ["fitness", "workout", "coaching", "gym", "health", "nutrition", "athlete"]):
            return "Health & Fitness Technology"
        elif any(w in combined for w in ["tuition", "academy", "cambridge", "o level", "a level", "tutoring", "education"]):
            return "Education & Academic Coaching"
        elif any(w in combined for w in ["saas", "kubernetes", "cloud", "api", "analytics", "software", "devops"]):
            return "B2B SaaS / Developer Tools"
        elif any(w in combined for w in ["dental", "clinic", "cosmetic", "patients", "healthcare", "dentist"]):
            return "Healthcare & Dental Practice"
        elif any(w in combined for w in ["bakery", "cake", "pastry", "sourdough", "confectionery", "cookies"]):
            return "Artisan Food & Confectionery"
        elif any(w in combined for w in ["marketing", "seo", "agency", "advertising", "growth", "leads"]):
            return "Digital Growth & Marketing Agency"
        elif any(w in combined for w in ["ecommerce", "fashion", "apparel", "clothing", "wear"]):
            return "E-Commerce & Retail Fashion"
        elif any(w in combined for w in ["real estate", "property", "realtor", "apartments"]):
            return "Real Estate & Property Management"
        return "Digital Innovation & Online Services"

    def _detect_location(self, text: str, full_text: str) -> str:
        combined = (text + " " + full_text).lower()
        
        # Pakistan markers
        if any(w in combined for w in ["islamabad", "rawalpindi", "lahore", "karachi", "peshawar", "pakistan", "+92", "pkr"]):
            if "islamabad" in combined or "rawalpindi" in combined:
                return "Islamabad & Rawalpindi, Pakistan"
            elif "lahore" in combined:
                return "Lahore, Pakistan"
            elif "karachi" in combined:
                return "Karachi, Pakistan"
            return "Pakistan (Major Metros)"

        # US / UK markers
        if any(w in combined for w in ["california", "new york", "texas", "austin", "usa", "san francisco", "+1 "]):
            return "United States (National / Target Metros)"
        if any(w in combined for w in ["london", "manchester", "uk", "+44"]):
            return "United Kingdom & Europe"

        return "Global / Remote & English-Speaking Markets"

    def _fallback_inferred_profile(self, url: str, error: str = "") -> dict[str, Any]:
        """Infers reasonable defaults when the URL cannot be fetched directly."""
        domain = urllib.parse.urlparse(url).netloc or url
        clean_name = re.sub(r"^(www\.)?", "", domain).split(".")[0].capitalize()
        return {
            "status": "partial",
            "url": url,
            "startup_name": clean_name or "Personal Startup",
            "business_model": "B2B",
            "industry": "Digital Products & Services",
            "target_city_region": "Global / Remote",
            "product_service_description": f"Online startup offering specialized solutions at {url}.",
            "unique_value_proposition": f"Cutting-edge digital solutions provided by {clean_name}.",
            "primary_goal": "Scale customer acquisition and discover high-intent decision-makers",
            "pricing_model": "Custom / Tiered Pricing",
            "notes": f"Fallback inferred from domain. Fetch notice: {error}",
            "extracted_meta": {}
        }
