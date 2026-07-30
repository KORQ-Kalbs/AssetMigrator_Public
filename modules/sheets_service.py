"""
sheets_service.py  (Strategy A - Asset Name Matching)

Talks to the Google Sheets "database". Matches rows by **Asset Name**
(case-insensitive, whitespace-normalised) rather than Asset Code.

Why:
  The source category export (Aset_Category.xlsx) has ONE master photo per
  asset MODEL (e.g. one photo for "SDB"), while the live Google Sheet has
  MANY rows for that model (one per physical unit / room).
  Strategy A uploads the picture once to Drive, then writes the same Drive
  URL to EVERY row whose Asset Name matches — regardless of Asset Code or
  room location.

Name normalisation:
  Both the source name and the sheet names are stripped of leading/trailing
  whitespace and compared case-insensitively, so "SDB ", "sdb", "SDB" all
  match the same rows.
"""

from dataclasses import dataclass, field
import json
import os
from typing import Optional
import time

import gspread
from google.oauth2.credentials import Credentials
from loguru import logger

import config


@dataclass
class MatchResult:
    asset_name: str
    row_indices: list[int]        # 1-indexed rows in the Google Sheet
    existing_pictures: list[str]  # existing Picture cell values, aligned with row_indices
    matched_codes: list[str] = field(default_factory=list)   # codes found across matched rows


class SheetsService:
    def __init__(self, creds: Credentials):
        self.client = gspread.authorize(creds)
        self.spreadsheet = self.client.open_by_key(config.SPREADSHEET_ID)
        self.ws = self.spreadsheet.worksheet(config.WORKSHEET_NAME)

        logger.info("Loading current sheet data into memory...")
        self._all_values = self.ws.get_all_values()
        if not self._all_values:
            raise ValueError(f"Worksheet '{config.WORKSHEET_NAME}' is empty")

        self._headers = [str(h).strip() for h in self._all_values[0]]

        required_headers = [
            (config.ASSET_CODE_HEADER, "_code_col"),
            (config.ASSET_NAME_HEADER, "_name_col"),
            (config.PICTURE_HEADER, "_picture_col"),
        ]
        for header_name, attr_name in required_headers:
            if header_name not in self._headers:
                raise ValueError(
                    f"Required column header '{header_name}' not found in Google Sheet "
                    f"'{config.WORKSHEET_NAME}'. Found headers: {self._headers}"
                )
            setattr(self, attr_name, self._headers.index(header_name) + 1)

        # Build normalised_name -> [row_index, ...] map (1-indexed, header = row 1)
        self._name_to_rows: dict[str, list[int]] = {}
        for i, row in enumerate(self._all_values[1:], start=2):
            if len(row) >= self._name_col:
                name = row[self._name_col - 1].strip()
                if name:
                    key = name.lower()
                    self._name_to_rows.setdefault(key, []).append(i)

        # Load name aliases if available
        self._aliases: dict[str, list[str]] = {}
        alias_file = "name_aliases.json"
        if os.path.exists(alias_file):
            try:
                with open(alias_file, "r") as f:
                    raw_aliases = json.load(f)
                    self._aliases = {
                        k.strip().lower(): [v.strip().lower() for v in vals]
                        for k, vals in raw_aliases.items()
                    }
                logger.info(f"Loaded {len(self._aliases)} alias rules from '{alias_file}'")
            except Exception as e:
                logger.warning(f"Failed to load '{alias_file}': {e}")

        unique_names = len(self._name_to_rows)
        total_rows = len(self._all_values) - 1
        logger.info(
            f"Loaded {total_rows} data rows, "
            f"{unique_names} unique Asset Names (name-based matching enabled)"
        )

    # ------------------------------------------------------------------
    # Primary API: find by name (with alias resolution)
    # ------------------------------------------------------------------

    def find_rows_by_name(self, asset_name: str) -> MatchResult:
        """
        Return all Google Sheet rows whose Asset Name matches `asset_name`
        or any of its configured aliases (case-insensitive).
        """
        key = asset_name.strip().lower()
        target_keys = self._aliases.get(key, [key])

        row_indices_set = set()
        for tkey in target_keys:
            row_indices_set.update(self._name_to_rows.get(tkey, []))

        row_indices = sorted(list(row_indices_set))

        pictures = []
        codes = []
        for r in row_indices:
            row = self._all_values[r - 1]
            pictures.append(
                row[self._picture_col - 1].strip()
                if len(row) >= self._picture_col else ""
            )
            codes.append(
                row[self._code_col - 1].strip()
                if len(row) >= self._code_col else ""
            )

        return MatchResult(
            asset_name=asset_name,
            row_indices=row_indices,
            existing_pictures=pictures,
            matched_codes=codes,
        )

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def update_picture_url(self, row_index: int, url: str):
        """Write the Picture URL to a single row, with retry."""
        for attempt in range(1, config.RETRY_ATTEMPTS + 1):
            try:
                self.ws.update_cell(row_index, self._picture_col, url)
                # keep in-memory cache in sync
                row = self._all_values[row_index - 1]
                while len(row) < self._picture_col:
                    row.append("")
                row[self._picture_col - 1] = url
                return
            except Exception as e:
                logger.warning(f"Sheet update attempt {attempt} failed for row {row_index}: {e}")
                if attempt < config.RETRY_ATTEMPTS:
                    time.sleep(config.RETRY_DELAY_SECONDS)
                else:
                    raise

    def batch_update_picture_url(self, row_indices: list[int], url: str):
        """
        Write the same Picture URL to multiple rows in a single batch API call.
        Falls back to individual updates if the batch fails.
        """
        if not row_indices:
            return
        try:
            updates = [
                {
                    "range": gspread.utils.rowcol_to_a1(r, self._picture_col),
                    "values": [[url]],
                }
                for r in row_indices
            ]
            self.ws.batch_update(updates, value_input_option="USER_ENTERED")
            # sync in-memory cache
            for r in row_indices:
                row = self._all_values[r - 1]
                while len(row) < self._picture_col:
                    row.append("")
                row[self._picture_col - 1] = url
            logger.debug(f"Batch updated {len(row_indices)} rows")
        except Exception as e:
            logger.warning(f"Batch update failed ({e}), falling back to individual updates")
            for r in row_indices:
                self.update_picture_url(r, url)
