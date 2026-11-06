"""Szybkie, deterministyczne dopasowanie. Procent nie oznacza szansy przyjecia."""

from collections import defaultdict
from datetime import datetime

from app.database import polaczenie
from app.geo import dystans_km, normalizuj, znajdz_miasto
from app.ustawienia import OBSZARY

CECHY = {
    "technologie": {"przedmioty": {"matematyka": 3,"informatyka": 2,"język angielski": 1},"mocne": ["Myślenie analityczne","Rozwiązywanie problemów"],"kwalifikacje": ["INF","EE","E."]},
    "inzynieria": {"przedmioty": {"matematyka": 3,"fizyka": 2,"informatyka": 1},"mocne": ["Myślenie analityczne","Zdolności manualne"],"kwalifikacje": ["ELE","MEC","BUD","EE"]},
    "zdrowie": {"przedmioty": {"biologia": 3,"chemia": 2,"matematyka": 1},"mocne": ["Empatia","Systematyczność"],"kwalifikacje": ["MED"]},
    "przyroda": {"przedmioty": {"biologia": 3,"chemia": 2,"geografia": 1},"mocne": ["Systematyczność","Rozwiązywanie problemów"],"kwalifikacje": ["ROL","LES","OGR"]},
    "nauki_scisle": {"przedmioty": {"matematyka": 3,"fizyka": 2,"chemia": 1},"mocne": ["Myślenie analityczne","Rozwiązywanie problemów"],"kwalifikacje": []},
    "biznes": {"przedmioty": {"matematyka": 2,"język angielski": 2,"geografia": 1},"mocne": ["Komunikacja","Myślenie analityczne"],"kwalifikacje": ["EKA","HAN","SPL"]},
    "prawo": {"przedmioty": {"historia": 2,"wiedza o społeczeństwie": 3,"język polski": 2},"mocne": ["Komunikacja","Systematyczność"],"kwalifikacje": ["EKA"]},
    "spoleczne": {"przedmioty": {"język polski": 2,"biologia": 1,"wiedza o społeczeństwie": 2},"mocne": ["Empatia","Komunikacja"],"kwalifikacje": ["SPO"]},
    "edukacja": {"przedmioty": {"język polski": 2,"język angielski": 1,"biologia": 1},"mocne": ["Empatia","Komunikacja"],"kwalifikacje": ["SPO"]},
    "jezyki": {"przedmioty": {"język polski": 2,"język angielski": 3,"historia": 1},"mocne": ["Języki obce","Komunikacja"],"kwalifikacje": []},
    "sztuka": {"przedmioty": {"historia sztuki": 3,"język polski": 1,"matematyka": 1},"mocne": ["Kreatywność","Zdolności manualne"],"kwalifikacje": ["AUD","PGF"]},
    "uslugi": {"przedmioty": {"geografia": 2,"język angielski": 2,"biologia": 1},"mocne": ["Komunikacja","Systematyczność"],"kwalifikacje": ["HGT","BPO","SPL"]},
}
NAZWY = {
    "technologie": ["informat","computer","sztuczna inteligenc","cyberbez","data science","programow"],
    "prawo": ["prawo","administrac"],
    "spoleczne": ["psycholog","socjolog","dziennikar","stosunki miedzynarod"],
    "edukacja": ["pedagog","edukac","naucz"],
    "zdrowie": ["lekars","medicine","pielegni","polozn","farmac","fizjoter","ratownictwo med","zdrowie","dietety"],
    "biznes": ["zarzadz","ekonom","finans","rachunk","marketing","biznes","logist"],
    "jezyki": ["filolog","lingwist","historia","filozof","literat"],
    "sztuka": ["architektur","wzornict","grafik","design","muzyk","malar","artyst"],
    "przyroda": ["biolog","biotechnolog","weterynar","rolnic","lesnict","ochrona srodow"],
    "nauki_scisle": ["matematy","fizyk","chemi","astronom"],
    "inzynieria": ["mechan","automaty","robot","budown","elektr","mechatron","inzynier","energet"],
    "uslugi": ["turyst","sport","wychowanie fizycz","bezpiecz","hotelar"],
}


def obszar_kierunku(nazwa, isced):
    nazwa = normalizuj(nazwa)
    for obszar, slowa in NAZWY.items():
        if any(slowo in nazwa for slowo in slowa):
            return obszar
    kod = str(isced or "")[:2]
    if kod == "02":
        return "sztuka" if str(isced).startswith("021") else "jezyki"
    return {"01":"edukacja","03":"spoleczne","04":"biznes","05":"nauki_scisle","06":"technologie","07":"inzynieria","08":"przyroda","09":"zdrowie","10":"uslugi"}.get(kod,"uslugi")


