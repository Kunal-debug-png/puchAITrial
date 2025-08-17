"""
invoice pdf generator server

ai-powered invoice pdf generator for puch ai. generates professional invoice pdfs from provided details.
"""

import asyncio
import logging
import os
import json
import traceback
from datetime import datetime, timedelta
from typing import Annotated, Optional
from pathlib import Path

from dotenv import dotenv_values
from fastmcp import FastMCP
from mcp import ErrorData, McpError
from mcp.types import INTERNAL_ERROR, TextContent
from pydantic import Field

from core.invoice_generator import InvoiceGenerator
from core.payment_processor import PaymentProcessor
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
mcp = FastMCP("Invoice PDF Generator")
invoice_generator = InvoiceGenerator()
download_manager = DownloadManager()
payment_processor = PaymentProcessor(base_url=DOWNLOAD_BASE_URL)


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
    
    logger.info(f"[MCP_TOOL] generate_invoice called via MCP")
    logger.info(f"[MCP_TOOL] Parameters: buyer={buyer_name}, company={company_name}")
    logger.info(f"[MCP_TOOL] Items JSON: {items}")
    logger.info(f"[MCP_TOOL] Generation ID: {generation_id}")
    
    # use current date if not provided
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    logger.debug(f"[MCP_TOOL] Using date: {date}, tax_rate: {tax_rate}, currency: {currency_symbol}")
    
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
        
        logger.info(f"[MCP_TOOL] About to call create_invoice_pdf with {len(pdf_data)} bytes")
        logger.debug(f"[MCP_TOOL] PDF creation args: buyer={buyer_name}, company={company_name}, amount={total_amount}")
        
        # save pdf and get download url
        download_url = await create_invoice_pdf(
            pdf_data=pdf_data,
            buyer_name=buyer_name,
            company_name=company_name,
            amount=total_amount,
            date=date,
            generation_id=generation_id
        )
        
        logger.info(f"[MCP_TOOL] create_invoice_pdf returned: {download_url}")
        
        # track generation metrics
        generation_time = (datetime.now() - start_time).total_seconds()
        log_progress(f"Multi-item invoice PDF generated successfully in {generation_time:.1f}s")
        
        # format response
        tax_display = f"Tax Rate: {tax_rate*100:.0f}%" if tax_rate > 0 else "Tax Rate: 0% (No tax)"
        items_display = "\n".join([f"- {item['name']}: {item['quantity']} x {currency_symbol}{item['rate']:.2f}" for item in items_list])
        
        subtotal = total_amount
        tax_amount = subtotal * tax_rate
        final_total = subtotal + tax_amount
        
        logger.info(f"[MCP_TOOL] Preparing success response with download URL: {download_url}")
        
        success_message = f"""✅ **Invoice Generated Successfully!**

📋 **Details:**
• Company: {company_name}
• Buyer: {buyer_name} 
• Items: {len(items_list)} items
• Total: {currency_symbol}{final_total:,.2f}
• Date: {date}

📎 **Download Link:** {download_url}
⏰ **Expires:** 24 hours
⚡ **Generated in:** {generation_time:.1f}s

Your professional invoice PDF is ready for download!"""
        
        logger.info(f"[MCP_TOOL] Returning success response with {len(success_message)} characters")
        
        logger.info(f"[MCP_TOOL] Successfully generated invoice, returning TextContent")
        return [TextContent(type="text", text=success_message)]
        
    except Exception as e:
        logger.error(f"[MCP_TOOL] [{generation_id}] Generation failed: {str(e)}")
        logger.error(f"[MCP_TOOL] Full exception: {traceback.format_exc()}")
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


