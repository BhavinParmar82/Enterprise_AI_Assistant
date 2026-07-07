from pathlib import Path
import pandas as pd
from pydantic import BaseModel, Field

from mcp.server.fastmcp import FastMCP
from typing import List

#=========================================================
# MCP Server    
#=========================================================

mcp = FastMCP("Finance")
# Finance → Budgets, invoices, payments, profitability

#=========================================================
# Load Data 
#=========================================================  
DATA_DIR = Path(__file__).parent.parent / "data"

sales_df = pd.read_csv(DATA_DIR / "sales.csv")
customers_df = pd.read_csv(DATA_DIR / "customers.csv")
sales_targets_df = pd.read_excel(DATA_DIR / "sales_targets.xlsx")

#=========================================================
# Tools
#=========================================================

@mcp.tool(description="Get the financial summary for a given month.")
def get_financial_summary(month: str) -> dict:
    """
    Get the financial summary for a given month.
    """
    sales_df["invoice_date"] = pd.to_datetime(sales_df["invoice_date"])
    month_start = pd.to_datetime(month + "-01")
    month_end = month_start + pd.offsets.MonthEnd(1)
    
    monthly_sales = sales_df[
        (sales_df["invoice_date"] >= month_start) & 
        (sales_df["invoice_date"] <= month_end)
    ]
    
    total_revenue = monthly_sales["amount"].sum()
    total_orders = monthly_sales.shape[0]
    total_quantity = monthly_sales["quantity"].sum()
    average_order_value = total_revenue / total_orders if total_orders > 0 else 0
    
    return {
        "month": month,
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "total_quantity": total_quantity,
        "average_order_value": average_order_value
    }
    
@mcp.tool(description="Get the monthly revenue for a given month.")
def get_monthly_revenue(month: str) -> float:
    """
    Get the monthly revenue for a given month.
    """
    sales_df["invoice_date"] = pd.to_datetime(sales_df["invoice_date"])
    month_start = pd.to_datetime(month + "-01")
    month_end = month_start + pd.offsets.MonthEnd(1)
    
    monthly_sales = sales_df[
        (sales_df["invoice_date"] >= month_start) & 
        (sales_df["invoice_date"] <= month_end)
    ]
    
    return monthly_sales["amount"].sum()

@mcp.tool(description="Get the target vs actual sales for a given month.")
def get_target_vs_actual(month: str) -> dict:
    """
    Get the target vs actual sales for a given month.
    """
    target_row = sales_targets_df[sales_targets_df["month"] == month]
    if target_row.empty:
        raise ValueError("Sales target for the given month not found")
    
    target_sales = target_row["target_sales"].values[0]
    actual_sales = get_monthly_revenue(month)
    
    return {
        "month": month,
        "target_sales": target_sales,
        "actual_sales": actual_sales
    }
    
@mcp.tool(description="Get the sales target for a given month.")
def get_sales_target(month: str) -> float:
    """
    Get the sales target for a given month.
    """
    target_row = sales_targets_df[sales_targets_df["month"] == month]
    if target_row.empty:
        raise ValueError("Sales target for the given month not found")
    
    return target_row["target_sales"].values[0]

@mcp.tool(description="Get the target achievement percentage for a given month.")
def get_target_achievement(month: str) -> float:    
    """
    Get the target achievement percentage for a given month.
    """
    target_row = sales_targets_df[sales_targets_df["month"] == month]
    if target_row.empty:
        raise ValueError("Sales target for the given month not found")
    
    target_sales = target_row["target_sales"].values[0]
    actual_sales = get_monthly_revenue(month)
    
    if target_sales == 0:
        return 0.0
    
    return (actual_sales / target_sales) * 100

@mcp.tool(description="Get the top N customers by revenue for a given month.")
def get_top_customers(month: str, top_n: int = 5) -> List[dict]:
    """
    Get the top N customers by revenue for a given month.
    """
    sales_df["invoice_date"] = pd.to_datetime(sales_df["invoice_date"])
    month_start = pd.to_datetime(month + "-01")
    month_end = month_start + pd.offsets.MonthEnd(1)
    
    monthly_sales = sales_df[
        (sales_df["invoice_date"] >= month_start) & 
        (sales_df["invoice_date"] <= month_end)
    ]
    
    customer_revenue = monthly_sales.groupby("customer_id")["amount"].sum().reset_index()
    top_customers = customer_revenue.nlargest(top_n, "amount")
    
    results = top_customers.merge(customers_df, on="customer_id", how="left")[
        ["customer_id", "company", "amount"]
    ]
    
    return results.to_dict(orient="records")

