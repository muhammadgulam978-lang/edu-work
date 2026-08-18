"""
DUMMY PAYMENT SERVICE - For Demo/Testing Only
Real payments ke liye: Stripe, PayPal, JazzCash integration karo
"""

from django.utils import timezone
from decimal import Decimal
from .models import FeeVoucher, StudentBalance, StudentLedger
import random
import string

class DummyPaymentService:
    """Simulates payment processing without real gateway"""
    
    @staticmethod
    def generate_transaction_id():
        """Generate dummy transaction ID"""
        return f"TXN-{timezone.now().strftime('%Y%m%d%H%M%S')}-{random.randint(10000, 99999)}"
    
    @staticmethod
    def process_payment(voucher_id, amount_paid, payment_method='CASH'):
        """
        Process payment for a voucher
        
        Args:
            voucher_id: FeeVoucher ID
            amount_paid: Amount paid (Decimal)
            payment_method: 'CASH', 'CARD', 'ONLINE', 'CHEQUE'
        
        Returns:
            dict with payment status
        """
        try:
            voucher = FeeVoucher.objects.get(id=voucher_id)
            amount_paid = Decimal(str(amount_paid))
            
            # Validate amount
            if amount_paid <= 0:
                return {
                    'success': False,
                    'message': 'Amount must be greater than 0',
                    'transaction_id': None
                }
            
            # Generate transaction ID
            transaction_id = DummyPaymentService.generate_transaction_id()
            
            # Check if payment exceeds voucher amount
            if amount_paid > voucher.net_amount:
                excess = amount_paid - voucher.net_amount
                return {
                    'success': False,
                    'message': f'Amount exceeds voucher amount by Rs.{excess}',
                    'transaction_id': None
                }
            
            # Update voucher status
            if amount_paid == voucher.net_amount:
                voucher.status = 'PAID'
                status_msg = 'PAID'
            elif amount_paid < voucher.net_amount:
                voucher.status = 'PARTIAL'
                status_msg = 'PARTIAL'
            
            voucher.save()
            
            # Update Student Balance
            balance, _ = StudentBalance.objects.get_or_create(student=voucher.student)
            balance.outstanding_amount -= amount_paid
            if balance.outstanding_amount < 0:
                balance.outstanding_amount = Decimal('0')
            balance.save()
            
            # Create Ledger Entry
            StudentLedger.objects.create(
                student=voucher.student,
                description=f"Payment received for {voucher.voucher_no}",
                credit=amount_paid,
                balance=balance.outstanding_amount,
                reference_no=transaction_id
            )
            
            return {
                'success': True,
                'message': f'Payment processed successfully. Status: {status_msg}',
                'transaction_id': transaction_id,
                'amount_paid': amount_paid,
                'remaining_balance': balance.outstanding_amount,
                'voucher_status': voucher.status,
                'payment_method': payment_method,
                'timestamp': timezone.now()
            }
            
        except FeeVoucher.DoesNotExist:
            return {
                'success': False,
                'message': f'Voucher ID {voucher_id} not found',
                'transaction_id': None
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error processing payment: {str(e)}',
                'transaction_id': None
            }
    
    @staticmethod
    def process_partial_payment(voucher_id, amount_paid):
        """Alias for partial payment"""
        return DummyPaymentService.process_payment(voucher_id, amount_paid, 'CASH')
    
    @staticmethod
    def process_full_payment(voucher_id):
        """Process full voucher amount"""
        voucher = FeeVoucher.objects.get(id=voucher_id)
        return DummyPaymentService.process_payment(voucher_id, voucher.net_amount, 'CASH')
    
    @staticmethod
    def refund_payment(voucher_id, refund_amount):
        """
        Process refund for a voucher
        """
        try:
            voucher = FeeVoucher.objects.get(id=voucher_id)
            refund_amount = Decimal(str(refund_amount))
            
            # Update balance
            balance, _ = StudentBalance.objects.get_or_create(student=voucher.student)
            balance.outstanding_amount += refund_amount
            balance.save()
            
            # Create ledger entry
            transaction_id = DummyPaymentService.generate_transaction_id()
            StudentLedger.objects.create(
                student=voucher.student,
                description=f"Refund for {voucher.voucher_no}",
                debit=refund_amount,
                balance=balance.outstanding_amount,
                reference_no=transaction_id
            )
            
            return {
                'success': True,
                'message': 'Refund processed successfully',
                'transaction_id': transaction_id,
                'refund_amount': refund_amount
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Refund error: {str(e)}'
            }
    
    @staticmethod
    def get_payment_summary(student_id=None):
        """
        Get payment summary for all or specific student
        """
        if student_id:
            vouchers = FeeVoucher.objects.filter(student_id=student_id)
        else:
            vouchers = FeeVoucher.objects.all()
        
        total_generated = sum(Decimal(str(v.net_amount)) for v in vouchers)
        paid = sum(Decimal(str(v.net_amount)) for v in vouchers if v.status == 'PAID')
        partial = vouchers.filter(status='PARTIAL').count()
        unpaid = vouchers.filter(status='UNPAID').count()
        
        return {
            'total_vouchers': vouchers.count(),
            'total_amount': total_generated,
            'amount_paid': paid,
            'amount_pending': total_generated - paid,
            'paid_vouchers': vouchers.filter(status='PAID').count(),
            'partial_vouchers': partial,
            'unpaid_vouchers': unpaid
        }