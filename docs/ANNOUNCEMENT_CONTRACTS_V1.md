# Announcement Template – ULog Contracts v1.0.0 Freeze

Use this template for Slack when announcing the contracts freeze.

---

## Short Slack announcement

**Channel:** #discussions

> :tada: *ULog contracts v1.0.0 are now frozen*  
>  
> We’ve just tagged **`contracts-v1.0.0`**, covering the Core/API, LLM, Agentic, and Computer Vision schemas plus the shared controlled vocabulary.  
>  
> What this means:
> - Contracts are **stable** – engineering and QA can rely on the current shapes.
> - Any changes now follow the semantic versioning and change process in `docs/VERSIONING.md` and `docs/CHANGE_PROCESS.md`.
> - The normalization-first model (`meta.*`, `_common.json`, vocabulary) is documented with worked examples in `docs/RELEASE_NOTES.md`.
>  
> Next steps:
> - If you produce logs, align your emitters to these contracts.
> - If you need a contract change, please open a proposal following `docs/CHANGE_PROCESS.md`.
>  
> Links:
> - Release notes: `docs/RELEASE_NOTES.md`
> - Tag: `contracts-v1.0.0` on the main repository
> - Release checklist: `docs/RELEASE_CHECKLIST.md`
