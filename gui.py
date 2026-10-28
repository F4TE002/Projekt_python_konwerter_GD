"""LAB 4: graficzny interfejs (Tkinter/ttk) dla konwertera plików.

Uruchomienie: python gui.py
Cała logika konwersji jest w konwerter.py - GUI tylko z niej korzysta.
"""
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from konwerter import (
    ConversionRequest,
    ToolNotFoundError,
    REGISTRY,
    available_targets,
    execute,
    supported_sources,
)


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

        frame = ttk.Frame(root, padding=16)
        frame.grid()

        # --- Wiersz 1: plik wejściowy ---
        ttk.Label(frame, text="Plik wejściowy:").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.source_var, width=50, state="readonly").grid(
            row=0, column=1, padx=8)
        ttk.Button(frame, text="Wybierz plik…", command=self.choose_file).grid(row=0, column=2)

        # --- Wiersz 2: katalog docelowy ---
        ttk.Label(frame, text="Katalog docelowy:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.output_var, width=50, state="readonly").grid(
            row=1, column=1, padx=8)
        ttk.Button(frame, text="Wybierz katalog…", command=self.choose_dir).grid(row=1, column=2)

        # --- Wiersz 3: format docelowy (lista zależna od rozszerzenia pliku) ---
        ttk.Label(frame, text="Format docelowy:").grid(row=2, column=0, sticky="w", pady=4)
        # state="disabled" na start; później "readonly" = można tylko WYBRAĆ z listy,
        # nie da się wpisać własnego formatu -> GUI nie przyjmie niedozwolonej pary
        self.format_box = ttk.Combobox(frame, textvariable=self.format_var,
                                       state="disabled", width=15)
        self.format_box.grid(row=2, column=1, sticky="w", padx=8)

        # --- Wiersz 4: komunikat + przycisk ---
        ttk.Label(frame, textvariable=self.info_var, foreground="#555", wraplength=420).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(12, 0))
        self.convert_btn = ttk.Button(frame, text="Konwertuj", command=self.run_conversion,
                                      state="disabled")
        self.convert_btn.grid(row=3, column=2, pady=(12, 0))

        # Za każdym razem, gdy zmieni się któreś pole, sprawdzamy, czy można włączyć przycisk
        for var in (self.source_var, self.output_var, self.format_var):
            var.trace_add("write", lambda *args: self.update_button())

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

    def update_button(self) -> None:
        """Przycisk 'Konwertuj' jest aktywny tylko dla poprawnej pary formatów."""
        source = self.source_var.get()
        ok = bool(source and self.output_var.get() and self.format_var.get()
                  and (Path(source).suffix.lower(), self.format_var.get()) in REGISTRY)
        self.convert_btn.config(state="normal" if ok else "disabled")

    # -----------------------------------------------------------------------
    # Konwersja
    # -----------------------------------------------------------------------

    def run_conversion(self) -> None:
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

        # Konwersja może chwilę potrwać (LibreOffice) -> kursor "zajęty", przycisk wyłączony
        self.info_var.set("Trwa konwersja…")
        self.convert_btn.config(state="disabled")
        self.root.config(cursor="watch")
        self.root.update_idletasks()

        try:
            result = execute(request)
        except ToolNotFoundError as e:
            self.show_error("Brak narzędzia", str(e))
        except FileNotFoundError:
            self.show_error("Brak pliku",
                            "Nie znaleziono pliku wejściowego. Mógł zostać przeniesiony "
                            "lub usunięty – wybierz go ponownie.")
        except NotADirectoryError:
            self.show_error("Brak katalogu",
                            "Wybrany katalog docelowy nie istnieje. Wybierz inny katalog.")
        except FileExistsError:
            self.show_error("Plik już istnieje",
                            "Plik wynikowy już istnieje, a nadpisanie nie zostało potwierdzone.")
        except ValueError as e:
            self.show_error("Nieprawidłowe dane",
                            f"Plik nie mógł zostać przekonwertowany:\n{e}")
        except RuntimeError as e:
            self.show_error("Konwersja nie powiodła się", str(e))
        except Exception as e:             # cokolwiek nieprzewidzianego
            self.show_error("Nieoczekiwany błąd", f"{type(e).__name__}: {e}")
        else:
            self.info_var.set(f"Gotowe: {result.name}")
            messagebox.showinfo("Konwersja zakończona",
                                f"Utworzono plik:\n{result}")
        finally:                           # wykona się zawsze, także po błędzie
            self.root.config(cursor="")
            self.update_button()

    def show_error(self, title: str, message: str) -> None:
        self.info_var.set(f"Błąd: {title}")
        messagebox.showerror(title, message)


if __name__ == "__main__":
    root = tk.Tk()
    KonwerterApp(root)
    root.mainloop()
