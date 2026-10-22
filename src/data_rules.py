
"""Documented business rules for the Online Retail II dataset.

These are project-defined analytical rules, not original dataset labels.
The source workbook must remain unchanged.
"""

DATASET_NAME = "UCI Online Retail II"
SOURCE_SHEETS = ["Year 2009-2010", "Year 2010-2011"]

REQUIRED_COLUMNS = [
    "Invoice",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "Price",
    "Customer ID",
    "Country",
]

# Cancellation identification rule:
# Invoice values beginning with C are flagged as cancellations.
CANCELLATION_PREFIX = "C"

# Negative quantities are candidates for returns or adjustments.
# They are not automatically treated as confirmed customer returns.
NEGATIVE_QUANTITY_RULE = "flag_for_review"

# Missing customer IDs are retained in overall transaction analysis.
# They are not assigned fabricated customer identifiers.
MISSING_CUSTOMER_RULE = "retain_and_mark_unknown"

# Exact duplicate rows are flagged, not automatically removed.
DUPLICATE_RULE = "preserve_and_flag"

# Zero and negative prices are retained and flagged for review.
PRICE_RULE = "retain_and_flag_nonpositive_prices"

# Known non-product/service codes observed during inspection.
# This list is not necessarily exhaustive.
NON_PRODUCT_STOCK_CODES = {"POST", "D", "M", "DOT"}


def is_cancellation(invoice):
    """Return True when the invoice identifier starts with C."""
    if invoice is None:
        return False

    value = str(invoice).strip()
    return value.upper().startswith(CANCELLATION_PREFIX)


def classify_quantity(quantity):
    """Classify quantity without assuming every negative is a return."""
    if quantity is None:
        return "missing_quantity"
    if quantity < 0:
        return "negative_quantity_candidate"
    if quantity == 0:
        return "zero_quantity"
    return "positive_quantity"


def classify_price(price):
    """Flag nonpositive prices without removing the record."""
    if price is None:
        return "missing_price"
    if price < 0:
        return "negative_price"
    if price == 0:
        return "zero_price"
    return "positive_price"


def has_customer_id(customer_id):
    """Check whether a customer ID is present."""
    if customer_id is None:
        return False

    # Handles pandas NaN without requiring pandas in this module.
    try:
        if customer_id != customer_id:
            return False
    except (TypeError, ValueError):
        pass

    return str(customer_id).strip() != ""


def is_non_product_code(stock_code):
    """Identify stock codes on the project's initial review list."""
    if stock_code is None:
        return False
    return str(stock_code).strip().upper() in NON_PRODUCT_STOCK_CODES
