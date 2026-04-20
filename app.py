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
st.write("Wypełnij dane, aby wygenerować gotowy plik PDF.")

# --- INTELIGENTNY PRZEŁĄCZNIK ---
st.header("1. Wybierz rodzaj klienta")
typ_klienta = st.radio(
    "Rodzaj podmiotu:",
    ["Spółka (KRS)", "Jednoosobowa Działalność (JDG)"],
    horizontal=True
)

st.header("2. Dane z bazy")
nip_input = st.text_input("Wpisz NIP (10 cyfr)")

st.header("3. Dane uzupełniające")
imie_input = st.text_input("Imię i nazwisko reprezentanta")
email_input = st.text_input("Adres e-mail")
tel_input = st.text_input("Telefon komórkowy")
pesel_input = st.text_input("PESEL")

# Pokazuj pole na dowód TYLKO jeśli wybrano JDG
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
            
            if typ_klienta == "Spółka (KRS)":
                plik_szablonu = "KRS.pdf"
                dowod_z_napisem = ""
            else:
                plik_szablonu = "JDG.pdf"
                dowod_z_napisem = f"Dowód Osobisty {nr_dowodu_input.strip()}" if nr_dowodu_input else ""
            
            # --- OSTATECZNE MAPOWANIE (KRS + JDG połączone) ---
            dane_do_pdf = {
                "Firma": dane_firmy['nazwa'],
                "adres": dane_firmy['adres'],
                "NIP": nip,
                "REGON": dane_firmy['regon'],
                "KRS": dane_firmy['krs'],
                
                # Zabezpieczenie obu wariantów E-maila (z kropką dla JDG, bez dla KRS)
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
                
                # Zabezpieczenie małego i dużego ID
                "id": "",
                "ID": "",
                
                # Zabezpieczenie TAK/NIE
                "TAK": "", 
                "NIE": "" 
            }
            
            try:
                writer = PdfWriter(clone_from=plik_szablonu)
                for strona in writer.pages:
                    writer.update_page_form_field_values(strona, dane_do_pdf)
                    
                for page in writer.pages:
                     if "/Annots" in page:
                        for annot in page["/Annots"]:
                            annot_obj = annot.get_object()
                            if annot_obj.get("/Subtype") == "/Widget":
                                annot_obj.update({NameObject("/Ff"): NumberObject(1)})

                # Skracanie nazwy pliku
                surowa_nazwa = dane_firmy['nazwa']
                formy_prawne = r"\b(SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ|SPÓŁKA Z O\.O\.|SP\. Z O\.O\.|SP Z O O|SPÓŁKA Z O O|SPÓŁKA JAWNA|SP\. J\.|SP J|SPÓŁKA AKCYJNA|S\.A\.|SA|SPÓŁKA KOMANDYTOWA|SP\. K\.|SP K|SPÓŁKA KOMANDYTOWO-AKCYJNA|S\.K\.A\.|SKA|SPÓŁKA PARTNERSKA|SP\. P\.|SP P|PROSTA SPÓŁKA AKCYJNA|P\.S\.A\.|PSA)\b"
                krotka_nazwa = re.sub(formy_prawne, "", surowa_nazwa, flags=re.IGNORECASE).strip()
                krotka_nazwa = re.sub(r'[,.-]+$', '', krotka_nazwa).strip()
                bezpieczna_nazwa_firmy = re.sub(r'[\\/*?:"<>|]', "", krotka_nazwa).strip()
                
                nazwa_pliku_wyjsciowego = f"ORK {bezpieczna_nazwa_firmy}.pdf"
                
                # Bufor pamięci
                pdf_bufor = io.BytesIO()
                writer.write(pdf_bufor)
                pdf_bufor.seek(0)
                
                st.success(f"Sukces! Wygenerowano plik dla: {dane_firmy['nazwa']}")
                
                # Przycisk pobierania
                st.download_button(
                    label="⬇️ Pobierz gotową umowę PDF",
                    data=pdf_bufor,
                    file_name=nazwa_pliku_wyjsciowego,
                    mime="application/pdf"
                )
                
            except FileNotFoundError:
                st.error(f"Na serwerze brakuje pliku matrycy: '{plik_szablonu}'! Upewnij się, że wgrałeś go na GitHuba.")
            except Exception as e:
                st.error(f"Błąd generowania PDF: {e}")