def pobierz_oferty():
    with polaczenie() as baza:
        wiersze = baza.execute(
            "SELECT w.id,w.id_kierunku,w.nazwa,w.tryb_studiow,w.jezyk,w.tytul_zawodowy,w.liczba_semestrow,"
            "k.poziom,k.profil,k.kod_isced,k.opis,k.adres_zrodla,k.adres_rekrutacji,k.data_pobrania,"
            "u.id AS id_uczelni,u.nazwa AS uczelnia,u.miasto,u.wojewodztwo,u.rodzaj,u.adres_strony,u.ulica,u.numer_budynku "
            "FROM warianty_studiow w JOIN kierunki_studiow k ON k.id=w.id_kierunku "
            "JOIN uczelnie u ON u.id=k.id_uczelni "
            "WHERE w.kod_statusu='3' AND k.kod_statusu='3' AND k.kod_poziomu IN ('1','2') "
            "ORDER BY w.nazwa,u.nazwa,w.tryb_studiow"
        ).fetchall()
    wynik = []
    for wiersz in wiersze:
        oferta = dict(wiersz)
        miasto = znajdz_miasto(oferta["miasto"] or "",oferta["wojewodztwo"] or "")
        oferta["szerokosc"] = miasto["szerokosc"] if miasto else None
        oferta["dlugosc"] = miasto["dlugosc"] if miasto else None
        oferta["obszar"] = obszar_kierunku(oferta["nazwa"],oferta["kod_isced"])
        wynik.append(oferta)
    return wynik


def ocena_wymagan(oferta, wyniki, kompletne, wymagania):
    reguly = wymagania.get(oferta["id_kierunku"], [])
    if not reguly:
        return "brak_danych", "Brak zweryfikowanych zasad rekrutacji dla wybranego roku."
    grupy = defaultdict(list)
    for regula in reguly:
        grupy[regula["grupa"]].append(regula)
    nieznane = False
    for alternatywy in grupy.values():
        pasuje = False
        brakujace = False
        for warunek in alternatywy:
            wartosci = [x["wynik_procentowy"] for x in wyniki if x["przedmiot"]==warunek["przedmiot"] and x["poziom"]==warunek["poziom"]]
            if wartosci and max(wartosci) >= warunek["minimalny_wynik"]:
                pasuje = True
            if not wartosci:
                brakujace = True
        if not pasuje:
            if kompletne or not brakujace:
                return "niespelnione", "Nie spełniasz zapisanych wymagań przedmiotowych. Sprawdź źródło uczelni."
            nieznane = True
    if nieznane:
        return "do_sprawdzenia", "Uzupełnij maturę, aby sprawdzić zapisane wymagania przedmiotowe."
    return "spelnione", "Spełniasz zapisane wymagania przedmiotowe. Wynik nie gwarantuje przyjęcia."


