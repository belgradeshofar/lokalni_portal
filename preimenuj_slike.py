import os

# Putanja do baze slika
BASE_DIR = "content/baza_slika"

def preimenuj_slike():
    if not os.path.exists(BASE_DIR):
        print(f"Folder {BASE_DIR} ne postoji!")
        return

    for folder_name in os.listdir(BASE_DIR):
        folder_path = os.path.join(BASE_DIR, folder_name)
        
        if os.path.isdir(folder_path):
            print(f"Obrađujem folder: {folder_name}...")
            
            # Uzimamo samo slike i sortiramo ih po imenu
            slike = [f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            slike.sort()
            
            for index, ime_slike in enumerate(slike, start=1):
                staro_ime = os.path.join(folder_path, ime_slike)
                novo_ime = os.path.join(folder_path, f"{index}.jpg")
                
                # Preskacemo ako se ime vec poklapa da ne bi doslo do greske
                if staro_ime != novo_ime:
                    os.rename(staro_ime, novo_ime)
            
            print(f"  Preimenovano {len(slike)} slika u {folder_name}.")

if __name__ == "__main__":
    preimenuj_slike()