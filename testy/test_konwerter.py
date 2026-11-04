"""Testy automatyczne konwertera (biblioteka standardowa unittest).

Uruchomienie z folderu głównego projektu:
    python -m unittest discover -s testy -v

Testy wymagające LibreOffice, pypdf lub ekranu (GUI) są pomijane (skip),
jeśli danego elementu brak. Każdy test zapisuje wyniki do folderu
tymczasowego, więc nie zmienia plików projektu.
"""
from pathlib import Path
import json
import sys
import tempfile
import time
import unittest
from unittest import mock
import zipfile

PROJEKT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJEKT))

import konwerter as k  # noqa: E402

DANE = PROJEKT / "testy" / "dane testowe"
OCZEKIWANE = PROJEKT / "testy" / "oczekiwane"


def libreoffice_dostepny() -> bool:
    try:
        k.find_libreoffice()
        return True
    except k.ToolNotFoundError:
        return False


def pypdf_dostepny() -> bool:
    try:
        import pypdf  # noqa: F401
        return True
    except ImportError:
        return False


class TestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.out = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_conv(self, source: Path, fmt: str, overwrite: bool = False) -> Path:
        return k.execute(k.ConversionRequest(source, fmt, self.out, overwrite))

    def plik(self, nazwa: str, tresc: str | bytes) -> Path:
        """Tworzy plik pomocniczy w podfolderze 'wej' (inny niż folder wyników)."""
        folder = self.out / "wej"
        folder.mkdir(exist_ok=True)
        sciezka = folder / nazwa
        if isinstance(tresc, bytes):
            sciezka.write_bytes(tresc)
        else:
            sciezka.write_text(tresc, encoding="utf-8")
        return sciezka


# ---------------------------------------------------------------------------
# validate()
# ---------------------------------------------------------------------------

class TestValidate(TestBase):
    def test_poprawne_zadanie_przechodzi(self):
        k.ConversionRequest(DANE / "studenci.csv", ".json", self.out).validate()

    def test_rozszerzenie_wielkimi_literami(self):
        plik = self.plik("DANE.CSV", "a,b\n1,2\n")
        k.ConversionRequest(plik, ".JSON", self.out).validate()

    def test_brak_pliku_wejsciowego(self):
        req = k.ConversionRequest(DANE / "nie_istnieje.csv", ".json", self.out)
        with self.assertRaises(k.InputNotFoundError):
            req.validate()

    def test_brak_katalogu_docelowego(self):
        req = k.ConversionRequest(DANE / "studenci.csv", ".json", self.out / "brak")
        with self.assertRaises(k.OutputDirError):
            req.validate()

    def test_niedozwolona_para(self):
        req = k.ConversionRequest(DANE / "studenci.csv", ".pdf", self.out)
        with self.assertRaises(k.UnsupportedConversionError):
            req.validate()

    def test_plik_wynikowy_istnieje_bez_zgody(self):
        (self.out / "studenci.json").write_text("stary", encoding="utf-8")
        req = k.ConversionRequest(DANE / "studenci.csv", ".json", self.out)
        with self.assertRaises(k.OutputExistsError):
            req.validate()

    def test_plik_wynikowy_istnieje_za_zgoda(self):
        (self.out / "studenci.json").write_text("stary", encoding="utf-8")
        k.ConversionRequest(DANE / "studenci.csv", ".json", self.out, overwrite=True).validate()

    def test_target_path(self):
        req = k.ConversionRequest(Path("x/dane.CSV"), ".JSON", Path("wyniki"))
        self.assertEqual(req.target_path(), Path("wyniki/dane.json"))

    def test_katalog_bez_prawa_zapisu(self):
        req = k.ConversionRequest(DANE / "studenci.csv", ".json", self.out)
        with mock.patch("konwerter.Path.mkdir", side_effect=PermissionError("brak")):
            with self.assertRaisesRegex(k.OutputDirError, "zapisu"):
                req.validate()

    def test_puste_wybory(self):
        with self.assertRaises(k.InputNotFoundError):
            k.ConversionRequest(Path(""), ".json", self.out).validate()
        with self.assertRaises(k.UnsupportedConversionError):
            k.ConversionRequest(DANE / "studenci.csv", "", self.out).validate()


