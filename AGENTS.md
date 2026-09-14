# A TuBe - Repository Guidelines & Agent Automation Rules

## 1. Continuous GitHub Synchronization (MANDATORY)
For EVERY user request or autonomous task where code, assets, configurations, or documents are added or modified:
- **Automatic Execution**: The assistant MUST automatically commit and push all changes to GitHub (`origin main`) before completing the task.
- **No Prompting Needed**: Do not ask the user for permission to push or wait for them to inquire about sync status.
- **Push Command Standard**:
  ```bash
  git add -A
  git commit -m "<type>(<scope>): <clear descriptive summary>"
  git pull --rebase origin main
  git push origin main
  ```
- **File Exclusions**: Never commit ephemeral locked cache databases (e.g. `config/dork_cache/*.sqlite`).

## 2. Media Player & Streaming Integrity
- All movies and series must use the Universal Stream Bridge (`/api/stream/bridge`) to bypass CORS and stream directly inside the native in-app player.
- 10-15s Zero-Click Auto-Play HUD must activate seamlessly when viewing content.
- Backdrop and poster integrity: TMDB posters must strictly match the exact media title and release year (e.g., "أسد 2026" must never display "أسد وأربع قطط").
