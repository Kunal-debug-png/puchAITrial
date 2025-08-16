"""
invoice pdf generator server

ai-powered invoice pdf generator for puch ai. generates professional invoice pdfs from provided details.
"""

import asyncio
import logging
import os
import json
from datetime import datetime
from typing import Annotated, Optional
from pathlib import Path

from dotenv import dotenv_values
from fastmcp import FastMCP
from mcp import ErrorData, McpError
from mcp.types import INTERNAL_ERROR, TextContent
from pydantic import Field

from core.invoice_generator import InvoiceGenerator
from core.csv_dashboard_generator import CSVDashboardGenerator
from utils.pdf_creator import create_invoice_pdf
from utils.download_manager import DownloadManager
from utils.dashboard_creator import create_dashboard_html, serve_dashboard, get_dashboard_stats
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
DOWNLOAD_BASE_URL = get_env_var("DOWNLOAD_BASE_URL", "http://localhost:8086")

# Validate required environment variables
required_vars = {
    "MY_NUMBER": MY_NUMBER,
    "AUTH_TOKEN": AUTH_TOKEN,  # Required for MCP authentication
}

missing_required = [name for name, value in required_vars.items() if not value]

if missing_required:
    logger.error(f"Missing required environment variables: {missing_required}")
    raise ValueError(f"Required environment variables not set: {missing_required}")

