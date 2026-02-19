"""
Billing Support Agent

Responsibilities:
- Handle billing question conversations
- Query policy documents using RAG for billing information
- Provide clear explanations about charges, plans, and billing policies
- Resolve billing discrepancies

Behavior Rules:
- MUST use RAG to retrieve relevant billing and policy information
- MUST provide clear, accurate billing information
- MUST NOT attempt retention or offer discounts
- MUST set appropriate final_action for routing
"""

import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from state import ConversationState
from rag.vectorstore import get_retriever
from tools.customer_tools import get_customer_data


def billing_agent(state: ConversationState) -> ConversationState:
    """
    Billing Support Agent node.
    
    Handles billing questions by:
    1. Retrieving customer data (if email available)
    2. Querying RAG for billing and policy context
    3. Providing clear billing explanations
    4. Setting appropriate final action
    
    Args:
        state: Current conversation state with intent and user_message
        
    Returns:
        Updated conversation state with customer_data, retrieved_context, and final_action
    """
    # Only handle billing question intents
    intent = state.get("intent")
    if intent != "billing_question":
        print(f"[Billing Agent] Skipping - intent is {intent}, not billing_question")
        return state
    
    # Get required state fields
    user_message = state.get("user_message", "")
    customer_email = state.get("customer_email")
    
    print(f"\n[Billing Agent] Processing billing question")
    if customer_email:
        print(f"[Billing Agent] Customer: {customer_email}")
    
    # Step 1: Retrieve customer data if email is available
    customer_data = None
    if customer_email:
        print("[Billing Agent] Retrieving customer data...")
        customer_data_result = get_customer_data.invoke({"email": customer_email})
        
        if "error" not in customer_data_result:
            customer_data = customer_data_result
            print(f"[Billing Agent] Customer: {customer_data.get('name')} - {customer_data.get('plan_type')}")
            print(f"[Billing Agent] Monthly Charge: ${customer_data.get('monthly_charge', 'N/A')}")
        else:
            print(f"[Billing Agent] Error retrieving customer data: {customer_data_result['error']}")
    
    # Step 2: Query RAG for relevant billing and policy context
    print("[Billing Agent] Querying RAG for billing and policy information...")
    retriever = get_retriever(k=4)  # Get top 4 relevant chunks for billing
    
    # Query with user message focused on billing
    query = f"billing charges payment plan cost: {user_message}"
    
    retrieved_docs = retriever.invoke(query)
    
    # Extract retrieved context snippets
    retrieved_context = []
    for doc in retrieved_docs:
        content = doc.page_content
        source = doc.metadata.get("source", "unknown")
        retrieved_context.append(f"[{source}] {content}")
        print(f"\n[Billing Agent] Retrieved from {source}:")
        print(f"  {content[:200]}...")  # Log first 200 chars
    
    # Step 3: Generate helpful billing response using Gemini
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set. Please set it before running.")
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=google_api_key,
        temperature=0.4,  # Lower temperature for accurate billing information
    )
    
    # Build context for the LLM
    customer_info = ""
    if customer_data:
        customer_info = f"""
Customer Information:
- Name: {customer_data.get('name', 'N/A')}
- Plan: {customer_data.get('plan_type', 'N/A')}
- Monthly Charge: ${customer_data.get('monthly_charge', 0)}
- Account Status: {customer_data.get('account_status', 'N/A')}
"""
    
    policy_context = "\n".join(retrieved_context) if retrieved_context else "No specific billing policy context retrieved."
    
    system_prompt = f"""You are a helpful billing support specialist for TechFlow Electronics Care+ insurance.

Your goal is to provide clear, accurate billing information and resolve billing questions.

CRITICAL RULES:
1. MUST use the policy and billing information provided below
2. Provide accurate information about charges, plans, and billing policies
3. If there's a discrepancy, explain what the customer should expect
4. Be clear and transparent about charges
5. If customer data is available, reference their specific plan and charges
6. DO NOT attempt to sell or retain customers - focus solely on billing questions
7. DO NOT offer discounts or retention offers
8. If the issue requires account investigation, suggest contacting billing department

Customer Billing Question:
- User Message: {user_message}
- Customer Email: {customer_email if customer_email else 'Not provided'}

{customer_info}

Relevant Billing and Policy Information:
{policy_context}

Generate a helpful billing support response that:
1. Acknowledges the customer's billing question
2. Provides clear information about charges, plans, or billing policies based on the context
3. If there's a discrepancy, explains what might have happened and what to expect
4. References the customer's specific plan information if available
5. Offers to help investigate further if needed

Keep the response clear, accurate, and focused on resolving the billing question.
"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message)
    ]
    
    try:
        response = llm.invoke(messages)
        agent_response = response.content
        print(f"\n[Billing Agent] Generated response:")
        print(f"  {agent_response[:300]}...")
    except Exception as e:
        print(f"[Billing Agent] Error generating response: {e}")
        agent_response = "I understand you have a billing question. Let me help clarify the charges and billing information for you."
    
    # Build updated state
    updated_state: ConversationState = {
        "user_message": user_message,
        "customer_email": customer_email,
        "customer_data": customer_data,  # Updated with retrieved data if available
        "intent": intent,
        "cancellation_reason": state.get("cancellation_reason"),  # Preserve existing
        "retrieved_context": retrieved_context,  # Updated with RAG results
        "retention_offer": state.get("retention_offer"),  # Preserve existing
        "final_action": "routed_to_billing",  # Mark as routed to billing support
    }
    
    return updated_state


