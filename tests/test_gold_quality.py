"""
Tests for Gold layer: Establishment Quality Fact Table.
"""


import pandas as pd
import pytest

from transform.gold.fact_establishment_quality import create_fact_establishment_quality


@pytest.mark.unit
class TestGoldQuality:
    """Test suite for fact_establishment_quality transformation."""

    @pytest.fixture
    def mock_silver_data(self, temp_dir):
        """Create mock Silver data for FINESS and IQSS."""
        finess_dir = temp_dir / "finess"
        iqss_dir = temp_dir / "iqss"

        finess_dir.mkdir(parents=True)
        iqss_dir.mkdir(parents=True)

        # 1. Mock FINESS data
        finess_csv = finess_dir / "finess.csv"
        finess_df = pd.DataFrame(
            {
                "finess": ["010000001", "020000002"],
                "rs": ["Hopital A", "Hopital B"],
                "commune": ["Paris", "Lyon"],
            }
        )
        finess_df.to_csv(finess_csv, sep=";", index=False, encoding="utf-8-sig")

        # 2. Mock IQSS data (2022 and 2023)
        # 2022: Hopital A scores 80
        # 2023: Hopital A scores 90 (Improvement), Hopital B scores 70 (No prev history)

        # IQSS 2022
        iqss_2022_dir = iqss_dir / "2022"
        iqss_2022_dir.mkdir()
        df_2022 = pd.DataFrame(
            {
                "finess": ["010000001"],
                "score_all_ajust": [80.0],
                "participation": ["Participe"],
                "depot": ["Déposé"],
                "evolution": [""],
            }
        )
        df_2022.to_csv(iqss_2022_dir / "resultats_iqss_2022.csv", sep=";", index=False)

        # IQSS 2023
        iqss_2023_dir = iqss_dir / "2023"
        iqss_2023_dir.mkdir()
        df_2023 = pd.DataFrame(
            {
                "finess": ["010000001", "020000002"],
                "score_all_ssr_ajust": [90.0, 70.0],  # Note: column name variation test
                "participation": ["Participe", "Participe"],
                "depot": ["Déposé", "Déposé"],
                "evolution": ["3-Amélioration", ""],
            }
        )
        df_2023.to_csv(iqss_2023_dir / "resultats_iqss_2023.csv", sep=";", index=False)

        return finess_csv, iqss_dir

    def test_create_fact_quality_success(self, temp_dir, mock_silver_data):
        """Test successful creation of fact table with evolution logic."""
        finess_path, iqss_dir = mock_silver_data
        output_path = temp_dir / "gold" / "fact_quality.parquet"

        metrics = create_fact_establishment_quality(finess_path, iqss_dir, output_path)

        assert metrics["output_rows"] == 3  # 1 (2022) + 2 (2023)
        assert output_path.exists()

        # Load result to check logic
        df = pd.read_parquet(output_path)

        # Check Hopital A (010000001) for 2023
        row_2023_df = df[(df["finess"] == "010000001") & (df["year"] == 2023)]
        if len(row_2023_df) == 0:
            pytest.fail("Row not found!")
        row_2023 = row_2023_df.iloc[0]

        # 1. Check Score Standardization (score_all_ajust vs score_all_ssr_ajust)
        assert row_2023["overall_score"] == 90.0

        # 2. Check Assessment of Previous Score
        assert row_2023["previous_overall_score"] == 80.0

        # 3. Check Evolution Diff Calculation (90 - 80 = 10)
        assert row_2023["score_evolution_diff"] == 10.0

        # 4. Check Custom Trend Logic (Diff >= 1.0 -> Improvement)
        assert row_2023["evolution_custom_trend"] == "Improvement"

        # 5. Check Evolution Label Cleaning ("3-Amélioration" -> "Amélioration")
        assert row_2023["evolution_label"] == "Amélioration"

    def test_create_fact_quality_decline(self, temp_dir, mock_silver_data):
        """Test calculation of declining scores."""
        finess_path, iqss_dir = mock_silver_data

        # Add 2024 data where Hopital A drops to 85
        iqss_2024_dir = iqss_dir / "2024"
        iqss_2024_dir.mkdir()
        df_2024 = pd.DataFrame({"finess": ["010000001"], "score_all_ssr_ajust": [85.0]})
        df_2024.to_csv(iqss_2024_dir / "resultats_iqss_2024.csv", sep=";", index=False)

        output_path = temp_dir / "gold" / "fact_quality.parquet"
        create_fact_establishment_quality(finess_path, iqss_dir, output_path)

        df = pd.read_parquet(output_path)
        row_2024 = df[(df["finess"] == "010000001") & (df["year"] == 2024)].iloc[0]

        # Previous (2023) was 90.0
        assert row_2024["previous_overall_score"] == 90.0
        assert row_2024["score_evolution_diff"] == -5.0
        assert row_2024["evolution_custom_trend"] == "Decline"

    def test_create_fact_quality_stable(self, temp_dir, mock_silver_data):
        """Test calculation of stable scores."""
        finess_path, iqss_dir = mock_silver_data

        # Add 2024 data where Hopital A stays at 90.5 (from 90.0 - small diff)
        # Custom logic: Diff < 1.0 and > -1.0 is Stable
        iqss_2024_dir = iqss_dir / "2024"
        iqss_2024_dir.mkdir()
        df_2024 = pd.DataFrame({"finess": ["010000001"], "score_all_ssr_ajust": [90.5]})
        df_2024.to_csv(iqss_2024_dir / "resultats_iqss_2024.csv", sep=";", index=False)

        output_path = temp_dir / "gold" / "fact_quality.parquet"
        create_fact_establishment_quality(finess_path, iqss_dir, output_path)

        df = pd.read_parquet(output_path)
        row_2024 = df[(df["finess"] == "010000001") & (df["year"] == 2024)].iloc[0]

        assert row_2024["score_evolution_diff"] == 0.5
        assert row_2024["evolution_custom_trend"] == "Stable"

    def test_create_fact_quality_no_files(self, temp_dir):
        """Test behavior when no IQSS files exist."""
        finess_path = temp_dir / "finess.csv"
        iqss_dir = temp_dir / "empty_iqss"
        iqss_dir.mkdir()
        output_path = temp_dir / "gold" / "output.parquet"

        metrics = create_fact_establishment_quality(finess_path, iqss_dir, output_path)

        assert metrics["output_rows"] == 0
