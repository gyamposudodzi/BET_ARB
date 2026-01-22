# BET_ARB Project Gemini Context

This document provides a comprehensive overview of the BET_ARB project for the Gemini assistant, including its purpose, architecture, and ongoing development tasks.

## Project Overview

**Project Name:** BET_ARB (Sports Arbitrage Bot)

**Purpose:** The primary goal of this project is to automatically detect arbitrage opportunities in sports betting markets and notify the user of these opportunities.

**Architecture:** The application is built using Python with a modern asynchronous architecture powered by `asyncio`.

**Core Components:**
*   **Data Collector (`data_collection/odds_api.py`):** Responsible for fetching odds data from "The Odds API". It includes a fallback mechanism to generate test data, which is useful for development and testing without hitting the live API.
*   **Database (`database/`):** Utilizes SQLAlchemy for database interaction. The schema, defined in `database/models.py`, includes tables for `sports`, `bookmakers`, `events`, `markets`, `odds`, and `opportunities`.
*   **Arbitrage Detector & Calculator (`core/detector.py`, `core/calculations.py`):** This is the heart of the bot. It processes the raw odds data to identify and validate arbitrage opportunities based on mathematical calculations of implied probabilities.
*   **Alerter (`alerts/telegram_bot.py`):** When a profitable opportunity is found, this component formats a message and sends it to the user via a Telegram bot.
*   **Main Orchestrator (`main.py`):** The `ArbitrageBot` class in this file initializes all components and runs the main continuous scanning loop.

## Development Tasks

### To Be Fixed

*   **Incomplete Data Persistence:** The current application logic only saves the summary of a detected arbitrage opportunity to the `opportunities` table. The detailed data that constitutes the opportunity—specifically the `Event`, `Market`, and `Odds` records from which the opportunity was derived—are not being saved to the database. This shortcut in the data pipeline results in the `events`, `markets`, and `odds` tables remaining empty.
    *   **Impact:** This prevents historical analysis, makes the stored opportunity data less informative, and hinders future features that might rely on detailed historical odds data.
    *   **Required Fix:** The logic needs to be updated to ensure that when an opportunity is detected and saved, the corresponding `Event`, `Market`, and `Odds` data are also persisted to the database. This will likely involve modifying the `handle_opportunity` method in `main.py` and potentially adding new CRUD operations in `database/crud.py`.

### Next Steps
*(To be populated with future ideas)*
