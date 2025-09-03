#!/usr/bin/env python3
"""
backup_app.py — Fast project backup with GUI progress bar and CLI mode.

- GUI: runs a Tkinter app with determinate ttk.Progressbar.
- CLI: headless mode via argparse with the same streaming ZIP writer.
"""
import os
import sys
import time
import argparse
import threading
import traceback
from datetime import datetime
from pathlib import Path
import zipfile

# GUI imports are deferred so headless environments without Tk still work
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    TK_OK = True
except Exception:
    TK_OK = False

CHUNK_SIZE = 8 * 1024 * 1024  # 8 MiB chunks for high throughput
DEFAULT_EXCLUDES = {".git", "node_modules", "venv", "__pycache__", "dist", "build"}

def iter_files_with_size(root: Path, excludes: set[str]) -> tuple[list[Path], int]:
    files: list[Path] = []
    total = 0
    root = root.resolve()
    for r, dirs, fnames in os.walk(root):
        dirs[:] = [d for d in dirs if d not in excludes]
        base = Path(r)
        for name in fnames:
            p = base / name
            try:
                st = p.stat()
            except Exception:
                continue
            if p.is_file():
                files.append(p)
                total += st.st_size
    return files, total

def compression_from_args(kind: str, level: int | None):
    # store = fastest, deflate = optional compression
    if kind == "store":
        return zipfile.ZIP_STORED, None
    if kind == "deflate":
        return zipfile.ZIP_DEFLATED, (level if level is not None else 1)
    raise ValueError(f"Unknown compression kind: {kind}")

def backup_streaming(source: Path,
                     dest_dir: Path,
                     compression: int,
                     compresslevel: int | None,
                     excludes: set[str],
                     progress_cb=None) -> Path:
    if not source.is_dir():
        raise ValueError(f"Source is not a directory: {source}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    files, total = iter_files_with_size(source, excludes)
    if total == 0:
        raise ValueError("No files to back up")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_path = dest_dir / f"{source.name}-{timestamp}.zip"

    processed = 0
    start = time.time()

    with zipfile.ZipFile(
        archive_path,
        mode="w",
        compression=compression,
        compresslevel=compresslevel if compresslevel is not None else None,
        allowZip64=True,
        strict_timestamps=False,
    ) as zf:
        for fpath in files:
            rel = fpath.relative_to(source)
            arcname = Path(source.name) / rel
            with fpath.open("rb") as fr, zf.open(str(arcname).replace("\\", "/"), mode="w") as fw:
                while True:
                    chunk = fr.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    fw.write(chunk)
                    processed += len(chunk)
                    if progress_cb:
                        progress_cb(processed, total, time.time() - start)
    if progress_cb:
        progress_cb(total, total, time.time() - start)
    return archive_path

# ---------------- GUI ----------------
class BackupApp:
    def __init__(self, root):
        self.root = root
        root.title("Project Backup (Fast, with Progress)")
        root.resizable(False, False)

        self.src_var = tk.StringVar()
        self.dst_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Select project and backup folder")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.speed_var = tk.StringVar(value="")
        self.exclude_var = tk.StringVar(value=",".join(sorted(DEFAULT_EXCLUDES)))
        self._worker = None

        # Compression selector
        self.compression_var = tk.StringVar(value="Store (fastest)")
        comp = ttk.Frame(root, padding=10); comp.grid(row=0, column=0, sticky="ew")
        ttk.Label(comp, text="Compression:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            comp,
            textvariable=self.compression_var,
            values=["Store (fastest)", "Deflate (level 1)", "Deflate (level 9)"],
            state="readonly",
            width=22,
        ).grid(row=0, column=1, padx=(8, 0), sticky="w")

        # Source
        src = ttk.Frame(root, padding=10); src.grid(row=1, column=0, sticky="ew")
        ttk.Label(src, text="Project folder:").grid(row=0, column=0, sticky="w")
        ttk.Entry(src, textvariable=self.src_var, width=54).grid(row=1, column=0, sticky="w")
        ttk.Button(src, text="Browse…", command=self.choose_src).grid(row=1, column=1, padx=(8, 0))

        # Destination
        dst = ttk.Frame(root, padding=10); dst.grid(row=2, column=0, sticky="ew")
        ttk.Label(dst, text="Backup location:").grid(row=0, column=0, sticky="w")
        ttk.Entry(dst, textvariable=self.dst_var, width=54).grid(row=1, column=0, sticky="w")
        ttk.Button(dst, text="Browse…", command=self.choose_dst).grid(row=1, column=1, padx=(8, 0))

        # Excludes
        ex = ttk.Frame(root, padding=(10, 0, 10, 10)); ex.grid(row=3, column=0, sticky="ew")
        ttk.Label(ex, text="Exclude folders (comma-separated):").grid(row=0, column=0, sticky="w")
        ttk.Entry(ex, textvariable=self.exclude_var, width=54).grid(row=1, column=0, sticky="w")

        # Progress
        prog = ttk.Frame(root, padding=10); prog.grid(row=4, column=0, sticky="ew")
        self.pb = ttk.Progressbar(prog, orient="horizontal", mode="determinate", length=420,
                                  variable=self.progress_var, maximum=1.0)
        self.pb.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.percent_label = ttk.Label(prog, text="0%"); self.percent_label.grid(row=0, column=2, padx=(8, 0))
        ttk.Label(prog, textvariable=self.speed_var, foreground="#555").grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 0))

        # Actions
        act = ttk.Frame(root, padding=10); act.grid(row=5, column=0, sticky="ew")
        ttk.Button(act, text="Create Backup", command=self.start_backup).grid(row=0, column=1, sticky="e")
        ttk.Label(act, textvariable=self.status_var, foreground="#444").grid(row=0, column=0, sticky="w")

    def choose_src(self):
        path = filedialog.askdirectory(title="Select project folder")
        if path:
            self.src_var.set(path)

    def choose_dst(self):
        path = filedialog.askdirectory(title="Select backup folder")
        if path:
            self.dst_var.set(path)

    def start_backup(self):
        src = Path(self.src_var.get()).expanduser()
        dst = Path(self.dst_var.get()).expanduser()
        if not src.is_dir():
            messagebox.showwarning("Missing or invalid", "Select a valid project folder."); return
        if not dst.is_dir():
            messagebox.showwarning("Missing or invalid", "Select a valid backup destination."); return

        comp_choice = self.compression_var.get()
        if comp_choice.startswith("Store"):
            kind, level = "store", None
        elif "level 1" in comp_choice:
            kind, level = "deflate", 1
        else:
            kind, level = "deflate", 9
        compression, compresslevel = compression_from_args(kind, level)

        excludes = {s.strip() for s in self.exclude_var.get().split(",") if s.strip()}
        self.status_var.set("Scanning files…"); self.progress_var.set(0.0)
        self.percent_label.config(text="0%"); self.speed_var.set("")

        def worker():
            try:
                files, total = iter_files_with_size(src, excludes)
                if total == 0:
                    self._post_status("No files to back up."); return
                self._post_status("Backing up…"); start = time.time()
                self._post_progress(0, total, 0.0)
                def on_progress(done, tot, elapsed):
                    self._post_progress(done, tot, elapsed)
                out = backup_streaming(src, dst, compression, compresslevel, excludes, on_progress)
                self._post_progress(total, total, time.time() - start)
                self._post_status(f"Backup created: {out}")
                self.root.after(0, lambda: messagebox.showinfo("Done", f"Backup created:\n{out}"))
            except Exception as e:
                self._post_status("Backup failed.")
                self.root.after(0, lambda: messagebox.showerror("Backup failed", f"{e}\n\n{traceback.format_exc()}"))
        threading.Thread(target=worker, daemon=True).start()

    def _post_status(self, text):
        self.root.after(0, lambda: self.status_var.set(text))

    def _post_progress(self, processed, total, elapsed):
        def update():
            self.pb.config(maximum=float(total))
            self.progress_var.set(float(processed))
            pct = 0 if total == 0 else int((processed / total) * 100)
            self.percent_label.config(text=f"{pct}%")
            if elapsed > 0:
                mbps = (processed / (1024 * 1024)) / elapsed
                self.speed_var.set(f"{mbps:.1f} MiB/s")
        self.root.after(0, update)

