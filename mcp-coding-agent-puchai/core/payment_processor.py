"""
Payment integration module for invoice PDF generator

Handles dummy payment processing, payment links, and QR code generation.
"""

import json
import logging
import qrcode
import uuid
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Dict, Optional, List
from PIL import Image

logger = logging.getLogger(__name__)


class PaymentMethod:
    """Payment method configuration."""
    
    def __init__(self, method_id: str, name: str, enabled: bool = True):
        self.method_id = method_id
        self.name = name
        self.enabled = enabled


class PaymentTransaction:
    """Payment transaction model."""
    
    def __init__(
        self,
        invoice_id: str,
        amount: float,
        currency: str,
        customer_email: str = "",
        payment_method: str = "card"
    ):
        self.transaction_id = str(uuid.uuid4())
        self.invoice_id = invoice_id
        self.amount = amount
        self.currency = currency
        self.customer_email = customer_email
        self.payment_method = payment_method
        self.status = "pending"  # pending, processing, completed, failed, refunded
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.payment_url = None
        self.confirmation_code = None
    
    def to_dict(self) -> Dict:
        """Convert transaction to dictionary."""
        return {
            "transaction_id": self.transaction_id,
            "invoice_id": self.invoice_id,
            "amount": self.amount,
            "currency": self.currency,
            "customer_email": self.customer_email,
            "payment_method": self.payment_method,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "payment_url": self.payment_url,
            "confirmation_code": self.confirmation_code
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PaymentTransaction':
        """Create transaction from dictionary."""
        transaction = cls(
            invoice_id=data["invoice_id"],
            amount=data["amount"],
            currency=data["currency"],
            customer_email=data.get("customer_email", ""),
            payment_method=data.get("payment_method", "card")
        )
        transaction.transaction_id = data.get("transaction_id", transaction.transaction_id)
        transaction.status = data.get("status", "pending")
        transaction.created_at = data.get("created_at", transaction.created_at)
        transaction.updated_at = data.get("updated_at", transaction.updated_at)
        transaction.payment_url = data.get("payment_url")
        transaction.confirmation_code = data.get("confirmation_code")
        return transaction


class PaymentProcessor:
    """Handles payment processing and integration."""
    
    def __init__(self, base_url: str = "http://localhost:8086"):
        """Initialize payment processor."""
        self.base_url = base_url
        self.data_dir = Path("data")
        self.payments_file = self.data_dir / "payments.json"
        self.invoices_file = self.data_dir / "invoices.json"
        self._ensure_data_directory()
        
        # Available payment methods
        self.payment_methods = {
            "card": PaymentMethod("card", "Credit/Debit Card"),
            "paypal": PaymentMethod("paypal", "PayPal"),
            "bank_transfer": PaymentMethod("bank_transfer", "Bank Transfer"),
            "crypto": PaymentMethod("crypto", "Cryptocurrency"),
            "upi": PaymentMethod("upi", "UPI Payment")
        }
        
        self.transactions: Dict[str, PaymentTransaction] = {}
        self.invoices: Dict[str, Dict] = {}
        self.load_data()
    
    def _ensure_data_directory(self):
        """Ensure data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def load_data(self):
        """Load payment and invoice data."""
        # Load transactions
        if self.payments_file.exists():
            try:
                with open(self.payments_file, 'r', encoding='utf-8') as f:
                    payments_data = json.load(f)
                self.transactions = {
                    tid: PaymentTransaction.from_dict(data)
                    for tid, data in payments_data.items()
                }
            except Exception as e:
                logger.error(f"Failed to load payments: {e}")
                self.transactions = {}
        
        # Load invoices
        if self.invoices_file.exists():
            try:
                with open(self.invoices_file, 'r', encoding='utf-8') as f:
                    self.invoices = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load invoices: {e}")
                self.invoices = {}
    
    def save_data(self):
        """Save payment and invoice data."""
        try:
            # Save transactions
            payments_data = {
                tid: transaction.to_dict()
                for tid, transaction in self.transactions.items()
            }
            with open(self.payments_file, 'w', encoding='utf-8') as f:
                json.dump(payments_data, f, indent=2, ensure_ascii=False)
            
            # Save invoices
            with open(self.invoices_file, 'w', encoding='utf-8') as f:
                json.dump(self.invoices, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save payment data: {e}")
            raise
    
    def create_payment_link(
        self,
        invoice_id: str,
        amount: float,
        currency: str = "₹",
        customer_email: str = "",
        payment_methods: List[str] = None
    ) -> Dict:
        """Create a payment link for an invoice."""
        try:
            # Validate inputs
            if not invoice_id or not invoice_id.strip():
                raise ValueError("Invoice ID cannot be empty")
            
            if amount <= 0:
                raise ValueError("Amount must be greater than zero")
            
            if not currency:
                currency = "₹"  # Default currency
            
            if payment_methods is None:
                payment_methods = ["card", "upi", "paypal"]
            
            logger.info(f"Creating payment link for invoice {invoice_id}, amount: {currency}{amount:.2f}")
            
            # Create transaction
            transaction = PaymentTransaction(
                invoice_id=invoice_id,
                amount=amount,
                currency=currency,
                customer_email=customer_email
            )
            
            # Create payment URL
            payment_url = f"{self.base_url}/payment/{transaction.transaction_id}"
            transaction.payment_url = payment_url
            
            # Store transaction
            self.transactions[transaction.transaction_id] = transaction
            
            # Update invoice with payment info
            if invoice_id not in self.invoices:
                self.invoices[invoice_id] = {
                    "invoice_id": invoice_id,
                    "status": "draft",
                    "amount": amount,
                    "currency": currency,
                    "created_at": datetime.now().isoformat()
                }
            
            self.invoices[invoice_id]["payment_link"] = payment_url
            self.invoices[invoice_id]["transaction_id"] = transaction.transaction_id
            self.invoices[invoice_id]["status"] = "pending_payment"
            
            # Save data with error handling
            try:
                self.save_data()
            except Exception as save_error:
                logger.error(f"Failed to save payment data: {save_error}")
                # Remove transaction from memory if save failed
                if transaction.transaction_id in self.transactions:
                    del self.transactions[transaction.transaction_id]
                raise
            
            logger.info(f"Created payment link for invoice {invoice_id}: {payment_url}")
            
            return {
                "transaction_id": transaction.transaction_id,
                "payment_url": payment_url,
                "amount": amount,
                "currency": currency,
                "available_methods": [
                    self.payment_methods[method].name 
                    for method in payment_methods 
                    if method in self.payment_methods
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to create payment link for invoice {invoice_id}: {e}")
            raise ValueError(f"Payment link creation failed: {str(e)}")
    
    def generate_payment_qr(self, transaction_id: str) -> Optional[bytes]:
        """Generate QR code for payment."""
        transaction = self.transactions.get(transaction_id)
        if not transaction:
            return None
        
        try:
            # Create QR code with payment URL
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(transaction.payment_url)
            qr.make(fit=True)
            
            # Create QR code image
            qr_image = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to bytes
            buffer = BytesIO()
            qr_image.save(buffer, format='PNG')
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to generate QR code: {e}")
            return None
    
    def process_dummy_payment(
        self,
        transaction_id: str,
        payment_method: str = "card",
        simulate_success: bool = True
    ) -> Dict:
        """Process a dummy payment (for testing/demo)."""
        transaction = self.transactions.get(transaction_id)
        if not transaction:
            return {"success": False, "error": "Transaction not found"}
        
        if transaction.status != "pending":
            return {"success": False, "error": f"Transaction already {transaction.status}"}
        
        # Simulate processing
        transaction.status = "processing"
        transaction.payment_method = payment_method
        transaction.updated_at = datetime.now().isoformat()
        
        # Simulate payment result
        if simulate_success:
            transaction.status = "completed"
            transaction.confirmation_code = f"PAY_{transaction.transaction_id[:8].upper()}"
            
            # Update invoice status
            if transaction.invoice_id in self.invoices:
                self.invoices[transaction.invoice_id]["status"] = "paid"
                self.invoices[transaction.invoice_id]["paid_at"] = datetime.now().isoformat()
                self.invoices[transaction.invoice_id]["payment_method"] = payment_method
            
            result = {
                "success": True,
                "status": "completed",
                "confirmation_code": transaction.confirmation_code,
                "message": f"Payment of {transaction.currency}{transaction.amount:.2f} completed successfully"
            }
        else:
            transaction.status = "failed"
            result = {
                "success": False,
                "status": "failed",
                "error": "Payment processing failed",
                "message": "Please try again or use a different payment method"
            }
        
        transaction.updated_at = datetime.now().isoformat()
        self.save_data()
        
        logger.info(f"Processed payment for transaction {transaction_id}: {result}")
        return result
    
    def get_transaction_status(self, transaction_id: str) -> Optional[Dict]:
        """Get transaction status."""
        transaction = self.transactions.get(transaction_id)
        if not transaction:
            return None
        
        return {
            "transaction_id": transaction.transaction_id,
            "invoice_id": transaction.invoice_id,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "status": transaction.status,
            "payment_method": transaction.payment_method,
            "created_at": transaction.created_at,
            "updated_at": transaction.updated_at,
            "confirmation_code": transaction.confirmation_code
        }
    
    def get_invoice_payments(self, invoice_id: str) -> List[Dict]:
        """Get all payment transactions for an invoice."""
        return [
            transaction.to_dict()
            for transaction in self.transactions.values()
            if transaction.invoice_id == invoice_id
        ]
    
    def refund_payment(self, transaction_id: str, reason: str = "Customer request") -> Dict:
        """Process a refund (dummy implementation)."""
        transaction = self.transactions.get(transaction_id)
        if not transaction:
            return {"success": False, "error": "Transaction not found"}
        
        if transaction.status != "completed":
            return {"success": False, "error": "Only completed payments can be refunded"}
        
        # Process refund
        transaction.status = "refunded"
        transaction.updated_at = datetime.now().isoformat()
        
        # Update invoice status
        if transaction.invoice_id in self.invoices:
            self.invoices[transaction.invoice_id]["status"] = "refunded"
            self.invoices[transaction.invoice_id]["refunded_at"] = datetime.now().isoformat()
            self.invoices[transaction.invoice_id]["refund_reason"] = reason
        
        self.save_data()
        
        result = {
            "success": True,
            "status": "refunded",
            "refund_amount": transaction.amount,
            "currency": transaction.currency,
            "reason": reason,
            "message": f"Refund of {transaction.currency}{transaction.amount:.2f} processed successfully"
        }
        
        logger.info(f"Processed refund for transaction {transaction_id}: {result}")
        return result
    
    def get_payment_analytics(self, days: int = 30) -> Dict:
        """Get payment analytics for the specified period."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        total_transactions = 0
        completed_payments = 0
        failed_payments = 0
        total_amount = 0.0
        refunded_amount = 0.0
        
        payment_methods = {}
        daily_amounts = {}
        
        for transaction in self.transactions.values():
            transaction_date = datetime.fromisoformat(transaction.created_at)
            if transaction_date < cutoff_date:
                continue
            
            total_transactions += 1
            
            if transaction.status == "completed":
                completed_payments += 1
                total_amount += transaction.amount
                
                # Track payment methods
                method = transaction.payment_method or "unknown"
                payment_methods[method] = payment_methods.get(method, 0) + 1
                
                # Track daily amounts
                date_str = transaction_date.strftime("%Y-%m-%d")
                daily_amounts[date_str] = daily_amounts.get(date_str, 0) + transaction.amount
                
            elif transaction.status == "failed":
                failed_payments += 1
            elif transaction.status == "refunded":
                refunded_amount += transaction.amount
        
        success_rate = (completed_payments / total_transactions * 100) if total_transactions > 0 else 0
        
        return {
            "period_days": days,
            "total_transactions": total_transactions,
            "completed_payments": completed_payments,
            "failed_payments": failed_payments,
            "success_rate": round(success_rate, 2),
            "total_amount": total_amount,
            "refunded_amount": refunded_amount,
            "net_amount": total_amount - refunded_amount,
            "payment_methods": payment_methods,
            "daily_amounts": daily_amounts
        }
