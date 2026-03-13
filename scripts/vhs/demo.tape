# VHS demo recording for wtf-restarted README
# https://github.com/charmbracelet/vhs
#
# Run from project root:
#   PATH=C:\code-ext\ttyd-msvc-dist;%PATH% && vhs scripts/vhs/demo.tape
# Requires: pip install -e . (so the render module is importable)
# Note: Must use "cmd" shell on Windows (bash doesn't work under ConPTY)
#
# Post-processing:
#   gifsicle --no-loopcount -O3 docs/demo.gif -o docs/demo.gif

Output docs/demo.gif

Set Shell "cmd"
Set Theme "Dracula"
Set FontSize 25
Set Width 1728
Set Height 1000
Set TypingSpeed 225ms
Set Framerate 28
Set CursorBlink false
Set Padding 20

# -- Scene 1: Tier 0 -- Verdict + AI Analysis --
Type "wtf-restarted --ai --hours 80"
Sleep 1s

# Hide enter + execution (~8s for analysis + AI fetch), scroll to top of output
Hide
Enter
Sleep 8s
ScrollUp 50
Show

# Let viewer read the verdict and AI analysis
Sleep 10s

# Scroll down through the rest of tier-0
ScrollDown 8
Sleep 3s
ScrollDown 8
Sleep 3s
ScrollDown 8
Sleep 3s
ScrollDown 8
Sleep 3s
ScrollDown 8
Sleep 10s

# -- Scene 2: Tier 1 -- Evidence Details --
# "Press any key for evidence details" prompt is visible; press Space
Sleep 2s
Space

# Let viewer read evidence table
Sleep 10s

# Scroll through evidence if needed
ScrollDown 8
Sleep 3s
ScrollDown 8
Sleep 6s

# -- Scene 3: Tier 2 -- Full Diagnostics --
# "Press any key for full diagnostics" prompt is visible; press Space
Sleep 2s
Space

# Let viewer read deep diagnostics
Sleep 10s

# Scroll through diagnostics
ScrollDown 8
Sleep 3s
ScrollDown 8
Sleep 3s
ScrollDown 8

# Jump to prompt for next command
Hide
ScrollDown 200
Show

# -- Scene 4: History --
Type "wtfr history"
Sleep 1s

# Hide enter + execution + scroll to top
Hide
Enter
Sleep 5s
ScrollUp 293
Show
Sleep 10s

# Scroll down gradually through history
ScrollDown 4
Sleep 2s
ScrollDown 4
Sleep 2s
ScrollDown 4
Sleep 2s
ScrollDown 4
Sleep 2s
ScrollDown 4
Sleep 2s

Sleep 10s
