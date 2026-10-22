
"""Read-only SQL execution and basic safety validation."""

from pathlib import Path
import re

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "sales.duckdb"

MAX_ROWS = 500
QUERY_TIMEOUT_SECONDS = 15

# Only one read-only SELECT statement is accepted.
FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "REPLACE", "TRUNCATE", "ATTACH", "DETACH", "COPY",
    "EXPORT", "IMPORT", "INSTALL", "LOAD", "CALL", "PRAGMA",
    "SET", "RESET", "EXECUTE", "PREPARE", "DEALLOCATE",
    "GRANT", "REVOKE", "VACUUM", "CHECKPOINT", "FOR",
}


class SQLSafetyError(ValueError):
    """Raised when a query does not meet the safety rules."""


def validate_sql(sql: str) -> str:
    """Validate a single read-only SELECT statement.

    This is a conservative first-pass validator, not a full SQL parser.
    """
    if not isinstance(sql, str) or not sql.strip():
        raise SQLSafetyError("SQL query is empty.")

    query = sql.strip()

    # Reject SQL comments to reduce validation ambiguity.
    if "--" in query or "/*" in query or "*/" in query:
        raise SQLSafetyError("SQL comments are not allowed.")

    # Permit one optional trailing semicolon, but no multiple statements.
    without_trailing = query[:-1].rstrip() if query.endswith(";") else query
    if ";" in without_trailing:
        raise SQLSafetyError("Only one SQL statement is allowed.")

    if not re.match(r"(?is)^SELECT\b", without_trailing):
        raise SQLSafetyError("Only SELECT queries are allowed.")

    # Reject dangerous keywords, including those inside quoted text.
    # This intentionally conservative check may reject some valid queries.
    tokens = re.findall(r"[A-Za-z_]+", without_trailing.upper())
    blocked = FORBIDDEN_KEYWORDS.intersection(tokens)
    if blocked:
        raise SQLSafetyError(
            f"Disallowed SQL keyword(s): {', '.join(sorted(blocked))}"
        )

    return without_trailing


def execute_read_only_sql(sql: str) -> dict:
    """Execute validated SQL using a read-only DuckDB connection."""
    safe_sql = validate_sql(sql)
    connection = duckdb.connect(str(DB_PATH), read_only=True)

    try:
        # Fetch at most MAX_ROWS + 1 rows to detect truncation.
        limited_sql = (
            f"SELECT * FROM ({safe_sql}) AS limited_result "
            f"LIMIT {MAX_ROWS + 1}"
        )
        result = connection.execute(limited_sql).fetchdf()

        truncated = len(result) > MAX_ROWS
        result = result.head(MAX_ROWS)

        return {
            "sql": safe_sql,
            "columns": result.columns.tolist(),
            "rows": result.to_dict(orient="records"),
            "row_count": len(result),
            "truncated": truncated,
        }
    finally:
        connection.close()

if __name__ == "__main__":
    demo_sql = """
        SELECT Country, COUNT(*) AS transaction_rows
        FROM retail_transactions
        GROUP BY Country
        ORDER BY transaction_rows DESC
        LIMIT 10
    """

    output = execute_read_only_sql(demo_sql)
    print("SQL executed successfully:")
    print(output["sql"])
    print("\nTop 10 countries by transaction-row count:")
    for row in output["rows"]:
        print(row)
