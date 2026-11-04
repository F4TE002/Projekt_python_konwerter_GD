from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable
import csv
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import uuid
import zipfile
import zlib

Converter = Callable[[Path, Path], Path]
REGISTRY: dict[tuple[str, str], Converter] = {}

# Dziennik programu. Moduł tylko zapisuje wpisy; do pliku trafiają one
# po wywołaniu setup_logging() (robi to gui.py i tryb skryptowy).
logger = logging.getLogger("konwerter")
logger.addHandler(logging.NullHandler())
LOG_FILE = Path(__file__).resolve().parent / "konwerter.log"


def setup_logging(path: Path = LOG_FILE) -> None:
    """Włącza zapis dziennika do pliku. Brak prawa zapisu nie blokuje programu."""
    try:
        logging.basicConfig(filename=path, encoding="utf-8", level=logging.INFO,
                            format="%(asctime)s %(levelname)s %(message)s")
    except OSError as e:
        print(f"Uwaga: nie można zapisać dziennika {path}: {e}")


# ---------------------------------------------------------------------------
# WSPÓLNY MODEL BŁĘDÓW
# Każdy błąd konwersji dziedziczy po ConversionError i niesie:
#   - tytuł (do nagłówka okna z komunikatem),
#   - treść (co się stało),
#   - wskazówkę (co użytkownik może zrobić).
# Dzięki temu GUI i tryb skryptowy obsługują wszystkie błędy jednym "except".
# ---------------------------------------------------------------------------

class ConversionError(Exception):
    """Klasa bazowa wszystkich błędów konwersji."""
    title = "Błąd konwersji"
    hint = ""

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if hint is not None:
            self.hint = hint

    def user_message(self) -> str:
        """Pełny komunikat dla użytkownika: treść + wskazówka."""
        return f"{self.message}\n\n{self.hint}" if self.hint else self.message


class InputNotFoundError(ConversionError):
    title = "Brak pliku"
    hint = "Plik mógł zostać przeniesiony lub usunięty – wybierz go ponownie."


class OutputDirError(ConversionError):
    title = "Problem z katalogiem docelowym"
    hint = "Wybierz istniejący katalog docelowy."


class UnsupportedConversionError(ConversionError):
    title = "Niedozwolona konwersja"
    hint = "Wybierz jeden z formatów dostępnych na liście."


class OutputExistsError(ConversionError):
    title = "Plik już istnieje"
    hint = "Potwierdź nadpisanie albo wybierz inny katalog docelowy."


class InvalidInputError(ConversionError):
    title = "Nieprawidłowe dane"
    hint = "Sprawdź zawartość i kodowanie pliku wejściowego."


class ToolNotFoundError(ConversionError):
    title = "Brak narzędzia"


class ConversionFailedError(ConversionError):
    title = "Konwersja nie powiodła się"


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
    overwrite: bool = False      # czy wolno nadpisać istniejący plik wynikowy

    def target_path(self) -> Path:
        #Ścieżka pliku, który powstanie, np. wyniki/dane.json.
        return self.output_dir / f"{self.source.stem}{self.target_format.lower()}"

#walidacja
    def validate(self) -> None:
        if not self.source.is_file():
            raise InputNotFoundError(f"Nie znaleziono pliku wejściowego: {self.source.name}")
        if not self.output_dir.is_dir():
            raise OutputDirError(f"Nie znaleziono katalogu docelowego: {self.output_dir}")
        key = (self.source.suffix.lower(), self.target_format.lower())
        if key not in REGISTRY:
            raise UnsupportedConversionError(
                f"Nieobsługiwana konwersja: {key[0] or '(brak rozszerzenia)'} -> {key[1]}")
        if self.target_path().exists() and not self.overwrite:
            raise OutputExistsError(f"Plik wynikowy już istnieje: {self.target_path().name}")
        check_writable(self.output_dir)


