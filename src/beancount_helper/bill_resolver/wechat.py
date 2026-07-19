import pandas as pd
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Bill:
    payment_method: str
    payment_tracking_number: str
    merchant_tracking_number: str
    bill_type: str
    note: str
    opposite: str
    product: str

    is_balance_in: bool
    date: datetime
    amount: float
    currency_type: str = "CNY"


def resolve_from_excel(file_path: str) -> list[Bill]:
    # 读取的 excel 的时候跳过开头三行(标题信息).
    df = pd.read_excel(file_path, engine="openpyxl", skiprows=17)

    # 数据清洗
    df.dropna(how="all", inplace=True)
    df.reset_index(drop=True, inplace=True)

    bills = []
    for _, row in df.iterrows():
        bill = Bill(
            date=pd.to_datetime(row["交易时间"]).to_pydatetime(),
            bill_type=row.get("交易类型", ""),
            opposite=row.get("交易对方", ""),
            product=row.get("商品", ""),
            is_balance_in=_resolve_to_is_balance_in(row["收/支"]),
            amount=row["金额(元)"],
            payment_method=row.get("支付方式", ""),
            payment_tracking_number=row.get("交易单号", ""),
            merchant_tracking_number=row.get("商家单号", ""),
            note=row.get("备注", ""),
        )

        bills.append(bill)

    return bills


def _resolve_to_is_balance_in(string: str):
    return string == "收入"