# init components
mcp = FastMCP("Puch AI Multi-Tool Generator")
invoice_generator = InvoiceGenerator()
csv_dashboard_generator = CSVDashboardGenerator()
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
    buyer_name: Annotated[str, Field(description="Name of the buyer/client")],
    company_name: Annotated[str, Field(description="Company name issuing the invoice")],
    items: Annotated[str, Field(description="JSON string of items: [{\"name\": \"Item 1\", \"quantity\": 2, \"rate\": 100.00}, {\"name\": \"Item 2\", \"quantity\": 1, \"rate\": 250.50}]")],
    date: Annotated[str, Field(description="Invoice date in YYYY-MM-DD format")] = None,
    tax_rate: Annotated[float, Field(description="Tax rate as decimal (e.g., 0.18 for 18%)")] = 0.0,
    currency_symbol: Annotated[str, Field(description="Currency symbol")] = "₹"
) -> list[TextContent]:
    """generate a professional invoice pdf with multiple items."""
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
        logger.info(f"[{generation_id}] Starting multi-item invoice generation for: {buyer_name}")
        
        # Parse items JSON
        try:
            items_list = json.loads(items)
        except json.JSONDecodeError:
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message="Invalid JSON format for items. Expected format: [{\"name\": \"Item 1\", \"quantity\": 2, \"rate\": 100.00}]"
            ))
        
        # validate inputs
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
        
        if not items_list or len(items_list) == 0:
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message="At least one item is required"
            ))
        
        # validate each item
        total_amount = 0
        for i, item in enumerate(items_list):
            if not isinstance(item, dict):
                raise McpError(ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Item {i+1} must be an object with name, quantity, and rate"
                ))
            
            required_fields = ['name', 'quantity', 'rate']
            for field in required_fields:
                if field not in item:
                    raise McpError(ErrorData(
                        code=INTERNAL_ERROR,
                        message=f"Item {i+1} missing required field: {field}"
                    ))
            
            if item['quantity'] <= 0 or item['rate'] <= 0:
                raise McpError(ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Item {i+1} quantity and rate must be greater than 0"
                ))
            
            total_amount += item['quantity'] * item['rate']
        
        # validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message="Date must be in YYYY-MM-DD format"
            ))
        
        log_progress("Generating professional multi-item invoice PDF...")
        
        # generate invoice pdf with multiple items
        pdf_data = await invoice_generator.generate_multi_item_invoice_pdf(
            items=items_list,
            buyer_name=buyer_name,
            company_name=company_name,
            date=date,
            generation_id=generation_id,
            tax_rate=tax_rate,
            currency_symbol=currency_symbol
        )
        
        log_progress("Creating downloadable PDF package...")
        
        # save pdf and get download url
        download_url = await create_invoice_pdf(
            pdf_data=pdf_data,
            buyer_name=buyer_name,
            company_name=company_name,
            amount=total_amount,
            date=date,
            generation_id=generation_id
        )
        
        # track generation metrics
        generation_time = (datetime.now() - start_time).total_seconds()
        log_progress(f"Multi-item invoice PDF generated successfully in {generation_time:.1f}s")
        
        # format response
        tax_display = f"Tax Rate: {tax_rate*100:.0f}%" if tax_rate > 0 else "Tax Rate: 0% (No tax)"
        items_display = "\n".join([f"- {item['name']}: {item['quantity']} x {currency_symbol}{item['rate']:.2f}" for item in items_list])
        
        subtotal = total_amount
        tax_amount = subtotal * tax_rate
        final_total = subtotal + tax_amount
        
        success_message = f"""**Invoice PDF Generated Successfully!**

**Invoice Details:**
- Company: {company_name}
- Buyer: {buyer_name}
- Items ({len(items_list)} items):
{items_display}
- Subtotal: {currency_symbol}{subtotal:,.2f}
- {tax_display}
- Tax Amount: {currency_symbol}{tax_amount:,.2f}
- Total Amount: {currency_symbol}{final_total:,.2f}
- Currency: {currency_symbol}
- Date: {date}
- Generation ID: {generation_id}

**Download Your Invoice**: {download_url}
**Link Expires**: 24 hours
**Generation Time**: {generation_time:.1f} seconds

**Invoice Features:**
- Professional PDF format
- Multiple line items support
- Company branding
- Automatic calculations
- Flexible tax calculations
- Customizable currency symbols
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

**Multi-Item Invoice:**
Use `generate_invoice` for multiple items in a single invoice:
- Buyer Name: "Sarah Johnson"
- Company Name: "TechCorp Ltd"
- Items: '[{"name": "Web Development", "quantity": 1, "rate": 1500.00}, {"name": "SEO Services", "quantity": 2, "rate": 500.00}]'
- Tax Rate: 0.18 (18%)
- Currency Symbol: "$"

**Single Item Invoice Example:**
- Buyer Name: "Mike Davis"
- Company Name: "Digital Services LLC"
- Items: '[{"name": "Software License", "quantity": 5, "rate": 170.05}]'
- Tax Rate: 0.12 (12%)
- Currency Symbol: "$"

**Multiple Items Example:**
- Buyer Name: "John Smith"
- Company Name: "Acme Solutions Inc"
- Items: '[{"name": "Consulting Services", "quantity": 1, "rate": 1200.00}, {"name": "Software License", "quantity": 2, "rate": 150.00}, {"name": "Cloud Storage", "quantity": 1, "rate": 99.99}]'
- Date: "2024-01-15"
- Tax Rate: 0.1 (10%)
- Currency Symbol: "€"

**Professional Features:**
- Automatic invoice numbering
- Professional PDF formatting
- Company branding elements
- Configurable tax calculations (0% to any %)
- Multiple item support
- Flexible currency symbols
- Terms and conditions
- Payment instructions

**Parameters:**
- items: JSON array of items, each with name, quantity and rate
- tax_rate: Tax as decimal (e.g., 0.18 for 18%, default: 0.0)
- currency_symbol: Currency symbol (default: "₹")

**Supported Formats:**
- Date: YYYY-MM-DD (e.g., 2024-01-15)
- Tax Rate: Decimal (e.g., 0.15 for 15%)
- Names: Full names or company names
- Currency: Any symbol (₹, $, €, £, etc.)

**Usage Tips:**
- Use current date if no date specified
- Tax rate of 0.0 means no tax applied
- Generated PDFs are professionally formatted
- Download links expire in 24 hours
- Each item must have name, quantity, and rate properties

**Ready to generate your customized professional invoice!**
"""
    
    return [TextContent(type="text", text=examples)]


# CSV Dashboard Generator Tools