def check_writable(directory: Path) -> None:
    """Próbne utworzenie podkatalogu - tego samego potrzebuje później execute().

    Nie używamy tu modułu tempfile: na Windowsie przy braku uprawnień ponawia on
    próby prawie w nieskończoność, a program by zawisł. os.access też się nie
    nadaje, bo na Windowsie nie sprawdza uprawnień do katalogów.
    """
    probe = directory / f".konwerter_{uuid.uuid4().hex}"
    try:
        probe.mkdir()
        probe.rmdir()
    except OSError as e:
        raise OutputDirError(f"Brak możliwości zapisu w katalogu: {directory}",
                             "Wybierz inny katalog docelowy, np. w folderze Dokumenty.") from e


def available_targets(source: Path) -> list[str]:
    return sorted(target for (src, target) in REGISTRY if src == source.suffix.lower())


def supported_sources() -> list[str]:
    """Wszystkie rozszerzenia, z których umiemy konwertować, np. ['.csv', '.docx', ...]."""
    return sorted({src for (src, target) in REGISTRY})


def supported_targets() -> list[str]:
    """Wszystkie rozszerzenia, na które umiemy konwertować (kolumny macierzy w GUI)."""
    return sorted({target for (src, target) in REGISTRY})


# ---------------------------------------------------------------------------
# LibreOffice: wykrywanie na Windows, macOS i Linux
# ---------------------------------------------------------------------------

# Zmienna środowiskowa, którą można wskazać LibreOffice w nietypowym miejscu
LIBREOFFICE_ENV = "LIBREOFFICE_PATH"


