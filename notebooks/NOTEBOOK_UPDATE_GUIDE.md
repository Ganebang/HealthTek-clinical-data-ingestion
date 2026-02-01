# Notebook Update Guide - FINESS Column Schema Fix

This guide contains the corrected code snippets to update the FINESS exploration notebooks with the official 32-column schema from data.gouv.fr.

## 📋 What Changed

The FINESS data structure uses a **32-column schema** (31 after removing 'structureet'). The previous notebooks had incorrect column names causing data misalignment.

### Key Changes:
- Added: `complrs`, `compldistrib`, `departement`, `ligneacheminement`, `libcategetab`, `libcategagretab`, `dateautor`, `numuai`
- Removed: `compvoie2`, `cpostal`, `libregion`, `coordx`, `coordy`, `sourcecoord`, `etat`, `dateferm`

---

## 📓 1. Bronze FINESS Notebook (`01_bronze_finess_exploration.ipynb`)

### Cell to Update: "Apply column names"

Replace the entire cell that applies FINESS_COLUMNS with this:

```python
# Remove structureet column
df_bronze = df_bronze.iloc[:, 1:]

# Apply column names (official schema from data.gouv.fr)
# Source: https://www.data.gouv.fr/fr/datasets/finess-extraction-du-fichier-des-etablissements/
FINESS_COLUMNS = [
    "nofinesset",           # Numéro FINESS ET
    "nofinessej",           # Numéro FINESS EJ
    "rs",                   # Raison sociale
    "rslongue",             # Raison sociale longue
    "complrs",              # Complément de raison sociale
    "compldistrib",         # Complément de distribution
    "numvoie",              # Numéro de voie
    "typvoie",              # Type de voie
    "voie",                 # Libellé de voie
    "compvoie",             # Complément de voie
    "lieuditbp",            # Lieu-dit / BP
    "commune",              # Code Commune
    "departement",          # Département
    "libdepartement",       # Libellé département
    "ligneacheminement",    # Code Postal + Lib commune
    "telephone",            # Téléphone
    "telecopie",            # Télécopie
    "categetab",            # Catégorie d'établissement
    "libcategetab",         # Libellé catégorie d'établissement
    "categagretab",         # Catégorie d'agrégat d'établissement
    "libcategagretab",      # Libellé catégorie d'agrégat d'établissement
    "siret",                # Numéro de SIRET
    "codeape",              # Code APE
    "codemft",              # Code MFT
    "libmft",               # Libellé MFT
    "codesph",              # Code SPH
    "libsph",               # Libellé SPH
    "dateouv",              # Date d'ouverture
    "dateautor",            # Date d'autorisation
    "datemaj",              # Date de mise à jour
    "numuai"                # Numéro éducation nationale
]

df_bronze.columns = FINESS_COLUMNS[:len(df_bronze.columns)]

print(f"\n📊 Final Shape: {df_bronze.shape}")
print(f"\n📋 Columns ({len(df_bronze.columns)}):")
for i, col in enumerate(df_bronze.columns, 1):
    print(f"  {i:2}. {col}")
```

### Update Distribution Analysis Cells

If there's a cell checking `libregion`, update it to use `libdepartement` instead:

**OLD:**
```python
print("\n📊 Top 10 Regions:")
if 'libregion' in df_bronze.columns:
    print(df_bronze['libregion'].value_counts().head(10))
```

**NEW:**
```python
print("\n📊 Top 10 Departments:")
if 'libdepartement' in df_bronze.columns:
    print(df_bronze['libdepartement'].value_counts().head(10))
```

---

## 📓 2. Silver FINESS Notebook (`03_silver_finess_exploration.ipynb`)

The Silver notebook should work correctly as-is, since the cleaned data already has the correct schema applied by `transform/finess_cleaner.py`.

### Optional: Update Distribution Analysis

If there's a cell checking for regions, update it:

**Replace:**
```python
# Regional distribution
if 'libregion' in df_silver.columns:
    print("🗺️ Top 10 Regions by Establishment Count:")
    print(df_silver['libregion'].value_counts().head(10))
```

**With:**
```python
# Department distribution
if 'libdepartement' in df_silver.columns:
    print("🗺️ Top 10 Departments by Establishment Count:")
    print(df_silver['libdepartement'].value_counts().head(10))
```

---

## 🚀 How to Apply Updates

### Method 1: Using JupyterLab (Recommended)

1. **Open JupyterLab** at http://localhost:8888/lab
2. **Open** `01_bronze_finess_exploration.ipynb`
3. **Find** the cell with `FINESS_COLUMNS = [...]`
4. **Select all text** in that cell and **delete it**
5. **Copy-paste** the new code from this guide
6. **Save** the notebook (Ctrl+S or Cmd+S)
7. **Restart kernel and run all cells**: Kernel menu → Restart Kernel and Run All Cells

Repeat for `03_silver_finess_exploration.ipynb` if needed.

### Method 2: Text Editor

1. Close the notebook in JupyterLab first
2. Open the `.ipynb` file in a text editor
3. Search for `"FINESS_COLUMNS = ["` in the JSON
4. Carefully replace the array values
5. Save and reload in JupyterLab

**⚠️ Note:** Method 2 is error-prone - Method 1 is much safer!

---

## ✅ Verification

After updating, the notebooks should show:

### Bronze Notebook
- **Shape**: (204916, 31) - 204,916 rows, 31 columns
- **First column**: nofinesset (FINESS identifier)
- **Sample FINESS**: 010000024
- **Sample Name**: "CH DE FLEYRIAT" or similar

### Silver Notebook  
- **Shape**: (204916, 32) - includes normalized 'finess' column
- **All data properly aligned**: phone numbers in telephone, SIRET in siret, etc.
- **No duplicate column count warnings**

---

## 📚 Reference

**Official Documentation:**
- Dataset: https://www.data.gouv.fr/fr/datasets/finess-extraction-du-fichier-des-etablissements/
- GitHub Schema: https://github.com/ansforge/finess

**Updated Files in Pipeline:**
- `transform/finess_cleaner.py` - ✅ Already updated
- `notebooks/01_bronze_finess_exploration.ipynb` - ⚠️ Needs manual update
- `notebooks/03_silver_finess_exploration.ipynb` - ✅ Should work as-is

---

## 🆘 Troubleshooting

### "NameError: name 'df_bronze' is not defined"
**Cause:** Running cells out of order  
**Fix:** Restart kernel and run all cells from top to bottom

### "Column count mismatch"
**Cause:** Old column schema still in use  
**Fix:** Make sure you copied the entire FINESS_COLUMNS list from this guide

### Data still looks misaligned
**Cause:** Using old schema or didn't restart kernel  
**Fix:** 
1. Restart kernel (Kernel → Restart Kernel)
2. Clear all outputs (Edit → Clear All Outputs)
3. Run all cells from beginning

---

## 💡 Need Help?

If you encounter issues:
1. Check that all cells before the problematic one ran successfully
2. Verify you're using the exact column list from this guide
3. Re-run the main pipeline: `python main.py --finess-only`
4. Check logs in the terminal for any errors

**Happy data exploring! 🎉**
