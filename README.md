# Konwerter plików

Projekt zaliczeniowy z przedmiotu Programowanie V.

Autor: Grzegorz Dyląg

## Cel projektu

Program okienkowy do konwersji plików między popularnymi formatami danych
i dokumentów. Ma rozszerzalną architekturę opartą na rejestrze konwerterów:
każdy kierunek konwersji to osobna funkcja zarejestrowana dekoratorem,
a interfejs graficzny automatycznie pokazuje wszystkie zarejestrowane konwersje.

Program nie obiecuje „dowolnej konwersji” – działa tylko dla par wymienionych
w tabeli poniżej. Tę samą macierz pokazuje przycisk „Obsługiwane pary…” w oknie.

## Obsługiwane funkcje

- 10 kierunków konwersji między formatami CSV, JSON, DOCX, ODT, PDF i TXT.
- Okno programu (Tkinter/ttk):
  - wybór pliku wejściowego i katalogu docelowego,
  - lista formatów docelowych zależna od rozszerzenia pliku,
  - blokada niedozwolonych par formatów i macierz wspieranych par,
  - pytanie przed nadpisaniem istniejącego pliku,
  - konwersja w osobnym wątku – okno nie zamarza, w trakcie widoczny jest
    pasek postępu, a przyciski są zablokowane,
  - zrozumiałe komunikaty błędów ze wskazówką, co zrobić.
- Walidacja: istnienie pliku, rozszerzenie, para formatów, istnienie katalogu
  i możliwość zapisu, konflikt nazw, poprawność treści pliku.
- Bezpieczne nadpisywanie: wynik powstaje w katalogu tymczasowym i dopiero
  gotowy zastępuje stary plik, więc nieudana konwersja niczego nie niszczy.
- Wspólny model błędów – wszystkie błędy dziedziczą po klasie `ConversionError`
  i niosą tytuł, opis oraz wskazówkę dla użytkownika.
- Wywoływanie LibreOffice bez `shell=True`, ze sprawdzaniem kodu zakończenia
  i limitem czasu (60 s).
- Wykrywanie LibreOffice na Windows, macOS i Linux; brak LibreOffice lub
  biblioteki pypdf jest wykrywany i opisany.
- Dziennik `konwerter.log`: czas każdej konwersji oraz wszystkie błędy.
- Testy automatyczne (unittest) – 73 testy.

## Wymagania

- Python 3.10 lub nowszy – <https://www.python.org/downloads/>
  (przy instalacji na Windowsie zaznacz „Add Python to PATH”)
- Tkinter – dołączony do Pythona na Windowsie i macOS
  (na Linuksie np.: `sudo apt install python3-tk`)
- pypdf 5.0 lub nowszy – potrzebny do konwersji PDF → TXT
  (zapisany w `requirements.txt`)
- LibreOffice 7.x lub nowszy – potrzebny do konwersji DOCX / ODT / TXT → dokument
  – <https://www.libreoffice.org/download/>

Brak LibreOffice lub pypdf nie blokuje programu – pozostałe konwersje działają,
a przy próbie użycia brakującego narzędzia pojawia się komunikat z instrukcją
instalacji dla danego systemu.

## Instalacja

1. Pobierz lub sklonuj repozytorium.
2. W terminalu, w folderze projektu, zainstaluj zależności:

   ```
   python -m pip install -r requirements.txt
   ```

3. Zainstaluj LibreOffice, jeśli chcesz konwertować dokumenty (nie instaluje się
   przez pip):
   - Windows: instalator ze strony <https://www.libreoffice.org/download/>
   - macOS: instalator jw. albo `brew install --cask libreoffice`
   - Linux: pakiet systemowy, np. `sudo apt install libreoffice`
     (Fedora: `sudo dnf install libreoffice`)

Program szuka LibreOffice automatycznie (funkcja `find_libreoffice`), w tej kolejności:

1. Zmienna środowiskowa `LIBREOFFICE_PATH` – pełna ścieżka do programu soffice
   (dla nietypowych instalacji).
2. PATH – polecenia `soffice` i `libreoffice`.
3. Typowe foldery instalacji:
   - Windows: `C:\Program Files\LibreOffice\program\soffice.exe`,
     `C:\Program Files (x86)\LibreOffice\program\soffice.exe`
   - macOS: `/Applications/LibreOffice.app/Contents/MacOS/soffice`,
     `~/Applications/LibreOffice.app/Contents/MacOS/soffice`
   - Linux: `/usr/bin/soffice`, `/usr/lib/libreoffice/program/soffice`,
     `/usr/local/bin/soffice`, `/snap/bin/libreoffice`,
     `/opt/libreoffice*/program/soffice`