def libreoffice_candidates() -> list[Path]:
    """Typowe miejsca instalacji LibreOffice dla bieżącego systemu."""
    if sys.platform.startswith("win"):
        folders = [os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                   os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")]
        return [Path(f) / "LibreOffice" / "program" / "soffice.exe" for f in folders]
    if sys.platform == "darwin":                       # macOS
        return [Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
                Path.home() / "Applications/LibreOffice.app/Contents/MacOS/soffice"]
    # Linux i inne systemy uniksowe
    candidates = [Path("/usr/bin/soffice"),
                  Path("/usr/lib/libreoffice/program/soffice"),
                  Path("/usr/local/bin/soffice"),
                  Path("/snap/bin/libreoffice")]
    candidates += sorted(Path("/opt").glob("libreoffice*/program/soffice"))   # wersje z libreoffice.org
    return candidates


def install_hint() -> str:
    """Wskazówka instalacji LibreOffice dopasowana do systemu."""
    if sys.platform.startswith("win"):
        how = "Pobierz instalator ze strony https://www.libreoffice.org/download/"
    elif sys.platform == "darwin":
        how = "Pobierz ze strony https://www.libreoffice.org/download/ lub: brew install --cask libreoffice"
    else:
        how = "Zainstaluj pakietem systemowym, np.: sudo apt install libreoffice"
    return (f"{how}\nJeśli LibreOffice jest w nietypowym miejscu, ustaw zmienną "
            f"środowiskową {LIBREOFFICE_ENV} na pełną ścieżkę do programu soffice.")


def find_libreoffice() -> str:
    """Zwraca ścieżkę do programu LibreOffice albo zgłasza ToolNotFoundError."""
    # 1. Ścieżka wskazana ręcznie przez użytkownika
    custom = os.environ.get(LIBREOFFICE_ENV)
    if custom and Path(custom).is_file():
        return custom
    # 2. Szukamy w PATH (tak jak terminal szuka poleceń)
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    # 3. Typowe foldery instalacji dla danego systemu
    for path in libreoffice_candidates():
        if path.is_file():
            return str(path)
    raise ToolNotFoundError("Nie znaleziono LibreOffice, który jest potrzebny "
                            "do konwersji dokumentów DOCX, ODT, PDF i TXT.", install_hint())


LIBREOFFICE_TIMEOUT = 60      # sekundy


def run_libreoffice(source: Path, output_dir: Path, target_ext: str, lo_format: str,
                    infilter: str | None = None) -> Path:
    """Wywołuje LibreOffice w trybie bez okna i zwraca ścieżkę do pliku wynikowego.

    infilter - opcjonalny filtr wejściowy, np. wymuszenie kodowania pliku TXT.
    """
    soffice = find_libreoffice()

    # Polecenie jako LISTA argumentów -> bez shell=True (bezpieczniej:
    # nazwa pliku nie jest interpretowana przez powłokę systemową)
    command = [soffice, "--headless"]
    if infilter:
        command.append(f"--infilter={infilter}")
    command += ["--convert-to", lo_format, "--outdir", str(output_dir), str(source)]
    try:
        # errors="replace": komunikat w nietypowym kodowaniu nie może wywołać kolejnego błędu
        result = subprocess.run(command, capture_output=True, text=True, errors="replace",
                                timeout=LIBREOFFICE_TIMEOUT)
    except FileNotFoundError as e:
        raise ToolNotFoundError(f"Nie udało się uruchomić LibreOffice: {e}", install_hint()) from e
    except subprocess.TimeoutExpired as e:
        raise ConversionFailedError(
            f"LibreOffice nie zakończył pracy w ciągu {LIBREOFFICE_TIMEOUT} sekund.",
            "Zamknij otwarte okna LibreOffice i spróbuj ponownie.") from e

    # Kod zakończenia: 0 = sukces, cokolwiek innego = błąd
    if result.returncode != 0:
        raise ConversionFailedError(
            f"LibreOffice zakończył się kodem {result.returncode}: "
            f"{result.stderr.strip() or 'brak opisu błędu'}",
            "Sprawdź, czy plik otwiera się poprawnie w edytorze.")

    target = output_dir / f"{source.stem}{target_ext}"
    if not target.exists():
        raise ConversionFailedError(
            "LibreOffice nie utworzył pliku wynikowego.",
            "Zamknij otwarte okna LibreOffice i spróbuj ponownie.")
    return target


# TXT -> PDF / DOCX / ODT (LibreOffice)
# ---------------------------------------------------------------------------

# Wymuszamy odczyt pliku TXT jako UTF-8; bez tego LibreOffice na Windowsie
# mógłby przyjąć kodowanie systemowe (Windows-1250) i zniekształcić polskie znaki.
TXT_INFILTER = "Text (encoded):UTF8,LF,,,"


def txt_via_libreoffice(source: Path, output_dir: Path, target_ext: str, lo_format: str) -> Path:
    """Sprawdza kodowanie pliku TXT i konwertuje go przez LibreOffice."""
    try:
        source.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as e:
        raise InvalidInputError(
            "Plik TXT nie jest zapisany w kodowaniu UTF-8.",
            "Zapisz plik w UTF-8 (Notatnik: Plik -> Zapisz jako -> Kodowanie: UTF-8).") from e
    return run_libreoffice(source, output_dir, target_ext, lo_format, infilter=TXT_INFILTER)


@converter(".txt", ".pdf")
def txt_to_pdf(source: Path, output_dir: Path) -> Path:
    return txt_via_libreoffice(source, output_dir, ".pdf", "pdf")


@converter(".txt", ".docx")
def txt_to_docx(source: Path, output_dir: Path) -> Path:
    return txt_via_libreoffice(source, output_dir, ".docx", "docx:MS Word 2007 XML")


@converter(".txt", ".odt")
def txt_to_odt(source: Path, output_dir: Path) -> Path:
    return txt_via_libreoffice(source, output_dir, ".odt", "odt")


# DOCX / ODT (LibreOffice)
# ---------------------------------------------------------------------------

# DOCX i ODT to archiwa ZIP; tu jest element, który musi się w nich znaleźć.
OFFICE_MARKERS = {".docx": "word/", ".odt": "content.xml"}


def check_office_file(source: Path) -> None:
    """Sprawdza, czy plik DOCX/ODT jest poprawnym archiwum.

    Bez tej kontroli LibreOffice otwiera uszkodzony plik jak zwykły tekst
    i "z sukcesem" tworzy dokument pełen przypadkowych znaków.
    """
    kind = source.suffix.lower()
    try:
        with zipfile.ZipFile(source) as archive:
            has_content = any(name.startswith(OFFICE_MARKERS[kind]) for name in archive.namelist())
            if not has_content or archive.testzip() is not None:
                raise zipfile.BadZipFile
    except (zipfile.BadZipFile, zlib.error) as e:
        raise InvalidInputError(
            f"Plik {source.name} jest uszkodzony lub nie jest dokumentem {kind[1:].upper()}.",
            "Sprawdź, czy otwiera się w edytorze i czy nie jest zabezpieczony hasłem.") from e


def office_via_libreoffice(source: Path, output_dir: Path, target_ext: str, lo_format: str) -> Path:
    """Sprawdza plik DOCX/ODT i konwertuje go przez LibreOffice."""
    check_office_file(source)
    return run_libreoffice(source, output_dir, target_ext, lo_format)


@converter(".docx", ".pdf")
def docx_to_pdf(source: Path, output_dir: Path) -> Path:
    return office_via_libreoffice(source, output_dir, ".pdf", "pdf")


@converter(".odt", ".pdf")
def odt_to_pdf(source: Path, output_dir: Path) -> Path:
    return office_via_libreoffice(source, output_dir, ".pdf", "pdf")


@converter(".docx", ".odt")
def docx_to_odt(source: Path, output_dir: Path) -> Path:
    return office_via_libreoffice(source, output_dir, ".odt", "odt")


@converter(".odt", ".docx")
def odt_to_docx(source: Path, output_dir: Path) -> Path:
    return office_via_libreoffice(source, output_dir, ".docx", "docx:MS Word 2007 XML")

# ---------------------------------------------------------------------------


# PDF -> TXT (biblioteka Pythona pypdf, bez narzędzia zewnętrznego)
# ---------------------------------------------------------------------------

def clean_pdf_text(text: str) -> str:
    """Skleja litery z osobnymi znakami diakrytycznymi i usuwa znaki sterujące."""
    text = unicodedata.normalize("NFC", text)
    return "".join(ch for ch in text if ch in "\n\t" or unicodedata.category(ch) != "Cc")


@converter(".pdf", ".txt")
def pdf_to_txt(source: Path, output_dir: Path) -> Path:
    try:
        from pypdf import PdfReader          # import tutaj: brak biblioteki
    except ImportError as e:                 # nie psuje pozostałych konwersji
        raise ToolNotFoundError(
            "Brak biblioteki pypdf, potrzebnej do odczytu plików PDF.",
            "Zainstaluj ją poleceniem: python -m pip install pypdf") from e

    try:
        reader = PdfReader(source)
        encrypted = reader.is_encrypted
        pages = [] if encrypted else [page.extract_text() or "" for page in reader.pages]
    except Exception as e:                   # uszkodzony plik może dać różne wyjątki biblioteki
        raise InvalidInputError(f"Plik PDF jest uszkodzony lub nieprawidłowy: {e}") from e
    if encrypted:
        raise InvalidInputError("Plik PDF jest zabezpieczony hasłem.",
                                "Usuń zabezpieczenie pliku i spróbuj ponownie.")

    raw = "\n\n".join(pages)
    text = clean_pdf_text(raw)
    if not text.strip():
        raise InvalidInputError("Plik PDF nie zawiera tekstu do odczytania (np. jest skanem).",
                                "Najpierw rozpoznaj tekst programem OCR.")
    if len(text) < len(unicodedata.normalize("NFC", raw)):
        logger.warning("%s: warstwa tekstowa PDF zawiera znaki sterujące - "
                       "tekst może być zniekształcony", source.name)

    target = output_dir / f"{source.stem}.txt"
    target.write_text(text, encoding="utf-8")
    return target

# ---------------------------------------------------------------------------


# CSV -> JSON
# ---------------------------------------------------------------------------

UTF8_HINT = "Zapisz plik w kodowaniu UTF-8 (w Excelu: Zapisz jako -> CSV UTF-8)."


@converter(".csv", ".json")
def csv_to_json(source: Path, output_dir: Path) -> Path:
    """Każdy wiersz CSV staje się obiektem JSON; nagłówki to klucze."""
    try:
        with source.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)          # pierwszy wiersz = nagłówki
            if not reader.fieldnames:
                raise InvalidInputError("Plik CSV jest pusty.")
            # Dwie kolumny o tej samej nazwie: jedna po cichu nadpisałaby drugą
            if len(set(reader.fieldnames)) < len(reader.fieldnames):
                raise InvalidInputError("Plik CSV ma powtórzone nazwy kolumn.",
                                        "Nadaj każdej kolumnie w pierwszym wierszu inną nazwę.")
            rows = []
            for row in reader:
                if None in row:                 # DictReader: pola bez nagłówka -> klucz None
                    raise InvalidInputError(
                        f"Wiersz {reader.line_num} ma więcej pól niż nagłówek.",
                        "Sprawdź separatory; tekst z przecinkiem ujmij w cudzysłów.")
                rows.append(row)
    except UnicodeDecodeError as e:
        raise InvalidInputError("Plik CSV nie jest zapisany w kodowaniu UTF-8.", UTF8_HINT) from e
    except csv.Error as e:
        raise InvalidInputError(f"Niepoprawny plik CSV: {e}") from e

    target = output_dir / f"{source.stem}.json"
    with target.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    return target

