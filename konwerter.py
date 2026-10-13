from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable
import csv
import json
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


# konwertery z instrukcji
# ---------------------------------------------------------------------------

@converter(".docx", ".pdf")
def docx_to_pdf(source: Path, output_dir: Path) -> Path:
    command = [
        "libreoffice", "--headless", "--convert-to", "pdf",
        "--outdir", str(output_dir), str(source)
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Konwersja nie powiodła się")
    target = output_dir / f"{source.stem}.pdf"
    if not target.exists():
        raise RuntimeError("Narzędzie nie utworzyło oczekiwanego pliku")
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
    except (FileNotFoundError, NotADirectoryError, ValueError, RuntimeError) as e:
        print(f"Błąd: {e}")
        print(f"Dostępne formaty dla {source.name}: {available_targets(source)}")


if __name__ == "__main__":
    # Tu wpisujesz, co chcesz przekonwertować.
    # Wyniki trafiają do folderu "wyniki", żeby nie nadpisać plików źródłowych.
    wyniki = Path("wyniki")
    wyniki.mkdir(exist_ok=True)           # tworzy folder, jeśli go nie ma

    convert(Path("trudny2.csv"), ".json", wyniki)    # CSV  -> JSON
    convert(Path("trudny1.json"), ".csv", wyniki)    # JSON -> CS
    
    # ---------------------------------------------------------------------------