Przykład ustawienia ścieżki na Windowsie (cmd, przed uruchomieniem programu):

```
set LIBREOFFICE_PATH=D:\Programy\LibreOffice\program\soffice.exe
```

## Uruchomienie

W terminalu, w folderze projektu:

```
python gui.py
```

Pliki `gui.py` i `konwerter.py` muszą znajdować się w tym samym folderze.

1. Kliknij „Wybierz plik…” i wskaż plik (przykłady: `testy/dane testowe`).
2. Katalog docelowy ustawia się automatycznie na folder pliku. Można go zmienić
   przyciskiem „Wybierz katalog…”.
3. Z listy „Format docelowy” wybierz format. Lista zawiera tylko formaty
   dozwolone dla danego rozszerzenia.
4. Kliknij „Konwertuj”. W trakcie widoczny jest pasek postępu.
5. Po zakończeniu pojawi się okno ze ścieżką pliku i czasem konwersji, a w razie
   problemu – okno z opisem błędu i wskazówką.

Jeśli plik wynikowy już istnieje, program zapyta, czy go zastąpić. Odpowiedź
„Nie” pozostawia istniejący plik bez zmian.

### Przykłady

| Plik wejściowy (`testy/dane testowe/`) | Format | Wynik |
|---|---|---|
| `studenci.csv` | `.json` | lista 5 obiektów (wzorzec: `testy/oczekiwane/studenci.json`) |
| `produkty.json` | `.csv` | tabela z 4 wierszami (wzorzec: `testy/oczekiwane/produkty.csv`) |
| `tekst.txt` | `.docx` | dokument z polskimi znakami; każda linia to akapit |
| `dokument.docx` | `.pdf` | PDF z nagłówkiem, akapitem i tabelą |

### Bez okna programu

```
python konwerter.py
```

uruchamia przykładowe konwersje z końca pliku `konwerter.py`; wyniki trafiają
do `testy/wyniki`. Z własnego kodu można wywołać konwersję tak:

```python
from pathlib import Path
from konwerter import ConversionRequest, execute

execute(ConversionRequest(Path("dane.csv"), ".json", Path("wyniki")))
```

## Testy automatyczne

```
python -m unittest discover -s testy -v
```

Opis i wyniki: `docs/RAPORT_TESTOW.txt`. Testy wymagające LibreOffice, pypdf
lub ekranu są pomijane, jeśli danego elementu brak.

## Format danych CSV i JSON

**Kodowanie.** Pliki wejściowe muszą być w UTF-8 (z BOM lub bez). Plik w innym
kodowaniu, np. Windows-1250, jest odrzucany z komunikatem. Wyniki są zapisywane
w UTF-8 bez BOM.

**CSV.** Separatorem jest przecinek, pole z przecinkiem, cudzysłowem lub końcem
linii ujmuje się w cudzysłów. Pierwszy wiersz to zawsze nagłówki; ich nazwy
i kolejność przechodzą bez zmian na klucze JSON.

**JSON.** Akceptowana struktura to lista obiektów lub pojedynczy obiekt
(traktowany jak lista z jednym elementem):

```json
[
  {"id": 1, "nazwa": "Żółty", "dostepny": true},
  {"id": 2, "nazwa": "Zielony", "uwagi": null}
]
```

Kolumny CSV to wszystkie klucze w kolejności pierwszego wystąpienia.

| Sytuacja | CSV → JSON | JSON → CSV |
|---|---|---|
| Liczba | tekst: `"4.5"` | `4.5` |
| Puste pole / `null` | `""` | pusta komórka |
| Brak pola na końcu wiersza / brak klucza | `null` | pusta komórka |
| `true` / `false` | tekst | `true` / `false` |
| Zagnieżdżona lista lub obiekt | – | tekst JSON w komórce |
| Tylko nagłówek / `[]` | `[]` (nazwy kolumn nie są zachowane) | błąd: brak danych |
| Powtórzone nazwy kolumn | błąd | – |
| Więcej pól niż nagłówków | błąd z numerem wiersza | – |

## Tabela wspieranych par formatów

