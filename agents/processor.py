"""
Processor Agent

Responsibilities:
- Process confirmed cancellations
- Update customer status using tools
- Log actions to a file
- Provide confirmation and timeline information
- Reference return/refund policies using RAG

Constraints:
- MUST NOT attempt persuasion
- MUST be procedural and concise
- MUST execute only after explicit user confirmation
- MUST update final_action in state
"""

import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from state import ConversationState
from rag.vectorstore import get_retriever
from tools.customer_tools import update_customer_status


def processor_agent(state: ConversationState) -> ConversationState:
    """
    Processor Agent node.
    
    Processes confirmed cancellations by:
    1. Verifying cancellation confirmation
    2. Updating customer status via tool
    3. Querying RAG for refund/return policy
    4. Providing procedural confirmation message
    
    Args:
        state: Current conversation state with confirmed cancellation
        
    Returns:
        Updated conversation state with final_action set to "cancelled"
    """
    # Check if cancellation is confirmed
    final_action = state.get("final_action")
    intent = state.get("intent")
    
    # Only process if intent is cancel_insurance and cancellation is confirmed
    if intent != "cancel_insurance":
        print(f"[Processor Agent] Skipping - intent is {intent}, not cancel_insurance")
        return state
    
    # Check for explicit confirmation or ready_to_cancel flag
    user_message = state.get("user_message", "").lower()
    confirmation_keywords = ["yes, cancel", "yes cancel", "proceed with cancellation", 
                            "confirm cancellation", "still want to cancel", 
                            "yes i want to cancel", "go ahead and cancel", "cancel it"]
    
    is_confirmed = final_action == "ready_to_cancel" or any(keyword in user_message for keyword in confirmation_keywords)
    
    if not is_confirmed:
        print("[Processor Agent] Cancellation not confirmed - waiting for explicit confirmation")
        return state
    
    print("\n[Processor Agent] Processing confirmed cancellation...")
    
    # Get required state fields
    customer_email = state.get("customer_email")
    customer_data = state.get("customer_data")
    
    if not customer_email:
        print("[Processor Agent] No customer email provided, cannot process cancellation")
        return state
    
    if not customer_data:
        print("[Processor Agent] No customer data available, cannot process cancellation")
        return state
    
    customer_id = customer_data.get("customer_id")
    if not customer_id:
        print("[Processor Agent] No customer_id found in customer data")
        return state
    
    # Step 1: Update customer status via tool
    print(f"[Processor Agent] Updating customer status for {customer_id}...")
    update_result = update_customer_status.invoke({
        "customer_id": customer_id,
        "action": "cancelled"
    })
    
    if "error" in update_result:
        print(f"[Processor Agent] Error updating status: {update_result['error']}")
        return state
    
    print(f"[Processor Agent] Status updated successfully: {update_result.get('timestamp', 'N/A')}")
    
    # Step 2: Query RAG for refund/return policy information
    print("[Processor Agent] Querying RAG for refund/return policy...")
    retriever = get_retriever(k=2)  # Get top 2 relevant chunks about refunds/returns
    
    # Query specifically for refund and return policy
    policy_query = "refund policy return policy cancellation refund processing time"
    retrieved_docs = retriever.invoke(policy_query)
    
    # Extract refund/return policy context
    refund_context = []
    for doc in retrieved_docs:
        content = doc.page_content
        source = doc.metadata.get("source", "unknown")
        # Only include if it's about refunds/returns
        if any(keyword in content.lower() for keyword in ["refund", "return", "cancel", "processing"]):
            refund_context.append(f"[{source}] {content}")
            print(f"\n[Processor Agent] Retrieved refund policy from {source}:")
            print(f"  {content[:200]}...")
    
    # Step 3: Generate concise, procedural confirmation message
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set. Please set it before running.")
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=google_api_key,
        temperature=0.2,  # Very low temperature for procedural, factual responses
    )
    
    customer_name = customer_data.get("name", "Customer")
    plan_type = customer_data.get("plan_type", "Care+ plan")
    
    refund_info = "\n".join(refund_context) if refund_context else "Standard refund processing applies."
    
    system_prompt = f"""You are a customer service processor for TechFlow Electronics.

Your role is to provide a concise, procedural confirmation message about the cancellation.

CRITICAL CONSTRAINTS:
- DO NOT attempt to persuade or retain the customer
- Be procedural, factual, and concise
- Provide clear next steps and timeline information
- Reference refund/return policy information when relevant
- Be professional and respectful

Customer Information:
- Name: {customer_name}
- Plan: {plan_type}
- Customer ID: {customer_id}

Refund/Return Policy Information:
{refund_info}

Generate a brief, procedural confirmation message that:
1. Confirms the cancellation has been processed
2. Provides the cancellation reference (customer ID)
3. Mentions refund/return policy details if applicable
4. States processing timeline (if available from policy)
5. Thanks them for being a customer

Keep it under 150 words. Be factual and procedural - no persuasion attempts.
"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Please provide the cancellation confirmation message.")
    ]
    
    try:
        response = llm.invoke(messages)
        confirmation_message = response.content
        print(f"\n[Processor Agent] Generated confirmation:")
        print(f"  {confirmation_message[:200]}...")
    except Exception as e:
        print(f"[Processor Agent] Error generating confirmation: {e}")
        # Fallback procedural message
        confirmation_message = f"""Your Care+ plan cancellation has been processed.

Cancellation Reference: {customer_id}
Status: Cancelled
Effective Date: End of current billing period

Refund processing will follow our standard policy. You will receive confirmation via email.

Thank you for being a TechFlow Electronics customer."""
    
    # Build updated state
    updated_state: ConversationState = {
        "user_message": state.get("user_message", ""),
        "customer_email": customer_email,
        "customer_data": customer_data,
        "intent": intent,
        "cancellation_reason": state.get("cancellation_reason"),
        "retrieved_context": refund_context,  # Updated with refund policy context
        "retention_offer": state.get("retention_offer"),  # Preserve existing
        "final_action": "cancelled",  # Updated to indicate completion
    }
    
    print(f"[Processor Agent] Cancellation processed. Final action: cancelled")
    
    return updated_state

