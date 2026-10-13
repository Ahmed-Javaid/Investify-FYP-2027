# Implemented CI and delivery status

The project has a GitHub Actions **CI workflow** and a shared executable validation runner. It has **no continuous deployment stage**, configured hosting target or recorded GitHub run. The consolidated repository currently has no remote configured.

The workflow starts on a push to `main`/`gpt/**`, a pull request or manual dispatch. It uses Python 3.11 with Windows and Ubuntu jobs, read-only repository permissions, finite timeouts, duplicate-run cancellation and disabled persistence of checkout credentials.

| Job | Implemented checks | Current execution evidence |
| --- | --- | --- |
| Portable evidence | Source ownership and metadata admission/cleanup guards; standard-library regressions; 372 saved-record/context/template validations; standalone HTML preview; no-inference explainer plan; 228 comparator probes; real localhost HTTP checks | Windows local replay passed: 165 portable tests, 7 CI guards, 62 HTTP checks. |
| Streamlit UI | Scoped Ruff source checks; preserved UI; current presenter; recorded-study selectors | Windows local replay passed: 24 legacy, 14 presenter and 4 selector tests. |
| Review artifact retention | Workflow uploads each job's output/log directory and source-bound receipt, including available failure logs, for 14 days | Configured; no GitHub artifact upload/run has occurred. |
| Continuous deployment | No deploy command, cloud hosting, broker/order execution or production release | Not implemented. Deployment is later scope and needs a chosen target. |

Both hosted jobs and local replay call [the same runner](../code/scripts/run_mid1_ci.py). [The workflow](../.github/workflows/mideval-evidence.yml) installs the pinned viewer/runtime and source checker on hosted runners. Local replay uses prepared E: runtimes, so it does not certify fresh package installation, Ubuntu execution, remote GitHub CI, prediction quality or user acceptance.

Receipts: [portable job](../evidence/ci_replay_20261013_run02/evidence/job_receipt.json), [UI job](../evidence/ci_replay_20261013_run02/streamlit-ui/job_receipt.json). Their source identity is explicitly declared for the code component; no unrelated ancestor repository supplies an automatic identity. Job declarations are kept with the artifacts and temporary checkout metadata is restored afterward. Earlier archive/test receipts retain their own snapshots.

To rerun locally, choose new output directories, from `code`:

```powershell
& 'E:\AI-Tools\Temp\investify-ui-py311\Scripts\python.exe' -B scripts/run_mid1_ci.py --job evidence --output ../evidence/ci_replay_NEW/evidence
& 'E:\AI-Tools\Temp\investify-ui-py311\Scripts\python.exe' -B scripts/run_mid1_ci.py --job streamlit-ui --output ../evidence/ci_replay_NEW/streamlit-ui --ruff-executable E:/AI-Tools/Work/investify-quality-tools/bin/ruff.exe
```

A real GitHub run needs an agreed repository/remote and an authorized push or dispatch. That external step is still pending. The current package can demonstrate the CI logic and actual local checks without claiming remote CI or CD.
