from __future__ import annotations

_TAXONOMY: dict[str, dict] = {
    "auto_renewal": {
        "name": "Auto-Renewal",
        "definition": "Contract renews automatically unless cancelled in a set window.",
        "why_it_matters": (
            "You can get locked into another full term — and billed — "
            "if you miss a narrow notice window."
        ),
        "signal_language": [
            "automatically renew",
            "unless cancelled … days prior",
            "evergreen term",
        ],
    },
    "unilateral_change": {
        "name": "Unilateral Change",
        "definition": "One side can change the terms (price, scope, rules) at will.",
        "why_it_matters": (
            "The deal you agreed to can shift under you, "
            "often with only 'notice' or none."
        ),
        "signal_language": [
            "we may modify at any time",
            "in our sole discretion",
            "continued use constitutes acceptance",
        ],
    },
    "liability_limitation": {
        "name": "Liability Limitation",
        "definition": "Caps or excludes one side's liability if things go wrong.",
        "why_it_matters": (
            "If they harm you, your recovery may be capped far below your actual loss "
            "(often to fees paid)."
        ),
        "signal_language": [
            "limited to the amount paid",
            "in no event liable",
            "exclusion of consequential damages",
        ],
    },
    "indemnification": {
        "name": "Indemnification",
        "definition": "One party agrees to cover the other's losses/legal costs.",
        "why_it_matters": (
            "A one-sided indemnity can make you pay for their lawsuits "
            "or third-party claims."
        ),
        "signal_language": [
            "indemnify and hold harmless",
            "defend against any claims arising from",
        ],
    },
    "arbitration_or_class_waiver": {
        "name": "Arbitration / Class Action Waiver",
        "definition": "Disputes go to private arbitration; class actions waived.",
        "why_it_matters": (
            "You give up court, a jury, and the ability to band together — "
            "arbitration can favor the drafter."
        ),
        "signal_language": [
            "binding arbitration",
            "waive any right to a jury trial",
            "no class actions",
        ],
    },
    "data_sharing_or_privacy": {
        "name": "Data Sharing / Privacy",
        "definition": "How your data is collected, used, shared, sold, or retained.",
        "why_it_matters": (
            "Your data may be sold or shared with third parties, or kept indefinitely, "
            "beyond what you'd expect."
        ),
        "signal_language": [
            "share with third parties",
            "sell or transfer",
            "for marketing purposes",
            "retain indefinitely",
        ],
    },
    "ip_assignment": {
        "name": "IP Assignment",
        "definition": "Ownership of work/ideas transfers to the other party.",
        "why_it_matters": (
            "You can lose rights to what you create — sometimes including work "
            "unrelated to the engagement."
        ),
        "signal_language": [
            "all work product shall be owned by",
            "hereby assigns",
            "including pre-existing IP",
        ],
    },
    "non_compete_or_non_solicit": {
        "name": "Non-Compete / Non-Solicit",
        "definition": "Restricts who you can work for or solicit afterward.",
        "why_it_matters": (
            "Can limit your ability to earn a living or take clients/colleagues after you leave."
        ),
        "signal_language": [
            "shall not compete",
            "for a period of … months",
            "shall not solicit",
        ],
    },
    "termination_terms": {
        "name": "Termination Terms",
        "definition": "How and when either side can end the contract.",
        "why_it_matters": (
            "One-sided or onerous exit terms can trap you in, "
            "or let them drop you, on bad conditions."
        ),
        "signal_language": [
            "may terminate for convenience",
            "with 90 days notice",
            "no early termination",
        ],
    },
    "payment_fees_penalties": {
        "name": "Payment / Fees / Penalties",
        "definition": "What you pay, when, and the penalties for lapses.",
        "why_it_matters": (
            "Hidden fees, steep late penalties, or non-refundable terms "
            "can cost far more than the headline price."
        ),
        "signal_language": [
            "late fee",
            "non-refundable",
            "liquidated damages",
            "interest at … %",
        ],
    },
    "confidentiality": {
        "name": "Confidentiality",
        "definition": "Obligations to keep information secret.",
        "why_it_matters": (
            "Overbroad or perpetual NDAs can restrict you long after the relationship ends."
        ),
        "signal_language": [
            "in perpetuity",
            "any information disclosed",
            "survives termination",
        ],
    },
    "governing_law_jurisdiction": {
        "name": "Governing Law / Jurisdiction",
        "definition": "Which law applies and where disputes are heard.",
        "why_it_matters": (
            "Disputes may be forced into a distant or unfavorable venue, "
            "raising the cost of ever pushing back."
        ),
        "signal_language": [
            "governed by the laws of",
            "exclusive jurisdiction of the courts of",
        ],
    },
    "warranty_disclaimer": {
        "name": "Warranty Disclaimer",
        "definition": "Disclaims promises about quality/fitness.",
        "why_it_matters": (
            "You may have little recourse if the product/service doesn't work as expected."
        ),
        "signal_language": [
            "as is",
            "without warranty of any kind",
            "disclaims all warranties",
        ],
    },
    "assignment_or_transfer": {
        "name": "Assignment / Transfer",
        "definition": "Whether the contract can be handed to another party.",
        "why_it_matters": (
            "They may transfer your contract (and your data) to anyone — "
            "including a competitor — without consent."
        ),
        "signal_language": [
            "may assign without consent",
            "successors and assigns",
        ],
    },
    "other": {
        "name": "Other",
        "definition": "Anything materially risky that doesn't fit above.",
        "why_it_matters": "Use sparingly; prefer a specific category when one fits.",
        "signal_language": [],
    },
}


