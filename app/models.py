from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any


def money(value: float | int | None) -> float:
    if value is None:
        return 0.0
    return round(float(value), 2)


def format_money(value: float | int | None) -> str:
    return f"${money(value):,.2f}"


def format_date(value: date | datetime | None) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        value = value.date()
    return value.strftime("%m/%d/%Y")


def possessive(name: str) -> str:
    name = (name or "").strip()
    if not name:
        return ""
    if name.lower().endswith("s"):
        return f"{name}'"
    return f"{name}'s"


@dataclass
class Transaction:
    today: date | None = None
    close_date: date | None = None
    is_sale: bool = True
    property_address: str = ""
    sale_price: float = 0.0
    mls: str = ""
    seller: str = ""
    buyer: str = ""
    listing_broker: str = ""
    listing_broker_phone: str = ""
    listing_agent: str = ""
    listing_agent_phone: str = ""
    listing_agent_email: str = ""
    selling_broker: str = ""
    selling_broker_phone: str = ""
    selling_broker_address: str = ""
    selling_agent: str = ""
    selling_agent_phone: str = ""
    selling_agent_email: str = ""
    title_company: str = ""
    closer: str = ""
    closer_email: str = ""
    closer_phone: str = ""
    escrow_no: str = ""
    broker_process_fees: float = 0.0
    broker_other_fees: float = 0.0
    selling_agent_commission: float = 0.0
    listing_agent_commission: float = 0.0
    agent_contribution: float = 0.0
    other_fees: float = 0.0
    total_commission: float = 0.0
    agent_payee_address: str = ""
    broker_name: str = ""
    brokerage_name: str = ""
    brokerage_mail_address: str = ""
    brokerage_email: str = ""
    brokerage_phone: str = ""
    warnings: list[str] = field(default_factory=list)

    @property
    def gross_commission(self) -> float:
        if self.total_commission:
            return money(self.total_commission)
        return money(
            self.broker_process_fees
            + self.broker_other_fees
            + self.selling_agent_commission
            + self.listing_agent_commission
            + self.agent_contribution
            + self.other_fees
        )

    @property
    def net_due_brokerage(self) -> float:
        return money(self.broker_process_fees + self.broker_other_fees + self.other_fees)

    @property
    def net_due_agent(self) -> float:
        return money(self.selling_agent_commission)

    def to_preview(self) -> dict[str, Any]:
        data = asdict(self)
        data["today"] = format_date(self.today)
        data["close_date"] = format_date(self.close_date)
        data["sale_price_fmt"] = format_money(self.sale_price)
        data["gross_commission"] = self.gross_commission
        data["gross_commission_fmt"] = format_money(self.gross_commission)
        data["broker_process_fees_fmt"] = format_money(self.broker_process_fees)
        data["selling_agent_commission_fmt"] = format_money(self.selling_agent_commission)
        data["net_due_brokerage"] = self.net_due_brokerage
        data["net_due_brokerage_fmt"] = format_money(self.net_due_brokerage)
        data["net_due_agent"] = self.net_due_agent
        data["net_due_agent_fmt"] = format_money(self.net_due_agent)
        data["suggested_filename"] = self.suggested_filename()
        return data

    def suggested_filename(self) -> str:
        addr = self.property_address or "transaction"
        slug = addr.replace("/", "-").replace("\\", "-")
        return f"CDA_{slug}.pdf"
