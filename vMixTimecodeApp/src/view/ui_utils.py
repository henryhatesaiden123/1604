import tkinter as tk

def is_focusable_widget(w):
    return isinstance(w, (tk.Entry, tk.Button, tk.Checkbutton))

def bind_entry_extended_events(entry, mode="timecode"):
    entry._drag_y = None
    entry._drag_in_progress = False
    entry._tc_idx = 2
    entry._tc_positions = [2, 5, 8]
    entry._tc_mode = (mode in ["timecode", "set_time"])

    def select_all(event):
        entry.after(1, lambda: entry.select_range(0, tk.END))
        entry.after(1, lambda: entry.icursor(tk.END))
    entry.bind("<FocusIn>", select_all, add="+")

    if entry._tc_mode:
        entry.bind("<FocusIn>", lambda e: set_tc_cursor(entry), add="+")
        entry.bind("<Shift-Left>", lambda e: tc_shift_move(entry, -1))
        entry.bind("<Shift-Right>", lambda e: tc_shift_move(entry, 1))
        entry.bind("<Shift-Up>", lambda e: tc_shift_incdec(entry, 1))
        entry.bind("<Shift-Down>", lambda e: tc_shift_incdec(entry, -1))
        entry.bind("<Return>", lambda e, en=entry: timecode_zero_autofill(en, app_instance=en.winfo_toplevel().nametowidget(".")))
    elif mode == "button":
        entry.bind("<Shift-Up>", lambda e: button_incdec(entry, 1))
        entry.bind("<Shift-Down>", lambda e: button_incdec(entry, -1))

def set_tc_cursor(entry):
    val = entry.get()
    if not val or len(val) != 8:
        return
    idx = getattr(entry, "_tc_idx", 2)
    pos = [2, 5, 8][idx]
    entry.icursor(pos)

def tc_shift_move(entry, delta):
    if entry.cget("state") in ("readonly", "disabled"):
        return "break"
    idx = getattr(entry, "_tc_idx", 2)
    idx = (idx + delta) % 3
    entry._tc_idx = idx
    set_tc_cursor(entry)
    return "break"

def tc_shift_incdec(entry, delta):
    if entry.cget("state") in ("readonly", "disabled"):
        return "break"
    val = entry.get()
    if not val or len(val) != 8 or val[2] != ":" or val[5] != ":":
        return "break"
    
    idx = getattr(entry, "_tc_idx", 2)
    try:
        h, m, s = map(int, val.split(":"))
    except ValueError:
        return "break"

    if idx == 0:
        h = (h + delta) % 24
    elif idx == 1:
        m = (m + delta) % 60
    else:
        s = (s + delta) % 60
    
    new_tc = f"{h:02d}:{m:02d}:{s:02d}"
    entry.delete(0, tk.END)
    entry.insert(0, new_tc)
    set_tc_cursor(entry)
    return "break"

def button_incdec(entry, delta):
    if entry.cget("state") in ("readonly", "disabled"):
        return "break"
    val = entry.get().strip()
    v = 0
    if val.isdigit():
        v = int(val)
    
    v = max(0, v + delta)
    entry.delete(0, tk.END)
    entry.insert(0, str(v))
    return "break"

def timecode_zero_autofill(entry, app_instance=None):
    if entry.cget("state") in ("readonly", "disabled"):
        return "break"
    val = entry.get().strip()

    if len(val) == 6 and val.isdigit():
        try:
            h = int(val[0:2])
            m = int(val[2:4])
            s = int(val[4:6])
            if not (0 <= h <= 23 and 0 <= m <= 59 and 0 <= s <= 59):
                if app_instance and hasattr(app_instance, 'push_error'):
                    app_instance.push_error(f"시간 값 오류: {h:02d}:{m:02d}:{s:02d}")
                return None
            
            formatted_val = f"{val[0:2]}:{val[2:4]}:{val[4:6]}"
            entry.delete(0, tk.END)
            entry.insert(0, formatted_val)
            entry.icursor(tk.END)
            return "break"
        except ValueError:
            return None

    if val == "0":
        entry.delete(0, tk.END)
        entry.insert(0, "00:00:00")
        entry.icursor(tk.END)
        return "break"

    return None

def bind_widget_full_navigation(widget, row_idx, col_idx, app):
    def on_key(event):
        dir_map = {
            "Up":    (-1, 0), "Down":  (1, 0),
            "Left":  (0, -1), "Right": (0, 1)
        }
        if event.state & 0x1: return None
        if event.keysym in dir_map:
            dr, dc = dir_map[event.keysym]
            r, c = row_idx, col_idx
            max_rows = len(app.widget_matrix)
            max_cols = len(app.widget_matrix[0]) if max_rows > 0 else 0
            for _ in range(max_rows * max_cols):
                r_new, c_new = r + dr, c + dc
                if dr != 0: r_new %= max_rows
                if dc != 0: c_new %= max_cols
                target = app.get_widget_by_rowcol(r_new, c_new)
                if target and target.winfo_ismapped() and target.cget('state') != 'disabled' and is_focusable_widget(target):
                    target.focus_set()
                    if isinstance(target, tk.Entry):
                        target.select_range(0, tk.END)
                        target.icursor(tk.END)
                    return "break"
                r, c = r_new, c_new
            return "break"
    for k in ["<Up>", "<Down>", "<Left>", "<Right>"]:
        widget.bind(k, on_key)

class StatusCircleBar(tk.Frame):
    def __init__(self, master, get_status_callback, status_items, *args, **kwargs):
        super().__init__(master, bg="black", *args, **kwargs)
        self.get_status = get_status_callback
        self.status_items = status_items
        self.labels = []
        self._create_widgets()
        self.update_status()

    def _create_widgets(self):
        for lbl, canvas in self.labels:
            lbl.destroy()
            canvas.destroy()
        self.labels.clear()
        
        for short, _ in self.status_items:
            lbl = tk.Label(self, text=short, fg="white", bg="black", font=("Helvetica", 13), width=2)
            canvas = tk.Canvas(self, width=16, height=16, bg="black", highlightthickness=0)
            lbl.pack(side=tk.LEFT, padx=(2,0))
            canvas.pack(side=tk.LEFT, padx=(0,10))
            self.labels.append((lbl, canvas))

    def update_labels(self, new_status_items):
        self.status_items = new_status_items
        self._create_widgets()

    def update_status(self):
        status = self.get_status()
        colors = {0: "yellow", 1: "red", 2: "lime"}
        for idx, (_, canvas) in enumerate(self.labels):
            color = colors.get(status[idx] if idx < len(status) else 0, "yellow")
            canvas.delete("all")
            canvas.create_oval(2, 2, 14, 14, fill=color, outline="gray")
        self.after(1000, self.update_status)