def get_risk_taxonomy() -> dict[str, dict]:
    """Returns the controlled risk vocabulary with definitions and danger rationale."""
    return _TAXONOMY


TAXONOMY_TEXT = """\
# ClauseLens Risk Taxonomy

Each category below has a definition, why it matters to the signer, and signal language.

## auto_renewal
**What it is:** Contract renews automatically unless cancelled in a set window.
**Why it matters:** You can get locked into another full term — and billed — if you miss a narrow notice window.
**Signal language:** "automatically renew", "unless cancelled … days prior", "evergreen term"

## unilateral_change
**What it is:** One side can change the terms (price, scope, rules) at will.
**Why it matters:** The deal you agreed to can shift under you, often with only "notice" or none.
**Signal language:** "we may modify at any time", "in our sole discretion", "continued use constitutes acceptance"

## liability_limitation
**What it is:** Caps or excludes one side's liability if things go wrong.
**Why it matters:** If they harm you, your recovery may be capped far below your actual loss (often to fees paid).
**Signal language:** "limited to the amount paid", "in no event liable", "exclusion of consequential damages"

## indemnification
**What it is:** One party agrees to cover the other's losses/legal costs.
**Why it matters:** A one-sided indemnity can make you pay for their lawsuits or third-party claims.
**Signal language:** "indemnify and hold harmless", "defend against any claims arising from"

## arbitration_or_class_waiver
**What it is:** Disputes go to private arbitration; class actions waived.
**Why it matters:** You give up court, a jury, and the ability to band together — arbitration can favor the drafter.
**Signal language:** "binding arbitration", "waive any right to a jury trial", "no class actions"

## data_sharing_or_privacy
**What it is:** How your data is collected, used, shared, sold, or retained.
**Why it matters:** Your data may be sold or shared with third parties, or kept indefinitely, beyond what you'd expect.
**Signal language:** "share with third parties", "sell or transfer", "for marketing purposes", "retain indefinitely"

## ip_assignment
**What it is:** Ownership of work/ideas transfers to the other party.
**Why it matters:** You can lose rights to what you create — sometimes including work unrelated to the engagement.
**Signal language:** "all work product shall be owned by", "hereby assigns", "including pre-existing IP"

## non_compete_or_non_solicit
**What it is:** Restricts who you can work for or solicit afterward.
**Why it matters:** Can limit your ability to earn a living or take clients/colleagues after you leave.
**Signal language:** "shall not compete", "for a period of … months", "shall not solicit"

## termination_terms
**What it is:** How and when either side can end the contract.
**Why it matters:** One-sided or onerous exit terms can trap you in, or let them drop you, on bad conditions.
**Signal language:** "may terminate for convenience", "with 90 days notice", "no early termination"

## payment_fees_penalties
**What it is:** What you pay, when, and the penalties for lapses.
**Why it matters:** Hidden fees, steep late penalties, or non-refundable terms can cost far more than the headline price.
**Signal language:** "late fee", "non-refundable", "liquidated damages", "interest at … %"

## confidentiality
**What it is:** Obligations to keep information secret.
**Why it matters:** Overbroad or perpetual NDAs can restrict you long after the relationship ends.
**Signal language:** "in perpetuity", "any information disclosed", "survives termination"

## governing_law_jurisdiction
**What it is:** Which law applies and where disputes are heard.
**Why it matters:** Disputes may be forced into a distant or unfavorable venue, raising the cost of ever pushing back.
**Signal language:** "governed by the laws of", "exclusive jurisdiction of the courts of"

## warranty_disclaimer
**What it is:** Disclaims promises about quality/fitness.
**Why it matters:** You may have little recourse if the product/service doesn't work as expected.
**Signal language:** "as is", "without warranty of any kind", "disclaims all warranties"

## assignment_or_transfer
**What it is:** Whether the contract can be handed to another party.
**Why it matters:** They may transfer your contract (and your data) to anyone — including a competitor — without consent.
**Signal language:** "may assign without consent", "successors and assigns"

## other
**What it is:** Anything materially risky that doesn't fit above.
**Why it matters:** Use sparingly; prefer a specific category when one fits.
"""

