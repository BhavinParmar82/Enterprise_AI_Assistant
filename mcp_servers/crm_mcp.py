import pandas as pd
from pathlib import Path
from typing import List
from datetime import datetime

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

# ==========================================================
# MCP Server    
# ==========================================================

mcp = FastMCP("CRM")

# ==========================================================
# Load Data
# ==========================================================

DATA_DIR = Path(__file__).parent.parent / "data"

customers_df = pd.read_csv(DATA_DIR / "customers.csv")
crm_opportunities_df = pd.read_json(DATA_DIR / "crm_opportunities.json", orient="records")

#=========================================================
# Pydantic Models
#=========================================================
class CustomerProfile(BaseModel):
    customer_id: str
    name: str
    company: str
    email: str

class Opportunity(BaseModel):
    opportunity_id: str
    customer_id: str
    value: float
    stage: str
    followup_date: datetime

#=========================================================
# Tools
#=========================================================  
@mcp.tool(description="Get the profile of a customer by their ID.")
def get_customer_profile(customer_id: str) -> CustomerProfile:
    """
    Get the profile of a customer by their ID.
    """
    customer = customers_df[customers_df["customer_id"] == customer_id]
    if customer.empty:
        raise ValueError("Customer not found")
    return CustomerProfile(**customer.to_dict(orient="records")[0])


@mcp.tool(description="Get all open opportunities for a given customer ID.")
def get_open_opportunities(customer_id: str) -> List[Opportunity]:
    """
    Get all open opportunities for a given customer ID.
    """
    opportunities = crm_opportunities_df[
        (crm_opportunities_df["customer_id"] == customer_id) &
        (crm_opportunities_df["stage"] != "Won")
    ]
    return [Opportunity(**opportunity) for opportunity in opportunities.to_dict(orient="records")]

@mcp.tool(description="Get a summary of the sales pipeline.")
def get_pipeline_summary() -> dict:
    """
    Get a summary of the sales pipeline.
    """
    total_opportunities = len(crm_opportunities_df)
    open_opportunities = len(crm_opportunities_df[crm_opportunities_df["stage"] != "Won"])
    closed_opportunities = len(crm_opportunities_df[crm_opportunities_df["stage"] == "Won"])
    
    return {
        "total_opportunities": total_opportunities,
        "open_opportunities": open_opportunities,
        "closed_opportunities": closed_opportunities
    }

@mcp.tool(description="Get all opportunities with a value greater than the specified threshold.")
def get_high_value_opportunities(threshold: float = 100000.0) -> List[dict]:
    """
    Get all opportunities with a value greater than the specified threshold.
    """
    high_value_opportunities = crm_opportunities_df[crm_opportunities_df["value"] > threshold]
    return high_value_opportunities.to_dict(orient="records")

@mcp.tool(description="Get all upcoming follow-ups for a given customer ID.")
def get_upcoming_followups(customer_id: str) -> List[dict]:
    """
    Get all upcoming follow-ups for a given customer ID.
    """
    followups = crm_opportunities_df[
        (crm_opportunities_df["customer_id"] == customer_id) &
        (crm_opportunities_df["followup_date"] >= pd.Timestamp.now())
    ]
    return followups.to_dict(orient="records")

@mcp.tool(description="Search for customers by name or company.")
def search_customers(query: str) -> List[dict]:
    """
    Search for customers by name or company.
    """
    results = customers_df[
        customers_df["name"].str.contains(query, case=False, na=False) |
        customers_df["company"].str.contains(query, case=False, na=False)
    ]
    return results.to_dict(orient="records")


# ==========================================================
# Run Server
# ==========================================================

if __name__ == "__main__":
    mcp.run(transport="stdio")