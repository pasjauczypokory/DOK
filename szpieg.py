from pypdf import PdfReader

# Lista plików do przeskanowania
pliki_do_sprawdzenia = ["KRS.pdf", "JDG.pdf", "Pelnomocnictwo.pdf"]

for nazwa_pliku in pliki_do_sprawdzenia:
    print(f"\n{'='*40}")
    print(f"--- ZNALEZIONE POLA W PLIKU: {nazwa_pliku} ---")
    
    try:
        reader = PdfReader(nazwa_pliku)
        pola = reader.get_fields()

        if pola:
            for nazwa in pola.keys():
                print(f"Nazwa pola: '{nazwa}'")
        else:
            print("Nie znaleziono żadnych interaktywnych pól w tym pliku!")
    except FileNotFoundError:
        print(f"Brak pliku! Upewnij się, że '{nazwa_pliku}' leży w tym samym folderze co skrypt.")
    except Exception as e:
        print(f"Błąd podczas czytania pliku {nazwa_pliku}: {e}")

print(f"\n{'='*40}\nSkanowanie zakończone!")