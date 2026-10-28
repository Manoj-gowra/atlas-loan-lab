# ADR-001: The borderline investigator runs on the most capable tier; intake stays on the compact tier

Status: accepted
Date: 2026-09-22 · Deciders: solution architect, Head of Commercial Lending, Credit Committee chair

## Context
The mandate is officer time on the routine majority (R1-R5). About three applications in ten are
borderline (a rule inside its referral band). Those are the cases where a shallow answer costs real money:
a missed tax lien or a wrong DSCR reaches the credit committee. Intake runs on every application with an
officer waiting; the investigator runs only on flagged cases and nobody watches it live.

## Decision
The investigator (coordinator + three specialists) uses the most capable tier with deep retrieval and full
reasoning effort. Intake, the policy check and drafting stay on the compact and mid tiers.

## Why
- The investigator's path depends on what it finds (lesson 1.2), it weighs conflicting evidence (stated vs
  verified EBITDA) and its mistakes are expensive; volume is low by construction, so the higher price per
  call is paid on a small share of cases.
- Intake is a bounded transformation. The A/B test showed that a few-shot prompt brings the compact tier to
  100% field accuracy on messy forms at about $0.025 per application, while upgrading intake's model to
  reach the same accuracy cost about 19% more per application. A prompt fix beat a model upgrade.
- Evaluation: borderline cases average about $0.055 each, routine cases about $0.012; the overall average
  is about $0.025 against the $0.05 budget (R5), and p95 latency is about 18 seconds against 60 (R1).

## What it gives up
- A borderline case costs about four times a routine one and takes about twice as long. Accepted because it
  is a minority of cases, nobody waits on it live, and the average stays at half the budget.
- The investigator's tier reaches Bedrock later than the API. Until it is available there, the documented
  exception is to stay on the previous tier inside AWS (constraint C2), never to call another platform.

## Alternatives considered
- One mid tier for every component: simpler, but intake would cost more for no accuracy gain and the
  investigator would give shallower answers on exactly the expensive cases. Rejected.
- The most capable tier everywhere: about twice the average cost for no measured gain on routine cases,
  and slower intake for an officer who is waiting. Rejected.
- No investigator (refer every borderline case to an officer as today): cheapest, but it leaves the
  judgment-heavy work unprepared, which is the need discovery found. Rejected.

## For executives
Routine applications stay fast and cheap; we spend more only on the three in ten that are borderline,
where a wrong call is expensive. Average running cost is about half the agreed budget.

## Revisit when
The share of borderline cases rises above 40%, the average cost per application passes $0.04, or a new
model generation changes the price of either tier.
