import pandas as pd
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Bill:
    is_balance_in: bool
    currency_type: str
    date: datetime
    amount: float
    note: str
    remaining_balance: float
    opposite: str
    raw_opposite: str
    raw_note: str


def resolve_from_excel(file_path: str) -> list[Bill]:
    # 读取的 excel 的时候跳过开头三行(标题信息).
    df = pd.read_excel(file_path, skiprows=3, keep_default_na=False)

    # 数据清洗
    df.dropna(how="all", inplace=True)
    df.reset_index(drop=True, inplace=True)

    bills = []
    for _, row in df.iterrows():
        # 尝试从交易附言里面解析出更多信息.
        raw_note = row.get("交易地点/附言", "Null")
        opposite, digest = _resolve_note(raw_note)

        bill = Bill(
            is_balance_in=_resolve_to_is_balance_in(row["摘要"]),
            currency_type=_resolve_to_standard_currency_type(row["币别"]),
            date=pd.to_datetime(row["交易日期"], format="%Y%m%d").to_pydatetime(),
            amount=abs(float(row.get("交易金额", 0.0).strip().replace(",", ""))),
            note=raw_note if digest == "" else digest,
            raw_note=raw_note,
            opposite=opposite,
            raw_opposite=row.get("对方账号与户名", "Null"),
            remaining_balance=row.get("账户余额", 0.0),
        )

        bills.append(bill)

    return bills


def _resolve_to_is_balance_in(string: str):
    return string not in ("消费")


def _resolve_to_standard_currency_type(string: str):
    _currency_dict = {"人民币元": "CNY"}

    return _currency_dict.get(string, "Null")


def _resolve_note(string: str) -> tuple[str, str]:
    # TODO: use DSL to do a transform on beancount bill would be more flexible than resolve at here. It might be remove in the future refactor work.
    if not isinstance(string, str):
        return "Null", ""
    try:
        app, digest = string.split("-", 1)

        if not app:
            return string, ""

        if app == "支付宝":
            opposite_type, opposite = digest.rsplit("-", 1)
            return opposite, f"{app}-{opposite_type}"

        if app == "抖音支付":
            opposite_type, opposite = digest.rsplit("-", 1)
            return opposite, f"{app}-{opposite_type}"
    except ValueError:
        pass
    finally:
        pass

    return string, ""
