KONWERTER PLIKÓW
================

Projekt zaliczeniowy z przedmiotu Programowanie V, Politechnika Opolska.

Autor: Grzegorz Dyląg
Kod tworzony ze wsparciem narzędzia AI - szczegóły w sekcji AUTORZY
oraz w pliku docs/ZRODLA.txt.


CEL PROJEKTU
------------

Program okienkowy do konwersji plików między popularnymi formatami danych
i dokumentów. Ma rozszerzalną architekturę opartą na rejestrze
konwerterów: każdy kierunek konwersji to osobna funkcja zarejestrowana
dekoratorem, a interfejs graficzny automatycznie pokazuje wszystkie
zarejestrowane konwersje.


OBSŁUGIWANE FUNKCJE
-------------------

- 7 kierunków konwersji między formatami CSV, JSON, DOCX, ODT, PDF i TXT
  (patrz: TABELA WSPIERANYCH PAR FORMATÓW).
- Okno programu (Tkinter/ttk):
  - wybór pliku wejściowego i katalogu docelowego,
  - lista formatów docelowych zależna od rozszerzenia pliku,
  - blokada niedozwolonych par formatów,
  - pytanie przed nadpisaniem istniejącego pliku,
  - zrozumiałe komunikaty błędów.
- Wywoływanie narzędzia zewnętrznego (LibreOffice) w tle, bez shell=True,
  ze sprawdzaniem kodu zakończenia i limitem czasu (60 s).
- Wykrywanie braku LibreOffice lub biblioteki pypdf z opisem,
  co należy zainstalować.
- Rejestrowanie czasu każdej konwersji w terminalu ([log] ...).


WYMAGANIA
---------

- Python 3.10 lub nowszy - https://www.python.org/downloads/
  (przy instalacji na Windowsie zaznacz "Add Python to PATH")
- Tkinter - dołączony do Pythona na Windowsie
- pypdf 5.0 lub nowszy - potrzebny do konwersji PDF -> TXT
  (zapisany w requirements.txt)
- LibreOffice 7.x lub nowszy - potrzebny do konwersji DOCX / ODT / PDF
  https://www.libreoffice.org/download/

LibreOffice nie instaluje się przez pip. Program sam szuka go w PATH
oraz w domyślnym folderze C:\Program Files\LibreOffice.

Brak LibreOffice lub pypdf nie blokuje programu - pozostałe konwersje
działają, a przy próbie użycia brakującego narzędzia pojawia się
komunikat z instrukcją.


INSTALACJA
----------

1. Pobierz lub sklonuj repozytorium.
2. W terminalu, w folderze projektu, zainstaluj zależności:

      python -m pip install -r requirements.txt

3. Zainstaluj LibreOffice, jeśli chcesz konwertować dokumenty.


URUCHOMIENIE
------------

Program uruchamia się plikiem gui.py. W terminalu, w folderze projektu:

      python gui.py

albo: otwórz gui.py w VS Code i kliknij przycisk Run.

Pliki gui.py i konwerter.py muszą znajdować się w tym samym folderze
(gui.py korzysta z logiki zapisanej w konwerter.py).

Po uruchomieniu pojawia się okno "Konwerter plików":

1. Kliknij "Wybierz plik..." i wskaż plik do konwersji
   (przykładowe pliki są w folderze testy/dane testowe).
2. Katalog docelowy ustawia się automatycznie na folder pliku.
   Można go zmienić przyciskiem "Wybierz katalog..."
   (np. na testy/wyniki, żeby wyniki nie mieszały się z danymi).
3. Z listy "Format docelowy" wybierz format. Lista zawiera tylko
   formaty dozwolone dla danego rozszerzenia pliku.
4. Kliknij "Konwertuj".
5. Po zakończeniu pojawi się okno "Konwersja zakończona" ze ścieżką
   utworzonego pliku. W razie problemu pojawi się okno z opisem błędu
   i wskazówką, co zrobić.

Jeśli plik wynikowy już istnieje, program zapyta, czy go zastąpić.
Odpowiedź "Nie" pozostawia istniejący plik bez zmian.

Konwersja dokumentów przez LibreOffice trwa 1-2 sekundy - w tym czasie
kursor zmienia się w klepsydrę.


STRUKTURA KATALOGÓW
-------------------

Projekt_python_konwerter/
   gui.py                - okno programu (Tkinter/ttk) - plik do uruchomienia
   konwerter.py          - logika: rejestr, walidacja, funkcje konwertujące
   testy/
      dane testowe/      - pliki wejściowe do testów
      oczekiwane/        - sprawdzone, oczekiwane wyniki konwersji
      wyniki/            - wyniki konwersji z testów (poza repozytorium)
   docs/
      RAPORT_TESTOW.txt  - dane testowe, oczekiwane wyniki, raport testów
      ZRODLA.txt         - źródła, biblioteki, narzędzia AI
   CHANGELOG.txt         - dziennik zmian
   README.txt            - ten plik
   requirements.txt      - zależności
   .gitignore            - pliki pomijane przez Git
   .gitattributes