# ---------------------------------------------------------------------------


# JSON -> CSV
# ---------------------------------------------------------------------------

def json_cell(value):
    """Wartość JSON -> komórka CSV: listy, obiekty i true/false zostają w zapisie JSON."""
    if isinstance(value, (dict, list, bool)):
        return json.dumps(value, ensure_ascii=False)
    return value


@converter(".json", ".csv")
def json_to_csv(source: Path, output_dir: Path) -> Path:
    """Oczekuje listy obiektów: [{"a": 1, "b": 2}, ...]."""
    try:
        with source.open(encoding="utf-8-sig") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise InvalidInputError(f"Niepoprawny JSON: {e}") from e
    except UnicodeDecodeError as e:
        raise InvalidInputError("Plik JSON nie jest zapisany w kodowaniu UTF-8.") from e

    if isinstance(data, dict):              # pojedynczy obiekt -> lista z 1 elementem
        data = [data]
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise InvalidInputError("JSON musi być listą obiektów (słowników).",
                                'Oczekiwany układ: [{"klucz": "wartość"}, ...]')

    # Zbieramy wszystkie klucze w kolejności wystąpienia -> nagłówki CSV
    fieldnames: list[str] = []
    for item in data:
        for key in item:
            if key not in fieldnames:
                fieldnames.append(key)
    if not fieldnames:
        raise InvalidInputError("JSON nie zawiera żadnych danych, więc nie ma z czego "
                                "utworzyć kolumn CSV.",
                                'Oczekiwany układ: [{"klucz": "wartość"}, ...]')

    target = output_dir / f"{source.stem}.csv"
    with target.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, restval="")
        writer.writeheader()
        for item in data:
            writer.writerow({k: json_cell(v) for k, v in item.items()})
    return target

