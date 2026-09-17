import queue
from tkinter import BOTH, END, LEFT, RIGHT, VERTICAL, Y, Text
from tkinter.ttk import Frame

from ttkbootstrap import Scrollbar

from generalsmodbuilder.gui.theme import AMBER, EMBER, FIELD, FONT_MONO, FOREGROUND, MUTED, TEAL

NORMAL = ""
WARNING = "warning"
ERROR = "error"

# Enough scrollback to hold a full build without growing without bound.
MAX_LINES = 5000

# Lines moved into the widget per tick, so that a noisy build cannot stall the window.
DRAIN_LIMIT = 400


def ClassifyLine(line: str) -> str:
    """
    The severity of one output line. The builder writes 'Warning: ...' and, when a job
    raises, 'ERROR CALLSTACK' followed by a traceback.
    """
    stripped: str = line.lstrip().lower()
    if stripped.startswith("warning"):
        return WARNING
    if stripped.startswith("error") or stripped.startswith("traceback"):
        return ERROR
    return NORMAL


class LineBuffer:
    """
    Collects written text and hands out whole lines. A severity is decided per line, and
    print writes its text and its newline separately, so partial writes have to be held.
    """

    def __init__(self):
        self.pending = ""

    def Add(self, text: str) -> list[str]:
        self.pending += text
        if "\n" not in self.pending:
            return list[str]()

        parts: list[str] = self.pending.split("\n")
        self.pending = parts.pop()
        return parts

    def Flush(self) -> list[str]:
        if not self.pending:
            return list[str]()
        line: str = self.pending
        self.pending = ""
        return [line]


class StreamTee:
    """
    Stands in for stdout or stderr. Text reaches the original stream unchanged, so the
    console keeps working, and a copy is queued for the output pane.
    """

    def __init__(self, stream, lineQueue: queue.Queue):
        self.stream = stream
        self.queue = lineQueue
        self.buffer = LineBuffer()

    def write(self, text: str) -> int:
        written: int = self.stream.write(text)
        for line in self.buffer.Add(text):
            self.queue.put(line)
        return written

    def flush(self) -> None:
        self.stream.flush()

    def isatty(self) -> bool:
        return self.stream.isatty()

    @property
    def encoding(self) -> str:
        return getattr(self.stream, "encoding", "utf-8")


class LogPane:
    """The output pane. Only its owner's main thread may call anything here."""

    def __init__(self, parent: Frame, lineQueue: queue.Queue):
        self.queue = lineQueue
        self.text = Text(
            parent, height=14, wrap="none", bd=0, highlightthickness=0, font=FONT_MONO,
            bg=FIELD, fg=FOREGROUND, insertbackground=FOREGROUND,
            selectbackground=TEAL, selectforeground="#FFFFFF", padx=6, pady=3)
        self.text.pack(side=LEFT, fill=BOTH, expand=True)

        scrollbar = Scrollbar(parent, orient=VERTICAL, command=self.text.yview,
                              bootstyle="secondary-round")
        scrollbar.pack(side=RIGHT, fill=Y)
        self.text.configure(yscrollcommand=scrollbar.set, state="disabled")

        self.text.tag_configure(WARNING, foreground=AMBER)
        self.text.tag_configure(ERROR, foreground=EMBER)
        self.text.tag_configure("dim", foreground=MUTED)

    def Drain(self) -> None:
        lines = list[str]()
        while len(lines) < DRAIN_LIMIT:
            try:
                lines.append(self.queue.get_nowait())
            except queue.Empty:
                break

        if not lines:
            return

        atEnd: bool = self.text.yview()[1] >= 0.999
        self.text.configure(state="normal")
        for line in lines:
            self.text.insert(END, line + "\n", ClassifyLine(line))
        self._Trim()
        self.text.configure(state="disabled")

        # Only follow the output when the reader has not scrolled back to look at something.
        if atEnd:
            self.text.see(END)

    def Clear(self) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", END)
        self.text.configure(state="disabled")

    def Copy(self) -> None:
        self.text.clipboard_clear()
        self.text.clipboard_append(self.text.get("1.0", END))

    def _Trim(self) -> None:
        overflow: int = int(self.text.index("end-1c").split(".")[0]) - MAX_LINES
        if overflow > 0:
            self.text.delete("1.0", f"{overflow + 1}.0")
