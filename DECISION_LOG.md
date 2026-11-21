# RiskMatch decision log

## 2026-11-21 — English as the project language

The project owner chose English for project files and folder names. This includes client-facing questions, documentation, research terminology, Python identifiers and messages, notebook cells and generated output. Imported course materials and datasets keep their original contents and filenames.

| Change | Current location |
|---|---|
| Client profile specification and research protocol | [Client profile](CLIENT_PROFILE.md) and [research](RESEARCH.md) |
| English card bank and separate transfer items | [60 cards](questions/bank.json) and [4 transfer items](questions/transfer_validation.json) |
| Data audit and pinned pilot dependencies | [Audit module](data_audit.py) and [requirements](requirements-pilot.txt) |
| Course groupings | `Theory/CFA/`, `Theory/Course_Notes/`, `Theory/Methodology/` and `Theory/Quant_Project/` |
| Local research data and input checksums | `data/additional_data/` and [pilot checksums](data/pilot_checksums.json) |
| In-progress profile, mandate and CHF demonstration | [Profile](riskmatch/profile.py), [mandate](riskmatch/mandate.py) and [catalogue generator](riskmatch/catalogue.py) |

The English questionnaire uses schema version `1.0-pilot-en` and the separate transfer set uses `pilot-1-en`. Field names and labels changed together with their readers. Card IDs, canonical answer order, stakes, outcomes, probabilities and financial thresholds were preserved. The input manifest records the two new questionnaire hashes. Market and course inputs retained their previous content.

**Verification.** Compared the original and English implementations on 1,000 seeded response paths covering all 60 cards. The paths, numerical φ bounds, held-out predictions and allocation choices matched. Verified hashes for 1,110 local course and data files across the directory renames, excluding operating-system metadata. The notebook reproduces the input audit and contains an executable check of the English bank at Step 3.1d.

**Team repository.** The reworked project replaces the previous tree on the default branch. The public source includes the synthetic demo, the English cards and the code for rebuilding the historical walkthrough from authorized local inputs.

**Handoff.** Development of the first product phase paused for this migration. The client specification and card bank are available for review. Human comprehension, timing, category calibration and the one-week retest remain open. Test the English wording in the pilot.
