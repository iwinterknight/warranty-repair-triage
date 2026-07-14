# Documentation Map & Self-Composing Guide

This project's documentation is **modular** — many small docs, each at the altitude of what it describes.
The parts alone don't read as one story; this file is (1) the **human-readable map** of what exists and how
it fits, and (2) a **load-bearing compose instruction** so any LLM pointed at `docs/` can assemble the full
human-readable narrative on demand — optionally focused by the reader.

> **The single rule:** to understand or (re)generate the whole picture, start here. The README.md at the
> repo root is the *product* front door (how to run it); **this** file is the *documentation* front door.

---

## 1. The picture — documentation as layers

Each doc answers one question, for one reader, and changes at its own rate.

| Layer | Doc(s) | Question it answers | Reader | Change-rate |
|---|---|---|---|---|
| **Front door (product)** | `../README.md` | how do I run it? | evaluator | stable |
| **Front door (docs)** | `docs/README.md` *(this file)* | what docs exist & how do they compose? | everyone + any LLM | stable |
| **Contract** | `schema/extraction_schema.json`, `schema/schema_spec.yaml` | what we extract & what each field *means* | engineer + LLM at runtime | versioned |
| **Decisions — why** | `docs/decisions/` (ADRs) + `../CLAUDE.md` (locked index) | why we chose this over that | reviewer / engineer | append-only / immutable |
| **Design — how** | `docs/sdd.md` | how it's built (components, interfaces, build order) | engineer | living |
| **Process — how we got here** | `docs/discussion-notes.md`, `architecture-notes.md`, `build-notes.md`, `deploy-notes.md` | the running decision/bug log | us / transparency | append-only |
| **AI disclosure** | `../LLM-USAGE.md` | how AI tools were used to build it | evaluator | updated at build |
| **Evidence / reference** | `eda/` (notebook + artifacts), `docs/assignment/` (the brief) | the data basis & the original ask | engineer / reviewer | frozen |
| **Synthesis** | the final project doc *(composed)* + `docs/project-doc-outline.md` (its seed) | the polished narrative for the interview | interviewer | composed at end |

**How the layers relate:** the **contract** rests on the **evidence** (EDA); **decisions → design → process**
form the build spine; the **process logs** feed both the decisions and the **synthesis**; the **synthesis**
is composed *from all of the above* — which is what section 3 automates.

## 2. Reader paths (use the docs without reading everything)

- *"I just want to run it"* → `../README.md`
- *"Why is it built this way?"* → `docs/decisions/` (ADRs), then `docs/sdd.md`
- *"What does it extract, and what do the values mean?"* → `schema/`
- *"How was AI used to build it?"* → `../LLM-USAGE.md`
- *"How did the thinking evolve?"* → `docs/discussion-notes.md`
- *"Give me the whole story, coherently"* → run **section 3** below.

## 3. Composing the complete human-readable picture — LOAD-BEARING (for an LLM)

> Point any capable LLM at the `docs/` folder and give it this section. It will assemble the modular docs
> into one coherent, human-readable document. This instruction *is* the build recipe for the narrative —
> keep it accurate as docs are added.

**Instruction to the composing LLM:**

1. **Read the manifest** in section 4 to learn every document, its role, and its `compose-order`.
2. **Read the source docs in `compose-order`.** Treat `schema/`, `docs/decisions/`, and `docs/sdd.md` as
   authoritative; treat `docs/*-notes.md` as chronological context.
3. **Synthesize one narrative** with these sections, in order:
   1. Problem & framing (from the assignment brief + SDD §1)
   2. Key decisions & rationale (from `docs/decisions/` ADRs — one crisp paragraph each)
   3. Architecture & data flow (SDD §2–3, §7.x)
   4. The data & the schema/contract (`schema/`, EDA highlights)
   5. Build, shortcuts & what's next (SDD build order + `build-notes.md`)
   6. AI usage (`LLM-USAGE.md`)
   7. Scaling & AWS deployment plan (SDD §12 + ADR-0006/0007/0008)
4. **Rules of synthesis:**
   - Prefer **ADRs** for *why*, the **SDD** for *how*, the **notes** for *chronology*.
   - On conflict, the **most recent ratified** statement wins (SDD status = RATIFIED; ADR status = Accepted;
     a "Superseded by" ADR loses to its successor).
   - **Never invent.** Every claim must trace to a source doc; if something is missing, say so — don't fill gaps.
   - Keep it human-readable: prose over tables where a human would prefer prose; define jargon on first use.
5. **Honor reader focus directives.** If the reader appends instructions (e.g., *"focus on the aggregation
   design; just enumerate the AWS parts; skip the process logs"*), apply them: **expand** the named parts,
   **summarize or enumerate** the rest, **omit** what's excluded — while keeping the result coherent.

**Default invocation:** *"Read `docs/README.md` section 3 and compose the full project narrative from the
`docs/` folder."*
**Focused example:** *"…compose the narrative, but focus on Decisions E–G (aggregation, providers, ingest)
and only enumerate the rest."*

## 4. Manifest (machine- and human-readable)

`compose-order` is the reading order for section 3; `role` and `authority` guide synthesis.

```yaml
docs:
  - id: brief
    path: docs/assignment/Honda-Technical-Take-Home-Assignment.docx
    role: the original ask
    authority: frozen
    compose-order: 1
  - id: readme
    path: README.md
    role: product front door / setup
    authority: living
    compose-order: 2
  - id: sdd
    path: docs/sdd.md
    role: design — how it's built
    authority: authoritative
    compose-order: 3
  - id: adrs
    path: docs/decisions/
    role: decisions — why (immutable trail)
    authority: authoritative
    compose-order: 4
  - id: schema
    path: schema/
    role: extraction contract + semantic descriptions
    authority: authoritative
    compose-order: 5
  - id: eda
    path: eda/
    role: evidence the schema was derived from
    authority: frozen
    compose-order: 6
  - id: process-logs
    path: [docs/discussion-notes.md, docs/architecture-notes.md, docs/build-notes.md, docs/deploy-notes.md]
    role: chronological decision/bug log
    authority: context
    compose-order: 7
  - id: llm-usage
    path: LLM-USAGE.md
    role: AI-tool usage disclosure
    authority: authoritative
    compose-order: 8
  - id: locked-index
    path: CLAUDE.md
    role: terse index of locked decisions + working agreement
    authority: authoritative
    compose-order: 9
  - id: project-doc-outline
    path: docs/project-doc-outline.md
    role: seed/talking-point bank for the final synthesis
    authority: context
    compose-order: 10
```

*Keep this manifest current when adding a doc — it's what makes section 3 reliable.*
