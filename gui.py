"""Graficzny interfejs (Tkinter/ttk) dla konwertera plików.

Uruchomienie: python gui.py
Cała logika konwersji jest w konwerter.py - GUI tylko z niej korzysta.

Konwersja działa w osobnym wątku, więc okno nie "zamarza" podczas
dłuższych operacji (np. LibreOffice). Tkinter nie pozwala zmieniać okna
z innego wątku, dlatego wątek roboczy tylko wkłada wynik do kolejki,
a okno co 100 ms sprawdza kolejkę metodą root.after().
"""
from pathlib import Path
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from konwerter import (
    ConversionError,
    ConversionRequest,
    LOG_FILE,
    REGISTRY,
    available_targets,
    execute,
    setup_logging,
    supported_sources,
    supported_targets,
)

POLL_MS = 100     # co ile milisekund okno sprawdza, czy konwersja się skończyła


class KonwerterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Konwerter plików")
        root.resizable(False, False)

        # Zmienne powiązane z polami w oknie (StringVar = "pudełko" na tekst)
        self.source_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.format_var = tk.StringVar()
        self.info_var = tk.StringVar(value="Wybierz plik do konwersji.")

        # Kolejka do przekazania wyniku z wątku roboczego do okna
        self.results: queue.Queue = queue.Queue()
        self.worker: threading.Thread | None = None

        frame = ttk.Frame(root, padding=16)
        frame.grid()

        # --- plik wejściowy ---
        ttk.Label(frame, text="Plik wejściowy:").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.source_var, width=50, state="readonly").grid(
            row=0, column=1, padx=8)
        self.file_btn = ttk.Button(frame, text="Wybierz plik…", command=self.choose_file)
        self.file_btn.grid(row=0, column=2, sticky="ew")

        # --- katalog docelowy ---
        ttk.Label(frame, text="Katalog docelowy:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.output_var, width=50, state="readonly").grid(
            row=1, column=1, padx=8)
        self.dir_btn = ttk.Button(frame, text="Wybierz katalog…", command=self.choose_dir)
        self.dir_btn.grid(row=1, column=2, sticky="ew")

        # --- format docelowy (lista zależna od rozszerzenia) ---
        ttk.Label(frame, text="Format docelowy:").grid(row=2, column=0, sticky="w", pady=4)
        self.format_box = ttk.Combobox(frame, textvariable=self.format_var,
                                       state="disabled", width=15)
        self.format_box.grid(row=2, column=1, sticky="w", padx=8)
        ttk.Button(frame, text="Obsługiwane pary…", command=self.show_matrix).grid(
            row=2, column=2, sticky="ew")

        # --- komunikat + przycisk ---
        ttk.Label(frame, textvariable=self.info_var, foreground="#555", wraplength=420).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(12, 0))
        self.convert_btn = ttk.Button(frame, text="Konwertuj", command=self.run_conversion,
                                      state="disabled")
        self.convert_btn.grid(row=3, column=2, sticky="ew", pady=(12, 0))

        # --- pasek postępu (widoczny tylko podczas konwersji) ---
        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.progress.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        self.progress.grid_remove()

        # Za każdym razem, gdy zmieni się któreś pole, sprawdzamy, czy można włączyć przycisk
        for var in (self.source_var, self.output_var, self.format_var):
            var.trace_add("write", lambda *args: self.update_button())

        # Zamknięcie okna w trakcie konwersji wymaga potwierdzenia
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    # -----------------------------------------------------------------------
    # Wybór pliku i katalogu
    # -----------------------------------------------------------------------

    def choose_file(self) -> None:
        patterns = tuple(f"*{ext}" for ext in supported_sources())
        path = filedialog.askopenfilename(
            title="Wybierz plik do konwersji",
            filetypes=[("Obsługiwane pliki", patterns), ("Wszystkie pliki", "*.*")],
        )
        if not path:                       # użytkownik kliknął "Anuluj"
            return
        source = Path(path)
        self.source_var.set(str(source))

        # Domyślny katalog docelowy = folder, w którym leży plik
        if not self.output_var.get():
            self.output_var.set(str(source.parent))

        self.refresh_formats(source)

    def choose_dir(self) -> None:
        path = filedialog.askdirectory(title="Wybierz katalog docelowy")
        if path:
            self.output_var.set(str(Path(path)))

    def refresh_formats(self, source: Path) -> None:
        """Wypełnia listę formatów tylko tymi, które są w rejestrze dla tego rozszerzenia."""
        targets = available_targets(source)
        self.format_var.set("")
        if targets:
            self.format_box.config(values=targets, state="readonly")
            self.format_box.current(0)     # zaznacz pierwszy dostępny format
            self.info_var.set(f"Dostępne formaty dla {source.suffix}: {', '.join(targets)}")
        else:
            self.format_box.config(values=[], state="disabled")
            self.info_var.set(
                f"Pliki „{source.suffix or 'bez rozszerzenia'}” nie są obsługiwane. "
                f"Obsługiwane: {', '.join(supported_sources())}"
            )

    def show_matrix(self) -> ttk.Treeview:
        """Okno z macierzą wspieranych par; zawartość pochodzi wprost z rejestru."""
        window = tk.Toplevel(self.root)
        window.title("Obsługiwane pary formatów")
        window.transient(self.root)

        targets = supported_targets()
        table = ttk.Treeview(window, columns=targets, height=len(supported_sources()))
        table.heading("#0", text="Z \\ Na")
        table.column("#0", width=80, anchor="center")
        for target in targets:
            table.heading(target, text=target)
            table.column(target, width=70, anchor="center")
        for source in supported_sources():
            marks = ["✓" if (source, target) in REGISTRY else "–" for target in targets]
            table.insert("", "end", text=source, values=marks)
        table.grid(padx=16, pady=(16, 8))

        ttk.Button(window, text="Zamknij", command=window.destroy).grid(pady=(0, 16))
        return table

    def is_busy(self) -> bool:
        return self.worker is not None and self.worker.is_alive()

    def update_button(self) -> None:
        """Przycisk 'Konwertuj' jest aktywny tylko dla poprawnej pary i gdy nic nie trwa."""
        source = self.source_var.get()
        ok = bool(source and self.output_var.get() and self.format_var.get()
                  and (Path(source).suffix.lower(), self.format_var.get()) in REGISTRY
                  and not self.is_busy())
        self.convert_btn.config(state="normal" if ok else "disabled")

    # -----------------------------------------------------------------------
    # Konwersja
    # -----------------------------------------------------------------------

    def run_conversion(self) -> None:
        if self.is_busy():                 # nie uruchamiamy dwóch konwersji naraz
            return
        source = Path(self.source_var.get())
        output_dir = Path(self.output_var.get())
        target_format = self.format_var.get()

        # Druga linia obrony: nawet gdyby coś ominęło listę, para musi być w rejestrze
        if (source.suffix.lower(), target_format) not in REGISTRY:
            messagebox.showerror("Niedozwolona konwersja",
                                 f"Nie można przekonwertować {source.suffix} na {target_format}.")
            return

        request = ConversionRequest(source, target_format, output_dir)

        # Polityka nadpisywania: pytamy, zanim cokolwiek zostanie zastąpione
        target = request.target_path()
        if target.exists():
            answer = messagebox.askyesno(
                "Plik już istnieje",
                f"W katalogu docelowym jest już plik:\n{target.name}\n\n"
                "Czy chcesz go zastąpić?",
                icon="warning",
            )
            if not answer:
                self.info_var.set("Anulowano – istniejący plik nie został zmieniony.")
                return
            request = ConversionRequest(source, target_format, output_dir, overwrite=True)

        # Uruchamiamy konwersję w osobnym wątku -> okno dalej reaguje
        self.set_busy(True)
        self.info_var.set(f"Trwa konwersja {source.name}…")
        self.worker = threading.Thread(target=self.worker_job, args=(request,), daemon=True)
        self.worker.start()
        self.root.after(POLL_MS, self.check_result)

    def worker_job(self, request: ConversionRequest) -> None:
        """Działa w wątku roboczym. NIE dotyka okna - tylko wkłada wynik do kolejki."""
        start = time.perf_counter()
        try:
            result = execute(request)
            self.results.put(("ok", result, time.perf_counter() - start))
        except Exception as e:             # każdy błąd przekazujemy do okna
            self.results.put(("error", e, time.perf_counter() - start))

    def check_result(self) -> None:
        """Działa w wątku okna. Sprawdza, czy wątek roboczy skończył pracę."""
        try:
            status, value, elapsed = self.results.get_nowait()
        except queue.Empty:
            self.root.after(POLL_MS, self.check_result)    # jeszcze nie - sprawdź za chwilę
            return

        self.worker = None                 # wątek skończył pracę
        self.set_busy(False)
        if status == "ok":
            self.info_var.set(f"Gotowe: {value.name} ({elapsed:.1f} s)")
            messagebox.showinfo("Konwersja zakończona",
                                f"Utworzono plik:\n{value}\n\nCzas: {elapsed:.1f} s")
        elif isinstance(value, ConversionError):          # wspólny model błędów
            self.show_error(value.title, value.user_message())
        else:                                             # coś nieprzewidzianego
            self.show_error("Nieoczekiwany błąd",
                            f"{type(value).__name__}: {value}\n\n"
                            f"Spróbuj ponownie. Szczegóły są w pliku {LOG_FILE.name}.")

    def set_busy(self, busy: bool) -> None:
        """Blokuje/odblokowuje przyciski i pokazuje/ukrywa pasek postępu."""
        state = "disabled" if busy else "normal"
        self.file_btn.config(state=state)
        self.dir_btn.config(state=state)
        if busy:
            self.format_box.config(state="disabled")
            self.convert_btn.config(state="disabled")
            self.progress.grid()
            self.progress.start(10)
        else:
            self.progress.stop()
            self.progress.grid_remove()
            if self.format_box.cget("values"):
                self.format_box.config(state="readonly")
            self.update_button()

    def show_error(self, title: str, message: str) -> None:
        self.info_var.set(f"Błąd: {title}")
        messagebox.showerror(title, message)

    def on_close(self) -> None:
        if self.is_busy() and not messagebox.askyesno(
                "Trwa konwersja", "Konwersja jeszcze trwa. Czy na pewno zamknąć program?"):
            return
        self.root.destroy()


if __name__ == "__main__":
    setup_logging()
    root = tk.Tk()
    KonwerterApp(root)
    root.mainloop()
