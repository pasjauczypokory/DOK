import streamlit as st
import requests
import datetime
import re
import io
import fitz  # Potężna biblioteka PyMuPDF

# --- POBIERANIE OFICJALNEJ CZCIONKI Z POLSKIMI ZNAKAMI ---
@st.cache_data
def get_font_bytes():
    try:
        url = "https://fonts.gstatic.com/s/roboto/v30/KFOmCnqEu92Fr1Me5Q.ttf"
        return requests.get(url).content
    except:
        return None

# --- INICJALIZACJA PAMIĘCI PODRĘCZNEJ (SESSION STATE) ---
if 'wygenerowano' not in st.session_state:
    st.session_state.wygenerowano = False
    st.session_state.bufor_ork = None
    st.session_state.bufor_oswiadczenie = None
    st.session_state.bezpieczna_nazwa_firmy = ""
    st.session_state.plik_umowy = ""

# --- INTELIGENTNE POBIERANIE DANYCH + AUTOMATYCZNA MIEJSCOWOŚĆ ---
def pobierz_dane_z_api(nip):
    dzisiaj = datetime.date.today().strftime("%Y-%m-%d")
    url = f"https://wl-api.mf.gov.pl/api/search/nip/{nip}?date={dzisiaj}"
    try:
        odpowiedz = requests.get(url)
        if odpowiedz.status_code == 200:
            dane = odpowiedz.json()['result']['subject']
            if dane:
                adres = dane.get('workingAddress') or dane.get('residenceAddress') or ""
                krs = dane.get('krs', '')

                # WYCIĄGANIE MIEJSCOWOŚCI Z ADRESU (szukamy miasta zaraz po kodzie pocztowym XX-XXX)
                miejscowosc = "Warszawa"  # domyślny zapas
                if adres:
                    match = re.search(r'\d{2}-\d{3}\s+([A-ZĄĆĘŁŃÓŚŹŻa-ęćłńóśźż\s-]+)', adres)
                    if match:
                        miejscowosc = match.group(1).strip().title()

                # Próba automatycznego wyciągnięcia Imienia i Nazwiska z nazwy JDG
                pelna_nazwa = dane.get('name', '')
                wykryte_reprezentant = ""
                if not krs and pelna_nazwa:
                    slowa = pelna_nazwa.split()
                    if len(slowa) >= 2:
                        wykryte_reprezentant = f"{slowa[0].capitalize()} {slowa[1].capitalize()}"

                return {
                    "nazwa": pelna_nazwa,
                    "regon": dane.get('regon', ''),
                    "krs": krs or "Brak",
                    "adres": adres,
                    "miejscowosc": miejscowosc,
                    "czy_krs": bool(krs),
                    "wykryte_reprezentant": wykryte_reprezentant
                }
        return None
    except Exception as e:
        return None

# --- WYGLĄD STRONY ---
st.set_page_config(page_title="Generator Oświadczeń", page_icon="📝")
st.title("🗂️ Generator Oświadczeń")
st.divider()

# --- RESZTA APLIKACJI ---
st.header("1. Wpisz NIP i wybierz datę")
col_nip, col_data = st.columns(2)
with col_nip:
    nip_input = st.text_input("Wpisz NIP (10 cyfr)")
with col_data:
    wybrana_data = st.date_input("Data na dokumencie:", datetime.date.today())

nazwa_do_edycji = ""
reprezentant_auto = ""
dane_z_api = None
czy_krs = False

# AUTOMATYCZNE ROZPOZNAWANIE KLIENTA
if nip_input and len(nip_input.strip().replace("-", "")) == 10:
    dane_z_api = pobierz_dane_z_api(nip_input.strip().replace("-", ""))
    if dane_z_api:
        nazwa_do_edycji = dane_z_api['nazwa']
        czy_krs = dane_z_api['czy_krs']
        reprezentant_auto = dane_z_api['wykryte_reprezentant']

        if czy_krs:
            st.success(f"🏢 Wykryto Spółkę (KRS: {dane_z_api['krs']}). System automatycznie użyje wzoru KRS.")
        else:
            st.info("👤 Wykryto działalność (CEIDG). System automatycznie użyje wzoru JDG.")

st.header("2. Dane firmy")
finalna_nazwa_firmy = st.text_input("Pełna nazwa firmy (edytuj, jeśli zachodzi potrzeba):", value=nazwa_do_edycji)