@mcp.tool(description="Generate a beautiful interactive dashboard from CSV data")
async def generate_csv_dashboard(
    csv_content: Annotated[str, Field(description="CSV file content as text string")],
    dashboard_title: Annotated[str, Field(description="Title for the dashboard")] = "CSV Data Dashboard",
    csv_filename: Annotated[str, Field(description="Original CSV filename for reference")] = "data.csv",
    theme: Annotated[str, Field(description="Dashboard theme (modern, classic, dark)")] = "modern"
) -> list[TextContent]:
    """Generate a stunning interactive dashboard from CSV data with AI-powered insights."""
    start_time = datetime.now()
    generation_id = f"dash_{int(start_time.timestamp())}"
    
    def log_progress(message: str):
        """Log progress updates with timestamps."""
        logger.info(f"[{generation_id}] Progress: {message}")
    
    try:
        logger.info(f"[{generation_id}] Starting CSV dashboard generation: {dashboard_title}")
        
        # Validate inputs
        if not csv_content.strip():
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message="CSV content cannot be empty"
            ))
        
        if not dashboard_title.strip():
            dashboard_title = "CSV Data Dashboard"
        
        log_progress("Analyzing CSV structure and data types...")
        
        # Analyze CSV structure
        analysis = await csv_dashboard_generator.analyze_csv_structure(csv_content)
        
        log_progress(f"Analysis complete: {analysis['total_rows']} rows, {analysis['total_columns']} columns")
        log_progress(f"Data quality score: {analysis['data_quality_score']:.1f}%")
        
        log_progress("Generating interactive dashboard HTML...")
        
        # Generate dashboard HTML
        dashboard_html = await csv_dashboard_generator.generate_dashboard_html(
            csv_content=csv_content,
            analysis=analysis,
            dashboard_title=dashboard_title,
            theme=theme
        )
        
        log_progress("Saving dashboard and creating download link...")
        
        # Save dashboard and get download URL
        download_url = await create_dashboard_html(
            html_content=dashboard_html,
            dashboard_title=dashboard_title,
            csv_filename=csv_filename,
            analysis=analysis,
            generation_id=generation_id
        )
        
        # Track generation metrics
        generation_time = (datetime.now() - start_time).total_seconds()
        log_progress(f"Dashboard generated successfully in {generation_time:.1f}s")
        
        # Generate insights summary for response
        insights_summary = []
        numeric_cols = [col for col, dtype in analysis['data_types'].items() if dtype == 'numeric']
        categorical_cols = [col for col, dtype in analysis['data_types'].items() if dtype == 'categorical']
        
        if numeric_cols:
            insights_summary.append(f"📊 {len(numeric_cols)} numeric columns ready for statistical analysis")
        if categorical_cols:
            insights_summary.append(f"🏷️ {len(categorical_cols)} categorical columns for grouping and filtering")
        
        # Chart recommendations
        chart_recommendations = []
        for rec in analysis['recommended_charts'][:3]:  # Top 3 recommendations
            chart_recommendations.append(f"• {rec['title']}: {rec['description']}")
        
        success_message = f"""**🎯 CSV Dashboard Generated Successfully!**

**📋 Dataset Overview:**
- **Rows**: {analysis['total_rows']:,}
- **Columns**: {analysis['total_columns']}
- **Data Quality Score**: {analysis['data_quality_score']:.1f}%
- **Missing Data**: {sum(1 for col, missing in analysis['missing_values'].items() if missing['percentage'] > 0)} columns have missing values

**🔍 Key Insights:**
{chr(10).join(insights_summary) if insights_summary else '• Dataset ready for analysis'}

**📈 Recommended Visualizations:**
{chr(10).join(chart_recommendations) if chart_recommendations else '• Basic charts available based on data types'}

**🎨 Dashboard Features:**
- Interactive charts with Chart.js
- Responsive Bootstrap design
- Data filtering and search
- Statistical insights
- Modern {theme} theme
- AI-powered recommendations
- Data quality analysis
- Professional styling

**🌐 Your Interactive Dashboard**: {download_url}
**⏱️ Generation Time**: {generation_time:.1f} seconds
**🔗 Link Access**: Available 24/7 for easy sharing
**📱 Responsive**: Works perfectly on all devices

**🚀 Next Steps:**
- Open the dashboard to explore your data
- Share the link with your team
- Use insights to make data-driven decisions
- Export charts and findings

Your beautiful, interactive dashboard is ready to transform your data into insights! 🎉"""
        
        return [TextContent(type="text", text=success_message)]
        
    except Exception as e:
        logger.error(f"[{generation_id}] Dashboard generation failed: {str(e)}")
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message=f"CSV dashboard generation failed: {str(e)}"
        ))