RUBRIC_TEXT = """\
# ClauseLens Severity Rubric

Severity is directional — judge it for the side chosen in Step 0.
Weigh three things: how much the clause shifts cost/risk/rights/freedom onto that party,
how hard it is to escape or reverse, and how far it departs from market-standard.

## Severity Levels

### critical
Use when there is severe, hard-to-reverse harm: open-ended financial exposure,
loss of major rights, or being locked in with no realistic exit.

Examples: Unlimited or uncapped personal indemnity; assignment of IP unrelated to the work;
total waiver of legal recourse with no opt-out; indefinite obligation with no termination right.

### high
Use when there is a clear, significant, adverse shift that isn't easily escaped or negotiated away.

Examples: One-sided indemnification; liability capped far below likely harm; broad non-compete;
auto-renewal with a long lock-in and steep early-exit penalty.

### medium
Use when there is a meaningful but bounded or commonly-negotiable concern.

Examples: Moderate auto-renewal with a reasonable cancel window; unfavorable-but-standard
termination notice; data shared with third parties for marketing.

### low
Use for minor issues, or standard-but-worth-knowing — flag for awareness, not alarm.

Examples: Governing law in another state; routine confidentiality;
ordinary "as-is" warranty disclaimer.

## Confidence Calibration

- **≥ 0.8**: Language is clear and unambiguous and matches a well-known pattern.
- **0.6–0.8**: Reasonable read, but some ambiguity or context dependence.
- **< 0.6 → set needs_human_review = true**: Vague or cross-referential wording; the real
  effect depends on facts not in the document; or enforceability is jurisdiction-dependent.
  Many clauses (notably non-competes, and liquidated-damages "penalties") are unenforceable
  or limited in some jurisdictions. When enforceability is the open question, lower confidence
  and flag for a human — do not assert the clause is binding.

When in doubt between two severities, pick the lower one and explain the upside risk —
calm and honest beats alarmist.
"""
