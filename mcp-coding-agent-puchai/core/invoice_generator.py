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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as ReportLabImage, PageBreak, Frame, FrameBreak
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from PIL import Image
import qrcode

logger = logging.getLogger(__name__)


class InvoiceGenerator:
    """generates professional invoice pdfs."""
    
    def __init__(self):
        """init invoice generator."""
        self.styles = getSampleStyleSheet()
        self.invoice_counter = 1000  # Starting invoice number
        
        # Enhanced Custom Styles
        self.title_style = ParagraphStyle(
            'EnhancedTitle',
            parent=self.styles['Heading1'],
            fontSize=32,
            spaceAfter=25,
            spaceBefore=15,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1a365d'),  # Professional dark blue
            fontName='Helvetica-Bold',
            borderWidth=2,
            borderColor=colors.HexColor('#2b77ad'),
            borderPadding=15,
            backColor=colors.HexColor('#f7fafc'),
        )
        
        self.company_style = ParagraphStyle(
            'EnhancedCompany',
            parent=self.styles['Heading1'],
            fontSize=22,
            spaceAfter=8,
            spaceBefore=10,
            textColor=colors.HexColor('#2b77ad'),
            fontName='Helvetica-Bold',
            alignment=TA_LEFT,
        )
        
        self.header_style = ParagraphStyle(
            'EnhancedHeader',
            parent=self.styles['Normal'],
            fontSize=13,
            spaceAfter=8,
            spaceBefore=4,
            textColor=colors.HexColor('#4a5568'),
            fontName='Helvetica-Bold',
            alignment=TA_RIGHT,
        )
        
        self.section_header_style = ParagraphStyle(
            'SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=18,
            spaceAfter=15,
            spaceBefore=20,
            textColor=colors.HexColor('#2b77ad'),
            fontName='Helvetica-Bold',
            alignment=TA_LEFT,
            borderWidth=1,
            borderColor=colors.HexColor('#e2e8f0'),
            borderPadding=8,
            leftIndent=0,
        )
        
        self.info_style = ParagraphStyle(
            'InfoStyle',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=4,
            textColor=colors.HexColor('#4a5568'),
            fontName='Helvetica',
            alignment=TA_LEFT,
        )
        
        self.payment_header_style = ParagraphStyle(
            'PaymentHeaderStyle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=20,
            spaceBefore=30,
            textColor=colors.HexColor('#38a169'),  # Green for payment
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            borderWidth=2,
            borderColor=colors.HexColor('#38a169'),
            borderPadding=12,
            backColor=colors.HexColor('#f0fff4'),
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
        """Generate a professional multi-item invoice PDF with enhanced styling."""
        # Ensure currency symbol is not empty
        if not currency_symbol:
            currency_symbol = "₹"  # Default to Rupee
        
        logger.info(f"[{generation_id}] Generating enhanced multi-item PDF for {buyer_name} - {len(items)} items")
        
        try:
            # Create PDF in memory with enhanced settings
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=60,
                leftMargin=60,
                topMargin=60,
                bottomMargin=60,
                title=f"Invoice {self._generate_invoice_number(generation_id)}"
            )
            
            # Build invoice content
            story = []
            
            # Professional Header Section
            header_data = [[
                [Paragraph(f"<b>{company_name}</b>", self.company_style)],
                [Paragraph("BILL", self.title_style)]
            ]]
            
            header_table = Table(header_data, colWidths=[4*inch, 3*inch])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ]))
            story.append(header_table)
            story.append(Spacer(1, 20))
            
            # Invoice metadata in professional layout
            invoice_number = self._generate_invoice_number(generation_id)
            due_date = self._calculate_due_date(date)
            
            # Create two-column layout for invoice details
            left_column_data = [
                [Paragraph("<b>BILL TO:</b>", self.section_header_style)],
                [Paragraph(buyer_name, self.info_style)],
            ]
            
            right_column_data = [
                [Paragraph("<b>BILL DETAILS:</b>", self.section_header_style)],
                [Paragraph(f"<b>BILL #:</b> {invoice_number}", self.info_style)],
                [Paragraph(f"<b>Issue Date:</b> {date}", self.info_style)],
                [Paragraph(f"<b>Due Date:</b> {due_date}", self.info_style)],
                [Paragraph(f"<b>From:</b> {company_name}", self.info_style)],
            ]
            
            # Combine columns into a table
            details_layout = []
            max_rows = max(len(left_column_data), len(right_column_data))
            for i in range(max_rows):
                left_cell = left_column_data[i][0] if i < len(left_column_data) else ""
                right_cell = right_column_data[i][0] if i < len(right_column_data) else ""
                details_layout.append([left_cell, right_cell])
            
            details_table = Table(details_layout, colWidths=[3.5*inch, 3.5*inch])
            details_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 15),
                ('RIGHTPADDING', (0, 0), (-1, -1), 15),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
                ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#2b77ad')),
            ]))
            
            story.append(details_table)
            story.append(Spacer(1, 30))
            
            # Enhanced Items Table
            line_items_data = [[
                Paragraph("<b>Description</b>", self.info_style),
                Paragraph("<b>Qty</b>", self.info_style),
                Paragraph("<b>Rate</b>", self.info_style),
                Paragraph("<b>Amount</b>", self.info_style)
            ]]
            
            # Add each item as a separate row with enhanced formatting
            subtotal = 0
            for item in items:
                item_name = item['name']
                quantity = item['quantity']
                rate = item['rate']
                amount = quantity * rate
                subtotal += amount
                
                line_items_data.append([
                    Paragraph(item_name, self.info_style),
                    Paragraph(str(quantity), self.info_style),
                    Paragraph(f"{currency_symbol}{rate:.2f}", self.info_style),
                    Paragraph(f"{currency_symbol}{amount:.2f}", self.info_style)
                ])
            
            # Calculate tax and total
            tax_amount = subtotal * tax_rate
            total_amount = subtotal + tax_amount
            
            # Add totals section with enhanced styling
            line_items_data.extend([
                ["", "", "", ""],  # Empty row for spacing
                ["", "", Paragraph("<b>Subtotal:</b>", self.info_style), Paragraph(f"<b>{currency_symbol}{subtotal:.2f}</b>", self.info_style)],
            ])
            
            if tax_rate > 0:
                tax_percentage = tax_rate * 100
                line_items_data.append([
                    "", "", 
                    Paragraph(f"<b>Tax ({tax_percentage:.0f}%):</b>", self.info_style), 
                    Paragraph(f"<b>{currency_symbol}{tax_amount:.2f}</b>", self.info_style)
                ])
            
            line_items_data.append([
                "", "", 
                Paragraph("<b>TOTAL:</b>", self.info_style), 
                Paragraph(f"<b>{currency_symbol}{total_amount:.2f}</b>", self.info_style)
            ])
            
            items_table = Table(line_items_data, colWidths=[3.5*inch, 0.8*inch, 1.3*inch, 1.4*inch])
            items_table.setStyle(TableStyle([
                # Header row styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2b77ad')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),  # Right align numbers
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                
                # Grid and padding
                ('GRID', (0, 0), (-1, len(items)), 1, colors.HexColor('#e2e8f0')),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                
                # Alternate row colors for items
                ('BACKGROUND', (0, 1), (-1, len(items)), colors.HexColor('#f8f9fa')),
                
                # Totals section styling
                ('BACKGROUND', (2, len(items)+2), (-1, -2), colors.HexColor('#e2e8f0')),
                ('BACKGROUND', (2, -1), (-1, -1), colors.HexColor('#2b77ad')),
                ('TEXTCOLOR', (2, -1), (-1, -1), colors.white),
                ('FONTNAME', (2, len(items)+2), (-1, -1), 'Helvetica-Bold'),
                ('LINEABOVE', (2, len(items)+2), (-1, len(items)+2), 2, colors.HexColor('#2b77ad')),
            ]))
            
            story.append(items_table)
            story.append(Spacer(1, 40))
            
            # Enhanced Terms and Conditions
            terms_text = """
            
            
            <b>🙏 Thank you for your business!</b><br/>
            We appreciate your trust in our services. If you have any questions <br/>
            about this invoice or need assistance, please don't hesitate to contact us.
            """
            
            terms_style = ParagraphStyle(
                'TermsStyle',
                parent=self.styles['Normal'],
                fontSize=11,
                spaceAfter=6,
                textColor=colors.HexColor('#4a5568'),
                fontName='Helvetica',
                alignment=TA_LEFT,
            )
            
            story.append(Paragraph(terms_text, terms_style))
            
            # Enhanced Footer
            story.append(Spacer(1, 30))
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            footer_text = f"📄 Generated on {current_time} | Invoice ID: {generation_id}"
            
            footer_style = ParagraphStyle(
                'EnhancedFooter',
                parent=self.styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#718096'),
                alignment=TA_CENTER,
                borderWidth=1,
                borderColor=colors.HexColor('#e2e8f0'),
                borderPadding=8,
                backColor=colors.HexColor('#f7fafc'),
            )
            
            story.append(Paragraph(footer_text, footer_style))
            
            # Build PDF with enhanced settings
            doc.build(story)
            
            # Get PDF data
            pdf_data = buffer.getvalue()
            buffer.close()
            
            logger.info(f"[{generation_id}] Enhanced multi-item PDF generated successfully: {len(pdf_data):,} bytes")
            return pdf_data
            
        except Exception as e:
            logger.error(f"[{generation_id}] Failed to generate enhanced multi-item PDF: {e}")
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
        """Generate professional invoice PDF with payment integration and proper page breaks."""
        # Ensure currency symbol is not empty
        if not currency_symbol:
            currency_symbol = "₹"  # Default to Rupee
        
        logger.info(f"[{generation_id}] Generating enhanced payment-enabled PDF for {buyer_name} - {len(items)} items")
        
        try:
            # Create PDF in memory with enhanced settings
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=60,
                leftMargin=60,
                topMargin=60,
                bottomMargin=60,
                title=f"Invoice {self._generate_invoice_number(generation_id)}"
            )
            
            # Build invoice content
            story = []
            
            # =================== PAGE 1: INVOICE DETAILS ===================
            
            # Professional Header Section
            header_data = [[
                [Paragraph(f"<b>{company_name}</b>", self.company_style)],
                [Paragraph("INVOICE", self.title_style)]
            ]]
            
            header_table = Table(header_data, colWidths=[4*inch, 3*inch])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ]))
            story.append(header_table)
            story.append(Spacer(1, 20))
            
            # Invoice metadata in professional layout
            invoice_number = self._generate_invoice_number(generation_id)
            due_date = self._calculate_due_date(date)
            
            # Create two-column layout for invoice details
            left_column_data = [
                [Paragraph("<b>BILL TO:</b>", self.section_header_style)],
                [Paragraph(buyer_name, self.info_style)],
            ]
            
            if buyer_email:
                left_column_data.append([Paragraph(f"Email: {buyer_email}", self.info_style)])
            
            right_column_data = [
                [Paragraph("<b>INVOICE DETAILS:</b>", self.section_header_style)],
                [Paragraph(f"<b>Invoice #:</b> {invoice_number}", self.info_style)],
                [Paragraph(f"<b>Issue Date:</b> {date}", self.info_style)],
                [Paragraph(f"<b>Due Date:</b> {due_date}", self.info_style)],
                [Paragraph(f"<b>From:</b> {company_name}", self.info_style)],
            ]
            
            # Combine columns into a table
            details_layout = []
            max_rows = max(len(left_column_data), len(right_column_data))
            for i in range(max_rows):
                left_cell = left_column_data[i][0] if i < len(left_column_data) else ""
                right_cell = right_column_data[i][0] if i < len(right_column_data) else ""
                details_layout.append([left_cell, right_cell])
            
            details_table = Table(details_layout, colWidths=[3.5*inch, 3.5*inch])
            details_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 15),
                ('RIGHTPADDING', (0, 0), (-1, -1), 15),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
                ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#2b77ad')),
            ]))
            
            story.append(details_table)
            story.append(Spacer(1, 30))
            
            # Enhanced Items Table
            line_items_data = [[
                Paragraph("<b>Description</b>", self.info_style),
                Paragraph("<b>Qty</b>", self.info_style),
                Paragraph("<b>Rate</b>", self.info_style),
                Paragraph("<b>Amount</b>", self.info_style)
            ]]
            
            # Add each item as a separate row with enhanced formatting
            subtotal = 0
            for item in items:
                item_name = item['name']
                quantity = item['quantity']
                rate = item['rate']
                amount = quantity * rate
                subtotal += amount
                
                line_items_data.append([
                    Paragraph(item_name, self.info_style),
                    Paragraph(str(quantity), self.info_style),
                    Paragraph(f"{currency_symbol}{rate:.2f}", self.info_style),
                    Paragraph(f"{currency_symbol}{amount:.2f}", self.info_style)
                ])
            
            # Calculate tax and total
            tax_amount = subtotal * tax_rate
            total_amount = subtotal + tax_amount
            
            # Add totals section with enhanced styling
            line_items_data.extend([
                ["", "", "", ""],  # Empty row for spacing
                ["", "", Paragraph("<b>Subtotal:</b>", self.info_style), Paragraph(f"<b>{currency_symbol}{subtotal:.2f}</b>", self.info_style)],
            ])
            
            if tax_rate > 0:
                tax_percentage = tax_rate * 100
                line_items_data.append([
                    "", "", 
                    Paragraph(f"<b>Tax ({tax_percentage:.0f}%):</b>", self.info_style), 
                    Paragraph(f"<b>{currency_symbol}{tax_amount:.2f}</b>", self.info_style)
                ])
            
            line_items_data.append([
                "", "", 
                Paragraph("<b>TOTAL:</b>", self.info_style), 
                Paragraph(f"<b>{currency_symbol}{total_amount:.2f}</b>", self.info_style)
            ])
            
            items_table = Table(line_items_data, colWidths=[3.5*inch, 0.8*inch, 1.3*inch, 1.4*inch])
            items_table.setStyle(TableStyle([
                # Header row styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2b77ad')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),  # Right align numbers
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                
                # Grid and padding
                ('GRID', (0, 0), (-1, len(items)), 1, colors.HexColor('#e2e8f0')),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                
                # Alternate row colors for items
                ('BACKGROUND', (0, 1), (-1, len(items)), colors.HexColor('#f8f9fa')),
                
                # Totals section styling
                ('BACKGROUND', (2, len(items)+2), (-1, -2), colors.HexColor('#e2e8f0')),
                ('BACKGROUND', (2, -1), (-1, -1), colors.HexColor('#2b77ad')),
                ('TEXTCOLOR', (2, -1), (-1, -1), colors.white),
                ('FONTNAME', (2, len(items)+2), (-1, -1), 'Helvetica-Bold'),
                ('LINEABOVE', (2, len(items)+2), (-1, len(items)+2), 2, colors.HexColor('#2b77ad')),
            ]))
            
            story.append(items_table)
            story.append(Spacer(1, 40))
            
            # =================== PAGE BREAK FOR PAYMENT SECTION ===================
            
            if payment_url:
                # Add page break to start payment section on new page
                story.append(PageBreak())
                
                # Payment section header with enhanced styling
                story.append(Paragraph("💳 PAYMENT INFORMATION", self.payment_header_style))
                story.append(Spacer(1, 20))
                
                # Generate enhanced QR code
                qr_bytes = self._create_payment_qr_code(payment_url, size=150)
                
                if qr_bytes:
                    # Create QR code image for ReportLab
                    qr_buffer = io.BytesIO(qr_bytes)
                    qr_image = ReportLabImage(qr_buffer, width=150, height=150)
                    
                    # Enhanced payment instructions with better formatting
                    payment_instructions = f"""
                    <b>🌟 Quick & Secure Payment Options</b><br/><br/>
                    
                    <b>💻 Online Payment:</b><br/>
                    Click or visit: <u><font color="blue">{payment_url}</font></u><br/><br/>
                    
                    <b>📱 Mobile Payment:</b><br/>
                    Scan the QR code with your mobile device for instant payment<br/><br/>
                    
                    <b>💡 Accepted Payment Methods:</b><br/>
                    <font color="green">✓</font> Credit/Debit Cards (Visa, MasterCard, American Express)<br/>
                    <font color="green">✓</font> UPI Payments (Google Pay, PhonePe, Paytm)<br/>
                    <font color="green">✓</font> PayPal & International Wallets<br/>
                    <font color="green">✓</font> Bank Transfer & Wire Transfer<br/><br/>
                    
                    <b>🔒 Security:</b><br/>
                    All payments are processed through secure, encrypted channels.
                    """
                    
                    payment_style = ParagraphStyle(
                        'PaymentInstructions',
                        parent=self.styles['Normal'],
                        fontSize=12,
                        spaceAfter=6,
                        textColor=colors.HexColor('#2d3748'),
                        fontName='Helvetica',
                        alignment=TA_LEFT,
                        leftIndent=10,
                    )
                    
                    # Create enhanced payment table layout
                    payment_data = [[
                        Paragraph(payment_instructions, payment_style),
                        qr_image
                    ]]
                    
                    payment_table = Table(payment_data, colWidths=[4.5*inch, 2.5*inch])
                    payment_table.setStyle(TableStyle([
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0fff4')),
                        ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#38a169')),
                        ('LEFTPADDING', (0, 0), (-1, -1), 20),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
                        ('TOPPADDING', (0, 0), (-1, -1), 20),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
                        ('LINEBELOW', (0, 0), (-1, 0), 3, colors.HexColor('#38a169')),
                    ]))
                    
                    story.append(payment_table)
                    
                else:
                    # Enhanced fallback if QR code generation fails
                    fallback_payment = f"""
                    <b>🌟 Secure Payment Portal</b><br/><br/>
                    
                    <b>Payment Link:</b><br/>
                    <u><font color="blue">{payment_url}</font></u><br/><br/>
                    
                    <b>Accepted Payment Methods:</b><br/>
                    Credit/Debit Cards, UPI, PayPal, Bank Transfer<br/><br/>
                    
                    <font color="red">Note: QR code generation failed. Please use the payment link above.</font>
                    """
                    
                    fallback_table = Table([[Paragraph(fallback_payment, payment_style)]], colWidths=[7*inch])
                    fallback_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fff5f5')),
                        ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#f56565')),
                        ('LEFTPADDING', (0, 0), (-1, -1), 20),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
                        ('TOPPADDING', (0, 0), (-1, -1), 20),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
                    ]))
                    
                    story.append(fallback_table)
                
                story.append(Spacer(1, 30))
                
                # Additional payment information
                payment_info = f"""
                <b>📋 Payment Instructions:</b><br/><br/>
                
                1. Click on the payment link above or scan the QR code<br/>
                2. You will be redirected to our secure payment portal<br/>
                3. Select your preferred payment method<br/>
                4. Enter the amount: <b>{currency_symbol}{total_amount:.2f}</b><br/>
                5. Complete the payment process<br/>
                6. You will receive a payment confirmation email<br/><br/>
                
                <b>❓ Need Help?</b><br/>
                If you encounter any issues with payment, please contact our support team.<br/>
                We're here to help make your payment process smooth and secure.
                """
                
                info_style = ParagraphStyle(
                    'PaymentInfo',
                    parent=self.styles['Normal'],
                    fontSize=11,
                    spaceAfter=6,
                    textColor=colors.HexColor('#4a5568'),
                    fontName='Helvetica',
                    alignment=TA_LEFT,
                    leftIndent=15,
                )
                
                info_table = Table([[Paragraph(payment_info, info_style)]], colWidths=[7*inch])
                info_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f7fafc')),
                    ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e0')),
                    ('LEFTPADDING', (0, 0), (-1, -1), 20),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 20),
                    ('TOPPADDING', (0, 0), (-1, -1), 15),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
                ]))
                
                story.append(info_table)
            
            # =================== TERMS AND FOOTER SECTION ===================
            
            story.append(Spacer(1, 40))
            
            # Enhanced Terms and Conditions
            terms_text = """
            <b>📋 Payment Terms & Conditions:</b><br/><br/>
            
            • Payment is due within 30 days of invoice date<br/>
            • Late payments may incur additional fees as per our policy<br/>
            • All payments should be made in the specified currency<br/>
            • Partial payments are accepted but please notify us in advance<br/><br/>
            
            <b>🙏 Thank you for your business!</b><br/>
            We appreciate your trust in our services. If you have any questions <br/>
            about this invoice or need assistance, please don't hesitate to contact us.
            """
            
            terms_style = ParagraphStyle(
                'TermsStyle',
                parent=self.styles['Normal'],
                fontSize=10,
                spaceAfter=6,
                textColor=colors.HexColor('#4a5568'),
                fontName='Helvetica',
                alignment=TA_LEFT,
            )
            
            story.append(Paragraph(terms_text, terms_style))
            
            # Enhanced Footer
            story.append(Spacer(1, 30))
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            footer_text = f"📄 Generated on {current_time} | Invoice ID: {generation_id}"
            if payment_url:
                footer_text += f" | 💳 Payment-Enabled Invoice"
            
            footer_style = ParagraphStyle(
                'EnhancedFooter',
                parent=self.styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#718096'),
                alignment=TA_CENTER,
                borderWidth=1,
                borderColor=colors.HexColor('#e2e8f0'),
                borderPadding=8,
                backColor=colors.HexColor('#f7fafc'),
            )
            
            story.append(Paragraph(footer_text, footer_style))
            
            # Build PDF with enhanced settings
            doc.build(story)
            
            # Get PDF data
            pdf_data = buffer.getvalue()
            buffer.close()
            
            logger.info(f"[{generation_id}] Enhanced payment-enabled PDF generated successfully: {len(pdf_data):,} bytes")
            return pdf_data
            
        except Exception as e:
            logger.error(f"[{generation_id}] Failed to generate enhanced payment PDF: {e}")
            raise
