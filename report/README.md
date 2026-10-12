# Investify mid report working sources

The editable entry point is `main.tex`. The current compiled output is
[the 13 October unsigned working draft](../deliverables/Investify_FYP1_Mid_Report_Working_Draft_20261013.pdf):
89 pages, all rendered and layout checked. [The delivery receipt](../evidence/report_delivery_20261013_run02.json)
records source/compiler/PDF/page identities and the visual-review method.
The supplied institutional class, logo and reference bytes remain unchanged.

Original September results are separated from the new Alpaca scientific run
and actual original-classifier sentiment comparison. AI-reference agreement,
weak predictive results, all-Buy calibration and the untrained student are
stated explicitly. The guided UI and overlapping test scopes are documented.

## Compile again

Use a new output directory under `E:\AI-Tools\Temp`. The current portable
compiler is `E:\AI-Tools\Cache\tectonic-0.17.0\tectonic.exe`. Set TEMP/TMP,
TECTONIC_CACHE_DIR and XDG_CACHE_HOME to the existing E: scratch/cache directories,
and run `tectonic --outdir <new-directory> --keep-logs --keep-intermediates main.tex`
from `report`. The main preamble bridges the supplied pdfTeX-only compression
setting, resolves numeric bibliography style, disables unbreakable OCG link
boxes and keeps authored front-matter lists separate. New builds must be rendered
and reviewed before delivery; prior output names are never overwritten.

The template's pdfLaTeX/BibTeX sequence remains an alternative when that runtime
is installed; this session used Tectonic's XeTeX pipeline. Its three cosmetic
warnings are recorded; the final log has no overfull boxes, unresolved citations
or duplicate page anchors.

The draft is not ready for institutional submission: programme session,
co-supervisor applicability and coordinator metadata need confirmation;
applicable signatures, actual student declarations/contributions and genuine
team/supervisor review remain outstanding. No approval or authorship is inferred.
