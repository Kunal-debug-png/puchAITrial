"""
invoice generator for invoice pdf generator

generates professional invoice pdfs using reportlab.
"""

import io
import logging
from datetime import datetime, timedelta
from typing import Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)


class InvoiceGenerator:
    """generates professional invoice pdfs."""
    
    def __init__(self):
        """init invoice generator."""
        self.styles = getSampleStyleSheet()
        self.invoice_counter = 1000  # Starting invoice number
        
        # Custom styles
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1,  # Center alignment
        )
        
        self.company_style = ParagraphStyle(
            'CompanyStyle',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.darkblue,
        )
        
        self.header_style = ParagraphStyle(
            'HeaderStyle',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=6,
            textColor=colors.black,
        )
    
    async def generate_invoice_pdf(
        self,
        amount: float,
        buyer_name: str,
        company_name: str,
        date: str,
        generation_id: str,
        item_name: str = None,
        tax_rate: float = 0.0,
        quantity: int = 1,
        currency_symbol: str = "₹"
    ) -> bytes:
        """generate a professional invoice pdf."""
        # Set default item name if not provided
        if item_name is None or item_name.strip() == "":
            item_name = "Not Applicable"
        
        # Ensure currency symbol is not empty
        if not currency_symbol:
            currency_symbol = "₹"  # Default to Rupee
        
        logger.info(f"[{generation_id}] Generating PDF for {buyer_name} - {currency_symbol}{amount}")
        
        try:
            # Create PDF in memory
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            # Build invoice content
            story = []
            
            # Company header
            story.append(Paragraph(company_name, self.company_style))
            story.append(Spacer(1, 12))
            
            # Invoice title and number
            invoice_number = self._generate_invoice_number(generation_id)
            story.append(Paragraph("INVOICE", self.title_style))
            story.append(Paragraph(f"Invoice #: {invoice_number}", self.header_style))
            story.append(Spacer(1, 20))
            
            # Invoice details table
            invoice_data = [
                ["Invoice Date:", date],
                ["Due Date:", self._calculate_due_date(date)],
                ["Bill To:", buyer_name],
                ["From:", company_name],
            ]
            
            details_table = Table(invoice_data, colWidths=[2*inch, 4*inch])
            details_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            story.append(details_table)
            story.append(Spacer(1, 30))
            
            # Line items table
            # Calculate subtotal based on quantity and rate
            unit_rate = amount / quantity if quantity > 0 else amount
            subtotal = unit_rate * quantity
            
            line_items_data = [
                ["Description", "Quantity", "Rate", "Amount"],
                [item_name, str(quantity), f"{currency_symbol}{unit_rate:.2f}", f"{currency_symbol}{subtotal:.2f}"],
            ]
            
            # Calculate tax using the provided tax_rate
            tax_amount = subtotal * tax_rate
            total_amount = subtotal + tax_amount
            
            # Add totals section
            line_items_data.append(["", "", "Subtotal:", f"{currency_symbol}{subtotal:.2f}"])
            
            if tax_rate > 0:
                tax_percentage = tax_rate * 100
                line_items_data.append(["", "", f"Tax ({tax_percentage:.0f}%):", f"{currency_symbol}{tax_amount:.2f}"])
            
            line_items_data.append(["", "", "Total:", f"{currency_symbol}{total_amount:.2f}"])
            
            items_table = Table(line_items_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
            items_table.setStyle(TableStyle([
                # Header row
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                
                # Data rows
                ('ALIGN', (0, 1), (0, 1), 'LEFT'),  # Description left-aligned
                ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),  # Numbers right-aligned
                
                # Grid
                ('GRID', (0, 0), (-1, 1), 1, colors.black),
                
                # Totals section
                ('FONTNAME', (2, -3), (-1, -1), 'Helvetica-Bold'),
                ('BACKGROUND', (2, -1), (-1, -1), colors.lightgrey),
            ]))
            
            story.append(items_table)
            story.append(Spacer(1, 40))
            
            # Payment terms
            terms_text = """
            <b>Payment Terms:</b><br/>
            Payment is due within 30 days of invoice date.<br/>
            Late payments may incur additional fees.<br/><br/>
            
            <b>Thank you for your business!</b><br/>
            For questions about this invoice, please contact us.
            """
            
            story.append(Paragraph(terms_text, self.styles['Normal']))
            
            # Footer
            story.append(Spacer(1, 30))
            footer_text = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Invoice ID: {generation_id}"
            footer_style = ParagraphStyle(
                'FooterStyle',
                parent=self.styles['Normal'],
                fontSize=8,
                textColor=colors.grey,
                alignment=1  # Center
            )
            story.append(Paragraph(footer_text, footer_style))
            
            # Build PDF
            doc.build(story)
            
            # Get PDF data
            pdf_data = buffer.getvalue()
            buffer.close()
            
            logger.info(f"[{generation_id}] PDF generated successfully: {len(pdf_data)} bytes")
            return pdf_data
            
        except Exception as e:
            logger.error(f"[{generation_id}] Failed to generate PDF: {e}")
            raise
    
    def _generate_invoice_number(self, generation_id: str) -> str:
        """generate a unique invoice number."""
        # Use timestamp from generation_id for consistency
        timestamp = generation_id.split('_')[1] if '_' in generation_id else generation_id
        return f"INV-{timestamp}"
    
    def _calculate_due_date(self, invoice_date: str, days: int = 30) -> str:
        """calculate due date from invoice date."""
        try:
            date_obj = datetime.strptime(invoice_date, "%Y-%m-%d")
            due_date = date_obj + timedelta(days=days)
            return due_date.strftime("%Y-%m-%d")
        except ValueError:
            # Fallback to 30 days from today
            due_date = datetime.now() + timedelta(days=days)
            return due_date.strftime("%Y-%m-%d")
