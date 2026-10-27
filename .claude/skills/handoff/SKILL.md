---
name: handoff
description: Compact the current conversation into a handoff document for another agent to pick up. 한국어 요청 예 — "인수인계해줘", "인수인계 문서 만들어줘", "다른 PC 에서 이어서 하게 정리해줘".
argument-hint: "What will the next session be used for?"
---

<!-- 원본: github.com/mattpocock/skills  skills/productivity/handoff (49dd158, 2026-10-19 복사, MIT).
     고친 곳: 저장 위치 한 줄 — 원본은 이 PC 의 임시 폴더라서 노트북 · 집 PC 에서 못 읽는다.
     그리고 "작업 폴더" 문단 (2026-10-20 추가).
     그리고 2026-10-21: disable-model-invocation 줄을 지우고 설명 끝에 한국어 요청 예를 붙였다(말로 불러도 돌게).
     그리고 2026-10-28: "Any command this doc tells the next session to run" 문단 — 넘길 명령은 먼저 돌려 보고, 다른 PC 할 일은 맞춤 스크립트부터 본다.
     C:\dev\vibe-study 는 비공개 저장소이고 사용자 설정 훅이 세 PC 사이에서 자동으로 맞춘다. -->

Write a handoff document summarising the current conversation so a fresh agent can continue the work. Save to `C:\dev\vibe-study\handoff\` as `YYYY-MM-DD-HHMM-<short-topic>.md` (shared across the user's three PCs by auto-sync; private repo) - not the current workspace, which is published.

Include a "suggested skills" section in the document, naming which skills the next agent should call the Skill tool for.

Name the **work folder** (the repo the next session will edit) near the top of the document, with this line for the next agent: "Before writing anything there, check whether this session was opened in that folder. If not, say so first: that repo's own auto-save and guard hooks run only in sessions opened in it, so edits from here are neither committed nor pushed unless you do it explicitly (or the user reopens the session there)." For example `c:\galleypark` has its own `.claude/hooks/auto-save.sh`, and the user-level hook skips it.

Do not duplicate content already captured in other artifacts (specs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

Any command this doc tells the next session to run, run it yourself first on this machine and paste its actual output as the expected result. For an absence check, also show it fires on the old state, and match the syntax (`^key:`), not the bare word — change notes mention removed tokens. Before writing "on the other PC, run X", check `C:\dev\vibe-study\tools\pc-sync.sh` and `git-auto-sync.sh` for what X touches: it may already run on its own after a pull.

Redact any sensitive information, such as API keys, passwords, or personally identifiable information.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.