# ---------------- CLI ----------------
def main():
    parser = argparse.ArgumentParser(
        description="Create a fast, timestamped ZIP backup of a project folder (GUI or CLI)."
    )
    parser.add_argument("--source", type=str, help="Path to the source project directory")
    parser.add_argument("--dest", type=str, help="Path to the destination directory")
    parser.add_argument("--compression", choices=["store", "deflate"], default="store",
                        help="Compression: store (no compression, fastest) or deflate")
    parser.add_argument("--level", type=int, choices=list(range(1, 10)),
                        help="Deflate level 1-9 (default 1 if --compression deflate)")
    parser.add_argument("--exclude", type=str, default=",".join(sorted(DEFAULT_EXCLUDES)),
                        help="Comma-separated folder names to exclude at any depth")
    parser.add_argument("--gui", action="store_true", help="Force GUI even if --source/--dest given")
    args = parser.parse_args()

    if args.gui or not (args.source and args.dest):
        if not TK_OK:
            print("Tkinter not available; run in CLI with --source and --dest", file=sys.stderr)
            sys.exit(2)
        root = tk.Tk()
        app = BackupApp(root)
        root.mainloop()
        return

    # Headless
    src = Path(args.source).expanduser()
    dst = Path(args.dest).expanduser()
    compression, compresslevel = compression_from_args(args.compression, args.level)
    excludes = {s.strip() for s in args.exclude.split(",") if s.strip()}

    # Simple textual progress
    last_print = 0
    def print_progress(done, tot, elapsed):
        nonlocal last_print
        now = time.time()
        if now - last_print >= 0.25 or done == tot:
            pct = 0 if tot == 0 else (done * 100 // tot)
            mbps = 0.0 if elapsed <= 0 else (done / (1024*1024)) / elapsed
            print(f"\rProgress: {pct:3.0f}% | {mbps:6.1f} MiB/s", end="", flush=True)
            last_print = now

    try:
        out = backup_streaming(src, dst, compression, compresslevel, excludes, print_progress)
        print()  # newline after progress
        print(f"Backup created: {out}")
    except Exception as e:
        print()  # ensure newline
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
