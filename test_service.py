import unittest
from decimal import Decimal
from service import DiscountService
from fake_data import cart_items, customer, payment_info, active_vouchers

class TestDiscountService(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        self.service = DiscountService(active_vouchers=active_vouchers)

    async def test_multiple_discount_scenario(self):
        """
        Tests the stacking:
        Base: 1000
        - 40% PUMA = 600
        - 10% T-shirts = 540
        - 10% ICICI = 486
        """
        result = await self.service.calculate_cart_discounts(
            cart_items=cart_items,
            customer=customer,
            payment_info=payment_info
        )

        self.assertEqual(result.original_price, Decimal("1000.00"))
        self.assertEqual(result.final_price, Decimal("486.00"))
        
        # Verify specific discounts were recorded correctly
        self.assertEqual(result.applied_discounts["PUMA Brand Offer"], Decimal("400.00"))
        self.assertEqual(result.applied_discounts["T-shirts Category Offer"], Decimal("60.00"))
        self.assertEqual(result.applied_discounts["ICICI Bank Offer"], Decimal("54.00"))

    async def test_voucher_validation_success(self):
        is_valid = await self.service.validate_discount_code(
            code="SUPER69",
            cart_items=cart_items,
            customer=customer
        )
        self.assertTrue(is_valid)

    async def test_full_stack_with_voucher(self):
        """
        Base: 1000
        - 40% PUMA = 600
        - 10% T-shirts = 540
        - 69% SUPER69 Voucher = 167.40
        - 10% ICICI = 150.66
        """
        result = await self.service.calculate_cart_discounts(
            cart_items=cart_items,
            customer=customer,
            payment_info=payment_info,
            voucher_code="SUPER69"
        )
        self.assertEqual(result.final_price, Decimal("150.66"))
        self.assertIn("Voucher SUPER69", result.applied_discounts)

if __name__ == "__main__":
    unittest.main()