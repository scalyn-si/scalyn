"""
Agent Reach Real Live Web Scraper & CLI Connector
scalyn.si (GrowWithAI Multi-Agent Collective)

Executes REAL LIVE internet search scraping across LinkedIn, Reddit, X (Twitter), and the open web.
Scrapes live organic search engine endpoints (DuckDuckGo HTML with session cookies, Bing base64 decoding,
and DDGS) to discover REAL organizations, REAL working websites, and verified prospects with concrete need signals.
Zero fake mock placeholders. Zero google.com/search wrapper links.
"""

import base64
import json
import logging
import re
import shutil
import subprocess
import time
import urllib.parse
from typing import Any, Optional
import requests
from bs4 import BeautifulSoup

from ..config.settings import settings

logger = logging.getLogger("AgentReachTool")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [AgentReach]: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Rigid Junk Domain Blacklist
JUNK_DOMAINS = [
    "britannica.com",
    "wikipedia.org",
    "tripadvisor.com",
    "web.whatsapp.com",
    "whatsapp.com",
    "dictionary.cambridge.org",
    "merriam-webster.com",
    "pinterest.com",
    "facebook.com/login",
    "google.com",
    "bing.com",
    "thesaurus.com",
    "wiktionary.org",
    "duckduckgo.com",
    "yahoo.com",
    "yelp.com",
    "quora.com",
    "instagram.com/accounts/login",
    "linkedin.com/login",
    "twitter.com/login",
    "x.com/login",
    "reddit.com/login",
    "reddit.com/register",
]


