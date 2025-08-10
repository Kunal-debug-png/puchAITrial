"""
zip creator for mcp code generator

creates downloadable zip packages containing generated mcp projects.
"""

import hashlib
import json
import logging
import os
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict
from dotenv import dotenv_values

logger = logging.getLogger(__name__)


async def create_download_zip(files: Dict[str, str], prompt: str, generation_id: str) -> str:
    """create a downloadable zip package containing all generated files."""
    # ensure downloads directory exists
    downloads_dir = Path("static/downloads")
    downloads_dir.mkdir(parents=True, exist_ok=True)
    
    # generate unique download id
    download_id = _generate_download_id(prompt, generation_id)
    zip_filename = f"mcp_{download_id}.zip"
    zip_path = downloads_dir / zip_filename
    
    logger.info(f"[{generation_id}] creating zip package: {zip_filename}")
    
    try:
        # create zip file with all generated files
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filename, content in files.items():
                zipf.writestr(filename, content)
                logger.debug(f"[{generation_id}] added {filename} to zip ({len(content)} bytes)")
            
            # add generation metadata
            metadata = _create_metadata(prompt, generation_id, files)
            zipf.writestr("GENERATION_INFO.json", json.dumps(metadata, indent=2))
        
        # create download record
        download_record = {
            "id": download_id,
            "generation_id": generation_id,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
            "prompt": prompt[:200],  # Truncated for storage
            "file_count": len(files),
            "zip_size": zip_path.stat().st_size,
            "zip_filename": zip_filename
        }
        
        # save download record
        record_path = downloads_dir / f"{download_id}.json"
        with open(record_path, 'w') as f:
            json.dump(download_record, f, indent=2)
        
        # construct download url (prefer .env, fallback system env)
        env_vars = dotenv_values(".env")
        base_url = env_vars.get("DOWNLOAD_BASE_URL") or os.environ.get("DOWNLOAD_BASE_URL", "http://localhost:8086")
        download_url = f"{base_url}/download/{download_id}"
        
        logger.info(f"[{generation_id}] zip package created: {zip_path.stat().st_size:,} bytes")
        return download_url
        
    except Exception as e:
        logger.error(f"[{generation_id}] failed to create zip package: {e}")
        # clean up partial files
        if zip_path.exists():
            zip_path.unlink()
        raise


def _generate_download_id(prompt: str, generation_id: str) -> str:
    """generate a unique download id."""
    # Create a hash from prompt, generation ID, and current time
    content = f"{prompt}{generation_id}{time.time()}".encode()
    return hashlib.sha256(content).hexdigest()[:16]


def _create_metadata(prompt: str, generation_id: str, files: Dict[str, str]) -> Dict:
    """create metadata about the generation."""
    return {
        "generation_info": {
            "id": generation_id,
            "prompt": prompt,
            "generated_at": datetime.now().isoformat(),
            "total_files": len(files),
            "total_size": sum(len(content) for content in files.values())
        },
        "files_manifest": {
            filename: {
                "size": len(content),
                "type": _get_file_type(filename),
                "description": _get_file_description(filename)
            }
            for filename, content in files.items()
        },
        "setup_instructions": {
            "1": "Extract this zip file to your desired directory",
            "2": "Copy .env.example to .env and fill in your API keys",
            "3": "Install dependencies: pip install -r requirements.txt",
            "4": "Run locally: python mcp_server.py",
            "5": "Deploy using the included deployment configuration",
            "6": "Connect to Puch AI: /mcp connect https://your-url/mcp/ your_token"
        },
        "generated_by": "MCP Code Generator",
        "documentation": "See README.md and DEPLOYMENT.md for detailed instructions"
    }


def _get_file_type(filename: str) -> str:
    """get the type description for a file."""
    if filename.endswith('.py'):
        return "Python source code"
    elif filename == 'requirements.txt':
        return "Python dependencies"
    elif filename == 'pyproject.toml':
        return "Project configuration"
    elif filename.endswith('.yaml') or filename.endswith('.yml'):
        return "YAML configuration"
    elif filename.endswith('.json'):
        return "JSON configuration"
    elif filename.endswith('.md'):
        return "Markdown documentation"
    elif filename.startswith('.env'):
        return "Environment variables template"
    else:
        return "Configuration file"


def _get_file_description(filename: str) -> str:
    """get a description for a file."""
    descriptions = {
        "mcp_server.py": "Main MCP server implementation",
        "requirements.txt": "Python package dependencies",
        "pyproject.toml": "Project metadata and build configuration",
        "render.yaml": "Render deployment configuration",
        "render_start.py": "Render startup script",
        "vercel.json": "Vercel deployment configuration",
        ".env.example": "Environment variables template",
        "README.md": "Project documentation and setup guide",
        "DEPLOYMENT.md": "Deployment instructions and guide",
        "database.py": "Database connection and models",
        "scheduler.py": "Background task scheduler"
    }
    
    return descriptions.get(filename, "Project file")


def cleanup_expired_downloads(max_age_hours: int = 24) -> int:
    """clean up expired download files."""
    downloads_dir = Path("static/downloads")
    if not downloads_dir.exists():
        return 0
    
    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    cleaned_count = 0
    
    logger.info(f"Cleaning up downloads older than {max_age_hours} hours")
    
    # clean up zip files and their records
    for json_file in downloads_dir.glob("*.json"):
        try:
            with open(json_file) as f:
                record = json.load(f)
            
            created_at = datetime.fromisoformat(record["created_at"])
            if created_at < cutoff_time:
                # Remove zip file
                zip_filename = record.get("zip_filename")
                if zip_filename:
                    zip_path = downloads_dir / zip_filename
                    if zip_path.exists():
                        zip_path.unlink()
                        logger.debug(f"Removed expired zip: {zip_filename}")
                
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
    
    logger.info(f"Cleaned up {cleaned_count} expired downloads")
    return cleaned_count


def get_download_stats() -> Dict:
    """get statistics about current downloads."""
    downloads_dir = Path("static/downloads")
    if not downloads_dir.exists():
        return {"total_downloads": 0, "total_size": 0, "active_downloads": 0}
    
    total_downloads = 0
    total_size = 0
    active_downloads = 0
    
    for zip_file in downloads_dir.glob("*.zip"):
        total_downloads += 1
        total_size += zip_file.stat().st_size
        
        # check if still active (not expired)
        record_file = downloads_dir / f"{zip_file.stem.replace('mcp_', '')}.json"
        if record_file.exists():
            try:
                with open(record_file) as f:
                    record = json.load(f)
                expires_at = datetime.fromisoformat(record["expires_at"])
                if expires_at > datetime.now():
                    active_downloads += 1
            except:
                pass
    
    return {
        "total_downloads": total_downloads,
        "total_size": total_size,
        "active_downloads": active_downloads
    }
