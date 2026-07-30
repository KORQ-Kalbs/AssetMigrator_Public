"""
validator.py

Pre-flight checks run before any upload happens, so problems surface in
Dry Run mode instead of mid-migration.
"""

from loguru import logger

from modules.excel_reader import ExtractedAsset
from modules.sheets_service import SheetsService


def validate(assets: list[ExtractedAsset], sheets: SheetsService) -> list[dict]:
    """Returns a list of warning/error dicts for the report; does not raise."""
    issues = []

    names_seen = set()
    for asset in assets:
        if not asset.asset_name:
            issues.append({
                "asset_code": asset.asset_code,
                "issue": "No Asset Name found in source file — cannot match by name"
            })
            continue

        if asset.asset_name.lower() in names_seen:
            issues.append({
                "asset_code": asset.asset_code,
                "issue": f"Duplicate Asset Name '{asset.asset_name}' in source file"
            })
        names_seen.add(asset.asset_name.lower())

        match = sheets.find_rows_by_name(asset.asset_name)
        if not match.row_indices:
            issues.append({
                "asset_code": asset.asset_code,
                "issue": f"Asset Name '{asset.asset_name}' not found in Google Sheet"
            })

    logger.info(f"Validation complete: {len(issues)} issue(s) found")
    for issue in issues:
        logger.warning(f"{issue['asset_code']}: {issue['issue']}")

    return issues
