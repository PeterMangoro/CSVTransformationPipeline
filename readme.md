# CueBox Data Import Assignment Plan

## Phase 1: Requirements & Data Understanding

- **Goal**: Build a precise mental model of the inputs, outputs, and edge cases before writing any code.
- **Steps**:
- Inspect input samples  to catalog data issues (missing names, multiple date formats, typos in emails, duplicate tags, refunded donations, etc.).
- Draft a short list of explicit assumptions (e.g., how to treat refunded donations, how to classify Person vs Company, how to deal with bad emails) and open questions for the client success manager.

## Phase 2: Data Model & Business Rules Design

- **Goal**: Define exactly how each output column is computed from the inputs.
- **Steps**:
- Decide on constituent typing rules:
    - If `Company` is non-empty and not a placeholder (e.g., "N/A", "None") → `CB Constituent Type = Company`, `CB Company Name = Company`.
    - Otherwise → `CB Constituent Type = Person`, `CB First Name`/`CB Last Name` from constituent row.
- Specify `CB Constituent ID` strategy (e.g., reuse `Patron ID` vs generate a new stable ID) and document the choice.
- Define email rules:
    - How to standardize emails (lowercasing, trimming whitespace).
    - How to validate and filter obviously invalid domains (e.g., `gmaill.com`, `hotmal.com`) and whether to try to auto-correct or drop them.
    - How to choose `CB Email 1` and `CB Email 2` from primary + extra emails.
- Define tag rules:
    - How to split, trim, and deduplicate tags from the `Tags` column.
    - How to fetch and apply the tag mapping from the tags API (original → `mapped_name`).
    - What to do with tags missing from the mapping (keep original vs drop vs flag).
- Define donation rules:
    - How to aggregate `CB Lifetime Donation Amount` (e.g., sum of all non-refunded donations per Patron ID).
    - How to determine `CB Most Recent Donation Date` and `CB Most Recent Donation Amount` (exclude refunded rows).
    - How to handle donations whose Patron ID is absent in the constituents file.
- Define formatting rules:
    - Standard datetime format for `CB Created At` and donation dates.
    - Allowed values for `CB Title` (mapping from `Salutation`/`Title` to {"Mr.", "Mrs.", "Ms.", "Dr.", ""}).
    - Rules for composing `CB Background Information` from job title + marital status.

## Phase 3: Implementation of the Transformation Pipeline (Python)

- **Goal**: Implement a clear, testable Python script/module that performs the full transformation from inputs to outputs.
- **Proposed structure**:
- Create a Python package directory `backend/` which will transform data and load results in `output/`

## Phase 4: QA, Validation & Edge-Case Review

- **Goal**: Build confidence that the outputs are correct and defensible.
- **Steps**:
- Implement a small set of sanity checks in code or a notebook, for example:
    - Row count in `OutputFormatCueBoxConstituents.csv` matches the number of unique constituents that should be imported.
    - All `CB Constituent ID` values are unique and non-null.
    - For each constituent, `CB Lifetime Donation Amount` equals the sum of their non-refunded donations.
    - `CB Most Recent Donation` fields match the latest non-refunded donation date per constituent.
    - All `CB Email 1/2` values are syntactically valid emails for acceptable domains.
