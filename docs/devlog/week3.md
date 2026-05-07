# Week 3 Devlog

Week 3 now covers Day 19-26 only.
The previous version of this file had grown through Day 36, which made the weekly timeline misleading.
Source-discovery hardening moved to `week4.md`, and staging deployment work moved to `week5.md`.

## Day 19-23 - School Exam Pause

### Status
- Active feature development paused for about one week because of the school exam period.
- No major code changes were made during this window.
- The project was intentionally left at the previous stable backend checkpoint rather than starting partially finished work.

### Why this is recorded
This pause explains the gap between development sessions and keeps the project timeline honest.
The project was not blocked technically; development capacity was temporarily redirected to coursework and exams.

### Outcome
- No architecture changes.
- No new features.
- No test baseline changes.
- Development resumed after exams with the existing profile, dashboard, and job-action APIs still stable.

---

## Day 24 - Frontend Environment Recovery and Dashboard MVP

### Focus
Restart development after the exam pause and begin turning the product backend into a visible user workflow.

### What was done
- Verified and repaired the local development environment.
- Recreated the Python virtual environment with Python 3.13 after the previous Python 3.14 environment exposed `_ctypes` DLL failures.
- Added a Vite/React frontend under `frontend/`.
- Added FastAPI CORS support for local frontend development from:
  - `http://localhost:5173`
  - `http://127.0.0.1:5173`
- Added `.gitignore` rules for frontend generated artifacts.
- Built the first frontend dashboard MVP with:
  - profile setup form
  - dashboard summary panel
  - recommendation run trigger
  - recent run loading
  - saved and applied job previews
  - job action buttons for save, applied, and dismiss

### Validation
- `npm run build` -> passed
- `pytest -q` -> **124 passed**

### Result
InternLens gained a browser-based entry point for the stored-profile recommendation flow.
The UI could exercise the main product loop: create or load a profile, run recommendations, inspect results, and record job actions.

---

## Day 25 - Frontend Session Persistence and API Status

### Focus
Make the new frontend less fragile during manual testing and demos.

### What was done
- Added local browser session persistence using `localStorage`.
- Restored profile form data, active profile ID, selected recommendation run, and recommendation filter after refresh.
- Added API health checking against `/health`.
- Added an online/offline/checking badge in the UI.
- Added a manual `Check API` action.
- Improved job-action refresh behavior so the UI avoids unnecessary run reloads when no run is selected.

### Validation
- `npm run build` -> passed
- `pytest -q` -> **124 passed**

### Result
The frontend now survives page refreshes more gracefully.
Users can tell whether the backend is reachable without opening browser developer tools or checking terminal logs.

---

## Day 26 - Recommendation Results UI

### Focus
Make recommendation output easier to scan and act on.

### What was done
- Added recommendation filters:
  - `All`
  - `Apply Now`
  - `Apply Later`
  - `Skip`
- Added per-filter counts.
- Changed the frontend recommendation request to use `include_debug=true` so the UI can show score and action-label details.
- Split recommendation cards into clearer frontend components:
  - `JobCard`
  - `ScoreDial`
  - `EvidenceList`
- Added visual score dials.
- Added clearer action pills for `Apply Now`, `Apply Later`, and `Skip`.
- Added separate evidence sections for fit reasons and watchouts.
- Added stronger visual treatment for high-priority and skipped jobs.

### Validation
- `npm run build` -> passed
- `pytest -q` -> **124 passed**

### Result
Recommendation results became easier to inspect.
The UI better communicates both the ranking decision and the next action a user should take.

---

## Week 3 Snapshot

### Current project state
- Backend profile, recommendation, job-action, and dashboard APIs remain stable.
- The React frontend now supports the core stored-profile workflow.
- The recommendation results UI is usable enough for demos.
- Python development is stabilized on Python 3.13.

### Latest quality checkpoint
- Frontend production build passing with `npm run build`.
- Backend test suite stable at **124 passed** at the end of Day 26.

### Remaining next steps
- Improve frontend empty states and error messages.
- Add clearer applied/saved/dismissed state transitions in recommendation cards.
- Add screenshots or a short demo walkthrough once the UI flow stabilizes.
- Consider adding a lightweight frontend lint/test setup.