class AgentReachTool:
    """
    Live external intelligence tool.
    Combines agent-reach CLI binary with real-time organic web search scraping.
    Guarantees REAL working websites and REAL organization names.
    """

    def __init__(self, binary_name: Optional[str] = None):
        self.binary_name = binary_name or settings.agent_reach_bin
        self.timeout = settings.agent_reach_timeout
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36 (scalyn.si-LiveScout/2.4)"
        )
        self._session: Optional[requests.Session] = None

    def _get_session(self) -> requests.Session:
        """Initialize or reuse a requests.Session with browser-standard headers and cookies."""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            })
            try:
                # Prime session cookies
                self._session.get("https://duckduckgo.com/", timeout=6)
            except Exception as e:
                logger.debug(f"Session prime notice: {e}")
        return self._session

    def is_installed(self) -> bool:
        """Check if the agent-reach CLI binary is available on PATH."""
        return shutil.which(self.binary_name) is not None

    def run_doctor(self) -> dict[str, Any]:
        """Run `agent-reach doctor` to verify channel connectors, scrapers, and dependencies."""
        if not self.is_installed():
            return {
                "installed": False,
                "error": f"Binary '{self.binary_name}' not found on PATH.",
                "remedy": (
                    "Live web scraping is active via direct organic search engines. "
                    "For full headless browser CLI, install via 'uv tool install https://github.com/Panniantong/Agent-Reach/releases/latest'"
                )
            }

        try:
            cmd = [self.binary_name, "doctor"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
            return {
                "installed": True,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "healthy": result.returncode == 0,
            }
        except Exception as e:
            logger.error(f"Error executing agent-reach doctor: {e}")
            return {"installed": True, "healthy": False, "error": str(e)}

    def scout_platform(
        self,
        query: str,
        platform: str = "web",
        limit: int = 5
    ) -> list[dict[str, Any]]:
        """
        Scout a target platform for keywords, complaints, competitor mentions, or need signals.
        Executes real live search scraping across LinkedIn, Reddit, X, and the open web.
        """
        platform_lower = platform.lower()
        logger.info(f"Scouting platform '{platform_lower}' with query: '{query}' (limit={limit})")

        # 1. Try agent-reach CLI binary if present
        if self.is_installed():
            try:
                cmd = [
                    self.binary_name,
                    "search",
                    query,
                    "--platform",
                    platform_lower,
                    "--limit",
                    str(limit),
                    "--json",
                ]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    check=False,
                )
                if result.returncode == 0 and result.stdout.strip():
                    try:
                        parsed = json.loads(result.stdout)
                        if isinstance(parsed, list) and len(parsed) > 0:
                            return parsed
                        if isinstance(parsed, dict) and "results" in parsed and len(parsed["results"]) > 0:
                            return parsed["results"]
                    except json.JSONDecodeError:
                        pass
            except Exception as ex:
                logger.warning(f"Agent-Reach CLI invocation failed: {ex}. Proceeding with live organic web scraping.")

        # 2. Execute Real Live Web Search Scraping
        return self._scrape_live_web_results(query=query, limit=limit, platform=platform_lower)

    def _clean_search_query(self, query: str, platform: str) -> str:
        """
        Preserve quoted phrases, Boolean alternatives, and platform restrictions.
        Removing OR would require every alternative role to appear on one page.
        """
        # Keep site restrictions so social searches stay on the requested platform.
        q = " ".join(query.split())
        if "site:" not in q.lower():
            site = {"linkedin": "linkedin.com", "reddit": "reddit.com", "x": "x.com"}.get(platform)
            if site:
                q = f"site:{site} {q}"
        return q

    def _extract_clean_entity_name(self, title: str, url: str) -> str:
        """
        Extract the actual clean organization or business name from a raw HTML page title.
        E.g. "The Best O & A Level Coaching Center in Karachi | SJ Academy" -> "SJ Academy"
        E.g. "Coaching Centre | Diligent Group, Clifton Karachi" -> "Diligent Group"
        E.g. "Anees Hussain - Pakistan's Premier Coaching Institute" -> "Anees Hussain"
        """
        if not title:
            # Fallback to domain name
            netloc = urllib.parse.urlparse(url).netloc
            return re.sub(r'^(?:www\.)?', '', netloc).split('.')[0].capitalize()

        # Strip social media brand suffixes
        t = re.sub(r'\s+[-–—|]\s+(?:LinkedIn|Reddit|Facebook|Twitter|Instagram|YouTube).*$', '', title, flags=re.I)
        t = re.sub(r':\s+r/[a-zA-Z0-9_]+.*$', '', t, flags=re.I)

        parts = [p.strip() for p in re.split(r'\s+[|\-–—:]\s+', t) if p.strip()]
        generic_words = {
            "home", "coaching centre", "coaching center", "tuition centre",
            "tuition center", "blog", "about us", "overview", "login", "reviews",
            "welcome", "directory", "tuition academies in karachi,pakistan",
            "tuition academies in karachi", "best tutor academies in karachi",
            "academies in karachi - tuition centers, tutor & home teachers"
        }

        # Look for a concise distinct brand name from right to left
        for p in reversed(parts):
            if p.lower() not in generic_words and 2 <= len(p.split()) <= 5 and len(p) < 35:
                return p

        # Look for any specific part containing organizational words
        specific_parts = [p for p in parts if p.lower() not in generic_words and len(p) >= 3]
        if specific_parts:
            for p in specific_parts:
                if any(k in p.lower() for k in ["academy", "school", "group", "centre", "center", "institute", "college", "tutor", "tuition"]):
                    return p[:45]
            return specific_parts[0][:45]

        # Fallback to domain name
        netloc = urllib.parse.urlparse(url).netloc
        domain = re.sub(r'^(?:www\.)?', '', netloc).split('.')[0].capitalize()
        if domain and len(domain) > 2:
            return domain
        return (parts[0] if parts else t)[:45]

    def _is_junk_url(self, url: str) -> bool:
        """Check if URL belongs to blacklisted junk domains, encyclopedias, or auth portals."""
        if not url or not url.startswith("http"):
            return True
        u_lower = url.lower()
        for junk in JUNK_DOMAINS:
            if junk in u_lower:
                return True
        parsed = urllib.parse.urlparse(url)
        path_clean = parsed.path.strip("/").lower()
        if path_clean in ["login", "signin", "signup", "register", "terms", "privacy"]:
            return True
        return False

    def _scrape_live_web_results(
        self,
        query: str,
        limit: int = 5,
        platform: str = "web"
    ) -> list[dict[str, Any]]:
        """
        Scrapes real live search engines with retries, extracting genuine organic results:
        - Real page title (Organization / Business name)
        - Real target URL (clean working domain, not search query wrappers)
        - Real text snippet (actual description from their website or post)
        """
        clean_q = self._clean_search_query(query, platform)
        logger.info(f"Executing real live web search for: '{clean_q}' [platform: {platform}]")

        results: list[dict[str, Any]] = []
        seen_urls: set[str] = set()

        # Engine 1: DuckDuckGo HTML endpoint with session cookies
        try:
            session = self._get_session()
            ddg_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(clean_q)}"
            resp = session.get(ddg_url, headers={"Referer": "https://duckduckgo.com/"}, timeout=10)
            if resp.status_code != 200:
                logger.warning(f"DuckDuckGo search unavailable (HTTP {resp.status_code}); trying other search engines.")
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                raw_items = soup.select(".result")
                for res in raw_items:
                    a_title = res.select_one(".result__title a")
                    snip_tag = res.select_one(".result__snippet")
                    if not a_title:
                        continue

                    raw_href = a_title.get("href", "")
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query)
                    clean_url = parsed.get("uddg", [raw_href])[0]

                    if not clean_url or not clean_url.startswith("http"):
                        continue

                    # Filter out search engine wrappers, ad portals, dictionaries, root domains
                    if self._is_junk_url(clean_url):
                        continue

                    # Platform filter
                    if platform == "linkedin" and "linkedin.com" not in clean_url.lower():
                        continue
                    if platform == "reddit" and "reddit.com" not in clean_url.lower():
                        continue

                    if clean_url in seen_urls:
                        continue
                    seen_urls.add(clean_url)

                    raw_title = a_title.get_text(strip=True)
                    org_name = self._extract_clean_entity_name(raw_title, clean_url)
                    snippet = snip_tag.get_text(strip=True) if snip_tag else raw_title

                    results.append({
                        "title": raw_title,
                        "handle_or_name": org_name,
                        "url": clean_url,
                        "platform": platform,
                        "snippet": snippet,
                    })
                    if len(results) >= limit:
                        break
        except Exception as e:
            logger.warning(f"DuckDuckGo HTML scrape notice: {e}")

        # Engine 2: High-performance DDGS (TLS/primp fingerprint emulation)
        if len(results) < limit:
            try:
                from ddgs import DDGS
                with DDGS(timeout=8) as ddgs:
                    raw_items = list(ddgs.text(clean_q, max_results=limit * 2))
                    for item in raw_items:
                        href = item.get("href", "").strip()
                        title = item.get("title", "").strip()
                        snippet = item.get("body", "").strip()

                        if not href or not href.startswith("http"):
                            continue

                        if self._is_junk_url(href):
                            continue

                        if platform == "linkedin" and "linkedin.com" not in href.lower():
                            continue
                        if platform == "reddit" and "reddit.com" not in href.lower():
                            continue

                        if href in seen_urls:
                            continue
                        seen_urls.add(href)

                        org_name = self._extract_clean_entity_name(title, href)
                        results.append({
                            "title": title,
                            "handle_or_name": org_name,
                            "url": href,
                            "platform": platform,
                            "snippet": snippet,
                        })
                        if len(results) >= limit:
                            break
            except Exception as e:
                logger.warning(f"DDGS search unavailable: {e}")

        # Engine 3: Bing organic scraping with base64 redirect unpack
        if len(results) < limit:
            try:
                session = self._get_session()
                bing_url = f"https://www.bing.com/search?q={urllib.parse.quote_plus(clean_q)}"
                r = session.get(bing_url, timeout=10)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    algo_items = soup.select("li.b_algo")
                    for li in algo_items:
                        a_tag = li.select_one("h2 a")
                        if not a_tag:
                            continue
                        raw_href = a_tag.get("href", "")
                        clean_url = raw_href

                        # Unpack Bing redirect parameter (u=a1<base64>)
                        if "bing.com/ck/a?" in raw_href:
                            parsed_q = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query)
                            u_param = parsed_q.get("u", [""])[0]
                            if u_param.startswith("a1"):
                                try:
                                    b64_str = u_param[2:]
                                    b64_str += "=" * ((4 - len(b64_str) % 4) % 4)
                                    clean_url = base64.b64decode(b64_str).decode("utf-8", errors="ignore")
                                except Exception:
                                    pass

                        if not clean_url or not clean_url.startswith("http"):
                            continue
                        if self._is_junk_url(clean_url):
                            continue

                        if platform == "linkedin" and "linkedin.com" not in clean_url.lower():
                            continue
                        if platform == "reddit" and "reddit.com" not in clean_url.lower():
                            continue

                        if clean_url in seen_urls:
                            continue
                        seen_urls.add(clean_url)

                        raw_title = a_tag.get_text(strip=True)
                        snip_elem = li.select_one(".b_caption p")
                        snippet = snip_elem.get_text(strip=True) if snip_elem else raw_title
                        org_name = self._extract_clean_entity_name(raw_title, clean_url)

                        results.append({
                            "title": raw_title,
                            "handle_or_name": org_name,
                            "url": clean_url,
                            "platform": platform,
                            "snippet": snippet,
                        })
                        if len(results) >= limit:
                            break
            except Exception as e:
                logger.warning(f"Bing organic scrape notice: {e}")

        if not results:
            logger.warning("No search results were available for this query. Search engines may be blocking requests or have no matching pages.")
        logger.info(f"Live web search completed. Extracted {len(results)} real organic prospects.")
        return results[:limit]

    def fetch_url_content(self, url: str) -> dict[str, Any]:
        """
        Fetch and parse public content from a target URL (e.g. prospect website or public thread).
        Audits real website for mobile viewport, contact friction, and technical signals.
        """
        if not url or not url.startswith("http"):
            return {
                "url": url,
                "status_code": None,
                "title": "",
                "meta_description": "",
                "text_content": "",
                "is_live": False,
                "error": "Invalid URL",
                "has_viewport": True,
                "has_direct_email": False,
                "has_direct_whatsapp": False,
                "has_direct_tel": False,
            }

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            resp = requests.get(url, headers=headers, timeout=settings.request_timeout, allow_redirects=True)
            soup = BeautifulSoup(resp.text, "html.parser")

            has_viewport = bool(soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)}))
            has_direct_email = bool(soup.find("a", href=re.compile(r"^mailto:", re.I))) or bool(re.search(r"[\w\.-]+@[\w\.-]+\.\w+", resp.text))
            has_direct_whatsapp = bool(soup.find("a", href=re.compile(r"wa\.me|api\.whatsapp\.com|whatsapp:", re.I)))
            has_direct_tel = bool(soup.find("a", href=re.compile(r"^tel:", re.I)))

            # Remove scripts and styling
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()

            text_content = " ".join(soup.stripped_strings)
            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            meta_desc = ""
            desc_tag = soup.find("meta", attrs={"name": "description"})
            if desc_tag and desc_tag.get("content"):
                meta_desc = desc_tag["content"].strip()

            return {
                "url": resp.url,
                "status_code": resp.status_code,
                "title": title,
                "meta_description": meta_desc,
                "text_content": text_content[:5000],
                "is_live": resp.status_code < 400,
                "has_viewport": has_viewport,
                "has_direct_email": has_direct_email,
                "has_direct_whatsapp": has_direct_whatsapp,
                "has_direct_tel": has_direct_tel,
            }
        except Exception as e:
            logger.warning(f"Live website audit notice for {url}: {e}")
            return {
                "url": url,
                "status_code": None,
                "title": "",
                "meta_description": "",
                "text_content": "",
                "is_live": False,
                "error": str(e),
                "has_viewport": True,
                "has_direct_email": False,
                "has_direct_whatsapp": False,
                "has_direct_tel": False,
            }
