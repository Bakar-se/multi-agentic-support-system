# Tool Calls and RAG Queries in Action

This document demonstrates how tools and RAG (Retrieval-Augmented Generation) are used throughout the multi-agent customer support system.

## Overview

The system uses:
- **LangChain Tools** for data operations (customer data, retention offers, status updates)
- **RAG System** for retrieving relevant policy and troubleshooting information
- **FAISS Vector Store** for efficient similarity search

---

## Part 1: Tool Calls

### Tool 1: `get_customer_data`

**Purpose:** Retrieve customer profile information from the database

**Location:** `tools/customer_tools.py`

**Example Usage in Retention Agent:**

```python
from tools.customer_tools import get_customer_data

# Agent invokes the tool
customer_data_result = get_customer_data.invoke({"email": "sarah.chen@email.com"})

# Result:
{
    "customer_id": "CUST_001",
    "email": "sarah.chen@email.com",
    "name": "Sarah Chen",
    "plan_type": "Care+ Premium",
    "monthly_charge": 12.99,
    "tier": "premium",
    "account_health_score": 85,
    "tenure_months": 8,
    "status": "active",
    ...
}
```

**Real Execution Example:**

```
[Retention Agent] Retrieving customer data...
[Retention Agent] Customer tier: premium
[Retention Agent] Customer: Sarah Chen - Care+ Premium
```

**When Used:**
- ✅ Retention Agent (for cancellation scenarios)
- ✅ Billing Agent (for billing questions)
- ❌ Tech Support Agent (not needed for technical issues)

---

### Tool 2: `calculate_retention_offer`

**Purpose:** Generate personalized retention offers based on customer tier and cancellation reason

**Location:** `tools/customer_tools.py`

**Example Usage in Retention Agent:**

```python
from tools.customer_tools import calculate_retention_offer

# Agent invokes the tool with customer tier and cancellation reason
offer_result = calculate_retention_offer.invoke({
    "customer_tier": "premium",
    "reason": "financial_hardship"
})

# Result:
{
    "type": "pause",
    "description": "Pause subscription for 6 months with no charges",
    "new_cost": 0.0,
    "duration_months": 6,
    "authorization": "manager_approval_required"
}
```

**Real Execution Example:**

```
[Retention Agent] Calculating retention offer for tier=premium, reason=financial_hardship...
[Retention Agent] Generated offer: pause
[Retention Agent] Offer details: Pause subscription for 6 months with no charges
```

**Business Rules Applied:**
- `financial_hardship` + `premium` tier → Pause offer
- `product_issues` + `new` tier → Device replacement offer
- `service_value` + `premium` tier → Benefits explanation offer

**When Used:**
- ✅ Retention Agent only (for cancellation scenarios)
- ❌ Tech Support Agent (no retention for technical issues)
- ❌ Billing Agent (no retention for billing questions)

---

### Tool 3: `update_customer_status`

**Purpose:** Log customer status changes (cancellations, retentions, etc.)

**Location:** `tools/customer_tools.py`

**Example Usage in Processor Agent:**

```python
from tools.customer_tools import update_customer_status

# Agent invokes the tool after cancellation confirmation
result = update_customer_status.invoke({
    "customer_id": "CUST_001",
    "action": "cancelled"
})

# Result:
{
    "status": "success",
    "customer_id": "CUST_001",
    "action": "cancelled",
    "timestamp": "2024-01-15 14:30:22",
    "message": "Customer status updated and logged successfully"
}
```

**Log File Entry:**
```
[2024-01-15 14:30:22] Customer: CUST_001 | Action: cancelled
```

**When Used:**
- ✅ Processor Agent (for confirmed cancellations)
- ❌ Other agents (only processor executes status changes)

---

## Part 2: RAG Queries

### RAG System Architecture

```
Documents (Markdown)
    ↓
Document Loader (chunking)
    ↓
FAISS Vector Store (embeddings)
    ↓
Retriever (similarity search)
    ↓
Agent Context
```

### RAG Query Example 1: Retention Agent

