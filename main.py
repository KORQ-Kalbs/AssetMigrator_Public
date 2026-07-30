"""
main.py - AMAT Direct API Mode (CLI)

Usage:
    python main.py --excel Aset_Category.xlsx --dry-run
    python main.py --excel Aset_Category.xlsx --spreadsheet-id XXX --drive-folder-id YYY

Strategy A (Asset Name Matching):
    The script matches each category photo to ALL rows in the Google Sheet
    that share the same Asset Name (case-insensitive). One image upload
    populates every room / unit row automatically.

    Run with --dry-run first to see how many rows each image would update
    before writing anything to Google Drive or Sheets.
"""

import argparse
import os
import sys
import time

from loguru import logger

import config
from modules.auth import get_credentials
from modules.excel_reader import extract_assets_with_images
from modules.drive_service import DriveService
from modules.sheets_service import SheetsService
from modules.validator import validate
from modules.report_generator import write_report


def parse_args():
    p = argparse.ArgumentParser(description="Asset Migration Automation Tool - Direct API Mode")
    p.add_argument("--excel", required=True, help="Path to the source .xlsx with embedded images")
    p.add_argument("--sheet", default=config.SOURCE_SHEET_NAME, help="Worksheet name in the source file")
    p.add_argument("--header-row", type=int, default=config.HEADER_ROW)
    p.add_argument("--spreadsheet-id", default=config.SPREADSHEET_ID)
    p.add_argument("--worksheet-name", default=config.WORKSHEET_NAME)
    p.add_argument("--drive-folder-id", default=config.DRIVE_FOLDER_ID)
    p.add_argument("--dry-run", action="store_true", help="Validate and simulate only, no uploads/writes")
    p.add_argument(
        "--on-existing",
        choices=["skip", "overwrite"],
        default="skip",
        help="What to do when a row already has a Picture URL (default: skip)",
    )
    return p.parse_args()


def has_existing_picture(match) -> bool:
    """Return True if ANY matched row already has a Picture URL."""
    return any(p for p in match.existing_pictures)


def main():
    args = parse_args()

    os.makedirs(config.LOG_DIR, exist_ok=True)
    logger.add(os.path.join(config.LOG_DIR, "amat_{time}.log"), rotation="5 MB")

    config.SPREADSHEET_ID = args.spreadsheet_id
    config.WORKSHEET_NAME = args.worksheet_name

    if not config.SPREADSHEET_ID:
        logger.error("No --spreadsheet-id given and none set in config.py")
        sys.exit(1)
    if not args.dry_run and not args.drive_folder_id:
        logger.error("No --drive-folder-id given and none set in config.py (required for live runs)")
        sys.exit(1)

    # 1. Extract images + asset codes from the source Excel
    assets = extract_assets_with_images(
        xlsx_path=args.excel,
        sheet_name=args.sheet,
        header_row=args.header_row,
        asset_code_header=config.ASSET_CODE_HEADER,
        asset_name_header=config.ASSET_NAME_HEADER,
    )
    if not assets:
        logger.error("No assets with images extracted - nothing to do")
        sys.exit(1)

    # 2. Auth + connect to Sheets (needed even in dry-run, to validate against real data)
    creds = get_credentials()
    sheets = SheetsService(creds)
    drive = None if args.dry_run else DriveService(creds)

    # 3. Validate
    validate(assets, sheets)

    # 4. Process each asset (Strategy A: match by Asset Name)
    results = []
    for asset in assets:
        start = time.time()

        if not asset.asset_name:
            results.append({
                "asset_code": asset.asset_code, "asset_name": "",
                "status": "ERROR", "rows_updated": [], "url": "",
                "message": "No Asset Name in source file — cannot match by name",
                "seconds": time.time() - start,
            })
            continue

        match = sheets.find_rows_by_name(asset.asset_name)

        if not match.row_indices:
            results.append({
                "asset_code": asset.asset_code, "asset_name": asset.asset_name,
                "status": "ERROR", "rows_updated": [], "url": "",
                "message": f"Asset Name '{asset.asset_name}' not found in Google Sheet",
                "seconds": time.time() - start,
            })
            continue

        # How many rows already have a picture?
        rows_with_pic   = [r for r, p in zip(match.row_indices, match.existing_pictures) if p]
        rows_without_pic = [r for r, p in zip(match.row_indices, match.existing_pictures) if not p]
        existing_url    = next((p for p in match.existing_pictures if p), None)

        if existing_url and args.on_existing == "skip":
            # Only update rows that are still empty; skip rows that already have a URL
            target_rows = rows_without_pic
            if not target_rows:
                results.append({
                    "asset_code": asset.asset_code, "asset_name": asset.asset_name,
                    "status": "SKIPPED", "rows_updated": [], "url": existing_url,
                    "message": f"All {len(match.row_indices)} row(s) already have a picture (--on-existing=skip)",
                    "seconds": time.time() - start,
                })
                continue
        elif args.on_existing == "overwrite":
            target_rows = match.row_indices  # update everything
        else:
            target_rows = match.row_indices  # default: update everything

        if args.dry_run:
            results.append({
                "asset_code": asset.asset_code, "asset_name": asset.asset_name,
                "status": "SUCCESS", "rows_updated": target_rows, "url": "[DRY RUN - not uploaded]",
                "message": (
                    f"Would upload once and update {len(target_rows)} row(s) "
                    f"(skipping {len(rows_with_pic)} row(s) that already have a picture)"
                    if rows_with_pic else
                    f"Would upload once and update {len(target_rows)} row(s)"
                ),
                "seconds": time.time() - start,
            })
            continue

        try:
            # Upload image once, named after the asset model
            safe_name = asset.asset_name.replace("/", "_").replace("\\", "_")
            filename = f"{safe_name}.{asset.image_ext}"
            url = drive.upload_image(
                asset.image_bytes, filename, asset.image_ext, args.drive_folder_id
            )
            # Write to all target rows in one batch call
            sheets.batch_update_picture_url(target_rows, url)

            skipped_msg = (
                f" ({len(rows_with_pic)} row(s) already had a picture and were skipped)"
                if rows_with_pic and args.on_existing == "skip" else ""
            )
            results.append({
                "asset_code": asset.asset_code, "asset_name": asset.asset_name,
                "status": "SUCCESS", "rows_updated": target_rows, "url": url,
                "message": f"OK — updated {len(target_rows)} row(s){skipped_msg}",
                "seconds": time.time() - start,
            })
        except Exception as e:
            logger.error(f"{asset.asset_code} ({asset.asset_name}): failed - {e}")
            results.append({
                "asset_code": asset.asset_code, "asset_name": asset.asset_name,
                "status": "ERROR", "rows_updated": [], "url": "",
                "message": str(e), "seconds": time.time() - start,
            })

    # 5. Report
    report_path = write_report(results)
    success = sum(1 for r in results if r["status"] == "SUCCESS")
    logger.info(
        f"Done. {success}/{len(results)} succeeded. "
        f"{'(DRY RUN - nothing was actually uploaded)' if args.dry_run else ''}"
    )
    logger.info(f"Report saved to: {report_path}")


if __name__ == "__main__":
    main()
