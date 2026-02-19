"""
Technical Support Agent

Responsibilities:
- Handle technical issue conversations
- Query troubleshooting guide using RAG
- Provide step-by-step technical support
- Escalate complex issues when needed

Behavior Rules:
- MUST use RAG to retrieve relevant troubleshooting information
- MUST provide clear, actionable technical guidance
- MUST NOT attempt retention or offer discounts
- MUST set appropriate final_action for routing
"""

import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from state import ConversationState
from rag.vectorstore import get_retriever


def tech_support_agent(state: ConversationState) -> ConversationState:
    """
    Technical Support Agent node.
    
    Handles technical issues by:
    1. Querying RAG for troubleshooting guide context
    2. Providing step-by-step technical guidance
    3. Setting appropriate final action
    
    Args:
        state: Current conversation state with intent and user_message
        
    Returns:
        Updated conversation state with retrieved_context and final_action
    """
    # Only handle technical issue intents
    intent = state.get("intent")
    if intent != "technical_issue":
        print(f"[Tech Support Agent] Skipping - intent is {intent}, not technical_issue")
        return state
    
    # Get required state fields
    user_message = state.get("user_message", "")
    customer_email = state.get("customer_email")
    
    print(f"\n[Tech Support Agent] Processing technical issue")
    if customer_email:
        print(f"[Tech Support Agent] Customer: {customer_email}")
    
    # Step 1: Query RAG for relevant troubleshooting context
    print("[Tech Support Agent] Querying RAG for troubleshooting guide...")
    retriever = get_retriever(k=4)  # Get top 4 relevant chunks for technical support
    
    # Query with user message focused on technical issue
    query = f"technical issue troubleshooting: {user_message}"
    
    retrieved_docs = retriever.invoke(query)
    
    # Extract retrieved context snippets
    retrieved_context = []
    for doc in retrieved_docs:
        content = doc.page_content
        source = doc.metadata.get("source", "unknown")
        retrieved_context.append(f"[{source}] {content}")
        print(f"\n[Tech Support Agent] Retrieved from {source}:")
        print(f"  {content[:200]}...")  # Log first 200 chars
    
    # Step 2: Generate helpful technical support response using Gemini
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set. Please set it before running.")
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=google_api_key,
        temperature=0.5,  # Balanced temperature for clear technical guidance
    )
    
    # Build context for the LLM
    troubleshooting_context = "\n".join(retrieved_context) if retrieved_context else "No specific troubleshooting context retrieved."
    
    system_prompt = f"""You are a helpful technical support specialist for TechFlow Electronics.

Your goal is to provide clear, step-by-step technical support to help customers resolve their device issues.

CRITICAL RULES:
1. MUST use the troubleshooting guide information provided below
2. Provide step-by-step instructions in a clear, easy-to-follow manner
3. Start with the most common solutions first
4. Be patient and encouraging
5. If the issue requires advanced diagnostics or hardware replacement, suggest escalation
6. DO NOT attempt to sell or retain customers - focus solely on technical support
7. DO NOT offer discounts or retention offers

Customer Issue:
- User Message: {user_message}
- Customer Email: {customer_email if customer_email else 'Not provided'}

Relevant Troubleshooting Information:
{troubleshooting_context}

Generate a helpful technical support response that:
1. Acknowledges the customer's technical issue
2. Provides step-by-step troubleshooting instructions based on the guide
3. Explains what each step does and why it helps
4. Asks the customer to try the steps and report back
5. Mentions escalation options if the issue persists after troubleshooting

Keep the response clear, friendly, and focused on solving the technical problem.
"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message)
    ]
    
    try:
        response = llm.invoke(messages)
        agent_response = response.content
        print(f"\n[Tech Support Agent] Generated response:")
        print(f"  {agent_response[:300]}...")
    except Exception as e:
        print(f"[Tech Support Agent] Error generating response: {e}")
        agent_response = "I understand you're experiencing a technical issue. Let me help you troubleshoot this step by step."
    
    # Build updated state
    updated_state: ConversationState = {
        "user_message": user_message,
        "customer_email": customer_email,
        "customer_data": state.get("customer_data"),  # Preserve existing
        "intent": intent,
        "cancellation_reason": state.get("cancellation_reason"),  # Preserve existing
        "retrieved_context": retrieved_context,  # Updated with RAG results
        "retention_offer": state.get("retention_offer"),  # Preserve existing
        "final_action": "routed_to_support",  # Mark as routed to technical support
    }
    
    return updated_state


