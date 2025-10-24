# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Name:** Fortune Lab: Decoding the Jackpot
**Purpose:** Full and deep analysis of Philippine PCSO lotto draw results with an elegant, modern dashboard displaying analysis reports and probability-based combination predictions.

## Technology Stack

- **Language:** Python 3.14+
- **Package Manager:** `uv` (NOT pip)
- **Web Framework:** Flask (modern, elegant UI design required)
- **Web Scraping:** Selenium (for PCSO website)
- **Data Storage:** JSON files

## Development Commands

### Dependency Management
```bash
# Add a new dependency
uv add package-name

# Sync dependencies
uv sync

# Run Python in the virtual environment
uv run python main.py
```

### Running the Application
```bash
# Run Flask application (once implemented)
uv run python app.py
# or
uv run flask run
```

## Architecture & Implementation Requirements

### Supported Lotto Game Types
- Lotto 6/42
- Mega Lotto 6/45
- Super Lotto 6/49
- Grand Lotto 6/55
- Ultra Lotto 6/58

### Data Extraction Workflow

1. **User Input:** Date range selection (default: January 1, 2015 to current date) and game type selection
2. **Trigger:** Generate button click
3. **Web Scraping:** Use Selenium to extract data from `https://www.pcso.gov.ph/SearchLottoResult.aspx`

**PCSO Website Selectors:**
- Start Date: `cphContainer_cpContent_ddlStartMonth`, `cphContainer_cpContent_ddlStartDate`, `cphContainer_cpContent_ddlStartYear`
- End Date: `cphContainer_cpContent_ddlEndMonth`, `cphContainer_cpContent_ddlEndDay`, `cphContainer_cpContent_ddlEndYear`
- Game Type: `cphContainer_cpContent_ddlSelectGame`
- Search Button: `cphContainer_cpContent_btnSearch`
- Results Table: `.search-lotto-result-div table tbody`

4. **Data Storage:** Save to `result_{game_type}_{end_date}.json`

### Dashboard Requirements

The Flask dashboard must display:

1. **Overall Analysis Report**
   - Statistical analysis with charts
   - Top 5 combinations with highest probability for next draw
   - Top 5 combinations from ultimate analysis

2. **Day-Specific Analysis**
   - Separate analysis for each day: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday
   - Day-specific probability patterns

3. **UI/UX Standards**
   - Modern, elegant component design
   - Professional data visualization
   - Clean, intuitive interface

## Code Quality Standards

- Follow Python best practices and PEP 8 style guide
- Maintain clean, readable code with proper documentation
- Use meaningful variable and function names
- Implement proper error handling

## Project Structure Notes

This is an early-stage project. When implementing:
- Create modular architecture (separate modules for scraping, analysis, visualization, Flask routes)
- Keep data extraction logic separate from analysis logic
- Design reusable components for different game types
- Ensure Flask templates are well-organized and maintainable
