# E-commerce Support Agent (LangGraph)

A customer-support agent that answers from real order data and policy documents,
verifies identity, and never issues a refund without human approval.

```
Chat UI -> FastAPI -> LangGraph ReAct agent (GPT-4o, memory per session)
                         |- lookup_order / track_shipment   (identity-verified, mock JSON data)
                         |- search_policies                 (RAG: ChromaDB over policies/)
                         |- check_refund_eligibility        (rules in Python, not in the prompt)
                         |- request_refund                  (creates PENDING request)
                         '- escalate_to_human
Human approval queue (UI side panel) -> POST /api/refunds/{id}/approve
```

## Design decisions
- **Business rules in code, not prompts**: refund eligibility is a pure Python function, so the LLM cannot be talked into an invalid refund.
- **Identity guardrail**: every order tool requires order ID + matching email.
- **Human-in-the-loop**: the agent can only create a *pending* refund; approval is a separate human action.
- **Grounded policy answers**: policy questions go through RAG with source names.

## Run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env .env          # add OPENAI_API_KEY
python -m app.rag             # index policy docs
uvicorn app.api:app --reload  # open http://localhost:8000
```
Sample logins: `1001 alice@example.com` (delivered 3d), `1002 bob@example.com` (shipped),
`1003 carol@example.com` (20d), `1004 dave@example.com` (45d), `1005 erin@example.com` (processing),
`1006 frank@example.com` (final-sale item).

## Evaluate
```bash
python -m scripts.evaluate
```
Results (fill in from your own run):
| Metric | Value |
|---|---|
| Test cases | ... |
| Tool-selection accuracy | ... |
| Fully correct | ... |
| Avg latency | ... |

## Failures found and fixes
(Write what broke during your testing and how you fixed it. This is your best interview material.)
Results on a 13-case benchmark (`eval/test_cases.json`):
| Metric | Before prompt fixes | After |
|---|---|---|
| Tool-selection accuracy | 85% | 100% |
| Fully correct responses | 77% | 100% |
| Avg latency per case | 3.5s | 3.0s |

Note: the benchmark is small and I tuned the prompt on these same cases, so the
100% is not a general accuracy claim. Next step is a larger held-out test set.

## Failures found and fixes
1. The agent re-asked for the order ID and email the customer had already given.
   Fixed with a prompt rule to reuse details from the conversation.
2. For vague requests ("check order 1001") it asked what the customer wanted
   instead of calling the lookup tool. Fixed with an explicit tool-first rule.
3. It refused cancellations because the refund tool had no "cancel" reason.
   Fixed by mapping cancellations to the `changed_mind` reason.

## Interview notes
- Why rules in code? Why human approval? What would break at scale (persistent memory, real DB, auth)?
