# Buffer Blaster hero UGC assets

These clips were generated specifically for the restrained laptop/phone hero composition.

## Skincare creator
- Fal endpoint: `minimax/h3-max/text-to-video`
- Fal request: `01a0639c-1b18-7c53-8871-8fc9f69d6f9f`
- Temporary CDN URL: `https://v3b.fal.media/files/b/0aa8d900/wv-O4NWWHaGbH-E21O5_6_minimax-h3.mp4`
- Destination: `frontend/public/media/ugc-skincare.mp4`
- Format: MP4, 9:16, 768P, 5 seconds

## Streetwear creator
- Fal endpoint: `minimax/h3-max/text-to-video`
- Fal request: `01a0639c-3e51-7670-b863-b119848dfacb`
- Temporary CDN URL: `https://v3b.fal.media/files/b/0aa8d901/2rwHx3RUbLd2krI-jpa07_minimax-h3.mp4`
- Destination: `frontend/public/media/ugc-streetwear.mp4`
- Format: MP4, 9:16, 768P, 5 seconds

## Production rule
Do not ship the homepage pointing at the temporary Fal CDN URLs. Download the two files to the local `frontend/public/media/` destinations above, verify playback in the built Next.js app, and commit the binary assets through the normal repository/server workflow. Keep videos muted, autoplay, looped, and `playsInline`.

The hero should remain visually quiet: one laptop, one phone, two real UGC outputs, no dashboard collage, no feature-card explosion, and no new logo treatment until the identity mark is separately approved.
