# LangChain Architecture Explanation

This document explains the LangChain architecture used in the multi-agent customer support system, including how LangGraph orchestrates agent workflows, how tools are integrated, and how RAG enhances agent capabilities.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [LangGraph Workflow](#langgraph-workflow)
3. [Agent Implementation](#agent-implementation)
4. [Tool Integration](#tool-integration)
5. [RAG Integration](#rag-integration)
6. [State Management](#state-management)
7. [LLM Configuration](#llm-configuration)

---

## Architecture Overview

The system uses a **multi-agent architecture** orchestrated by **LangGraph**, where specialized agents handle different aspects of customer interactions.

```
┌─────────────────────────────────────────────────────────┐
│                    LangGraph Workflow                   │
│                                                         │
│  Orchestrator → [Retention | Tech Support | Billing]   │
│                      ↓                                   │
│                   Processor                              │
└─────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
    LangChain Tools      RAG System          LLM (Gemini)
```

### Key Components

1. **LangGraph** - Orchestrates agent workflow and routing
2. **LangChain Agents** - Specialized agents for different tasks
3. **LangChain Tools** - Functions that agents can invoke
4. **RAG System** - Retrieval-Augmented Generation for context
5. **Google Gemini** - LLM for agent reasoning and responses

---

## LangGraph Workflow

### Graph Structure

The workflow is defined in `graph.py` using LangGraph's `StateGraph`:

```python
from langgraph.graph import StateGraph, END
from state import ConversationState

# Create state graph
workflow = StateGraph(ConversationState)

# Add agent nodes
workflow.add_node("orchestrator_agent", orchestrator_agent)
workflow.add_node("retention_agent", retention_agent)
workflow.add_node("tech_support_agent", tech_support_agent)
workflow.add_node("billing_agent", billing_agent)
workflow.add_node("processor_agent", processor_agent)

# Set entry point
workflow.set_entry_point("orchestrator_agent")
```

### Routing Logic

**After Orchestrator:**
```python
def route_after_orchestrator(state: ConversationState):
    intent = state.get("intent")
    
    if intent == "cancel_insurance":
        return "retention_agent"
    elif intent == "technical_issue":
        return "tech_support_agent"
    elif intent == "billing_question":
        return "billing_agent"
    else:
        return "end"
```

**After Retention:**
```python
def route_after_retention(state: ConversationState):
    final_action = state.get("final_action")
    
    if final_action == "ready_to_cancel":
        return "processor_agent"
    else:
        return "end"
```

### Graph Execution Flow

```
User Input
    ↓
Orchestrator Agent (classifies intent)
    ↓
    ├─→ cancel_insurance → Retention Agent
    │                          ↓
    │                    (if confirmed)
    │                          ↓
    │                    Processor Agent → END
    │
    ├─→ technical_issue → Tech Support Agent → END
    │
    ├─→ billing_question → Billing Agent → END
    │
    └─→ general_question → END
```

---

## Agent Implementation

### Agent Structure

Each agent follows this pattern:

```python
from state import ConversationState
from langchain_google_genai import ChatGoogleGenerativeAI

def agent_name(state: ConversationState) -> ConversationState:
    """
    Agent function that processes state and returns updated state.
    
    Args:
        state: Current conversation state
        
    Returns:
        Updated conversation state
    """
    # 1. Extract relevant state fields
    user_message = state.get("user_message", "")
    intent = state.get("intent")
    
    # 2. Perform agent-specific logic
    #    - Call tools
    #    - Query RAG
    #    - Generate response
    
    # 3. Build updated state
    updated_state: ConversationState = {
        "user_message": user_message,
        "intent": intent,
        # ... update relevant fields
    }
    
    return updated_state
```

### Orchestrator Agent

**Purpose:** Classify intent and route to appropriate agent

**Key Features:**
- Uses **structured output** for reliable classification
- Extracts customer email
- Identifies cancellation reason
- No tool calls or RAG queries

```python
from pydantic import BaseModel

class IntentClassification(BaseModel):
    customer_email: Optional[str]
    intent: Literal["cancel_insurance", "technical_issue", "billing_question", "general_question"]
    cancellation_reason: Optional[str]
    greeting_message: str
    needs_email: bool

# Use structured output
structured_llm = llm.with_structured_output(IntentClassification)
classification = structured_llm.invoke(prompt)
```

### Retention Agent

**Purpose:** Handle cancellations and attempt retention

**Key Features:**
- Calls `get_customer_data` tool
- Queries RAG for policy context
- Calls `calculate_retention_offer` tool
- Generates empathetic response

**Tool Usage:**
```python
from tools.customer_tools import get_customer_data, calculate_retention_offer

# Get customer data
customer_data = get_customer_data.invoke({"email": customer_email})

# Calculate retention offer
offer = calculate_retention_offer.invoke({
    "customer_tier": customer_data["tier"],
    "reason": cancellation_reason
})
```

**RAG Usage:**
```python
from rag.vectorstore import get_retriever

retriever = get_retriever(k=3)
retrieved_docs = retriever.invoke(user_message)
```

### Tech Support Agent

**Purpose:** Handle technical issues

**Key Features:**
- Queries RAG for troubleshooting guide
- Provides step-by-step technical guidance
- No tool calls (doesn't need customer data)
- No retention attempts

**RAG Usage:**
```python
from rag.vectorstore import get_retriever

retriever = get_retriever(k=4)  # More chunks for technical support
query = f"technical issue troubleshooting: {user_message}"
retrieved_docs = retriever.invoke(query)
```

### Billing Agent

**Purpose:** Handle billing questions

**Key Features:**
- Calls `get_customer_data` tool (if email available)
- Queries RAG for billing and policy information
- Provides clear billing explanations
- No retention attempts

**Tool + RAG Usage:**
```python
from tools.customer_tools import get_customer_data
from rag.vectorstore import get_retriever

# Get customer data
if customer_email:
    customer_data = get_customer_data.invoke({"email": customer_email})

# Query RAG for billing info
retriever = get_retriever(k=4)
query = f"billing charges payment plan cost: {user_message}"
retrieved_docs = retriever.invoke(query)
```

### Processor Agent

**Purpose:** Process confirmed cancellations

**Key Features:**
- Calls `update_customer_status` tool
- Queries RAG for refund/return policies
- Provides procedural confirmation
- No retention attempts

---

## Tool Integration

### Tool Definition

Tools are defined using LangChain's `@tool` decorator:

```python
from langchain_core.tools import tool

@tool
def get_customer_data(email: str) -> dict:
    """Load customer profile from customers.csv
    
    Args:
        email: Customer email address to look up
        
    Returns:
        dict: Customer profile data
    """
    # Implementation
    return customer_data
```

### Tool Invocation

Agents invoke tools directly (not through LLM function calling):

```python
# Direct invocation
result = get_customer_data.invoke({"email": "customer@example.com"})

# Check for errors
if "error" in result:
    print(f"Error: {result['error']}")
else:
    # Use result
    customer_tier = result["tier"]
```

### Tool Error Handling

All tools return error dictionaries on failure:

```python
# Tool returns error
result = get_customer_data.invoke({"email": "nonexistent@example.com"})
# Result: {"error": "Customer with email nonexistent@example.com not found"}

# Agent handles error
if "error" in result:
    print(f"[Agent] Error: {result['error']}")
    customer_data = None
else:
    customer_data = result
```

---

## RAG Integration

### RAG System Components

1. **Document Loader** (`rag/loader.py`)
   - Loads markdown files from `data/` directory
   - Splits documents into chunks
   - Returns list of Document objects

2. **Vector Store** (`rag/vectorstore.py`)
   - Creates FAISS index
   - Uses HuggingFace embeddings
   - Provides retriever interface

3. **Retriever Usage** (in agents)
   - Agents query retriever with user messages
   - Retrieve top-k relevant chunks
   - Use chunks as context for LLM

### RAG Implementation

```python
# rag/vectorstore.py
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# Create embeddings
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)

# Build vector store
vectorstore = FAISS.from_documents(documents, embedding=embeddings)

# Get retriever
retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 4}
)
```

### RAG Query in Agents

```python
# In agent code
from rag.vectorstore import get_retriever

# Get retriever
retriever = get_retriever(k=3)

# Query with user message
retrieved_docs = retriever.invoke(user_message)

# Extract context
retrieved_context = []
for doc in retrieved_docs:
    content = doc.page_content
    source = doc.metadata.get("source", "unknown")
    retrieved_context.append(f"[{source}] {content}")
```

### RAG Context in LLM Prompt

```python
# Build prompt with RAG context
system_prompt = f"""
You are a customer support agent.

Relevant Policy Information:
{policy_context}  # From RAG

Customer Situation:
{user_message}

Generate a helpful response...
"""

messages = [
    SystemMessage(content=system_prompt),
    HumanMessage(content=user_message)
]

response = llm.invoke(messages)
```

---

## State Management

### ConversationState Schema

```python
from typing import TypedDict, Optional

class ConversationState(TypedDict):
    user_message: str
    customer_email: Optional[str]
    customer_data: Optional[dict]
    intent: Optional[str]
    cancellation_reason: Optional[str]
    retrieved_context: list[str]
    retention_offer: Optional[dict]
    final_action: Optional[str]
```

### State Flow

1. **Initial State** (from user input)
   ```python
   initial_state = {
       "user_message": "I want to cancel...",
       "customer_email": "sarah.chen@email.com",
       "customer_data": None,
       "intent": None,
       ...
   }
   ```

2. **After Orchestrator**
   ```python
   updated_state = {
       "user_message": "I want to cancel...",
       "customer_email": "sarah.chen@email.com",
       "intent": "cancel_insurance",
       "cancellation_reason": "financial_hardship",
       ...
   }
   ```

3. **After Retention Agent**
   ```python
   updated_state = {
       "user_message": "I want to cancel...",
       "customer_email": "sarah.chen@email.com",
       "customer_data": {...},  # From tool
       "intent": "cancel_insurance",
       "retrieved_context": [...],  # From RAG
       "retention_offer": {...},  # From tool
       ...
   }
   ```

### State Persistence

- State is passed between agents automatically by LangGraph
- Each agent reads from and updates the state
- State persists across the entire workflow
- Final state contains all information from all agents

---

## LLM Configuration

### Google Gemini Integration

```python
from langchain_google_genai import ChatGoogleGenerativeAI
import os

# Initialize LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.7  # Adjust based on agent needs
)
```

### Temperature Settings

- **Orchestrator:** `0.3` - Lower for consistent classification
- **Retention:** `0.7` - Higher for empathetic responses
- **Tech Support:** `0.5` - Balanced for clear technical guidance
- **Billing:** `0.4` - Lower for accurate billing information
- **Processor:** `0.3` - Lower for procedural accuracy

### Structured Output

Used in Orchestrator for reliable intent classification:

```python
from pydantic import BaseModel

class IntentClassification(BaseModel):
    intent: Literal["cancel_insurance", "technical_issue", ...]
    customer_email: Optional[str]
    ...

# Use structured output
structured_llm = llm.with_structured_output(IntentClassification)
result = structured_llm.invoke(prompt)
```

---

## Architecture Benefits

### 1. Modularity
- Each agent is independent
- Easy to add new agents
- Clear separation of concerns

### 2. Scalability
- Agents can be optimized independently
- RAG system can be enhanced without changing agents
- Tools can be extended easily

### 3. Observability
- State transitions are visible
- Tool calls are logged
- RAG queries are logged
- Full traceability

### 4. Maintainability
- Clear agent responsibilities
- Standardized patterns
- Easy to debug and test

---

## Design Patterns Used

### 1. State Machine Pattern
- LangGraph implements a state machine
- Clear state transitions
- Conditional routing based on state

### 2. Tool Pattern
- Agents use tools for data operations
- Tools are reusable across agents
- Error handling is standardized

### 3. RAG Pattern
- Retrieval-Augmented Generation
- Context injection into prompts
- Semantic search for relevance

### 4. Agent Pattern
- Specialized agents for specific tasks
- Each agent has clear responsibilities
- Agents communicate via shared state

---

## Extension Points

### Adding New Agents

1. Create agent file: `agents/new_agent.py`
2. Implement agent function: `def new_agent(state: ConversationState) -> ConversationState`
3. Add node to graph: `workflow.add_node("new_agent", new_agent)`
4. Add routing logic in `route_after_orchestrator`

### Adding New Tools

1. Define tool in `tools/customer_tools.py`:
   ```python
   @tool
   def new_tool(param: str) -> dict:
       """Tool description"""
       # Implementation
       return result
   ```

2. Import in agent: `from tools.customer_tools import new_tool`
3. Invoke in agent: `result = new_tool.invoke({"param": value})`

### Adding New Documents to RAG

1. Add markdown file to `data/` directory
2. Document loader automatically picks it up
3. Vector store rebuilds index
4. Agents can retrieve from new document

---

## Performance Considerations

### RAG Optimization
- **Chunk size:** 300-500 tokens for balance
- **Top-k:** 3-4 chunks typically sufficient
- **Embedding model:** Lightweight for fast retrieval

### Tool Optimization
- **Caching:** Customer data could be cached
- **Error handling:** Fast failure for missing data
- **Logging:** Minimal overhead

### Graph Execution
- **Compilation:** Graph compiled once at startup
- **State passing:** Efficient state updates
- **Conditional routing:** Fast intent-based routing

---

## Conclusion

The LangChain architecture provides:
- ✅ **Flexible agent orchestration** via LangGraph
- ✅ **Powerful tool integration** for data operations
- ✅ **Context-aware responses** via RAG
- ✅ **Reliable intent classification** via structured output
- ✅ **Maintainable codebase** with clear patterns

This architecture enables the system to handle complex multi-step customer interactions while maintaining clarity and observability.

---

*For examples of tool calls and RAG queries in action, see [TOOL_CALLS_AND_RAG.md](TOOL_CALLS_AND_RAG.md)*

