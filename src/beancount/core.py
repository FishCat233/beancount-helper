import re
from datetime import datetime

_HEADER_PATTERN = re.compile(r'^(\d{4}-\d{2}-\d{2}) \* "(.*?)" "(.*?)"$')


def resolve_beancounts(string: str) -> list["BeanCount"]:
    # 去除空行
    string = "\n".join([line.rstrip() for line in string.split("\n")])

    blocks = [b.strip() for b in string.strip().split("\n\n") if b.strip()]
    results: list["BeanCount"] = []

    for block in blocks:
        results.append(resolve_beancount(block))

    return results


def resolve_beancount(string: str) -> "BeanCount":
    lines = [line.strip() for line in string.split("\n") if line.strip()]
    if len(lines) < 3:
        raise ValueError(
            f"Beancount transaction block must be 3 lines for resolving, but {len(lines)} lines got from: {string}"
        )

    # resolve header
    match = _HEADER_PATTERN.match(lines[0])
    if not match:
        raise ValueError(f"Can't resolve beancount block: {string}")

    date, receiver, digest = match.groups()
    date = datetime.strptime(date, "%Y-%m-%d")

    # resolve information
    in_account, amount, currency_type = lines[1].split(" ")
    out_account = lines[2]

    return BeanCount(
        datetime=date,
        receiver=receiver,
        digest=digest,
        in_account=in_account,
        out_account=out_account,
        amount=float(amount),
        currency_type=currency_type,
    )


def dump_beancount(beancount: "BeanCount") -> str:
    return beancount.to_str()


def dump_beancounts(beancounts: list["BeanCount"]) -> str:
    return "\n\n".join([b.to_str() for b in beancounts])


class BeanCount:
    def __init__(
        self,
        datetime: datetime,
        receiver: str,
        digest: str,
        in_account: str,
        out_account: str,
        amount: float,
        currency_type: str,
    ):
        self.datetime = datetime
        self.receiver = receiver
        self.digest = digest
        self.in_account = in_account
        self.out_account = out_account
        self.amount = amount
        self.currency_type = currency_type

    def __str__(self) -> str:
        date_str = self.datetime.strftime("%Y-%m-%d")
        return (
            f'{date_str} * "{self.receiver}" "{self.digest}"\n'
            f"  {self.in_account} {self.amount} {self.currency_type}\n"
            f"  {self.out_account}"
        )

    def __repr__(self) -> str:
        return f'BeanCount(date={self.datetime.strftime("%Y-%m-%d")}, {self.in_account}->{self.out_account}({self.amount}), receiver: {self.receiver}({self.digest}))'

    to_str = __str__
