# rule: p=name:eq:哈基米;;lt=20.0;;direct=in=>Expenses::Life
from functools import lru_cache
import datetime
from typing import Callable, TypedDict


class Bill(TypedDict, total=False):
    is_balance_in: bool
    date: datetime.datetime
    amount: float
    currency_type: str
    opposite: str
    note: str
    product: str


operator_type = Callable[[Bill, str], bool]
_OPERATOR_MAPPING: dict[str, operator_type] = {}


@lru_cache(maxsize=128)
def _get_compile_re(pattern: str):
    import re

    return re.compile(pattern)


def _operator(name: str):
    def decorator(func: operator_type):
        _OPERATOR_MAPPING[name] = func
        return func

    return decorator


def match_rule(bill: Bill, rule: str) -> str | None:
    try:
        match_rule, target = rule.strip().rsplit("=>", 1)
        match_rule = match_rule.strip()
        target = target.strip()
        segments = match_rule.split(";;")
    except ValueError:
        raise ValueError(f"Can't resolve rule: {rule}")

    for seg in segments:
        if "=" not in seg:
            continue

        seg_type, rule_input = seg.split("=", 1)
        op = _OPERATOR_MAPPING.get(seg_type, None)
        if op is None:
            continue

        if not op(bill, rule_input):
            return None

    return target


@_operator("direct")
@_operator("direction")
def _direct_operator(bill: Bill, input: str) -> bool:
    is_balance_in = bill.get("is_balance_in", None)
    if is_balance_in is None:
        return False

    direct = "in" if is_balance_in else "out"
    return input == direct


@_operator("p")
@_operator("property")
def _property_operator(bill: Bill, input: str) -> bool:
    # name:eq:daisy
    property, method, string = input.split(":", 2)

    property = bill.get(property, None)
    if property is None:
        return False

    if method == "eq":
        return string == property
    elif method == "in":
        return string in property
    elif method == "re":
        pattern = _get_compile_re(string)

        if pattern.search(property):
            return True
        return False

    return False


def _make_comparision_operator(comparator_func: Callable[[float, float], bool]):
    # 高阶函数
    def op(bill: Bill, input: str):
        try:
            value = bill["amount"]  # type: ignore
            value = float(value)
            input_value: float = float(input)  # type: ignore
        except (KeyError, ValueError):
            return False

        return comparator_func(value, input_value)

    return op


_OPERATOR_MAPPING["lt"] = _make_comparision_operator(lambda x, y: x < y)
_OPERATOR_MAPPING["le"] = _make_comparision_operator(lambda x, y: x <= y)
_OPERATOR_MAPPING["gt"] = _make_comparision_operator(lambda x, y: x > y)
_OPERATOR_MAPPING["ge"] = _make_comparision_operator(lambda x, y: x >= y)
_OPERATOR_MAPPING["eq"] = _make_comparision_operator(lambda x, y: x == y)