# ---------------------------------------------------------------------------
# available_targets()
# ---------------------------------------------------------------------------

class TestAvailableTargets(TestBase):
    def test_docx(self):
        self.assertEqual(k.available_targets(Path("a.docx")), [".odt", ".pdf"])

    def test_odt(self):
        self.assertEqual(k.available_targets(Path("a.odt")), [".docx", ".pdf"])

    def test_txt(self):
        self.assertEqual(k.available_targets(Path("a.txt")), [".docx", ".odt", ".pdf"])

    def test_csv_json_pdf(self):
        self.assertEqual(k.available_targets(Path("a.csv")), [".json"])
        self.assertEqual(k.available_targets(Path("a.json")), [".csv"])
        self.assertEqual(k.available_targets(Path("a.pdf")), [".txt"])

    def test_wielkosc_liter_bez_znaczenia(self):
        self.assertEqual(k.available_targets(Path("A.DOCX")), [".odt", ".pdf"])

    def test_nieobslugiwane_i_bez_rozszerzenia(self):
        self.assertEqual(k.available_targets(Path("a.xyz")), [])
        self.assertEqual(k.available_targets(Path("README")), [])

    def test_zgodnosc_z_rejestrem(self):
        for (src, target) in k.REGISTRY:
            self.assertIn(target, k.available_targets(Path(f"plik{src}")))
        self.assertEqual(len(k.REGISTRY), 10)


# ---------------------------------------------------------------------------
# Konwertery CSV <-> JSON (dane testowe autora)
# ---------------------------------------------------------------------------

class TestCsvJson(TestBase):
    def assert_json(self, wynik: Path, nazwa: str) -> None:
        self.assertEqual(json.loads(wynik.read_text(encoding="utf-8")),
                         json.loads((OCZEKIWANE / nazwa).read_text(encoding="utf-8")))

    def assert_csv(self, wynik: Path, nazwa: str) -> None:
        self.assertEqual(wynik.read_text(encoding="utf-8"),
                         (OCZEKIWANE / nazwa).read_text(encoding="utf-8"))

    def test_studenci_csv_do_json(self):
        self.assert_json(self.run_conv(DANE / "studenci.csv", ".json"), "studenci.json")

    def test_produkty_json_do_csv(self):
        self.assert_csv(self.run_conv(DANE / "produkty.json", ".csv"), "produkty.csv")

    def test_trudny1_json_do_csv(self):
        # null, brakujące klucze, dodatkowe pole, cudzysłów, przecinek, polskie znaki
        self.assert_csv(self.run_conv(DANE / "trudny1.json", ".csv"), "trudny1.csv")

    def test_trudny2_csv_do_json(self):
        # przecinek i cudzysłów w polu, pole w dwóch liniach, puste pola
        wynik = self.run_conv(DANE / "trudny2.csv", ".json")
        self.assert_json(wynik, "trudny2.json")
        self.assertEqual(json.loads(wynik.read_text(encoding="utf-8"))[2]["opis"],
                         "Opis\nw dwóch liniach")

    def test_w_obie_strony_bez_utraty_danych(self):
        json_plik = self.run_conv(DANE / "trudny2.csv", ".json")
        drugi = self.out / "drugi"
        drugi.mkdir()
        z_powrotem = k.execute(k.ConversionRequest(json_plik, ".csv", drugi))
        self.assertEqual((DANE / "trudny2.csv").read_text(encoding="utf-8").splitlines(),
                         z_powrotem.read_text(encoding="utf-8").splitlines())

    def test_kolejnosc_kolumn_i_puste_wartosci(self):
        plik = self.plik("dane.csv", "ż,a,m\nźdźbło,,x\n1\n")
        wiersze = json.loads(self.run_conv(plik, ".json").read_text(encoding="utf-8"))
        self.assertEqual(list(wiersze[0]), ["ż", "a", "m"])
        self.assertEqual(wiersze[0], {"ż": "źdźbło", "a": "", "m": "x"})     # puste pole -> ""
        self.assertEqual(wiersze[1], {"ż": "1", "a": None, "m": None})       # brak pola -> null

    def test_csv_tylko_naglowek(self):
        wynik = self.run_conv(self.plik("naglowek.csv", "a,b\n"), ".json")
        self.assertEqual(json.loads(wynik.read_text(encoding="utf-8")), [])

    def test_csv_z_bom_z_excela(self):
        wynik = self.run_conv(self.plik("excel.csv", "﻿imię\nŁukasz\n"), ".json")
        self.assertEqual(json.loads(wynik.read_text(encoding="utf-8")), [{"imię": "Łukasz"}])

    def test_json_z_bom(self):
        wynik = self.run_conv(self.plik("bom.json", '﻿[{"a": "ż"}]'), ".csv")
        self.assertEqual(wynik.read_text(encoding="utf-8").splitlines(), ["a", "ż"])

    def test_json_wartosci_specjalne(self):
        plik = self.plik("typy.json", '[{"t": true, "n": null, "l": [1, "ą"]}]')
        wynik = self.run_conv(plik, ".csv")
        self.assertEqual(wynik.read_text(encoding="utf-8").splitlines(),
                         ["t,n,l", 'true,,"[1, ""ą""]"'])