def policz_dopasowanie(oferty, profil, wyniki, ankieta, kwalifikacje, preferencje, wymagania=None):
    wymagania = wymagania or []
    reguly = defaultdict(list)
    for warunek in wymagania:
        reguly[warunek["id_kierunku"]].append(warunek)
    przedmioty = {}
    for wiersz in wyniki:
        wartosc = float(wiersz["wynik_procentowy"]) * (1 if wiersz["poziom"] in ["rozszerzony","dwujezyczny"] else .7)
        przedmioty[wiersz["przedmiot"]] = max(przedmioty.get(wiersz["przedmiot"] ,0),wartosc)
    zainteresowania = set(ankieta.get("zainteresowania",[]))
    preferowane = set(preferencje.get("preferowane_obszary",[]))
    wykluczone = set(preferencje.get("wykluczone_obszary",[]))
    mocne = set(ankieta.get("mocne_strony",[]))
    slabe = set(ankieta.get("slabe_strony",[]))
    kompletne = bool(profil.get("matura_uzupelniona"))
    wagi = {"zainteresowania": .4,"wyniki": .3,"predyspozycje": .15,"preferencje": .15}
    priorytet = preferencje.get("priorytet")
    if priorytet == "wyniki":
        wagi = {"zainteresowania": .25,"wyniki": .5,"predyspozycje": .1,"preferencje": .15}
    elif priorytet == "odleglosc":
        wagi = {"zainteresowania": .25,"wyniki": .25,"predyspozycje": .1,"preferencje": .4}
    elif priorytet == "zainteresowania":
        wagi = {"zainteresowania": .55,"wyniki": .2,"predyspozycje": .15,"preferencje": .1}
    rezultat = []
    for baza_oferty in oferty:
        oferta = dict(baza_oferty)
        obszar = oferta["obszar"]
        if obszar in wykluczone:
            continue
        cechy = CECHY[obszar]
        powod = []
        zainteresowanie = 100 if obszar in zainteresowania else (20 if zainteresowania else 50)
        if obszar in zainteresowania:
            powod.append("Zgodny z zainteresowaniem: " + OBSZARY[obszar].lower() + ".")
        if preferowane:
            zainteresowanie = .5*zainteresowanie + .5*(100 if obszar in preferowane else 15)
            if obszar in preferowane:
                powod.append("Uwzględnia preferencję podaną w rozmowie.")
        suma, mianownik = 0, sum(cechy["przedmioty"].values())
        for przedmiot, waga in cechy["przedmioty"].items():
            suma += przedmioty.get(przedmiot,0 if kompletne else 40)*waga
        akademickie = suma/mianownik if wyniki or kompletne else 50
        zgodne = [x for x in cechy["przedmioty"] if przedmioty.get(x,0) >= 50]
        if zgodne:
            powod.append("Pomagają wyniki z przedmiotów: " + ", ".join(zgodne[:2]) + ".")
        if cechy["kwalifikacje"] and any(str(k["kod_kwalifikacji"]).upper().startswith(tuple(cechy["kwalifikacje"])) for k in kwalifikacje):
            akademickie = min(100,akademickie+8)
            powod.append("Kwalifikacja zawodowa pasuje do profilu kierunku.")
        predyspozycje = 40 + 60*len(mocne.intersection(cechy["mocne"]))/len(cechy["mocne"]) if mocne else 50
        if obszar in ["technologie","inzynieria","nauki_scisle"] and "Matematyka" in slabe:
            predyspozycje = max(0,predyspozycje-10)
        if mocne.intersection(cechy["mocne"]):
            powod.append("Pasuje do mocnych stron: " + ", ".join(sorted(mocne.intersection(cechy["mocne"]))) + ".")
        dystans = dystans_km(profil.get("szerokosc"),profil.get("dlugosc"),oferta.get("szerokosc"),oferta.get("dlugosc"))
        oferta["dystans_km"] = dystans
        preferencje_oceny = []
        tryb = preferencje.get("preferowany_tryb") or ankieta.get("preferowany_tryb") or profil.get("tryb_studiow")
        jezyk = preferencje.get("preferowany_jezyk") or ankieta.get("preferowany_jezyk")
        for oczekiwane, rzeczywiste in [(tryb,oferta.get("tryb_studiow")),(jezyk,oferta.get("jezyk"))]:
            if oczekiwane and oczekiwane != "Bez preferencji":
                preferencje_oceny.append(100 if oczekiwane==rzeczywiste else 15)
        rodzaj = ankieta.get("rodzaj_uczelni")
        if rodzaj in ["publiczna","niepubliczna"]:
            preferencje_oceny.append(100 if (oferta.get("rodzaj") or "").lower().endswith(" "+rodzaj) else 20)
        regiony = preferencje.get("preferowane_wojewodztwa",[])
        if regiony:
            preferencje_oceny.append(100 if oferta.get("wojewodztwo") in regiony else 15)
        limit = preferencje.get("maksymalny_dystans",profil.get("maksymalny_dystans",300))
        if dystans is not None:
            if ankieta.get("przeprowadzka")=="Nie":
                preferencje_oceny.append(max(0,100*(1-dystans/max(limit,25))))
            else:
                preferencje_oceny.append(max(0,100*(1-max(0,dystans-limit)/max(limit,25))))
            if dystans <= limit:
                powod.append(f"Około {round(dystans)} km od wskazanego miejsca.")
        if ankieta.get("styl_nauki") == "Przez praktykę i projekty":
            preferencje_oceny.append(100 if oferta.get("profil")=="praktyczny" else 60)
        srodowisko = ankieta.get("srodowisko_pracy")
        docelowe = {"Przy komputerze":["technologie","nauki_scisle"],"W kontakcie z ludźmi":["zdrowie","spoleczne","edukacja","biznes"],"W laboratorium":["zdrowie","przyroda","nauki_scisle"],"W terenie":["przyroda","inzynieria","uslugi"],"W pracowni twórczej":["sztuka","jezyki"]}.get(srodowisko)
        if docelowe:
            preferencje_oceny.append(100 if obszar in docelowe else 35)
        motywacja = ankieta.get("motywacja")
        if motywacja in ["Pomaganie innym","Możliwość tworzenia","Rozwój własnej firmy"]:
            preferencje_oceny.append(100 if obszar in {"Pomaganie innym":["zdrowie","edukacja","spoleczne"],"Możliwość tworzenia":["sztuka","technologie","inzynieria"],"Rozwój własnej firmy":["biznes","technologie"]}[motywacja] else 50)
        ocena_preferencji = sum(preferencje_oceny)/len(preferencje_oceny) if preferencje_oceny else 50
        komponenty = {"zainteresowania":round(zainteresowanie,1),"wyniki":round(akademickie,1),"predyspozycje":round(predyspozycje,1),"preferencje":round(ocena_preferencji,1)}
        procent = sum(komponenty[k]*wagi[k] for k in wagi)
        ostrzezenia = []
        medyczny = "lekars" in normalizuj(oferta["nazwa"]) or "medicine" in normalizuj(oferta["nazwa"])
        rozszerzenia = {x["przedmiot"] for x in wyniki if x["poziom"] in ["rozszerzony","dwujezyczny"] and x["wynik_procentowy"] > 0}
        if medyczny and kompletne and not {"biologia","chemia"}.intersection(rozszerzenia):
            procent = min(procent,40)
            ostrzezenia.append("Brak biologii i chemii rozszerzonej w profilu. Dopasowanie obniżone; sprawdź zasady konkretnej uczelni.")
        status, opis = ocena_wymagan(oferta,wyniki,kompletne,reguly)
        if status == "niespelnione":
            procent = 0
            ostrzezenia.append(opis)
        if not wyniki:
            ostrzezenia.append("Brak wyników matury — ocena wstępna.")
        if not ankieta:
            ostrzezenia.append("Uzupełnij ankietę, aby spersonalizować wynik.")
        oferta.update({"dopasowanie":round(max(0,min(100,procent)),1),"rozbicie":komponenty,"wagi":wagi,"powody":powod[:4],"ostrzezenia":ostrzezenia,"status_wymagan":status,"opis_wymagan":opis})
        rezultat.append(oferta)
    return rezultat


