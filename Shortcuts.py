### For finding .exe and .ink files in specified location


import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import win32com.client 

class ShortcutCopierApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced File Copier & Shortcut Creator")
        self.root.geometry("650x700")
        self.root.minsize(500, 500)

        self.root.configure(bg="#1e1e1e")

        self.source_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.filter_type = tk.StringVar(value="Both (.lnk/.ink & .exe)")
        self.search_query = tk.StringVar()

        # Track all found items: {'path': str, 'var': tk.BooleanVar, 'cb': tk.Checkbutton, 'visible': bool}
        self.found_files = []

        self.setup_dark_styles()
        self.create_widgets()

        # Trace search bar changes for a live search experience
        self.search_query.trace_add("write", self.filter_search)

    def setup_dark_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('default')
        self.style.configure("TCombobox",
                             fieldbackground="#2d2d2d",
                             background="#3d3d3d",
                             foreground="#ffffff",
                             arrowcolor="#ffffff",
                             bordercolor="#3d3d3d")
        self.root.option_add("*TCombobox*Listbox.background", "#2d2d2d")
        self.root.option_add("*TCombobox*Listbox.foreground", "#ffffff")
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#008CBA")

    def create_widgets(self):
        # --- Top Section: Configuration ---
        top_frame = tk.LabelFrame(
            self.root, text=" Configuration ", padx=10, pady=10,
            bg="#1e1e1e", fg="#ffffff", font=("Arial", 10, "bold")
        )
        top_frame.pack(fill="x", padx=15, pady=10)

        # Source
        tk.Label(top_frame, text="Source Folder:", bg="#1e1e1e", fg="#ffffff").grid(row=0, column=0, sticky="w", pady=2)
        tk.Entry(top_frame, textvariable=self.source_dir, width=45, bg="#2d2d2d", fg="#ffffff",
                 insertbackground="white", bd=1).grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        tk.Button(top_frame, text="Browse...", command=self.browse_source, bg="#3d3d3d", fg="#ffffff",
                  activebackground="#4d4d4d", activeforeground="#ffffff").grid(row=0, column=2, pady=2)

        # Output
        tk.Label(top_frame, text="Output Folder:", bg="#1e1e1e", fg="#ffffff").grid(row=1, column=0, sticky="w", pady=2)
        tk.Entry(top_frame, textvariable=self.output_dir, width=45, bg="#2d2d2d", fg="#ffffff",
                 insertbackground="white", bd=1).grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        tk.Button(top_frame, text="Browse...", command=self.browse_output, bg="#3d3d3d", fg="#ffffff",
                  activebackground="#4d4d4d", activeforeground="#ffffff").grid(row=1, column=2, pady=2)

        # File type Filter
        tk.Label(top_frame, text="Process Types:", bg="#1e1e1e", fg="#ffffff").grid(row=2, column=0, sticky="w", pady=5)
        options = ["Shortcuts Only (.lnk/.ink)", "EXEs Only (.exe)", "Both (.lnk/.ink & .exe)"]
        filter_menu = ttk.Combobox(top_frame, textvariable=self.filter_type, values=options, state="readonly", width=30)
        filter_menu.grid(row=2, column=1, columnspan=2, sticky="w", padx=5, pady=5)

        top_frame.columnconfigure(1, weight=1)

        # --- Search & Global Select Section ---
        search_frame = tk.Frame(self.root, bg="#1e1e1e")
        search_frame.pack(fill="x", padx=15, pady=(5, 5))

        tk.Label(search_frame, text="Search:", bg="#1e1e1e", fg="#ffffff", font=("Arial", 10, "bold")).pack(side="left",
                                                                                                            padx=(0, 5))
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_query, bg="#2d2d2d", fg="#ffffff",
                                     insertbackground="white", bd=1)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.select_all_btn = tk.Button(search_frame, text="Select All", command=self.select_all, state="disabled",
                                        bg="#3d3d3d", fg="#ffffff", disabledforeground="#777777")
        self.select_all_btn.pack(side="left", padx=2)

        self.deselect_all_btn = tk.Button(search_frame, text="Deselect All", command=self.deselect_all,
                                          state="disabled", bg="#3d3d3d", fg="#ffffff", disabledforeground="#777777")
        self.deselect_all_btn.pack(side="left", padx=2)

        # --- Middle Section: Scan Action & Results ---
        action_frame = tk.Frame(self.root, bg="#1e1e1e")
        action_frame.pack(fill="x", padx=15, pady=(5, 0))
        tk.Button(action_frame, text="🔍 Scan Folder", command=self.scan_folder, bg="#008CBA", fg="white",
                  font=("Arial", 10, "bold"), activebackground="#005f73", activeforeground="white").pack(fill="x")

        # Preview Frame (Scrollable)
        preview_label_frame = tk.LabelFrame(
            self.root, text=" Found Files (Unchecked items will be skipped) ",
            bg="#1e1e1e", fg="#ffffff", font=("Arial", 10, "bold")
        )
        preview_label_frame.pack(fill="both", expand=True, padx=15, pady=10)

        self.canvas = tk.Canvas(preview_label_frame, borderwidth=0, highlightthickness=0, background="#2d2d2d")
        self.scrollbar = ttk.Scrollbar(preview_label_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, background="#2d2d2d")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind_all("<MouseWheel>",
                             lambda event: self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))

        # --- Bottom Section: Execution ---
        self.copy_btn = tk.Button(
            self.root,
            text="🚀 Process Selected Files",
            command=self.copy_files,
            bg="#2e7d32",
            fg="white",
            font=("Arial", 12, "bold"),
            state="disabled",
            disabledforeground="#777777",
            activebackground="#1b5e20",
            activeforeground="white",
            pady=8
        )
        self.copy_btn.pack(fill="x", padx=15, pady=15)

    def browse_source(self):
        folder = filedialog.askdirectory(title="Select Source Folder")
        if folder:
            self.source_dir.set(folder)

    def browse_output(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_dir.set(folder)

    def scan_folder(self):
        src = self.source_dir.get()
        if not src or not os.path.exists(src):
            messagebox.showwarning("Error", "Please select a valid source folder first.")
            return

        # Clear old items
        for item in self.found_files:
            item['cb'].destroy()
        self.found_files.clear()
        self.search_query.set("")  # Reset search on new scan

        choice = self.filter_type.get()
        valid_extensions = []
        if "Shortcuts" in choice or "Both" in choice:
            valid_extensions.extend(['.lnk', '.ink'])
        if "EXEs" in choice or "Both" in choice:
            valid_extensions.append('.exe')

        for root_dir, _, files in os.walk(src):
            for file in files:
                if any(file.lower().endswith(ext) for ext in valid_extensions):
                    full_path = os.path.join(root_dir, file)
                    var = tk.BooleanVar(value=True)
                    rel_path = os.path.relpath(full_path, src)

                    cb = tk.Checkbutton(
                        self.scrollable_frame,
                        text=rel_path,
                        variable=var,
                        bg="#2d2d2d",
                        fg="#ffffff",
                        selectcolor="#1e1e1e",
                        activebackground="#3d3d3d",
                        activeforeground="#ffffff",
                        anchor="w",
                        justify="left"
                    )
                    cb.pack(fill="x", anchor="w", padx=5, pady=2)

                    self.found_files.append({
                        'path': full_path,
                        'rel_path': rel_path,
                        'var': var,
                        'cb': cb,
                        'visible': True
                    })

        if not self.found_files:
            messagebox.showinfo("No Matches", "No matching files found.")
            self.copy_btn.config(state="disabled")
            self.select_all_btn.config(state="disabled")
            self.deselect_all_btn.config(state="disabled")
        else:
            self.copy_btn.config(state="normal")
            self.select_all_btn.config(state="normal")
            self.deselect_all_btn.config(state="normal")

    def filter_search(self, *args):
        query = self.search_query.get().lower()
        for item in self.found_files:
            if query in item['rel_path'].lower():
                if not item['visible']:
                    item['cb'].pack(fill="x", anchor="w", padx=5, pady=2)
                    item['visible'] = True
            else:
                if item['visible']:
                    item['cb'].pack_forget()
                    item['visible'] = False

    def select_all(self):
        for item in self.found_files:
            if item['visible']:  # Only affects items visible under current search filter
                item['var'].set(True)

    def deselect_all(self):
        for item in self.found_files:
            if item['visible']:  # Only affects items visible under current search filter
                item['var'].set(False)

    def create_shortcut(self, target_path, dest_folder):
        """Creates an actual Windows shortcut file (.lnk) pointing to an EXE."""
        shell = win32com.client.Dispatch("WScript.Shell")

        base_name = os.path.splitext(os.path.basename(target_path))[0]
        shortcut_name = f"{base_name} - Shortcut.lnk"
        dest_file = os.path.join(dest_folder, shortcut_name)

        # Handle duplicate naming conflicts
        counter = 1
        while os.path.exists(dest_file):
            shortcut_name = f"{base_name} - Shortcut ({counter}).lnk"
            dest_file = os.path.join(dest_folder, shortcut_name)
            counter += 1

        shortcut = shell.CreateShortCut(dest_file)
        shortcut.TargetPath = target_path
        shortcut.WorkingDirectory = os.path.dirname(target_path)
        shortcut.IconLocation = target_path  # Assigns the target EXE's native icon
        shortcut.Save()

    def copy_files(self):
        dest = self.output_dir.get()
        if not dest or not os.path.exists(dest):
            messagebox.showwarning("Error", "Please select a valid output folder.")
            return

        # Target checked items that are currently active
        selected_items = [f for f in self.found_files if f['var'].get()]

        if not selected_items:
            messagebox.showwarning("Selection Empty", "No items have been selected.")
            return

        copied_count = 0
        shortcut_count = 0
        error_count = 0

        for item in selected_items:
            src_file = item['path']
            try:
                filename = os.path.basename(src_file)

                # Condition A: It's an executable file -> Create shortcut instead of copying
                if src_file.lower().endswith('.exe'):
                    self.create_shortcut(src_file, dest)
                    shortcut_count += 1

                # Condition B: It's already a shortcut -> Safely copy it over
                else:
                    dest_file = os.path.join(dest, filename)
                    if os.path.exists(dest_file):
                        base, ext = os.path.splitext(filename)
                        counter = 1
                        while os.path.exists(dest_file):
                            dest_file = os.path.join(dest, f"{base}_{counter}{ext}")
                            counter += 1
                    shutil.copy2(src_file, dest_file)
                    copied_count += 1

            except Exception:
                error_count += 1

        msg = f"Operation complete!\n\n• Existing shortcuts copied: {copied_count}\n• New shortcuts generated from EXEs: {shortcut_count}"
        if error_count > 0:
            msg += f"\n• Failures (Permissions/System errors): {error_count}"

        messagebox.showinfo("Success", msg)


if __name__ == "__main__":
    root = tk.Tk()
    app = ShortcutCopierApp(root)
    root.mainloop()
