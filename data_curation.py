#%%
import pandas as pd

# Učitaj Excel datoteku
df = pd.read_excel("/Users/admin/Documents/GitHub/sample_preparation/_lab_req/equipment.xlsx")

# Očisti DataFrame – ukloni prazne redove i višak NaN vrijednosti
df = df.dropna(how="all").fillna("")

# Pretvori sve stupce u stringove (sigurnije zbog NaN)
df = df.astype(str)

# Ujedini sve stupce u jedan popis [Inv no, naziv opreme, odgovorna osoba]
data = []

# Pronađi sve stupce koji sadrže oznake laboratorija (LG 1, LG 2, LG 3, LG 4, LG 5, GF Ri)
labs = ["LG 1", "LG 2", "LG 3", "LG 4", "LG 5", "GF Ri"]

for lab in labs:
    # pronađi pripadajući stupac s inventarnim brojem i osobom
    inv_col = "Inv no"
    person_col = "Odg osoba"

    for i, row in df.iterrows():
        inv_no = row[inv_col]
        oprema = row.get(lab, "")
        osoba = row.get(person_col, "")

        if oprema.strip():
            data.append([inv_no.strip(), oprema.strip(), osoba.strip()])

# Ispiši kao gotov Python blok
print("data = [")
for row in data:
    print(f'    ["{row[0]}", "{row[1]}", "{row[2]}"],')
print("]")

# %%
