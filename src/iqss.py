"""
IQSS (Indicateurs de Qualité et de Sécurité des Soins) data source.

Downloads quality and safety indicators data from French health data portal.
"""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import config
from .base import DataSource, DownloadError, RefreshCheckError

logger = logging.getLogger("healthtek.iqss")


class IQSSSource(DataSource):
    """
    Data source for IQSS (quality and safety indicators).
    
    Downloads annual IQSS data from data.gouv.fr for a specific year.
    """

    def __init__(self, annee: int, base_dir: Optional[str] = None):
        """
        Initialize IQSS source for a specific year.
        
        Args:
            annee: Year to download (e.g., 2023)
            base_dir: Optional base directory for downloads
            
        Raises:
            ValueError: If year is invalid
        """
        if not (2015 <= annee <= datetime.now().year):
            raise ValueError(
                f"Invalid year {annee}. Must be between 2015 and {datetime.now().year}"
            )
            
        super().__init__(name=f"IQSS-{annee}")
        self.annee = annee
        
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = config.get_bronze_path("iqss")
            
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.meta_file = self.base_dir / f"{self.annee}.last_modified"
        logger.debug(f"Initialized IQSS source for year {annee} in {self.base_dir}")

    @property
    def marker_file(self) -> Path:
        """Path to marker file indicating successful download."""
        return self.base_dir / f"{self.annee}.done"

    @property
    def year_directory(self) -> Path:
        """Directory for this year's data."""
        return self.base_dir / str(self.annee)

    def _get_local_last_modified(self) -> Optional[str]:
        """Get the locally stored last_modified timestamp."""
        if not self.meta_file.exists():
            return None
        try:
            return self.meta_file.read_text().strip()
        except Exception as e:
            logger.warning(f"Failed to read last_modified file: {e}")
            return None

    def _get_remote_last_modified(self) -> str:
        """Fetch the remote dataset's last_modified timestamp."""
        url = config.IQSS_API_URL_TEMPLATE.format(annee=self.annee)
        try:
            resp = self.session.get(url)
            resp.raise_for_status()
            data = resp.json()
            return data.get("last_modified", "")
        except Exception as e:
            raise RefreshCheckError(f"Failed to fetch IQSS metadata for {self.annee}: {e}") from e

    def should_refresh(self) -> bool:
        """
        Check if IQSS data needs to be downloaded.
        
        Returns:
            True if marker doesn't exist OR remote timestamp > local timestamp.
        """
        if not self.marker_file.exists():
            logger.debug(f"Year {self.annee}: No marker file, refresh needed.")
            return True
            
        remote = self._get_remote_last_modified()
        local = self._get_local_last_modified()
        
        if not local:
            logger.debug(f"Year {self.annee}: No local timestamp, refresh needed.")
            return True
            
        needs_refresh = remote != local
        if needs_refresh:
            logger.info(f"Year {self.annee}: Update detected (Local: {local}, Remote: {remote})")
        else:
            logger.debug(f"Year {self.annee}: Up to date.")
            
        return needs_refresh

    def download(self) -> None:
        """
        Download IQSS data for the configured year.
        
        Fetches dataset metadata from API and downloads the main results file.
        Creates marker file upon successful completion.
        
        Raises:
            DownloadError: If download fails or no suitable file is found
        """
        url = config.IQSS_API_URL_TEMPLATE.format(annee=self.annee)
        logger.info(f"Fetching IQSS metadata from: {url}")
        
        try:
            resp = self.session.get(url)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise DownloadError(f"Failed to fetch IQSS metadata for {self.annee}: {e}") from e

        # Create year directory
        self.year_directory.mkdir(parents=True, exist_ok=True)

        # Find the best results file
        best_resource = None
        best_priority = -1
        
        # Priority patterns (higher is better)
        # 2: resultats + esatisca + mco (The "good" files)
        # 1: resultats + iqss (Fallback)
        # 0: No match
        
        for res in data.get("resources", []):
            title = res.get("title", "").lower()
            
            # Basic validation
            if "resultats" not in title or "open-data" not in title:
                continue
                
            # Check for year if present in title (some files might not have it or have it differently, 
            # but usually they do)
            if str(self.annee) not in title:
                continue

            priority = -1
            if "esatisca" in title and "mco" in title:
                priority = 2
            elif "iqss" in title:
                priority = 1
            
            if priority > best_priority:
                best_priority = priority
                best_resource = res
                
        if best_resource:
            title = best_resource.get("title")
            link = best_resource.get("url")
            logger.info(f"Found best matching file: {title} (Priority: {best_priority})")
            
            try:
                # Download file
                logger.info(f"Downloading from: {link}")
                file_resp = self.session.get(link)
                file_resp.raise_for_status()

                # Determine file extension
                ext = ".csv" if link.endswith(".csv") else ".xlsx"
                filepath = self.year_directory / f"resultats_iqss_{self.annee}{ext}"

                # Save file
                with open(filepath, "wb") as f:
                    f.write(file_resp.content)
                
                file_size_mb = len(file_resp.content) / (1024 * 1024)
                logger.info(f"Saved {file_size_mb:.2f} MB to: {filepath}")

                # Create marker file
                with open(self.marker_file, "w") as f:
                    f.write(datetime.utcnow().isoformat())
                    
                # Update last_modified metadata
                remote_last_modified = data.get("last_modified", "")
                with open(self.meta_file, "w") as f:
                    f.write(remote_last_modified)
                
                logger.info(f"Successfully downloaded IQSS data for {self.annee} (Updated: {remote_last_modified})")
                return
                
            except Exception as e:
                raise DownloadError(f"Failed to download IQSS file: {e}") from e

        # No suitable file found
        raise DownloadError(
            f"No IQSS results file found for year {self.annee}. "
            f"Check that the dataset exists on data.gouv.fr"
        )
