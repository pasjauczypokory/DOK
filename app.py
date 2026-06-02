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
    st.session_state.bufor_glowny = None
    st.session_state.bufor_pelnomocnictwo = None
    st.session_state.bufor_zalacznik = None
    st.session_state.bezpieczna_nazwa_firmy = ""
    st.session_state.plik_glownego = ""

# --- INTELIGENTNE POBIERANIE DANYCH ---
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
                return {
                    "nazwa": dane.get('name', ''),
                    "regon": dane.get('regon', ''),
                    "krs": krs or "Brak (CEIDG)",
                    "adres": adres,
                    "czy_krs": bool(krs) 
                }
        return None
    except Exception as e:
        return None

# --- WYGLĄD STRONY ---
st.set_page_config(page_title="Generator", page_icon="📝")
st.title("🩷 Generator + 📌 Linki")

# --- SZYBKIE SKRÓTY (LINKI) ---
st.markdown("""
[🍊 OMNI](https://sso.online.orange.pl/capGui/?url=https://esklep.online.orange.pl/konsola-konsultanta) &nbsp; | &nbsp; 
[🏢 Wyszukiwarka JDG](https://www.biznes.gov.pl/pl/wyszukiwarka-firm/) &nbsp; | &nbsp; 
[🏛️ Wyszukiwarka KRS](https://wyszukiwarka-krs.ms.gov.pl/) &nbsp; | &nbsp; 
[💻 VDI](https://login.t-mobile.pl/) &nbsp; | &nbsp; 
[📡 W jakiej sieci numer?](https://bip.uke.gov.pl/numeracja/dostawca-uslug/) &nbsp; | &nbsp; 
[📄 iLovePDF](https://www.ilovepdf.com/pl)
""")
st.divider() 

# --- RESZTA APLIKACJI ---
st.header("1. Wpisz NIP i wybierz datę")
col_nip, col_data = st.columns(2)
with col_nip:
    nip_input = st.text_input("Wpisz NIP (10 cyfr)")
with col_data:
    wybrana_data = st.date_input("Data na dokumentach:", datetime.date.today())

nazwa_do_edycji = ""
dane_z_api = None
czy_krs = False

# AUTOMATYCZNE ROZPOZNAWANIE KLIENTA
if nip_input and len(nip_input.strip().replace("-", "")) == 10:
    dane_z_api = pobierz_dane_z_api(nip_input.strip().replace("-", ""))
    if dane_z_api:
        nazwa_do_edycji = dane_z_api['nazwa']
        czy_krs = dane_z_api['czy_krs']
        
        if czy_krs:
            st.success(f"🏢 Wykryto Spółkę (KRS: {dane_z_api['krs']}). System automatycznie wygeneruje druk KRS.")
        else:
            st.info("👤 Wykryto działalność (CEIDG). System automatycznie wygeneruje druk JDG.")

st.header("2. Dane z bazy")
finalna_nazwa_firmy = st.text_input("Pełna nazwa firmy (edytuj, jeśli brakuje nazwy własnej w JDG):", value=nazwa_do_edycji)

st.header("3. Dane uzupełniające")
col1, col2 = st.columns(2)
with col1:
    imie_input = st.text_input("Imię i nazwisko reprezentanta")
    email_input = st.text_input("Adres e-mail")
with col2:
    tel_input = st.text_input("Telefon komórkowy")
    pesel_input = st.text_input("PESEL")

col3, col4 = st.columns(2)
with col3:
    if not czy_krs:
        nr_dowodu_input = st.text_input("Seria i nr Dowodu Osobistego")
    else:
        nr_dowodu_input = ""
with col4:
    id_weryfikacji_input = st.text_input("ID weryfikacji (do Załącznika)")

# --- LOGIKA GENEROWANIA ---
if st.button("Generuj Dokumenty", type="primary"):
    nip = nip_input.strip().replace("-", "")
    
    if len(nip) != 10:
        st.warning("Podaj poprawny, 10-cyfrowy NIP!")
    elif not finalna_nazwa_firmy:
        st.error("Uzupełnij nazwę firmy!")
    else:
        if not dane_z_api:
            st.error("Nie znaleziono firmy o takim NIP w bazie MF.")
        else:
            dowod_z_napisem = nr_dowodu_input.strip() if nr_dowodu_input else ""
            
            surowa_nazwa = finalna_nazwa_firmy
            formy_prawne = r"\b(SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ|SPÓŁKA Z O\.O\.|SP\. Z O\.O\.|SP Z O O|SPÓŁKA Z O O|SPÓŁKA JAWNA|SP\. J\.|SP J|SPÓŁKA AKCYJNA|S\.A\.|SA|SPÓŁKA KOMANDYTOWA|SP\. K\.|SP K|SPÓŁKA KOMANDYTOWO-AKCYJNA|S\.K\.A\.|SKA|SPÓŁKA PARTNERSKA|SP\. P\.|SP P|PROSTA SPÓŁKA AKCYJNA|P\.S\.A\.|PSA)\b"
            krotka_nazwa = re.sub(formy_prawne, "", surowa_nazwa, flags=re.IGNORECASE).strip()
            krotka_nazwa = re.sub(r'[,.-]+$', '', krotka_nazwa).strip()
            bezpieczna_nazwa = re.sub(r'[\\/*?:"<>|]', "", krotka_nazwa).strip()
            
            def generuj_plik(szablon):
                try:
                    doc = fitz.open(szablon)
                    font_bytes = get_font_bytes()
                    
                    # ETAP 1: WYPEŁNIANIE W PAMIĘCI
                    for page in doc:
                        if font_bytes:
                            page.insert_font(fontname="Roboto", fontbuffer=font_bytes)
                        
                        pola_do_narysowania = []
                        
                        # --- TUTAJ UPROŚCIŁEM KOD (Brak zbędnych ifów i spacji) ---
                        for widget in page.widgets():
                            if widget.field_type in [fitz.PDF_WIDGET_TYPE_TEXT, fitz.PDF_WIDGET_TYPE_COMBOBOX]:
                                nazwa_pola = widget.field_name or ""
                                n_lower = nazwa_pola.lower()
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
                                elif "mail" in n_lower:
                                    wartosc = email_input
                                elif "telefon" in n_lower:
                                    wartosc = tel_input
                                elif n_lower == "do" or "dowód" in n_lower or "dowod" in n_lower:
                                    wartosc = dowod_z_napisem
                                elif "pesel" in n_lower:
                                    wartosc = pesel_input
                                elif "imie" in n_lower or "nazwisko" in n_lower:
                                    wartosc = imie_input
                                elif "miejscowość" in n_lower or "miejscowosc" in n_lower:
                                    wartosc = "Warszawa