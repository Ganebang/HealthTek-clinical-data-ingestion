# Data Exploration Notebooks

This folder contains Jupyter notebooks for exploring the HealthTek clinical data at different stages of the pipeline.

## 📓 Notebooks

### Bronze Layer (Raw Data)

1. **[01_bronze_finess_exploration.ipynb](01_bronze_finess_exploration.ipynb)**
   - Explores raw FINESS establishment data
   - Shows file structure before transformation
   - Analyzes null values and data distributions

2. **[02_bronze_iqss_exploration.ipynb](02_bronze_iqss_exploration.ipynb)**
   - Explores raw IQSS quality indicator data
   - Configurable year selection
   - Shows categorical values before cleaning (with numbered prefixes)

### Silver Layer (Cleaned Data)

3. **[03_silver_finess_exploration.ipynb](03_silver_finess_exploration.ipynb)**
   - Explores cleaned FINESS data
   - Verifies transformations (SIRET/FINESS formatting, text cleaning)
   - Shows data quality improvements

4. **[04_silver_iqss_exploration.ipynb](04_silver_iqss_exploration.ipynb)**
   - Explores cleaned IQSS data
   - Verifies categorical cleaning (Obligatoire/Facultatif, Oui/Non)
   - Analyzes numeric conversions and normalization

## 🚀 Usage

### Installation

Make sure you have Jupyter installed:

```bash
pip install jupyter notebook
```

### Running Notebooks

1. **Start Jupyter Notebook:**
   ```bash
   cd notebooks
   jupyter notebook
   ```

2. **Or use JupyterLab:**
   ```bash
   jupyter lab
   ```

3. **Or use VS Code:**
   - Open any `.ipynb` file in VS Code
   - VS Code will automatically activate the Jupyter extension

### Before Running

Make sure you've run the data pipeline first to have data available:

```bash
# From project root
python main.py --years 2023  # or any year you want to explore
```

## 📊 What You'll Learn

- **Data Structure**: Column names, types, and counts
- **Data Quality**: Null values, completeness
- **Transformations**: Before/after comparisons
- **Distributions**: Geographic, categorical distributions
- **Sample Data**: Random records for manual inspection

## 💡 Tips

- Change the `YEAR` variable in IQSS notebooks to explore different years
- All notebooks include data quality checks
- Use the Bronze notebooks to understand the raw data API format
- Use the Silver notebooks to verify your transformations are working correctly

## 🔄 Workflow

```
01_bronze_finess → 03_silver_finess  (Compare FINESS transformations)
02_bronze_iqss   → 04_silver_iqss    (Compare IQSS transformations)
```

This helps you understand exactly what the cleaning pipeline does to your data!