@mcp.tool(description="Generate invoice with payment integration (QR codes and payment links)")
async def generate_invoice_with_payment(
    buyer_name: Annotated[str, Field(description="Name of the buyer/client")],
    company_name: Annotated[str, Field(description="Company name issuing the invoice")],
    items: Annotated[str, Field(description="JSON string of items: [{\"name\": \"Item 1\", \"quantity\": 2, \"rate\": 100.00}]")],
    date: Annotated[str, Field(description="Invoice date in YYYY-MM-DD format")] = None,
    tax_rate: Annotated[float, Field(description="Tax rate as decimal (e.g., 0.18 for 18%)")] = 0.0,
    currency_symbol: Annotated[str, Field(description="Currency symbol")] = "₹"
) -> list[TextContent]:
    """Generate an invoice with payment integration."""
    start_time = datetime.now()
    generation_id = f"inv_{int(start_time.timestamp())}"
    
    # Use current date if not provided
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    try:
        logger.info(f"[{generation_id}] Starting payment-enabled invoice generation")
        
        # Parse and validate items
        try:
            items_list = json.loads(items)
        except json.JSONDecodeError as e:
            logger.error(f"[{generation_id}] JSON parsing failed: {e}")
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Invalid JSON format for items: {str(e)}"
            ))
        
        # Basic validation
        if not items_list:
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message="Items list cannot be empty"
            ))
        
        logger.info(f"[{generation_id}] Validating {len(items_list)} items")
        
        # Calculate total amount
        total_amount = sum(item['quantity'] * item['rate'] for item in items_list)
        tax_amount = total_amount * tax_rate
        final_total = total_amount + tax_amount
        
        logger.info(f"[{generation_id}] Calculated total: {currency_symbol}{final_total:.2f}")
        
        # Create payment link with improved error handling
        payment_info = {
            "payment_url": "",
            "available_methods": ["Manual Payment"],
            "error": None
        }
        
        try:
            logger.info(f"[{generation_id}] Attempting to create payment link for amount: {currency_symbol}{final_total:.2f}")
            
            # Validate payment processor configuration
            if not payment_processor:
                raise ValueError("Payment processor not initialized")
                
            if not hasattr(payment_processor, 'base_url') or not payment_processor.base_url:
                raise ValueError("Payment processor base URL not configured")
            
            # Create payment link
            payment_result = payment_processor.create_payment_link(
                invoice_id=generation_id,
                amount=final_total,
                currency=currency_symbol
            )
            
            # Update payment info with successful result
            payment_info = {
                "payment_url": payment_result.get("payment_url", ""),
                "available_methods": payment_result.get("available_methods", ["Card", "UPI", "PayPal"]),
                "transaction_id": payment_result.get("transaction_id", ""),
                "error": None
            }
            
            logger.info(f"[{generation_id}] Payment link created successfully: {payment_info['payment_url']}")
            
        except Exception as e:
            error_msg = f"Payment system error: {str(e)}"
            logger.warning(f"[{generation_id}] {error_msg}")
            logger.debug(f"[{generation_id}] Payment creation error details: {traceback.format_exc()}")
            
            # Set error info but continue with invoice generation
            payment_info["error"] = error_msg
            # Keep default values for payment_url (empty) and manual payment methods
        
        # Generate invoice with payment integration
        pdf_data = await invoice_generator.generate_invoice_with_payment(
            items=items_list,
            buyer_name=buyer_name,
            company_name=company_name,
            date=date,
            generation_id=generation_id,
            payment_url=payment_info["payment_url"],
            tax_rate=tax_rate,
            currency_symbol=currency_symbol
        )
        
        # Save PDF and get download URL
        download_url = await create_invoice_pdf(
            pdf_data=pdf_data,
            buyer_name=buyer_name,
            company_name=company_name,
            amount=final_total,
            date=date,
            generation_id=generation_id
        )
        
        
        # Generation time
        generation_time = (datetime.now() - start_time).total_seconds()
        
        # Format response
        items_display = "\n".join([f"- {item['name']}: {item['quantity']} x {currency_symbol}{item['rate']:.2f}" for item in items_list])
        
        # Check if payment link was successfully created
        has_payment_link = payment_info["payment_url"] and payment_info["payment_url"].strip()
        
        if has_payment_link:
            payment_section = f"""**Payment Integration:**
🔗 **Payment Link:** {payment_info["payment_url"]}
📱 **QR Code:** Embedded in PDF for mobile payments
💳 **Payment Methods:** {', '.join(payment_info["available_methods"])}
⏰ **Payment Status:** Pending"""
            
            features_section = """**Features:**
- ✅ Payment-enabled PDF with QR codes
- ✅ Clickable payment buttons
- ✅ Multiple payment methods
- ✅ Payment status tracking
- ✅ Professional invoice design

Customers can now pay instantly by scanning the QR code or clicking the payment link!"""
        else:
            payment_section = f"""**Payment Integration:**
⚠️ **Payment Link:** Not available (payment system temporarily unavailable)
📄 **Invoice PDF:** Contains payment instructions for manual processing
💳 **Payment Methods:** {', '.join(payment_info["available_methods"])}
⏰ **Payment Status:** Pending (Manual processing required)"""
            
            features_section = """**Features:**
- ✅ Professional invoice PDF generated
- ✅ Payment instructions included in PDF
- ✅ Manual payment processing available
- ✅ Invoice tracking and management
- ⚠️ Automatic payment processing temporarily unavailable

Customers can process payment manually using the instructions in the PDF."""
        
        success_message = f"""✅ **Payment-Enabled Invoice Generated Successfully!**

📋 **Invoice Details:**
• Company: {company_name}
• Buyer: {buyer_name}
• Items: {len(items_list)} items
• Total: {currency_symbol}{final_total:,.2f}
• Date: {date}

📎 **Download Link:** {download_url}
⏰ **Expires:** 24 hours
⚡ **Generated in:** {generation_time:.1f}s

{payment_section}

{features_section}

Your payment-enabled invoice PDF is ready for download!"""
        
        return [TextContent(type="text", text=success_message)]
        
    except Exception as e:
        logger.error(f"[{generation_id}] Payment-enabled invoice generation failed: {str(e)}")
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message=f"Payment-enabled invoice generation failed: {str(e)}"
        ))


