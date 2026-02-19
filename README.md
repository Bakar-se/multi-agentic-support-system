# Multi-Agent AI-Powered Customer Support System

A production-ready multi-agent customer support system for TechFlow Electronics that handles Care+ insurance plan cancellations, retention attempts, and customer inquiries using LangChain, LangGraph, and Google Gemini.

## Getting Started

### Prerequisites

- **Python 3.13** (recommended) or Python 3.10+
- **Google Gemini API key** - Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
- **Git** (for cloning the repository)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Bakar-se/multi-agentic-support-system.git
   cd multi-agentic-support-system
   ```

2. **Create a virtual environment with Python 3.13:**
   ```bash
   python3.13 -m venv venv
   ```
   
   If Python 3.13 is not available, you can use Python 3.10+:
   ```bash
   python3 -m venv venv
   ```

3. **Activate the virtual environment:**
   
   On macOS/Linux:
   ```bash
   source venv/bin/activate
   ```
   
   On Windows:
   ```bash
   venv\Scripts\activate
   ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up environment variables:**
   
   Create a `.env` file in the project root:
   ```bash
   echo "GOOGLE_API_KEY=your_gemini_api_key_here" > .env
   ```
   
   Or manually create `.env` and add:
   ```
   GOOGLE_API_KEY=your_gemini_api_key_here
   ```
   
   Alternatively, export directly in your terminal:
   ```bash
   export GOOGLE_API_KEY=your_gemini_api_key_here
   ```

### Running the Project

**Start the application:**
```bash
python main.py
```

Or if using the virtual environment directly:
```bash
venv/bin/python main.py
```

**Application Options:**
1. **Run all test scenarios** - Automated testing of all 5 predefined scenarios
2. **Interactive mode** - Manual conversation testing with custom messages
3. **Single test scenario** - Run one specific test scenario (1-5)
4. **Exit** - Quit the application

### Quick Test

To verify everything is set up correctly:
```bash
python main.py
# Select option 3 (Single test scenario)
# Enter scenario number: 1
```

## Overview

This system assists customers who want to cancel their Care+ phone insurance plan, attempts retention where appropriate, and routes non-cancellation requests correctly. It uses a multi-agent architecture where specialized agents handle different aspects of customer interactions, all orchestrated by LangGraph.

## Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Input                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   Orchestrator  │
                    │     Agent       │
                    │  (Intent Class) │
                    └────────┬────────┘
                             │
                ┌────────────┼────────────┐
                │            │            │
                ▼            ▼            ▼
        ┌───────────┐  ┌──────────┐  ┌──────────┐
        │ Retention │  │  Tech    │  │  Billing │
        │   Agent   │  │ Support  │  │  Agent   │
        └─────┬─────┘  └──────────┘  └──────────┘
              │
              ▼
        ┌───────────┐
        │ Processor │
        │   Agent   │
        └───────────┘