| Grupa | Konwersja | Realizacja | Znane ograniczenia |
|---|---|---|---|
| A | CSV → JSON | `csv`, `json` | tylko separator przecinek (plik ze średnikami z polskiego Excela da jedną kolumnę); wartości trafiają do JSON jako tekst |
| A | JSON → CSV | `csv`, `json` | Excel może źle pokazać polskie znaki po dwukrotnym kliknięciu (plik bez BOM) – użyj Dane → Z pliku tekstowego/CSV |
| B | TXT → PDF | LibreOffice | wejście tylko w UTF-8; brak formatowania, czcionka domyślna |
| B | TXT → DOCX | LibreOffice | wejście tylko w UTF-8; każda linia to akapit; brak nagłówków, list, tabel |
| B | TXT → ODT | LibreOffice | jak TXT → DOCX |
| B | PDF → TXT | pypdf | tylko warstwa tekstowa (skan daje komunikat o braku tekstu); układ i tabele są spłaszczane; PDF z hasłem nie jest obsługiwany; patrz uwaga niżej |
| C | DOCX → PDF | LibreOffice | brak czcionek dokumentu zmienia wygląd |
| C | ODT → PDF | LibreOffice | jak DOCX → PDF |
| C | DOCX → ODT | LibreOffice | makra, SmartArt i część stylów mogą zostać uproszczone lub utracone |
| C | ODT → DOCX | LibreOffice | elementy specyficzne dla LibreOffice mogą wyglądać inaczej w Wordzie |

**Uwaga: PDF z czcionką Cambria.** PDF utworzony przez LibreOffice na Windowsie
z dokumentu w czcionce Cambria wygląda poprawnie, ale ma błędną warstwę tekstu
(np. „Narżędżie” zamiast „Narzędzie”). Inne programy odczytują z niego to samo
(sprawdzono też bibliotekę pdfminer), więc nie da się tego naprawić przy odczycie.
Taki przypadek jest zapisywany w dzienniku jako ostrzeżenie. Dotyczy to m.in.
PDF-a z `testy/dane testowe/dokument.docx`. Sprawdzone czcionki Calibri, Arial,
Times New Roman, Liberation Serif i Liberation Mono działają poprawnie.

**Ograniczenia ogólne:**

- konwertowany jest jeden plik naraz,
- plik wynikowy ma nazwę pliku źródłowego z nowym rozszerzeniem,
- trwającej konwersji nie można anulować; kończy się ona sama albo po 60 s,
- zamknięcie okna w trakcie konwersji może pozostawić LibreOffice pracujący
  w tle do końca tej konwersji; w katalogu docelowym może wtedy zostać ukryty
  folder tymczasowy `.konwerter_*`, który można usunąć,
- otwarte okno LibreOffice może zablokować konwersję dokumentu.

## Struktura katalogów

```
Projekt_python_konwerter/
   gui.py                - okno programu (Tkinter/ttk) - plik do uruchomienia
   konwerter.py          - logika: rejestr, walidacja, funkcje konwertujące
   testy/
      test_konwerter.py  - testy automatyczne (unittest)
      dane testowe/      - pliki wejściowe do testów
      oczekiwane/        - sprawdzone, oczekiwane wyniki konwersji
      wyniki/            - wyniki z trybu skryptowego (poza repozytorium)
   docs/
      RAPORT_TESTOW.txt  - dane testowe, oczekiwane wyniki, raport testów
      ZRODLA.txt         - źródła, biblioteki, narzędzia AI
   README.md             - ten plik
   requirements.txt      - zależności
   konwerter.log         - dziennik programu (poza repozytorium)
```

## Jak działa program

- `@converter(".csv", ".json")` – dekorator wpisujący funkcję do słownika `REGISTRY`.
- `ConversionRequest` – plik źródłowy, format docelowy, katalog i zgoda na
  nadpisanie; metoda `validate()` sprawdza, czy konwersja jest możliwa.
- `execute()` – waliduje żądanie, uruchamia funkcję z rejestru w katalogu
  tymczasowym, przenosi gotowy plik na miejsce, mierzy czas i zapisuje dziennik.
- Model błędów – klasa bazowa `ConversionError` i jej podklasy:

  | Klasa | Sytuacja |
  |---|---|
  | `InputNotFoundError` | brak pliku wejściowego |
  | `OutputDirError` | brak katalogu docelowego lub prawa zapisu |
  | `UnsupportedConversionError` | niedozwolona para formatów |
  | `OutputExistsError` | plik wynikowy istnieje, brak zgody na nadpisanie |
  | `InvalidInputError` | błędna treść: zły JSON/CSV, kodowanie, uszkodzony DOCX/ODT/PDF |
  | `ToolNotFoundError` | brak LibreOffice lub pypdf |
  | `ConversionFailedError` | narzędzie zwróciło błąd, przekroczono czas, błąd zapisu |

- `gui.py` buduje okno i pobiera formaty z rejestru (`available_targets`,
  `supported_sources`, `supported_targets`), a konwersję zleca funkcji `execute()`.
