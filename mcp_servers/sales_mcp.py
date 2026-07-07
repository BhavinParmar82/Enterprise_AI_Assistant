from pathlib import Path
from typing import List

import pandas as pd
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field


# ==========================================================
# MCP Server
# ==========================================================

mcp = FastMCP("Sales")


# ==========================================================
# Load Data
# ==========================================================

DATA_DIR = Path(__file__).parent.parent / "data"

sales_df = pd.read_csv(DATA_DIR / "sales.csv")
customers_df = pd.read_csv(DATA_DIR / "customers.csv")
products_df = pd.read_csv(DATA_DIR / "products.csv")

sales_df["invoice_date"] = pd.to_datetime(sales_df["invoice_date"])


# ==========================================================
# Pydantic Models
# ==========================================================

class MonthlySalesRequest(BaseModel):
    month: str = Field(
        ...,
        description="Month in YYYY-MM format. Example: 2025-03"
    )


class MonthlySalesResponse(BaseModel):
    month: str
    total_revenue: float
    total_orders: int
    total_quantity: int
    average_order_value: float


class TopCustomersRequest(BaseModel):
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of top customers to return"
    )


class CustomerRevenue(BaseModel):
    customer_id: str
    company: str
    total_revenue: float


# ==========================================================
# MCP Tools
# ==========================================================

@mcp.tool(
    description="Return sales summary for a given month."
)
def get_sales_by_month(
    request: MonthlySalesRequest,
) -> MonthlySalesResponse:

    df = sales_df[
        sales_df["invoice_date"].dt.strftime("%Y-%m") == request.month
    ]

    if df.empty:
        return MonthlySalesResponse(
            month=request.month,
            total_revenue=0,
            total_orders=0,
            total_quantity=0,
            average_order_value=0,
        )

    return MonthlySalesResponse(
        month=request.month,
        total_revenue=float(df["amount"].sum()),
        total_orders=len(df),
        total_quantity=int(df["quantity"].sum()),
        average_order_value=float(df["amount"].mean()),
    )


@mcp.tool(
    description="Return customers ranked by total revenue."
)
def get_top_customers(
    request: TopCustomersRequest,
) -> List[CustomerRevenue]:

    customer_sales = (
        sales_df
        .groupby("customer_id")["amount"]
        .sum()
        .reset_index()
    )

    customer_sales = customer_sales.merge(
        customers_df,
        on="customer_id",
        how="left",
    )

    customer_sales = (
        customer_sales
        .sort_values("amount", ascending=False)
        .head(request.limit)
    )

    results = []

    for _, row in customer_sales.iterrows():
        results.append(
            CustomerRevenue(
                customer_id=row["customer_id"],
                company=row["company"],
                total_revenue=float(row["amount"]),
            )
        )

    return results


# ==========================================================
# Run Server
# ==========================================================

if __name__ == "__main__":
    mcp.run(transport="stdio")