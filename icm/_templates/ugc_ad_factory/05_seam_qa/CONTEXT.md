# 05 Seam QA

## Order
1. Compare clip 1's approved end frame with clip 2's first frame.
2. Target mean absolute pixel difference below `5/255` when local frame analysis is available.
3. If the seam fails, regenerate/reseed clip 2; do not hide a failed continuation with an arbitrary transition.
4. Trim clip 2 tail only after the seam is accepted.
5. Stitch the approved clips.

## Quality checks
- Creator continuity.
- Product identity and packaging remain stable.
- No duplicate/warped objects.
- Speech is complete and intelligible.
- 9:16 output remains valid.

## Output
QA receipt with pass/fail evidence and final stitched asset reference.
