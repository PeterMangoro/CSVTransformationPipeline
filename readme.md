# CueBox Data Import Transformation Pipeline

This project transforms client data from three input CSV files into two output CSV files that can be imported into CueBox for constituent and donation management.

## Project Structure

```
CueBox/
├── backend/              # Main application code
│   ├── config.py        # Configuration constants
│   ├── constituents.py  # Constituent transformation logic
│   ├── donations.py     # Donation aggregation logic
│   ├── email_utils.py   # Email standardization and validation
│   ├── io_utils.py      # CSV reading/writing utilities
│   ├── main.py          # Main orchestration pipeline
│   ├── tags.py          # Tag processing and API integration
│   └── validation.py    # Output validation checks
├── tests/               # Unit tests (129 tests)
├── output/              # Generated output CSV files
├── InputConstituents.csv      # Input: Constituent data
├── InputEmails.csv            # Input: Email records
├── InputDonationHistory.csv   # Input: Donation records
├── run.py               # Entry point to run the pipeline
├── validate.py          # Validation script for output files
└── requirements.txt     # Python dependencies
```

## How to Run

### Prerequisites

- Python 3.8 or higher
- Virtual environment (recommended)

### Setup

1. **Create and activate a virtual environment:**

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**

```bash
pip install pytest  # Only dependency (for running tests)
```

Note: The main application uses only Python standard library modules.

### Running the Pipeline

Run the main transformation pipeline:

```bash
python run.py
```

This will:
1. Load the three input CSV files
2. Transform constituents according to business rules
3. Generate tag counts
4. Write two output CSV files to the `output/` directory:
   - `FinalOutputFormatCueBoxConstituents.csv`
   - `FinalOutputFormatCueBoxTags.csv`

### Running Tests

Run the full test suite (129 unit tests):

```bash
pytest tests/ -v
```

Run tests for a specific module:

```bash
pytest tests/test_constituents.py -v
pytest tests/test_donations.py -v
pytest tests/test_email_utils.py -v
pytest tests/test_tags.py -v
pytest tests/test_io_utils.py -v
```

### Validating Output

Run validation checks on the generated output files:

```bash
python validate.py
```

This validates:
- Row counts match input
- Constituent IDs are unique and non-null
- Lifetime donation amounts are correct
- Most recent donation dates/amounts are correct
- Email formats are valid
- Constituent types are correctly determined
- Tag counts match actual usage

## Assumptions and Decisions

This section documents the key decisions made during data processing and the reasoning behind them.

### 1. Constituent Type Determination

**Decision:** A constituent is classified as a "Company" if the `Company` field is non-empty and not in a list of invalid values. Otherwise, it's a "Person."

**Invalid Company Values:** `""`, `"None"`, `"N/A"`, `"n/a"`, `"Retired"`, `"Used to work here."`

**Rationale:** These values represent placeholder or descriptive text rather than actual company names. Companies with actual names should be classified as Company type, while individuals (even those with empty or placeholder company values) should be Person type.

**Questions for Client Success Manager:**
- Are there other placeholder values we should exclude?
- Should we treat whitespace-only company values as empty?

### 2. Constituent ID

**Decision:** Reuse the `Patron ID` from the input data as `CB Constituent ID`.

**Rationale:** The Patron ID appears to be a stable identifier already assigned by the client's system. Reusing it maintains referential integrity and allows the client to trace records back to their original system.

**Questions:**
- Should we generate new IDs, or is reusing Patron ID acceptable?
- Are Patron IDs guaranteed to be unique and stable?

### 3. Email Standardization

**Decision:** 
- Lowercase all email addresses
- Trim whitespace
- Auto-correct common domain typos (e.g., `gmaill.com` - `gmail.com`)
- Validate email format using regex
- Deduplicate emails
- Select Primary Email as Email 1 if valid; otherwise use first valid email from list

**Domain Corrections:**
- `gmaill.com` - `gmail.com`
- `hotmal.com` - `hotmail.com`
- `yaho.com` - `yahoo.com`
- `gmal.com` - `gmail.com`
- `outlok.com` - `outlook.com`

**Rationale:** Email typos are common in data entry. Auto-correcting obvious domain typos improves data quality without losing information. Standardizing to lowercase ensures consistency for matching and deduplication.

**Questions:**
- Should we auto-correct other common typos?
- Should invalid emails be dropped entirely or flagged for manual review?

### 4. Tag Processing

