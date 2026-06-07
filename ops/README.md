# NailAI Engineering Ops

This folder stores the operational knowledge that should survive across agents, teammates, branches, and Hackathon sessions.

## Structure

- `handoff/PROJECT_REPORT.md`: stage report for teammates, mentors, and demos.
- `handoff/FRONTEND_BACKEND_INTEGRATION.md`: frontend/backend API contract and debugging guide.
- `handoff/STANDARD_ENGINEERING_GUIDE.md`: standardized engineering handoff guide.
- `manual/ENGINEERING_OPERATIONS.md`: product-aligned engineering handbook.
- `manual/HARNESS_CHECKS.md`: repeatable verification commands and checks.
- `issues/KNOWN_ISSUES.md`: bugs, symptoms, root causes, fixes, and prevention notes.
- `templates/ISSUE_RECORD.md`: template for adding new problem records.

## How To Use

Before starting a task, read `AGENTS.md` and skim the relevant manual section. When a real problem is found, add a short record to `issues/KNOWN_ISSUES.md` with:

- symptom
- cause
- fix
- prevention harness

This keeps the project from rediscovering the same problems under time pressure.
