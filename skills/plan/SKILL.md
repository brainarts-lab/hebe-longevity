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

1. Find the person. If the user names none, call `hebe_preview` with action `status` and use the only saved person,
   or ask which one. `alex-demo` is a fictional demo person made for trying Hebe: plan for it right away, say once
   that it is demo data, and never ask the user for real results first. No saved person at all: tell the user to
   open **Hebe** in the sidebar (or enter `/hebe`) and try the demo.
2. `hebe_state` for the person. Name the markers and the PhenoAge it shows before suggesting anything.
3. Gather and verify evidence as the original step 1 says. Cite only identifiers `hebe_evidence verify` resolved.
   Never cite web pages or anything you did not verify. Present 2 to 4 graded options and let the user pick.
4. Write one PlanInput exactly as the original step 2 (one no-action control, predictions on `blood_phenoage`
   coordinates, expected values from `hebe_calc`).
5. `hebe_plan_check`. Fix every Hebe gate problem and PLSI violation, then check again. Drug and supplement actions
   carry an RxNorm code and category `drug` or `supplement`; Hebe refuses a code under any other category.
6. `hebe_challenge` with the plan_id. Answer each objection once: revise and check again, or rebut with a verified
   source. A revised plan gets a new plan_id; challenge that one.
7. Show the plan, cautions, predictions and the challenger's verdict in short bullets. Tell the user to start it on
   the **Plans** tab of the Hebe page, or with `/hebe plan start PLAN_ID`. End with a paragraph that is exactly
   `::hebe{view="plans"}`. Never claim a plan started before they confirm.

Do not replace these steps with general health advice. If a tool fails, say which step failed and stop.

## Rules

- No outside reference ranges or benchmarks. Use only PLSI maps, PLSI calculators and verified sources.
- Original safety rules apply: a `block` cannot be argued away; cautions are listed for the user; urgent symptoms
  go to care, not into a plan.
- Hebe and PLSI are for research and education. They do not diagnose or treat. The user should talk to their
  clinician before starting, stopping or changing medication, supplements or routines.
