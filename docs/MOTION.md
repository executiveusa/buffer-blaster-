# Motion for React (animation)

The `motion` package (motion.dev, formerly Framer Motion) is installed in this
frontend. Use it when a build needs animation.

## Import

```tsx
import { motion } from "motion/react";
```

## Minimal example

```tsx
<motion.div
  initial={{ opacity: 0, y: 8 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.3 }}
>
  ...
</motion.div>
```

## Rules for agents

- Client components only: any file using `motion` needs `"use client"` at the
  top (Next.js App Router). Do not animate inside server components; wrap the
  animated piece in a client child.
- Prefer `initial`/`animate`/`transition` and layout animations; avoid
  imperative `animate()` loops unless the interaction requires it.
- Respect reduced motion: for anything decorative beyond a fade, gate it with
  `useReducedMotion` from `motion/react`.
- Do not add other animation libraries (framer-motion legacy package, GSAP,
  react-spring) - this repo standardizes on `motion`.
- Docs: https://motion.dev/docs/react
