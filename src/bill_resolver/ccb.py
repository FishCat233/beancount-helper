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


def resolve_from_excel(file_path: str) -> list[Bill]:
    # 读取的 excel 的时候跳过开头三行(标题信息).
    df = pd.read_excel(file_path, skiprows=3)

    # 数据清洗
    df.dropna(how="all", inplace=True)
    df.reset_index(drop=True, inplace=True)

    bills = []
    for _, row in df.iterrows():
        bill = Bill(
            is_balance_in=_resolve_to_is_balance_in(row["摘要"]),
            currency_type=_resolve_to_standard_currency_type(row["币别"]),
            date=pd.to_datetime(row["交易日期"]).to_pydatetime(),
            amount=row.get("交易金额", 0.0),
            note=row.get("交易地点/附言", ""),
            opposite=row.get("对方账户与户名", "Null"),
            remaining_balance=row.get("账户余额", 0.0),
        )

        bills.append(bill)

    return bills


def _resolve_to_is_balance_in(string: str):
    return string not in ("消费")


def _resolve_to_standard_currency_type(string: str):
    _currency_dict = {"人民币元": "CNY"}

    return _currency_dict.get(string, "Null")
