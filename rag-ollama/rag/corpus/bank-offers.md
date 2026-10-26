# Bank and Payment Offers

Bank offers are the final step in the discount chain and apply to the cart
total after all item-level discounts.

## Caps

Every bank offer carries a maximum discount cap. The ICICI Bank offer is 10%
off with a cap of 500 rupees, so a 10000 rupee cart receives 500 rupees off,
not 1000.

## Eligibility

A bank offer requires the payment instrument to match at checkout. Offers are
not stacked with each other: when a cart qualifies for two bank offers, the
engine applies the one that produces the larger discount for the customer.