def filtruj(oferty, filtry):
    wynik = []
    tekst = normalizuj(filtry.get("szukaj",""))
    for oferta in oferty:
        if tekst and tekst not in normalizuj(oferta["nazwa"]):
            continue
        if any(filtry.get(klucz) and oferta.get(pole) not in filtry[klucz] for klucz,pole in [("wojewodztwa","wojewodztwo"),("uczelnie","uczelnia"),("miasta","miasto"),("obszary","obszar"),("tryby","tryb_studiow"),("jezyki","jezyk"),("poziomy","poziom")]):
            continue
        if filtry.get("rodzaj") and not (oferta.get("rodzaj") or "").lower().endswith(" "+filtry["rodzaj"]):
            continue
        limit = filtry.get("dystans")
        if limit is not None and (oferta.get("dystans_km") is None or oferta["dystans_km"] > limit):
            continue
        if filtry.get("ukryj_niespelnione",True) and oferta.get("status_wymagan")=="niespelnione":
            continue
        wynik.append(oferta)
    sortowanie = filtry.get("sortowanie","Dopasowanie")
    if sortowanie == "Odległość":
        return sorted(wynik,key=lambda x:(x.get("dystans_km") is None,x.get("dystans_km") or 0,-x["dopasowanie"]))
    if sortowanie == "Nazwa kierunku":
        return sorted(wynik,key=lambda x:normalizuj(x["nazwa"]))
    return sorted(wynik,key=lambda x:(-x["dopasowanie"],x.get("dystans_km") if x.get("dystans_km") is not None else 99999,x["nazwa"],x["uczelnia"]))


def top_kierunki(oferty, limit=10):
    wynik, widziane = [], set()
    for oferta in sorted(oferty,key=lambda x:(-x["dopasowanie"],x["nazwa"],x["uczelnia"])):
        klucz = (normalizuj(oferta["nazwa"]),oferta["id_uczelni"],oferta["poziom"])
        if klucz in widziane or oferta["status_wymagan"]=="niespelnione":
            continue
        wynik.append(oferta)
        widziane.add(klucz)
        if len(wynik) >= limit:
            break
    return wynik
