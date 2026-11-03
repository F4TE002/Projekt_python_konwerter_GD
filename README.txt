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
  - konwersja w osobnym wątku - okno nie zamarza, w trakcie widoczny
    jest pasek postępu, a przyciski są zablokowane,
  - zrozumiałe komunikaty błędów ze wskazówką, co zrobić.
- Wspólny model błędów - wszystkie błędy konwersji dziedziczą po klasie
  ConversionError i niosą tytuł, opis oraz wskazówkę dla użytkownika.
- Wywoływanie narzędzia zewnętrznego (LibreOffice) w tle, bez shell=True,
  ze sprawdzaniem kodu zakończenia i limitem czasu (60 s).
- Wykrywanie LibreOffice na Windows, macOS i Linux; brak LibreOffice
  lub biblioteki pypdf jest wykrywany i opisany.
- Rejestrowanie czasu każdej konwersji (terminal i okno programu).
- Testy automatyczne (unittest) - 42 testy.


WYMAGANIA
---------

- Python 3.10 lub nowszy - https://www.python.org/downloads/
  (przy instalacji na Windowsie zaznacz "Add Python to PATH")
- Tkinter - dołączony do Pythona na Windowsie i macOS
  (na Linuksie np.: sudo apt install python3-tk)
- pypdf 5.0 lub nowszy - potrzebny do konwersji PDF -> TXT
  (zapisany w requirements.txt)
- LibreOffice 7.x lub nowszy - potrzebny do konwersji DOCX / ODT / PDF
  https://www.libreoffice.org/download/

Brak LibreOffice lub pypdf nie blokuje programu - pozostałe konwersje
działają, a przy próbie użycia brakującego narzędzia pojawia się
komunikat z instrukcją instalacji dla danego systemu.


ZALEŻNOŚĆ: LIBREOFFICE
----------------------

LibreOffice nie instaluje się przez pip. Instalacja:

- Windows: instalator ze strony https://www.libreoffice.org/download/
- macOS:   instalator ze strony jw. albo: brew install --cask libreoffice
- Linux:   pakiet systemowy, np.: sudo apt install libreoffice
           (Fedora: sudo dnf install libreoffice)

Program szuka LibreOffice automatycznie (funkcja find_libreoffice),
w tej kolejności:

1. Zmienna środowiskowa LIBREOFFICE_PATH - jeśli jest ustawiona,
   wskazuje pełną ścieżkę do programu soffice (dla nietypowych instalacji).
2. PATH - polecenia soffice i libreoffice.
3. Typowe foldery instalacji dla danego systemu:
   - Windows: C:\Program Files\LibreOffice\program\soffice.exe
              C:\Program Files (x86)\LibreOffice\program\soffice.exe
   - macOS:   /Applications/LibreOffice.app/Contents/MacOS/soffice
              ~/Applications/LibreOffice.app/Contents/MacOS/soffice
   - Linux:   /usr/bin/soffice, /usr/lib/libreoffice/program/soffice,
              /usr/local/bin/soffice, /snap/bin/libreoffice,
              /opt/libreoffice*/program/soffice

Przykład ustawienia LIBREOFFICE_PATH na Windowsie (w terminalu, przed
uruchomieniem programu):

      set LIBREOFFICE_PATH=D:\Programy\LibreOffice\program\soffice.exe

Jeśli LibreOffice nie zostanie znaleziony, przy konwersji dokumentu
pojawia się okno "Brak narzędzia" z instrukcją instalacji.


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
4. Kliknij "Konwertuj". Podczas konwersji pod przyciskiem pojawia się
   pasek postępu, a przyciski są zablokowane. Okno cały czas reaguje
   (można je np. przesuwać).
5. Po zakończeniu pojawi się okno "Konwersja zakończona" ze ścieżką
   utworzonego pliku i czasem konwersji. W razie problemu pojawi się
   okno z opisem błędu i wskazówką, co zrobić.

Jeśli plik wynikowy już istnieje, program zapyta, czy go zastąpić.
Odpowiedź "Nie" pozostawia istniejący plik bez zmian.

Próba zamknięcia okna w trakcie konwersji wymaga potwierdzenia.


TESTY AUTOMATYCZNE
------------------

W terminalu, w folderze projektu:

      python -m unittest discover -s testy -v

Testy obejmują m.in. validate(), available_targets(), konwertery
CSV <-> JSON i dokumentów, wspólny model błędów, wykrywanie LibreOffice
oraz brak zamrażania okna. Opis i wyniki: docs/RAPORT_TESTOW.txt.


