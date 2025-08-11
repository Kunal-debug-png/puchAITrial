"""
invoice pdf generator server

ai-powered invoice pdf generator for puch ai. generates professional invoice pdfs from provided details.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Annotated, Optional
from pathlib import Path

from dotenv import dotenv_values
from fastmcp import FastMCP
from mcp import ErrorData, McpError
from mcp.types import INTERNAL_ERROR, TextContent
from pydantic import Field

from core.invoice_generator import InvoiceGenerator
from utils.pdf_creator import create_invoice_pdf
from utils.download_manager import DownloadManager
from fastapi import FastAPI

# configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

# load env vars (local .env and render)
env_vars = dotenv_values(".env")

def get_env_var(key: str, default: str = None) -> str:
    """get env var from .env or system (render fallback)."""
    return env_vars.get(key) or os.environ.get(key, default)

# required env vars (try .env first, then system env)
MY_NUMBER = get_env_var("MY_NUMBER")
AUTH_TOKEN = get_env_var("AUTH_TOKEN")
BL_WORKSPACE = get_env_var("BL_WORKSPACE")
BL_API_KEY = get_env_var("BL_API_KEY")
MORPH_API_KEY = get_env_var("MORPH_API_KEY")
OPENAI_API_KEY = get_env_var("OPENAI_API_KEY")
DOWNLOAD_BASE_URL = get_env_var("DOWNLOAD_BASE_URL", "https://run.blaxel.ai")

# Validate required environment variables
required_vars = {
    "MY_NUMBER": MY_NUMBER,
    "AUTH_TOKEN": AUTH_TOKEN,  # Required for MCP authentication
}

# optional blaxel vars (legacy features)
optional_vars = {
    "BL_WORKSPACE": BL_WORKSPACE,
    "BL_API_KEY": BL_API_KEY,
    "MORPH_API_KEY": MORPH_API_KEY,
}

missing_required = [name for name, value in required_vars.items() if not value]
missing_optional = [name for name, value in optional_vars.items() if not value]

if missing_required:
    logger.error(f"Missing required environment variables: {missing_required}")
    raise ValueError(f"Required environment variables not set: {missing_required}")

if missing_optional:
    logger.warning(f"Missing optional Blaxel environment variables: {missing_optional}")
    logger.warning("Blaxel features will be disabled, but core invoice generation will work.")

# init components
mcp = FastMCP("Invoice PDF Generator")
invoice_generator = InvoiceGenerator()
download_manager = DownloadManager()


@mcp.tool
async def validate() -> str:
    """return phone number for puch ai validation."""
    if not MY_NUMBER:
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message="MY_NUMBER not configured"
        ))
    return MY_NUMBER


@mcp.tool(description="Generate a professional invoice PDF")
async def generate_invoice(
    amount: Annotated[float, Field(description="Invoice amount in decimal format (e.g., 1250.00)")],
    buyer_name: Annotated[str, Field(description="Name of the buyer/client")],
    company_name: Annotated[str, Field(description="Company name issuing the invoice")],
    date: Annotated[str, Field(description="Invoice date in YYYY-MM-DD format")] = None
) -> list[TextContent]:
    """generate a professional invoice pdf from provided details."""
    start_time = datetime.now()
    generation_id = f"inv_{int(start_time.timestamp())}"
    
    # use current date if not provided
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    # progress logging
    def log_progress(message: str):
        """Log progress updates with timestamps."""
        logger.info(f"[{generation_id}] Progress: {message}")
    
    try:
        logger.info(f"[{generation_id}] Starting invoice generation for: {buyer_name} - ${amount}")
        
        # validate inputs
        if amount <= 0:
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message="Amount must be greater than 0"
            ))
        
        if not buyer_name.strip():
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message="Buyer name cannot be empty"
            ))
        
        if not company_name.strip():
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message="Company name cannot be empty"
            ))
        
        # validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message="Date must be in YYYY-MM-DD format"
            ))
        
        log_progress("Generating professional invoice PDF...")
        
        # generate invoice pdf
        pdf_data = await invoice_generator.generate_invoice_pdf(
            amount=amount,
            buyer_name=buyer_name,
            company_name=company_name,
            date=date,
            generation_id=generation_id
        )
        
        log_progress("Creating downloadable PDF package...")
        
        # save pdf and get download url
        download_url = await create_invoice_pdf(
            pdf_data=pdf_data,
            buyer_name=buyer_name,
            company_name=company_name,
            amount=amount,
            date=date,
            generation_id=generation_id
        )
        
        # track generation metrics
        generation_time = (datetime.now() - start_time).total_seconds()
        log_progress(f"Invoice PDF generated successfully in {generation_time:.1f}s")
        
        # format response
        success_message = f"""**Invoice PDF Generated Successfully!**

**Invoice Details:**
- Company: {company_name}
- Buyer: {buyer_name}
- Amount: ${amount:,.2f}
- Date: {date}
- Generation ID: {generation_id}

**Download Your Invoice**: {download_url}
**Link Expires**: 24 hours
**Generation Time**: {generation_time:.1f} seconds

**Invoice Features:**
- Professional PDF format
- Company branding
- Itemized billing structure
- Tax calculations (if applicable)
- Terms and conditions

