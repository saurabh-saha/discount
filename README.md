# E-Commerce Discount Engine

A robust, asynchronous Python service for calculating and stacking complex e-commerce discounts. This engine handles brand-specific offers, category-specific deals, custom voucher codes, and bank-specific payment discounts.

## 🚀 Features

* **Hierarchical Discount Stacking:** Applies discounts in a specific, margin-safe order:
  1. Brand-specific discounts (e.g., 40% off PUMA)
  2. Category-specific deals (e.g., 10% off T-shirts)
  3. Voucher codes (e.g., SUPER69 for 69% off)
  4. Bank/Payment offers (e.g., 10% off via ICICI Bank)
* **Successive Calculation:** Calculates percentages successively (on the discounted remainder) rather than additively, protecting business margins.
* **Granular Application:** Processes brand, category, and voucher restrictions at the *item level*, while applying bank offers at the *cart level*.
* **Voucher Validation:** Validates coupon codes against excluded brands, allowed categories, and customer loyalty tiers.

## 📁 Project Structure

* `models.py` - Core data structures using Python `dataclasses` (Product, CartItem, CustomerProfile, VoucherConfig, etc.).
* `service.py` - The core business logic (`DiscountService`). Contains methods for validation and discount calculations.
* `fake_data.py` - Dummy data setup mapping to real-world e-commerce scenarios.
* `test_service.py` - Asynchronous unit tests validating the business logic and mathematical accuracy.

## 🛠️ Prerequisites

* Python 3.7+ (relies on `dataclasses`, `typing`, and `asyncio`)
* No external dependencies (Flask/Django/FastAPI are not required to run the core logic)

## 💻 Running the Code

Because this is a core logic module, you don't need a server to run it. You can validate the logic directly by running the test suite.

```bash
# Run the test suite
python -m unittest test_service.py -v