# ---------------------------------------------------------------------------


# Uruchomienie konwersji
# ---------------------------------------------------------------------------

def execute(request: ConversionRequest) -> Path:
    key = (request.source.suffix.lower(), request.target_format.lower())
    label = f"{request.source.name} -> {request.target_format}"

    # Rejestrowanie czasu operacji
    start = time.perf_counter()
    try:
        # Polityka nadpisywania: validate() już odrzuciło istniejący plik bez zgody.
        request.validate()
        target = request.target_path()
        # Konwerter pisze do katalogu tymczasowego, a gotowy plik dopiero na końcu
        # trafia na miejsce. Nieudana konwersja nie niszczy więc starego pliku
        # i nie zostawia w katalogu docelowym niedokończonego wyniku.
        with tempfile.TemporaryDirectory(dir=request.output_dir, prefix=".konwerter_",
                                         ignore_cleanup_errors=True) as tmp:
            os.replace(REGISTRY[key](request.source, Path(tmp)), target)
    except ConversionError as e:                # błąd już w naszym modelu
        logger.error("%s: %s: %s", label, e.title, e.message)
        raise
    except OSError as e:                        # np. brak uprawnień, plik otwarty w innym programie
        logger.error("%s: błąd odczytu lub zapisu: %s", label, e)
        raise ConversionFailedError(
            f"Błąd odczytu lub zapisu pliku: {e}",
            "Sprawdź uprawnienia do katalogu i zamknij plik wynikowy, jeśli jest "
            "otwarty w innym programie.") from e
    except Exception:
        logger.exception("%s: nieoczekiwany błąd", label)
        raise
    logger.info("%s: gotowe w %.2f s (%s)", label, time.perf_counter() - start, target)
    return target


