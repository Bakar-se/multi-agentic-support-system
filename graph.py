"""
LangGraph workflow for multi-agent customer support system.

This module defines the LangGraph workflow that orchestrates agent routing and execution.
"""

from typing import Literal

from langgraph.graph import END, StateGraph

from agents.orchestrator import orchestrator_agent
from agents.processor import processor_agent
from agents.retention import retention_agent
from state import ConversationState


def route_after_orchestrator(state: ConversationState) -> Literal["retention_agent", "end"]:
    """
    Route after orchestrator agent based on classified intent.
    
    Args:
        state: Conversation state with intent classified by orchestrator
        
    Returns:
        Next node to execute: 'retention_agent' for cancellations, 'end' for others
    """
    intent = state.get("intent")
    
    if intent == "cancel_insurance":
        print("[Graph] Routing to retention_agent for cancellation handling")
        return "retention_agent"
    else:
        # For technical_issue, billing_question, general_question
        # End the conversation (could be extended with dedicated agents later)
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
    
    # Set entry point
    workflow.set_entry_point("orchestrator_agent")
    
    # Add conditional edges from orchestrator
    workflow.add_conditional_edges(
        "orchestrator_agent",
        route_after_orchestrator,
        {
            "retention_agent": "retention_agent",
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
    
    # Compile the graph
    app = workflow.compile()
    
    print("\n[Graph] LangGraph workflow compiled successfully")
    print("[Graph] Nodes: orchestrator_agent -> retention_agent -> processor_agent")
    print("[Graph] Routing: Based on intent and cancellation confirmation")
    
    return app


# Create the compiled graph instance
graph = build_graph()
