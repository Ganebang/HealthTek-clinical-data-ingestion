"""
FINESS (Fichier National des Établissements Sanitaires et Sociaux) data source.

Downloads French healthcare facility registry data.
"""
import logging
from pathlib import Path
from typing import Optional

from config import config
from .base import DataSource, DownloadError, RefreshCheckError

logger = logging.getLogger("healthtek.finess")


class FinessSource(DataSource):
    """
    Data source for FINESS (French healthcare facility registry).
    
    Downloads the latest FINESS establishment file from data.gouv.fr.
    Uses last_modified timestamp to determine if refresh is needed.
    """

    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize FINESS source.
        
        Args:
            base_dir: Optional base directory for downloads
        """
        super().__init__(name="FINESS")
        
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = config.get_bronze_path("finess")
            
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.meta_file = self.base_dir / "last_modified.txt"
        logger.debug(f"Initialized FINESS source in {self.base_dir}")

    def _get_local_last_modified(self) -> Optional[str]:
        """
        Get the locally stored last_modified timestamp.
        
        Returns:
            Last modified timestamp or None if not available
        """
        if not self.meta_file.exists():
            return None
        
        try:
            return self.meta_file.read_text().strip()
        except Exception as e:
            logger.warning(f"Failed to read last_modified file: {e}")
            return None

    def _get_remote_last_modified(self) -> str:
        """
        Fetch the remote dataset's last_modified timestamp.
        
        Returns:
            Remote last modified timestamp
            
        Raises:
            RefreshCheckError: If fetching metadata fails
        """
        try:
            resp = self.session.get(config.FINESS_API_URL)
            resp.raise_for_status()
            data = resp.json()
            return data.get("last_modified", "")
        except Exception as e:
            raise RefreshCheckError(f"Failed to fetch FINESS metadata: {e}") from e

    def should_refresh(self) -> bool:
        """
        Check if FINESS data needs to be refreshed.
        
        Compares local and remote last_modified timestamps.
        
        Returns:
            True if refresh is needed, False otherwise
            
        Raises:
            RefreshCheckError: If fetching remote metadata fails
        """
        remote = self._get_remote_last_modified()
        local = self._get_local_last_modified()
        
        needs_refresh = remote != local
        logger.debug(
            f"Refresh check - Local: {local}, Remote: {remote}, "
            f"Needs refresh: {needs_refresh}"
        )
        return needs_refresh

    def download(self) -> None:
        """
        Download FINESS establishment data.
        
        Fetches the latest FINESS file and saves it locally.
        Updates the last_modified metadata file.
        
        Raises:
            DownloadError: If download fails or no suitable file is found
        """
        logger.info(f"Fetching FINESS metadata from: {config.FINESS_API_URL}")
        
        try:
            resp = self.session.get(config.FINESS_API_URL)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise DownloadError(f"Failed to fetch FINESS metadata: {e}") from e

        # Find the FINESS establishment file
        for res in data.get("resources", []):
            title = res.get("title", "").lower()
            link = res.get("url", "")

            if "finess" in title and "etabl" in title:
                logger.info(f"Found matching file: {res.get('title')}")
                
                try:
                    # Download file
                    logger.info(f"Downloading from: {link}")
                    file_resp = self.session.get(link)
                    file_resp.raise_for_status()

                    # Determine file extension
                    ext = ".csv" if link.endswith(".csv") else ".xlsx"
                    filepath = self.base_dir / f"finess{ext}"

                    # Save file
                    with open(filepath, "wb") as f:
                        f.write(file_resp.content)
                    
                    file_size_mb = len(file_resp.content) / (1024 * 1024)
                    logger.info(f"Saved {file_size_mb:.2f} MB to: {filepath}")

                    # Update metadata file
                    last_modified = data.get("last_modified", "")
                    with open(self.meta_file, "w") as f:
                        f.write(last_modified)
                    
                    logger.info(f"Successfully downloaded FINESS data (last_modified: {last_modified})")
                    return
                    
                except Exception as e:
                    raise DownloadError(f"Failed to download FINESS file: {e}") from e

        # No suitable file found
        raise DownloadError(
            "No FINESS establishment file found. "
            "Check that the dataset exists on data.gouv.fr"
        )
