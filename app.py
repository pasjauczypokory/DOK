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
    # POLE DOWODU ZAWSZE WIDOCZNE: Można wpisać dla JDG i do Załącznika przy spółce
    nr_dowodu_input = st.text_input("Seria i nr Dowodu Osobistego")
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
                                elif "mail" in n_lower:
                                    wartosc = email_input
                                elif "telefon" in n_lower:
                                    wartosc = tel_input
                                # SZTYWNE UDERZENIE W POLE "DO":
                                elif nazwa_pola == "DO" or "dowód" in n_lower or "dowod" in n_lower:
                                    wartosc = dowod_z_napisem
                                elif "pesel" in n_lower:
                                    wartosc = pesel_input
                                elif "imie" in n_lower or "nazwisko" in n_lower:
                                    wartosc = imie_input
                                elif "miejscowość" in n_lower or "miejscowosc" in n_lower:
                                    wartosc = "Warszawa"
                                elif "haslo" in n_lower or "hasło" in n_lower:
                                    wartosc = "12345678"
                                elif "dzień" in n_lower or "dzien" in n_lower:
                                    wartosc = wybrana_data.strftime("%d")
                                elif "miesiac" in n_lower:
                                    wartosc = wybrana_data.strftime("%m")
                                elif "rok" in n_lower:
                                    wartosc = wybrana_data.strftime("%Y")
                                elif "data" in n_lower:
                                    wartosc = wybrana_data.strftime("%d.%m.%Y")
                                elif "id" in n_lower and "weryfikacji" in n_lower:
                                    wartosc = id_weryfikacji_input

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
                                page.insert_textbox(rect, text, fontname="Roboto", fontsize=fs, color=(0,0,0))
                            else:
                                page.insert_textbox(rect, text, fontsize=fs, color=(0,0,0))
                    
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
                        
                    pdf_bufor = io.BytesIO()
                    doc_flat.save(pdf_bufor, deflate=True, garbage=3)
                    
                    doc.close()
                    doc_flat.close()
                    
                    return pdf_bufor.getvalue() 
                except Exception as e:
                    st.error(f"Szczegóły błędu dla pliku {szablon}: {e}")
                    return None
            
            plik_glownego = "KRS.pdf" if czy_krs else "JDG.pdf"
            
            st.session_state.bufor_glowny = generuj_plik(plik_glownego)
            st.session_state.bufor_pelnomocnictwo = generuj_plik("Pelnomocnictwo.pdf")
            st.session_state.bufor_zalacznik = generuj_plik("Zalacznik.pdf")
            st.session_state.bezpieczna_nazwa_firmy = bezpieczna_nazwa
            st.session_state.plik_glownego = plik_glownego
            
            st.session_state.wygenerowano = True

if st.session_state.wygenerowano:
    if st.session_state.bufor_glowny:
        st.success("Wygenerowano! Podpisz mnie proszę podpisem kwalifikowanym. Miłego dnia!")
        
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        
        with col_btn1:
            st.download_button(
                "⬇️ Pobierz Oświadczenie", 
                data=st.session_state.bufor_glowny, 
                file_name=f"Oswiadczenie_{st.session_state.bezpieczna_nazwa_firmy}.pdf", 
                mime="application/pdf"
            )
            
        if st.session_state.bufor_pelnomocnictwo:
            with col_btn2:
                st.download_button(
                    "⬇️ Pobierz Pełnomocnictwo", 
                    data=st.session_state.bufor_pelnomocnictwo, 
                    file_name=f"Pelnomocnictwo_{st.session_state.bezpieczna_nazwa_firmy}.pdf", 
                    mime="application/pdf"
                )
                
        if st.session_state.bufor_zalacznik:
            with col_btn3:
                st.download_button(
                    "⬇️ Pobierz Załącznik", 
                    data=st.session_state.bufor_zalacznik, 
                    file_name=f"Zalacznik_{st.session_state.bezpieczna_nazwa_firmy}.pdf", 
                    mime="application/pdf"
                )
    else:
        st.error(f"Nie udało się wygenerować głównego pliku ({st.session_state.plik_glownego}). Zobacz błąd powyżej.")