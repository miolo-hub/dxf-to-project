# Chandamama Phase-2 map — label conflict correction

## What changed

- Preserved the 155 CAD-derived candidate polygons and their internal candidate IDs.
- Kept the PDF-text-matched plot 30 at P152 and plot 31 at P151 as the canonical text-matched records.
- Removed automatically assigned official plot numbers from P108 and P120 because their visual transcriptions (31 and 30) conflict with those canonical records.
- The raw readings are retained in `source_label_transcription`, and these two candidates remain searchable by their raw source labels.
- The map displays `P108?` and `P120?` until a human verifies and enters the approved plot number.
- The interactive map attempts to migrate older browser data. It clears the previous default label only when no buyer/payment/property details were saved; existing populated records are preserved.

## Unresolved items

| Candidate | Raw visual reading | Official number field |
|---|---|---|
| P108 | 31 | Blank pending confirmation |
| P120 | 30 | Blank pending confirmation |

No replacement official plot numbers have been invented. Please confirm these two against the approved layout or site records before recording a sale.

## Boundary accuracy

This correction fixes the duplicate assignment behavior; it does not certify the polygon geometry. Use `boundaries_over_original_pdf.png` and `plot_number_review_overlay.png` for review. All geometry-based area measurements remain in drawing units and are not approved sale areas.

## Browser storage limitation

The HTML is a local-only prototype. Data are stored in the current browser and do not synchronize between staff members or include login/security. Export JSON/CSV backups.
