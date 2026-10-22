from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable
import csv
import json
import shutil
import subprocess

Converter = Callable[[Path, Path], Path]
REGISTRY: dict[tuple[str, str], Converter] = {}

#dekorator
def converter(source: str, target: str):
    """Dekorator rejestrujący pojedynczy kierunek konwersji."""
    def register(func: Converter) -> Converter:
        REGISTRY[(source.lower(), target.lower())] = func
        return func
    return register

#klasa konwersji
@dataclass(frozen=True)
class ConversionRequest:
    source: Path
    target_format: str
    output_dir: Path

#walidacja
    def validate(self) -> None:
        if not self.source.is_file():
            raise FileNotFoundError("Nie znaleziono pliku wejściowego")
        if not self.output_dir.is_dir():
            raise NotADirectoryError("Nie znaleziono katalogu docelowego")
        key = (self.source.suffix.lower(), self.target_format.lower())
        if key not in REGISTRY:
            raise ValueError(f"Nieobsługiwana konwersja: {key}")


def available_targets(source: Path) -> list[str]:
    return sorted(target for (src, target) in REGISTRY if src == source.suffix.lower())


# LAB 3: narzędzie zewnętrzne LibreOffice (DOCX, ODT, PDF)
# ---------------------------------------------------------------------------

class ToolNotFoundError(RuntimeError):
    """Błąd: brak wymaganego narzędzia zewnętrznego lub biblioteki."""


# Typowe miejsca instalacji LibreOffice na Windowsie (zwykle NIE ma go w PATH)
WINDOWS_LIBREOFFICE_PATHS = [
    Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
    Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
]


def find_libreoffice() -> str:
    """Zwraca ścieżkę do programu LibreOffice albo zgłasza ToolNotFoundError."""
    # 1. Szukamy w PATH (Linux, macOS, Windows z dodanym PATH)
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    # 2. Szukamy w domyślnych folderach instalacji na Windowsie
    for path in WINDOWS_LIBREOFFICE_PATHS:
        if path.is_file():
            return str(path)
    raise ToolNotFoundError(
        "Nie znaleziono LibreOffice. Zainstaluj go ze strony "
        "https://www.libreoffice.org/download/ i uruchom program ponownie."
    )


def run_libreoffice(source: Path, output_dir: Path, target_ext: str, lo_format: str) -> Path:
    """Wywołuje LibreOffice w trybie bez okna i zwraca ścieżkę do pliku wynikowego."""
    soffice = find_libreoffice()

    # Polecenie jako LISTA argumentów -> bez shell=True (bezpieczniej:
    # nazwa pliku nie jest interpretowana przez powłokę systemową)
    command = [
        soffice, "--headless", "--convert-to", lo_format,
        "--outdir", str(output_dir), str(source)
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    except FileNotFoundError as e:
        raise ToolNotFoundError(f"Nie udało się uruchomić LibreOffice: {e}") from e
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("LibreOffice nie zakończył pracy w ciągu 60 sekund") from e

    # Kod zakończenia: 0 = sukces, cokolwiek innego = błąd
    if result.returncode != 0:
        raise RuntimeError(
            f"LibreOffice zakończył się kodem {result.returncode}: "
            f"{result.stderr.strip() or 'brak opisu błędu'}"
        )

    target = output_dir / f"{source.stem}{target_ext}"
    if not target.exists():
        raise RuntimeError(
            "LibreOffice nie utworzył pliku wynikowego "
            "(zamknij otwarte okna LibreOffice i spróbuj ponownie)"
        )
    return target


@converter(".docx", ".pdf")
def docx_to_pdf(source: Path, output_dir: Path) -> Path:
    return run_libreoffice(source, output_dir, ".pdf", "pdf")


@converter(".odt", ".pdf")
def odt_to_pdf(source: Path, output_dir: Path) -> Path:
    return run_libreoffice(source, output_dir, ".pdf", "pdf")


@converter(".docx", ".odt")
def docx_to_odt(source: Path, output_dir: Path) -> Path:
    return run_libreoffice(source, output_dir, ".odt", "odt")


@converter(".odt", ".docx")
def odt_to_docx(source: Path, output_dir: Path) -> Path:
    return run_libreoffice(source, output_dir, ".docx", "docx:MS Word 2007 XML")

# ---------------------------------------------------------------------------


# LAB 3: PDF -> TXT (biblioteka Pythona pypdf, bez narzędzia zewnętrznego)
# ---------------------------------------------------------------------------

@converter(".pdf", ".txt")
def pdf_to_txt(source: Path, output_dir: Path) -> Path:
    try:
        from pypdf import PdfReader          # import tutaj: brak biblioteki
    except ImportError as e:                 # nie psuje pozostałych konwersji
        raise ToolNotFoundError(
            "Brak biblioteki pypdf. Zainstaluj ją poleceniem: pip install pypdf"
        ) from e

    reader = PdfReader(source)
    pages = [page.extract_text() or "" for page in reader.pages]

    target = output_dir / f"{source.stem}.txt"
    target.write_text("\n\n".join(pages), encoding="utf-8")
    return target

# ---------------------------------------------------------------------------


# CSV -> JSON
# ---------------------------------------------------------------------------

@converter(".csv", ".json")
def csv_to_json(source: Path, output_dir: Path) -> Path:
    """Każdy wiersz CSV staje się obiektem JSON; nagłówki to klucze."""
    with source.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)          # pierwszy wiersz = nagłówki
        if reader.fieldnames is None:
            raise ValueError("Plik CSV jest pusty")
        rows = [dict(row) for row in reader]

    target = output_dir / f"{source.stem}.json"
    with target.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    return target

