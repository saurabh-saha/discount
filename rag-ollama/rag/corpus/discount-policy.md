# Discount Stacking Policy

Discounts are applied in a fixed, margin-safe order. The order is not
configurable, because changing it changes the final payable amount.

1. Brand-specific discounts, for example 40% off PUMA.
2. Category-specific deals, for example 10% off T-shirts.
3. Voucher codes, for example SUPER69.
4. Bank and payment offers, for example 10% off with ICICI Bank.

## Successive calculation

Percentages are calculated successively, on the discounted remainder, never
additively. A 40% brand discount followed by a 10% category deal on a 1000
rupee item yields 540 rupees, not 500 rupees. Additive stacking is treated as
a margin bug and is rejected in code review.

## Application level

Brand, category and voucher restrictions are evaluated at the item level, so
one ineligible item in a cart does not block the rest. Bank offers are
applied once at the cart level, after every item-level discount has run.