# ---------------------------------------------------------------------------
# Wspólny model błędów
# ---------------------------------------------------------------------------

class TestModelBledow(TestBase):
    def test_wszystkie_bledy_dziedzicza_po_conversion_error(self):
        for klasa in (k.InputNotFoundError, k.OutputDirError, k.UnsupportedConversionError,
                      k.OutputExistsError, k.InvalidInputError, k.ToolNotFoundError,
                      k.ConversionFailedError):
            self.assertTrue(issubclass(klasa, k.ConversionError), klasa.__name__)
            self.assertTrue(klasa.title, klasa.__name__)

    def test_komunikat_zawiera_wskazowke(self):
        blad = k.InvalidInputError("Treść", "Wskazówka")
        self.assertEqual(blad.user_message(), "Treść\n\nWskazówka")

    def test_bledny_json(self):
        plik = self.plik("bledny.json", '[{"id": 1')
        with self.assertRaisesRegex(k.InvalidInputError, "Niepoprawny JSON"):
            self.run_conv(plik, ".csv")

    def test_json_nie_lista_obiektow(self):
        plik = self.plik("liczby.json", "[1, 2, 3]")
        with self.assertRaisesRegex(k.InvalidInputError, "listą obiektów"):
            self.run_conv(plik, ".csv")

    def test_json_bez_danych(self):
        for nazwa, tresc in (("lista.json", "[]"), ("obiekt.json", "[{}]")):
            with self.assertRaisesRegex(k.InvalidInputError, "żadnych danych"):
                self.run_conv(self.plik(nazwa, tresc), ".csv")

    def test_pusty_csv(self):
        for nazwa, tresc in (("pusty.csv", ""), ("entery.csv", "\n\n\n")):
            with self.assertRaisesRegex(k.InvalidInputError, "pusty"):
                self.run_conv(self.plik(nazwa, tresc), ".json")

    def test_csv_powtorzone_kolumny(self):
        with self.assertRaisesRegex(k.InvalidInputError, "powtórzone"):
            self.run_conv(self.plik("dup.csv", "a,a\n1,2\n"), ".json")

    def test_csv_wiersz_z_nadmiarem_pol(self):
        with self.assertRaisesRegex(k.InvalidInputError, "Wiersz 3"):
            self.run_conv(self.plik("nadmiar.csv", "a,b\n1,2\n1,2,3\n"), ".json")

    def test_uszkodzone_docx_i_odt(self):
        # sprawdzane przed uruchomieniem LibreOffice, więc nie wymaga narzędzia
        with mock.patch("konwerter.subprocess.run") as run:
            for nazwa in ("zly.docx", "zly.odt"):
                with self.assertRaisesRegex(k.InvalidInputError, "uszkodzony"):
                    self.run_conv(self.plik(nazwa, "to nie jest dokument"), ".pdf")
        run.assert_not_called()

    def test_archiwum_bez_tresci_dokumentu(self):
        plik = self.plik("arkusz.docx", b"")
        with zipfile.ZipFile(plik, "w") as z:              # np. XLSX ze zmienioną nazwą
            z.writestr("xl/workbook.xml", "<x/>")
        with self.assertRaisesRegex(k.InvalidInputError, "uszkodzony"):
            self.run_conv(plik, ".pdf")

    @unittest.skipUnless(pypdf_dostepny(), "brak pypdf")
    def test_pdf_bez_tekstu(self):
        from pypdf import PdfWriter
        plik = self.plik("skan.pdf", b"")
        writer = PdfWriter()
        writer.add_blank_page(200, 200)
        writer.write(plik)
        with self.assertRaisesRegex(k.InvalidInputError, "nie zawiera tekstu"):
            self.run_conv(plik, ".txt")

    @unittest.skipUnless(pypdf_dostepny(), "brak pypdf")
    def test_pdf_zabezpieczony_haslem(self):
        from pypdf import PdfWriter
        plik = self.plik("tajny.pdf", b"")
        writer = PdfWriter()
        writer.add_blank_page(200, 200)
        writer.encrypt("haslo", algorithm="RC4-128")
        writer.write(plik)
        with self.assertRaisesRegex(k.InvalidInputError, "hasłem"):
            self.run_conv(plik, ".txt")

    def test_czyszczenie_tekstu_pdf(self):
        self.assertEqual(k.clean_pdf_text("ó\x1c\r\na\tb"), "ó\na\tb")

    def test_brak_pypdf_jest_opisany(self):
        plik = self.plik("a.pdf", "x")
        with mock.patch.dict(sys.modules, {"pypdf": None}):
            with self.assertRaises(k.ToolNotFoundError) as ctx:
                self.run_conv(plik, ".txt")
        self.assertIn("pip install", ctx.exception.user_message())

    def test_bledy_i_sukcesy_sa_logowane(self):
        with self.assertLogs("konwerter", "ERROR") as logi:
            with self.assertRaises(k.InvalidInputError):
                self.run_conv(self.plik("zly.json", "{"), ".csv")
        self.assertIn("Nieprawidłowe dane", logi.output[0])
        with self.assertLogs("konwerter", "INFO") as logi:
            self.run_conv(DANE / "studenci.csv", ".json")
        self.assertIn("gotowe", logi.output[0])

    def test_csv_w_kodowaniu_windows_1250(self):
        plik = self.plik("excel.csv", "imie,miasto\nŁukasz,Wrocław\n".encode("cp1250"))
        with self.assertRaises(k.InvalidInputError) as ctx:
            self.run_conv(plik, ".json")
        self.assertIn("UTF-8", ctx.exception.user_message())

    def test_txt_w_kodowaniu_windows_1250(self):
        # sprawdzane przed uruchomieniem LibreOffice, więc nie wymaga narzędzia
        plik = self.plik("ansi.txt", "Zażółć gęślą jaźń".encode("cp1250"))
        with self.assertRaises(k.InvalidInputError) as ctx:
            self.run_conv(plik, ".pdf")
        self.assertIn("UTF-8", ctx.exception.user_message())

    @unittest.skipUnless(pypdf_dostepny(), "brak pypdf")
    def test_uszkodzony_pdf(self):
        plik = self.plik("zly.pdf", "to nie jest PDF")
        with self.assertRaises(k.InvalidInputError):
            self.run_conv(plik, ".txt")


