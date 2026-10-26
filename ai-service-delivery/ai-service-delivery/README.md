# AI-Enabled Service Delivery (base project)

Customers submit service requests; an AI engine classifies the category, sets priority and
SLA, routes to a team, and drafts a reply. Agents manage tickets from a live dashboard.

## Run
    pip install -r requirements.txt
    python app.py            # http://localhost:5000

Optional: `export ANTHROPIC_API_KEY=...` to use Claude; without it, keyword rules are used.

## Structure
- `app.py` – Flask API + SQLite (tickets, stats, status updates)
- `ai_engine.py` – classification / priority / routing / reply (Claude or rule-based)
- `templates/index.html` – submission form, stats, ticket queue

## Ideas to extend
Authentication, email intake, knowledge-base retrieval for replies, SLA breach alerts, analytics.
