import tkinter as tk
import tkinter.font as tkfont
import json
import sys
import os

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.style import Style  # Explicitly import Style for theme_names
except ImportError:
    print(
        "Warning: ttkbootstrap not installed. Falling back to classic ttk with 'default' theme."
    )
    from tkinter import ttk  # Corrected import for classic ttk

if os.name == "nt":
    import ctypes

    try:
        import darkdetect  # For detecting system theme as a fallback
    except ImportError:
        darkdetect = None
        print(
            "Warning: darkdetect not installed. Title bar color may not match system theme perfectly."
        )
    # Set DPI awareness before creating the Tkinter window
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # System DPI Aware
    except AttributeError:
        print("Warning: DPI awareness not set; shcore.dll might not be available.")

# Manual mapping of ttkbootstrap themes to dark/light status
TTKBOOTSTRAP_DARK_THEMES = {
    "cosmo",
    "darkly",
    "cyborg",
    "superhero",
    "vapor",
    "solar",
    "minty",
    "pulse",
}  # Based on ttkbootstrap documentation/source


class InfluxDataCleaner:
    def __init__(self, root, config_manager, data_manager, state_file):
        self.root = root
        self.config_manager = config_manager
        self.data_manager = data_manager
        self.state_file = state_file  # Use the state file passed from main
        self.entity_config = self.config_manager.get_entities()
        self.influxdb_config = self.config_manager.get_influxdb_config()

        self.root.title("InfluxDB Data Cleaner")
        self.root.geometry("1280x1024")  # Increased size for better visibility

        # Set window icon using .png (cross-platform)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.png_path = os.path.join(script_dir, "app_icon.png")
        if os.path.exists(self.png_path):
            try:
                icon_image = tk.PhotoImage(file=self.png_path)
                self.root.iconphoto(True, icon_image)
            except tk.TclError as e:
                print(f"Warning: Failed to set .png icon: {e}")
        else:
            print(f"Warning: Icon file 'app_icon.png' not found at {self.png_path}")

        # Adjusted grid configuration for single column since logo moves inside frame
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=0)
        self.root.grid_rowconfigure(2, weight=0)
        self.root.grid_rowconfigure(3, weight=1)
        self.root.grid_rowconfigure(4, weight=0)
        self.root.grid_rowconfigure(5, weight=0)
        self.root.grid_rowconfigure(6, weight=0)
        self.root.grid_columnconfigure(0, weight=1)

        # Initialize style and set initial theme
        if "ttkbootstrap" in sys.modules:
            self.style = ttk.Style(theme="darkly")  # Default to 'darkly'
            self.available_themes = list(self.style.theme_names())
        else:
            self.style = ttk.Style()  # Use classic ttk style
            self.available_themes = ["default"]

        self.initial_theme = self.get_initial_theme()
        if self.initial_theme in self.available_themes:
            self.style.theme_use(self.initial_theme)
        else:
            self.style.theme_use(
                "darkly" if "ttkbootstrap" in sys.modules else "default"
            )

        self.setup_gui()
        self.load_state()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        # Schedule title bar update after GUI is fully initialized, passing self.root
        self.root.after(100, lambda: self.update_title_bar_color(self.root))

    def get_initial_theme(self):
        """Load the initial theme from state file or return default."""
        default_theme = "darkly" if "ttkbootstrap" in sys.modules else "default"
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    content = f.read().strip()  # Read and strip whitespace
                    if not content:  # If file is empty
                        print(
                            f"State file '{self.state_file}' is empty. Using default theme: {default_theme}"
                        )
                        return default_theme
                    state = json.loads(content)  # Parse JSON
                    saved_theme = state.get("theme", default_theme)
                    if saved_theme in self.available_themes:
                        return saved_theme
                    else:
                        print(
                            f"Saved theme '{saved_theme}' not available, using {default_theme}"
                        )
                        return default_theme
            except (json.JSONDecodeError, ValueError) as e:
                print(
                    f"Invalid state file '{self.state_file}': {e}. Using default theme: {default_theme}"
                )
                return default_theme
        return default_theme

    def setup_gui(self):
        # Query Settings Frame
        query_frame = ttk.LabelFrame(self.root, text="Query Settings")
        query_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        # Column configuration for controls and logo
        query_frame.columnconfigure(0, weight=0)  # Labels
        query_frame.columnconfigure(1, weight=1)  # Entry/combobox
        query_frame.columnconfigure(2, weight=0)  # Unit label
        query_frame.columnconfigure(3, weight=0)  # Unit value
        query_frame.columnconfigure(4, weight=0)  # Edit Config button
        query_frame.columnconfigure(5, weight=0)  # Logo

        # Entity ID (row 0)
        ttk.Label(query_frame, text="Entity ID:").grid(
            row=0, column=0, padx=5, pady=5, sticky="e"
        )
        self.entity_var = tk.StringVar(value="hichi_gth_sml_total_in")
        self.entity_combo = ttk.Combobox(
            query_frame, textvariable=self.entity_var, state="readonly"
        )
        self.entity_combo["values"] = list(self.entity_config.keys())
        self.entity_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.entity_combo.bind(
            "<<ComboboxSelected>>", lambda e: (self.update_config(), self.save_state())
        )
        self._set_combobox_width(self.entity_combo, self.entity_config.keys())

        # Unit (row 0)
        ttk.Label(query_frame, text="Unit:").grid(row=0, column=2, padx=5, pady=5)
        self.unit_var = tk.StringVar(
            value=self.entity_config[self.entity_var.get()]["unit"]
        )
        self.unit_label = ttk.Label(query_frame, textvariable=self.unit_var)
        self.unit_label.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        # Edit Config Button (row 0)
        ttk.Button(
            query_frame,
            text="Edit Config",
            command=self.open_config_window,
            takefocus=0,
        ).grid(row=0, column=4, padx=5, pady=5)

        # Start Time Range (row 1)
        ttk.Label(query_frame, text="Start Time Range: now()").grid(
            row=1, column=0, padx=5, pady=5, sticky="e"
        )
        self.start_time_var = tk.StringVar(value="-200d")
        ttk.Entry(query_frame, textvariable=self.start_time_var).grid(
            row=1, column=1, padx=5, pady=5, sticky="ew", columnspan=4
        )
        self.start_time_var.trace_add("write", lambda *args: self.save_state())

        # End Time Range (row 2)
        ttk.Label(query_frame, text="End Time Range: now()").grid(
            row=2, column=0, padx=5, pady=5, sticky="e"
        )
        self.end_time_var = tk.StringVar(value="0d")
        ttk.Entry(query_frame, textvariable=self.end_time_var).grid(
            row=2, column=1, padx=5, pady=5, sticky="ew", columnspan=4
        )
        self.end_time_var.trace_add("write", lambda *args: self.save_state())

        # Context Size (row 3)
        ttk.Label(query_frame, text="Context Size:").grid(
            row=3, column=0, padx=5, pady=5, sticky="e"
        )
        self.context_var = tk.IntVar(value=2)
        ttk.Spinbox(
            query_frame,
            from_=0,
            to=10,
            textvariable=self.context_var,
            width=5,
            command=lambda: (self.update_context_height(), self.save_state()),
        ).grid(row=3, column=1, padx=5, pady=5, sticky="w")

        # Logo Display (inside query frame, right side)
        logo_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "logo_large.png"
        )
        if os.path.exists(logo_path):
            try:
                self.logo_image = tk.PhotoImage(file=logo_path)
                logo_label = tk.Label(query_frame, image=self.logo_image)
                logo_label.grid(row=0, column=5, rowspan=4, padx=10, pady=5, sticky="n")
            except tk.TclError as e:
                print(f"Warning: Failed to load logo_large.png: {e}")
        else:
            print(f"Warning: Logo file 'logo_large.png' not found at {logo_path}")

        # Rest of the GUI below the query frame
        check_frame = ttk.LabelFrame(self.root, text="Check Type")
        check_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        self.check_var = tk.StringVar(value="bounds")
        ttk.Radiobutton(
            check_frame,
            text="Bounds Check",
            variable=self.check_var,
            value="bounds",
            command=self.update_check_ui,
        ).grid(row=0, column=0, padx=5, pady=5)
        ttk.Radiobutton(
            check_frame,
            text="Monotonicity Check",
            variable=self.check_var,
            value="monotonicity",
            command=self.update_check_ui,
        ).grid(row=0, column=1, padx=5, pady=5)

        self.bounds_frame = ttk.LabelFrame(self.root, text="Value Bounds")
        self.bounds_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        ttk.Label(self.bounds_frame, text="Min Value:").grid(
            row=0, column=0, padx=5, pady=5
        )
        self.min_var = tk.DoubleVar(
            value=self.entity_config[self.entity_var.get()]["min"]
        )
        ttk.Entry(self.bounds_frame, textvariable=self.min_var).grid(
            row=0, column=1, padx=5, pady=5
        )

        ttk.Label(self.bounds_frame, text="Max Value:").grid(
            row=0, column=2, padx=5, pady=5
        )
        self.max_var = tk.DoubleVar(
            value=self.entity_config[self.entity_var.get()]["max"]
        )
        ttk.Entry(self.bounds_frame, textvariable=self.max_var).grid(
            row=0, column=3, padx=5, pady=5
        )

        ttk.Button(
            self.bounds_frame, text="Save", command=self.save_bounds, takefocus=0
        ).grid(row=0, column=4, padx=5, pady=5)

        self.results_frame = ttk.LabelFrame(self.root, text="Detected Anomalies")
        self.results_frame.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")

        self.tree = ttk.Treeview(
            self.results_frame, columns=("Time", "Value", "Action"), show="headings"
        )
        self.tree.heading("Time", text="Timestamp")
        self.tree.heading("Value", text="Value")
        self.tree.heading("Action", text="Action")
        self.tree.column("Time", width=200)
        self.tree.column("Value", width=100)
        self.tree.column("Action", width=100)

        scrollbar = ttk.Scrollbar(
            self.results_frame, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.update_context_display)

        self.context_frame = ttk.LabelFrame(self.root, text="Selected Anomaly Context")
        self.context_frame.grid(row=4, column=0, padx=10, pady=5, sticky="ew")

        self.context_tree = ttk.Treeview(
            self.context_frame,
            columns=("Type", "Time", "Value"),
            show="headings",
            height=self.calculate_context_height(),
        )
        self.context_tree.heading("Type", text="Type")
        self.context_tree.heading("Time", text="Timestamp")
        self.context_tree.heading("Value", text="Value")
        self.context_tree.column("Type", width=80)
        self.context_tree.column("Time", width=300)
        self.context_tree.column("Value", width=100)

        context_scrollbar = ttk.Scrollbar(
            self.context_frame, orient="vertical", command=self.context_tree.yview
        )
        self.context_tree.configure(yscrollcommand=context_scrollbar.set)
        self.context_tree.pack(side="left", fill="x", expand=True)
        context_scrollbar.pack(side="right", fill="y")

        btn_frame = ttk.Frame(self.root)
        btn_frame.grid(row=5, column=0, padx=10, pady=5, sticky="ew")

        ttk.Button(btn_frame, text="Scan", command=self.scan_data, takefocus=0).pack(
            side="left", padx=5
        )
        ttk.Button(
            btn_frame, text="Delete Selected", command=self.delete_selected, takefocus=0
        ).pack(side="left", padx=5)

        ttk.Label(btn_frame, text="Fix Method:").pack(side="left", padx=5)
        self.fix_method_var = tk.StringVar(value="Previous Value")
        fix_method_options = (
            "Previous Value",
            "Next Value",
            "Average of Previous and Next",
        )
        fix_method_combo = ttk.Combobox(
            btn_frame, textvariable=self.fix_method_var, state="readonly"
        )
        fix_method_combo["values"] = fix_method_options
        self._set_combobox_width(fix_method_combo, fix_method_options)
        fix_method_combo.pack(side="left", padx=5)
        fix_method_combo.bind("<<ComboboxSelected>>", lambda e: self.save_state())

        ttk.Button(
            btn_frame, text="Fix Selected", command=self.fix_selected, takefocus=0
        ).pack(side="left", padx=5)

        ttk.Label(btn_frame, text="Theme:").pack(side="left", padx=5)
        self.theme_var = tk.StringVar(value=self.initial_theme)
        theme_combo = ttk.Combobox(
            btn_frame,
            textvariable=self.theme_var,
            values=self.available_themes,
            state="readonly",
        )
        self._set_combobox_width(theme_combo, self.available_themes)
        theme_combo.pack(side="left", padx=5)
        theme_combo.bind("<<ComboboxSelected>>", self.change_theme)

        self.status_bar = ttk.Label(self.root, text="", relief="sunken", anchor="w")
        self.status_bar.grid(row=6, column=0, sticky="ew", padx=10, pady=5)

    def _set_combobox_width(self, combobox, items):
        font = tkfont.Font(font=combobox["font"])
        longest_width = max(font.measure(item) for item in items)
        char_width = font.measure("0")
        combobox.config(width=max(20, longest_width // char_width + 2))

    def is_theme_dark(self, theme_name):
        """Check if the selected theme is dark based on manual mapping or fallback."""
        if "ttkbootstrap" in sys.modules:
            return theme_name in TTKBOOTSTRAP_DARK_THEMES
        # Fallback: use darkdetect or assume light if not available
        if darkdetect is not None:
            return darkdetect.isDark()
        return False  # Default to light if no better info

    def update_title_bar_color(self, window):
        """Update the title bar color based on the current theme (Windows only)."""
        if os.name != "nt":  # Only apply on Windows
            return

        theme = self.theme_var.get()
        is_dark = self.is_theme_dark(theme)

        # Use Windows API to set title bar color
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20  # Windows 10+ attribute for dark mode
        value = 1 if is_dark else 0  # 1 for dark, 0 for light
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(ctypes.c_int(value)),
            ctypes.sizeof(ctypes.c_int),
        )

    def change_theme(self, event):
        theme = self.theme_var.get()
        if theme in self.available_themes and theme != "default":
            self.style.theme_use(theme)
        else:
            self.style.theme_use(
                "default"
            )  # Fall back to default ttkbootstrap or classic ttk theme
        self.update_title_bar_color(self.root)  # Update main window
        if hasattr(self, "config_window") and self.config_window.winfo_exists():
            self.update_title_bar_color(
                self.config_window
            )  # Update config window if open
        self.set_status(f"Theme changed to {theme}", "success")
        self.save_state()

    def set_status(self, message, status_type="info"):
        colors = {
            "info": "black",
            "success": "green",
            "warning": "orange",
            "error": "red",
        }
        self.status_bar.config(
            text=message, foreground=colors.get(status_type, "black")
        )
        self.root.after(5000, lambda: self.status_bar.config(text=""))

    def save_bounds(self):
        entity_id = self.entity_var.get()
        if not entity_id or entity_id not in self.entity_config:
            self.set_status("No valid entity selected", "warning")
            return
        try:
            min_val = self.min_var.get()
            max_val = self.max_var.get()
        except tk.TclError:
            self.set_status("Min and Max must be numbers", "error")
            return
        if min_val > max_val:
            self.set_status("Min value cannot be greater than Max value", "error")
            return
        self.entity_config[entity_id]["min"] = min_val
        self.entity_config[entity_id]["max"] = max_val
        self.config_manager.save_config(
            {"influxdb": self.influxdb_config, "entities": self.entity_config}
        )
        self.set_status(f"Bounds for {entity_id} saved", "success")

    def open_config_window(self):
        config_window = tk.Toplevel(self.root)
        self.config_window = config_window  # Store reference to track it
        config_window.title("Edit Configuration")
        config_window.geometry("800x800")  # Set to 800x800 as requested

        # Notebook for tabs
        notebook = ttk.Notebook(config_window)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # Entities Tab (first and default)
        entities_frame = ttk.Frame(notebook)
        notebook.add(entities_frame, text="Entities")

        # Grid configuration for entities_frame
        entities_frame.grid_rowconfigure(0, weight=1)  # Treeview row expands
        entities_frame.grid_rowconfigure(1, weight=0)  # Edit frame row stays fixed
        entities_frame.grid_columnconfigure(0, weight=1)

        # Frame for Treeview and Scrollbar
        tree_frame = ttk.Frame(entities_frame)
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Entities Treeview with Scrollbar
        tree = ttk.Treeview(
            tree_frame, columns=("Entity ID", "Unit", "Min", "Max"), show="headings"
        )
        tree.heading("Entity ID", text="Entity ID")
        tree.heading("Unit", text="Unit")
        tree.heading("Min", text="Min Value")
        tree.heading("Max", text="Max Value")
        tree.column("Entity ID", width=200)
        tree.column("Unit", width=100)
        tree.column("Min", width=100)
        tree.column("Max", width=100)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for entity, config in self.entity_config.items():
            tree.insert(
                "", "end", values=(entity, config["unit"], config["min"], config["max"])
            )

        # Edit frame for entity details and buttons
        edit_frame = ttk.Frame(entities_frame)
        edit_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

        # Configure grid for centered layout in edit_frame
        edit_frame.columnconfigure(0, weight=1)
        edit_frame.columnconfigure(1, weight=1)
        edit_frame.columnconfigure(2, weight=1)
        edit_frame.columnconfigure(3, weight=1)

        ttk.Label(edit_frame, text="Entity ID:").grid(
            row=0, column=0, padx=5, sticky="e"
        )
        entity_entry = ttk.Entry(edit_frame)
        entity_entry.grid(row=0, column=1, padx=5, sticky="ew")

        ttk.Label(edit_frame, text="Unit:").grid(row=0, column=2, padx=5, sticky="e")
        unit_entry = ttk.Entry(edit_frame)
        unit_entry.grid(row=0, column=3, padx=5, sticky="ew")

        ttk.Label(edit_frame, text="Min:").grid(row=1, column=0, padx=5, sticky="e")
        min_entry = ttk.Entry(edit_frame)
        min_entry.grid(row=1, column=1, padx=5, sticky="ew")

        ttk.Label(edit_frame, text="Max:").grid(row=1, column=2, padx=5, sticky="e")
        max_entry = ttk.Entry(edit_frame)
        max_entry.grid(row=1, column=3, padx=5, sticky="ew")

        # Button frame for centered buttons
        button_frame = ttk.Frame(edit_frame)
        button_frame.grid(row=2, column=0, columnspan=4, pady=5)

        def fill_fields(event):
            selected = tree.selection()
            if selected:
                entity_id, unit, min_val, max_val = tree.item(selected[0])["values"]
                entity_entry.delete(0, tk.END)
                entity_entry.insert(0, entity_id)
                unit_entry.delete(0, tk.END)
                unit_entry.insert(0, unit)
                min_entry.delete(0, tk.END)
                min_entry.insert(0, min_val)
                max_entry.delete(0, tk.END)
                max_entry.insert(0, max_val)

        tree.bind("<<TreeviewSelect>>", fill_fields)

        def save_entity():
            entity_id = entity_entry.get().strip()
            unit = unit_entry.get().strip()
            try:
                min_val = float(min_entry.get())
                max_val = float(max_entry.get())
            except ValueError:
                self.set_status("Min and Max must be numbers", "error")
                return
            if not entity_id or not unit:
                self.set_status("Entity ID and Unit cannot be empty", "error")
                return
            self.entity_config[entity_id] = {
                "unit": unit,
                "min": min_val,
                "max": max_val,
            }
            tree.delete(*tree.get_children())
            for entity, config in self.entity_config.items():
                tree.insert(
                    "",
                    "end",
                    values=(entity, config["unit"], config["min"], config["max"]),
                )
            entity_entry.delete(0, tk.END)
            unit_entry.delete(0, tk.END)
            min_entry.delete(0, tk.END)
            max_entry.delete(0, tk.END)
            self.config_manager.save_config(
                {"influxdb": self.influxdb_config, "entities": self.entity_config}
            )
            self.update_entity_combo()
            self.set_status(f"Entity {entity_id} saved", "success")

        def delete_entity():
            selected = tree.selection()
            if not selected:
                self.set_status("No entity selected", "warning")
                return
            entity_id = tree.item(selected[0])["values"][0]
            del self.entity_config[entity_id]
            tree.delete(selected[0])
            entity_entry.delete(0, tk.END)
            unit_entry.delete(0, tk.END)
            min_entry.delete(0, tk.END)
            max_entry.delete(0, tk.END)
            self.config_manager.save_config(
                {"influxdb": self.influxdb_config, "entities": self.entity_config}
            )
            self.update_entity_combo()
            self.set_status(f"Entity {entity_id} deleted", "success")

        ttk.Button(
            button_frame, text="Save Entity", command=save_entity, takefocus=0
        ).pack(side="left", padx=5)
        ttk.Button(
            button_frame, text="Delete Selected", command=delete_entity, takefocus=0
        ).pack(side="left", padx=5)

        # InfluxDB Config Tab (second)
        influxdb_frame = ttk.Frame(notebook)
        notebook.add(influxdb_frame, text="InfluxDB Config")

        ttk.Label(influxdb_frame, text="Host:").grid(
            row=0, column=0, padx=5, pady=5, sticky="e"
        )
        self.host_entry = ttk.Entry(influxdb_frame)
        self.host_entry.insert(0, self.influxdb_config["host"])
        self.host_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(influxdb_frame, text="Port:").grid(
            row=1, column=0, padx=5, pady=5, sticky="e"
        )
        self.port_entry = ttk.Entry(influxdb_frame)
        self.port_entry.insert(0, self.influxdb_config["port"])
        self.port_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(influxdb_frame, text="Username:").grid(
            row=2, column=0, padx=5, pady=5, sticky="e"
        )
        self.username_entry = ttk.Entry(influxdb_frame)
        self.username_entry.insert(0, self.influxdb_config["username"])
        self.username_entry.grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(influxdb_frame, text="Password:").grid(
            row=3, column=0, padx=5, pady=5, sticky="e"
        )
        self.password_entry = ttk.Entry(influxdb_frame, show="*")
        self.password_entry.insert(0, self.influxdb_config["password"])
        self.password_entry.grid(row=3, column=1, padx=5, pady=5)

        ttk.Label(influxdb_frame, text="Database:").grid(
            row=4, column=0, padx=5, pady=5, sticky="e"
        )
        self.database_entry = ttk.Entry(influxdb_frame)
        self.database_entry.insert(0, self.influxdb_config["database"])
        self.database_entry.grid(row=4, column=1, padx=5, pady=5)

        ttk.Button(
            influxdb_frame,
            text="Save InfluxDB Config",
            command=self.save_influxdb_config,
        ).grid(row=5, column=0, columnspan=2, pady=10)

        # Select Entities tab by default
        notebook.select(entities_frame)

        # Update title bar color for config window after initialization
        config_window.after(100, lambda: self.update_title_bar_color(config_window))

    def save_influxdb_config(self):
        """Save the InfluxDB configuration from the UI."""
        try:
            port = int(self.port_entry.get())
            if port < 1 or port > 65535:
                raise ValueError("Port must be between 1 and 65535")
        except ValueError:
            self.set_status("Port must be a valid number between 1 and 65535", "error")
            return

        host = self.host_entry.get().strip()
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        database = self.database_entry.get().strip()

        if not all([host, username, password, database]):
            self.set_status("All InfluxDB fields must be filled", "error")
            return

        self.influxdb_config = {
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "database": database,
        }
        self.config_manager.save_config(
            {"influxdb": self.influxdb_config, "entities": self.entity_config}
        )
        self.set_status("InfluxDB configuration saved", "success")

    def update_entity_combo(self):
        self.entity_combo["values"] = list(self.entity_config.keys())
        if self.entity_var.get() not in self.entity_config:
            self.entity_var.set(
                list(self.entity_config.keys())[0] if self.entity_config else ""
            )
        self._set_combobox_width(self.entity_combo, self.entity_config.keys())
        self.update_config()

    def calculate_context_height(self):
        context_size = self.context_var.get()
        return max(5, 2 * context_size + 1)

    def update_context_height(self):
        new_height = self.calculate_context_height()
        self.context_tree.config(height=new_height)

    def update_config(self, event=None):
        entity = self.entity_var.get()
        if entity in self.entity_config:
            config = self.entity_config[entity]
            self.unit_var.set(config["unit"])
            self.min_var.set(config["min"])
            self.max_var.set(config["max"])

    def update_check_ui(self):
        if self.check_var.get() == "bounds":
            self.bounds_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        else:
            self.bounds_frame.grid_forget()

    def update_context_display(self, event):
        self.context_tree.delete(*self.context_tree.get_children())
        selected = self.tree.selection()
        if selected:
            idx = self.tree.index(selected[0])
            anomaly = self.data_manager.anomalies[idx]
            for t, v in reversed(anomaly["context_before"]):
                self.context_tree.insert("", "end", values=("Before", t, v))
            self.context_tree.insert(
                "", "end", values=("Anomaly", anomaly["time"], anomaly["value"])
            )
            for t, v in anomaly["context_after"]:
                self.context_tree.insert("", "end", values=("After", t, v))

    def save_state(self):
        state = {
            "start_time": self.start_time_var.get(),
            "end_time": self.end_time_var.get(),
            "fix_method": self.fix_method_var.get(),
            "entity_id": self.entity_var.get(),
            "context_size": self.context_var.get(),
            "theme": (
                self.theme_var.get()
                if hasattr(self, "theme_var")
                else ("darkly" if "ttkbootstrap" in sys.modules else "default")
            ),
        }
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=4)

    def load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    content = f.read().strip()  # Read and strip whitespace
                    if not content:  # If file is empty, skip loading
                        print(
                            f"State file '{self.state_file}' is empty. Skipping state load."
                        )
                        return
                    state = json.loads(content)  # Parse JSON
                    self.start_time_var.set(state.get("start_time", "-200d"))
                    self.end_time_var.set(state.get("end_time", "0d"))
                    self.fix_method_var.set(state.get("fix_method", "Previous Value"))
                    entity_id = state.get("entity_id", "hichi_gth_sml_total_in")
                    self.entity_var.set(
                        entity_id
                        if entity_id in self.entity_config
                        else (
                            list(self.entity_config.keys())[0]
                            if self.entity_config
                            else ""
                        )
                    )
                    self.context_var.set(state.get("context_size", 2))
                    self.update_config()
                    self.update_context_height()
            except (json.JSONDecodeError, ValueError) as e:
                print(
                    f"Invalid state file '{self.state_file}': {e}. Skipping state load."
                )

    def on_closing(self):
        self.save_state()
        self.root.destroy()

    def scan_data(self):
        self.tree.delete(*self.tree.get_children())
        self.context_tree.delete(*self.context_tree.get_children())
        anomalies = self.data_manager.scan_data(
            unit=self.unit_var.get(),
            entity_id=self.entity_var.get(),
            start_time=self.start_time_var.get(),
            end_time=self.end_time_var.get(),
            context_size=self.context_var.get(),
            check_type=self.check_var.get(),
            min_val=self.min_var.get(),
            max_val=self.max_var.get(),
        )
        for anomaly in anomalies:
            self.tree.insert(
                "", "end", values=(anomaly["time"], anomaly["value"], "None")
            )
        self.set_status(f"Found {len(anomalies)} anomalies", "info")

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            self.set_status("No items selected to delete", "warning")
            return
        indices = [self.tree.index(item) for item in selected]
        deleted_count = self.data_manager.delete_selected(indices)
        for item in selected:
            self.tree.item(
                item,
                values=(
                    self.tree.item(item)["values"][0],
                    self.tree.item(item)["values"][1],
                    "Deleted",
                ),
            )
        self.update_context_display(None)
        self.set_status(f"Deleted {deleted_count} item(s)", "success")

    def fix_selected(self):
        selected = self.tree.selection()
        if not selected:
            self.set_status("No items selected to fix", "warning")
            return
        indices = [self.tree.index(item) for item in selected]
        success_count, errors = self.data_manager.fix_selected(
            indices, self.fix_method_var.get()
        )
        for item in selected:
            idx = self.tree.index(item)
            anomaly = self.data_manager.anomalies[idx]
            self.tree.item(
                item,
                values=(
                    anomaly["time"],
                    anomaly["value"],
                    "Fixed" if not errors else "Error",
                ),
            )
        self.update_context_display(None)
        if errors:
            self.set_status("\n".join(errors), "warning")
        elif success_count == len(selected):
            self.set_status(
                f"All {len(selected)} item(s) fixed successfully", "success"
            )
        else:
            self.set_status(
                f"{success_count} of {len(selected)} item(s) fixed successfully",
                "success",
            )
