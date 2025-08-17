"""
invoice generator for invoice pdf generator

generates professional invoice pdfs using reportlab.
"""

import io
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as ReportLabImage
from reportlab.pdfgen import canvas
from PIL import Image
import qrcode

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
    
    async def generate_multi_item_invoice_pdf(
        self,
        items: list,
        buyer_name: str,
        company_name: str,
        date: str,
        generation_id: str,
        tax_rate: float = 0.0,
        currency_symbol: str = "₹"
    ) -> bytes:
        """generate a professional multi-item invoice pdf."""
        # Ensure currency symbol is not empty
        if not currency_symbol:
            currency_symbol = "₹"  # Default to Rupee
        
        logger.info(f"[{generation_id}] Generating multi-item PDF for {buyer_name} - {len(items)} items")
        
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
            
            # Multi-item line items table
            line_items_data = [
                ["Description", "Quantity", "Rate", "Amount"],
            ]
            
            # Add each item as a separate row
            subtotal = 0
            for item in items:
                item_name = item['name']
                quantity = item['quantity']
                rate = item['rate']
                amount = quantity * rate
                subtotal += amount
                
                line_items_data.append([
                    item_name,
                    str(quantity),
                    f"{currency_symbol}{rate:.2f}",
                    f"{currency_symbol}{amount:.2f}"
                ])
            
            # Calculate tax
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
                
                # Data rows (item rows)
                ('ALIGN', (0, 1), (0, len(items)), 'LEFT'),  # Description left-aligned
                ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),  # Numbers right-aligned
                
                # Grid for item rows
                ('GRID', (0, 0), (-1, len(items)), 1, colors.black),
                
                # Totals section styling
                ('FONTNAME', (2, len(items)+1), (-1, -1), 'Helvetica-Bold'),
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
            
            logger.info(f"[{generation_id}] Multi-item PDF generated successfully: {len(pdf_data)} bytes")
            return pdf_data
            
        except Exception as e:
            logger.error(f"[{generation_id}] Failed to generate multi-item PDF: {e}")
            raise
    
    def _create_payment_qr_code(self, payment_url: str, size: int = 100) -> Optional[bytes]:
        """Create QR code for payment URL."""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=8,
                border=4,
            )
            qr.add_data(payment_url)
            qr.make(fit=True)
            
            # Create QR code image
            qr_image = qr.make_image(fill_color="black", back_color="white")
            
            # Resize if needed
            if size != 100:
                qr_image = qr_image.resize((size, size), Image.Resampling.LANCZOS)
            
            # Convert to bytes
            buffer = io.BytesIO()
            qr_image.save(buffer, format='PNG')
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to create payment QR code: {e}")
            return None
    
    async def generate_invoice_with_payment(
        self,
        items: list,
        buyer_name: str,
        company_name: str,
        date: str,
        generation_id: str,
        payment_url: str = "",
        tax_rate: float = 0.0,
        currency_symbol: str = "₹",
        buyer_email: str = ""
    ) -> bytes:
        """Generate invoice PDF with payment integration (QR code and payment button)."""
        # Ensure currency symbol is not empty
        if not currency_symbol:
            currency_symbol = "₹"  # Default to Rupee
        
        logger.info(f"[{generation_id}] Generating payment-enabled PDF for {buyer_name} - {len(items)} items")
        
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
            
            # Add email if provided
            if buyer_email:
                invoice_data.append(["Email:", buyer_email])
            
            details_table = Table(invoice_data, colWidths=[2*inch, 4*inch])
            details_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            story.append(details_table)
            story.append(Spacer(1, 30))
            
            # Multi-item line items table
            line_items_data = [
                ["Description", "Quantity", "Rate", "Amount"],
            ]
            
            # Add each item as a separate row
            subtotal = 0
            for item in items:
                item_name = item['name']
                quantity = item['quantity']
                rate = item['rate']
                amount = quantity * rate
                subtotal += amount
                
                line_items_data.append([
                    item_name,
                    str(quantity),
                    f"{currency_symbol}{rate:.2f}",
                    f"{currency_symbol}{amount:.2f}"
                ])
            
            # Calculate tax
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
                
                # Data rows (item rows)
                ('ALIGN', (0, 1), (0, len(items)), 'LEFT'),  # Description left-aligned
                ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),  # Numbers right-aligned
                
                # Grid for item rows
                ('GRID', (0, 0), (-1, len(items)), 1, colors.black),
                
                # Totals section styling
                ('FONTNAME', (2, len(items)+1), (-1, -1), 'Helvetica-Bold'),
                ('BACKGROUND', (2, -1), (-1, -1), colors.lightgrey),
            ]))
            
            story.append(items_table)
            story.append(Spacer(1, 30))
            
            # Payment section with QR code if payment URL is provided
            if payment_url:
                # Create payment section header
                payment_header_style = ParagraphStyle(
                    'PaymentHeader',
                    parent=self.styles['Heading2'],
                    fontSize=16,
                    spaceAfter=15,
                    textColor=colors.darkgreen,
                    alignment=1  # Center
                )
                
                story.append(Paragraph("💳 PAYMENT OPTIONS", payment_header_style))
                story.append(Spacer(1, 10))
                
                # Create payment instructions and QR code table
                payment_data = []
                
                # Generate QR code
                qr_bytes = self._create_payment_qr_code(payment_url, size=120)
                
                if qr_bytes:
                    # Create QR code image for ReportLab
                    qr_buffer = io.BytesIO(qr_bytes)
                    qr_image = ReportLabImage(qr_buffer, width=120, height=120)
                    
                    # Payment instructions
                    payment_instructions = f"""
                    <b>Quick Payment Options:</b><br/><br/>
                    
                    <b>🔗 Online Payment:</b><br/>
                    Click or visit: <u>{payment_url}</u><br/><br/>
                    
                    <b>📱 Mobile Payment:</b><br/>
                    Scan the QR code with your mobile device<br/><br/>
                    
                    <b>💡 Payment Methods Accepted:</b><br/>
                    • Credit/Debit Cards<br/>
                    • UPI Payments<br/>
                    • PayPal<br/>
                    • Bank Transfer
                    """
                    
                    # Create payment table with QR code and instructions
                    payment_data = [[
                        Paragraph(payment_instructions, self.styles['Normal']),
                        qr_image
                    ]]
                    
                    payment_table = Table(payment_data, colWidths=[4*inch, 2*inch])
                    payment_table.setStyle(TableStyle([
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                        ('BACKGROUND', (0, 0), (-1, -1), colors.aliceblue),
                        ('BOX', (0, 0), (-1, -1), 1, colors.darkblue),
                        ('LEFTPADDING', (0, 0), (-1, -1), 15),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 15),
                        ('TOPPADDING', (0, 0), (-1, -1), 15),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
                    ]))
                    
                    story.append(payment_table)
                else:
                    # Fallback if QR code generation fails
                    payment_instructions = f"""
                    <b>Payment Link:</b><br/>
                    {payment_url}<br/><br/>
                    
                    <b>Payment Methods Accepted:</b><br/>
                    Credit/Debit Cards, UPI, PayPal, Bank Transfer
                    """
                    
                    story.append(Paragraph(payment_instructions, self.styles['Normal']))
                
                story.append(Spacer(1, 20))
            
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
            if payment_url:
                footer_text += f" | Payment-Enabled Invoice"
            
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
            
            logger.info(f"[{generation_id}] Payment-enabled PDF generated successfully: {len(pdf_data)} bytes")
            return pdf_data
            
        except Exception as e:
            logger.error(f"[{generation_id}] Failed to generate payment-enabled PDF: {e}")
            raise