**Scenario:** Customer wants to cancel due to financial hardship

**Query:**
```python
from rag.vectorstore import get_retriever

# Get retriever with top-k results
retriever = get_retriever(k=3)

# Query with user message and context
query = "I want to cancel my Care+ plan. It's too expensive and I can't afford it anymore. Reason: financial_hardship"

# Invoke retriever
retrieved_docs = retriever.invoke(query)
```

**Retrieved Context:**
```
[Retention Agent] Retrieved from care_plus_benefits.md:
  ## Care+ Basic ($6.99/month)

### Core Protection
- **Screen Repair**: $29 deductible for cracked screen repairs
- **Hardware Defects**: Standard warranty extension coverage
- **Basic Support**: Stand...

[Retention Agent] Retrieved from care_plus_benefits.md:
  ### Preventive Care
- Regular device health checkups
- Software optimization and cleanup
- Early warning for potential hardware issues
- Proactive battery health monitoring

[Retention Agent] Retrieved from care_plus_benefits.md:
  # TechFlow Care+ Benefits Guide

## Care+ Premium ($12.99/month)

### Accident Protection
- **Screen Repair**: Zero deductible for cracked screens (normally $300+ repair cost)
- **Water Damage**: Full...
```

**How It's Used:**
The agent uses this context to:
1. Understand the customer's current plan benefits
2. Explain value of Care+ Premium plan
3. Reference specific benefits in retention conversation
4. Generate empathetic response with relevant information

---

### RAG Query Example 2: Tech Support Agent

**Scenario:** Customer reports battery drain issue

**Query:**
```python
from rag.vectorstore import get_retriever

# Get retriever with top-k results (more chunks for technical support)
retriever = get_retriever(k=4)

# Query focused on technical issue
query = "technical issue troubleshooting: My phone battery is draining really fast. Can you help me fix this?"

# Invoke retriever
retrieved_docs = retriever.invoke(query)
```

**Retrieved Context:**
```
[Tech Support Agent] Retrieved from troubleshooting_guide.md:
  # TechFlow Device Troubleshooting Guide

## Common Phone Issues

### Overheating Problems
**Symptoms**: Device feels hot, performance slows down, battery drains quickly

**Quick Fixes**:
- Remove phone case and let device cool down
- Close all background apps
- Reduce screen brightness temporarily
...

[Tech Support Agent] Retrieved from troubleshooting_guide.md:
  ### Battery Drain Issues
**Common Causes**: Background app refresh, location services, screen brightness, aging battery

**Optimization Steps**:
- Enable Low Power Mode
- Disable Background App Refresh for non-essential apps
- Reduce location service permissions
- Lower screen brightness and timeout settings
...
```

**How It's Used:**
The agent uses this context to:
1. Provide step-by-step troubleshooting instructions
2. Reference specific optimization steps
3. Explain what each step does
4. Guide customer through resolution process

---

### RAG Query Example 3: Billing Agent

**Scenario:** Customer questions billing charge

**Query:**
```python
from rag.vectorstore import get_retriever

# Get retriever with top-k results
retriever = get_retriever(k=4)

# Query focused on billing
query = "billing charges payment plan cost: I was charged $12.99 this month but I thought my plan was $6.99. Can you explain the charge?"

# Invoke retriever
retrieved_docs = retriever.invoke(query)
```

**Retrieved Context:**
```
[Billing Agent] Retrieved from care_plus_benefits.md:
  ## Care+ Basic ($6.99/month)

### Core Protection
- **Screen Repair**: $29 deductible for cracked screen repairs
...

[Billing Agent] Retrieved from care_plus_benefits.md:
  # TechFlow Care+ Benefits Guide

## Care+ Premium ($12.99/month)

### Accident Protection
- **Screen Repair**: Zero deductible for cracked screens (normally $300+ repair cost)
...
```

**How It's Used:**
The agent uses this context to:
1. Explain the difference between Basic ($6.99) and Premium ($12.99) plans
2. Reference customer's actual plan from customer data
3. Clarify billing charges
4. Provide accurate billing information

---

