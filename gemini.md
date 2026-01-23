# ♊ Gemini Project Context: BET_ARB

## 📂 Project Overview
**Name:** BET_ARB (Sports Arbitrage Bot)
**Goal:** An automated system to detect and alert on sports betting arbitrage opportunities ("sure bets") by comparing odds across different bookmakers (e.g., Pinnacle, Bet365).
**Tech Stack:**
- **Language:** Python 3.9+
- **Core:** `asyncio` for concurrent execution.
- **Database:** SQLite (via `aiosqlite` / custom session management).
- **Data Source:** The Odds API.
- **Notifications:** Telegram Bot API.
- **Logging:** `loguru`.

## 🏗️ Architecture
1.  **`main.py`**: The central orchestrator. Runs the `scan_cycle` loop, manages the lifecycle of the bot, and handles signal interrupts.
2.  **`data_collection/`**: Handles fetching odds from external APIs (The Odds API).
3.  **`core/`**:
    -   `calculations.py`: Math for arbitrage detection (implied probability, profit %).
    -   `detector.py`: Logic to compare odds and find opportunities.
    -   `rate_limiter.py`: Manages API quota tracking.
4.  **`database/`**:
    -   `session.py`: DB connection and initialization.
    -   `crud.py`: Database operations (Create, Read, Update, Delete).
    -   `models.py`: Schema definitions (Sports, Events, Odds, Opportunities).
5.  **`alerts/`**: Telegram bot integration for sending real-time notifications.

## 📍 Current Status
-   **Pipeline State:** Fully functional. Data persistence (Events, Odds, Opportunities) is working correctly.
-   **Testing:** A test suite (`test_bot.py`) exists for DB, Calculations, Telegram, and API connectivity.
-   **Data Flow:**
    1.  Fetch odds from API.
    2.  Store raw market data (Events/Odds) to DB.
    3.  Detect Arbitrage.
    4.  Store Opportunity to DB.
    5.  Send Alert.

## 🐛 Known Issues & Fixes Needed
*(None currently critical)*

## ✅ Resolved Issues
### 🟢 Fixed: Empty Events/Odds Tables & Opportunity Storage Failure
**Resolution:**
-   Modified `scan_sport` to pass `sport_id` directly to `process_and_store_market_data` and `handle_opportunity`.
-   Updated `handle_opportunity` to use the passed `sport_id` for efficient event lookup.
-   Optimized database commits in `crud.py` (batch processing).

### 🟢 Fixed: Telegram Bot Shutdown Error
**Resolution:**
-   Updated `alerts/telegram_bot.py` to explicitly stop the `Updater` before stopping the `Application` to prevent "Updater is still running" errors and network tracebacks on exit.

---

## 📝 Roadmap / Next Steps
-   [x] Fix the Events/Odds persistence bug.
-   [ ] **Smart Rate Limiting**: Connect `odds_api.py` to `RateLimiter` to read response headers.
-   [x] **Interactive Telegram Bot**: Added `/status` and `/help` commands.
-   [ ] **Configuration Expansion**: Remove hardcoded limits (currently limited to 3 sports) and add bookmaker filtering in `settings.py`.
-   [ ] **Docker Support**: Add `Dockerfile` and `docker-compose.yml` for easy 24/7 server deployment.
-   [ ] **Profit Analysis**: Create a script to analyze the `opportunities` table and visualize potential profit over time.

---
*This file is maintained by Gemini Code Assist to track project context and tasks.*
Last Updated: 2026-01-23