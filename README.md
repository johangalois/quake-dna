# Quake DNA

**An end-to-end earthquake data pipeline and interactive dashboard powered by the USGS Earthquake API.**

🌐 **[Live Dashboard](https://quake-dna-nvggp83uttopbswljogcac.streamlit.app/)**

Quake DNA is a data analytics project designed to collect, validate, process, and explore earthquake events through an interactive dashboard.

The project combines Python-based data ingestion and processing with Streamlit visualizations to make seismic activity easier to explore and understand.

## Live Demo

Explore the deployed application:

**[Open Quake DNA Dashboard](https://quake-dna-nvggp83uttopbswljogcac.streamlit.app/)**

The dashboard allows users to explore recent earthquake activity, analyze geographic patterns, filter individual events, and review seismic records interactively.

## Project Overview

Quake DNA uses publicly available earthquake data from the [USGS Earthquake API](https://earthquake.usgs.gov/fdsnws/event/1/).

The dashboard retrieves recent earthquake events and provides an interactive way to explore seismic activity across geographic regions, magnitudes, and time periods.

The project also includes a local data-processing workflow and automated tests to validate the quality and consistency of the processed dataset.

## Features

- **Overview:** Explore key earthquake indicators and general seismic activity.
- **Regional Analysis:** Examine earthquake distribution across geographic areas.
- **Earthquake Explorer:** Filter and investigate individual earthquake events.
- **Event Records:** Review event-level information and explore the underlying records.
- **Data Processing:** Transform raw GeoJSON earthquake data into a structured dataset.
- **Data Quality Checks:** Validate event identifiers, columns, coordinates, depth values, magnitudes, and timestamps.

## Data Source

Earthquake data is obtained from the **USGS Earthquake API**.

The dashboard retrieves a rolling 365-day window of recent events, applying a minimum magnitude threshold of 2.5.

The application uses Streamlit caching to reduce repeated API requests and improve the dashboard experience.

## Project Architecture

```text
quake-dna/
│
├── app.py
├── requirements.txt
├── README.md
│
├── data/
│   ├── raw/
│   └── processed/
│
├── src/
│   ├── __init__.py
│   ├── data_source.py
│   ├── ingestion.py
│   ├── processing.py
│   ├── validate_raw.py
│   ├── inspect_quality.py
│   └── eda.py
│
└── tests/
    └── test_processing.py
```

### Data Workflow

1. **Data Ingestion:** Retrieve earthquake event data from the USGS API.
2. **Raw Data Storage:** Store source data in GeoJSON format for local processing.
3. **Data Validation:** Inspect and validate raw records.
4. **Data Processing:** Transform raw earthquake records into a structured tabular dataset.
5. **Exploratory Analysis:** Examine distributions and identify patterns in seismic activity.
6. **Visualization:** Present earthquake information through an interactive Streamlit dashboard.

The deployed dashboard retrieves data directly from USGS. The local raw and processed datasets support the separate processing and validation workflow.

## Technology Stack

| Area | Technologies |
|---|---|
| Programming | Python |
| Data Collection | USGS Earthquake API, Requests |
| Data Processing | Pandas |
| Data Visualization | Plotly |
| Dashboard | Streamlit |
| Testing | Pytest |
| Version Control | Git, GitHub |

## Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/johangalois/quake-dna.git
cd quake-dna
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

**Windows (Git Bash):**

```bash
source .venv/Scripts/activate
```

**macOS / Linux:**

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Run the dashboard

```bash
streamlit run app.py
```

The application will open in your browser.

## Run Tests

Run the automated test suite from the project root:

```bash
python -m pytest -v
```

The tests validate:

- Unique earthquake event identifiers.
- Expected processed dataset columns.
- Consistency of negative-depth flags.
- Minimum magnitude threshold.
- Valid geographic coordinates.
- Presence of event timestamps.

## Project Status

The data-processing workflow and automated tests are implemented. The interactive dashboard is being prepared for public deployment through Streamlit Community Cloud.

## Future Improvements

- Expand the automated data-quality test coverage.
- Add historical trend analysis and additional seismic indicators.
- Improve data pipeline automation and scheduling.
- Explore additional geographic and temporal analysis features.

## Acknowledgements

- [United States Geological Survey (USGS)](https://www.usgs.gov/) for providing public earthquake data.
- [Streamlit](https://streamlit.io/) for the dashboard framework.