- Konwersja działa w osobnym wątku. Tkinter nie pozwala zmieniać okna z innego
  wątku, dlatego wątek roboczy tylko wkłada wynik do kolejki (`queue.Queue`),
  a okno co 100 ms sprawdza ją metodą `root.after()`.

Nowy kierunek konwersji dodaje się, dopisując funkcję z dekoratorem. Pojawi się
ona w GUI bez żadnych zmian w `gui.py`.

### Decyzje biblioteczne

- **LibreOffice** zamiast python-docx i osobnych bibliotek: jedno narzędzie
  obsługuje DOCX, ODT i PDF z zachowaniem formatowania, a instrukcja dopuszcza
  tryb bez interfejsu.
- **pypdf** do PDF → TXT: LibreOffice domyślnie otwiera PDF w programie Draw
  i nie nadaje się do wyciągania tekstu; pypdf to czysty Python, łatwy do instalacji.

## Rozwiązywanie problemów

| Komunikat | Co zrobić |
|---|---|
| „Nie znaleziono pliku wejściowego”, choć plik jest w folderze | Windows mógł ukryć rozszerzenie (np. `dane.json.txt`). Włącz: Eksplorator → Widok → Pokaż → Rozszerzenia nazw plików. |
| „LibreOffice nie utworzył pliku wynikowego” | Zamknij otwarte okna LibreOffice i spróbuj ponownie. |
| „Brak narzędzia”, choć LibreOffice jest zainstalowany | Ustaw zmienną `LIBREOFFICE_PATH` (patrz: Instalacja). |
| „Plik CSV nie jest zapisany w kodowaniu UTF-8” | W Excelu: Plik → Zapisz jako → CSV UTF-8 (rozdzielany przecinkami). |
| „Brak biblioteki pypdf” | `python -m pip install -r requirements.txt` |
| „Błąd odczytu lub zapisu pliku” | Zamknij plik wynikowy, jeśli jest otwarty w innym programie. |
| Nieoczekiwany błąd | Szczegóły są w pliku `konwerter.log`. |

## Historia pracy (Git)

Pełna historia zmian jest w repozytorium Git. Commity odpowiadają etapom projektu:

| Data | Commit | Etap / zakres zmian |
|---|---|---|
| 2026-10-13 | Initial commit | utworzenie repozytorium |
| 2026-10-13 | python konwerter wrzucenie na gita | Lab. 2: szkielet z instrukcji, CSV ↔ JSON, dane testowe |
| 2026-10-13 | Create README.md | pierwsza wersja README |
| 2026-10-22 | Rozszerzenie | Lab. 3: DOCX/ODT/PDF przez LibreOffice, PDF → TXT, wykrywanie braku narzędzia |
| 2026-10-28 | GUI | Lab. 4: okno programu (Tkinter/ttk) |
| 2026-10-28 | GUI oraz lekkie poprawki | Lab. 4: pytanie o nadpisanie, pomiar czasu, poprawki okna |
| 2026-11-02 | Finalny pakiet do oddania zadania | struktura katalogów, dane i wyniki oczekiwane, dokumentacja |
| 2026-11-02 | Update README.txt | poprawki README |
| 2026-11-03 | Finalne dopięcie projektu | Lab. 5: model błędów, osobny wątek, LibreOffice na 3 systemach, testy automatyczne |
| 2026-11-03 | usuwanie pycache | porządki w repozytorium, README |
| 2026-11-03 | poprawki szybkie + txt converter | konwersje TXT → PDF/DOCX/ODT |
| 2026-11-04 | Poprawki konwerterów i walidacji | kontrola uszkodzonych DOCX/ODT, możliwości zapisu i danych CSV/JSON, bezpieczne nadpisywanie, dziennik |
| 2026-11-04 | GUI: macierz obsługiwanych par | przycisk i okno z macierzą par, włączenie dziennika |
| 2026-11-04 | Rozszerzenie testów automatycznych | testy nowych walidacji, nadpisywania, dziennika i okna (73 testy) |
| 2026-11-04 | Dokumentacja: README.md i raport testów | README w Markdownie, opis formatu CSV/JSON, aktualny raport testów |

## Autorzy

- Grzegorz Dyląg – autor projektu.
- Szkielet architektury (rejestr konwerterów, `ConversionRequest`, `execute`,
  konwerter DOCX → PDF) pochodzi z instrukcji projektowej przedmiotu.
- Ze względu na słabą znajomość języka Python pisanie kodu, testów
  i dokumentacji było wspomagane narzędziami AI Claude i Claude Code (Anthropic).
  Szczegóły i pozostałe źródła: `docs/ZRODLA.txt`.