**Decision:**
- Split tags by comma
- Trim whitespace from each tag
- Deduplicate tags
- Fetch tag mapping from API (`https://6719768f7fc4c5ff8f4d84f1.mockapi.io/api/v1/tags`)
- Map tags using API response (original - `mapped_name`)
- Keep unmapped tags as-is (original name)
- Output tags as comma-separated string

**Rationale:** The API provides a mapping to standardize tag names (e.g., "Top Donor" - "Major Donor"). Tags not found in the API are kept to preserve all information, but the client may want to review unmapped tags.

**Questions:**
- Should unmapped tags be dropped or flagged?
- What should happen if the tag API is unavailable?
- Are there tag naming conventions we should follow?

### 5. Donation Aggregation

**Decision:**
- **Lifetime Donation Amount:** Sum of all non-refunded donations per Patron ID
- **Most Recent Donation:** Latest non-refunded donation date and amount
- **Exclude Refunded:** Donations with Status="Refunded" are excluded from all calculations
- **Orphaned Donations:** Donations for Patron IDs not in the constituents file are excluded and logged as warnings

**Rationale:** Refunded donations should not count toward lifetime totals or recent activity. Orphaned donations represent data inconsistencies that need client review.

**Questions:**
- Should refunded donations be tracked separately?
- How should we handle orphaned donations in production?

### 6. Date Handling

**Decision:** Support multiple date formats and try parsing in order of preference:

1. `"%b %d, %Y"` (e.g., "Jan 19, 2020")
2. `"%m/%d/%Y"` (e.g., "04/19/2022")
3. `"%m/%d/%Y %H:%M"` (e.g., "12/07/2017 12:34")
4. `"%Y-%m-%d"` (ISO format)

**Fallback Logic for CB Created At:**
- If `Date Entered` is missing or unparseable, use the earliest non-refunded donation date
- If no donations exist, use current date

**Output Format:** ISO 8601 format (`YYYY-MM-DDTHH:MM:SS`)

**Rationale:** Input data contains multiple date formats. Supporting all formats ensures maximum data capture. The fallback ensures every constituent has a Created At date.

**Questions:**
- Are there other date formats we should support?
- Is the fallback logic acceptable for missing dates?

### 7. Title Mapping

**Decision:** Map `Salutation` field to allowed Title values: `"Mr."`, `"Mrs."`, `"Ms."`, `"Dr."`, or empty string.

**Mapping:**
- `"mr"` - `"Mr."`
- `"mrs"` - `"Mrs."`
- `"ms"` - `"Ms."`
- `"dr"` - `"Dr."`
- `"rev"` - `""` (not in allowed list)
- `"mr. and mrs."` - `""` (not in allowed list)

**Rationale:** The output requires specific title values. Values not in the allowed list are mapped to empty string to avoid data loss while maintaining compliance.

**Questions:**
- Should we add other titles (e.g., "Rev.") to the allowed list?
- How should we handle other salutation values?

### 8. Background Information

**Decision:** Format as: `"Job Title: {job_title}; Marital Status: {marital_status}"`

If either field is missing, only include the present field(s). If both are missing, output empty string.

**Rationale:** Provides structured, human-readable background information in a consistent format.

**Questions:**
- Is this format acceptable, or should it be structured differently?

### 9. Column Name Normalization

**Decision:** The input CSV has column headers that don't match their actual content:
- `Title` column contains job titles - normalized to `Job Title`
- `Gender` column contains marital status - normalized to `Marital Status`

**Rationale:** The actual data content in these columns doesn't match the headers. Normalizing the column names in code ensures correct mapping during transformation.

**Questions:**
- Is this a data quality issue we should flag for the client?
- Should we verify this interpretation is correct?

### 10. Name Standardization

**Decision:** Capitalize first letter, lowercase rest (e.g., `"JOHN DOE"` - `"John Doe"`)

**Rationale:** Provides consistent name formatting while preserving compound names and special characters.

**Questions:**
- Are there name formatting requirements (e.g., Mc/Mac prefixes)?
- Should we handle special name cases differently?

## Questions for Client Success Manager

1. **Data Quality:**
   - The `Title` and `Gender` columns in InputConstituents.csv contain job titles and marital status respectively, not titles/salutations and gender. Is this expected, or a data quality issue?
   - Should we validate and report on data quality issues (missing required fields, invalid formats, etc.)?

2. **Orphaned Donations:**
   - How should we handle donations for Patron IDs that don't exist in the constituents file? Currently excluded with warnings.

3. **Tag Mapping:**
   - Should unmapped tags be dropped, kept as-is, or flagged for review?
   - What happens if the tag API is unavailable in production?

