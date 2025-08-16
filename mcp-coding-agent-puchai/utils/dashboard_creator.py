"""
Dashboard Creator utility for CSV Dashboard Generator

Saves generated dashboard HTML files and manages download links.
"""

import logging
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)


async def create_dashboard_html(
    html_content: str,
    dashboard_title: str,
    csv_filename: str,
    analysis: Dict,
    generation_id: str
) -> str:
    """Save dashboard HTML and return download URL."""
    
    try:
        # Create dashboards directory
        dashboard_dir = Path("static/dashboards")
        dashboard_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        safe_title = "".join(c for c in dashboard_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')[:50]  # Limit length
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_title}_{timestamp}.html"
        file_path = dashboard_dir / filename
        
        # Save HTML file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Log creation
        logger.info(f"[{generation_id}] Dashboard HTML saved: {file_path} ({len(html_content)} chars)")
        
        # Return download URL
        from urllib.parse import quote
        download_url = f"{os.environ.get('DOWNLOAD_BASE_URL', 'http://localhost:8086')}/dashboard/{quote(filename)}"
        
        return download_url
        
    except Exception as e:
        logger.error(f"[{generation_id}] Failed to save dashboard HTML: {e}")
        raise ValueError(f"Dashboard save failed: {str(e)}")


def get_dashboard_stats() -> Dict:
    """Get statistics about saved dashboards."""
    
    dashboard_dir = Path("static/dashboards")
    if not dashboard_dir.exists():
        return {
            "total_dashboards": 0,
            "total_size": 0,
            "active_dashboards": 0,
            "oldest_dashboard": None,
            "newest_dashboard": None
        }
    
    html_files = list(dashboard_dir.glob("*.html"))
    
    if not html_files:
        return {
            "total_dashboards": 0,
            "total_size": 0,
            "active_dashboards": 0,
            "oldest_dashboard": None,
            "newest_dashboard": None
        }
    
    # Calculate statistics
    total_size = sum(f.stat().st_size for f in html_files)
    
    # Get file timestamps
    file_times = [(f, f.stat().st_mtime) for f in html_files]
    file_times.sort(key=lambda x: x[1])
    
    oldest_file = file_times[0][0] if file_times else None
    newest_file = file_times[-1][0] if file_times else None
    
    # Count active dashboards (less than 7 days old)
    cutoff_time = datetime.now().timestamp() - (7 * 24 * 60 * 60)  # 7 days
    active_count = sum(1 for _, timestamp in file_times if timestamp > cutoff_time)
    
    return {
        "total_dashboards": len(html_files),
        "total_size": total_size,
        "active_dashboards": active_count,
        "oldest_dashboard": oldest_file.name if oldest_file else None,
        "newest_dashboard": newest_file.name if newest_file else None
    }


def cleanup_old_dashboards(days_old: int = 30) -> int:
    """Clean up dashboard files older than specified days."""
    
    dashboard_dir = Path("static/dashboards")
    if not dashboard_dir.exists():
        return 0
    
    cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
    removed_count = 0
    
    try:
        for html_file in dashboard_dir.glob("*.html"):
            if html_file.stat().st_mtime < cutoff_time:
                html_file.unlink()
                removed_count += 1
                logger.info(f"Cleaned up old dashboard: {html_file.name}")
        
        return removed_count
        
    except Exception as e:
        logger.error(f"Failed to cleanup old dashboards: {e}")
        return 0


async def serve_dashboard(dashboard_id: str):
    """Serve dashboard HTML file for download."""
    
    try:
        dashboard_dir = Path("static/dashboards")
        dashboard_path = dashboard_dir / dashboard_id
        
        if not dashboard_path.exists():
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Dashboard not found")
        
        # Read HTML content
        with open(dashboard_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content=html_content,
            headers={
                "Content-Disposition": f"inline; filename=\"{dashboard_id}\"",
                "Cache-Control": "max-age=3600"  # Cache for 1 hour
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to serve dashboard {dashboard_id}: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Dashboard serving failed")