@mcp.tool(description="Process a dummy payment for testing")
async def process_dummy_payment(
    transaction_id: Annotated[str, Field(description="Transaction ID from payment link")],
    payment_method: Annotated[str, Field(description="Payment method: card, upi, paypal, etc.")] = "card",
    simulate_success: Annotated[bool, Field(description="Simulate successful payment (true) or failure (false)")] = True
) -> list[TextContent]:
    """Process a dummy payment for demonstration purposes."""
    try:
        result = payment_processor.process_dummy_payment(
            transaction_id=transaction_id,
            payment_method=payment_method,
            simulate_success=simulate_success
        )
        
        if result["success"]:
            message = f"""**✅ Payment Processed Successfully!**

**Payment Details:**
- Transaction ID: {transaction_id}
- Status: {result["status"].upper()}
- Confirmation Code: {result.get("confirmation_code", "N/A")}
- Payment Method: {payment_method.title()}
- Message: {result["message"]}

**Next Steps:**
- Invoice marked as PAID
- Transaction recorded in system

🎉 **Payment completed successfully!**"""
        else:
            message = f"""**❌ Payment Failed**

**Payment Details:**
- Transaction ID: {transaction_id}
- Status: {result["status"].upper()}
- Error: {result["error"]}
- Payment Method: {payment_method.title()}

**Suggested Actions:**
- Try a different payment method
- Check payment details
- Contact support if issue persists

😔 **Please try again.**"""
        
        return [TextContent(type="text", text=message)]
        
    except Exception as e:
        logger.error(f"Failed to process dummy payment: {e}")
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message=f"Payment processing failed: {str(e)}"
        ))