JAK DZIAŁA PROGRAM
------------------

- @converter(".csv", ".json") - dekorator wpisujący funkcję do słownika REGISTRY.
- ConversionRequest - przechowuje plik źródłowy, format docelowy, katalog
  i zgodę na nadpisanie; metoda validate() sprawdza, czy konwersja jest możliwa.
- execute() - wybiera funkcję z rejestru, pilnuje polityki nadpisywania
  i mierzy czas.
- gui.py buduje okno i reaguje na kliknięcia; nie ma wpisanych formatów
  na sztywno - pobiera je z rejestru (available_targets, supported_sources),
  a konwersję zleca funkcji execute() z konwerter.py.

Nowy kierunek konwersji dodaje się, dopisując funkcję z dekoratorem.
Pojawi się ona w GUI bez żadnych zmian w gui.py.


TABELA WSPIERANYCH PAR FORMATÓW
-------------------------------

CSV -> JSON
   Realizacja: biblioteki standardowe csv i json
   Ograniczenia:
   - separatorem musi być przecinek; pliki ze średnikiem (typowe dla
     polskiego Excela) dają jedną kolumnę,
   - plik musi być zapisany w UTF-8 (Windows-1250 daje błąd dekodowania),
   - wszystkie wartości trafiają do JSON jako tekst ("4.5", a nie 4.5),
   - pierwszy wiersz musi zawierać nagłówki.

JSON -> CSV
   Realizacja: biblioteki standardowe csv i json
   Ograniczenia:
   - JSON musi być listą obiektów (lub pojedynczym obiektem),
   - zagnieżdżone listy i obiekty zapisywane są w komórce jako tekst JSON,
   - true/false zapisują się jako True/False, a null jako pusta komórka,
   - kolejność kolumn wynika z kolejności pierwszego wystąpienia kluczy.

DOCX -> PDF
   Realizacja: LibreOffice
   Ograniczenia:
   - wymaga zainstalowanego LibreOffice,
   - brak czcionek użytych w dokumencie zmienia wygląd,
   - otwarte okno LibreOffice może zablokować konwersję,
   - limit czasu 60 s.

ODT -> PDF
   Realizacja: LibreOffice
   Ograniczenia: jak przy DOCX -> PDF.

DOCX -> ODT
   Realizacja: LibreOffice
   Ograniczenia: złożone elementy Worda (makra, SmartArt, niektóre style
   i pola) mogą zostać uproszczone lub utracone.

ODT -> DOCX
   Realizacja: LibreOffice
   Ograniczenia: elementy specyficzne dla LibreOffice mogą wyglądać
   inaczej w Wordzie.

PDF -> TXT
   Realizacja: biblioteka pypdf
   Ograniczenia:
   - odczytuje tylko warstwę tekstową - skany bez OCR dają pusty plik,
   - układ, tabele i obrazy są tracone (tabela staje się zwykłymi liniami tekstu),
   - PDF zabezpieczony hasłem nie zostanie odczytany.

Ograniczenia ogólne:
- konwertowany jest jeden plik naraz (brak trybu wsadowego),
- plik wynikowy ma nazwę pliku źródłowego z nowym rozszerzeniem;
  konflikt nazw jest obsługiwany pytaniem o nadpisanie,
- podczas konwersji przez LibreOffice okno programu nie reaguje
  przez 1-2 s (konwersja działa w głównym wątku),
- konwersji nie można przerwać przed upływem limitu czasu.


ROZWIĄZYWANIE PROBLEMÓW
-----------------------

- "Nie znaleziono pliku wejściowego", choć plik jest w folderze:
  Windows mógł ukryć rozszerzenie (np. plik to dane.json.txt).
  Włącz: Eksplorator -> Widok -> Pokaż -> Rozszerzenia nazw plików.

- "LibreOffice nie utworzył pliku wynikowego":
  zamknij otwarte okna LibreOffice i spróbuj ponownie.

- "Brak biblioteki pypdf":
  python -m pip install -r requirements.txt

- VS Code podkreśla import pypdf:
  Ctrl+Shift+P -> Python: Select Interpreter i wybierz ten sam Python,
  w którym instalowano pakiet.


AUTORZY
-------

- Grzegorz Dyląg - autor projektu.
- Szkielet architektury (rejestr konwerterów, ConversionRequest, execute,
  konwerter DOCX -> PDF) pochodzi z instrukcji projektowej przedmiotu.
- Ze względu na słabą znajomość języka Python, przy tworzeniu kodu
  i dokumentacji korzystano z narzędzia AI Claude (Anthropic).
  Zakres wsparcia opisano w pliku docs/ZRODLA.txt.
