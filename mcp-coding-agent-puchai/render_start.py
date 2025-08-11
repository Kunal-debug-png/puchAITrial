#!/usr/bin/env python3
"""
render.com startup script for invoice pdf generator

starts the fastapi app for deployment on render as a persistent web service.
"""

import os
import sys
import asyncio
from pathlib import Path

# add project root to python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import mcp_generator

if __name__ == "__main__":
    # get port from env (render sets this)
    port = int(os.environ.get("PORT", 8086))
    
    # run the invoice server
    async def run_invoice_server():
        print("\n" + "=" * 60)
        print("INVOICE PDF GENERATOR SERVER")
        print("=" * 60)
        print(f"[OK] Running on port: {port}")
        print(f"[OK] Environment: {'Render' if 'RENDER' in os.environ else 'Local'}")
        print("=" * 60)
        
        # import the configured mcp server (initialized globally)
        from mcp_generator import mcp, download_manager
        from datetime import datetime
        
        # create downloads directory
        downloads_dir = Path("static/downloads")
        downloads_dir.mkdir(parents=True, exist_ok=True)
        print(f"Downloads directory: {downloads_dir.absolute()}")
        
        # add custom routes (as in main())
        @mcp.custom_route(methods=["GET"], path="/download/{download_id}")
        async def download_mcp_endpoint(request):
            # extract download_id from url path
            path_parts = request.url.path.split('/')
            download_id = path_parts[-1]  # Get the last part of the path
            return await download_manager.serve_download(download_id)
        
        @mcp.custom_route(methods=["GET"], path="/health")
        async def health_check():
            return {
                "status": "healthy",
                "service": "Invoice PDF Generator",
                "timestamp": datetime.now().isoformat()
            }
        
        @mcp.custom_route(methods=["GET"], path="/download-stats")
        async def download_stats():
            from utils.zip_creator import get_download_stats
            from utils.pdf_creator import get_pdf_download_stats
            
            zip_stats = get_download_stats()
            pdf_stats = get_pdf_download_stats()
            
            return {
                "zip_files": zip_stats,
                "pdf_files": pdf_stats,
                "total_files": zip_stats["total_downloads"] + pdf_stats["total_pdfs"],
                "total_size": zip_stats["total_size"] + pdf_stats["total_size"],
                "total_active": zip_stats["active_downloads"] + pdf_stats["active_pdfs"]
            }
        
        print("=" * 60)
        print(f"Downloads: {os.environ.get('DOWNLOAD_BASE_URL', 'Not Set')}/download/")
        print("=" * 60)
        
        # start server with render port
        await mcp.run_async("streamable-http", host="0.0.0.0", port=port)
    
    # run the invoice server
    asyncio.run(run_invoice_server())
