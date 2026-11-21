"""The Code Agent desktop window (tkinter).

One small window: a password-style field for the DeepSeek API key,
file pickers for the two input documents, a task description line, an
output-folder picker, Run and Stop buttons, a scrolling log, and a
live cost readout. It calls the same agent loop the command line
uses. No separate code path.

The loop runs in a worker thread so the window stays responsive.
Shell commands outside the safe list ask the user to confirm first:
the worker thread posts the question to a queue, the main thread
shows the dialog, and the answer goes back to the worker.
"""

import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import Budget, preprocess, run_agent  # noqa: E402


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Code Agent")
        self.geometry("720x620")
        self.resizable(True, True)

        self.api_key_var = tk.StringVar()
        self.doc_var = tk.StringVar()
        self.view_var = tk.StringVar()
        self.task_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.cost_var = tk.StringVar(value="Spent $0.0000 of $0.90 cap")

        self.event_queue = queue.Queue()
        self.confirm_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.worker = None

        self._build_widgets()
        self.after(100, self._poll)

    # ------------------------------------------------------------ widgets

    def _build_widgets(self):
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(frame, text="DeepSeek API key:").grid(row=row, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.api_key_var, show="*").grid(
            row=row, column=1, sticky="ew", padx=(6, 0)
        )
        row += 1
        ttk.Label(frame, text="Architecture doc:").grid(row=row, column=0, sticky="w")
        self._picker_row(frame, row, self.doc_var, "Browse...", self._pick_doc)
        row += 1
        ttk.Label(frame, text="Architecture views:").grid(row=row, column=0, sticky="w")
        self._picker_row(frame, row, self.view_var, "Browse...", self._pick_view)
        row += 1
        ttk.Label(frame, text="Task (optional):").grid(row=row, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.task_var).grid(
            row=row, column=1, sticky="ew", padx=(6, 0)
        )
        row += 1
        ttk.Label(frame, text="Output folder:").grid(row=row, column=0, sticky="w")
        self._picker_row(frame, row, self.output_var, "Browse...", self._pick_output)
        row += 1

        buttons = ttk.Frame(frame)
        buttons.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(10, 6))
        self.run_button = ttk.Button(buttons, text="Run", command=self._on_run)
        self.run_button.pack(side=tk.LEFT)
        self.stop_button = ttk.Button(
            buttons, text="Stop", command=self._on_stop, state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=(6, 0))
        ttk.Label(buttons, textvariable=self.cost_var).pack(side=tk.RIGHT)
        row += 1

        self.log = tk.Text(frame, height=20, wrap=tk.WORD, state=tk.DISABLED)
        self.log.grid(row=row, column=0, columnspan=2, sticky="nsew")
        frame.rowconfigure(row, weight=1)
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.log.yview)
        scrollbar.grid(row=row, column=2, sticky="ns")
        self.log.configure(yscrollcommand=scrollbar.set)

    def _picker_row(self, frame, row, var, button_text, command):
        entry = ttk.Entry(frame, textvariable=var)
        entry.grid(row=row, column=1, sticky="ew", padx=(6, 0))
        ttk.Button(frame, text=button_text, command=command).grid(
            row=row, column=2, padx=(6, 0)
        )

    # ------------------------------------------------------------ pickers

    def _pick_doc(self):
        path = filedialog.askopenfilename(
            title="Architecture document", filetypes=[("Markdown", "*.md"), ("All files", "*.*")]
        )
        if path:
            self.doc_var.set(path)

    def _pick_view(self):
        path = filedialog.askopenfilename(
            title="Architecture views", filetypes=[("Markdown", "*.md"), ("All files", "*.*")]
        )
        if path:
            self.view_var.set(path)

    def _pick_output(self):
        path = filedialog.askdirectory(title="Output folder")
        if path:
            self.output_var.set(path)

    # ------------------------------------------------------------ run/stop

    def _on_run(self):
        api_key = self.api_key_var.get().strip()
        doc = self.doc_var.get().strip()
        view = self.view_var.get().strip()
        output = self.output_var.get().strip()
        if not api_key:
            messagebox.showerror("Missing API key", "Enter your DeepSeek API key first.")
            return
        if not doc or not view:
            messagebox.showerror(
                "Missing input", "Pick both architecture documents first."
            )
            return
        if not output:
            messagebox.showerror("Missing output", "Pick an output folder first.")
            return
        try:
            spec = preprocess(doc, view)
        except (FileNotFoundError, ValueError) as exc:
            messagebox.showerror("Cannot read input", str(exc))
            return
        self._log("Starting. Input documents parsed.\n")
        self.stop_event.clear()
        self.run_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL)
        self.worker = threading.Thread(
            target=self._run_in_thread,
            args=(spec, api_key, output, self.task_var.get().strip()),
            daemon=True,
        )
        self.worker.start()

    def _run_in_thread(self, spec, api_key, output, extra_instructions):
        budget = Budget()

        def on_event(kind, text):
            self.event_queue.put((kind, text))

        result = run_agent(
            spec,
            work_dir=output,
            output_dir=output,
            api_key=api_key,
            budget=budget,
            on_event=on_event,
            confirm=self._confirm_from_worker,
            extra_instructions=extra_instructions or None,
            stop_event=self.stop_event,
        )
        self.event_queue.put(("finished", result))

    def _on_stop(self):
        self.stop_event.set()
        self._log("Stopping after the current step...\n")

    # ------------------------------------------------- worker/main-thread bridge

    def _confirm_from_worker(self, command):
        """Asked by the loop (worker thread) for shell commands to confirm."""
        answer = {}
        done = threading.Event()
        self.confirm_queue.put((command, answer, done))
        done.wait()
        return bool(answer.get("yes", False))

    def _poll(self):
        # Log and cost events from the worker thread.
        while True:
            try:
                kind, text = self.event_queue.get_nowait()
            except queue.Empty:
                break
            if kind == "finished":
                self._on_finished(text)
            elif kind == "cost":
                self.cost_var.set(text)
            else:
                self._log("[{}] {}\n".format(kind, text))
        # Confirmation requests: the dialog must open on the main thread.
        while True:
            try:
                command, answer, done = self.confirm_queue.get_nowait()
            except queue.Empty:
                break
            answer["yes"] = messagebox.askyesno(
                "Confirm shell command",
                "The agent wants to run:\n\n{}\n\nAllow it?".format(command),
            )
            done.set()
        self.after(100, self._poll)

    def _on_finished(self, result):
        self.cost_var.set(result.budget.summary())
        self._log("\nStatus: {}\n".format(result.status))
        self._log("Turns: {}\n".format(result.turns))
        self._log("Cost: {}\n".format(result.budget.summary()))
        self._log("Files written: {}\n".format(len(result.files_written)))
        for name in result.files_written:
            self._log("  - {}\n".format(name))
        self._log("\n{}\n".format(result.final_text))
        self.run_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)

    def _log(self, text):
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, text)
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
