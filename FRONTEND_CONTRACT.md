# Vendor Document Auto-Fill — Frontend Integration Contract

## New Upload Flow

**Old flow (REMOVED):** `POST /upload/vendor` → Done.
**New flow:**
1. `POST /upload/vendor?profile_id={optional}`
   - Returns `doc_id`
2. Poll `GET /upload/vendor/draft/{doc_id}` every 3 seconds
   - Wait for `status == "draft_ready"`
3. Display `extracted_draft` fields in an editable form
   - Pre-populate VendorProfile form fields with extracted values
   - Show `extraction_confidence` as a percentage indicator
   - Fields with low confidence should be visually highlighted for review
4. User edits and confirms
5. `POST /upload/vendor/confirm/{doc_id}`
   - Body: `{ "profile_data": <edited form data>, "target_profile_id": <uuid or null> }`
   - On success: redirect to the vendor profile page

## Confidence Indicator
- `extraction_confidence >= 0.85` → **Green**, "High confidence"
- `extraction_confidence 0.60-0.84` → **Yellow**, "Review recommended"
- `extraction_confidence < 0.60` → **Red**, "Manual review required"

## Error States
- `status == "failed"` → Show error banner, offer manual profile creation.
- `status == "processing"` after 5 minutes → Show timeout warning.
