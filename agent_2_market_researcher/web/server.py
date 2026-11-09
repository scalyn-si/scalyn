"""
Visual Interactive Web Server for Agent 2: Target Market Researcher
scalyn.si (GrowWithAI Multi-Agent Collective)

Serves the interactive dashboard, manages live research runs,
exposes lead database APIs, and provides master Excel downloads.
Uses Python standard library ThreadingHTTPServer for zero-dependency reliability.
"""

import json
import logging
import mimetypes
import os
import sys
import threading
import urllib.parse
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

# Ensure project paths are available
CURRENT_DIR = Path(__file__).resolve().parent
MODULE_DIR = CURRENT_DIR.parent
PROJECT_ROOT = MODULE_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent_2_market_researcher.config.settings import settings
from agent_2_market_researcher.core.schemas import BusinessModelType, ClientBrief
from agent_2_market_researcher.core.researcher_agent import TargetMarketResearcherAgent
from agent_2_market_researcher.tools.excel_manager import MasterExcelManager
from agent_2_market_researcher.tools.site_ingestor import SemanticSiteIngestor
from agent_2_market_researcher.run_agent import SAMPLE_BRIEFS

logger = logging.getLogger("VisualWebServer")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [WebStudio]: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Global in-memory log buffer for live terminal display
MAX_LOG_HISTORY = 100
live_terminal_logs: list[dict[str, Any]] = []


def add_terminal_log(message: str, level: str = "INFO", stage: str = "general"):
    """Record a timestamped log entry for the visual dashboard."""
    entry = {
        "timestamp": datetime_str(),
        "level": level,
        "stage": stage,
        "message": message,
    }
    live_terminal_logs.append(entry)
    if len(live_terminal_logs) > MAX_LOG_HISTORY:
        live_terminal_logs.pop(0)


def datetime_str() -> str:
    from datetime import datetime
    return datetime.utcnow().strftime("%H:%M:%S")


class LiveProgressHandler(logging.Handler):
    """Forward real crawler and scout activity to the dashboard's log endpoint."""

    def emit(self, record):
        stages = {
            "SemanticSiteIngestor": "site_ingestor",
            "AgentReachTool": "omnichannel_scout",
            "TargetMarketResearcher": "query_planner",
            "RelevanceFilter": "signal_auditor",
        }
        add_terminal_log(record.getMessage(), record.levelname, stages.get(record.name, "general"))


progress_handler = LiveProgressHandler()
for progress_logger in ("SemanticSiteIngestor", "AgentReachTool", "TargetMarketResearcher", "RelevanceFilter"):
    logging.getLogger(progress_logger).addHandler(progress_handler)


