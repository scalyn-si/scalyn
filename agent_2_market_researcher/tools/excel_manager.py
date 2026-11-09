"""
Master Excel Synchronizer for Agent 2: Target Market Researcher
scalyn.si (GrowWithAI Multi-Agent Collective)

Maintains a SINGLE persistent, styled Excel workbook (`master_lead_database.xlsx`).
Automatically appends qualified prospects across multiple startup runs,
prevents duplicates based on Verified URL and Name/Handle,
and logs execution metrics into a dedicated Run History sheet.
"""

from datetime import datetime
import logging
from pathlib import Path
from typing import Any, Optional

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from ..config.settings import settings
from ..core.schemas import DiscoveredProspect

logger = logging.getLogger("MasterExcelManager")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [ExcelManager]: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Brand Style Colors
COLOR_SKY_BLUE = "0593C6"       # Header background
COLOR_TEXT_WHITE = "FCFFFF"     # Header text
COLOR_HOT_PINK = "D83995"       # High-priority badge
COLOR_ROW_ALT = "F4FAFD"        # Subtle zebra tint
COLOR_BORDER = "D1E9F4"         # Clean soft gridline


class MasterExcelManager:
    """
    Manages the single centralized master Excel database for all discovered leads.
    """

    DEFAULT_FILENAME = "master_lead_database.xlsx"

    LEAD_HEADERS = [
        "Lead ID",
        "Target Startup",
        "Prospect / Organization",
        "Role",
        "Platform",
        "Verified URL",
        "Match Score",
        "Observed Need Signals",
        "Personalized Sales Hook",
        "Status",
        "Discovery Date",
    ]

    HISTORY_HEADERS = [
        "Run Timestamp",
        "Target Startup",
        "Total Discovered",
        "New Leads Appended",
        "Duplicates Skipped",
        "Total In Database",
    ]

    def __init__(self, filepath: Optional[str] = None):
        if filepath:
            self.filepath = Path(filepath)
        else:
            self.filepath = settings.dossier_output_dir / self.DEFAULT_FILENAME
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_workbook_exists()

    def _ensure_workbook_exists(self) -> None:
        """Create and style the workbook if it doesn't already exist."""
        if not self.filepath.exists():
            self.clear_database()

    def clear_database(self) -> None:
        """Clear all lead data and history, resetting workbook to pristine empty styled state."""
        wb = openpyxl.Workbook()
        # Sheet 1: Master Leads
        ws_leads = wb.active
        ws_leads.title = "Master Leads"
        self._apply_header_styling(ws_leads, self.LEAD_HEADERS)

        # Sheet 2: Run History
        ws_history = wb.create_sheet(title="Run History")
        self._apply_header_styling(ws_history, self.HISTORY_HEADERS)

        self._auto_fit_columns(ws_leads)
        self._auto_fit_columns(ws_history)
        wb.save(self.filepath)
        logger.info(f"Initialized pristine empty Master Lead Database at: {self.filepath}")

    def _apply_header_styling(self, ws, headers: list[str]) -> None:
        """Apply Sky Blue brand theme and freeze pane to headers."""
        ws.append(headers)
        ws.freeze_panes = "A2"

        header_font = Font(name="Segoe UI", size=11, bold=True, color=COLOR_TEXT_WHITE)
        header_fill = PatternFill(start_color=COLOR_SKY_BLUE, end_color=COLOR_SKY_BLUE, fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        thin_side = Side(border_style="thin", color=COLOR_BORDER)
        border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = border
            ws.row_dimensions[1].height = 28

    def sync_prospects(
        self,
        startup_name: str,
        prospects: list[DiscoveredProspect]
    ) -> dict[str, int]:
        """
        Synchronize a list of scouted prospects into the master workbook.
        Skips prospects whose verified_url or (name_or_handle + startup) is already recorded.
        Logs metrics into the 'Run History' sheet.
        """
        wb = openpyxl.load_workbook(self.filepath)
        ws_leads = wb["Master Leads"]
        ws_history = wb["Run History"] if "Run History" in wb.sheetnames else wb.create_sheet("Run History")

        # 1. Ingest existing entries to detect duplicates
        existing_urls: set[str] = set()
        existing_names: set[str] = set()
        max_id_num = 0

        for row_idx in range(2, ws_leads.max_row + 1):
            lead_id_val = ws_leads.cell(row=row_idx, column=1).value
            if lead_id_val and str(lead_id_val).startswith("LEAD-"):
                try:
                    num = int(str(lead_id_val).replace("LEAD-", ""))
                    if num > max_id_num:
                        max_id_num = num
                except ValueError:
                    pass

            name_val = ws_leads.cell(row=row_idx, column=3).value
            url_val = ws_leads.cell(row=row_idx, column=6).value

            if url_val:
                existing_urls.add(str(url_val).strip().lower())
            if name_val:
                existing_names.add(str(name_val).strip().lower())

        # 2. Filter and append new leads
        new_leads_appended = 0
        duplicates_skipped = 0

        regular_font = Font(name="Segoe UI", size=10)
        bold_font = Font(name="Segoe UI", size=10, bold=True)
        pink_badge_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
        pink_fill = PatternFill(start_color=COLOR_HOT_PINK, end_color=COLOR_HOT_PINK, fill_type="solid")
        alt_fill = PatternFill(start_color=COLOR_ROW_ALT, end_color=COLOR_ROW_ALT, fill_type="solid")
        white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
        thin_border = Border(
            left=Side(border_style="thin", color=COLOR_BORDER),
            right=Side(border_style="thin", color=COLOR_BORDER),
            top=Side(border_style="thin", color=COLOR_BORDER),
            bottom=Side(border_style="thin", color=COLOR_BORDER),
        )

        for p in prospects:
            norm_url = p.verified_url.strip().lower()
            norm_name = p.name_or_handle.strip().lower()

            # Prevent duplication
            if norm_url in existing_urls or norm_name in existing_names:
                duplicates_skipped += 1
                continue

            max_id_num += 1
            lead_id = f"LEAD-{max_id_num:04d}"
            existing_urls.add(norm_url)
            existing_names.add(norm_name)

            prospect_display = p.name_or_handle
            if p.organization and p.organization != p.name_or_handle:
                prospect_display = f"{p.name_or_handle} ({p.organization})"

            signals_str = "; ".join(s.description for s in p.observed_need_signals)
            discovery_str = p.scouted_at.strftime("%Y-%m-%d %H:%M:%S")

            row_data = [
                lead_id,
                startup_name,
                prospect_display,
                p.role_or_title or "Decision Maker",
                p.platform_source.upper(),
                p.verified_url,
                p.match_score,
                signals_str,
                p.personalized_hook_for_sales,
                "New Lead",
                discovery_str,
            ]

            current_row = ws_leads.max_row + 1
            ws_leads.append(row_data)

            # Styling row
            use_alt = (current_row % 2 == 0)
            row_fill = alt_fill if use_alt else white_fill

            for c_idx in range(1, len(row_data) + 1):
                c = ws_leads.cell(row=current_row, column=c_idx)
                c.font = regular_font
                c.fill = row_fill
                c.border = thin_border
                c.alignment = Alignment(vertical="center", wrap_text=(c_idx in [8, 9]))

                # High match score highlight (Hot Pink for 9-10)
                if c_idx == 7:  # Match Score column
                    c.alignment = Alignment(horizontal="center", vertical="center")
                    if p.match_score >= 9:
                        c.fill = pink_fill
                        c.font = pink_badge_font
                    else:
                        c.font = bold_font
                elif c_idx in [1, 5, 10]:
                    c.alignment = Alignment(horizontal="center", vertical="center")

            ws_leads.row_dimensions[current_row].height = 22
            new_leads_appended += 1

        total_in_db = ws_leads.max_row - 1

        # 3. Log to Run History
        run_record = [
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            startup_name,
            len(prospects),
            new_leads_appended,
            duplicates_skipped,
            total_in_db,
        ]
        ws_history.append(run_record)
        hist_row = ws_history.max_row
        for c_idx in range(1, len(run_record) + 1):
            hc = ws_history.cell(row=hist_row, column=c_idx)
            hc.font = regular_font
            hc.border = thin_border
            hc.alignment = Alignment(horizontal="center", vertical="center")

        # 4. Auto-fit column widths
        self._auto_fit_columns(ws_leads)
        self._auto_fit_columns(ws_history)

        wb.save(self.filepath)
        logger.info(
            f"Synced with Master Excel: +{new_leads_appended} added, "
            f"{duplicates_skipped} duplicates skipped. Total leads in DB: {total_in_db}."
        )

        return {
            "total_added": new_leads_appended,
            "duplicates_skipped": duplicates_skipped,
            "total_in_db": total_in_db,
            "filepath": str(self.filepath),
        }

    def _auto_fit_columns(self, ws) -> None:
        """Calculate column widths based on maximum content length with reasonable caps."""
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val = cell.value
                if val:
                    val_str = str(val)
                    if len(val_str) > max_len:
                        max_len = len(val_str)
            # Apply padding and caps for readability
            calc_width = min(max(max_len + 4, 12), 48)
            ws.column_dimensions[col_letter].width = calc_width

    def get_all_leads(self) -> list[dict[str, Any]]:
        """
        Read and return all leads from the Master Leads sheet as clean dictionaries.
        Used by the interactive web dashboard API.
        """
        if not self.filepath.exists():
            return []

        wb = openpyxl.load_workbook(self.filepath, data_only=True)
        if "Master Leads" not in wb.sheetnames:
            return []

        ws = wb["Master Leads"]
        leads = []
        for r in range(2, ws.max_row + 1):
            lead_id = ws.cell(row=r, column=1).value
            if not lead_id:
                continue

            leads.append({
                "lead_id": str(ws.cell(row=r, column=1).value or ""),
                "target_startup": str(ws.cell(row=r, column=2).value or ""),
                "prospect": str(ws.cell(row=r, column=3).value or ""),
                "role": str(ws.cell(row=r, column=4).value or ""),
                "platform": str(ws.cell(row=r, column=5).value or ""),
                "url": str(ws.cell(row=r, column=6).value or ""),
                "match_score": int(ws.cell(row=r, column=7).value or 5),
                "signals": str(ws.cell(row=r, column=8).value or ""),
                "sales_hook": str(ws.cell(row=r, column=9).value or ""),
                "status": str(ws.cell(row=r, column=10).value or "New Lead"),
                "date": str(ws.cell(row=r, column=11).value or ""),
            })

        return leads

    def get_run_history(self) -> list[dict[str, Any]]:
        """Read and return all entries from the Run History sheet."""
        if not self.filepath.exists():
            return []

        wb = openpyxl.load_workbook(self.filepath, data_only=True)
        if "Run History" not in wb.sheetnames:
            return []

        ws = wb["Run History"]
        history = []
        for r in range(2, ws.max_row + 1):
            ts = ws.cell(row=r, column=1).value
            if not ts:
                continue
            history.append({
                "timestamp": str(ws.cell(row=r, column=1).value or ""),
                "startup": str(ws.cell(row=r, column=2).value or ""),
                "total_discovered": int(ws.cell(row=r, column=3).value or 0),
                "new_added": int(ws.cell(row=r, column=4).value or 0),
                "duplicates_skipped": int(ws.cell(row=r, column=5).value or 0),
                "total_in_db": int(ws.cell(row=r, column=6).value or 0),
            })

        return history
