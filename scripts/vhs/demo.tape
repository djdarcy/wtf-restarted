# VHS demo recording for wtf-restarted README
# https://github.com/charmbracelet/vhs
#
# Run from project root:
#   PATH=C:\code-ext\ttyd-msvc-dist;%PATH% && vhs scripts/vhs/demo.tape
# Requires: pip install -e . (so the render module is importable)
# Note: Must use "cmd" shell on Windows (bash doesn't work under ConPTY)

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

# -- Scene 1: Diagnose --
Type "wtf-restarted"
Sleep 1s

# Hide enter, execution, and scroll-to-top so output appears immediately
Hide
Enter
Sleep 5s
ScrollUp 156
Show
Sleep 10s
# Page down to show evidence table
ScrollDown 20
Sleep 2s
ScrollDown 4
Sleep 2s
ScrollDown 4
Sleep 2s
ScrollDown 4
Sleep 2s
ScrollDown 4
Sleep 10s

# Page down to show new prompt
Hide
ScrollDown 156
Show

# -- Scene 2: History --
Type "wtfr history"
Sleep 1s

# Same trick -- hide enter + execution + scroll-to-top
Hide
Enter
Sleep 5s
ScrollUp 215
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

# End on the key "hero shot" -- scroll back to verdict + evidence summary
# This becomes the resting frame after the GIF stops looping
# Hide
# ScrollUp 500
# ScrollDown 16
# Show
# Sleep 5s
