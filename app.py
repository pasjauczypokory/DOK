import streamlit as st
import requests
import datetime
import re
import io
from pypdf import PdfWriter, PdfReader
from pypdf.generic import NameObject, NumberObject, ArrayObject

def pobierz_dane_z_api(nip):
    dzisiaj = datetime.date.today().strftime("%Y-%m-%d")
    url = f"https://wl-api.mf.gov.pl/api/search/nip/{nip}?date={dzisiaj}"
    try:
        odpowiedz = requests.get(url)
        if odpowiedz.status_code == 200:
            dane = odpowiedz.json()['result']['subject']
            if dane:
                adres = dane.get('workingAddress') or dane.get('residenceAddress') or ""
                return {
                    "nazwa": dane.get('name', ''),
                    "regon": dane.get('regon', ''),
                    "krs": dane.get('krs', '') or "Brak (CEIDG)",
                    "adres": adres
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
st.header("1. Wybierz rodzaj klienta i datę")
col_typ, col_data = st.columns(2)
with col_typ:
    typ_klienta = st.radio("Rodzaj podmiotu:", ["Spółka (KRS)", "Jednoosobowa Działalność (JDG)"])
with col_data:
    wybrana_data = st.date_input("Data na dokumentach:", datetime.date.today())

st.header("2. Dane z bazy")
nip_input = st.text_input("Wpisz NIP (10 cyfr)")

nazwa_do_edycji = ""
dane_z_api = None

if nip_input and len(nip_input.strip().replace("-", "")) == 10:
    dane_z_api = pobierz_dane_z_api(nip_input.strip().replace("-", ""))
    if dane_z_api:
        nazwa_do_edycji = dane_z_api['nazwa']

finalna_nazwa_firmy = st.text_input("Pełna nazwa firmy (edytuj, jeśli brakuje nazwy własnej w JDG):", value=nazwa_do_edycji)

st.header("3. Dane uzupełniające")
col1, col2 = st.columns(2)
with col1:
    imie_input = st.text_input("Imię i nazwisko reprezentanta")
    email_input = st.text_input("Adres e-mail")
with col2:
    tel_input = st.text_input("Telefon komórkowy")
    pesel_input = st.text_input("PESEL")

# Dodatkowe pola zależne od wyboru
col3, col4 = st.columns(2)
with col3:
    if typ_klienta == "Jednoosobowa Działalność (JDG)":
        nr_dowodu_input = st.text_input("Seria i nr Dowodu Osobistego")
    else:
        nr_dowodu_input = ""
with col4:
    id_weryfikacji_input = st.text_input("ID weryfikacji (do Załącznika)")

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
            
            dane_do_pdf = {
                "Firma": finalna_nazwa_firmy, 
                "adres": dane_z_api['adres'],
                "NIP": nip,
                "REGON": dane_z_api['regon'],
                "KRS": dane_z_api['krs'],
                
                "Email": email_input,             
                ".Email": email_input,             
                "E-mail": email_input, 
                
                "Telefon": tel_input,             
                "DO": dowod_z_napisem,                 
                "PESEL": pesel_input,             
                "ImieNazwisko": imie_input,       
                "imie_i_nazwisko_klienta": imie_input, 
                "Miejscowość": "Warszawa", 
                
                "Haslo": "12345678",                   
                "Hasło": "12345678", 
                
                "dzień": wybrana_data.strftime("%d"),
                "miesiac": wybrana_data.strftime("%m"),
                "rok": wybrana_data.strftime("%Y"),
                "Data": wybrana_data.strftime("%d.%m.%Y"),
                
                "id": "",
                "ID": "",
                "TAK": "", 
                "NIE": "",
                
                # Nasze nowe pole z ID!
                "ID_weryfikacji": id_weryfikacji_input 
            }
            
            surowa_nazwa = finalna_nazwa_firmy
            formy_prawne = r"\b(SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ|SPÓŁKA Z O\.O\.|SP\. Z O\.O\.|SP Z O O|SPÓŁKA Z O O|SPÓŁKA JAWNA|SP\. J\.|SP J|SPÓŁKA AKCYJNA|S\.A\.|SA|SPÓŁKA KOMANDYTOWA|SP\. K\.|SP K|SPÓŁKA KOMANDYTOWO-AKCYJNA|S\.K\.A\.|SKA|SPÓŁKA PARTNERSKA|SP\. P\.|SP P|PROSTA SPÓŁKA AKCYJNA|P\.S\.A\.|PSA)\b"
            krotka_nazwa = re.sub(formy_prawne, "", surowa_nazwa, flags=re.IGNORECASE).strip()
            krotka_nazwa = re.sub(r'[,.-]+$', '', krotka_nazwa).strip()
            bezpieczna_nazwa_firmy = re.sub(r'[\\/*?:"<>|]', "", krotka_nazwa).strip()
            
            def generuj_plik(szablon):
                try:
                    writer = PdfWriter(clone_from=szablon)
                    try:
                        writer.add_need_appearances()
                    except Exception:
                        pass 
                    
                    for strona in writer.pages:
                        writer.update_page_form_field_values(strona, dane_do_pdf)
                    
                    for page in writer.pages:
                        if "/Annots" in page:
                            for annot in page["/Annots"]:
                                annot_obj = annot.get_object()
                                if annot_obj.get("/Subtype") == "/Widget":
                                    annot_obj.update({NameObject("/Ff"): NumberObject(1)}) 
                                    
                    pdf_bufor = io.BytesIO()
                    writer.write(pdf_bufor)
                    pdf_bufor.seek(0)
                    return pdf_bufor
                except FileNotFoundError:
                    return None
            
            plik_glownego = "KRS.pdf" if typ_klienta == "Spółka (KRS)" else "JDG.pdf"
            
            bufor_glowny = generuj_plik(plik_glownego)
            bufor_pelnomocnictwo = generuj_plik("Pelnomocnictwo.pdf")
            bufor_zalacznik = generuj_plik("Zalacznik.pdf")
            
            st.success("Wygenerowano! Podpisz mnie proszę podpisem kwalifikowanym. Miłego dnia!")
            
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            
            if bufor_glowny:
                with col_btn1:
                    st.download_button("⬇️ Pobierz Oświadczenie", data=bufor_glowny, file_name=f"Oswiadczenie_{bezpieczna_nazwa_firmy}.pdf", mime="application/pdf")
            else:
                st.error(f"Brak pliku {plik_glownego} na serwerze.")
                
            if bufor_pelnomocnictwo:
                with col_btn2:
                    st.download_button("⬇️ Pobierz Pełnomocnictwo", data=bufor_pelnomocnictwo, file_name=f"Pelnomocnictwo_{bezpieczna_nazwa_firmy}.pdf", mime="application/pdf")
                    
            if bufor_zalacznik:
                with col_btn3:
                    st.download_button("⬇️ Pobierz Załącznik", data=bufor_zalacznik, file_name=f"Zalacznik_{bezpieczna_nazwa_firmy}.pdf", mime="application/pdf")