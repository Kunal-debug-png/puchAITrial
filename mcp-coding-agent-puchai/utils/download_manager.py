"""
download manager for mcp code generator

manages download links, expiration, and cleanup for generated mcp packages.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

logger = logging.getLogger(__name__)


class DownloadManager:
    """manages download functionality for generated mcp packages."""
    
    def __init__(self):
        """init download manager."""
        self.downloads_dir = Path("static/downloads")
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
    
    def setup_download_endpoints(self, app: FastAPI) -> None:
        """set up download endpoints in the fastapi app."""
        @app.get("/download/{download_id}")
        async def download_mcp(download_id: str):
            """serve generated mcp zip files."""
            return await self.serve_download(download_id)
        
        @app.get("/health")
        async def health_check():
            """health check endpoint for deployment platforms."""
            return {
                "status": "healthy",
                "service": "MCP Code Generator",
                "timestamp": datetime.now().isoformat()
            }
        
        @app.get("/download-stats")
        async def download_stats():
            """get download statistics (optional endpoint)."""
            from .zip_creator import get_download_stats
            return get_download_stats()
    
    async def serve_download(self, download_id: str) -> FileResponse:
        """serve a download file if it exists and hasn't expired."""
        logger.info(f"Download request for ID: {download_id}")
        
        # check if download record exists
        record_path = self.downloads_dir / f"{download_id}.json"
        if not record_path.exists():
            logger.warning(f"Download record not found: {download_id}")
            logger.debug(f"Looking for record at: {record_path}")
            # List available downloads for debugging
            available = list(self.downloads_dir.glob("*.json"))
            logger.debug(f"Available download records: {[f.stem for f in available]}")
            raise HTTPException(status_code=404, detail="Download not found")
        
        # load download record
        try:
            with open(record_path) as f:
                record = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read download record {download_id}: {e}")
            raise HTTPException(status_code=500, detail="Download record corrupted")
        
        # check if download has expired
        expires_at = datetime.fromisoformat(record["expires_at"])
        if datetime.now() > expires_at:
            logger.warning(f"Download expired: {download_id}")
            # Clean up expired files
            self._cleanup_expired_download(download_id, record)
            raise HTTPException(status_code=410, detail="Download has expired")
        
        # check if zip file exists
        zip_filename = record.get("zip_filename", f"mcp_{download_id}.zip")
        zip_path = self.downloads_dir / zip_filename
        
        if not zip_path.exists():
            logger.error(f"Zip file not found: {zip_path}")
            raise HTTPException(status_code=404, detail="Download file not found")
        
        # serve the file
        logger.info(f"Serving download: {zip_filename} ({zip_path.stat().st_size:,} bytes)")
        
        # generate a descriptive filename
        prompt_slug = self._create_filename_slug(record.get("prompt", "generated-mcp"))
        download_filename = f"{prompt_slug}_{download_id[:8]}.zip"
        
        return FileResponse(
            path=zip_path,
            filename=download_filename,
            media_type="application/zip",
            headers={
                "Content-Description": "Generated MCP Package",
                "X-Generation-ID": record.get("generation_id", "unknown")
            }
        )
    
    def _cleanup_expired_download(self, download_id: str, record: Dict) -> None:
        """clean up an expired download."""
        try:
            # remove zip file
            zip_filename = record.get("zip_filename", f"mcp_{download_id}.zip")
            zip_path = self.downloads_dir / zip_filename
            if zip_path.exists():
                zip_path.unlink()
                logger.debug(f"Removed expired zip: {zip_filename}")
            
            # remove record file
            record_path = self.downloads_dir / f"{download_id}.json"
            if record_path.exists():
                record_path.unlink()
                logger.debug(f"Removed expired record: {download_id}.json")
                
        except Exception as e:
            logger.warning(f"Error cleaning up expired download {download_id}: {e}")
    
    def _create_filename_slug(self, prompt: str) -> str:
        """create a safe filename slug from the user prompt."""
        # take first 30 characters and clean them up
        slug = prompt[:30].lower()
        
        # replace spaces and special chars with hyphens
        safe_chars = "abcdefghijklmnopqrstuvwxyz0123456789-"
        slug = "".join(c if c in safe_chars else "-" for c in slug)
        
        # remove consecutive hyphens and trim
        while "--" in slug:
            slug = slug.replace("--", "-")
        slug = slug.strip("-")
        
        # ensure not empty
        if not slug:
            slug = "generated-mcp"
        
        return slug
    
    def get_download_info(self, download_id: str) -> Optional[Dict]:
        """get info about a download without serving it."""
        record_path = self.downloads_dir / f"{download_id}.json"
        if not record_path.exists():
            return None
        
        try:
            with open(record_path) as f:
                record = json.load(f)
            
            # check if expired
            expires_at = datetime.fromisoformat(record["expires_at"])
            is_expired = datetime.now() > expires_at
            
            # check if file exists
            zip_filename = record.get("zip_filename", f"mcp_{download_id}.zip")
            zip_path = self.downloads_dir / zip_filename
            file_exists = zip_path.exists()
            
            return {
                "download_id": download_id,
                "generation_id": record.get("generation_id"),
                "created_at": record["created_at"],
                "expires_at": record["expires_at"],
                "is_expired": is_expired,
                "file_exists": file_exists,
                "file_count": record.get("file_count"),
                "zip_size": record.get("zip_size"),
                "prompt": record.get("prompt", "")[:100]  # Truncated
            }
            
        except Exception as e:
            logger.error(f"error reading download info {download_id}: {e}")
            return None
    
    async def cleanup_expired_downloads(self, max_age_hours: int = 24) -> int:
        """clean up expired downloads."""
        from .zip_creator import cleanup_expired_downloads
        return cleanup_expired_downloads(max_age_hours)
    
    def list_active_downloads(self) -> list[Dict]:
        """list all active (non-expired) downloads."""
        active_downloads = []
        
        for record_file in self.downloads_dir.glob("*.json"):
            download_id = record_file.stem
            info = self.get_download_info(download_id)
            
            if info and not info["is_expired"] and info["file_exists"]:
                active_downloads.append(info)
        
        # sort by creation time (newest first)
        active_downloads.sort(
            key=lambda x: x["created_at"], 
            reverse=True
        )
        
        return active_downloads