class DashboardAPIHandler(SimpleHTTPRequestHandler):
    """Handles visual studio API requests and serves static frontend assets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(CURRENT_DIR), **kwargs)

    def do_HEAD(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path == "/api/download-excel":
            excel_mgr = MasterExcelManager()
            if excel_mgr.filepath.exists():
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                self.send_header("Content-Disposition", 'attachment; filename="master_lead_database.xlsx"')
                self.send_header("Content-Length", str(excel_mgr.filepath.stat().st_size))
                self.end_headers()
                return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ["/", "/index.html"]:
            self._serve_file(CURRENT_DIR / "index.html", "text/html; charset=utf-8")
        elif path in ["/dashboard", "/dashboard.html"]:
            self._serve_file(CURRENT_DIR / "dashboard.html", "text/html; charset=utf-8")
        elif path == "/api/leads":
            self._handle_get_leads()
        elif path == "/api/presets":
            self._handle_get_presets()
        elif path == "/api/history":
            self._handle_get_history()
        elif path == "/api/download-excel":
            self._handle_download_excel()
        elif path == "/api/logs":
            self._handle_get_logs()
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/run-research":
            self._handle_run_research()
        elif path == "/api/analyze-website":
            self._handle_analyze_website()
        elif path == "/api/clear-leads":
            self._handle_clear_leads()
        else:
            self._send_json({"error": "Endpoint not found"}, status=HTTPStatus.NOT_FOUND)

    def _handle_clear_leads(self):
        """Reset master lead database and run history."""
        try:
            excel_mgr = MasterExcelManager()
            excel_mgr.clear_database()
            add_terminal_log("Master lead database cleared and reset to pristine state.", "SUCCESS", "excel_sync")
            self._send_json({"status": "success", "message": "Master lead database reset."})
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_analyze_website(self):
        """Crawl and inspect a startup website URL, extracting a structured ClientBrief."""
        try:
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len)
            payload = json.loads(body.decode("utf-8")) if body else {}
            url = payload.get("url", "").strip()

            if not url:
                self._send_json({"error": "No URL provided."}, status=HTTPStatus.BAD_REQUEST)
                return

            add_terminal_log(f"[SiteIngestor] Crawling and inspecting startup URL: {url}", "INFO", "site_ingestor")
            ingestor = SemanticSiteIngestor()
            profile = ingestor.ingest(url)

            add_terminal_log(
                f"[SiteIngestor] Extracted Profile: '{profile.startup_name}' | Vertical: {profile.industry_vertical} | Scope: {profile.geographic_scope}",
                "SUCCESS",
                "site_ingestor",
            )
            add_terminal_log(
                f"[SiteIngestor] Core UVP: '{profile.core_value_prop}'",
                "SUCCESS",
                "site_ingestor",
            )

            profile_dict = {
                "startup_name": profile.startup_name,
                "industry": profile.industry_vertical,
                "industry_vertical": profile.industry_vertical,
                "geographic_scope": profile.geographic_scope,
                "target_buyer_personas": profile.target_buyer_personas,
                "known_competitors": profile.known_competitors,
                "unique_value_proposition": profile.core_value_prop,
                "core_value_prop": profile.core_value_prop,
                "product_service_description": profile.product_service_description,
                "business_model": profile.business_model.value,
                "target_city_region": profile.target_city_region,
                "primary_goal": profile.primary_goal,
                "pricing_model": profile.pricing_model,
            }

            self._send_json({"status": "success", "profile": profile_dict})
        except ValueError as e:
            add_terminal_log(str(e), "ERROR", "site_ingestor")
            self._send_json({"status": "error", "message": str(e)}, status=HTTPStatus.UNPROCESSABLE_ENTITY)
        except Exception as e:
            logger.error(f"Error exploring website: {e}")
            self._send_json({"status": "error", "message": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_get_leads(self):
        """Return all leads from the master Excel sheet."""
        excel_mgr = MasterExcelManager()
        leads = excel_mgr.get_all_leads()
        self._send_json({
            "status": "success",
            "total_count": len(leads),
            "leads": leads,
        })

    def _handle_get_presets(self):
        """Return predefined sample briefs for one-click intake."""
        presets_data = {}
        for key, brief in SAMPLE_BRIEFS.items():
            presets_data[key] = {
                "startup_name": brief.startup_name,
                "industry": brief.industry,
                "business_model": brief.business_model.value if brief.business_model else "B2B",
                "product_service_description": brief.product_service_description,
                "unique_value_proposition": brief.unique_value_proposition,
                "target_city_region": brief.target_city_region,
                "primary_goal": brief.primary_goal,
                "budget": brief.budget,
                "pricing_model": brief.pricing_model,
                "key_competitors": brief.key_competitors,
                "notes_from_agent_1": brief.notes_from_agent_1,
            }
        self._send_json(presets_data)

    def _handle_get_history(self):
        """Return run history logs from Master Excel."""
        excel_mgr = MasterExcelManager()
        history = excel_mgr.get_run_history()
        self._send_json({"status": "success", "history": history})

    def _handle_get_logs(self):
        """Return recent terminal log entries."""
        self._send_json({"status": "success", "logs": live_terminal_logs})

    def _handle_download_excel(self):
        """Stream the Master Excel workbook as a downloadable binary attachment."""
        excel_mgr = MasterExcelManager()
        filepath = excel_mgr.filepath
        if not filepath.exists():
            self._send_json({"error": "Master Excel database not yet created."}, status=HTTPStatus.NOT_FOUND)
            return

        with open(filepath, "rb") as f:
            content = f.read()

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.send_header("Content-Disposition", 'attachment; filename="master_lead_database.xlsx"')
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(content)

    def _handle_run_research(self):
        """Execute Agent 2 research run with live progress instrumentation."""
        try:
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len)
            payload = json.loads(body.decode("utf-8")) if body else {}

            # Determine client brief (URL exploration, preset, or custom input)
            target_url = (payload.get("url") or "").strip()
            preset_key = payload.get("preset")

            if target_url:
                add_terminal_log(f"Autonomously ingesting startup website: '{target_url}'", "INFO", "site_ingestor")
                ingestor = SemanticSiteIngestor()
                brief = ingestor.convert_to_client_brief(target_url)
                add_terminal_log(
                    f"Profile Ingested: '{brief.startup_name}' | Vertical: {brief.industry} | Scope: {brief.geographic_scope}",
                    "SUCCESS",
                    "site_ingestor",
                )
            elif preset_key and preset_key in SAMPLE_BRIEFS:
                brief = SAMPLE_BRIEFS[preset_key]
                add_terminal_log(f"Loaded preset brief: '{brief.startup_name}' ({preset_key})", "INFO", "intake")
            else:
                brief = ClientBrief(
                    startup_name=payload.get("startup_name", "Innovative Startup"),
                    industry=payload.get("industry", "Technology Services"),
                    business_model=BusinessModelType(payload.get("business_model", "B2B")),
                    product_service_description=payload.get("product_service_description", "High efficiency AI and workflow automation services."),
                    unique_value_proposition=payload.get("unique_value_proposition", "Delivers 3x faster execution with transparent ROI."),
                    target_city_region=payload.get("target_city_region", "Global / Remote"),
                    primary_goal=payload.get("primary_goal", "Acquire initial 25 paying pilot accounts"),
                    budget=payload.get("budget", "Bootstrapped / Low Budget"),
                    pricing_model=payload.get("pricing_model"),
                    key_competitors=payload.get("key_competitors", []),
                    notes_from_agent_1=payload.get("notes_from_agent_1"),
                    geographic_scope=payload.get("geographic_scope", "GLOBAL"),
                    target_buyer_personas=payload.get("target_buyer_personas", []),
                )
                add_terminal_log(f"Custom brief submitted: '{brief.startup_name}'", "INFO", "intake")

            # Instrument agent execution with stage logging
            add_terminal_log(f"[Node 1: Query Planner] Synthesizing Boolean and intent queries for {brief.startup_name}...", "INFO", "query_planner")
            
            agent = TargetMarketResearcherAgent()
            
            # Execute end-to-end reasoning loop
            dossier = agent.run(brief)

            # Record logs for queries
            for q in dossier.generated_query_plan[:4]:
                add_terminal_log(f"[Query Built] [{q.get('target_platform','').upper()}] {q.get('query','')}", "SUCCESS", "omnichannel_scout")

            add_terminal_log(f"[Node 2: Omnichannel Scout] Scouted live platforms. Found {len(dossier.discovered_prospects)} candidates.", "INFO", "omnichannel_scout")
            add_terminal_log(f"[Node 3: Signal Auditor] Audited technical gaps, manual friction & contact blockers.", "INFO", "signal_auditor")
            add_terminal_log(f"[Node 4: Excel Sync] Synchronized qualified leads into Master Excel Database.", "SUCCESS", "excel_sync")

            # Fetch fresh master stats
            excel_mgr = MasterExcelManager()
            leads = excel_mgr.get_all_leads()

            response_data = {
                "status": "success",
                "dossier_id": dossier.dossier_id,
                "startup_name": brief.startup_name,
                "industry": brief.industry,
                "business_model": dossier.business_model_classification,
                "discovered_count": len(dossier.discovered_prospects),
                "total_in_master_db": len(leads),
                "query_count": len(dossier.generated_query_plan),
                "icp_summary": dossier.ideal_customer_profile.target_category,
                "top_personas": [p.persona_name for p in dossier.buyer_personas],
                "prospects": [p.model_dump(mode="json") for p in dossier.discovered_prospects[:6]],
                "recent_logs": live_terminal_logs[-8:],
            }

            self._send_json(response_data)

        except Exception as e:
            logger.error(f"Error running market research: {e}", exc_info=True)
            add_terminal_log(f"Execution Error: {str(e)}", "ERROR", "error")
            self._send_json({"status": "error", "message": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _serve_file(self, filepath: Path, content_type: str):
        """Serve a static file with appropriate headers."""
        if not filepath.exists():
            self._send_json({"error": "File not found"}, status=HTTPStatus.NOT_FOUND)
            return
        with open(filepath, "rb") as f:
            data = f.read()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, data: Any, status: HTTPStatus = HTTPStatus.OK):
        """Helper to send JSON response."""
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        """Suppress noisy default request logging from console."""
        pass


def run_web_server(host: str = "127.0.0.1", port: int = 8000, block: bool = True):
    """Run the threaded dashboard web server."""
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, DashboardAPIHandler)
    logger.info(f"scalyn.si Agent 2 Studio Web Server running at: http://{host}:{port}/")
    print(f"\n" + "=" * 70)
    print(f"🚀 scalyn.si · AGENT 2 VISUAL STUDIO IS LIVE")
    print(f"   URL: http://{host}:{port}/")
    print(f"   Master Database: scalyn.si/agent_2_market_researcher/output/master_lead_database.xlsx")
    print("=" * 70 + "\n")

    if block:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Shutting down web server...")
            httpd.server_close()
    else:
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        return httpd


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    run_web_server(host="127.0.0.1", port=port, block=True)