```

### Component Flow

1. **Orchestrator Agent** classifies intent and routes to appropriate agent
2. **Retention Agent** handles cancellations, retrieves customer data, queries RAG, generates offers
3. **Processor Agent** executes confirmed cancellations and logs actions
4. **Shared State** (`ConversationState`) persists across all agent transitions
5. **RAG System** provides policy document retrieval via FAISS vector store
6. **Tools** enable data retrieval, offer calculation, and status updates

## Agent Responsibilities

### 1. Greeter & Orchestrator Agent

**Location:** `agents/orchestrator.py`

**Responsibilities:**
- Greets the user and identifies/requests customer email
- Classifies user intent into: `cancel_insurance`, `technical_issue`, `billing_question`, `general_question`
- Extracts cancellation reason when applicable (`financial_hardship`, `product_issues`, `service_value`)
- Routes conversation using LangGraph conditional edges

**Constraints:**
- Does NOT attempt retention or cancellation
- Outputs structured JSON for routing decisions
- Uses Gemini 1.5 Flash with structured output

### 2. Retention & Problem-Solving Agent

**Location:** `agents/retention.py`

**Responsibilities:**
- Handles cancellation-related conversations only
- Retrieves customer data using `get_customer_data` tool
- Queries RAG retriever for relevant policy context
- Generates retention offers using `calculate_retention_offer` tool
- Communicates empathetically with customers
- Decides whether to escalate to Processor Agent

**Behavior Rules:**
- MUST attempt retention before cancellation
- MUST NOT offer discounts for technical or billing issues
- MUST explain Care+ value when applicable
- Only escalates after explicit cancellation confirmation

### 3. Processor Agent

**Location:** `agents/processor.py`

**Responsibilities:**
- Processes confirmed cancellations only
- Updates customer status using `update_customer_status` tool
- References refund/return policies via RAG
- Provides procedural confirmation messages

**Constraints:**
- Does NOT attempt persuasion
- Procedural and concise communication
- Executes only after explicit user confirmation

## How to Run the System

> **Note:** For detailed installation and setup instructions, see the [Getting Started](#getting-started) section above.

**Start the main application:**
```bash
python main.py
```

**Application Options:**
1. Run all test scenarios (automated testing)
2. Interactive mode (manual conversation testing)
3. Single test scenario (run one specific scenario)
4. Exit

## How RAG Works

The Retrieval-Augmented Generation (RAG) system enhances agent responses with relevant policy document context.

### Document Loading (`rag/loader.py`)

- Loads policy documents from `data/` directory:
  - `return_policy.md` - Return Policy
  - `care_plus_benefits.md` - Care+ Benefits
  - `troubleshooting_guide.md` - Tech Support Guide
- Splits documents into chunks (300-500 tokens, ~1500 characters)
- Uses `RecursiveCharacterTextSplitter` with overlap for context preservation

### Vector Store (`rag/vectorstore.py`)

- Uses **FAISS** for efficient similarity search
- Employs **SentenceTransformers** (`all-MiniLM-L6-v2`) for embeddings
- Builds index from loaded documents
- Provides `get_retriever(k=4)` interface for top-k document retrieval

### Usage in Agents

Agents query the RAG system with user messages or specific queries:
```python
retriever = get_retriever(k=3)
retrieved_docs = retriever.invoke("refund policy cancellation")
```

Retrieved context is:
- Stored in `ConversationState.retrieved_context`
- Logged for observability
- Used by agents to generate informed responses

## How Tools Are Used

Three LangChain tools enable agent interactions with data:

### 1. `get_customer_data(email: str) -> dict`

**Location:** `tools/customer_tools.py`

- Loads customer profile from `data/customers.csv`
- Returns customer data including: `customer_id`, `name`, `plan_type`, `tier`, `account_health_score`, etc.
- Used by Retention Agent to retrieve customer information

**Example:**
```python
customer_data = get_customer_data.invoke({"email": "sarah.chen@email.com"})
```

### 2. `calculate_retention_offer(customer_tier: str, reason: str) -> dict`

**Location:** `tools/customer_tools.py`

- Generates retention offers using `data/retention_rules.json`
- Maps customer tier (`premium`, `regular`, `new`) and cancellation reason to appropriate offers
- Returns offer details: `type`, `cost`, `duration`, `description`, `authorization`
- Used by Retention Agent to generate personalized offers

**Example:**
```python
offer = calculate_retention_offer.invoke({
    "customer_tier": "premium",
    "reason": "financial_hardship"
})
```

### 3. `update_customer_status(customer_id: str, action: str) -> dict`

**Location:** `tools/customer_tools.py`

- Updates customer status and logs to `customer_status_log.txt`
- Records action with timestamp
- Used by Processor Agent to finalize cancellations

**Example:**
```python
result = update_customer_status.invoke({
    "customer_id": "CUST_001",
    "action": "cancelled"
})
```

## Testing All 5 Scenarios

The system includes 5 predefined test scenarios that demonstrate correct agent routing, tool usage, RAG retrieval, and final actions.

### Running All Scenarios

```bash
python main.py
# Select option 1: Run all test scenarios
```

### Individual Scenarios

**1. Affordability-based cancellation**
- Customer: `sarah.chen@email.com`
- Message: "I want to cancel my Care+ plan. It's too expensive and I can't afford it anymore."
- Expected: Intent `cancel_insurance`, reason `financial_hardship`, retention offer generated

**2. Device malfunction + cancellation**
- Customer: `mike.rodriguez@email.com`
- Message: "My phone keeps overheating and I want to cancel my insurance because the device is defective."
- Expected: Intent `cancel_insurance`, reason `product_issues`, device replacement offer

**3. Value questioning**
- Customer: `lisa.kim@email.com`
- Message: "I'm thinking about canceling. I've had the plan for 8 months and haven't used it once. Is it really worth it?"
- Expected: Intent `cancel_insurance`, reason `service_value`, value explanation and trial extension

**4. Technical support request**
- Customer: `james.wilson@email.com`
- Message: "My phone battery is draining really fast. Can you help me fix this?"
- Expected: Intent `technical_issue`, routed to end (no retention attempt)

**5. Billing discrepancy inquiry**
- Customer: `maria.garcia@email.com`
- Message: "I was charged $12.99 this month but I thought my plan was $6.99. Can you explain the charge?"
- Expected: Intent `billing_question`, routed to end (no retention attempt)

### Running Single Scenario

```bash
python main.py
# Select option 3: Single test scenario
# Enter scenario number (1-5)
```

### Interactive Testing

```bash
python main.py
# Select option 2: Interactive mode
# Enter messages manually, optionally with email: email@example.com <message>
```

## Project Structure

```
multi-agentic-support-system/
├── agents/
│   ├── orchestrator.py    # Intent classification and routing
│   ├── retention.py       # Retention and problem-solving
│   └── processor.py       # Cancellation processing
├── data/
│   ├── customers.csv           # Customer profiles
│   ├── retention_rules.json    # Business rules for offers
│   ├── care_plus_benefits.md   # Policy document
│   ├── return_policy.md        # Policy document
│   └── troubleshooting_guide.md # Policy document
├── rag/
│   ├── loader.py          # Document loading and chunking
│   └── vectorstore.py     # FAISS vector store and retriever
├── tools/
│   └── customer_tools.py  # LangChain tools for data operations
├── graph.py               # LangGraph workflow definition
├── main.py                # CLI entry point
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Technology Stack

- **Python 3.13** (recommended) or Python 3.10+
- **LangChain** - LLM framework and tooling
- **LangGraph** - Multi-agent orchestration
- **Google Gemini 1.5 Flash** - Language model
- **FAISS** - Vector similarity search
- **SentenceTransformers** - Text embeddings
- **Pandas** - Data processing

## Observability

The system provides comprehensive logging:

- **Agent transitions** - Which agent is currently executing
- **Tool calls** - All tool invocations with parameters and results
- **RAG retrieval** - Retrieved document chunks with source information
- **Final outcomes** - Final action taken (cancelled, retained, etc.)

All information is printed to console during execution for debugging and demonstration purposes.

## License

This project is part of a technical demonstration and evaluation system.

