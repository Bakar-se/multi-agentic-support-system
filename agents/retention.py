"""
Retention & Problem-Solving Agent

Responsibilities:
- Handle cancellation-related conversations
- Retrieve customer data using tools
- Query policy documents using RAG
- Generate retention offers using business rules
- Communicate empathetically with the customer
- Decide whether to escalate to Processor

Behavior Rules:
- MUST attempt retention before cancellation
- MUST NOT offer discounts for technical or billing issues
- MUST explain Care+ value when applicable
- MUST escalate to Processor Agent only after explicit cancellation confirmation
"""

import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from state import ConversationState
from rag.vectorstore import get_retriever
from tools.customer_tools import calculate_retention_offer, get_customer_data


def retention_agent(state: ConversationState) -> ConversationState:
    """
    Retention & Problem-Solving Agent node.
    
    Handles cancellation requests by:
    1. Retrieving customer data
    2. Querying RAG for policy context
    3. Generating retention offers
    4. Communicating empathetically
    5. Deciding whether to escalate to Processor
    
    Args:
        state: Current conversation state with intent and customer_email
        
    Returns:
        Updated conversation state with customer_data, retrieved_context, and retention_offer
    """
    # Only handle cancellation-related intents
    intent = state.get("intent")
    if intent != "cancel_insurance":
        print(f"[Retention Agent] Skipping - intent is {intent}, not cancel_insurance")
        return state
    
    # Get required state fields
    user_message = state.get("user_message", "")
    customer_email = state.get("customer_email")
    cancellation_reason = state.get("cancellation_reason")
    
    if not customer_email:
        print("[Retention Agent] No customer email provided, cannot proceed")
        return state
    
    print(f"\n[Retention Agent] Processing cancellation request for {customer_email}")
    print(f"[Retention Agent] Cancellation reason: {cancellation_reason}")
    
    # Step 1: Retrieve customer data
    print("[Retention Agent] Retrieving customer data...")
    customer_data_result = get_customer_data.invoke({"email": customer_email})
    
    if "error" in customer_data_result:
        print(f"[Retention Agent] Error retrieving customer data: {customer_data_result['error']}")
        customer_data = None
        customer_tier = None
    else:
        customer_data = customer_data_result
        customer_tier = customer_data.get("tier")  # premium, regular, or new
        print(f"[Retention Agent] Customer tier: {customer_tier}")
        print(f"[Retention Agent] Customer: {customer_data.get('name')} - {customer_data.get('plan_type')}")
    
    # Step 2: Query RAG for relevant policy context
    print("[Retention Agent] Querying RAG for policy context...")
    retriever = get_retriever(k=3)  # Get top 3 relevant chunks
    
    # Query with user message and cancellation reason
    query = f"{user_message}"
    if cancellation_reason:
        query += f" Reason: {cancellation_reason}"
    
    retrieved_docs = retriever.invoke(query)
    
    # Extract retrieved context snippets
    retrieved_context = []
    for doc in retrieved_docs:
        content = doc.page_content
        source = doc.metadata.get("source", "unknown")
        retrieved_context.append(f"[{source}] {content}")
        print(f"\n[Retention Agent] Retrieved from {source}:")
        print(f"  {content[:200]}...")  # Log first 200 chars
    
    # Step 3: Generate retention offer using business rules
    retention_offer = None
    if customer_tier and cancellation_reason:
        print(f"[Retention Agent] Calculating retention offer for tier={customer_tier}, reason={cancellation_reason}...")
        offer_result = calculate_retention_offer.invoke({
            "customer_tier": customer_tier,
            "reason": cancellation_reason
        })
        
        if "error" not in offer_result:
            retention_offer = offer_result
            print(f"[Retention Agent] Generated offer: {retention_offer.get('type', 'unknown')}")
            print(f"[Retention Agent] Offer details: {retention_offer.get('description', 'N/A')}")
        else:
            print(f"[Retention Agent] Error calculating offer: {offer_result['error']}")
    
    # Step 4: Generate empathetic response using Gemini
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set. Please set it before running.")
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=google_api_key,
        temperature=0.7,  # Slightly higher for more empathetic, natural responses
    )
    
    # Build context for the LLM
    customer_info = ""
    if customer_data:
        customer_info = f"""
Customer Information:
- Name: {customer_data.get('name', 'N/A')}
- Plan: {customer_data.get('plan_type', 'N/A')}
- Monthly Charge: ${customer_data.get('monthly_charge', 0)}
- Account Health Score: {customer_data.get('account_health_score', 'N/A')}
- Tenure: {customer_data.get('tenure_months', 0)} months
- Tier: {customer_tier}
"""
    
    policy_context = "\n".join(retrieved_context) if retrieved_context else "No specific policy context retrieved."
    
    offer_info = ""
    if retention_offer:
        offer_info = f"""
Available Retention Offer:
- Type: {retention_offer.get('type', 'N/A')}
- Description: {retention_offer.get('description', 'N/A')}
- Cost: ${retention_offer.get('new_cost', retention_offer.get('cost', 'N/A'))}
- Duration: {retention_offer.get('duration_months', 'N/A')} months
- Authorization: {retention_offer.get('authorization', 'N/A')}
"""
    
    system_prompt = f"""You are an empathetic customer retention specialist for TechFlow Electronics Care+ insurance.

Your goal is to understand the customer's situation and attempt to retain them with appropriate solutions.

CRITICAL RULES:
1. MUST attempt retention before accepting cancellation
2. MUST NOT offer discounts for technical issues or billing questions (only for financial hardship or service value concerns)
3. MUST explain Care+ value when applicable
4. Be empathetic and understanding - acknowledge their concerns
5. Present ONE solution at a time (don't overwhelm)
6. Only escalate to cancellation processing if customer explicitly confirms they want to cancel after hearing your offer

Customer Situation:
- User Message: {user_message}
- Cancellation Reason: {cancellation_reason}

{customer_info}

Relevant Policy Information:
{policy_context}

{offer_info}

Generate a warm, empathetic response that:
1. Acknowledges their concern
2. Explains relevant Care+ benefits based on the policy context
3. Presents the retention offer (if available and appropriate)
4. Asks if they'd like to proceed with the offer or if they still want to cancel

Keep the response conversational and empathetic. Do NOT be pushy.
"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message)
    ]
    
    try:
        response = llm.invoke(messages)
        agent_response = response.content
        print(f"\n[Retention Agent] Generated response:")
        print(f"  {agent_response[:300]}...")
    except Exception as e:
        print(f"[Retention Agent] Error generating response: {e}")
        agent_response = "I understand you're considering canceling your Care+ plan. Let me help you explore options that might work better for your situation."
    
    # Step 5: Determine if we should escalate to Processor
    # Only escalate if customer explicitly confirms cancellation after retention attempt
    should_escalate = False
    confirmation_keywords = ["yes, cancel", "yes cancel", "proceed with cancellation", "confirm cancellation", 
                            "still want to cancel", "yes i want to cancel", "go ahead and cancel"]
    
    user_lower = user_message.lower()
    if any(keyword in user_lower for keyword in confirmation_keywords):
        should_escalate = True
        print("[Retention Agent] Customer explicitly confirmed cancellation - will escalate to Processor")
    
    # Build updated state
    updated_state: ConversationState = {
        "user_message": user_message,
        "customer_email": customer_email,
        "customer_data": customer_data,  # Updated with retrieved data
        "intent": intent,
        "cancellation_reason": cancellation_reason,
        "retrieved_context": retrieved_context,  # Updated with RAG results
        "retention_offer": retention_offer,  # Updated with calculated offer
        "final_action": "ready_to_cancel" if should_escalate else None,  # Signal for Processor
    }
    
    # Preserve existing fields if they exist
    if "final_action" in state and state["final_action"]:
        updated_state["final_action"] = state["final_action"]
    
    return updated_state

