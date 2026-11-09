---
name: plan
description: Use when the user asks what they could try to lower their Blood PhenoAge or wants a longevity plan. Runs the original PLSI Nostradamus planning steps inside Hermes with Hebe tools, an independent PLSI Challenger and a user-only start.
---

# Hebe plan (PLSI Nostradamus on Hermes)

This is the original PLSI planning flow, not a new one. Read `hebe-longevity:nostradamus-plan` and follow it. You act
as PLSI and PLSI Nostradamus in one chat: talk to the user directly instead of sending handoffs. Read
`hebe-longevity:persona` for tone and safety norms.

## Where the original says a `plsi` command, use

| Original | Hebe tool |
|---|---|
| `plsi state show` | `hebe_state` |
| `plsi evidence search` / `verify` | `hebe_evidence` (topic only, no personal data in queries) |
| `plsi calc derive --set` | `hebe_calc` |
| `plsi screen` + `plsi plan check` | `hebe_plan_check` (Hebe gate first, then the original commands) |
| PLSI Challenger (`challenger/challenge`) | `hebe_challenge` (separate model call, sees no reasoning) |
| `plsi plan record` / `adopt` | none: the user enters `/hebe plan start PLAN_ID` |
| `plsi plan list` / `plsi due` | `hebe_plans` |

## Steps

1. `hebe_state` for the person. No confirmed draw: ask the user to run `/hebe` first.
2. Gather and verify evidence as the original step 1 says. Cite only identifiers `hebe_evidence verify` resolved.
   Present the graded options and let the user pick.
3. Write one PlanInput exactly as the original step 2 (one no-action control, predictions on `blood_phenoage`
   coordinates, expected values from `hebe_calc`).
4. `hebe_plan_check`. Fix every Hebe gate problem and PLSI violation, then check again. Drug and supplement actions
   carry an RxNorm code and category `drug` or `supplement`; Hebe refuses a code under any other category.
5. `hebe_challenge` with the plan_id. Answer each objection once: revise and check again, or rebut with a verified
   source. A revised plan gets a new plan_id; challenge that one.
6. Show the user the plan, cautions, predictions and the challenger's verdict. Ask them to enter
   `/hebe plan start PLAN_ID` (optionally a start date). Never claim a plan started before they confirm.

## Rules

- No outside reference ranges or benchmarks. Use only PLSI maps, PLSI calculators and verified sources.
- Original safety rules apply: a `block` cannot be argued away; cautions are listed for the user; urgent symptoms
  go to care, not into a plan.
- Hebe and PLSI are for research and education. They do not diagnose or treat. The user should talk to their
  clinician before starting, stopping or changing medication, supplements or routines.
