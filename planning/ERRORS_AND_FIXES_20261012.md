# Investify network and authentication errors

Updated 12 October 2026. Replacement keys restored Alpaca authentication.
Approved execution outside the sandbox reaches the provider, with 200 responses
from account and news. The default sandbox still refuses connections before HTTP.

## Errors and fixes

| Error or issue | What established the cause | Action and verified result |
| --- | --- | --- |
| WinError 10061 before HTTP | The sandbox failed before a provider response; the normal terminal and approved outside-sandbox checks reached the same hosts. | Used explicitly approved outside-sandbox execution with inherited routing unchanged. Default sandbox access remains restricted. |
| Local network configuration did not enable this running sandbox | Adding network_access = true did not change observed behavior. | Tested effective access. Did not remove the proxy or alter security settings. |
| Paper account 401 with unauthorized. | Detailed urllib diagnostics and the independent requests client reproduced it. Local parsers and outgoing APCA headers matched. | The user replaced the matching key pair in local .env; account and news then returned 200. Alpaca did not identify the precise defect in the old pair. |
| News 401 with nginx Authorization Required HTML | The independent client reproduced the same rejection. | Replacement keys resolved it; no subscription or endpoint change was required. |
| Early diagnostics saved status without the error details | The original receipt could not distinguish rejection causes. | Retained bounded, redacted provider messages and request IDs; discarded account bodies and credential values. |
| Independent-client TypeError about duplicate stream | It occurred locally before any request. | Removed the duplicate option and reran successfully. |
| Unintended line-ending changes | Git diff showed whole-file changes and CR whitespace warnings. | Restored each file's existing LF/CRLF convention; final formatting check passed. |
| Revised news text can be later than publication | Fourteen of the thirty sampled articles have updates after creation. | Retain both timestamps. Use the later timestamp in a conservative CSV and exclude versions updated beyond the study window. Original-version availability remains unproven. |
| Yahoo 429 in the earlier host check | The response established provider connectivity and rate limiting. | Avoid repeated immediate requests. Price acquisition remains a separate dependency. |

## Endpoints and evidence

Paper authentication uses GET https://paper-api.alpaca.markets/v2/account.
Investify news uses GET https://data.alpaca.markets/v1beta1/news with symbols=NVDA.
Both use APCA-API-KEY-ID and APCA-API-SECRET-KEY, as documented by
[Alpaca](https://docs.alpaca.markets/us/docs/authentication).

- [Detailed old-key errors](../evidence/market_reacquisition_20261012/paper_auth_20261012T151704775Z/probe.json).
- [Independent client and parser/header checks](../evidence/market_reacquisition_20261012/independent_auth_20261012T151921041173Z/probe.json).
- [New-key account and news success](../evidence/market_reacquisition_20261012/paper_auth_20261012T152909983Z/probe.json).
- [Thirty historical NVDA articles across 2018 through 2023](../evidence/market_reacquisition_20261012/historical_news_sample_20261012T153005905951Z/probe.json).

The sample confirms usable time-of-day fields in those thirty records.
Full pagination and coverage/revision audits are the next acquisition step.

## Prevent recurrence

Keep the matching current pair in Git-ignored code/.env. Never paste or package
it. Test connectivity before interpreting authentication errors, preserve
provider diagnostics, and compare a second client when the cause is unclear.

Run tools/acquire_alpaca_news.ps1 to create a dated snapshot. Resume a stopped
pull with -Resume -SnapshotName followed by its existing snapshot name. Saved
pages are replayed and hash-checked. The legacy downloader remains historical
because it drops update timestamps and writes to fixed paths.

FNSPID is excluded by the user's direction. No FNSPID request or download was
needed to resolve Alpaca access.


## Scientific continuation - 12 October, 18:11 UTC

The Python 3.11 scientific runtime has no dependency conflicts and imports all
required packages. Matplotlib initially failed because the read-only sandbox
could not create its cache. Approved execution created the required directories
on E:\AI-Tools; no security/routing change was made.

The fresh doctor reports zero blockers and all three commands completed. Both
calibration modes remain all Buy. Actual raw scores are diverse, and retained
isotonic mappings demonstrably collapse this fresh evaluation to Buy.
Independent model/calibration/native-TreeSHAP replay passes. A lower Brier score
does not establish classification usefulness. Recommended next research action:
compare calibration policies on development data under a new frozen identity,
while retaining these findings and never tuning on this evaluation fold.

The independent checker was aligned with the engine's actual default-corpus
filenames before execution. The preparation gate now binds exact publisher
hashes rather than trusting a receipt's publisher boolean alone; eight labelled
refusal tests pass. The executed preparation source is preserved and matches
its original receipt. Original scientific data bytes and the exact lock remain
unreproduced; no social candidate inference or institutional rendering occurred.


## 13 October 2026 - original classifiers and first report build

Both original publisher snapshots download and pass Git/LFS byte gates.
Transformers 5.17 exposes loader fields as sets; normalization preserves every
entry, and nonempty/missing diagnostics still refuse a checkpoint. Original
Cardiff includes two native pooler tensors missing from the modern default
classifier constructor. The first refusal is retained. The compatible loader
retains those original native tensors and proves exact classification-logit
parity with/without the unused pooler. It reruns both candidates under a fresh
source-bound plan; both complete 24 posts and their receipt/logit comparison
replays. No weight, label, mapping or selection criterion was changed.

A transient plan helper failed on Windows default text encoding before writing
or inference; the existing UTF-8-safe CLI froze the replacement plan. The first
viewer check exposed a pending-caption assumption. Caption status now follows
the validated classifier comparison; the failed receipt remains, and the new
25-check viewer run passes with zero skips.

The verified portable Tectonic compiler reached the supplied class and stopped
at its pdfTeX-only compression command before producing pages. The supplied
class is preserved unchanged; a guarded preamble counter lets XeTeX retain its
own compression defaults while keeping native pdfLaTeX behavior unchanged.
The failed console/log and source snapshot are retained in the first build receipt.
The next separate build includes current science/social abstract and summary
wording and the descriptive, calibration-only class-prior comparator.

## Report and guided-demo continuation - 13 October

Tectonic's XeTeX engine refused the supplied pdfTeX compression primitive; the main preamble supplies a compatibility counter without changing the class. Its mixed natbib mode refused the numeric bibliography, corrected by explicit numeric style. OCG link boxes prevented URL wrapping; disabling OCG keeps references within margins. The class's automatic lists duplicated authored front matter; the wrapper defers lists and explicit page breaks/anchors remove duplication and ambiguous page destinations. A missing paragraph before signature rows caused text run-in, corrected. URL formatting suppressed spaces in launch commands, replaced with verbatim commands. Final build08 has 89 rendered/reviewed pages, no overflow/unresolved citation/anchor warning and an unsigned working delivery.

Two source-edit helpers failed syntax/anchor checks; the syntax failure changed no files, and the anchor failure retained only preceding routine draft edits. A PowerShell check incorrectly used an inherited LASTEXITCODE after a successful native-PDF PowerShell render; all 89 pages were actually present. The audit then ran on those images without rerendering. Prior builds/receipts remain unchanged.

The guided demo has fresh-record defaults, a start route, navigation callbacks, three decision stages and explicitly fictional profile buttons. Its final focused scope passes 28 checks. Browser inventory was empty and IAB opening refused, so programmatic checks and localhost health are retained without a browser-visual claim. Presentation authoring remains blocked by the required bundled runtime, not user authorization.
