EluSlot Product Icon Kit v1.0 — 2026-10-27
182 semantic icons / 13 categories

FILES
svg/: currentColor SVG, 24x24, 1.75 stroke, round caps and joins.
svg-light/: explicit dark strokes for light backgrounds.
svg-dark/: explicit light strokes for dark backgrounds.
png-light/ and png-dark/: transparent PNG at 16,20,24,32 px.
catalog.html: self-contained searchable reference; opens offline.
manifest.json and icon-map.csv: semantic IDs and usage mapping.
licenses/: retain these license notices when distributing assets.

INTEGRATION
Use currentColor SVG inline on the web; external img does not inherit the parent CSS color into the SVG. For Qt or renderers without currentColor support, use the explicit-color SVG or PNG variants. Test your actual Qt SVG backend before integration.
Keep semantic IDs stable; avoid selecting by display label. Use text/tooltips and accessible labels for buttons. Do not rely on status color alone. Stop/cancel, close and delete are separate actions; result submit, accept and Git commit use different icons. Platform icons are generic device indicators, not Apple/Android/Windows trademarks. No application logo or OS-specific .ico/.icns is included.

COVERAGE
Covers the functionality discussed for EluSlot. Future product actions require an explicit mapping review. Small-size geometric rendering is checked, but users should still evaluate semantic clarity in the actual interface.

STYLE
Monochrome neutral defaults; apply status accents in the application. A status change does not change permissions or model policy by itself. SVG originals use a transparent background.

Qt resource collection: eluslot-icons.qrc. Example resource path: :/eluslot/icons/dark/task-claim.svg