@mcp.tool(description="Get the revenue variance for a given month.")
def get_revenue_variance(month: str) -> dict:   
    """
    Get the revenue variance for a given month.
    """
    target_row = sales_targets_df[sales_targets_df["month"] == month]
    if target_row.empty:
        raise ValueError("Sales target for the given month not found")
    
    target_sales = target_row["target_sales"].values[0]
    actual_sales = get_monthly_revenue(month)
    
    variance = actual_sales - target_sales
    
    return {
        "month": month,
        "target_sales": target_sales,
        "actual_sales": actual_sales,
        "variance": variance
    }       
    
@mcp.tool(description="Get the top N revenue-generating customers for a given month.")
def get_top_revenue_customers(month: str, top_n: int = 5) -> List[dict]:
    """
    Get the top N revenue-generating customers for a given month.
    """
    sales_df["invoice_date"] = pd.to_datetime(sales_df["invoice_date"])
    month_start = pd.to_datetime(month + "-01")
    month_end = month_start + pd.offsets.MonthEnd(1)
    
    monthly_sales = sales_df[
        (sales_df["invoice_date"] >= month_start) & 
        (sales_df["invoice_date"] <= month_end)
    ]
    
    customer_revenue = monthly_sales.groupby("customer_id")["amount"].sum().reset_index()
    top_customers = customer_revenue.nlargest(top_n, "amount")
    
    results = top_customers.merge(customers_df, on="customer_id", how="left")[
        ["customer_id", "company", "amount"]
    ]
    
    return results.to_dict(orient="records")    

@mcp.tool(description="Get the revenue variance for a given month.")
def get_revenue_variance(month: str) -> dict:   
    """
    Get the revenue variance for a given month.
    """
    target_row = sales_targets_df[sales_targets_df["month"] == month]
    if target_row.empty:
        raise ValueError("Sales target for the given month not found")
    
    target_sales = target_row["target_sales"].values[0]
    actual_sales = get_monthly_revenue(month)
    
    variance = actual_sales - target_sales
    
    return {
        "month": month,
        "target_sales": target_sales,
        "actual_sales": actual_sales,
        "variance": variance
    }   
    
@mcp.tool(description="Get the top N revenue-generating customers for a given month.")
def get_top_revenue_customers(month: str, top_n: int = 5)   -> List[dict]:
    """
    Get the top N revenue-generating customers for a given month.
    """
    sales_df["invoice_date"] = pd.to_datetime(sales_df["invoice_date"])
    month_start = pd.to_datetime(month + "-01")
    month_end = month_start + pd.offsets.MonthEnd(1)
    
    monthly_sales = sales_df[
        (sales_df["invoice_date"] >= month_start) & 
        (sales_df["invoice_date"] <= month_end)
    ]
    
    customer_revenue = monthly_sales.groupby("customer_id")["amount"].sum().reset_index()
    top_customers = customer_revenue.nlargest(top_n, "amount")
    
    results = top_customers.merge(customers_df, on="customer_id", how="left")[
        ["customer_id", "company", "amount"]
    ]
    
    return results.to_dict(orient="records")    

@mcp.tool(description="Get the revenue variance for a given month.")
def get_revenue_variance(month: str) -> dict:
    """
    Get the revenue variance for a given month.
    """
    target_row = sales_targets_df[sales_targets_df["month"] == month]
    if target_row.empty:
        raise ValueError("Sales target for the given month not found")
    
    target_sales = target_row["target_sales"].values[0]
    actual_sales = get_monthly_revenue(month)
    
    variance = actual_sales - target_sales
    
    return {
        "month": month,
        "target_sales": target_sales,
        "actual_sales": actual_sales,
        "variance": variance
    }
    
if __name__ == "__main__":
    mcp.run(transport="stdio")