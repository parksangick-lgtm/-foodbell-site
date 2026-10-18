---
name: handoff
description: Compact the current conversation into a handoff document for another agent to pick up.
argument-hint: "What will the next session be used for?"
disable-model-invocation: true
---

<!-- 원본: github.com/mattpocock/skills  skills/productivity/handoff (49dd158, 2026-10-19 복사, MIT).
     고친 곳은 저장 위치 한 줄뿐 — 원본은 이 PC 의 임시 폴더라서 노트북 · 집 PC 에서 못 읽는다.
     C:\dev\vibe-study 는 비공개 저장소이고 사용자 설정 훅이 세 PC 사이에서 자동으로 맞춘다. -->

Write a handoff document summarising the current conversation so a fresh agent can continue the work. Save to `C:\dev\vibe-study\handoff\` as `YYYY-MM-DD-HHMM-<short-topic>.md` (shared across the user's three PCs by auto-sync; private repo) - not the current workspace, which is published.

Include a "suggested skills" section in the document, naming which skills the next agent should call the Skill tool for.

Do not duplicate content already captured in other artifacts (specs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

Redact any sensitive information, such as API keys, passwords, or personally identifiable information.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.
