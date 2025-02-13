import nuke
from python.submission_panel import SubmitterPanel

# Add menu to Nuke
main_menu = nuke.menu("Nuke")
submission_menu = main_menu.findItem("Render Submission")

if not submission_menu:
    submission_menu = main_menu.addMenu("Render Submission")

submission_menu.addCommand("Submit Selected Nodes", lambda: SubmitterPanel.show(True))
submission_menu.addCommand("Submit Script", lambda: SubmitterPanel.show(False))

