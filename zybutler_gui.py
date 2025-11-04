"""
Modern GUI for ZyButler. Imports logic from ZyButler.py.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import ZyButler
from PIL import Image, ImageTk
import os

class ZyButlerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ZyButler GUI")
        self.root.geometry("900x700")
        style = ttk.Style()
        style.theme_use('clam')

        # Bootstrap color palette
        BOOTSTRAP_PRIMARY = '#007bff'
        BOOTSTRAP_INFO = '#17a2b8'
        BOOTSTRAP_LIGHT = '#f8f9fa'
        BOOTSTRAP_BG = '#fff'
        BOOTSTRAP_BORDER = '#007bff'
        BOOTSTRAP_MUTED = '#6c757d'
        BOOTSTRAP_SHADOW = '#e9ecef'

        style.configure('TFrame', background=BOOTSTRAP_LIGHT)
        style.configure('TLabel', font=('Segoe UI', 12), background=BOOTSTRAP_LIGHT, foreground='#212529')
        style.configure('Header.TLabel', font=('Segoe UI', 24, 'bold'), foreground=BOOTSTRAP_PRIMARY, background=BOOTSTRAP_LIGHT)
        style.configure('Section.TLabelframe', background=BOOTSTRAP_BG, borderwidth=2, relief='groove')
        style.configure('Section.TLabelframe.Label', font=('Segoe UI', 16, 'bold'), foreground=BOOTSTRAP_PRIMARY, background=BOOTSTRAP_BG)
        style.configure('TEntry', font=('Segoe UI', 12), fieldbackground=BOOTSTRAP_LIGHT, foreground='#212529')
        style.configure('TCheckbutton', font=('Segoe UI', 12), background=BOOTSTRAP_BG, foreground='#212529')
        style.configure('TButton', font=('Segoe UI', 12, 'bold'), background=BOOTSTRAP_PRIMARY, foreground='#fff', borderwidth=0)
        style.map('TButton', background=[('active', BOOTSTRAP_INFO)], foreground=[('active', '#fff')])

        main_canvas = tk.Canvas(self.root, background=BOOTSTRAP_LIGHT, highlightthickness=0)
        main_scroll = ttk.Scrollbar(self.root, orient="vertical", command=main_canvas.yview)
        main_canvas.configure(yscrollcommand=main_scroll.set)
        main_scroll.pack(side="right", fill="y")
        main_canvas.pack(side="left", fill="both", expand=True)
        self.main_frame = ttk.Frame(main_canvas, padding=(32,24,32,24), style='TFrame')
        main_frame_id = main_canvas.create_window((0, 0), window=self.main_frame, anchor="nw", width=self.root.winfo_width())
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=0, minsize=32)

        def resize_main_frame(event):
            main_canvas.itemconfig(main_frame_id, width=event.width)
            # Show scrollbar only if content overflows
            bbox = main_canvas.bbox("all")
            if bbox and bbox[3] > event.height:
                main_scroll.pack(side="right", fill="y")
            else:
                main_scroll.pack_forget()
        main_canvas.bind("<Configure>", resize_main_frame)

        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        main_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        main_canvas.bind_all("<Button-4>", lambda e: main_canvas.yview_scroll(-1, "units"))  # Linux
        main_canvas.bind_all("<Button-5>", lambda e: main_canvas.yview_scroll(1, "units"))   # Linux

        # Load icons
        self.icon_add = self.load_icon('add.png', fallback='plus')
        self.icon_remove = self.load_icon('remove.png', fallback='minus')
        self.icon_copy = self.load_icon('copy.png', fallback='copy')
        self.icon_run = self.load_icon('run.png', fallback='play')

        ttk.Label(self.main_frame, text="ZyButler Android Test Runner", style='Header.TLabel').grid(row=0, column=0, columnspan=2, pady=(0, 24), sticky='ew', padx=(0,0))

        self.device_list = self.get_connected_devices()
        self.dut_vars = []
        self.flags = []
        self.custom_flags = []
        self.sttl_block = tk.StringVar()
        self.test_path = tk.StringVar(value="TS/ANDROID/")
        self.color_enabled = tk.BooleanVar(value=True)
        self.output_text = None

        self.build_gui()

    def load_icon(self, name, fallback=None):
        # Try to load PNG icon from local directory, fallback to unicode
        icon_path = os.path.join(os.path.dirname(__file__), name)
        try:
            img = Image.open(icon_path).resize((18,18))
            return ImageTk.PhotoImage(img)
        except Exception:
            if fallback == 'plus': return None
            if fallback == 'minus': return None
            if fallback == 'copy': return None
            if fallback == 'play': return None
            return None

    def get_connected_devices(self):
        try:
            result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
            lines = result.stdout.splitlines()
            devices = []
            for line in lines[1:]:
                if line.strip() and "device" in line:
                    serial = line.split()[0]
                    devices.append(serial)
            return devices
        except Exception:
            return []

    def build_gui(self):
        row_idx = 1
        # Device Section
        dut_frame = ttk.LabelFrame(self.main_frame, text="Android Devices (DUT serials)", style='Section.TLabelframe')
        self.style_section(dut_frame)
        dut_frame.grid(row=row_idx, column=0, columnspan=2, sticky='ew', padx=(10,20), pady=10)
        dut_frame.columnconfigure(0, weight=1)
        ttk.Label(dut_frame, text="Select or type device serial and press '+':").grid(row=0, column=0, sticky='w', padx=8, pady=(8,2))
        device_row = ttk.Frame(dut_frame)
        device_row.grid(row=1, column=0, sticky='ew')
        device_row.columnconfigure(0, weight=1)
        self.device_combobox = ttk.Combobox(device_row, values=self.device_list, width=24)
        self.device_combobox.grid(row=0, column=0, sticky='ew', padx=8, pady=4)
        self.device_combobox.set("")
        # Device add button
        add_btn_args = self.icon_or_text(self.icon_add, "+")
        ttk.Button(device_row, width=3, command=self.add_device, **add_btn_args).grid(row=0, column=1, padx=4)
        self.device_list_frame = ttk.Frame(dut_frame)
        self.device_list_frame.grid(row=2, column=0, sticky='ew', padx=8, pady=4)
        self.device_list_frame.columnconfigure(0, weight=1)
        self.refresh_device_list()
        row_idx += 1

        # Test Case Section
        sttl_frame = ttk.LabelFrame(self.main_frame, text="Test Cases (Paste any text containing STTL IDs)", style='Section.TLabelframe')
        self.style_section(sttl_frame)
        sttl_frame.grid(row=row_idx, column=0, columnspan=2, sticky='ew', padx=(10,20), pady=10)
        sttl_frame.columnconfigure(0, weight=1)
        ttk.Label(sttl_frame, text="Paste or type test case block (any format, IDs will be extracted):").grid(row=0, column=0, sticky='w', padx=8, pady=(8,2))
        sttl_entry = ttk.Entry(sttl_frame, textvariable=self.sttl_block, width=60)
        sttl_entry.grid(row=1, column=0, sticky='ew', padx=8, pady=4)
        ttk.Button(sttl_frame, text="Parse", width=8, command=self.parse_sttl_input).grid(row=2, column=0, sticky='w', padx=8, pady=2)
        self.test_list_frame = ttk.Frame(sttl_frame)
        self.test_list_frame.grid(row=3, column=0, sticky='ew', padx=8, pady=4)
        self.test_list_frame.columnconfigure(0, weight=1)
        self.test_ids = []
        self.refresh_test_list()
        row_idx += 1

        # Path Section
        path_frame = ttk.LabelFrame(self.main_frame, text="Test Path (default: TS/ANDROID/)", style='Section.TLabelframe')
        self.style_section(path_frame)
        path_frame.grid(row=row_idx, column=0, columnspan=2, sticky='ew', padx=(10,20), pady=10)
        path_frame.columnconfigure(0, weight=1)
        ttk.Label(path_frame, text="Test case path:").grid(row=0, column=0, sticky='w', padx=8, pady=(8,2))
        path_entry = ttk.Entry(path_frame, textvariable=self.test_path, width=60)
        path_entry.grid(row=1, column=0, sticky='ew', padx=8, pady=4)
        row_idx += 1

        # Flags Section
        flag_frame = ttk.LabelFrame(self.main_frame, text="zybot Flags", style='Section.TLabelframe')
        self.style_section(flag_frame)
        flag_frame.grid(row=row_idx, column=0, columnspan=2, sticky='ew', padx=(10,20), pady=10)
        flag_frame.columnconfigure(0, weight=1)
        ttk.Label(flag_frame, text="Common flags:").grid(row=0, column=0, sticky='w', padx=8, pady=(8,2))
        self.flag_vars = {}
        common_flags = ["-L TRACE", "--dryrun", "--outputdir Results", "--loglevel DEBUG"]
        flag_checks_frame = ttk.Frame(flag_frame)
        flag_checks_frame.grid(row=1, column=0, sticky='w', padx=8)
        for idx, flag in enumerate(common_flags):
            var = tk.BooleanVar()
            chk = ttk.Checkbutton(flag_checks_frame, text=flag, variable=var, command=self.update_command)
            chk.grid(row=0, column=idx, padx=4, sticky='w')
            self.flag_vars[flag] = var
        ttk.Label(flag_frame, text="Add custom flag:").grid(row=2, column=0, sticky='w', padx=8, pady=(8,2))
        custom_flag_row = ttk.Frame(flag_frame)
        custom_flag_row.grid(row=3, column=0, sticky='ew')
        custom_flag_row.columnconfigure(0, weight=1)
        self.custom_flag_var = tk.StringVar()
        custom_flag_entry = ttk.Entry(custom_flag_row, textvariable=self.custom_flag_var, width=40)
        custom_flag_entry.grid(row=0, column=0, sticky='ew', padx=8, pady=4)
        # Custom flag add button
        add_flag_btn_args = self.icon_or_text(self.icon_add, "+")
        ttk.Button(custom_flag_row, width=3, command=self.add_custom_flag, **add_flag_btn_args).grid(row=0, column=1, padx=4)
        self.custom_flag_list_frame = ttk.Frame(flag_frame)
        self.custom_flag_list_frame.grid(row=4, column=0, sticky='ew', padx=8, pady=4)
        self.custom_flag_list_frame.columnconfigure(0, weight=1)
        self.refresh_custom_flag_list()
        row_idx += 1

        # Output Section
        output_frame = ttk.LabelFrame(self.main_frame, text="Resulting zybot Command", style='Section.TLabelframe')
        self.style_section(output_frame)
        output_frame.grid(row=row_idx, column=0, columnspan=2, sticky='ew', padx=(10,20), pady=10)
        output_frame.columnconfigure(0, weight=1)
        self.command_var = tk.StringVar()
        cmd_entry = ttk.Entry(output_frame, textvariable=self.command_var, font=('Consolas', 12), state='readonly', width=60)
        cmd_entry.grid(row=0, column=0, sticky='ew', padx=8, pady=8)
        btns_row = ttk.Frame(output_frame)
        btns_row.grid(row=0, column=1, sticky='e', padx=8)
        # Copy and run buttons
        copy_btn_args = self.icon_or_text(self.icon_copy, "Copy")
        run_btn_args = self.icon_or_text(self.icon_run, "Run zybot")
        ttk.Button(btns_row, command=self.copy_command, **copy_btn_args).pack(side='left', padx=8)
        ttk.Button(btns_row, command=self.run_zybot, **run_btn_args).pack(side='left', padx=8)

    def icon_or_text(self, icon, text):
        return {'image': icon, 'text': text, 'compound': 'left'} if icon else {'text': text}

    def add_device(self):
        serial = self.device_combobox.get().strip()
        if serial and serial not in self.dut_vars:
            self.dut_vars.append(serial)
            self.refresh_device_list()
            self.device_combobox.set("")

    def refresh_device_list(self):
        for widget in self.device_list_frame.winfo_children():
            widget.destroy()
        for idx, serial in enumerate(self.dut_vars):
            btn_args = self.icon_or_text(self.icon_remove, "-")
            row = ttk.Frame(self.device_list_frame)
            ttk.Label(row, text=serial).pack(side='left', padx=4)
            ttk.Button(row, width=3, command=lambda i=idx: self.remove_device(i), **btn_args).pack(side='left', padx=4)
            row.pack(anchor='w', pady=2)

    def remove_device(self, idx):
        self.dut_vars.pop(idx)
        self.refresh_device_list()
        self.update_command()

    def parse_sttl_input(self):
        raw = self.sttl_block.get().strip()
        ids = ZyButler.parse_sttl_ids_any(raw)
        self.test_ids = ids
        self.refresh_test_list()
        self.update_command()

    def refresh_test_list(self):
        for widget in self.test_list_frame.winfo_children():
            widget.destroy()
        for idx, tid in enumerate(self.test_ids):
            btn_args = self.icon_or_text(self.icon_remove, "-")
            row = ttk.Frame(self.test_list_frame)
            ttk.Label(row, text=tid).pack(side='left', padx=4)
            ttk.Button(row, width=3, command=lambda i=idx: self.remove_test_id(i), **btn_args).pack(side='left', padx=4)
            row.pack(anchor='w', pady=2)

    def remove_test_id(self, idx):
        self.test_ids.pop(idx)
        self.refresh_test_list()
        self.update_command()

    def add_custom_flag(self):
        flag = self.custom_flag_var.get().strip()
        if flag and flag not in self.custom_flags:
            self.custom_flags.append(flag)
            self.refresh_custom_flag_list()
            self.custom_flag_var.set("")
            self.update_command()

    def refresh_custom_flag_list(self):
        for widget in self.custom_flag_list_frame.winfo_children():
            widget.destroy()
        for idx, flag in enumerate(self.custom_flags):
            btn_args = self.icon_or_text(self.icon_remove, "-")
            row = ttk.Frame(self.custom_flag_list_frame)
            ttk.Label(row, text=flag).pack(side='left', padx=4)
            ttk.Button(row, width=3, command=lambda i=idx: self.remove_custom_flag(i), **btn_args).pack(side='left', padx=4)
            row.pack(anchor='w', pady=2)

    def remove_custom_flag(self, idx):
        self.custom_flags.pop(idx)
        self.refresh_custom_flag_list()
        self.update_command()

    def style_section(self, frame):
        # Style for section frames to match Bootstrap
        frame.configure(style='Section.TLabelframe')
        frame['borderwidth'] = 2
        frame['relief'] = 'groove'

    def update_command(self):
        dut_tokens = [f"DUT{idx+1}:{serial}" for idx, serial in enumerate(self.dut_vars)]
        path = self.test_path.get().strip() or None
        flags = []
        for flag, var in self.flag_vars.items():
            if var.get():
                flags.append(flag)
        flags.extend(self.custom_flags)
        if not self.test_ids:
            self.command_var.set("")
            return
        cmd_obj = ZyButler.build_command(dut_tokens, self.test_ids, path, allow_empty_vars=True, flags=flags)
        self.command_var.set(cmd_obj.display_command())

    def copy_command(self):
        cmd = self.command_var.get()
        if cmd:
            self.root.clipboard_clear()
            self.root.clipboard_append(cmd)
            self.root.update()
            messagebox.showinfo("Copied", "Command copied to clipboard.")

    def run_zybot(self):
        cmd = self.command_var.get()
        if not cmd:
            messagebox.showerror("Error", "No command to run.")
            return
        # Build ZybotCommand object for execution
        dut_tokens = [f"DUT{idx+1}:{serial}" for idx, serial in enumerate(self.dut_vars)]
        path = self.test_path.get().strip() or None
        flags = []
        for flag, var in self.flag_vars.items():
            if var.get():
                flags.append(flag)
        flags.extend(self.custom_flags)
        cmd_obj = ZyButler.build_command(dut_tokens, self.test_ids, path, allow_empty_vars=True, flags=flags)
        rc = ZyButler.execute(cmd_obj)
        messagebox.showinfo("zybot finished", f"Execution finished with code {rc}")

def main():
    root = tk.Tk()
    app = ZyButlerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
