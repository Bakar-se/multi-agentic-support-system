"""
Greeter & Orchestrator Agent

Responsibilities:
- Greet the user
- Identify or request customer email
- Classify user intent
- Extract cancellation reason when applicable
- Output structured data for routing

Constraints:
- MUST NOT attempt retention or cancellation
- MUST NOT call update tools
- MUST output structured JSON for routing decisions
"""

import os
import re
from typing import Literal, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from state import ConversationState


# Structured output schema for intent classification
class IntentClassification(BaseModel):
    """Structured output for intent classification and routing."""
    
    customer_email: Optional[str] = Field(
        default=None,
        description="Customer email address if identified in the message, otherwise None"
    )
    
    intent: Literal["cancel_insurance", "technical_issue", "billing_question", "general_question"] = Field(
        description="Classified user intent"
    )
    
    cancellation_reason: Optional[str] = Field(
        default=None,
        description="Reason for cancellation if intent is cancel_insurance. "
                    "Values: 'financial_hardship', 'product_issues', 'service_value', or None"
    )
    
    greeting_message: str = Field(
        description="Friendly greeting message to send to the user"
    )
    
    needs_email: bool = Field(
        description="Whether the customer email still needs to be requested"
    )


def orchestrator_agent(state: ConversationState) -> ConversationState:
    """
    Greeter & Orchestrator Agent node.
    
    Greets the user, identifies/requests email, classifies intent,
    and extracts cancellation reason for routing decisions.
    
    Args:
        state: Current conversation state
        
    Returns:
        Updated conversation state with intent, email, and cancellation_reason
    """
    # Initialize Gemini 2.5 Flash
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set. Please set it before running.")
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=google_api_key,
        temperature=0.3,  # Lower temperature for more consistent classification
    )
    
    # Get user message
    user_message = state.get("user_message", "")
    
    # Get existing email if already identified
    existing_email = state.get("customer_email")
    
    # Build system prompt
    system_prompt = """You are a friendly customer support greeter and orchestrator for TechFlow Electronics Care+ insurance.

Your responsibilities:
1. Greet the customer warmly
2. Identify or request their email address
3. Classify their intent into one of these categories:
   - cancel_insurance: Customer wants to cancel their Care+ insurance
   - technical_issue: Customer has a technical problem with their device
   - billing_question: Customer has questions about billing, charges, or payments
   - general_question: General inquiries about services, policies, or other topics

4. If intent is cancel_insurance, extract the cancellation reason:
   - financial_hardship: Customer mentions cost, affordability, financial difficulties
   - product_issues: Customer mentions device problems, malfunctions, defects
   - service_value: Customer questions the value, hasn't used benefits, doesn't see the point

CRITICAL CONSTRAINTS:
- DO NOT attempt to retain the customer or offer solutions
- DO NOT process cancellations
- DO NOT call any update tools
- ONLY classify intent and extract information for routing
- Be friendly and professional
- If email is not provided, politely request it

Current conversation context:
- User message: {user_message}
- Existing email (if any): {existing_email}
"""

    # Format prompt with current state
    formatted_prompt = system_prompt.format(
        user_message=user_message,
        existing_email=existing_email if existing_email else "Not yet identified"
    )
    
    # Use structured output for reliable classification
    structured_llm = llm.with_structured_output(IntentClassification)
    
    # Get classification
    try:
        classification = structured_llm.invoke(formatted_prompt)
    except Exception as e:
        print(f"Error in orchestrator agent: {e}")
        # Fallback to basic classification
        classification = IntentClassification(
            customer_email=None,
            intent="general_question",
            cancellation_reason=None,
            greeting_message="Hello! How can I help you today?",
            needs_email=True
        )
    
    # Extract email from user message if not already identified
    email = classification.customer_email
    if not email and existing_email:
        email = existing_email
    elif not email:
        # Try to extract email from user message using regex
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(email_pattern, user_message)
        if matches:
            email = matches[0].lower()
    
    # Normalize cancellation reason
    cancellation_reason = classification.cancellation_reason
    if cancellation_reason:
        cancellation_reason = cancellation_reason.lower().strip()
        # Map to expected values
        if "financial" in cancellation_reason or "cost" in cancellation_reason or "afford" in cancellation_reason:
            cancellation_reason = "financial_hardship"
        elif "product" in cancellation_reason or "device" in cancellation_reason or "malfunction" in cancellation_reason:
            cancellation_reason = "product_issues"
        elif "value" in cancellation_reason or "benefit" in cancellation_reason or "point" in cancellation_reason:
            cancellation_reason = "service_value"
        else:
            # Default to service_value if unclear
            cancellation_reason = "service_value"
    
    # Build updated state
    updated_state: ConversationState = {
        "user_message": user_message,
        "customer_email": email if email else existing_email,
        "customer_data": state.get("customer_data"),  # Preserve existing
        "intent": classification.intent,
        "cancellation_reason": cancellation_reason if classification.intent == "cancel_insurance" else None,
        "retrieved_context": state.get("retrieved_context", []),  # Preserve existing
        "retention_offer": state.get("retention_offer"),  # Preserve existing
        "final_action": state.get("final_action"),  # Preserve existing
    }
    
    # Log classification for debugging
    print(f"\n[Orchestrator] Intent: {classification.intent}")
    print(f"[Orchestrator] Email: {updated_state['customer_email']}")
    if cancellation_reason:
        print(f"[Orchestrator] Cancellation reason: {cancellation_reason}")
    
    return updated_state

