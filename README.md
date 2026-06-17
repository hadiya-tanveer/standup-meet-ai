<div align="center">

<img src="https://img.icons8.com/fluency/96/bot.png" width="90" alt="Standup Meet AI logo"/>

# Standup Meet AI

</div>


## Overview

**Standup Meet AI** is an intelligent automation system designed to streamline daily standup meetings conducted via Google Meet. Instead of relying on manual facilitation, the project uses a collection of specialized agents to schedule, orchestrate, and manage meetings while integrating seamlessly with organizational tools such as **Google Calendar**, **Jira**, and **Slack**.

The system ensures that all participants remain engaged, issues are surfaced and resolved efficiently, and meeting summaries are generated automatically for future reference. Beyond simple meeting automation, it introduces adaptability and intelligence to the entire workflow:

- **Preparation is automated** — Meetings are scheduled in advance and relevant Jira issues are aggregated so participants enter the call with context already in place.
- **Facilitation is dynamic** — The bot randomly calls participants, adapts to unexpected absences, and ensures everyone has a chance to speak without disrupting the flow.
- **Collaboration is enhanced** — Overdue tasks, inactive tickets, and blockers are automatically highlighted, while real-time issues are analyzed for solutions or escalations.
- **Post-meeting follow-up is handled** — Summaries are distributed to participants and stakeholders, reducing the need for manual note-taking and ensuring accountability.

In essence, the project transforms the traditional standup into a hands-free, intelligent, and productive session — freeing team members to focus on meaningful discussions rather than logistics. Over time, the system can be further improved with AI-powered search, retrieval-augmented generation (RAG) for issue analysis, and advanced integration with additional collaboration tools.

---

## Agent Overview

The system is powered by **8 specialized agents**, each responsible for a distinct part of the standup lifecycle, all coordinated by a central Orchestrator.

| # | Agent | Description |
|---|-------|--------------|
| 1 | 🗓️ **Scheduler Agent** | Automates recurring standup scheduling and sends calendar invites via Google Calendar. |
| 2 | 📋 **Context Aggregator Agent** | Surfaces overdue/inactive Jira tickets and assigns new tasks to keep discussions focused. |
| 3 | 🚪 **Absence Manager Agent** | Detects absentees in real time and sends automated Slack reminders to prompt them to join. |
| 4 | 🎙️ **Facilitator Agent** | Acts as the virtual host in Google Meet, randomly selecting speakers and managing dynamic attendance. |
| 5 | 🛠️ **Issue Analyzer Agent** | Listens for blockers raised during the meeting and suggests real-time solutions or workarounds. |
| 6 | 🗂️ **Issue History Agent** | Tracks previously discussed issues to avoid repetition across standups. |
| 7 | 📄 **Summary Agent** | Generates full meeting and per-participant summaries (Did, Plan to Do, Issues Faced). |
| 8 | 🧭 **Orchestrator Agent** | Central coordinator that integrates all agents with Google Meet and manages the end-to-end flow. |

---

## Tool Stack

<div align="center">

| ![CrewAI](https://img.shields.io/badge/CrewAI-FF6B35?style=for-the-badge&logo=robot&logoColor=white) | <img src="https://img.icons8.com/color/48/slack-new.png" width="40"/> | <img src="https://img.icons8.com/fluency/48/lightning-bolt.png" width="40"/> | <img src="https://img.icons8.com/color/48/jira.png" width="40"/> |
|:---:|:---:|:---:|:---:|
| **CrewAI** | **Slack API** | **Groq API** | **Jira API** |

</div>

## Demo

<div align="center">

https://github.com/user-attachments/assets/1df604ea-853f-4015-afb1-992f04fe7b4a
</div>

---

### Disclaimer

This project, **Standup Meet AI**, was developed as part of an **internship program**. It serves as a demonstration of applied multi-agent AI orchestration and tool integration, and may be extended further for production use.