# ---------------------------------------------------------------------------
# Polityka nadpisywania
# ---------------------------------------------------------------------------

class TestNadpisywanie(TestBase):
    def test_bez_zgody_plik_nie_jest_nadpisany(self):
        istniejacy = self.out / "studenci.json"
        istniejacy.write_text("STARA TREŚĆ", encoding="utf-8")
        with self.assertRaises(k.OutputExistsError):
            self.run_conv(DANE / "studenci.csv", ".json")
        self.assertEqual(istniejacy.read_text(encoding="utf-8"), "STARA TREŚĆ")

    def test_za_zgoda_plik_jest_nadpisany(self):
        istniejacy = self.out / "studenci.json"
        istniejacy.write_text("STARA TREŚĆ", encoding="utf-8")
        self.run_conv(DANE / "studenci.csv", ".json", overwrite=True)
        self.assertIn("Kowalska", istniejacy.read_text(encoding="utf-8"))

    def test_nieudana_konwersja_nie_niszczy_starego_pliku(self):
        istniejacy = self.out / "zly.csv"
        istniejacy.write_text("STARA TREŚĆ", encoding="utf-8")
        with self.assertRaises(k.InvalidInputError):
            self.run_conv(self.plik("zly.json", "{"), ".csv", overwrite=True)
        self.assertEqual(istniejacy.read_text(encoding="utf-8"), "STARA TREŚĆ")

    def test_w_katalogu_docelowym_nie_zostaja_smieci(self):
        with self.assertRaises(k.InvalidInputError):
            self.run_conv(self.plik("zly.json", "{"), ".csv")
        self.run_conv(DANE / "studenci.csv", ".json")
        self.assertEqual(sorted(p.name for p in self.out.iterdir()), ["studenci.json", "wej"])


