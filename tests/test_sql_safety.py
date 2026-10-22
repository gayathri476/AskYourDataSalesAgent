
from src.sql_agent import validate_sql, SQLSafetyError


def test_valid_select():
    validate_sql("SELECT COUNT(*) FROM retail_transactions")


def test_delete_rejected():
    try:
        validate_sql("DELETE FROM retail_transactions")
    except SQLSafetyError:
        return
    raise AssertionError("DELETE was not rejected")


def test_multiple_statements_rejected():
    try:
        validate_sql("SELECT 1; DROP TABLE retail_transactions")
    except SQLSafetyError:
        return
    raise AssertionError("Multiple statements were not rejected")


if __name__ == "__main__":
    test_valid_select()
    test_delete_rejected()
    test_multiple_statements_rejected()
    print("All 3 SQL safety tests passed!")
