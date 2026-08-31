from decimal import Decimal
from models import (
    Product, BrandTier, CartItem, PaymentInfo, 
    CustomerProfile, CustomerTier, VoucherConfig
)

# 1. Product Setup (PUMA T-shirt)
puma_tshirt = Product(
    id="PROD_123",
    brand="PUMA",
    brand_tier=BrandTier.PREMIUM,
    category="T-shirts",
    base_price=Decimal("1000.00"),
    current_price=Decimal("1000.00") 
)

# 2. Cart Setup
cart_items = [
    CartItem(product=puma_tshirt, quantity=1, size="L")
]

# 3. Customer Profile
customer = CustomerProfile(
    id="CUST_999",
    tier=CustomerTier.GOLD
)

# 4. Payment Setup (ICICI Bank)
payment_info = PaymentInfo(
    method="CARD",
    bank_name="ICICI",
    card_type="CREDIT"
)

# 5. Voucher Setup
active_vouchers = {
    "SUPER69": VoucherConfig(
        code="SUPER69",
        discount_percent=Decimal("0.69"),
        excluded_brands=["NIKE"], # PUMA is allowed
        allowed_categories=None,
        min_tier=CustomerTier.STANDARD
    )
}