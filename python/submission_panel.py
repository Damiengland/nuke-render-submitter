import os
import re

import nuke
import sgtk
import uuid
import pathlib
import platform
import subprocess
import nukescripts


class SubmitterPanel(nukescripts.PythonPanel):
    """Creates a UI panel for submitting Nuke renders to Deadline."""

    def __init__(self):
        super().__init__('Submit Nuke to Deadline')

        self._initialize_knobs()
        self._set_default_values()
        self._configure_knobs()
        self._add_knobs()

    # ----------------------------------------
    # UI Setup Methods
    # ----------------------------------------

    def _initialize_knobs(self):
        """Initialize UI knobs."""
        ctx, _ = self._get_shotgrid_context()  # Retrieve ShotGrid context
        department_value = ctx.task["name"] if ctx.task else ""

        self.frame_range = nuke.String_Knob('frame_range', 'Frame Range',
                                            f"{nuke.root().firstFrame()}-{nuke.root().lastFrame()}")
        self.department = nuke.String_Knob('department', 'Department', department_value)
        self.comment = nuke.String_Knob('comment', 'Comment')
        self.chunk_size = nuke.Int_Knob('chunk_size', 'Chunk Size', 10)
        self.priority = nuke.Int_Knob('priority', 'Priority', 33)
        self.divider = nuke.Text_Knob('divider', '')

        self.render_review = nuke.Boolean_Knob('render_review', 'Review file')
        self.add_slate = nuke.Boolean_Knob('add_slate', 'Add slate')
        self.add_burn = nuke.Boolean_Knob('add_burn', 'Add burn-in')
        self.spacer = nuke.Text_Knob('spacer', ' ', ' ')

        # TODO: disable slate and burn in option when movout is disabled

    def _set_default_values(self):
        """Set default knob values."""
        self.chunk_size.setValue(10)
        self.priority.setValue(33)
        self.render_review.setValue(True)
        self.add_burn.setValue(1)
        self.add_slate.setValue(1)

    def _configure_knobs(self):
        """Configure knob properties."""
        self.render_review.setFlag(nuke.STARTLINE)

    def _add_knobs(self):
        """Add knobs to the panel."""
        knobs = [
            self.department, self.comment, self.chunk_size, self.priority,
            self.divider, self.frame_range, self.render_review,
            self.add_slate, self.add_burn, self.spacer
        ]
        for knob in knobs:
            self.addKnob(knob)

    # ----------------------------------------
    # Get Methods
    # ----------------------------------------

    @staticmethod
    def _get_shotgrid_context():
        """
        Retrieves the current ShotGrid Toolkit context and toolkit instance.

        Returns:
            tuple: (ShotGrid context, ShotGrid toolkit)
        """
        engine = sgtk.platform.current_engine()
        return engine.context, engine.sgtk

    @staticmethod
    def _get_deadline_command():
        """
        Retrieves the Deadline command path from environment variables or a fallback file.

        Returns:
            str: The full path to the `deadlinecommand` executable.
        """
        deadline_path = os.environ.get("DEADLINE_PATH", "")

        if not deadline_path:
            fallback_path = "/Users/Shared/Thinkbox/DEADLINE_PATH"
            if os.path.exists(fallback_path):
                with open(fallback_path, "r") as f:
                    deadline_path = f.read().strip()

        return os.path.join(deadline_path, "deadlinecommand")

    @staticmethod
    def _get_ocio_path():
        """
        Retrieves the OCIO environment variable and processes it for Windows and non-Windows systems.

        Returns:
            str: The processed OCIO file path or an empty string if not found.
        """
        ocio_path = os.getenv("OCIO", "")
        if not ocio_path:
            return ""

        if platform.system() != "Windows":
            return ocio_path.replace("/Volumes/production/", "P:/").replace("\\", "/")
        return ocio_path

    @staticmethod
    def _get_nuke_script_path():
        """
        Retrieves the current Nuke script path and ensures it is saved.

        Returns:
            str | None: The path to the saved Nuke script, or None if not saved.
        """
        script_path = nuke.root().name()

        if not script_path or script_path == "Root":
            nuke.message("Please save the Nuke script before submitting to Deadline.")
            return None

        nuke.scriptSave()
        return script_path

    def _get_render_template(self, script_path, template_name="nuke_shot_render_movie"):
        """Generates the render path dynamically based on the given template name."""

        ctx, tk = self._get_shotgrid_context()

        try:
            script_template = tk.template_from_path(script_path)
            current_fields = script_template.get_fields(script_path)
            print(f"Extracted fields: {current_fields}")

            # Fetch the requested template
            render_template = tk.templates.get(template_name)
            if not render_template:
                raise ValueError(f"Render template '{template_name}' is missing or undefined.")

            # Generate fields using context and extracted data
            render_fields = ctx.as_template_fields(render_template)
            render_fields.update({
                key: current_fields.get(key) for key in ["Sequence", "Shot", "Step", "version"] if key in current_fields
            })
            # TODO: get actual output of the write node & width / height
            render_fields.update({
                "SEQ": "%04d",
                "output": "output",
                "width": 1920,
                "height": 1080
            })

            # Apply fields to the template and normalize path
            render_path = render_template.apply_fields(render_fields)
            return render_path.replace("\\", "/") if platform.system() == "Windows" else render_path

        except Exception as e:
            print(f"Error generating render template: {e}")
            return None

    def _get_write_nodes(self, selected_only):
        """
        Retrieves 'Write' nodes either from selected nodes or from all nodes.

        Args:
            selected_only (bool): If True, fetches only selected 'Write' nodes;
                                  If False, fetches all 'Write' nodes.

        Returns:
            list: A list of 'Write' class nodes.
        """
        if selected_only:
            nodes = nuke.selectedNodes()
            if not nodes:
                return None
        else:
            nodes = nuke.allNodes()

        write_nodes = [node for node in nodes if node.Class() in ["Write", "WriteTank"]]

        return write_nodes


    def _get_submission_files(self, node):
        """
        Gathers submission files for both EXR and MOV formats if applicable.

        Returns:
            list: A list of tuples containing job info and plugin info file paths.
        """
        submission_files = [self._build_submission_files("exr", node)]

        if self.render_review.value():
            script_path, output_file = self._build_temp_nuke_script(node)
            submission_files.append(self._build_submission_files("mov", node, script_path=script_path, output_file=output_file))

        return submission_files

    @staticmethod
    def _get_resources_dir():
        """Returns the absolute path to the 'resources' directory."""
        return os.path.join(pathlib.Path(__file__).resolve().parent.parent, "resources")

    def get_adjusted_frame_range(self):
        """
        Retrieves and adjusts the frame range based on user settings.

        If `add_slate` is enabled, the first frame is decremented by 1
        to account for the slate frame.

        Returns:
            str: Adjusted frame range in the format "start-end".
        """
        frame_range_str = self.frame_range.value()
        start_frame, end_frame = map(int, frame_range_str.split("-"))

        if self.add_slate:
            start_frame -= 1  # Adjust for slate

        return f"{start_frame}-{end_frame}"


    # ----------------------------------------
    # Build Methods
    # ----------------------------------------

    def _build_submission_files(self, output_type: str, node, script_path=None, output_file=None):
        """
        Generates job info and plugin info files for Deadline submission.

        Args:
            output_type (str): Output format (e.g., 'mov', 'exr', 'png', etc.).
            node (nuke.Node): The Nuke node related to the submission.

        Returns:
            tuple: Paths to the generated job info and plugin info files.
        """

        if not output_type:
            raise ValueError("Output type must be a non-empty string.")

        # Ensure script_path is valid
        script_path = script_path or self._get_nuke_script_path()
        if not script_path:
            print("Error: Unable to determine script path.")
            return None  # Early exit if script path is missing

        temp_dir = os.getenv("TEMP", "/tmp")  # Use system temp directory
        unique_id = uuid.uuid4().hex  # Generate a unique identifier

        job_info_path = os.path.join(temp_dir, f"{output_type}_nuke_deadline_job_{unique_id}.txt")
        plugin_info_path = os.path.join(temp_dir, f"{output_type}_nuke_deadline_plugin_{unique_id}.txt")

        # Create job info file with submission details
        self._write_job_info(job_info_path, output_type, node, output_file=output_file)

        # Create plugin info file with Nuke version and scene file
        self._write_plugin_info(plugin_info_path, script_path)

        return job_info_path, plugin_info_path

    def _build_temp_nuke_script(self, node):
        """Creates a new Nuke script in the same directory as the current script with a Read and Write node."""

        read_file_path = node["file"].value()

        # Ensure the current script is saved
        current_script_path = self._get_nuke_script_path()

        # Determine the directory and generate a new filename
        script_dir = os.path.dirname(current_script_path)
        base_name = pathlib.Path(current_script_path).stem
        script_number = 1

        new_script_dir = os.path.join(script_dir, "tmp")
        if not os.path.exists(new_script_dir):
            os.mkdir(new_script_dir)

        while True:
            new_script_name = f"{base_name}_tmp_{script_number:02d}.nk"
            new_script_path = os.path.join(new_script_dir, new_script_name)
            if not os.path.exists(new_script_path):
                break
            script_number += 1

        # Escape backslashes for Windows paths (Nuke uses Unix-style paths)
        read_file_path = read_file_path.replace("\\", "/")

        render_path = self._get_render_template(current_script_path)


        if not render_path:
            # Get the node's file path
            original_path = node["file"].value()
            original_dir = os.path.dirname(original_path)

            # Define the "review" folder inside the original directory
            review_dir = os.path.join(original_dir, "review")
            os.makedirs(review_dir, exist_ok=True)  # Ensure the folder exists

            # Extract filename without extension and frame numbers
            filename = os.path.basename(original_path)
            filename = re.sub(r"\.\d{4,}\.exr$", "", filename)  # Remove .####.exr

            # Construct new render path inside the "review" folder
            render_path = os.path.join(review_dir, f"{filename}.mov")

        # Determine Write node output path (same dir as Read file)
        if render_path:
            render_dir = os.path.dirname(render_path)
            os.makedirs(render_dir, exist_ok=True)  # Ensure the folder exists
            output_file_path = render_path.replace("\\", "/")
        elif read_file_path:
            output_dir = os.path.dirname(read_file_path)
            output_file_path = os.path.join(output_dir, "output.mov").replace("\\", "/")
        else:
            output_file_path = "/tmp/output.exr"  # Default location if no Read file is provided

        # Generate Nuke script content
        nuke_script_content = self._write_script_content(read_file_path, output_file_path, self._get_resources_dir())

        # Write the script to disk
        with open(new_script_path, "w") as script_file:
            script_file.write(nuke_script_content)

        return new_script_path, output_file_path

    @staticmethod
    def _build_submission_command(command, submission_files):
        """Adds job info and plugin info for each submission file."""
        for job_info, plugin_info in submission_files:
            command.extend(["-job", job_info, plugin_info])

    # ----------------------------------------
    # Write Methods
    # ----------------------------------------

    def _write_job_info(self, job_info_path, output_type, node, output_file=None):
        """Writes the job info file for Deadline submission."""
        script_path = self._get_nuke_script_path()
        render_type = "Movie" if output_type == "mov" else "Rendered Image"

        job_file_lines = [
                    "Plugin=Nuke\n",
                    f"Name={node.name()} - {render_type}\n",
                    f"BatchName={os.path.basename(script_path)}\n",
                    f"Frames={self.get_adjusted_frame_range()}\n",
                    f"ChunkSize={self.chunk_size.value() if output_type != 'mov' else 1000000}\n",
                    f"Priority={self.priority.value()}\n",
                    "Pool=none\n",
                    f"Department={self.department.value()}\n",
                    f"Comment={self.comment.value()}\n",
                    f"EnvironmentKeyValue0=OCIO={self._get_ocio_path()}\n",
                    f"OutputDirectory0={os.path.dirname(node['file'].value())}\n",
                ]

        if output_type == "exr":
            output_dir = os.path.dirname(node['file'].value())
            job_file_lines.append(f"OutputDirectory0={output_dir}\n")
        if output_type == "mov":
            job_file_lines.append(f"OutputDirectory1={os.path.dirname(output_file)}\n")

        with open(job_info_path, "w") as job_file:
            job_file.writelines(job_file_lines)

    @staticmethod
    def _write_plugin_info(plugin_info_path, script_path):
        """Writes the plugin info file for Deadline submission."""
        with open(plugin_info_path, "w") as plugin_file:
            plugin_file.writelines([
                f"SceneFile={script_path}\n",
                f"Version={nuke.NUKE_VERSION_MAJOR}.{nuke.NUKE_VERSION_MINOR}\n",
            ])

    def _write_script_content(self, read_file_path, output_file_path, resources_dir):
        """
        Reads a Nuke script template from a file and populates it with dynamic values.

        Args:
            read_file_path (str): Path to the input file for the Read node.
            output_file_path (str): Path for the output file in the Write node.
            resources_dir (Path): Path to the text file containing the Nuke script template.

        Returns:
            str: The populated Nuke script content.
        """
        try:
            # Extract frame range
            root_fr = self.frame_range.value()
            root_first, root_last = root_fr.split("-")
            read_fr = self.get_adjusted_frame_range()
            read_first, read_last =map(int, read_fr.split("-"))

            # Get OCIO path
            ocio_path = self._get_ocio_path()

            # Get project name
            ctx, tk = self._get_shotgrid_context()
            project = ctx.project.get("name")
            if project:
                file = f"burn_{project}.nk"
            else:
                file = "burn.nk"

            # Define paths
            burn_path = os.path.join(resources_dir, file)
            template_path = os.path.join(resources_dir, "nuke_template.txt")

            if self.add_burn.value():

                # Read burn file and skip the first two lines
                with open(burn_path, "r") as file:
                    lines = file.readlines()

                # Find the first occurrence of the target string
                for i, line in enumerate(lines):
                    if "push $cut_paste_input" in line:
                        filtered_lines = lines[i+1:]  # Keep everything after this line
                        break

                burn_content = "".join(filtered_lines)  # Join list into a string

            else:
                
                burn_content = ""

            # Read template file
            with open(template_path, "r") as file:
                nuke_script_template = file.read()

            # Populate template with values
            nuke_script_content = nuke_script_template.format(
                root_first=root_first,
                root_last=root_last,
                read_first=read_first,
                read_last=read_last,
                OCIO_PATH=ocio_path,
                read_file_path=read_file_path,
                output_file_path=output_file_path,
                burn_in_file=burn_content.strip()  # Remove leading/trailing newlines
            )

            return nuke_script_content

        except Exception as e:
            nuke.message(f"Error generating Nuke script: {e}")
            return None

    # ----------------------------------------
    # Utility Methods
    # ----------------------------------------
    @staticmethod
    def _check_write_has_files(write_node):
        """Checks if the output directory of a Nuke Write node exists and prompts the user to proceed."""
        try:
            file_path = write_node['cached_path'].value()
        except NameError:
            file_path = write_node['file'].value()

        output_dir = os.path.dirname(file_path)

        if not os.path.exists(output_dir):
            return True  # Directory does not exist

        if any(os.path.isfile(os.path.join(output_dir, f)) for f in os.listdir(output_dir)):
            return nuke.ask(f"Files found in directory:\n{output_dir}\nDo you want to proceed?")

    @staticmethod
    def _convert_write_nodes(nodes, direction):
        """
        Converts selected nodes between 'Write' and 'WriteTank' classes.

        Args:
            nodes (list): List of nodes to check and convert.
            direction (str): The direction of conversion, either "to" or "from".
                             "to" converts WriteTank nodes to Write nodes.
                             "from" converts Write nodes to WriteTank nodes.

        Returns:
            list: Updated list of nodes after conversion.
        """
        engine = sgtk.platform.current_engine()
        app = engine.apps.get("tk-nuke-writenode")

        if not app:
            return nodes  # Return original list if app is unavailable

        if direction not in {"to", "from"}:
            raise ValueError(f"Invalid direction '{direction}'. Use 'to' or 'from'.")

        updated_nodes = nodes.copy()  # Ensure we don't modify the input list directly

        if direction == "from":
            app.convert_from_write_nodes()
            return updated_nodes  # Conversion handled internally

        # Convert WriteTank nodes to Write nodes
        write_tank_nodes = [node for node in nodes if node.Class() == "WriteTank"]

        if not write_tank_nodes:
            return updated_nodes  # No conversion needed

        write_tank_names = [node.name() for node in write_tank_nodes]
        for node in write_tank_nodes:
            updated_nodes.remove(node)  # Remove from the list before conversion

        app.convert_to_write_nodes()

        for name in write_tank_names:
            converted_node = nuke.toNode(name)
            if converted_node:
                updated_nodes.append(converted_node)

        return updated_nodes  # Return the updated list

    @staticmethod
    def _deselect_and_disable_write_nodes(write_nodes):
        """Deselects and disables all write nodes in the list."""
        for node in write_nodes:
            node.setSelected(False)
            node['disable'].setValue(True)

    @staticmethod
    def _select_and_enable_write_node(write_node):
        """Selects and enables a single write node for rendering."""
        write_node.setSelected(True)
        write_node['disable'].setValue(False)

    @staticmethod
    def _deselect_non_write_nodes():
        """Deselects all nodes that are not of the 'Write' class."""
        all_nodes = nuke.allNodes()
        for node in all_nodes:
            if node.Class() != "Write":
                node.setSelected(False)  # Deselect non-Write nodes

    # ----------------------------------------
    # Execute Methods
    # ----------------------------------------

    def _execute_command(self, submission_files):
        """
        Executes the Deadline submission command with the provided submission files.
        Displays a Nuke message indicating whether the submission was successful or failed.

        Args:
            submission_files (list): List of tuples containing job info and plugin info file paths.
        """
        command = [self._get_deadline_command(), "-Multi", "-dependent"]
        self._build_submission_command(command, submission_files)

        result = subprocess.run(command, capture_output=True, text=True)
        self._handle_submission_result(result)

    @staticmethod
    def _handle_submission_result(result):
        """Handles the submission result and shows appropriate message."""
        if result.returncode != 0:
            nuke.message(f"Failed to submit to Deadline!\n{result.stderr}")
        else:
            nuke.message(f"Successfully submitted to Deadline!\n{result.stdout}")

    # ----------------------------------------
    # Exposed Methods
    # ----------------------------------------
    @staticmethod
    def show(send_selected: bool):
        """Displays the submission panel and executes the command based on user input."""
        panel = SubmitterPanel()
        panel.setMinimumSize(400, 100)

        # Show the panel and handle user input
        if not panel.showModalDialog():
            return  # Exit if the dialog was canceled or closed

        # Get the write nodes based on user selection
        write_nodes = panel._get_write_nodes(send_selected)

        if not write_nodes:
            nuke.message("No valid Write nodes selected. Please select at least one Write or WriteTank node.")
            return

        # Check if any write node should prevent proceeding
        if not any(SubmitterPanel._check_write_has_files(node) for node in write_nodes):
            return  # Exit early if a check fails

        # Convert write nodes
        write_nodes = panel._convert_write_nodes(write_nodes, "to")

        # Process nodes for submission
        SubmitterPanel._deselect_and_disable_write_nodes(write_nodes)
        SubmitterPanel._deselect_non_write_nodes()

        for write_node in write_nodes:
            SubmitterPanel._select_and_enable_write_node(write_node)

            # Gather submission files for the selected write node
            submission_files = panel._get_submission_files(write_node)

            # Execute the command to submit the job
            panel._execute_command(submission_files)

        # Convert sgtk back from Write
        panel._convert_write_nodes(write_nodes, "from")