# ---------------------------------------------------------------------------
# Wykrywanie LibreOffice na różnych systemach
# ---------------------------------------------------------------------------

class TestWykrywanieLibreOffice(TestBase):
    def test_kandydaci_windows(self):
        with mock.patch.object(k.sys, "platform", "win32"):
            sciezki = [str(p) for p in k.libreoffice_candidates()]
        self.assertTrue(any("LibreOffice" in s and s.endswith("soffice.exe") for s in sciezki))

    def test_kandydaci_macos(self):
        with mock.patch.object(k.sys, "platform", "darwin"):
            sciezki = k.libreoffice_candidates()
        self.assertIn(Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"), sciezki)

    def test_kandydaci_linux(self):
        with mock.patch.object(k.sys, "platform", "linux"):
            sciezki = k.libreoffice_candidates()
        self.assertIn(Path("/usr/bin/soffice"), sciezki)

    def test_zmienna_srodowiskowa_ma_pierwszenstwo(self):
        udawany = self.plik("soffice", "")
        with mock.patch.dict(k.os.environ, {k.LIBREOFFICE_ENV: str(udawany)}):
            self.assertEqual(k.find_libreoffice(), str(udawany))

    def test_brak_libreoffice_jest_wykrywany_i_opisany(self):
        with mock.patch.dict(k.os.environ, {k.LIBREOFFICE_ENV: ""}), \
             mock.patch("konwerter.shutil.which", return_value=None), \
             mock.patch("konwerter.libreoffice_candidates", return_value=[]):
            with self.assertRaises(k.ToolNotFoundError) as ctx:
                self.run_conv(DANE / "dokument.docx", ".pdf")
        self.assertIn("libreoffice", ctx.exception.user_message().lower())
        self.assertIn(k.LIBREOFFICE_ENV, ctx.exception.user_message())

    def test_wywolanie_bez_shell_i_jako_lista(self):
        wynik = mock.Mock(returncode=0, stderr="")
        with mock.patch("konwerter.find_libreoffice", return_value="soffice"), \
             mock.patch("konwerter.subprocess.run", return_value=wynik) as run:
            (self.out / "dokument.pdf").write_bytes(b"%PDF")   # udajemy wynik
            k.run_libreoffice(DANE / "dokument.docx", self.out, ".pdf", "pdf")
        args, kwargs = run.call_args
        self.assertIsInstance(args[0], list)
        self.assertNotIn("shell", kwargs)

    def test_txt_wymusza_kodowanie_utf8(self):
        wynik = mock.Mock(returncode=0, stderr="")
        with mock.patch("konwerter.find_libreoffice", return_value="soffice"), \
             mock.patch("konwerter.subprocess.run", return_value=wynik) as run:
            (self.out / "tekst.pdf").write_bytes(b"%PDF")      # udajemy wynik
            k.txt_to_pdf(DANE / "tekst.txt", self.out)
        polecenie = run.call_args[0][0]
        self.assertIn(f"--infilter={k.TXT_INFILTER}", polecenie)
        self.assertIn("UTF8", k.TXT_INFILTER)

    def test_niezerowy_kod_zakonczenia_to_blad(self):
        wynik = mock.Mock(returncode=1, stderr="symulowany błąd")
        with mock.patch("konwerter.find_libreoffice", return_value="soffice"), \
             mock.patch("konwerter.subprocess.run", return_value=wynik):
            with self.assertRaisesRegex(k.ConversionFailedError, "kodem 1"):
                k.run_libreoffice(DANE / "dokument.docx", self.out, ".pdf", "pdf")


# ---------------------------------------------------------------------------
# Konwertery dokumentów (wymagają LibreOffice)
# ---------------------------------------------------------------------------

@unittest.skipUnless(libreoffice_dostepny(), "brak LibreOffice")
class TestDokumenty(TestBase):
    def test_docx_do_pdf(self):
        self.assertTrue(self.run_conv(DANE / "dokument.docx", ".pdf").read_bytes().startswith(b"%PDF"))

    def test_odt_do_pdf(self):
        self.assertTrue(self.run_conv(DANE / "notatka.odt", ".pdf").read_bytes().startswith(b"%PDF"))

    def test_docx_do_odt(self):
        self.assertTrue(self.run_conv(DANE / "dokument.docx", ".odt").read_bytes().startswith(b"PK"))

    def test_odt_do_docx(self):
        self.assertTrue(self.run_conv(DANE / "notatka.odt", ".docx").read_bytes().startswith(b"PK"))

    def test_txt_do_docx_zachowuje_polskie_znaki(self):
        wynik = self.run_conv(DANE / "tekst.txt", ".docx")
        with zipfile.ZipFile(wynik) as z:                 # DOCX to archiwum ZIP z XML
            tresc = z.read("word/document.xml").decode("utf-8")
        self.assertIn("Zażółć gęślą jaźń", tresc)

    def test_txt_do_odt_zachowuje_polskie_znaki(self):
        wynik = self.run_conv(DANE / "tekst.txt", ".odt")
        with zipfile.ZipFile(wynik) as z:                 # ODT to archiwum ZIP z XML
            tresc = z.read("content.xml").decode("utf-8")
        self.assertIn("Zażółć gęślą jaźń", tresc)

    def test_txt_do_pdf(self):
        self.assertTrue(self.run_conv(DANE / "tekst.txt", ".pdf").read_bytes().startswith(b"%PDF"))

    @unittest.skipUnless(pypdf_dostepny(), "brak pypdf")
    def test_pdf_do_txt(self):
        txt = self.run_conv(self.run_conv(DANE / "dokument.docx", ".pdf"), ".txt")
        tekst = txt.read_text(encoding="utf-8")
        # dokument.docx używa czcionki Cambria, dla której LibreOffice na Windowsie
        # zapisuje w PDF błędną warstwę tekstu (ograniczenie opisane w README),
        # dlatego tutaj sprawdzamy słowa bez polskich znaków. Polskie znaki
        # sprawdza test_pdf_do_txt_zachowuje_polskie_znaki.
        for slowo in ("Dokument testowy", "Konwerter", "DOCX", "PDF", "ODT", "Format"):
            self.assertIn(slowo, tekst)

    @unittest.skipUnless(pypdf_dostepny(), "brak pypdf")
    def test_pdf_do_txt_zachowuje_polskie_znaki(self):
        txt = self.run_conv(self.run_conv(DANE / "tekst.txt", ".pdf"), ".txt")
        self.assertIn("Zażółć gęślą jaźń. ĄĘÓŁŚŻŹĆŃ", txt.read_text(encoding="utf-8"))

    def test_akapity_txt_zostaja_osobnymi_akapitami(self):
        wynik = self.run_conv(DANE / "tekst.txt", ".docx")
        with zipfile.ZipFile(wynik) as z:
            tresc = z.read("word/document.xml").decode("utf-8")
        self.assertEqual(tresc.count("<w:p>") + tresc.count("<w:p "), 4)


# ---------------------------------------------------------------------------
# GUI: konwersja nie zamraża okna
# ---------------------------------------------------------------------------

class TestGuiBezZamrazania(TestBase):
    def setUp(self) -> None:
        super().setUp()
        try:
            import tkinter as tk
            self.root = tk.Tk()
            self.root.withdraw()
        except Exception as e:           # brak ekranu / brak Tkintera
            self.skipTest(f"GUI niedostępne: {e}")
        import gui
        self.app = gui.KonwerterApp(self.root)
        self.messages: list = []
        self._patches = [
            mock.patch("gui.messagebox.showinfo", lambda t, m, **kw: self.messages.append(t)),
            mock.patch("gui.messagebox.showerror", lambda t, m, **kw: self.messages.append(t)),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self) -> None:
        for p in getattr(self, "_patches", []):
            p.stop()
        if hasattr(self, "root"):
            self.root.destroy()
        super().tearDown()

    def test_okno_reaguje_podczas_dlugiej_konwersji(self):
        def wolna_konwersja(request):          # udaje konwersję trwającą 1 s
            time.sleep(1.0)
            return request.target_path()

        self.app.source_var.set(str(DANE / "studenci.csv"))
        self.app.output_var.set(str(self.out))
        self.app.refresh_formats(DANE / "studenci.csv")

        odswiezenia = [0]
        def tik():
            odswiezenia[0] += 1
            self.root.after(20, tik)
        tik()

        with mock.patch("gui.execute", wolna_konwersja):
            start = time.perf_counter()
            self.app.run_conversion()
            czas_wywolania = time.perf_counter() - start
            self.assertTrue(self.app.is_busy())
            self.assertEqual(str(self.app.convert_btn["state"]), "disabled")
            while not self.messages:
                self.root.update()
                time.sleep(0.01)

        self.assertLess(czas_wywolania, 0.2)       # przycisk nie blokuje okna
        self.assertGreater(odswiezenia[0], 20)     # okno odświeżało się w trakcie
        self.assertEqual(self.messages[-1], "Konwersja zakończona")
        self.assertEqual(str(self.app.convert_btn["state"]), "normal")

    def test_blad_z_watku_trafia_do_okna(self):
        self.app.source_var.set(str(DANE / "studenci.csv"))
        self.app.output_var.set(str(self.out))
        self.app.refresh_formats(DANE / "studenci.csv")
        with mock.patch("gui.execute", side_effect=k.ToolNotFoundError("brak")):
            self.app.run_conversion()
            while not self.messages:
                self.root.update()
                time.sleep(0.01)
        self.assertEqual(self.messages[-1], "Brak narzędzia")

    def test_formaty_zalezne_od_rozszerzenia(self):
        self.app.source_var.set(str(DANE / "dokument.docx"))
        self.app.output_var.set(str(self.out))
        self.app.refresh_formats(DANE / "dokument.docx")
        self.assertEqual(list(self.app.format_box["values"]), [".odt", ".pdf"])
        self.assertEqual(str(self.app.convert_btn["state"]), "normal")

    def test_nieobslugiwany_plik_blokuje_konwersje(self):
        self.app.source_var.set("dane.xyz")
        self.app.output_var.set(str(self.out))
        self.app.refresh_formats(Path("dane.xyz"))
        self.assertEqual(str(self.app.format_box["state"]), "disabled")
        self.assertEqual(str(self.app.convert_btn["state"]), "disabled")

    def test_odmowa_nadpisania_nie_uruchamia_konwersji(self):
        istniejacy = self.out / "studenci.json"
        istniejacy.write_text("STARA TREŚĆ", encoding="utf-8")
        self.app.source_var.set(str(DANE / "studenci.csv"))
        self.app.output_var.set(str(self.out))
        self.app.refresh_formats(DANE / "studenci.csv")
        with mock.patch("gui.messagebox.askyesno", return_value=False), \
             mock.patch("gui.execute") as wykonaj:
            self.app.run_conversion()
        wykonaj.assert_not_called()
        self.assertEqual(istniejacy.read_text(encoding="utf-8"), "STARA TREŚĆ")

    def test_macierz_par_zgodna_z_rejestrem(self):
        tabela = self.app.show_matrix()
        kolumny = list(tabela["columns"])
        znaczniki = 0
        for wiersz in tabela.get_children():
            zrodlo = tabela.item(wiersz, "text")
            for cel, znak in zip(kolumny, tabela.item(wiersz, "values")):
                self.assertEqual(znak == "✓", (zrodlo, cel) in k.REGISTRY)
                znaczniki += znak == "✓"
        self.assertEqual(znaczniki, len(k.REGISTRY))


if __name__ == "__main__":
    unittest.main(verbosity=2)