# BLOK DANYCH UZUPEŁNIAJĄCYCH (Pokazuje się TYLKO dla działalności gospodarczej - CEIDG)
imie_input = ""
pesel_input = ""
nr_dowodu_input = ""

if not czy_krs and dane_z_api:
    st.header("3. Dane uzupełniające właściciela")
    col1, col2 = st.columns(2)
    with col1:
        imie_input = st.text_input("Imię i nazwisko reprezentanta:", value=reprezentant_auto)
        nr_dowodu_input = st.text_input("Seria i nr Dowodu Osobistego:")
    with col2:
        pesel_input = st.text_input("PESEL:")

# --- LOGIKA GENEROWANIA ---
if st.button("Generuj Oświadczenie", type="primary"):
    nip = nip_input.strip().replace("-", "")

    if len(nip) != 10:
        st.warning("Podaj poprawny, 10-cyfrowy NIP!")
    elif not finalna_nazwa_firmy:
        st.error("Uzupełnij nazwę firmy!")
    elif not czy_krs and not imie_input:
        st.error("Uzupełnij imię i nazwisko właściciela!")
    else:
        if not dane_z_api:
            st.error("Nie znaleziono firmy o takim NIP w bazie MF.")
        else:
            surowa_nazwa = finalna_nazwa_firmy

            # Bezpieczne rozbicie długiego tekstu na kilka linijek, żeby nie ucinało przy kopiowaniu
            formy_prawne = (
                r"\b(SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ|SPÓŁKA Z O\.O\.|SP\. Z O\.O\.|SP Z O O|SPÓŁKA Z O O|"
                r"SPÓŁKA JAWNA|SP\. J\.|SP J|SPÓŁKA AKCYJNA|S\.A\.|SA|SPÓŁKA KOMANDYTOWA|SP\. K\.|SP K|"
                r"SPÓŁKA KOMANDYTOWO-AKCYJNA|S\.K\.A\.|SKA|SPÓŁKA PARTNERSKA|SP\. P\.|SP P|"
                r"PROSTA SPÓŁKA AKCYJNA|P\.S\.A\.|PSA)\b"
            )

            krotka_nazwa = re.sub(formy_prawne, "", surowa_nazwa, flags=re.IGNORECASE).strip()
            krotka_nazwa = re.sub(r'[,.-]+$', '', krotka_nazwa).strip()
            bezpieczna_nazwa = re.sub(r'[\\/*?:"<>|]', "", krotka_nazwa).strip()

            def generuj_plik(szablon):
                """
                Zwraca krotkę (bufor_ork, bufor_oswiadczenie) - dwa osobne pliki PDF
                wycięte z tego samego, wypełnionego i spłaszczonego dokumentu:
                - ORK: zawsze pierwsze 2 strony
                - Oświadczenie: strona 3 (dla Spółki/KRS) albo strony 3-4 (dla JDG)
                W razie błędu zwraca (None, None).
                """
                try:
                    doc = fitz.open(szablon)
                    font_bytes = get_font_bytes()

                    for page in doc:
                        if font_bytes:
                            page.insert_font(fontname="Roboto", fontbuffer=font_bytes)

                        pola_do_narysowania = []

                        for widget in page.widgets():
                            if widget.field_type in [fitz.PDF_WIDGET_TYPE_TEXT, fitz.PDF_WIDGET_TYPE_COMBOBOX]:
                                nazwa_pola = widget.field_name or ""
                                n_lower = nazwa_pola.strip().lower()
                                wartosc = ""

                                if "firma" in n_lower or "nazwa" in n_lower:
                                    wartosc = finalna_nazwa_firmy
                                elif "adres" in n_lower:
                                    wartosc = dane_z_api['adres'] if dane_z_api else ""
                                elif "nip" in n_lower:
                                    wartosc = nip
                                elif "regon" in n_lower:
                                    wartosc = dane_z_api['regon'] if dane_z_api else ""
                                elif "krs" in n_lower:
                                    wartosc = dane_z_api['krs'] if dane_z_api else ""
                                elif "pesel" in n_lower:
                                    wartosc = pesel_input
                                elif nazwa_pola == "DO" or "dowód" in n_lower or "dowod" in n_lower:
                                    wartosc = nr_dowodu_input
                                elif "imie" in n_lower or "nazwisko" in n_lower or "reprezentant" in n_lower:
                                    wartosc = imie_input
                                elif "miejscowość" in n_lower or "miejscowosc" in n_lower:
                                    wartosc = dane_z_api['miejscowosc'] if dane_z_api else "Warszawa"
                                elif "data" in n_lower:
                                    wartosc = wybrana_data.strftime("%d.%m.%Y")

                                if wartosc:
                                    fs = widget.text_fontsize
                                    if fs <= 0:
                                        fs = 8
                                    pola_do_narysowania.append((widget.rect, str(wartosc), fs))

                        for annot in page.annots():
                            if annot.type[0] == 20:
                                page.delete_annot(annot)

                        for rect, text, fs in pola_do_narysowania:
                            rect.y0 += 4
                            rect.y1 += 15
                            rect.x1 += 30
                            rect.x0 += 2

                            if font_bytes:
                                page.insert_textbox(rect, text, fontname="Roboto", fontsize=fs, color=(0, 0, 0))
                            else:
                                page.insert_textbox(rect, text, fontsize=fs, color=(0, 0, 0))

                    # Spłaszczenie całego dokumentu do obrazów (jak wcześniej)
                    doc_flat = fitz.open()
                    for page in doc:
                        mat = fitz.Matrix(1.5, 1.5)
                        pix = page.get_pixmap(matrix=mat, alpha=False)
                        nowa_strona = doc_flat.new_page(width=page.rect.width, height=page.rect.height)

                        try:
                            img_bytes = pix.tobytes("jpeg")
                            nowa_strona.insert_image(page.rect, stream=img_bytes)
                        except:
                            nowa_strona.insert_image(page.rect, pixmap=pix)

                    doc.close()

                    liczba_stron = doc_flat.page_count

                    # --- PODZIAŁ NA DWA DOKUMENTY ---

                    # 1) ORK: zawsze pierwsze 2 strony (indeksy 0-1)
                    doc_ork = fitz.open()
                    koniec_ork = min(1, liczba_stron - 1)
                    if liczba_stron > 0:
                        doc_ork.insert_pdf(doc_flat, from_page=0, to_page=koniec_ork)
                    bufor_ork = io.BytesIO()
                    doc_ork.save(bufor_ork, deflate=True, garbage=3)
                    doc_ork.close()

                    # 2) Oświadczenie: strona 3 (KRS) albo strony 3-4 (JDG)
                    doc_osw = fitz.open()
                    if liczba_stron > 2:
                        if czy_krs:
                            # tylko strona 3 (indeks 2)
                            doc_osw.insert_pdf(doc_flat, from_page=2, to_page=2)
                        else:
                            # strony 3 i 4 (indeksy 2-3), jeśli strona 4 istnieje
                            koniec_osw = min(3, liczba_stron - 1)
                            doc_osw.insert_pdf(doc_flat, from_page=2, to_page=koniec_osw)
                    bufor_osw = io.BytesIO()
                    doc_osw.save(bufor_osw, deflate=True, garbage=3)
                    doc_osw.close()

                    doc_flat.close()

                    return bufor_ork.getvalue(), bufor_osw.getvalue()
                except Exception as e:
                    st.error(f"Szczegóły błędu dla pliku {szablon}: {e}")
                    return None, None

            plik_umowy = "KRS.pdf" if czy_krs else "JDG.pdf"

            bufor_ork, bufor_osw = generuj_plik(plik_umowy)

            st.session_state.bufor_ork = bufor_ork
            st.session_state.bufor_oswiadczenie = bufor_osw
            st.session_state.bezpieczna_nazwa_firmy = bezpieczna_nazwa
            st.session_state.plik_umowy = plik_umowy
            st.session_state.wygenerowano = True

if st.session_state.wygenerowano:
    if st.session_state.bufor_ork and st.session_state.bufor_oswiadczenie:
        st.success("Miłego dnia!")

        col_a, col_b = st.columns(2)
        with col_a:
            st.download_button(
                "⬇️ Pobierz ORK",
                data=st.session_state.bufor_ork,
                file_name=f"ORK_{st.session_state.bezpieczna_nazwa_firmy}.pdf",
                mime="application/pdf"
            )
        with col_b:
            st.download_button(
                "⬇️ Pobierz Oświadczenie",
                data=st.session_state.bufor_oswiadczenie,
                file_name=f"Oswiadczenie_{st.session_state.bezpieczna_nazwa_firmy}.pdf",
                mime="application/pdf"
            )
    else:
        st.error(f"Nie udało się wygenerować dokumentu ({st.session_state.plik_umowy}). Zobacz błąd powyżej.")
