# Voucher Validation Rules

A voucher is valid only when every check below passes. Validation is
fail-closed: an unknown voucher code is rejected rather than ignored.

## Checks

- Excluded brands. A voucher that lists a brand as excluded cannot apply to
  any item of that brand.
- Allowed categories. If the voucher names allowed categories, items outside
  those categories are skipped.
- Customer tier. Tier-gated vouchers require the customer profile to match,
  for example SUPER69 requires the GOLD tier or above.

## Known codes

SUPER69 gives 69% off, excludes the brand NIKE, and is limited to the
T-SHIRT and SHIRT categories. It requires the GOLD loyalty tier.

WELCOME10 gives 10% off with no brand or category restriction and is
available to every tier, but only on a customer's first order.
