"""Wspolne slowniki formularzy, rankingu i walidacji odpowiedzi modelu."""

OBSZARY = {
    "technologie": "Technologie i programowanie",
    "inzynieria": "Inżynieria i budowanie",
    "zdrowie": "Medycyna i zdrowie",
    "przyroda": "Przyroda i środowisko",
    "nauki_scisle": "Matematyka i nauki ścisłe",
    "biznes": "Biznes i finanse",
    "prawo": "Prawo i administracja",
    "spoleczne": "Psychologia i społeczeństwo",
    "edukacja": "Edukacja i pomaganie",
    "jezyki": "Języki i humanistyka",
    "sztuka": "Sztuka i projektowanie",
    "uslugi": "Turystyka, sport i bezpieczeństwo",
}
MOCNE_STRONY = ["Myślenie analityczne", "Rozwiązywanie problemów", "Komunikacja", "Empatia", "Kreatywność", "Zdolności manualne", "Języki obce", "Systematyczność"]
SLABE_STRONY = ["Matematyka", "Zapamiętywanie dużej ilości materiału", "Wystąpienia publiczne", "Praca pod presją", "Pisanie długich tekstów", "Praca w grupie", "Organizacja czasu"]
PRZEDMIOTY = ["język polski", "matematyka", "język angielski", "język niemiecki", "język francuski", "język hiszpański", "język włoski", "język rosyjski", "biologia", "chemia", "fizyka", "informatyka", "geografia", "historia", "wiedza o społeczeństwie", "historia sztuki", "filozofia"]
POZIOMY = ["podstawowy", "rozszerzony", "dwujezyczny"]
WOJEWODZTWA = ["dolnośląskie", "kujawsko-pomorskie", "lubelskie", "lubuskie", "łódzkie", "małopolskie", "mazowieckie", "opolskie", "podkarpackie", "podlaskie", "pomorskie", "śląskie", "świętokrzyskie", "warmińsko-mazurskie", "wielkopolskie", "zachodniopomorskie"]
TRYBY = ["stacjonarne", "niestacjonarne"]
STRONY = ["Przegląd", "Katalog kierunków", "Mapa uczelni", "Mój profil", "Ankieta", "Ulubione"]
PYTANIA = {
    "zainteresowania": ("Które dziedziny najbardziej Cię interesują?", "obszary"),
    "mocne_strony": ("Co przychodzi Ci z łatwością?", MOCNE_STRONY),
    "slabe_strony": ("Nad czym chcesz jeszcze popracować?", SLABE_STRONY),
    "srodowisko_pracy": ("W jakim środowisku widzisz siebie w przyszłości?", ["Przy komputerze", "W kontakcie z ludźmi", "W laboratorium", "W terenie", "W pracowni twórczej", "Jeszcze nie wiem"]),
    "styl_nauki": ("Jak najchętniej się uczysz?", ["Przez praktykę i projekty", "Przez teorię i analizę", "Łącząc teorię z praktyką"]),
    "motywacja": ("Co jest dla Ciebie najważniejsze przy wyborze studiów?", ["Rozwijanie pasji", "Perspektywy zawodowe", "Pomaganie innym", "Możliwość tworzenia", "Rozwój własnej firmy"]),
    "praca_zespolowa": ("Jak wolisz pracować?", ["Samodzielnie", "W zespole", "To zależy od zadania"]),
    "preferowany_tryb": ("Jaki tryb studiów preferujesz?", ["Bez preferencji", *TRYBY]),
    "preferowany_jezyk": ("W jakim języku chcesz studiować?", ["Bez preferencji", "polski", "angielski"]),
    "rodzaj_uczelni": ("Jaki rodzaj uczelni bierzesz pod uwagę?", ["Bez preferencji", "publiczna", "niepubliczna"]),
    "przeprowadzka": ("Czy rozważasz przeprowadzkę na studia?", ["Tak", "Nie", "Jeszcze nie wiem"]),
    "dodatkowe_informacje": ("Co jeszcze powinniśmy wiedzieć o Twoich planach?", "tekst"),
}
