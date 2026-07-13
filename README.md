# Friday AI — Build Week 2026 Edition

Friday AI is a local desktop AI assistant for Windows that combines conversational AI, voice interaction, browser automation, screen understanding, memory, and controlled computer actions.

> This branch is the dedicated **OpenAI Build Week 2026** development line. The existing project is being upgraded into a safer, more reliable, and more transparent desktop agent.

## Project goal

Most desktop assistants can answer questions, but they cannot safely complete real work. Friday AI aims to bridge that gap by combining natural-language interaction with visible plans, explicit permission checks, controlled execution, verification, and recoverable changes.

## Current capabilities

- Voice and text interaction
- Local Windows desktop control
- Browser automation through Playwright
- Screen capture and computer-vision utilities
- Search and web-content extraction
- Local memory support
- File and application actions
- Audio and notification integration

## Build Week upgrade direction

The Build Week edition will focus on a controlled engineering workflow:

1. Select an approved project workspace.
2. Inspect the project without modifying it.
3. Generate a clear implementation plan.
4. Show affected files, commands, risks, and rollback steps.
5. Require approval before sensitive actions.
6. Apply bounded changes only inside the workspace.
7. Run verification commands and tests.
8. Present the final diff and result.
9. Restore the checkpoint when verification fails.

## Safety principles

- No silent destructive actions
- No access outside the approved workspace
- No credential collection or exposure
- No command execution without validation
- Explicit approval for sensitive or dangerous operations
- Activity history and human-readable results
- Fail-closed behavior when permission context is missing

## Technology

- Python
- Google GenAI integration in the current base project
- Playwright
- OpenCV and MSS
- PyAutoGUI, PyWinAuto, and Windows audio APIs
- Local JSON/file-based memory utilities

The Build Week branch will add a meaningful OpenAI-powered workflow rather than using OpenAI only as a basic chat replacement.

## Installation

### Requirements

- Windows 10 or Windows 11
- Python 3.11 recommended
- A microphone for voice features
- A supported browser

### Setup

```powershell
git clone https://github.com/SanketMaurya0408/friday-ai.git
cd friday-ai
git checkout build-week-2026
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python setup.py
```

Copy `.env.example` to `.env`, add only the API keys required by the features you enable, and never commit `.env`.

Run the application:

```powershell
python main.py
```

## Planned submission material

- Architecture diagram
- Permission-flow screenshots
- Two-to-three-minute demo video
- Installation walkthrough
- Before/after Build Week changelog
- Verification report

## Build Week work log

All competition-specific work should be committed to the `build-week-2026` branch so that prior work and new work remain clearly separated.

See [`BUILD_WEEK_PLAN.md`](BUILD_WEEK_PLAN.md) for the execution roadmap.

## Status

**Active development — not yet ready for final judging.**

## Author

Sanket Maurya
