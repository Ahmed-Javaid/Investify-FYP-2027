# Integrated Investify workspace

This is the active consolidated project at `E:\Uni_Stuff\FYP\Investify`.
`code` contains the revised implementation; `report`, `deliverables`, `sources`,
`evidence`, `planning` and `tools` retain its supporting material.

The original checkout at `E:\Uni_Stuff\investify_repo` and the preceding
`GPT_MIDEVAL` working tree were not modified by integration. The verified
pre-merge ZIP is in `E:\Uni_Stuff\FYP\_archives`; it includes their existing Git
history. Historical FYP material is retained locally in `original_materials`.
`MERGE_MANIFEST.json` records source commits, precedence and copied-file hashes.

The local Git repository tracks this integration. Its first commit imports
original source and tool-assisted revisions; it does not establish new student
authorship or supervisor acceptance. `code/source_revision.json` retains the
captured code snapshot's base identity; it is separate from the consolidated
repository's new commit history. Frozen source/data bytes are preserved through
Git without line-ending conversion. No remote or publication is configured.

Current code checks: 212 selected tests with twenty Streamlit cases; 153 scoped
core tests with three deselected. These are not a reproduced market study.
Fresh Yahoo/FNSPID/Alpaca probes failed before HTTP with WinError 10061. Alpaca
credentials and verified original FinBERT weight/config/tokenizer files are
absent. Reacquired inputs must have a new snapshot/cache identity rather than
being relabelled as the historical originals.

Run the local historical-record demo from `code`:

```powershell
python -B scripts/serve_mideval_demo.py --port 8768
```

Caches/temp/scratch on this machine remain beneath `E:\AI-Tools`. Phi-3-mini
remains the planned student, the current assistant is teacher and Mistral is
fallback. QLoRA remains later work.
