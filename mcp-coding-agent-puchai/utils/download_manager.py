"""
download manager for mcp code generator

manages download links, expiration, and cleanup for generated mcp packages.
"""

import json
import logging
import traceback
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
        logger.info(f"[DOWNLOAD] Request for ID: {download_id}")
        
        # check if download record exists
        record_path = self.downloads_dir / f"{download_id}.json"
        logger.debug(f"[DOWNLOAD] Looking for record at: {record_path} (exists: {record_path.exists()})")
        if not record_path.exists():
            logger.warning(f"[DOWNLOAD] Record not found: {download_id}")
            # List available downloads for debugging
            available = list(self.downloads_dir.glob("*.json"))
            logger.warning(f"[DOWNLOAD] Available download records: {[f.stem for f in available]}")
            raise HTTPException(status_code=404, detail="Download not found")
        
        # load download record
        try:
            logger.debug(f"[DOWNLOAD] Reading record file: {record_path}")
            with open(record_path) as f:
                record = json.load(f)
            logger.debug(f"[DOWNLOAD] Record loaded successfully: {record.get('type', 'unknown type')}")
        except Exception as e:
            logger.error(f"[DOWNLOAD] Failed to read record {download_id}: {e}")
            logger.error(f"[DOWNLOAD] Exception details: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail="Download record corrupted")
        
        # check if download has expired
        expires_at = datetime.fromisoformat(record["expires_at"])
        current_time = datetime.now()
        logger.debug(f"[DOWNLOAD] Expiration check: current={current_time.isoformat()}, expires={expires_at.isoformat()}")
        if current_time > expires_at:
            logger.warning(f"[DOWNLOAD] Expired: {download_id} (expired {(current_time - expires_at).total_seconds()/60:.1f} minutes ago)")
            # Clean up expired files
            self._cleanup_expired_download(download_id, record)
            raise HTTPException(status_code=410, detail="Download has expired")
        else:
            logger.debug(f"[DOWNLOAD] Valid: expires in {(expires_at - current_time).total_seconds()/60:.1f} minutes")
        
        # check if file exists (could be ZIP or PDF)
        file_path = None
        media_type = "application/octet-stream"
        content_description = "Generated File"
        download_filename = None
        
        # Handle different file types
        if record.get("type") == "invoice_pdf":
            # PDF invoice file
            pdf_filename = record.get("pdf_filename", f"invoice_{download_id}.pdf")
            file_path = self.downloads_dir / pdf_filename
            media_type = "application/pdf"
            content_description = "Generated Invoice PDF"
            
            logger.debug(f"[DOWNLOAD] PDF file: {pdf_filename} (exists: {file_path.exists()})")
            
            # generate a descriptive filename for invoice
            buyer_slug = self._create_filename_slug(record.get("buyer_name", "invoice"))
            company_slug = self._create_filename_slug(record.get("company_name", "company"))
            invoice_number = record.get("invoice_number", download_id[:8])
            download_filename = f"{company_slug}_{buyer_slug}_{invoice_number}.pdf"
            logger.debug(f"[DOWNLOAD] Generated descriptive filename: {download_filename}")
        else:
            # Legacy ZIP file (MCP packages)
            zip_filename = record.get("zip_filename", f"mcp_{download_id}.zip")
            file_path = self.downloads_dir / zip_filename
            media_type = "application/zip"
            content_description = "Generated MCP Package"
            
            logger.debug(f"[DOWNLOAD] ZIP file: {zip_filename} (exists: {file_path.exists()})")
            
            # generate a descriptive filename for MCP
            prompt_slug = self._create_filename_slug(record.get("prompt", "generated-mcp"))
            download_filename = f"{prompt_slug}_{download_id[:8]}.zip"
            logger.debug(f"[DOWNLOAD] Generated descriptive filename: {download_filename}")
        
        if not file_path.exists():
            logger.error(f"[DOWNLOAD] File not found: {file_path}")
            # List all files in downloads directory for debugging
            all_files = list(self.downloads_dir.glob("*.*"))
            logger.error(f"[DOWNLOAD] Files in directory: {[f.name for f in all_files]}")
            raise HTTPException(status_code=404, detail="Download file not found")
        
        # serve the file
        file_size = file_path.stat().st_size
        logger.info(f"[DOWNLOAD] Serving file: {file_path.name} ({file_size:,} bytes)")
        logger.debug(f"[DOWNLOAD] Content type: {media_type}, filename: {download_filename}")
        
        return FileResponse(
            path=file_path,
            filename=download_filename,
            media_type=media_type,
            headers={
                "Content-Description": content_description,
                "X-Generation-ID": record.get("generation_id", "unknown")
            }
        )
    
    def _cleanup_expired_download(self, download_id: str, record: Dict) -> None:
        """clean up an expired download."""
        try:
            # remove file (could be ZIP or PDF)
            if record.get("type") == "invoice_pdf":
                # PDF invoice file
                pdf_filename = record.get("pdf_filename", f"invoice_{download_id}.pdf")
                file_path = self.downloads_dir / pdf_filename
                if file_path.exists():
                    file_path.unlink()
                    logger.debug(f"Removed expired PDF: {pdf_filename}")
            else:
                # Legacy ZIP file
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
            
            # check if file exists (could be ZIP or PDF)
            if record.get("type") == "invoice_pdf":
                pdf_filename = record.get("pdf_filename", f"invoice_{download_id}.pdf")
                file_path = self.downloads_dir / pdf_filename
            else:
                zip_filename = record.get("zip_filename", f"mcp_{download_id}.zip")
                file_path = self.downloads_dir / zip_filename
            
            file_exists = file_path.exists()
            
            return {
                "download_id": download_id,
                "generation_id": record.get("generation_id"),
                "created_at": record["created_at"],
                "expires_at": record["expires_at"],
                "is_expired": is_expired,
                "file_exists": file_exists,
                "file_count": record.get("file_count"),
                "file_size": record.get("zip_size", record.get("pdf_size", 0)),
                "file_type": record.get("type", "zip"),
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
