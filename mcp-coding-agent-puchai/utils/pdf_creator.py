"""
pdf creator for invoice pdf generator

creates downloadable pdf packages containing generated invoice pdfs.
"""

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict
from dotenv import dotenv_values

logger = logging.getLogger(__name__)


async def create_invoice_pdf(
    pdf_data: bytes,
    buyer_name: str,
    company_name: str,
    amount: float,
    date: str,
    generation_id: str
) -> str:
    """create a downloadable pdf package containing the generated invoice."""
    # ensure downloads directory exists
    downloads_dir = Path("static/downloads")
    downloads_dir.mkdir(parents=True, exist_ok=True)
    
    # generate unique download id
    download_id = _generate_download_id(buyer_name, company_name, generation_id)
    pdf_filename = f"invoice_{download_id}.pdf"
    pdf_path = downloads_dir / pdf_filename
    
    logger.info(f"[{generation_id}] creating pdf package: {pdf_filename}")
    
    try:
        # save pdf file
        with open(pdf_path, 'wb') as f:
            f.write(pdf_data)
        
        logger.debug(f"[{generation_id}] saved invoice PDF ({len(pdf_data)} bytes)")
        
        # create download record
        download_record = {
            "id": download_id,
            "generation_id": generation_id,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
            "buyer_name": buyer_name,
            "company_name": company_name,
            "amount": amount,
            "date": date,
            "pdf_size": len(pdf_data),
            "pdf_filename": pdf_filename,
            "invoice_number": f"INV-{generation_id.split('_')[1] if '_' in generation_id else generation_id}",
            "type": "invoice_pdf"
        }
        
        # save download record
        record_path = downloads_dir / f"{download_id}.json"
        with open(record_path, 'w') as f:
            json.dump(download_record, f, indent=2)
        
        # construct download url (prefer .env, fallback system env)
        env_vars = dotenv_values(".env")
        base_url = env_vars.get("DOWNLOAD_BASE_URL") or os.environ.get("DOWNLOAD_BASE_URL", "http://localhost:8086")
        download_url = f"{base_url}/download/{download_id}"
        
        logger.info(f"[{generation_id}] pdf package created: {pdf_path.stat().st_size:,} bytes")
        return download_url
        
    except Exception as e:
        logger.error(f"[{generation_id}] failed to create pdf package: {e}")
        # clean up partial files
        if pdf_path.exists():
            pdf_path.unlink()
        raise


def _generate_download_id(buyer_name: str, company_name: str, generation_id: str) -> str:
    """generate a unique download id."""
    # Create a hash from buyer, company, generation ID, and current time
    content = f"{buyer_name}{company_name}{generation_id}{time.time()}".encode()
    return hashlib.sha256(content).hexdigest()[:16]


def cleanup_expired_pdf_downloads(max_age_hours: int = 24) -> int:
    """clean up expired pdf download files."""
    downloads_dir = Path("static/downloads")
    if not downloads_dir.exists():
        return 0
    
    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    cleaned_count = 0
    
    logger.info(f"Cleaning up PDF downloads older than {max_age_hours} hours")
    
    # clean up pdf files and their records
    for json_file in downloads_dir.glob("*.json"):
        try:
            with open(json_file) as f:
                record = json.load(f)
            
            # only process invoice PDF records
            if record.get("type") != "invoice_pdf":
                continue
            
            created_at = datetime.fromisoformat(record["created_at"])
            if created_at < cutoff_time:
                # Remove pdf file
                pdf_filename = record.get("pdf_filename")
                if pdf_filename:
                    pdf_path = downloads_dir / pdf_filename
                    if pdf_path.exists():
                        pdf_path.unlink()
                        logger.debug(f"Removed expired PDF: {pdf_filename}")
                
                # Remove record file
                json_file.unlink()
                logger.debug(f"Removed expired record: {json_file.name}")
                cleaned_count += 1
                
        except Exception as e:
            logger.warning(f"Error processing {json_file}: {e}")
            # Remove corrupted record files
            try:
                json_file.unlink()
                cleaned_count += 1
            except:
                pass
    
    logger.info(f"Cleaned up {cleaned_count} expired PDF downloads")
    return cleaned_count


def get_pdf_download_stats() -> Dict:
    """get statistics about current pdf downloads."""
    downloads_dir = Path("static/downloads")
    if not downloads_dir.exists():
        return {"total_pdfs": 0, "total_size": 0, "active_pdfs": 0}
    
    total_pdfs = 0
    total_size = 0
    active_pdfs = 0
    
    for pdf_file in downloads_dir.glob("*.pdf"):
        if pdf_file.name.startswith("invoice_"):
            total_pdfs += 1
            total_size += pdf_file.stat().st_size
            
            # check if still active (not expired)
            download_id = pdf_file.stem.replace('invoice_', '')
            record_file = downloads_dir / f"{download_id}.json"
            if record_file.exists():
                try:
                    with open(record_file) as f:
                        record = json.load(f)
                    expires_at = datetime.fromisoformat(record["expires_at"])
                    if expires_at > datetime.now():
                        active_pdfs += 1
                except:
                    pass
    
    return {
        "total_pdfs": total_pdfs,
        "total_size": total_size,
        "active_pdfs": active_pdfs
    }
