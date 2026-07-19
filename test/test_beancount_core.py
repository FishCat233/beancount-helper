import pytest
from datetime import datetime

from src.beancount.core import (
    BeanCount,
    resolve_beancount,
    resolve_beancounts,
    dump_beancount,
    dump_beancounts,
)


# ---------- BeanCount 构造与序列化 ----------

def make_beancount(**kwargs) -> BeanCount:
    defaults = {
        "datetime": datetime(2025, 1, 15),
        "receiver": "商家A",
        "digest": "午餐消费",
        "in_account": "Expenses:Food",
        "out_account": "Assets:Cash",
        "amount": 50.0,
        "currency_type": "CNY",
    }
    defaults.update(kwargs)
    return BeanCount(**defaults)


def test_beancount_str():
    bc = make_beancount()
    expected = (
        '2025-01-15 * "商家A" "午餐消费"\n'
        "  Expenses:Food 50.0 CNY\n"
        "  Assets:Cash"
    )
    assert str(bc) == expected


def test_beancount_to_str():
    bc = make_beancount()
    assert bc.to_str() == str(bc)


def test_beancount_repr():
    bc = make_beancount()
    assert "BeanCount" in repr(bc)
    assert "2025-01-15" in repr(bc)
    assert "Expenses:Food->Assets:Cash(50.0)" in repr(bc)


def test_beancount_str_different_amount():
    bc = make_beancount(amount=123.45, currency_type="USD")
    s = str(bc)
    assert "123.45 USD" in s


# ---------- resolve_beancount ----------

VALID_BLOCK = """2025-01-15 * "商家A" "午餐消费"
  Expenses:Food 50.0 CNY
  Assets:Cash"""


def test_resolve_beancount_success():
    bc = resolve_beancount(VALID_BLOCK)
    assert bc.datetime == datetime(2025, 1, 15)
    assert bc.receiver == "商家A"
    assert bc.digest == "午餐消费"
    assert bc.in_account == "Expenses:Food"
    assert bc.out_account == "Assets:Cash"
    assert bc.amount == 50.0
    assert bc.currency_type == "CNY"


def test_resolve_beancount_too_few_lines():
    with pytest.raises(ValueError, match="must be 3 lines"):
        resolve_beancount("header only")


def test_resolve_beancount_bad_header():
    with pytest.raises(ValueError, match="Can't resolve beancount block"):
        resolve_beancount("bad header\n  Expenses:Food 50.0 CNY\n  Assets:Cash")


def test_resolve_beancount_missing_account_line():
    # 只有 2 行有效行
    block = '2025-01-15 * "A" "B"\n  OnlyOneLine'
    with pytest.raises(ValueError, match="must be 3 lines"):
        resolve_beancount(block)


# ---------- resolve_beancounts ----------

MULTI_BLOCK = """2025-01-15 * "商家A" "午餐"
  Expenses:Food 50.0 CNY
  Assets:Cash

2025-01-16 * "商家B" "交通"
  Expenses:Transport 30.0 CNY
  Assets:Cash"""


def test_resolve_beancounts_multiple():
    bcs = resolve_beancounts(MULTI_BLOCK)
    assert len(bcs) == 2
    assert bcs[0].datetime == datetime(2025, 1, 15)
    assert bcs[0].receiver == "商家A"
    assert bcs[1].datetime == datetime(2025, 1, 16)
    assert bcs[1].receiver == "商家B"


def test_resolve_beancounts_single():
    bcs = resolve_beancounts(VALID_BLOCK)
    assert len(bcs) == 1


def test_resolve_beancounts_with_trailing_blank():
    block = MULTI_BLOCK + "\n\n"
    bcs = resolve_beancounts(block)
    assert len(bcs) == 2


def test_resolve_beancounts_empty():
    bcs = resolve_beancounts("")
    assert bcs == []


# ---------- dump_beancount ----------

def test_dump_beancount():
    bc = make_beancount()
    result = dump_beancount(bc)
    assert str(bc) in result


def test_dump_beancounts():
    bc1 = make_beancount()
    bc2 = make_beancount(datetime=datetime(2025, 2, 1))
    result = dump_beancounts([bc1, bc2])
    assert "\n\n" in result
    assert "2025-01-15" in result
    assert "2025-02-01" in result


def test_dump_beancounts_empty_list():
    result = dump_beancounts([])
    assert result == ""


# ---------- round-trip ----------

def test_round_trip():
    bc = make_beancount()
    dumped = dump_beancount(bc)
    resolved = resolve_beancount(dumped)
    assert resolved.datetime == bc.datetime
    assert resolved.receiver == bc.receiver
    assert resolved.digest == bc.digest
    assert resolved.in_account == bc.in_account
    assert resolved.out_account == bc.out_account
    assert resolved.amount == bc.amount
    assert resolved.currency_type == bc.currency_type