Your professional invoice is ready for download!"""
        
        return [TextContent(type="text", text=success_message)]
        
    except Exception as e:
        logger.error(f"[{generation_id}] Generation failed: {str(e)}")
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message=f"Invoice generation failed: {str(e)}"
        ))


@mcp.tool(description="Get examples of invoice formats")
async def get_invoice_examples() -> list[TextContent]:
    """return examples of invoice generation."""
    examples = """**Invoice Generation Examples**

**Basic Invoice:**
- Amount: 1500.00
- Buyer Name: "John Smith"
- Company Name: "Acme Solutions Inc"
- Date: "2024-01-15"

**Service Invoice:**
- Amount: 2750.50
- Buyer Name: "Sarah Johnson"
- Company Name: "TechCorp Ltd"
- Date: "2024-02-01"

**Product Invoice:**
- Amount: 850.25
- Buyer Name: "Mike Davis"
- Company Name: "Digital Services LLC"
- Date: "2024-01-30"

**Professional Features:**
- Automatic invoice numbering
- Professional PDF formatting
- Company branding elements
- Tax calculations (where applicable)
- Terms and conditions
- Payment instructions
- Due date calculations

**Supported Formats:**
- Date: YYYY-MM-DD (e.g., 2024-01-15)
- Amount: Decimal format (e.g., 1250.00)
- Names: Full names or company names

**Usage Tips:**
- Use current date if no date specified
- Amount must be greater than 0
- All fields are required except date
- Generated PDFs are professionally formatted
- Download links expire in 24 hours

**Ready to generate your professional invoice!**
"""
    
    return [TextContent(type="text", text=examples)]


@mcp.tool(description="Check the status of the Invoice PDF generator system")
async def system_status() -> list[TextContent]:
    """report system status and configuration."""
    status_info = f"""**Invoice PDF Generator System Status**

**Configuration Status:**
- Phone Number: {'Configured' if MY_NUMBER else 'Missing MY_NUMBER'}
- Authentication Token: {'Configured' if AUTH_TOKEN else 'Missing AUTH_TOKEN'}

**System Information:**
- Download Base URL: {DOWNLOAD_BASE_URL}
- Downloads Directory: {'Available' if Path('static/downloads').exists() else 'Not Found'}
- Active Downloads: {len(list(Path('static/downloads').glob('*.pdf')) if Path('static/downloads').exists() else [])} files

**Service Status:**
- Invoice Generator: Running
- PDF Generator: Ready
- Download Manager: Ready

**Usage:**
- Use `generate_invoice` to create professional invoice PDFs
- Use `get_invoice_examples` for formatting examples
- Generated invoices are automatically saved and ready for download

**Invoice Features:**
- Professional PDF formatting
- Company branding
- Automatic invoice numbering
- Tax calculations (where applicable)
- Terms and conditions
- Secure 24-hour download links

**Puch AI Features:**
- Automatic bearer token authentication
- Secure PDF generation and storage
- Professional invoice templates
- Fast PDF processing
"""
    
    return [TextContent(type="text", text=status_info)]


def _format_file_list(files: dict) -> str:
    """format generated file list."""
    file_list = []
    for filename in sorted(files.keys()):
        size = len(files[filename])
        file_list.append(f"  - {filename} ({size:,} bytes)")
    return "\n".join(file_list)


def _format_syntax_results(results: dict) -> str:
    """format syntax validation results."""
    result_lines = []
    for filename, result in results.items():
        result_lines.append(f"  - {filename}: {result}")
    return "\n".join(result_lines)


async def main() -> None:
    """run the invoice pdf generator server."""
    print("\n" + "=" * 60)
    print("INVOICE PDF GENERATOR SERVER")
    print("=" * 60)
    
    # system status
    if MY_NUMBER:
        print(f"Phone: {MY_NUMBER}")
    else:
        print("Phone: NOT CONFIGURED")
    
    if BL_WORKSPACE:
        print(f"Blaxel Workspace: {BL_WORKSPACE}")
    else:
        print("Blaxel Workspace: NOT CONFIGURED")
    
    if BL_API_KEY:
        print("Blaxel API: CONFIGURED")
    else:
        print("Blaxel API: NOT CONFIGURED")
    
    if MORPH_API_KEY:
        print("MorphLLM API: CONFIGURED")
    else:
        print("MorphLLM API: NOT CONFIGURED")
    
    if OPENAI_API_KEY:
        print("OpenAI API: CONFIGURED")
    else:
        print("OpenAI API: NOT CONFIGURED")
    
    # create downloads directory
    downloads_dir = Path("static/downloads")
    downloads_dir.mkdir(parents=True, exist_ok=True)
    print(f"Downloads directory: {downloads_dir.absolute()}")
    
    # add custom routes
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
    print(f"Server: wss://run.blaxel.ai/{BL_WORKSPACE}/functions/invoice-pdf-generator")
    print(f"Downloads: {DOWNLOAD_BASE_URL}/download/")
    print("=" * 60)
    
    # start server
    await mcp.run_async("streamable-http", host="0.0.0.0", port=8086)


if __name__ == "__main__":
    asyncio.run(main())
