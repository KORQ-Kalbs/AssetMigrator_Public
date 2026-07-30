# AssetMigrator 🚀

**AssetMigrator** is an automated CLI tool designed to extract embedded images from Microsoft Excel (`.xlsx`) exports, upload them to **Google Drive**, and sync public view URLs directly into target rows of a **Google Sheets** asset database.

It uses **anchor-based cell position extraction** and **smart Asset Name / Alias matching** so that a single master catalog image (e.g. for a equipment model) automatically updates across all corresponding inventory unit rows.

---

## ✨ Features

- 📷 **Anchor-Based Image Extraction**: Extracts embedded `.png`/`.jpg` images from `.xlsx` files based on exact cell anchor coordinates rather than un-ordered internal XML lists.
- 🎯 **Smart Name & Alias Matching**: Automatically matches category images to Google Sheets rows using Asset Model Names and customizable alias rules (`name_aliases.json`).
- ⚡ **Batch Operations & Deduplication**: Uploads each unique image model **once** to Google Drive and uses Google Sheets batch API calls to update hundreds of matching rows efficiently.
- 🔍 **Safe Dry-Run Mode**: Full simulation capability that validates data and generates an inspection report without making any changes to Google Drive or Sheets.
- 📊 **Automatic Excel Reporting**: Produces detailed timestamped migration reports (`reports/MigrationReport_*.xlsx`) tracking every success, skip, or missing row.

---

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/KORQ-Kalbs/AssetMigrator.git
   cd AssetMigrator
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🔑 Google Cloud API Setup (One-Time)

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project and enable both the **Google Drive API** and **Google Sheets API**.
3. Create an **OAuth 2.0 Client ID** with Application Type set to **Desktop App**.
4. Download the JSON credential file and save it as `credentials.json` in the root directory (see `credentials.json.template` for format).
5. On the first execution, a browser tab will prompt for a one-time Google authorization. It saves `token.json` locally for subsequent silent runs.

---

## ⚙️ Configuration

Edit `config.py` or provide parameters via CLI arguments:

```python
# --- Google Sheets ---
SPREADSHEET_ID = "YOUR_SPREADSHEET_ID_HERE"
WORKSHEET_NAME = "Assets"

# --- Google Drive ---
DRIVE_FOLDER_ID = "YOUR_DRIVE_FOLDER_ID_HERE"
```

### 🏷️ Name Aliases (`name_aliases.json`)
You can map source asset names to target database names in `name_aliases.json`:
```json
{
  "Tv": ["Televisi"],
  "Tv Remote": ["Remote TV"],
  "Alarm": ["Alarm Clock"]
}
```

---

## 🚀 Usage

### 1. Run a Dry Run (Simulation)
Always test with `--dry-run` first to verify image extraction and row matching without modifying any online data:

```bash
python main.py --excel "Source_Export.xlsx" --dry-run
```

### 2. Perform Live Migration
When you are ready to upload images to Google Drive and sync URLs to Google Sheets:

```bash
python main.py --excel "Source_Export.xlsx" --on-existing overwrite
```

### 💡 CLI Options

| Flag | Description | Default |
|---|---|---|
| `--excel` | Path to the source `.xlsx` export file with embedded images | *Required* |
| `--dry-run` | Perform validation and simulation only (no uploads or writes) | `False` |
| `--spreadsheet-id` | Override target Google Spreadsheet ID | `config.py` |
| `--drive-folder-id` | Override destination Google Drive Folder ID | `config.py` |
| `--on-existing` | Behavior when cell already has a URL (`skip` or `overwrite`) | `skip` |

---

## 📄 License

Directed By KORQ-Kalbs

# AssetMigrator_Public
