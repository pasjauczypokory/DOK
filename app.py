# --- ZUPEŁNIE NOWA FUNKCJA GENERUJĄCA Z PYMUPDF ---
            def generuj_plik(szablon):
                try:
                    # 1. Wypełnianie dokumentu w pamięci
                    doc = fitz.open(szablon)
                    for page in doc:
                        widgets = page.widgets()
                        if widgets:
                            for widget in widgets:
                                nazwa_pola = widget.field_name
                                if nazwa_pola in dane_do_pdf:
                                    wartosc = str(dane_do_pdf[nazwa_pola])
                                    if wartosc:
                                        widget.field_value = wartosc
                                        
                                        # --- NAPRAWA UCINANIA TEKSTU ---
                                        # 0 wymusza na bibliotece tryb AUTO:
                                        # dopasowuje czcionkę i wyśrodkowuje tekst w pionie
                                        widget.text_fontsize = 0 
                                        
                                        widget.update() 
                    
                    # 2. TWARDE SPŁASZCZANIE (tworzenie zdjęć z PDF-a)
                    doc_flat = fitz.open()
                    for page in doc:
                        mat = fitz.Matrix(2, 2)
                        pix = page.get_pixmap(matrix=mat)
                        
                        nowa_strona = doc_flat.new_page(width=page.rect.width, height=page.rect.height)
                        nowa_strona.insert_image(page.rect, pixmap=pix)
                    
                    pdf_bufor = io.BytesIO()
                    doc_flat.save(pdf_bufor)
                    
                    doc.close()
                    doc_flat.close()
                    
                    return pdf_bufor.getvalue() 
                except Exception as e:
                    st.error(f"Szczegóły błędu dla pliku {szablon}: {e}")
                    return None