@mcp.tool(description="Get examples and usage instructions for CSV dashboard generation")
async def get_csv_dashboard_examples() -> list[TextContent]:
    """Return examples and best practices for CSV dashboard generation."""
    examples = """**🎯 CSV Dashboard Generator Examples**

**📁 CSV Format Requirements:**
- First row should contain column headers
- Data should be clean and consistent
- Missing values are automatically handled
- Supports numeric, categorical, and date columns

**📊 Sample CSV Structure:**
```csv
Date,Product,Sales,Region,Customer_Type
2024-01-01,Widget A,1200.50,North,Premium
2024-01-02,Widget B,800.25,South,Standard
2024-01-03,Widget A,1500.00,East,Premium
```

**🎨 Usage Examples:**

**Basic Dashboard:**
- CSV Content: [Your CSV data as text]
- Dashboard Title: "Sales Performance Dashboard"
- Theme: "modern"

**Advanced Dashboard:**
- CSV Content: [Your CSV data as text]
- Dashboard Title: "Customer Analytics Dashboard"
- CSV Filename: "customer_data_2024.csv"
- Theme: "dark"

**💡 Best Practices:**

**Data Preparation:**
- Clean column names (no special characters)
- Consistent date formats (YYYY-MM-DD)
- Remove duplicate headers
- Handle missing values appropriately

**Column Types Detected:**
- **Numeric**: Sales figures, quantities, scores
- **Categorical**: Regions, product types, status
- **DateTime**: Dates, timestamps
- **Text**: Descriptions, comments, IDs

**🚀 Dashboard Features:**

**Interactive Charts:**
- Bar charts for category comparisons
- Line charts for time series data
- Pie charts for proportional data
- Scatter plots for correlations
- Histograms for distributions

**AI-Powered Insights:**
- Data quality assessment
- Missing data analysis
- Statistical summaries
- Chart recommendations
- Trend identification

**Professional Design:**
- Responsive Bootstrap layout
- Modern color schemes
- Interactive filters
- Export capabilities
- Mobile-friendly interface

**🎯 Optimal Data Sizes:**
- **Small**: 1-1,000 rows - Perfect for detailed analysis
- **Medium**: 1,000-100,000 rows - Great for insights
- **Large**: 100,000+ rows - Sampled for performance

**🔧 Troubleshooting:**
- Ensure CSV has proper headers
- Check for encoding issues (UTF-8 recommended)
- Verify data consistency
- Remove extra commas or quotes

**🌟 Pro Tips:**
- Use descriptive column names
- Include units in column names (e.g., 'Sales_USD')
- Separate date and time if needed
- Keep categorical values consistent
- Add a 'Notes' column for context

**Ready to transform your CSV data into stunning interactive dashboards! 📈✨**
"""
    
    return [TextContent(type="text", text=examples)]


