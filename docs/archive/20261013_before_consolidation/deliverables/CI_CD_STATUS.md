# CI/CD implementation and execution

The [GitHub workflow](../.github/workflows/mideval-evidence.yml) executes two Python 3.11 test jobs on **Windows and Ubuntu**, followed by a dependent **continuous-delivery job**. Pushes to main/gpt/**, pull requests and manual dispatch trigger it. Permissions are read-only; credentials are not persisted; timeouts, duplicate-run cancellation and 14-day artifact retention are configured.

| Stage | Implemented checks | Execution boundary |
| --- | --- | --- |
| Portable evidence, Windows/Ubuntu | 168 portable tests, seven source/metadata guards, 372 saved records, 228 comparator probes, preview, no-inference plan and 62 live HTTP checks | Shared runner passes locally; hosted results recorded in Actions |
| Streamlit UI, Windows/Ubuntu | Ruff source check, 24 legacy UI, 14 presenter UI and four recorded-study selectors | 42 UI tests in separate overlapping scopes |
| Delivery, Ubuntu | Nine delivery/checkout guards; four same-commit CI receipts required; source/log hashes checked; reviewed PDF/source archive packaged; extraction, portable tests and HTTP checks replayed | Successful delivery uploads the verified artifact |
| Reviewed byte restoration | Restore newline-only Git translations to reviewed source/artifact hashes; content/binary changes refused | Windows/Ubuntu compatible with frozen evidence; originals unchanged |

Target: [Ahmed-Javaid/Investify-FYP-2027 Actions](https://github.com/Ahmed-Javaid/Investify-FYP-2027/actions). The actual [hosted run](https://github.com/Ahmed-Javaid/Investify-FYP-2027/actions/runs/38426650755) passes all five jobs, including both platforms and verified delivery. The artifact was downloaded and its server digest and every delivered-file hash independently matched. [Current completion receipt](../evidence/mid1_technical_completion_current.json) records that run when verified.

Continuous delivery produces the tested source/PDF/handover artifact. **Production hosting is later FYP scope.** CI/CD performs no paid inference or student training. Publisher weights and raw acquisition inputs remain separate prerequisites for fresh scientific replay. If original acquisition inputs are absent, delivery verifies retained corpus/label/plan consistency and explicitly records that raw-source reconstruction was not executed.

Local replay uses prepared E: runtimes; hosted jobs install pinned viewer/source-check dependencies. Source declarations are retained in artifacts and prior metadata is restored afterward. Dated receipts preserve their own snapshots.
