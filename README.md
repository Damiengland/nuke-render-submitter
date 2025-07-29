# **Nuke Render Submitter for Deadline**

This Nuke plugin provides a user-friendly interface to streamline the process of submitting Nuke rendering jobs to a Deadline render farm. It supports submitting selected Write nodes or the entire script, with options for generating review files, adding slates, and burn-ins.

## **Features**

* **Integrated Submission Panel:** A dedicated UI panel for configuring and submitting render jobs.  
* **Flexible Submission Options:**  
  * Submit all Write/WriteTank nodes in the current script.  
  * Submit only the currently selected Write/WriteTank nodes.  
* **Customizable Job Parameters:**  
  * Set frame ranges.  
  * Define chunk size for rendering.  
  * Adjust job priority.  
  * Add department and comment information (integrates with ShotGrid context).  
* **Review File Generation:** Option to automatically generate a review (e.g., .mov) file alongside the main render.  
* **Automated Review Enhancements:**  
  * Add a slate frame to review renders.  
  * Include burn-ins on review renders.  
* **ShotGrid Integration:** Automatically retrieves department and project information from the current ShotGrid context.  
* **Temporary Script Handling:** Creates temporary Nuke scripts for review renders, ensuring clean submission without modifying the main script.  
* **Write/WriteTank Node Management:** Handles conversion between standard Nuke Write nodes and ShotGrid Toolkit WriteTank nodes for seamless submission.  
* **Pre-submission Checks:** Warns users if output directories already contain files.

## **Installation**

To install the Nuke Render Submitter plugin:

1. **Locate your Nuke Plugin Path:** Find a suitable directory in your Nuke plugin path (e.g., \~/.nuke on Linux/macOS, C:\\Users\\\<username\>\\.nuke on Windows, or a custom path defined in your init.py).  
2. **Create Directory Structure:** Inside your chosen plugin path, create a folder named python (if it doesn't already exist).  
3. **Place Files:**  
   * Place submission\_panel.py into the python directory.  
   * Place menu.py directly into your Nuke plugin path (the same directory where python is located, or any other directory Nuke loads .py files from).  
4. **Restart Nuke:** Close and reopen Nuke to ensure the plugin and its menu items are loaded.

## **Usage**

Once installed, you can access the render submission panel from the Nuke menu:

1. **Open Nuke:** Launch Nuke.  
2. **Navigate to Menu:** Go to **Nuke Menu** \> **Render Submission**.  
3. **Choose Submission Type:**  
   * **Submit Selected Nodes:** Click this to open the submission panel and submit only the Write or WriteTank nodes that are currently selected in your Node Graph.  
   * **Submit Script:** Click this to open the submission panel and submit all Write or WriteTank nodes found within the entire Nuke script.  
4. **Configure Parameters:** In the "Submit Nuke to Deadline" panel, adjust the following parameters as needed:  
   * **Frame Range:** The range of frames to render (e.g., 1001-1100).  
   * **Department:** (Pre-filled from ShotGrid if available) The department for the job.  
   * **Comment:** Any specific notes for the render job.  
   * **Chunk Size:** How many frames per render task.  
   * **Priority:** The job's priority on the Deadline farm.  
   * **Review file:** Check this box to generate a review movie.  
   * **Add slate:** Check this to add a slate at the beginning of the review movie.  
   * **Add burn-in:** Check this to add burn-in information to the review movie.  
5. **Submit:** Click "OK" to submit your job(s) to Deadline.

## **Requirements**

* **Nuke:** The plugin is built for Nuke.  
* **Deadline:** A running Deadline render management system is required for job submission.  
* **ShotGrid Toolkit (Optional):** Integration with ShotGrid is present for department and project context, but the plugin can function without it (though some fields might be empty).

## **License**

MIT

## **Author**

Damien England