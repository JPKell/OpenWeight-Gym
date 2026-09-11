# Local inference for writers

## Where the work happens

Everything happens on your own machine. The model reads what you wrote and answers there, with nothing uploaded and no account needed, and no network involved at any point. The hardware is yours to provide: that is the trade for keeping the work where you made it.

## What it costs

The cost is hardware you already own and the patience of a slower answer. On your own machine the fan will spin, the model loads for a moment, and nothing leaves the room.

---

## Provenance

- Export format version: 1.0
- Content type: article 1.0
- Workflow: standard 1.0
- Units: 2 committed of 2 planned
- Words: 80

### Requirement coverage

| Requirement | Class | Satisfied | Decided by | Checked by | Grounded in |
| --- | --- | --- | --- | --- | --- |
| R-001 — The unit must be explicit about where inference happens. | blocking | yes | deterministic_check | contains any of: 'own machine' | brief: “inference runs entirely on the reader's own machine” |
| R-002 — The unit should keep a plain register. | advisory | no | unsatisfied | no deterministic check — evaluated by audit only | brief: “no document content is uploaded anywhere” |

A requirement decided by `audit` is guaranteed by model review, not a deterministic check: nothing mechanical settled it, and this table says so rather than implying otherwise. The *grounded in* column is the verbatim span of the author material the requirement was compiled from — the claim and its evidence side by side, so a requirement the material does not support is visible as exactly that.

### Units

#### U-01 — Where the work happens

- Version: 2
- Committed: 2026-09-11T06:40:37.399668+00:00
- Content hash: sha256:eeaa0bce9958229471e7cc1e0924c05790a97ee00cadc3325d380d0dc2089777
- Words: 47
- draft attempt 1 (round 0): completed via fake, model fake/gemma4:12b@sha256:1212121212121212121212121212121212121212121212121212121212121212, prompt stages.draft.write 1.0.0
- repair attempt 2 (round 0): completed via fake, model fake/qwen3.5:9b-q8_0@sha256:9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b, prompt stages.repair.fix 1.0.0
  - degradation: model_switch: unloaded ollama/gemma4:12b to load ollama/qwen3.5:9b-q8_0 (0 ms)
- repair attempt 3 (round 0): completed via fake, model fake/qwen3.5:9b-q8_0@sha256:9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b, prompt stages.repair.fix 1.0.0
  - degradation: model_switch: unloaded ollama/gemma4:12b to load ollama/qwen3.5:9b-q8_0 (0 ms)
- draft attempt 1 (round 0): completed via fake, model fake/gemma4:12b@sha256:1212121212121212121212121212121212121212121212121212121212121212, prompt stages.draft.write 1.0.0
- audit_fast attempt 1 (round 0): completed via fake, model fake/qwen3.5:9b-q8_0@sha256:9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b, prompt stages.audit_fast.review 1.1.0
  - degradation: model_switch: unloaded ollama/gemma4:12b to load ollama/qwen3.5:9b-q8_0 (0 ms)
- critique attempt 1 (round 0): completed via fake, model fake/qwen3.5:9b-q8_0@sha256:9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b, prompt stages.critique.judge 1.0.0
  - degradation: model_switch: unloaded ollama/gemma4:12b to load ollama/qwen3.5:9b-q8_0 (0 ms)
- revise attempt 1 (round 1): completed via fake, model fake/qwen3.5:9b-q8_0@sha256:9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b, prompt stages.revise.improve 1.0.0
- audit_fast attempt 1 (round 1): completed via fake, model fake/qwen3.5:9b-q8_0@sha256:9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b, prompt stages.audit_fast.review 1.1.0
- critique attempt 1 (round 1): completed via fake, model fake/qwen3.5:9b-q8_0@sha256:9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b, prompt stages.critique.judge 1.0.0

#### U-02 — What it costs

- Version: 1
- Committed: 2026-09-11T06:40:37.328988+00:00
- Content hash: sha256:3f0b6f969aa84e7d09e863eeae85e1933a746d97f3f5dc57538bc5816c4a94ec
- Words: 33
- draft attempt 1 (round 0): completed via fake, model fake/gemma4:12b@sha256:1212121212121212121212121212121212121212121212121212121212121212, prompt stages.draft.write 1.0.0
  - degradation: model_switch: unloaded ollama/qwen3.5:9b-q8_0 to load ollama/gemma4:12b (0 ms)
- draft attempt 1 (round 0): completed via fake, model fake/gemma4:12b@sha256:1212121212121212121212121212121212121212121212121212121212121212, prompt stages.draft.write 1.0.0
  - degradation: model_switch: unloaded ollama/qwen3.5:9b-q8_0 to load ollama/gemma4:12b (0 ms)
- audit_fast attempt 1 (round 0): completed via fake, model fake/qwen3.5:9b-q8_0@sha256:9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b, prompt stages.audit_fast.review 1.1.0
  - degradation: model_switch: unloaded ollama/gemma4:12b to load ollama/qwen3.5:9b-q8_0 (0 ms)
- critique attempt 1 (round 0): completed via fake, model fake/qwen3.5:9b-q8_0@sha256:9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b, prompt stages.critique.judge 1.0.0
  - degradation: model_switch: unloaded ollama/gemma4:12b to load ollama/qwen3.5:9b-q8_0 (0 ms)