# ---------------------------------------------------------------------------


# NOWE: JSON -> CSV
# ---------------------------------------------------------------------------

@converter(".json", ".csv")
def json_to_csv(source: Path, output_dir: Path) -> Path:
    """Oczekuje listy obiektów: [{"a": 1, "b": 2}, ...]."""
    with source.open(encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Niepoprawny JSON: {e}") from e

    if isinstance(data, dict):              # pojedynczy obiekt -> lista z 1 elementem
        data = [data]
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ValueError("JSON musi być listą obiektów (słowników)")

    # Zbieramy wszystkie klucze w kolejności wystąpienia -> nagłówki CSV
    fieldnames: list[str] = []
    for item in data:
        for key in item:
            if key not in fieldnames:
                fieldnames.append(key)

    target = output_dir / f"{source.stem}.csv"
    with target.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, restval="")
        writer.writeheader()
        for item in data:
            # Zagnieżdżone listy/obiekty zapisujemy jako tekst JSON
            row = {
                k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                for k, v in item.items()
            }
            writer.writerow(row)
    return target

# ---------------------------------------------------------------------------


# Uruchomienie konwersji
# ---------------------------------------------------------------------------

def execute(request: ConversionRequest) -> Path:
    request.validate()
    key = (request.source.suffix.lower(), request.target_format.lower())
    # TODO: polityka nadpisywania i rejestrowanie czasu operacji
    return REGISTRY[key](request.source, request.output_dir)


def convert(source: Path, target_format: str, output_dir: Path = Path(".")) -> None:
    """Wykonuje jedną konwersję i wypisuje wynik albo błąd."""
    request = ConversionRequest(source, target_format, output_dir)
    try:
        wynik = execute(request)
        print(f"Gotowe: {wynik}")
    except ToolNotFoundError as e:
        print(f"Brak narzędzia: {e}")
    except ValueError as e:
        print(f"Błąd: {e}")
        print(f"Dostępne formaty dla {source.name}: {available_targets(source)}")
    except (FileNotFoundError, NotADirectoryError, RuntimeError) as e:
        print(f"Błąd: {e}")


if __name__ == "__main__":
    # Tu wpisujesz, co chcesz przekonwertować.
    # Wyniki trafiają do folderu "wyniki", żeby nie nadpisać plików źródłowych.
    wyniki = Path("wyniki")
    wyniki.mkdir(exist_ok=True)           # tworzy folder, jeśli go nie ma

    # Lab 2
    # convert(Path("trudny2.csv"), ".json", wyniki)    # CSV  -> JSON
    # convert(Path("trudny1.json"), ".csv", wyniki)    # JSON -> CSV

    # Lab 3: najpierw sprawdzamy, czy narzędzie zewnętrzne jest dostępne
    try:
        print(f"LibreOffice: {find_libreoffice()}")
    except ToolNotFoundError as e:
        print(f"Uwaga: {e}")

    convert(Path("dokument.docx"), ".pdf", wyniki)    # DOCX -> PDF
    convert(Path("dokument.docx"), ".odt", wyniki)    # DOCX -> ODT
    convert(Path("notatka.odt"), ".pdf", wyniki)      # ODT  -> PDF
    convert(Path("notatka.odt"), ".docx", wyniki)     # ODT  -> DOCX
    convert(wyniki / "dokument.pdf", ".txt", wyniki)  # PDF  -> TXT
    
    # ---------------------------------------------------------------------------