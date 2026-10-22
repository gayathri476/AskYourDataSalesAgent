
"""Load UCI Online Retail II Excel sheets into DuckDB."""

from pathlib import Path

import duckdb
import pandas as pd

from src.data_rules import (
    REQUIRED_COLUMNS,
    SOURCE_SHEETS,
    is_cancellation,
    classify_quantity,
    classify_price,
    has_customer_id,
    is_non_product_code,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXCEL_PATH = PROJECT_ROOT / "data" / "online_retail_II.xlsx"
DB_PATH = PROJECT_ROOT / "data" / "sales.duckdb"
TABLE_NAME = "retail_transactions"


def prepare_sheet(excel_file, sheet_name):
    """Read and validate one source sheet without dropping records."""
    df = pd.read_excel(excel_file, sheet_name=sheet_name)

    missing_columns = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing_columns:
        raise ValueError(
            f"{sheet_name} is missing columns: {sorted(missing_columns)}"
        )

    # Preserve source columns and identify where each row came from.
    df["source_sheet"] = sheet_name

    # These flags support investigation; they do not delete transactions.
    df["is_cancellation"] = df["Invoice"].apply(is_cancellation)
    df["quantity_status"] = df["Quantity"].apply(classify_quantity)
    df["price_status"] = df["Price"].apply(classify_price)
    df["has_customer_id"] = df["Customer ID"].apply(has_customer_id)
    df["is_non_product_code"] = df["StockCode"].apply(
        is_non_product_code
    )

    # Mark every member of an exact-duplicate group based on source columns.
    df["is_exact_duplicate"] = df.duplicated(
        subset=REQUIRED_COLUMNS,
        keep=False,
    )

    return df


def build_database():
    """Build the analytical table and return basic validation results."""
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {EXCEL_PATH}\n"
            "Place online_retail_II.xlsx in the data folder."
        )

    frames = []
    source_counts = {}

    for sheet_name in SOURCE_SHEETS:
        df = prepare_sheet(EXCEL_PATH, sheet_name)
        source_counts[sheet_name] = len(df)
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)

    # Convert Excel date values to pandas datetime values.
    combined["InvoiceDate"] = pd.to_datetime(
        combined["InvoiceDate"], errors="raise"
    )

    # This is the arithmetic line amount, not a claim about accounting totals.
    combined["line_value"] = combined["Quantity"] * combined["Price"]

    # Create a fresh database file so repeated runs don't append duplicate data.
    if DB_PATH.exists():
        DB_PATH.unlink()

    connection = duckdb.connect(str(DB_PATH))
    try:
        connection.register("incoming_data", combined)
        connection.execute(
            f"CREATE TABLE {TABLE_NAME} AS SELECT * FROM incoming_data"
        )

        loaded_count = connection.execute(
            f"SELECT COUNT(*) FROM {TABLE_NAME}"
        ).fetchone()[0]

        summary = connection.execute(
            f"""
            SELECT
                COUNT(*) AS total_rows,
                SUM(CASE WHEN is_cancellation THEN 1 ELSE 0 END)
                    AS cancellation_invoice_rows,
                SUM(CASE WHEN Quantity < 0 THEN 1 ELSE 0 END)
                    AS negative_quantity_rows,
                SUM(CASE WHEN "Customer ID" IS NULL THEN 1 ELSE 0 END)
                    AS missing_customer_rows,
                SUM(CASE WHEN is_exact_duplicate THEN 1 ELSE 0 END)
                    AS rows_marked_as_exact_duplicates
            FROM {TABLE_NAME}
            """
        ).fetchdf()

        if loaded_count != len(combined):
            raise RuntimeError(
                f"Row-count mismatch: combined={len(combined)}, "
                f"database={loaded_count}"
            )

        return {
            "database_path": str(DB_PATH),
            "source_counts": source_counts,
            "combined_rows": len(combined),
            "loaded_rows": loaded_count,
            "summary": summary,
        }
    finally:
        connection.close()


if __name__ == "__main__":
    result = build_database()

    print("\nSource row counts:")
    for sheet, count in result["source_counts"].items():
        print(f"  {sheet}: {count:,}")

    print(f"\nCombined rows: {result['combined_rows']:,}")
    print(f"Database rows: {result['loaded_rows']:,}")
    print(f"Database file: {result['database_path']}")
    print("\nData-quality summary:")
    print(result["summary"].to_string(index=False))
