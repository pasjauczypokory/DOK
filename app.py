import streamlit as st
import requests
from datetime import date
import re
import io
from pypdf import PdfWriter
from pypdf.generic import NameObject, NumberObject

def pobierz_dane_z_api(nip):
    dzisiaj = date.today().strftime("%Y-%m-%d")
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
st.set_page_config(page_title="Generator T-Mobile", page_icon="📝")
st.title("🩷 Generator Dokumentów T-Mobile")

# --- SZYBKIE SKRÓTY (LINKI) ---
st.markdown("### 📌 Przydatne linki")
st.markdown("""
[OMNI](https://sso.online.orange.pl/capGui/?url=https://esklep.online.orange.pl/konsola-konsultanta) &nbsp; | &nbsp; 
[Wyszukiwarka JDG](https://www.biznes.gov.pl/pl/wyszukiwarka-firm/) &nbsp; | &nbsp; 
[Wyszukiwarka KRS](https://wyszukiwarka-krs.ms.gov.pl/) &nbsp; | &nbsp; 
[VDI](https://login.t-mobile.pl/) &nbsp; | &nbsp; 
[W jakiej sieci numer?](https://bip.uke.gov.pl/numeracja/dostawca-uslug/) &nbsp; | &nbsp; 
[iLovePDF](https://www.ilovepdf.com/pl)
""")
st.divider() 

# --- RESZTA APLIKACJI ---
st.header("1. Wybierz rodzaj klienta")
typ_klienta = st.radio("Rodzaj podmiotu:", ["Spółka (KRS)", "Jednoosobowa Działalność (JDG)"], horizontal=True)

st.header("2. Dane z bazy")
nip_input = st.text_input("Wpisz NIP (10 cyfr)")

st.header("3. Dane uzupełniające")
col1, col2 = st.columns(2)
with col1:
    imie_input = st.text_input("Imię i nazwisko reprezentanta")
    email_input = st.text_input("Adres e-mail")
with col2:
    tel_input = st.text_input("Telefon komórkowy")
    pesel_input = st.text_input("PESEL")

nr_dowodu_input = ""
if typ_klienta == "Jednoosobowa Działalność (JDG)":
    nr_dowodu_input = st.text_input("Seria i nr Dowodu Osobistego")

if st.button("Generuj PDF", type="primary"):
    nip = nip_input.strip().replace("-", "")
    
    if len(nip) != 10:
        st.warning("Podaj poprawny, 10-cyfrowy NIP!")
    else:
        dane_firmy = pobierz_dane_z_api(nip)
        
        if not dane_firmy:
            st.error("Nie znaleziono firmy o takim NIP w bazie MF.")
        else:
            dzisiaj = date.today()
            plik_szablonu = "KRS.pdf" if typ_klienta == "Spółka (KRS)" else "JDG.pdf"
            dowod_z_napisem = f"Dowód Osobisty {nr_dowodu_input.strip()}" if nr_dowodu_input else ""
            
            dane_do_pdf = {
                "Firma": dane_firmy['nazwa'], 
                "adres": dane_firmy['adres'],
                "NIP": nip,
                "REGON": dane_firmy['regon'],
                "KRS": dane_firmy['krs'],
                "Email": email_input,             
                ".Email": email_input,             
                "Telefon": tel_input,             
                "DO": dowod_z_napisem,                 
                "PESEL": pesel_input,             
                "ImieNazwisko": imie_input,       
                "imie_i_nazwisko_klienta": imie_input, 
                "Miejscowość": "Warszawa",             
                "Haslo": "12345678",                   
                "dzień": dzisiaj.strftime("%d"),
                "miesiac": dzisiaj.strftime("%m"),
                "rok": dzisiaj.strftime("%Y"),
                "id": "",
                "ID": "",
                "TAK": "", 
                "NIE": "" 
            }
            
            try:
                writer = PdfWriter(clone_from=plik_szablonu)
                
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

                surowa_nazwa = dane_firmy['nazwa']
                formy_prawne = r"\b(SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ|SPÓŁKA Z O\.O\.|SP\. Z O\.O\.|SP Z O O|SPÓŁKA Z O O|SPÓŁKA JAWNA|SP\. J\.|SP J|SPÓŁKA AKCYJNA|S\.A\.|SA|SPÓŁKA KOMANDYTOWA|SP\. K\.|SP K|SPÓŁKA KOMANDYTOWO-AKCYJNA|S\.K\.A\.|SKA|SPÓŁKA PARTNERSKA|SP\. P\.|SP P|PROSTA SPÓŁKA AKCYJNA|P\.S\.A\.|PSA)\b"
                krotka_nazwa = re.sub(formy_prawne, "", surowa_nazwa, flags=re.IGNORECASE).strip()
                krotka_nazwa = re.sub(r'[,.-]+$', '', krotka_nazwa).strip()
                bezpieczna_nazwa_firmy = re.sub(r'[\\/*?:"<>|]', "", krotka_nazwa).strip()
                
                nazwa_pliku_wyjsciowego = f"ORK {bezpieczna_nazwa_firmy}.pdf"

                pdf_bufor = io.BytesIO()
                writer.write(pdf_bufor)
                pdf_bufor.seek(0)
                
                st.success("Wygenerowano! Plik jest zgodny z systemem Mac i zablokowany (gotowy dla Szafira).")
                st.download_button("⬇️ Pobierz PDF", data=pdf_bufor, file_name=nazwa_pliku_wyjsciowego, mime="application/pdf")
                
            except FileNotFoundError:
                st.error(f"Na serwerze brakuje pliku: '{plik_szablonu}'.")
            except Exception as e:
                st.error(f"Błąd: {e}")