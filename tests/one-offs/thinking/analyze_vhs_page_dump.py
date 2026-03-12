"""Analyze VHS page dump to find xterm.js renderer type and canvas elements.

Context: VHS hangs on Windows because it looks for canvas.xterm-text-layer
and canvas.xterm-cursor-layer, but ttyd 1.7.7's xterm.js uses the DOM
renderer instead of the canvas renderer. This script examines the page
HTML dumped from our debug VHS build to understand what's available.
"""

import re
import sys

DUMP_PATH = "vhs-page-dump.html"

try:
    with open(DUMP_PATH, encoding="utf-8", errors="replace") as f:
        html = f.read()
except FileNotFoundError:
    print(f"ERROR: {DUMP_PATH} not found. Run vhs-debug.exe first.")
    sys.exit(1)

print(f"Page HTML size: {len(html):,} bytes")
print()

# Find all class attributes with xterm in them
xterm_classes = re.findall(r'class="([^"]*xterm[^"]*)"', html)
print(f"=== xterm CSS classes found ({len(xterm_classes)}) ===")
for cls in sorted(set(xterm_classes)):
    print(f"  {cls}")

print()

# Find canvas elements
canvases = re.findall(r'<canvas[^>]*>', html)
print(f"=== <canvas> elements found: {len(canvases)} ===")
for c in canvases:
    print(f"  {c}")

print()

# Find rendererType context
idx = html.find("rendererType")
if idx >= 0:
    start = max(0, idx - 200)
    end = min(len(html), idx + 200)
    print("=== rendererType context ===")
    print(html[start:end])
else:
    print("rendererType not found in HTML")

print()

# Check for WebGL references
webgl_refs = [m.start() for m in re.finditer(r"webgl|WebGL|webGl", html)]
print(f"=== WebGL references: {len(webgl_refs)} ===")
for ref in webgl_refs[:5]:
    print(f"  ...{html[max(0,ref-50):ref+50]}...")

# Check for DOM renderer references
dom_refs = [m.start() for m in re.finditer(r"dom-renderer|DomRenderer", html)]
print(f"\n=== DOM renderer references: {len(dom_refs)} ===")
for ref in dom_refs[:5]:
    print(f"  ...{html[max(0,ref-30):ref+50]}...")
