# GhostGrid Frontend — Fix Tracker

> Note: Project uses Tailwind CSS v4 (@tailwindcss/vite). No tailwind.config.js exists.
> Custom animations are defined directly in index.css.

- [x] FIX-01: Define animate-slide-in-top in index.css (already present — verify & harden)
- [x] FIX-02: Fix radial gradient hex opacity bug in CrisisIndex
- [x] FIX-03: Fix location case-sensitivity bug in WorldMap deduplication
- [x] FIX-04: Fix SVG tooltip clipping at right/bottom map edges
- [x] FIX-05: Fix LiveTerminalFeed pause — snapshot rows on pause
- [x] FIX-06: Add continent SVG paths to WorldMap
- [x] FIX-07: Harden getAlertText and all utils against null/undefined fields
- [x] FIX-08: Verify and fix .card CSS class exists in global styles
- [x] FIX-09: Add 30-second polling useEffect to AlertsContext
- [x] FIX-10: Add 30-second polling useEffect to SourcesContext
- [x] FIX-11: Add empty state overlay to WorldMap when alerts array is empty
- [ ] FIX-12: Add empty state to LiveTerminalFeed and RecentAlerts panel
- [ ] FIX-13: Verify MetricCard, SignalBadge, AlertDrawer components are complete
- [ ] FIX-14: Verify UIContext openDrawer wires correctly to AlertDrawer render
- [ ] FIX-15: Smoke test — confirm CommandCenter renders without console errors

## SMOKE TEST
_(populated during FIX-15)_
