"""
LangChain tools for customer data operations.

Implements the three required tools as specified in SRS:
1. get_customer_data - Load customer profile from CSV
2. calculate_retention_offer - Generate retention offers from rules
3. update_customer_status - Log customer status changes
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict

import pandas as pd
from langchain_core.tools import tool


# Get the project root directory (parent of tools/)
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CUSTOMERS_CSV = DATA_DIR / "customers.csv"
RETENTION_RULES_JSON = DATA_DIR / "retention_rules.json"
LOG_FILE = PROJECT_ROOT / "customer_status_log.txt"


@tool
def get_customer_data(email: str) -> dict:
    """Load customer profile from customers.csv
    
    Args:
        email: Customer email address to look up
        
    Returns:
        dict: Customer profile data including customer_id, name, plan_type, 
              tier, account_health_score, etc. Returns empty dict if not found.
    """
    try:
        if not CUSTOMERS_CSV.exists():
            return {"error": "Customer database not found"}
        
        df = pd.read_csv(CUSTOMERS_CSV)
        
        # Find customer by email (case-insensitive)
        customer = df[df["email"].str.lower() == email.lower()]
        
        if customer.empty:
            return {"error": f"Customer with email {email} not found"}
        
        # Convert to dict (first match)
        customer_dict = customer.iloc[0].to_dict()
        
        # Convert numeric types appropriately
        return {
            "customer_id": customer_dict.get("customer_id"),
            "email": customer_dict.get("email"),
            "phone": customer_dict.get("phone"),
            "name": customer_dict.get("name"),
            "plan_type": customer_dict.get("plan_type"),
            "monthly_charge": float(customer_dict.get("monthly_charge", 0)),
            "signup_date": customer_dict.get("signup_date"),
            "status": customer_dict.get("status"),
            "total_spent": float(customer_dict.get("total_spent", 0)),
            "support_tickets_count": int(customer_dict.get("support_tickets_count", 0)),
            "account_health_score": int(customer_dict.get("account_health_score", 0)),
            "tenure_months": int(customer_dict.get("tenure_months", 0)),
            "tier": customer_dict.get("tier"),
            "device": customer_dict.get("device"),
            "purchase_date": customer_dict.get("purchase_date"),
        }
    except Exception as e:
        return {"error": f"Error loading customer data: {str(e)}"}


@tool
def calculate_retention_offer(customer_tier: str, reason: str) -> dict:
    """Generate offers using retention_rules.json
    
    Args:
        customer_tier: Customer tier ('premium', 'regular', or 'new')
        reason: Cancellation reason ('financial_hardship', 'product_issues', 'service_value')
        
    Returns:
        dict: Retention offer details including type, cost, duration, description, etc.
              Returns empty dict if no matching offer found.
    """
    try:
        if not RETENTION_RULES_JSON.exists():
            return {"error": "Retention rules file not found"}
        
        with open(RETENTION_RULES_JSON, "r") as f:
            rules = json.load(f)
        
        # Map customer_tier to rules structure
        tier_mapping = {
            "premium": "premium_customers",
            "regular": "regular_customers",
            "new": "new_customers"
        }
        
        # Handle different reason structures
        if reason not in rules:
            return {"error": f"Unknown cancellation reason: {reason}"}
        
        reason_rules = rules[reason]
        
        # For financial_hardship, map tier directly
        if reason == "financial_hardship":
            tier_key = tier_mapping.get(customer_tier)
            if not tier_key or tier_key not in reason_rules:
                return {"error": f"No offers available for tier '{customer_tier}' and reason '{reason}'"}
            
            offers = reason_rules[tier_key]
            # Return first available offer
            if offers:
                return offers[0]
            return {"error": "No offers available"}
        
        # For product_issues, reason structure is different (overheating, battery_issues)
        # Return first available option
        elif reason == "product_issues":
            # Return first category's first offer (e.g., overheating)
            for category, offers in reason_rules.items():
                if offers:
                    return offers[0]
            return {"error": "No product issue offers available"}
        
        # For service_value, structure is plan-specific
        elif reason == "service_value":
            # Return first available offer (typically care_plus_premium)
            for plan_type, offers in reason_rules.items():
                if offers:
                    return offers[0]
            return {"error": "No service value offers available"}
        
        return {"error": f"Unable to generate offer for tier '{customer_tier}' and reason '{reason}'"}
        
    except Exception as e:
        return {"error": f"Error calculating retention offer: {str(e)}"}


@tool
def update_customer_status(customer_id: str, action: str) -> dict:
    """Process cancellations/changes and log to file
    
    Args:
        customer_id: Customer ID (e.g., 'CUST_001')
        action: Action taken (e.g., 'cancelled', 'retained', 'downgraded')
        
    Returns:
        dict: Confirmation with timestamp and logged action
    """
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] Customer: {customer_id} | Action: {action}\n"
        
        # Append to log file
        with open(LOG_FILE, "a") as f:
            f.write(log_entry)
        
        return {
            "status": "success",
            "customer_id": customer_id,
            "action": action,
            "timestamp": timestamp,
            "message": f"Customer status updated and logged successfully"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Error updating customer status: {str(e)}"
        }