def convert(source: Path, target_format: str, output_dir: Path = Path("."),
            overwrite: bool = False) -> None:
    """Wykonuje jedną konwersję i wypisuje wynik albo błąd."""
    request = ConversionRequest(source, target_format, output_dir, overwrite)
    try:
        wynik = execute(request)
        print(f"Gotowe: {wynik}")
    except ConversionError as e:             # jeden except dla wszystkich błędów
        print(f"{e.title}: {e.user_message()}")
        if isinstance(e, UnsupportedConversionError):
            print(f"Dostępne formaty dla {source.name}: {available_targets(source)}")


if __name__ == "__main__":
    setup_logging()
    # Tu wpisujesz, co chcesz przekonwertować.
    # Ścieżki liczone od położenia tego pliku -> działa niezależnie od tego,
    # z którego folderu uruchomisz program.
    PROJEKT = Path(__file__).resolve().parent          # folder projektu
    DANE = PROJEKT / "testy" / "dane testowe"          # pliki wejściowe

    # Wyniki trafiają do folderu "testy/wyniki", żeby nie nadpisać plików źródłowych.
    wyniki = PROJEKT / "testy" / "wyniki"
    wyniki.mkdir(exist_ok=True)           # tworzy folder, jeśli go nie ma

    # bez overwrite=True istniejące pliki w "wyniki" nie zostaną nadpisane.
    # Interfejs graficzny jest w pliku gui.py.
    nadpisz = True

    # CSV <-> JSON
    convert(DANE / "studenci.csv", ".json", wyniki, nadpisz)    # CSV  -> JSON
    convert(DANE / "produkty.json", ".csv", wyniki, nadpisz)    # JSON -> CSV
    convert(DANE / "trudny1.json", ".csv", wyniki, nadpisz)     # JSON -> CSV
    convert(DANE / "trudny2.csv", ".json", wyniki, nadpisz)     # CSV  -> JSON

    # najpierw sprawdzamy, czy narzędzie zewnętrzne jest dostępne
    try:
        print(f"LibreOffice: {find_libreoffice()}")
    except ToolNotFoundError as e:
        print(f"Uwaga: {e.message}")

    # DOCX / ODT / PDF
    convert(DANE / "dokument.docx", ".pdf", wyniki, nadpisz)    # DOCX -> PDF
    convert(DANE / "dokument.docx", ".odt", wyniki, nadpisz)    # DOCX -> ODT
    convert(DANE / "notatka.odt", ".pdf", wyniki, nadpisz)      # ODT  -> PDF
    convert(DANE / "notatka.odt", ".docx", wyniki, nadpisz)     # ODT  -> DOCX
    convert(wyniki / "dokument.pdf", ".txt", wyniki, nadpisz)   # PDF  -> TXT
    convert(DANE / "tekst.txt", ".pdf", wyniki, nadpisz)        # TXT  -> PDF
    convert(DANE / "tekst.txt", ".docx", wyniki, nadpisz)       # TXT  -> DOCX
    convert(DANE / "tekst.txt", ".odt", wyniki, nadpisz)        # TXT  -> ODT

    # ---------------------------------------------------------------------------
