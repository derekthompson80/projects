"""
Typing Speed Test — Tkinter Desktop App

Run it:
  python projects\Typing_test\type_speed_test.py

What it does:
- Shows a sample passage to type.
- Starts the timer on your first keystroke.
- Computes live WPM and accuracy as you type.
- Highlights mismatched characters.
- Buttons for Reset and Next Text.

WPM formula used (standard):
  WPM = (correct_characters / 5) / minutes_elapsed
Accuracy:
  accuracy% = (correct_characters / max(1, typed_characters)) * 100
"""
from __future__ import annotations

import random
import time
import tkinter as tk
from tkinter import ttk, messagebox


SAMPLE_TEXTS = [
    "The quick brown fox jumps over the lazy dog.",
    "Typing is a fundamental skill that improves with consistent practice.",
    "Python makes it easy to build powerful applications with concise code.",
    "Discipline equals freedom. Small steps taken daily lead to big results.",
    "In the middle of difficulty lies opportunity. Keep learning and building.",
    "Simplicity is the soul of efficiency. Write code for humans first, then machines.",
]


class TypingTestApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Typing Speed Test")
        self.geometry("900x520")
        self.minsize(760, 480)

        # State
        self.target_text: str = random.choice(SAMPLE_TEXTS)
        self.start_time: float | None = None
        self.elapsed: float = 0.0
        self.timer_running: bool = False
        self.update_job: str | None = None

        self._build_ui()
        self._bind_events()
        self._load_text(self.target_text)

    # --- UI ---
    def _build_ui(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(3, weight=1)

        # Header
        title = ttk.Label(container, text="Typing Speed Test", font=("Segoe UI", 16, "bold"))
        title.grid(row=0, column=0, sticky="w")

        # Controls row
        controls = ttk.Frame(container)
        controls.grid(row=1, column=0, sticky="ew", pady=(6, 10))
        controls.columnconfigure(4, weight=1)

        ttk.Label(controls, text="Sample:").grid(row=0, column=0, padx=(0, 6))
        self.sample_var = tk.StringVar(value=self.target_text)
        self.sample_combo = ttk.Combobox(controls, textvariable=self.sample_var, values=SAMPLE_TEXTS, state="readonly")
        self.sample_combo.grid(row=0, column=1, sticky="ew")
        self.sample_combo.bind("<<ComboboxSelected>>", lambda e: self._on_choose_text())

        self.btn_next = ttk.Button(controls, text="Next Text", command=self._next_text)
        self.btn_next.grid(row=0, column=2, padx=6)

        self.btn_reset = ttk.Button(controls, text="Reset", command=self._reset)
        self.btn_reset.grid(row=0, column=3)

        # Stats row
        stats = ttk.Frame(container)
        stats.grid(row=2, column=0, sticky="ew", pady=(0, 6))

        self.time_var = tk.StringVar(value="Time: 0.0s")
        self.wpm_var = tk.StringVar(value="WPM: 0.0")
        self.acc_var = tk.StringVar(value="Accuracy: 100.0%")

        ttk.Label(stats, textvariable=self.time_var, width=16).pack(side=tk.LEFT)
        ttk.Label(stats, textvariable=self.wpm_var, width=14).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Label(stats, textvariable=self.acc_var, width=20).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Label(stats, text="Tip: Timer starts on first keypress. Use Reset to try again.", foreground="#666").pack(side=tk.RIGHT)

        # Target text (read-only Text with tags for styling, line-wrapped)
        self.target = tk.Text(container, height=5, wrap=tk.WORD, padx=8, pady=8, relief=tk.FLAT, bg="#0b1220", fg="#e5e7eb")
        self.target.grid(row=3, column=0, sticky="nsew")
        self.target.configure(state=tk.DISABLED)

        # Typed text (user input)
        self.input = tk.Text(container, height=6, wrap=tk.WORD, padx=8, pady=8)
        self.input.grid(row=4, column=0, sticky="nsew", pady=(8, 0))

        # Configure tags for highlighting in input
        self.input.tag_configure("ok", foreground="#10b981")
        self.input.tag_configure("bad", foreground="#ef4444", underline=1)
        self.input.tag_configure("pending", foreground="#9ca3af")

        # Footer
        footer = ttk.Frame(container)
        footer.grid(row=5, column=0, sticky="ew", pady=(8, 0))
        ttk.Label(footer, text="Correct chars are green. Mistakes are red and underlined.", foreground="#666").pack(side=tk.LEFT)

    def _bind_events(self) -> None:
        self.input.bind("<KeyPress>", self._on_keypress, add=True)
        self.input.bind("<<Modified>>", self._on_modified, add=True)

    # --- Logic ---
    def _on_choose_text(self) -> None:
        chosen = self.sample_var.get()
        self._load_text(chosen)
        self._reset(start_fresh=False)

    def _next_text(self) -> None:
        # Pick a different random sample
        candidates = [t for t in SAMPLE_TEXTS if t != self.target_text]
        if not candidates:
            candidates = SAMPLE_TEXTS[:]
        self._load_text(random.choice(candidates))
        self._reset(start_fresh=False)

    def _load_text(self, text: str) -> None:
        self.target_text = text
        self.sample_var.set(text)
        self.target.configure(state=tk.NORMAL)
        self.target.delete("1.0", tk.END)
        self.target.insert("1.0", text)
        self.target.configure(state=tk.DISABLED)

    def _reset(self, start_fresh: bool = True) -> None:
        # Stop timer
        self.timer_running = False
        self.start_time = None
        self.elapsed = 0.0
        if self.update_job:
            try:
                self.after_cancel(self.update_job)
            except Exception:
                pass
            self.update_job = None
        # Clear input and stats
        self.input.delete("1.0", tk.END)
        self.time_var.set("Time: 0.0s")
        self.wpm_var.set("WPM: 0.0")
        self.acc_var.set("Accuracy: 100.0%")
        # Focus input
        self.input.focus_set()
        if start_fresh:
            messagebox.showinfo("Ready", "Start typing to begin the test.")

    def _on_keypress(self, event) -> None:
        # Start timer on first real keypress (ignore modifiers)
        if not self.timer_running and event.keysym not in ("Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R"):
            self.start_time = time.perf_counter()
            self.timer_running = True
            self._tick()

    def _on_modified(self, event=None) -> None:
        # Reset Tk modified flag
        self.input.edit_modified(False)
        self._recompute_and_highlight()

    def _tick(self) -> None:
        if not self.timer_running:
            return
        now = time.perf_counter()
        if self.start_time is not None:
            self.elapsed = max(0.0, now - self.start_time)
        self.time_var.set(f"Time: {self.elapsed:.1f}s")
        self._recompute_and_highlight()
        self.update_job = self.after(100, self._tick)  # update ~10 times per second

    def _recompute_and_highlight(self) -> None:
        typed = self.input.get("1.0", tk.END).rstrip("\n")
        target = self.target_text

        # Compute correct characters compared positionally
        correct_chars = 0
        for i, ch in enumerate(typed):
            if i < len(target) and ch == target[i]:
                correct_chars += 1

        typed_chars = len(typed)
        minutes = max(1e-9, self.elapsed / 60.0)
        wpm = (correct_chars / 5.0) / minutes if self.timer_running else 0.0
        accuracy = (correct_chars / max(1, typed_chars)) * 100.0 if typed_chars > 0 else 100.0

        self.wpm_var.set(f"WPM: {wpm:.1f}")
        self.acc_var.set(f"Accuracy: {accuracy:.1f}%")

        # Highlight input
        self.input.tag_remove("ok", "1.0", tk.END)
        self.input.tag_remove("bad", "1.0", tk.END)
        self.input.tag_remove("pending", "1.0", tk.END)

        # Apply tags per character
        for i, ch in enumerate(typed):
            idx_start = f"1.0+{i}c"
            idx_end = f"1.0+{i+1}c"
            if i < len(target):
                if ch == target[i]:
                    self.input.tag_add("ok", idx_start, idx_end)
                else:
                    self.input.tag_add("bad", idx_start, idx_end)
            else:
                # Extra characters beyond target
                self.input.tag_add("bad", idx_start, idx_end)

        # Optionally show remaining target as pending gray ghost text in the title bar or status
        # Here we keep UI clean and just color what you typed.

        # If finished (all chars match and lengths equal), stop timer
        if typed == target and typed_chars == len(target) and len(target) > 0 and self.timer_running:
            self.timer_running = False
            # One last stats refresh to freeze values with final elapsed
            minutes = max(1e-9, self.elapsed / 60.0)
            final_wpm = (len(target) / 5.0) / minutes
            self.wpm_var.set(f"WPM: {final_wpm:.1f}")
            messagebox.showinfo("Completed", f"You finished!\nWPM: {final_wpm:.1f}\nAccuracy: {accuracy:.1f}%\nTime: {self.elapsed:.1f}s")


def main() -> int:
    app = TypingTestApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