4. **Email Validation:**
   - Should invalid emails be excluded entirely or included with a flag?
   - Are there additional domain corrections needed?

5. **Date Handling:**
   - Are there other date formats we should support?
   - Is the fallback Created At date logic acceptable?

6. **Output Validation:**
   - Are there additional validation rules we should implement before client sign-off?

## QA Process

The output has been validated through multiple methods:

### 1. Automated Validation Script

Run `python validate.py` to execute comprehensive checks:

-  **Row Count Validation:** Ensures output row count matches input constituents (100 rows)
-  **Constituent ID Validation:** Verifies all IDs are unique and non-null
-  **Lifetime Donation Validation:** Validates that CB Lifetime Donation Amount equals the sum of non-refunded donations per constituent
-  **Most Recent Donation Validation:** Confirms CB Most Recent Donation Date/Amount match the latest non-refunded donation
-  **Email Format Validation:** Ensures all CB Email 1/2 values are syntactically valid
-  **Constituent Type Validation:** Verifies Person/Company classification is correct
-  **Tag Count Validation:** Validates that tag counts match actual usage in constituents

### 2. Unit Test Suite

129 unit tests cover all transformation logic:

- **test_constituents.py** (36 tests): Constituent type determination, name standardization, date parsing, title mapping, background info formatting, full transformation
- **test_donations.py** (23 tests): Amount parsing, filtering, aggregation, lifetime calculation, most recent donation
- **test_email_utils.py** (24 tests): Email standardization, domain typo fixes, validation, selection
- **test_tags.py** (18 tests): Tag API fetching, processing, counting, deduplication
- **test_io_utils.py** (10 tests): CSV reading/writing, column normalization

Run with: `pytest tests/ -v`

### 3. Manual Review

- Reviewed sample output rows to verify data transformation correctness
- Verified tag mapping API integration works correctly
- Confirmed edge cases (missing data, invalid formats) are handled appropriately
- Checked that all business rules are applied consistently

### 4. Data Integrity Checks

- All input constituents appear in output (no data loss)
- Donation amounts sum correctly
- Email deduplication works correctly
- Tag mapping preserves all tags (mapped or unmapped)

## AI Tool Usage Statement

### What I Did vs. What AI Assisted With

**I Did (Manual Work):**
- Initial requirements analysis and data inspection
- Design of the transformation pipeline architecture
- Business rule decisions and assumptions documentation
- Writing all transformation logic code (`backend/` modules)
- Creating comprehensive unit test suite (129 tests)
- Writing validation script (`backend/validation.py`)
- Code refactoring into modular structure
- Debugging and fixing issues
- Writing this README and documentation
- Manual QA and output verification

**AI Assisted With:**
- Code scaffolding and boilerplate generation (virtual environment setup, basic file structure)
- Research on Python best practices for CSV handling and date parsing
- Suggestions for error handling patterns
- Initial test case ideas (I then expanded significantly)
- Reviewing code for potential bugs and improvements
- Grammar and clarity improvements in documentation

**Percentage Estimate:** Approximately **85-90% manual work, 10-15% AI-assisted** (primarily scaffolding and research).

**Key Principle:** All code logic, business rules, and decisions are my own. AI was used as a tool for efficiency in boilerplate and research, similar to using Stack Overflow or documentation, but all critical thinking, design decisions, and implementation details are my work.

## Output Files

The pipeline generates two CSV files in the `output/` directory:

### 1. FinalOutputFormatCueBoxConstituents.csv

Contains one row per constituent with the following fields:
- `CB Constituent ID`
- `CB Constituent Type` (Person or Company)
- `CB First Name`
- `CB Last Name`
- `CB Company Name`
- `CB Created At` (ISO 8601 format)
- `CB Email 1 (Standardized)`
- `CB Email 2 (Standardized)`
- `CB Title`
- `CB Tags` (comma-separated)
- `CB Background Information`
- `CB Lifetime Donation Amount`
- `CB Most Recent Donation Date`
- `CB Most Recent Donation Amount`

### 2. FinalOutputFormatCueBoxTags.csv

Contains one row per unique tag with:
- `CB Tag Name`
- `CB Tag Count` (number of constituents with this tag)

## Technical Notes

- **Python Version:** Requires Python 3.8+
- **Testing:** Uses pytest for unit tests (only external dependency)
- **Code Style:** Follows PEP 8, modular structure following SOLID principles
- **Error Handling:** Comprehensive logging and graceful error handling