STRUKTURA KATALOGÓW
-------------------

Projekt_python_konwerter/
   gui.py                - okno programu (Tkinter/ttk) - plik do uruchomienia
   konwerter.py          - logika: rejestr, walidacja, funkcje konwertujące
   testy/
      test_konwerter.py  - testy automatyczne (unittest)
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
- Wspólny model błędów - klasa bazowa ConversionError i jej podklasy:
     InputNotFoundError          - brak pliku wejściowego
     OutputDirError              - brak katalogu docelowego
     UnsupportedConversionError  - niedozwolona para formatów
     OutputExistsError           - plik wynikowy istnieje, brak zgody na nadpisanie
     InvalidInputError           - błędne dane (zły JSON, pusty CSV, złe kodowanie,
                                   uszkodzony PDF)
     ToolNotFoundError           - brak LibreOffice lub pypdf
     ConversionFailedError       - narzędzie zwróciło błąd, przekroczono czas
  Każdy błąd ma tytuł, opis i wskazówkę (metoda user_message()), więc okno
  programu obsługuje wszystkie błędy jednym fragmentem kodu.
- gui.py buduje okno i reaguje na kliknięcia; nie ma wpisanych formatów
  na sztywno - pobiera je z rejestru (available_targets, supported_sources),
  a konwersję zleca funkcji execute() z konwerter.py.
- Konwersja działa w osobnym wątku (threading). Tkinter nie pozwala
  zmieniać okna z innego wątku, dlatego wątek roboczy tylko wkłada wynik
  do kolejki (queue.Queue), a okno co 100 ms sprawdza ją metodą root.after().

Nowy kierunek konwersji dodaje się, dopisując funkcję z dekoratorem.
Pojawi się ona w GUI bez żadnych zmian w gui.py.


TABELA WSPIERANYCH PAR FORMATÓW
-------------------------------

CSV -> JSON
   Realizacja: biblioteki standardowe csv i json
   Ograniczenia:
   - separatorem musi być przecinek; pliki ze średnikiem (typowe dla
     polskiego Excela) dają jedną kolumnę,
   - plik musi być zapisany w UTF-8 (plik w Windows-1250 jest odrzucany
     z komunikatem i wskazówką, jak zapisać go w UTF-8),
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
   - polskie znaki mogą zostać odczytane jako zniekształcone, jeśli PDF
     używa czcionki zapisującej litery z ogonkami jako dwa osobne znaki
     (zaobserwowane dla PDF utworzonych przez LibreOffice na Windowsie,
     np. "Zaż\x1co łć" zamiast "Zażółć"),
   - układ, tabele i obrazy są tracone (tabela staje się zwykłymi liniami tekstu),
   - PDF zabezpieczony hasłem lub uszkodzony nie zostanie odczytany
     (pojawia się komunikat "Nieprawidłowe dane").

Ograniczenia ogólne:
- konwertowany jest jeden plik naraz (brak trybu wsadowego),
- plik wynikowy ma nazwę pliku źródłowego z nowym rozszerzeniem;
  konflikt nazw jest obsługiwany pytaniem o nadpisanie,
- trwającej konwersji nie można anulować przyciskiem; kończy się ona
  sama albo po upływie limitu czasu (60 s),
- zamknięcie okna w trakcie konwersji dokumentu może pozostawić
  LibreOffice pracujący w tle do końca tej konwersji.


ROZWIĄZYWANIE PROBLEMÓW
-----------------------

- "Nie znaleziono pliku wejściowego", choć plik jest w folderze:
  Windows mógł ukryć rozszerzenie (np. plik to dane.json.txt).
  Włącz: Eksplorator -> Widok -> Pokaż -> Rozszerzenia nazw plików.

- "LibreOffice nie utworzył pliku wynikowego":
  zamknij otwarte okna LibreOffice i spróbuj ponownie.

- "Brak narzędzia", choć LibreOffice jest zainstalowany:
  ustaw zmienną LIBREOFFICE_PATH (patrz: ZALEŻNOŚĆ: LIBREOFFICE).

- "Plik CSV nie jest zapisany w kodowaniu UTF-8":
  w Excelu wybierz Plik -> Zapisz jako -> CSV UTF-8 (rozdzielany przecinkami).

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
- Ze względu na słabą znajomość języka Python, przy tworzeniu kodu,
  testów i dokumentacji korzystano z narzędzia AI Claude (Anthropic).
  Zakres wsparcia opisano w pliku docs/ZRODLA.txt.
