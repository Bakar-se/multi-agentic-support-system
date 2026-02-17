# Software Requirements Specification (SRS)
## Multi-Agent AI-Powered Customer Support Chat System

### 1. Introduction

#### 1.1 Purpose

This document specifies the requirements for building a multi-agent AI-powered customer support chat system for TechFlow Electronics. The system assists customers who want to cancel their Care+ phone insurance plan, attempts retention where appropriate, and routes non-cancellation requests correctly.

This SRS is intended for implementation using Python, LangChain, and LangGraph, and will be used by an AI coding assistant (Cursor) to generate production-quality code aligned with evaluation criteria.

#### 1.2 Scope

**The system will:**
- Accept customer chat input
- Identify user intent (cancellation, technical support, billing, general inquiry)
- Use multiple AI agents with distinct responsibilities
- Retrieve customer data and company policy documents
- Offer retention solutions before cancellation
- Process cancellations when explicitly confirmed
- Log all customer account changes

**The system will not include:**
- A complex UI. Interaction will be via CLI or Streamlit.

---

### 2. Overall System Description

#### 2.1 System Architecture

The system uses a multi-agent architecture orchestrated by LangGraph, consisting of:

1. **Greeter & Orchestrator Agent**
2. **Retention & Problem-Solving Agent**
3. **Processor Agent**

Agents communicate via a shared conversation state managed by LangGraph.

#### 2.2 Technology Stack

**Backend:**
- Python 3.10+
- LangChain
- LangGraph

**LLM:**
- Google Gemini 1.5 Flash (free tier)
- Function calling / structured output enabled

**RAG:**
- FAISS (local vector store)
- SentenceTransformers embeddings
- Local document loading from policy files

**Data Sources:**
- `customers.csv` (customer profiles)
- `retention_rules.json` (business rules)
- Policy documents (Markdown / TXT)

---

### 3. Functional Requirements

#### 3.1 Conversation State Management

The system MUST maintain a shared state across agents containing:

```python
ConversationState:
  user_message: str
  customer_email: Optional[str]
  customer_data: Optional[dict]
  intent: Optional[str]
  cancellation_reason: Optional[str]
  retrieved_context: list[str]
  retention_offer: Optional[dict]
  final_action: Optional[str]
```

**State MUST persist and update between agent transitions.**

#### 3.2 Agent Definitions

##### 3.2.1 Agent 1 – Greeter & Orchestrator

**Responsibilities:**
- Greet the user
- Identify or request customer email
- Classify user intent
- Route conversation to the appropriate agent using LangGraph conditional edges

**Intent Categories:**
- `cancel_insurance`
- `technical_issue`
- `billing_question`
- `general_question`

**Constraints:**
- MUST NOT attempt retention or cancellation
- MUST output structured JSON for routing decisions

##### 3.2.2 Agent 2 – Retention & Problem Solver

**Responsibilities:**
- Handle cancellation-related conversations
- Retrieve customer data using tools
- Query policy documents using RAG
- Generate retention offers using business rules
- Communicate empathetically with the customer

**Behavior Rules:**
- MUST attempt retention before cancellation
- MUST NOT offer discounts for technical or billing issues
- MUST explain Care+ value when applicable
- MUST escalate to Processor Agent only after explicit cancellation confirmation

##### 3.2.3 Agent 3 – Processor

**Responsibilities:**
- Process confirmed cancellations
- Update customer status using tools
- Log actions to a file
- Provide confirmation and timeline information

**Constraints:**
- MUST NOT attempt persuasion
- MUST reference return/refund policies using RAG
- MUST execute only after explicit user confirmation

---

### 4. Tooling Requirements

The system MUST implement the following tools exactly as specified:

```python
@tool
def get_customer_data(email: str) -> dict:
    """Load customer profile from customers.csv"""

@tool
def calculate_retention_offer(customer_tier: str, reason: str) -> dict:
    """Generate offers using retention_rules.json"""

@tool
def update_customer_status(customer_id: str, action: str) -> dict:
    """Process cancellations/changes and log to file"""
```

**Tool Usage Rules:**
- Tools MUST be invoked by agents (not manually)
- Tools MUST operate on real data files
- Error handling is required for missing or invalid inputs

---

### 5. Retrieval-Augmented Generation (RAG)

#### 5.1 Documents

The system MUST ingest and retrieve from:
- Return Policy
- Care+ Benefits
- Tech Support Guide

#### 5.2 Vector Search

- Use FAISS for vector indexing
- Chunk documents (300–500 tokens)
- Retrieve top-k relevant chunks per query

#### 5.3 Usage

- Agents MUST query documents during conversations
- Retrieved context MUST influence responses
- Retrieved snippets SHOULD be logged for demo visibility

---

### 6. LangGraph Workflow

#### 6.1 Graph Structure

**Nodes:**
- `orchestrator_agent`
- `retention_agent`
- `processor_agent`
- Optional: `tech_support_agent`, `billing_agent`

**Edges:**
- Conditional routing based on intent
- Explicit handoff between agents

#### 6.2 Requirements

- LangGraph MUST be used for orchestration
- Conditional edges MUST determine agent routing
- State transitions MUST be inspectable

---

### 7. Non-Functional Requirements

#### 7.1 Reliability

- System must handle missing customer data gracefully
- Prevent infinite agent loops

#### 7.2 Observability

Log:
- Agent transitions
- Tool calls
- RAG retrieval results
- Final outcomes

#### 7.3 Maintainability

- Modular folder structure
- Clear separation of agents, tools, and RAG logic

---

### 8. Testing Requirements

The system MUST correctly handle the following test scenarios:

1. **Affordability-based cancellation**
2. **Device malfunction + cancellation**
3. **Value questioning**
4. **Technical support request**
5. **Billing discrepancy inquiry**

Each test MUST demonstrate:
- Correct agent routing
- Appropriate tool usage
- Relevant RAG retrieval
- Proper final action

---

### 9. Deliverables

- Fully working Python codebase
- README with setup and run instructions
- Loom video demonstrating:
  - All 5 test cases
  - Agent routing
  - Tool calls
  - RAG usage

---

### 10. Out of Scope

- Advanced UI / frontend development
- Authentication
- Persistent databases
- Production deployment

---

### ✅ Implementation Priority Order

1. **LangGraph orchestration**
2. **Tool integration**
3. **RAG retrieval**
4. **Agent behavior**
5. **UI (optional)**

**Note:** Correctness and architectural clarity take precedence over conversational polish.