@mcp.tool(description="Get payment status and transaction details")
async def get_payment_status(
    transaction_id: Annotated[str, Field(description="Transaction ID to check")]
) -> list[TextContent]:
    """Get the current status of a payment transaction."""
    try:
        transaction = payment_processor.get_transaction_status(transaction_id)
        
        if not transaction:
            return [TextContent(type="text", text=f"Transaction {transaction_id} not found.")]
        
        status_message = f"""**Payment Transaction Status**

**Transaction Details:**
- Transaction ID: {transaction['transaction_id']}
- Invoice ID: {transaction['invoice_id']}
- Amount: {transaction['currency']}{transaction['amount']:,.2f}
- Status: {transaction['status'].upper()}
- Payment Method: {transaction.get('payment_method', 'Not specified').title()}
- Created: {transaction['created_at']}
- Last Updated: {transaction['updated_at']}

**Additional Info:**
{f"- Confirmation Code: {transaction['confirmation_code']}" if transaction.get('confirmation_code') else ""}

**Status Legend:**
- 🟡 PENDING: Awaiting payment
- 🟠 PROCESSING: Payment being processed
- ✅ COMPLETED: Payment successful
- ❌ FAILED: Payment failed
- 🔄 REFUNDED: Payment refunded"""
        
        return [TextContent(type="text", text=status_message)]
        
    except Exception as e:
        logger.error(f"Failed to get payment status: {e}")
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message=f"Failed to get payment status: {str(e)}"
        ))




@mcp.tool(description="Get payment analytics")
async def get_system_analytics(
    days: Annotated[int, Field(description="Number of days to analyze (default: 30)")] = 30
) -> list[TextContent]:
    """Get comprehensive analytics for payment processing."""
    try:
        payment_analytics = payment_processor.get_payment_analytics(days=days)
        
        analytics_message = f"""**System Analytics Report** 📊

**Payment Analytics ({days} days):**
- Total Transactions: {payment_analytics['total_transactions']}
- Completed Payments: {payment_analytics['completed_payments']}
- Failed Payments: {payment_analytics['failed_payments']}
- Success Rate: {payment_analytics['success_rate']}%
- Total Amount: ₹{payment_analytics['total_amount']:,.2f}
- Net Amount: ₹{payment_analytics['net_amount']:,.2f}

**Payment Methods:**
{chr(10).join([f"- {method.title()}: {count} transactions" for method, count in payment_analytics['payment_methods'].items()]) if payment_analytics['payment_methods'] else "- No payment method data"}

**Performance Insights:**
- Payment processing is {'performing well' if payment_analytics['success_rate'] > 90 else 'needs attention'}
- Peak activity: {max(payment_analytics['daily_amounts'].items(), key=lambda x: x[1])[0] if payment_analytics['daily_amounts'] else 'No data'}

📊 **Payment system operating efficiently!**"""
        
        return [TextContent(type="text", text=analytics_message)]
        
    except Exception as e:
        logger.error(f"Failed to get analytics: {e}")
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message=f"Failed to get analytics: {str(e)}"
        ))


