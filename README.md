# HealthTek Clinical Data Ingestion

A robust, production-ready ETL pipeline for ingesting French clinical data from FINESS and IQSS sources. This project automatically extracts, transforms, and loads healthcare facility data and quality indicators.

## 📋 Overview

This pipeline ingests data from two primary sources:

- **FINESS**: French healthcare facility registry (Fichier National des Établissements Sanitaires et Sociaux)
- **IQSS**: Quality and safety indicators (Indicateurs de Qualité et de Sécurité des Soins)

The pipeline follows a medallion architecture with Bronze (raw) and Silver (cleaned) data layers.

## ✨ Features

- ✅ Automatic data extraction from data.gouv.fr APIs
- ✅ Robust error handling with retry logic
- ✅ Comprehensive data validation and cleaning
- ✅ Idempotent pipeline execution
- ✅ Structured logging and monitoring
- ✅ Configurable via environment variables
- ✅ Comprehensive test suite (>80% coverage)
- ✅ Type-safe with type hints
- ✅ Production-ready code quality

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip or pipenv

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/HealthTek-clinical-data-ingestion.git
   cd HealthTek-clinical-data-ingestion
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment** (optional)
   ```bash
   cp .env.example .env
   # Edit .env with your preferences
   ```

### Basic Usage

Run the complete pipeline for specific years:

```bash
python main.py --years 2022 2023 2024
```

Run only FINESS pipeline:

```bash
python main.py --finess-only
```

Run only IQSS pipeline:

```bash
python main.py --iqss-only --years 2023
```

## 📁 Project Structure

```
HealthTek-clinical-data-ingestion/
├── config.py                 # Configuration management
├── main.py                   # Entry point
├── orchestrator.py           # Pipeline orchestration
├── requirements.txt          # Python dependencies
├── pyproject.toml           # Project metadata and tool configs
├── pytest.ini               # Test configuration
│
├── src/                     # Data sources
│   ├── __init__.py
│   ├── base.py             # Abstract DataSource class
│   ├── finess.py           # FINESS source
│   └── iqss.py             # IQSS source
│
├── transform/               # Data transformations
│   ├── __init__.py
│   ├── finess_cleaner.py   # FINESS cleaning logic
│   └── iqss_cleaner.py     # IQSS cleaning logic
│
├── tests/                   # Test suite
│   ├── conftest.py         # Shared fixtures
│   ├── test_base.py
│   ├── test_finess.py
│   ├── test_iqss.py
│   ├── test_finess_cleaner.py
│   ├── test_iqss_cleaner.py
│   └── test_orchestrator.py
│
├── notebooks/               # Data exploration
│   ├── 01_bronze_finess_exploration.ipynb
│   ├── 02_bronze_iqss_exploration.ipynb
│   ├── 03_silver_finess_exploration.ipynb
│   ├── 04_silver_iqss_exploration.ipynb
│   └── README.md
│
└── data/                    # Data directories (created automatically)
    ├── bronze/             # Raw data
    │   ├── finess/
    │   └── iqss/
    └── silver/             # Cleaned data
        ├── finess/
        └── iqss/
```

## ⚙️ Configuration

Configuration is managed through environment variables. Copy `.env.example` to `.env` and customize:

```bash
# Data directories
BRONZE_DIR=data/bronze
SILVER_DIR=data/silver

# API Configuration
REQUEST_TIMEOUT=30
MAX_RETRIES=3
RETRY_BACKOFF_FACTOR=2

# Logging
LOG_LEVEL=INFO
```

## 🧪 Testing

### Run all tests

```bash
pytest
```

### Run with coverage report

```bash
pytest --cov=src --cov=transform --cov=orchestrator --cov-report=html
```

### Run specific test categories

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration
```

## 🛠️ Development

### Install development dependencies

```bash
pip install -e ".[dev]"
```

### Code formatting

```bash
black .
```

### Linting

```bash
ruff check .
```

### Type checking

```bash
mypy src/ transform/ orchestrator.py
```

### Pre-commit hooks (optional)

```bash
pre-commit install
pre-commit run --all-files
```

## 📊 Data Pipeline

### Extraction (Bronze Layer)

- **FINESS**: Downloads the latest establishment registry
- **IQSS**: Downloads annual quality indicator files for specified years

Both sources:
- Check if data needs refresh before downloading
- Use retry logic for network resilience
- Create marker files to prevent redundant downloads

### Transformation (Silver Layer)

#### FINESS Cleaning

- Applies official column headers
- Filters for active establishments only
- Normalizes text fields (title case, cleanup)
- Formats SIRET to 14 digits
- Creates standardized `finess` identifier (9 digits)

#### IQSS Cleaning

- Normalizes column names
- Converts numeric columns (`nb_*`, `score_*`)
- Cleans categorical fields (`participation`, `depot`)
- Normalizes FINESS identifier
- Performs data quality checks

## 🔍 Logging

The pipeline provides detailed logging at multiple levels:

- **INFO**: Pipeline progress and milestones
- **WARNING**: Data quality issues and non-critical errors
- **ERROR**: Pipeline failures and critical issues
- **DEBUG**: Detailed execution information

Logs are written to:
- Console (stdout)
- `pipeline.log` file

## 🐛 Error Handling

The pipeline includes comprehensive error handling:

- Custom exceptions for different failure types
- Graceful degradation (continues processing other years if one fails)
- Detailed error messages with context
- Automatic retry for transient network errors

## 📝 CLI Reference

```
usage: main.py [-h] [--years YEARS [YEARS ...]] 
               [--bronze-dir BRONZE_DIR] [--silver-dir SILVER_DIR]
               [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
               [--finess-only] [--iqss-only]

HealthTek Clinical Data Ingestion Pipeline

optional arguments:
  -h, --help            show this help message and exit
  --years YEARS [YEARS ...]
                        Years to process for IQSS data (default: 2019-2024)
  --bronze-dir BRONZE_DIR
                        Directory for raw data
  --silver-dir SILVER_DIR
                        Directory for cleaned data
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Logging level
  --finess-only         Only run FINESS pipeline
  --iqss-only          Only run IQSS pipeline
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Ensure all tests pass (`pytest`)
5. Run code quality checks (`black`, `ruff`, `mypy`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📄 License

This project is provided as-is for educational and research purposes.

## 🙏 Acknowledgments

Data sources:
- [data.gouv.fr](https://www.data.gouv.fr/) - French open data portal
- FINESS data provided by the French Ministry of Health
- IQSS data from French healthcare quality agencies

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

**Built with ❤️ for better healthcare data**
