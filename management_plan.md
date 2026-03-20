# Haven: Mental Load Relief App - Management Plan

## Context
Modern life demands managing an overwhelming number of tasks, schedules, and rapid thoughts. Users often experience "mental load" or "decision fatigue" trying to track everything. Current tools (like basic to-do lists) lack intelligent structuring. Haven aims to solve this by providing an Agentic AI that actively helps users unpack their thoughts and automatically organizes them into actionable, stress-free items.

## Goal
To build a fully functional cross-platform (Android-first) application in Python that uses Agentic AI to ingest unstructured user thoughts, validate their feelings, and output logically categorized tasks to reduce cognitive overload.

## Constraints
1. **Technical Foundation:** Must be built in Python using Flet for the UI and LangChain for the core AI logic.
2. **Environment:** Must be deployable as a standalone Android APK.
3. **API Dependency:** Requires a valid API Key (e.g., Google Gemini) securely managed within the app or injected during the build process, so it works on mobile devices without relying on local [.env](file:///c:/Users/perdo/Documents/GitHub/haven-mental-load-relief/.env) files.
4. **Performance:** The AI must respond reasonably quickly on mobile devices to prevent UI blocking or freezing.

## Features
- **Thought Dump Interface:** A conversational, calming UI for users to quickly dump their thoughts via text.
- **Agentic AI Processing:** An LLM-powered background agent to parse, empathize, and structure chaotic thoughts.
- **Task Management View:** An organized dashboard for categorized tasks (e.g., Now, Later, Delegate).
- **Settings / Config Screen:** An interface to input or manage the API key directly on the device, ensuring the app can connect to the AI provider. *(Implementing this will fix why your Send button did nothing!)*

## Deliverables
1. `management_plan.md` - The foundational vision document (this file).
2. The core Python application codebase ([main.py](file:///c:/Users/perdo/Documents/GitHub/haven-mental-load-relief/main.py), `app/` modules, and UI assets).
3. A fully functioning local execution environment (via `.venv`).
4. A deployable Android `.apk` file that functions standalone on a mobile device and correctly communicates with the AI.

## Validation & Verification
1. **Automated Verification:** Logic tests ensuring the LangChain agent correctly parses complex thought dumps into structured text.
2. **Manual UX Validation:** Real-world testing of the UI workflow on an physical Android device to confirm responsiveness and usability.
3. **Build Verification:** Successful `flet build apk` execution without missing dependencies or silent crashes on mobile.

## Definition of Done (DoD)
- The app can be built into an APK without compiler errors.
- The user can open the app on an Android phone, securely input their API key, input their thoughts, and successfully receive a structured AI response.
- The UI handles loading states gracefully (the app does not freeze when waiting for the AI response).
- All code is committed and well-documented.