## Part 3: Complete Flow Example

### Scenario: Affordability-based Cancellation

**Step 1: Orchestrator Classifies Intent**
```
[Orchestrator] Intent: cancel_insurance
[Orchestrator] Email: sarah.chen@email.com
[Orchestrator] Cancellation reason: financial_hardship
```

**Step 2: Retention Agent - Tool Call**
```python
# Tool: get_customer_data
customer_data = get_customer_data.invoke({"email": "sarah.chen@email.com"})
# Returns: Customer profile with tier="premium"
```

**Step 3: Retention Agent - RAG Query**
```python
# RAG: Retrieve policy context
retriever = get_retriever(k=3)
retrieved_docs = retriever.invoke("I want to cancel my Care+ plan. It's too expensive...")
# Returns: 3 chunks from care_plus_benefits.md
```

**Step 4: Retention Agent - Tool Call**
```python
# Tool: calculate_retention_offer
offer = calculate_retention_offer.invoke({
    "customer_tier": "premium",
    "reason": "financial_hardship"
})
# Returns: Pause offer (6 months, no charge)
```

**Step 5: Agent Generates Response**
- Uses customer data (name, plan, tier)
- Uses RAG context (benefits, plan details)
- Uses retention offer (pause offer details)
- Generates empathetic response with all context

**Step 6: If Cancellation Confirmed - Processor Agent - Tool Call**
```python
# Tool: update_customer_status
result = update_customer_status.invoke({
    "customer_id": "CUST_001",
    "action": "cancelled"
})
# Logs to customer_status_log.txt
```

---

## RAG System Details

### Document Loading Process

```python
# rag/loader.py
from langchain_community.document_loaders import DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Load documents from data/ directory
documents = load_documents()
# Returns: List of Document objects from:
#   - return_policy.md
#   - care_plus_benefits.md
#   - troubleshooting_guide.md
```

### Vector Store Creation

```python
# rag/vectorstore.py
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# Create embeddings model
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)

# Build FAISS index
vectorstore = FAISS.from_documents(
    documents=documents,
    embedding=embeddings
)
```

### Retrieval Process

```python
# Get retriever interface
retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 4}  # Top 4 most similar chunks
)

# Query the retriever
results = retriever.invoke("user query here")
# Returns: List of Document objects with:
#   - page_content: The chunk text
#   - metadata: Source file information
```

---

## Tool and RAG Usage Matrix

| Agent | get_customer_data | calculate_retention_offer | update_customer_status | RAG Query |
|-------|-------------------|---------------------------|------------------------|-----------|
| Orchestrator | ❌ | ❌ | ❌ | ❌ |
| Retention | ✅ | ✅ | ❌ | ✅ |
| Processor | ❌ | ❌ | ✅ | ✅ |
| Tech Support | ❌ | ❌ | ❌ | ✅ |
| Billing | ✅ | ❌ | ❌ | ✅ |

---

## Best Practices

### Tool Usage
1. **Always check for errors** in tool return values
2. **Use tools only when needed** (e.g., don't retrieve customer data for tech support)
3. **Handle missing data gracefully** (customer not found, etc.)
4. **Log tool calls** for observability

### RAG Usage
1. **Query with context** - Include user message and relevant keywords
2. **Adjust k value** - More chunks for complex queries, fewer for specific topics
3. **Use retrieved context** - Don't ignore the retrieved information
4. **Log retrieved chunks** - Show what context was used for transparency

---

## Observability

All tool calls and RAG queries are logged to console:

```
[Retention Agent] Retrieving customer data...
[Retention Agent] Customer tier: premium
[Retention Agent] Querying RAG for policy context...
[Retention Agent] Retrieved from care_plus_benefits.md: ...
[Retention Agent] Calculating retention offer...
[Retention Agent] Generated offer: pause
```

This provides full transparency into:
- Which tools were called
- What data was retrieved
- What RAG context was used
- How decisions were made

---

*For more details on the architecture, see [LANGCHAIN_ARCHITECTURE.md](LANGCHAIN_ARCHITECTURE.md)*

