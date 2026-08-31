from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime
from decimal import Decimal
from enum import Enum

class BrandTier(Enum):
    PREMIUM = "premium"
    REGULAR = "regular"
    BUDGET = "budget"

class CustomerTier(Enum):
    STANDARD = "standard"
    GOLD = "gold"
    PLATINUM = "platinum"

@dataclass
class Product:
    id: str
    brand: str
    brand_tier: BrandTier
    category: str
    base_price: Decimal
    current_price: Decimal  

@dataclass
class CartItem:
    product: Product
    quantity: int
    size: str

@dataclass
class PaymentInfo:
    method: str  
    bank_name: Optional[str]
    card_type: Optional[str]  

@dataclass
class CustomerProfile:
    id: str
    tier: CustomerTier

@dataclass
class DiscountedPrice:
    original_price: Decimal
    final_price: Decimal
    applied_discounts: Dict[str, Decimal] = field(default_factory=dict)
    message: str = ""

# --- Discount Rule Configurations ---

@dataclass
class VoucherConfig:
    code: str
    discount_percent: Decimal
    excluded_brands: List[str]
    allowed_categories: Optional[List[str]]
    min_tier: CustomerTier