# Buffer Blaster art-of-reduction audit

Candidate branch: `fix/art-of-reduction-journey`

## Journey walked

Landing → Create an ad → brief → plan → cost/credit approval → render → library/receipt → optional schedule → analytics.

The Vercel preview is authentication-protected for anonymous visitors, so the interactive walk used the same production build locally after confirming every route compiles. No checkout, render, scheduling, or publishing action ran.

## Breaks found and fixed

1. **Primary CTA pointed to a beta form, not the product.** Landing now sends "Create an ad" straight to `/studio/create`.
2. **Beta form falsely posted to `/`.** Next has no POST handler there, so signup could appear to work only in a host-specific setup. It now uses `/api/beta`, validates email, and fails honestly until `BETA_WAITLIST_ENDPOINT` is connected.
3. **Two product stories conflicted.** `/founding` sold a legacy $29 creator-workflow product unrelated to the UGC factory. It now redirects to `/pricing`.
4. **Pricing was a position paper, not a decision page.** Replaced with two clear choices: managed or private install, plus direct Studio/beta actions.
5. **Core create screen explained infrastructure before the task.** It now starts with the brief and labels the next action "Review scripts and cost."
6. **Raw implementation language leaked into navigation and empty states.** Removed or shortened "canonical," "provider routing," "governed system," "production ledger," "synthetic metrics," and similar internal terms across the Studio journey.
7. **Missing API key caused server-side proxy setup to throw before a request.** Server proxies now send the API key only when present, allowing public/read endpoints or a clear backend response instead of an internal exception.
8. **Private Vercel preview blocks anonymous evaluation.** Not changed: publishing/access settings remain an owner-controlled deploy decision.
9. **Real beta persistence is not configured.** Not faked: the new endpoint returns 503 with "The beta list is not connected yet" until an endpoint is supplied.
10. **Paid end-to-end render cannot be tested without an active paid pass.** Not run. The user sees the scripts and cost before that wallet-bearing step.

## Worst copy reductions

- Before: "Buffer Blaster is private creative infrastructure for teams and agents that need to turn product truth into testable UGC, keep paid actions governed, and bring real evidence back into the next creative decision."
  After: "Brief the product. Review the script and cost. Approve when you are ready."
- Before: "One governed system from signal to evidence."
  After: "From brief to finished ad."
- Before: "Planning is free of provider spend... The factory then runs both clips, continuity QA, stitching, storage, and the final receipt."
  After: "Add the product details. Review the scripts and cost. Approve the render."
- Before: "This library is generated from canonical creative-job receipts. Nothing appears here merely because a mock card exists in the frontend."
  After: "Finished renders and receipts appear here."
- Before: "This surface no longer invents scheduled posts... keep the returned scheduling receipt."
  After: "Choose an account, review the post and time, then approve."
- Before: "The previous demo numbers were removed because presence is not proof..."
  After: "This page stays empty until real channel data arrives."

## Verification

- `npm --prefix frontend run build`: passes, 35 routes.
- All key journey pages return HTTP 200 in the production server build.
- `/founding`: HTTP 307 → `/pricing`.
- Unconfigured `/api/beta`: honest HTTP 503, no fake success.
- Unauthenticated `/api/trial/status`: HTTP 401 with `{ok:false, active:false}`.
- Pixel checks: 1440×1100 landing, 390×844 landing, 1440×1100 create screen.
- No spend, render, checkout, schedule, publish, or production deployment occurred.
