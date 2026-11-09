# Hebe Longevity

Your local blood PhenoAge workbench for Hermes. Review the inputs, confirm the exact snapshot, get a traceable calculation and a local HTML report.

**Research prototype. Not a diagnosis or treatment recommendation.** No clinical validation is claimed. Built on PLSI by Insilico Medicine (MIT). Not affiliated with or endorsed by Insilico Medicine or xAI.

## Try it

Requires Hermes >=0.23.0 (tested commit recorded in the project status). No additional Python packages, model subscription, API keys or profile package required for this demo.

```sh
hermes plugins install https://github.com/brainarts-studio/hebe-longevity
```

The repository is currently private: your GitHub account needs access and Hermes must be able to authenticate Git. For a local checkout, install this directory using `hermes plugins install /absolute/path/to/hebe-longevity`. Enable `hebe-longevity` if your installer does not enable it, then start a new Hermes chat.

Enter **`/hebe`**. Review the fictional Alex Demo panel and select **Save and calculate**. Hebe returns blood PhenoAge and a local report link. This requires a Hermes surface supporting plugin confirmation dialogs; if no dialog is available, nothing is committed. Report links point to the machine running Hermes; remote messenger clients may not open them.

## Your own CSV (advanced, research use only)

Copy `data/demo.csv` as the template. Replace fictional data with your local pseudonym and values, preserving exact header order. Enter:

```text
/hebe import "/absolute/path/panel.csv" 1981 person-id
```

All nine markers, one matching person, one draw/date, unique observation IDs and `status=final` are required. Canonical units only; no guessed conversions. Files are limited to 64 KiB. Negative values, nonfinite values, percentages outside 0–100, CRP <=0, future dates and minors are refused. Only unsigned plain decimal notation is accepted (for example `44` or `4.4`, without spaces or exponents). With birth year alone, the collection year must be at least birth year + 19 to establish adulthood conservatively. These checks are not a complete medical plausibility assessment. Birth year is approximated to mid-year by the upstream age formula.

`/hebe status` lists saved identifiers. `/hebe report RESULT_ID` regenerates the report. A repeated confirmation is idempotent. Changing an existing draw is refused; corrections are not supported yet.

## Data and approval

Data lives under the active `HERMES_HOME/plugin-data/hebe-longevity/`, never the plugin installation directory. Validated previews are stored locally for up to 30 minutes (expired previews are removed on the next preview), separately from confirmed results. Starting the same preview refreshes its 30-minute deadline; cancelling or a missing confirmation dialog discards it. The dialog approves an immutable snapshot, not a later file read. The database uses transactions to prevent duplicate concurrent commits.

The model tool `hebe_preview` can prepare **fictional** demo data and list result identifiers. It cannot approve or commit. Real imports use the user command and confirmation dialog. Who may answer a dialog in a shared messenger session depends on Hermes and has not been tested. This permission split is not a sandbox against a separately enabled shell or other powerful tools.

No network or model calls are made by this plugin. **Hermes itself may send chat/tool outputs to your configured cloud model.** The plugin does not enforce network isolation. Health data shown in reports and chat remains sensitive. Delete the plugin data directory yourself to remove stored results; there is no automatic retention policy for confirmed results.

## Supported now

Strict CSV review, fictional demo, user confirmation, native command/tool, blood PhenoAge, input provenance and HTML report.

**Unsupported:** FHIR, PDF/photo extraction, wearables, medication/supplement advice, plans/scoring, counterfactual forecasts, a dashboard tab, DE translation and an offline security boundary. Rejecting FHIR does not repair the upstream FHIR importer.

The first milestone selectively vendors unchanged PLSI numerical definitions instead of installing the incomplete upstream wheel. No PLSI executable extensions, relay, automatic updates or specialist skills are included. See `NOTICE.md` and `vendor/provenance.json`.

## Development

```sh
python3 -m unittest discover -s tests -v
hermes plugins validate . --install-deps --json
hermes plugins doctor . --ci
```

Uses the Python standard library only. The broader project contains a real Hermes discovery/dispatch smoke test. No full live human-dialog or browser verification has yet been claimed.
