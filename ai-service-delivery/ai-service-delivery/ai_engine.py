"""AI engine: classify a service request, set priority, route to a team, draft a reply.
Uses Claude when ANTHROPIC_API_KEY is set; otherwise falls back to simple keyword rules."""
import json
import os

CATEGORIES = {
    "billing":   ["invoice", "charge", "refund", "payment", "billing", "price"],
    "technical": ["error", "bug", "crash", "not working", "login", "password", "slow", "down"],
    "account":   ["account", "profile", "email change", "update my", "delete my"],
    "delivery":  ["delivery", "shipping", "order", "late", "tracking", "package"],
}
TEAMS = {"billing": "Finance Team", "technical": "Tech Support", "account": "Account Services",
         "delivery": "Logistics Team", "general": "General Helpdesk"}
SLA_HOURS = {"high": 4, "medium": 24, "low": 72}
URGENT_WORDS = ["urgent", "asap", "immediately", "down", "outage", "critical", "cannot access", "emergency"]


def _rule_based(text: str) -> dict:
    t = text.lower()
    scores = {c: sum(k in t for k in kws) for c, kws in CATEGORIES.items()}
    category = max(scores, key=scores.get) if any(scores.values()) else "general"
    urgent = sum(w in t for w in URGENT_WORDS)
    negative = sum(w in t for w in ["angry", "terrible", "worst", "unacceptable", "disappointed"])
    priority = "high" if urgent else ("medium" if negative or scores.get(category, 0) >= 2 else "low")
    sentiment = "negative" if negative else "neutral"
    reply = (f"Hello, thanks for contacting us. We've logged your {category} request as "
             f"{priority} priority and assigned it to {TEAMS[category]}. "
             f"You can expect an update within {SLA_HOURS[priority]} hours.")
    return {"category": category, "priority": priority, "sentiment": sentiment, "reply": reply}


def _claude(text: str) -> dict:
    import anthropic
    client = anthropic.Anthropic()
    prompt = (
        "You triage customer service requests. Return ONLY JSON with keys: "
        "category (billing|technical|account|delivery|general), priority (high|medium|low), "
        "sentiment (positive|neutral|negative), reply (a short, polite draft response).\n\n"
        f"Request: {text}"
    )
    msg = client.messages.create(model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5"),
                                 max_tokens=400, messages=[{"role": "user", "content": prompt}])
    raw = msg.content[0].text.strip()
    raw = raw[raw.find("{"): raw.rfind("}") + 1]
    return json.loads(raw)


def analyze(text: str) -> dict:
    result = None
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            result = _claude(text)
            result["source"] = "claude"
        except Exception as e:  # network/parse failure -> fall back
            print("Claude failed, using rules:", e)
    if result is None:
        result = _rule_based(text)
        result["source"] = "rules"
    if result.get("category") not in TEAMS:
        result["category"] = "general"
    if result.get("priority") not in SLA_HOURS:
        result["priority"] = "medium"
    result["team"] = TEAMS[result["category"]]
    result["sla_hours"] = SLA_HOURS[result["priority"]]
    return result
