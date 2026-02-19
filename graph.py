"""
LangGraph workflow for multi-agent customer support system.

This module defines the LangGraph workflow that orchestrates agent routing and execution.
"""

from typing import Literal

from langgraph.graph import END, StateGraph

from agents.billing import billing_agent
from agents.orchestrator import orchestrator_agent
from agents.processor import processor_agent
from agents.retention import retention_agent
from agents.tech_support import tech_support_agent
from state import ConversationState


def route_after_orchestrator(state: ConversationState) -> Literal["retention_agent", "tech_support_agent", "billing_agent", "end"]:
    """
    Route after orchestrator agent based on classified intent.
    
    Args:
        state: Conversation state with intent classified by orchestrator
        
    Returns:
        Next node to execute based on intent:
        - 'retention_agent' for cancellations
        - 'tech_support_agent' for technical issues
        - 'billing_agent' for billing questions
        - 'end' for general questions
    """
    intent = state.get("intent")
    
    if intent == "cancel_insurance":
        print("[Graph] Routing to retention_agent for cancellation handling")
        return "retention_agent"
    elif intent == "technical_issue":
        print("[Graph] Routing to tech_support_agent for technical support")
        return "tech_support_agent"
    elif intent == "billing_question":
        print("[Graph] Routing to billing_agent for billing support")
        return "billing_agent"
    else:
        # For general_question or unknown intents
        print(f"[Graph] Intent '{intent}' - ending conversation")
        return "end"


def route_after_retention(state: ConversationState) -> Literal["processor_agent", "end"]:
    """
    Route after retention agent based on cancellation confirmation.
    
    Args:
        state: Conversation state with retention attempt completed
        
    Returns:
        Next node to execute: 'processor_agent' if confirmed, 'end' if waiting
    """
    final_action = state.get("final_action")
    
    if final_action == "ready_to_cancel":
        print("[Graph] Cancellation confirmed - routing to processor_agent")
        return "processor_agent"
    else:
        # Waiting for user response or retention successful
        print("[Graph] Waiting for user response or retention in progress - ending")
        return "end"


def route_after_processor(state: ConversationState) -> Literal["end"]:
    """
    Route after processor agent - always ends.
    
    Args:
        state: Conversation state with cancellation processed
        
    Returns:
        Always 'end' - processor is the final step
    """
    print("[Graph] Cancellation processed - ending conversation")
    return "end"


def build_graph():
    """
    Build and configure the LangGraph workflow.
    
    Creates a StateGraph with:
    - orchestrator_agent node (entry point)
    - retention_agent node (cancellation handling)
    - processor_agent node (cancellation processing)
    - Conditional routing based on intent and confirmation
    
    Returns:
        Compiled StateGraph ready for execution
    """
    # Create StateGraph with ConversationState schema
    workflow = StateGraph(ConversationState)
    
    # Add nodes
    workflow.add_node("orchestrator_agent", orchestrator_agent)
    workflow.add_node("retention_agent", retention_agent)
    workflow.add_node("processor_agent", processor_agent)
    workflow.add_node("tech_support_agent", tech_support_agent)
    workflow.add_node("billing_agent", billing_agent)
    
    # Set entry point
    workflow.set_entry_point("orchestrator_agent")
    
    # Add conditional edges from orchestrator
    workflow.add_conditional_edges(
        "orchestrator_agent",
        route_after_orchestrator,
        {
            "retention_agent": "retention_agent",
            "tech_support_agent": "tech_support_agent",
            "billing_agent": "billing_agent",
            "end": END
        }
    )
    
    # Add conditional edges from retention
    workflow.add_conditional_edges(
        "retention_agent",
        route_after_retention,
        {
            "processor_agent": "processor_agent",
            "end": END
        }
    )
    
    # Add edge from processor (always ends)
    workflow.add_edge("processor_agent", END)
    
    # Add edges from tech_support_agent (always ends)
    workflow.add_edge("tech_support_agent", END)
    
    # Add edges from billing_agent (always ends)
    workflow.add_edge("billing_agent", END)
    
    # Compile the graph
    app = workflow.compile()
    
    print("\n[Graph] LangGraph workflow compiled successfully")
    print("[Graph] Nodes: orchestrator_agent -> [retention_agent -> processor_agent | tech_support_agent | billing_agent]")
    print("[Graph] Routing: Based on intent and cancellation confirmation")
    
    return app


# Create the compiled graph instance
graph = build_graph()
