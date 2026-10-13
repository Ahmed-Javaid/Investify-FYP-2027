# Investify Mid-1 LaTeX report

Editable entry: `main.tex`. The current [handbook revision PDF](../deliverables/Investify_FYP1_Mid_Report_Handbook_Revision_20261013.pdf) contains **95 pages and zero fully blank pages**. All pages were rendered and visually reviewed. The sixteen blank verso pages from the previous draft are removed. Added report content means the new page count exceeds the earlier 89-page PDF, which remains preserved.

The [new delivery receipt](../evidence/handbook_report_delivery_20261013.json) binds compiled source inputs, compiler, PDF and render hashes. It records the actual review method. The supplied institutional class, logo and reference bytes remain unchanged. Compiled sources exclude documentation-only README files.

New native TikZ models cover conceptual and implementation domains, pipeline, components, layers, DFD, field/schema contracts, sequence, activity, state, deployment and the UI wireframe. Charts summarize existing retained research results. The handbook appendix maps 34 requirements and marks actual UI screenshots and genuine approvals as pending. Wireframes are labelled as design, not actual browser captures.

Use a new scratch directory beneath E:\AI-Tools\Temp. Existing compiler: E:\AI-Tools\Cache\tectonic-0.17.0\tectonic.exe. Set TEMP/TMP, TECTONIC_CACHE_DIR and XDG_CACHE_HOME to the E: directories. From `report`, run `tectonic --outdir <new-directory> --keep-logs --keep-intermediates main.tex`, then render and review the new output. The preamble preserves the supplied class while bridging XeTeX compression and bibliography/link issues. The final build has zero overfull boxes or unresolved citations.

The [presentation](../presentation/main.tex) is also LaTeX/Beamer. Report status remains an unsigned working draft: programme session, co-supervisor applicability and coordinator details need confirmation, together with real student declarations/contributions and genuine team/supervisor review. Weak prediction and all-Buy calibration are preserved. No approval is inferred.