@mcp.tool(description="Check the status of the Puch AI Multi-Tool Generator system")
async def system_status() -> list[TextContent]:
    """report system status and configuration."""
    
    # Get dashboard stats
    dashboard_stats = get_dashboard_stats()
    
    status_info = f"""**🚀 Puch AI Multi-Tool Generator System Status**

**🔧 Configuration Status:**
- Phone Number: {'✅ Configured' if MY_NUMBER else '❌ Missing MY_NUMBER'}
- Authentication Token: {'✅ Configured' if AUTH_TOKEN else '❌ Missing AUTH_TOKEN'}

**🌐 System Information:**
- Download Base URL: {DOWNLOAD_BASE_URL}
- Downloads Directory: {'✅ Available' if Path('static/downloads').exists() else '❌ Not Found'}
- Dashboards Directory: {'✅ Available' if Path('static/dashboards').exists() else '❌ Not Found'}
- Active PDF Downloads: {len(list(Path('static/downloads').glob('*.pdf')) if Path('static/downloads').exists() else [])} files
- Active Dashboards: {dashboard_stats['active_dashboards']} dashboards

**⚙️ Service Status:**
- Invoice Generator: ✅ Running
- CSV Dashboard Generator: ✅ Running
- PDF Generator: ✅ Ready
- Dashboard HTML Generator: ✅ Ready
- Download Manager: ✅ Ready

**📊 Available Tools:**

**📄 Invoice Generation:**
- `generate_invoice` - Create professional invoice PDFs
- `get_invoice_examples` - View formatting examples
- Features: Multi-item support, tax calculations, professional styling

**📈 CSV Dashboard Generation:**
- `generate_csv_dashboard` - Create interactive data dashboards
- `get_csv_dashboard_examples` - View usage examples
- Features: AI-powered insights, interactive charts, responsive design

**🎯 Key Features:**
- **Invoice PDFs**: Professional formatting, company branding, automatic numbering
- **CSV Dashboards**: Interactive charts, statistical analysis, mobile-responsive
- **Security**: Bearer token authentication, secure file storage
- **Performance**: Fast processing, optimized for large datasets
- **Accessibility**: 24/7 download links, cross-platform compatibility

**📈 Usage Statistics:**
- Total Dashboards Generated: {dashboard_stats['total_dashboards']}
- Dashboard Storage Used: {dashboard_stats['total_size'] / 1024 / 1024:.1f} MB
- System Uptime: Ready for requests

**🔗 Endpoints:**
- Downloads: {DOWNLOAD_BASE_URL}/download/[file_id]
- Dashboards: {DOWNLOAD_BASE_URL}/dashboard/[dashboard_id]
- Health Check: {DOWNLOAD_BASE_URL}/health
- Statistics: {DOWNLOAD_BASE_URL}/download-stats

**Ready to generate professional invoices and stunning data dashboards! 🎉**
"""
    
    return [TextContent(type="text", text=status_info)]




async def main() -> None:
    """run the puch ai multi-tool generator server."""
    print("\n" + "=" * 70)
    print("🚀 PUCH AI MULTI-TOOL GENERATOR SERVER 🚀")
    print("=" * 70)
    print("📄 Invoice PDF Generation + 📊 CSV Dashboard Generation")
    
    # system status
    if MY_NUMBER:
        print(f"Phone: {MY_NUMBER}")
    else:
        print("Phone: NOT CONFIGURED")
        
    if AUTH_TOKEN:
        print("Auth Token: CONFIGURED")
    else:
        print("Auth Token: NOT CONFIGURED")
    
    # create downloads directory
    downloads_dir = Path("static/downloads")
    downloads_dir.mkdir(parents=True, exist_ok=True)
    print(f"Downloads directory: {downloads_dir.absolute()}")
    
    # create dashboards directory
    dashboards_dir = Path("static/dashboards")
    dashboards_dir.mkdir(parents=True, exist_ok=True)
    print(f"Dashboards directory: {dashboards_dir.absolute()}")
    
    # add custom routes
    @mcp.custom_route(methods=["GET"], path="/download/{download_id}")
    async def download_mcp_endpoint(request):
        # extract download_id from url path
        path_parts = request.url.path.split('/')
        download_id = path_parts[-1]  # Get the last part of the path
        return await download_manager.serve_download(download_id)
    
    @mcp.custom_route(methods=["GET"], path="/dashboard/{dashboard_id}")
    async def dashboard_mcp_endpoint(request):
        # extract dashboard_id from url path
        path_parts = request.url.path.split('/')
        dashboard_id = path_parts[-1]  # Get the last part of the path
        return await serve_dashboard(dashboard_id)
    
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
    print(f"Server: {DOWNLOAD_BASE_URL}")
    print(f"Downloads: {DOWNLOAD_BASE_URL}/download/")
    print("=" * 60)
    
    # start server
    await mcp.run_async("streamable-http", host="0.0.0.0", port=8086)


if __name__ == "__main__":
    asyncio.run(main())