@mcp.tool(description="Check the status of the Invoice PDF generator system")
async def system_status() -> list[TextContent]:
    """Report comprehensive system status and configuration."""
    try:
        # Get system stats
        payment_stats = payment_processor.get_payment_analytics(days=7)  # Last 7 days
        
        status_info = f"""**Invoice PDF Generator System Status** 🗺️

**Configuration Status:**
- Phone Number: {'Configured' if MY_NUMBER else 'Missing MY_NUMBER'}
- Authentication Token: {'Configured' if AUTH_TOKEN else 'Missing AUTH_TOKEN'}

**System Information:**
- Download Base URL: {DOWNLOAD_BASE_URL}
- Downloads Directory: {'Available' if Path('static/downloads').exists() else 'Not Found'}
- Data Directory: {'Available' if Path('data').exists() else 'Not Found'}
- Active Downloads: {len(list(Path('static/downloads').glob('*.pdf')) if Path('static/downloads').exists() else [])} files

**Service Status:**
- ✅ Invoice Generator: Running
- ✅ PDF Generator: Ready
- ✅ Download Manager: Ready
- ✅ Payment Processor: Ready

**Recent Activity (7 days):**
- Payment Transactions: {payment_stats['total_transactions']}
- Payment Success Rate: {payment_stats['success_rate']}%

**Available Tools:**
- 📎 `generate_invoice` - Basic invoice generation
- 💳 `generate_invoice_with_payment` - Payment-enabled invoices
- ⏯️ `process_dummy_payment` - Test payment processing
- 📊 `get_payment_status` - Check payment status
- 📊 `get_system_analytics` - Payment analytics
- 📜 `get_invoice_examples` - Usage examples

**Features:**
- ✨ QR code payment integration
- ✨ Multiple payment methods
- ✨ Payment status tracking
- ✨ Professional invoice design
- ✨ System analytics

**System Health:** {'Excellent' if payment_stats['success_rate'] > 90 else 'Good' if payment_stats['success_rate'] > 80 else 'Needs Attention'} ✅

🚀 **Invoice system with payment integration ready!**"""
        
        return [TextContent(type="text", text=status_info)]
        
    except Exception as e:
        # Fallback to basic status if analytics fail
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
- Payment Processor: Ready

**Usage:**
- Use available tools to create and manage invoices
- Enhanced with payment features

**System Health:** Good ✅"""
        
        return [TextContent(type="text", text=status_info)]




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
        
    if AUTH_TOKEN:
        print("Auth Token: CONFIGURED")
    else:
        print("Auth Token: NOT CONFIGURED")
    
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
        logger.info(f"[ROUTE] Download request received: {download_id}")
        logger.debug(f"[ROUTE] Full URL path: {request.url.path}")
        logger.debug(f"[ROUTE] Request headers: {dict(request.headers)}")
        try:
            result = await download_manager.serve_download(download_id)
            logger.info(f"[ROUTE] Download served successfully: {download_id}")
            return result
        except Exception as e:
            logger.error(f"[ROUTE] Download failed for {download_id}: {str(e)}")
            logger.error(f"[ROUTE] Exception details: {traceback.format_exc()}")
            raise
    
    @mcp.custom_route(methods=["GET"], path="/health")
    async def health_check():
        logger.debug(f"[ROUTE] Health check requested")
        return {
            "status": "healthy",
            "service": "Invoice PDF Generator",
            "timestamp": datetime.now().isoformat()
        }
    
    @mcp.custom_route(methods=["GET"], path="/download-stats")
    async def download_stats():
        logger.debug(f"[ROUTE] Download stats requested")
        try:
            from utils.zip_creator import get_download_stats
            from utils.pdf_creator import get_pdf_download_stats
            
            zip_stats = get_download_stats()
            pdf_stats = get_pdf_download_stats()
            
            stats = {
                "zip_files": zip_stats,
                "pdf_files": pdf_stats,
                "total_files": zip_stats["total_downloads"] + pdf_stats["total_pdfs"],
                "total_size": zip_stats["total_size"] + pdf_stats["total_size"],
                "total_active": zip_stats["active_downloads"] + pdf_stats["active_pdfs"]
            }
            logger.info(f"[ROUTE] Download stats: {stats['total_files']} files, {stats['total_active']} active")
            return stats
        except Exception as e:
            logger.error(f"[ROUTE] Failed to get download stats: {e}")
            raise
    
    print("=" * 60)
    print(f"Server: {DOWNLOAD_BASE_URL}")
    print(f"Downloads: {DOWNLOAD_BASE_URL}/download/")
    print("=" * 60)
    
    # start server
    await mcp.run_async("streamable-http", host="0.0.0.0", port=8086)


if __name__ == "__main__":
    asyncio.run(main())
