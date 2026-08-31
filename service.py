from typing import List, Optional, Dict
from decimal import Decimal
from models import CartItem, CustomerProfile, PaymentInfo, DiscountedPrice, VoucherConfig, CustomerTier

class DiscountService:
    def __init__(self, active_vouchers: Dict[str, VoucherConfig]):
        """
        In a real app, these configs would be fetched from a database.
        """
        self.active_vouchers = active_vouchers
        
        # Hardcoded for this scenario, normally fetched from DB/Cache
        self.brand_discounts = {"PUMA": Decimal("0.40")} # 40% off
        self.category_discounts = {"T-shirts": Decimal("0.10")} # 10% off
        self.bank_offers = {"ICICI": Decimal("0.10")} # 10% off

    async def validate_discount_code(
        self,
        code: str,
        cart_items: List[CartItem],
        customer: CustomerProfile
    ) -> bool:
        """Validates voucher against brand, category, and customer tier rules."""
        voucher = self.active_vouchers.get(code.upper())
        if not voucher:
            return False

        # Tier validation
        tier_hierarchy = {CustomerTier.STANDARD: 1, CustomerTier.GOLD: 2, CustomerTier.PLATINUM: 3}
        if tier_hierarchy[customer.tier] < tier_hierarchy[voucher.min_tier]:
            return False

        # Item validation (At least one item must be eligible)
        has_eligible_item = False
        for item in cart_items:
            brand_allowed = item.product.brand not in voucher.excluded_brands
            category_allowed = (
                not voucher.allowed_categories or 
                item.product.category in voucher.allowed_categories
            )
            if brand_allowed and category_allowed:
                has_eligible_item = True
                break

        return has_eligible_item

    async def calculate_cart_discounts(
        self,
        cart_items: List[CartItem],
        customer: CustomerProfile,
        payment_info: Optional[PaymentInfo] = None,
        voucher_code: Optional[str] = None
    ) -> DiscountedPrice:
        
        total_original = Decimal("0.0")
        total_final = Decimal("0.0")
        applied_discounts: Dict[str, Decimal] = {}

        # 1. & 2. Apply Brand/Category & Voucher Discounts (Item Level)
        is_voucher_valid = False
        if voucher_code:
            is_voucher_valid = await self.validate_discount_code(voucher_code, cart_items, customer)

        for item in cart_items:
            item_base_total = item.product.base_price * item.quantity
            total_original += item_base_total
            
            # Start tracking current price of this item batch
            current_item_total = item_base_total

            # Apply Brand Discount
            brand_disc_pct = self.brand_discounts.get(item.product.brand, Decimal("0.0"))
            if brand_disc_pct > 0:
                discount_amt = current_item_total * brand_disc_pct
                current_item_total -= discount_amt
                applied_discounts[f"{item.product.brand} Brand Offer"] = applied_discounts.get(f"{item.product.brand} Brand Offer", Decimal("0.0")) + discount_amt

            # Apply Category Discount
            cat_disc_pct = self.category_discounts.get(item.product.category, Decimal("0.0"))
            if cat_disc_pct > 0:
                discount_amt = current_item_total * cat_disc_pct
                current_item_total -= discount_amt
                applied_discounts[f"{item.product.category} Category Offer"] = applied_discounts.get(f"{item.product.category} Category Offer", Decimal("0.0")) + discount_amt

            # Apply Voucher Discount
            if is_voucher_valid:
                voucher = self.active_vouchers[voucher_code.upper()]
                if item.product.brand not in voucher.excluded_brands:
                    discount_amt = current_item_total * voucher.discount_percent
                    current_item_total -= discount_amt
                    applied_discounts[f"Voucher {voucher_code}"] = applied_discounts.get(f"Voucher {voucher_code}", Decimal("0.0")) + discount_amt

            total_final += current_item_total

        # 3. Apply Bank Offers (Cart Level)
        if payment_info and payment_info.bank_name:
            bank_disc_pct = self.bank_offers.get(payment_info.bank_name, Decimal("0.0"))
            if bank_disc_pct > 0:
                bank_discount_amt = total_final * bank_disc_pct
                total_final -= bank_discount_amt
                applied_discounts[f"{payment_info.bank_name} Bank Offer"] = bank_discount_amt

        # Formatting
        total_final = total_final.quantize(Decimal("0.01"))
        total_original = total_original.quantize(Decimal("0.01"))
        
        return DiscountedPrice(
            original_price=total_original,
            final_price=total_final,
            applied_discounts={k: v.quantize(Decimal("0.01")) for k, v in applied_discounts.items()},
            message="Discounts applied successfully!" if applied_discounts else "No eligible discounts."
        )