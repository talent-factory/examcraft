# Dokument-Metadaten

**Titel:** Praktische Algorithmik mit Python

**Autor:** Häberlein, Tobias

**Erstellt mit:** TeX

**Anzahl Seiten:** 346


---


## Seite 4

Oldenbourg Verlag München
Praktische Algorithmik 
mit Python
von
Tobias Häberlein

## Seite 5

Tobias Häberlein ist seit 2006 Professor an der Hochschule Albstadt-Sigmaringen im 
Studiengang Kommunikations- und Softwaretechnik.
Bibliografische Information der Deutschen Nationalbibliothek
Die Deutsche Nationalbibliothek verzeichnet diese Publikation in der Deutschen 
Nationalbibliografie; detaillierte bibliografische Daten sind im Internet über
http://dnb.d-nb.de abrufbar.
© 2012  Oldenbourg Wissenschaftsverlag GmbH
Rosenheimer Straße 145, D-81671 München
Telefon: (089) 45051-0
www.oldenbourg-verlag.de
Das Werk einschließlich aller Abbildungen ist urheberrechtlich geschützt. Jede Verwertung 
außerhalb der Grenzen des Urheberrechtsgesetzes ist ohne Zustimmung des Verlages unzulässig 
und strafbar. Das gilt insbesondere für Vervielfältigungen, Übersetzungen, Mikroverfilmungen 
und die Einspeicherung und Bearbeitung in elektronischen Systemen.
Lektorat: Dr. Gerhard Pappert
Herstellung: Constanze Müller
Titelbild: thinkstockphotos.de
Einbandgestaltung: hauser lacour
Gesamtherstellung: Grafik & Druck GmbH, München
Dieses Papier ist alterungsbeständig nach DIN/ISO 9706.
ISBN     978-3-486-71390-9
eISBN   978-3-486-71444-9 

## Seite 6

Vorwort
Pseudocode vs. Python
Man kann die Algorithmik sowohl der Theoretischen Informatik als auch der Prakti-
schen Informatik zuordnen, je nachdem auf welchen Aspekten der Algorithmik man
den Schwerpunkt legen m ¨ochte. Eine theoretische Betrachtung der Algorithmik, die
viele Ber ¨uhrungspunkte zur Komplexit ¨atstherie besitzt, hat dabei durchaus ihre Be-
rechtigung. Das vorliegende Buch w¨ahlt jedoch eine praktischere Betrachtung der Algo-
rithmik, die mehr Ber ¨uhrungspunkte zur Programmiermethodik und zu Programmier-
techniken aufweist.
Viele (nicht alle!) B ¨ucher pr¨asentieren Algorithmen in Pseudocode – wohl vor allem
aus didaktischen Gr ¨unden: Pseudocode ist kompakter, abstrahiert l ¨astige Details (wie
die Realisierung von Datenstrukturen, die konkrete Ausgestaltung von Schleifen, usw.)
und erm¨oglicht es dem Leser, sich auf das Wesentliche, n¨amlich die Funktionsweise des
entsprechenden Algorithmus, zu konzentrieren. Pseudocode ist jedoch nicht ausf¨uhrbar;
das erh¨oht die Barriere des Lesers, die Algorithmen ”auszuprobieren“ und mit ihnen zu
”spielen“.
Dieses Buch verwendet statt Pseudocode Python, eine ausf¨uhrbare Programmierspra-
che, zur Beschreibung der Algorithmen. Python hat auch im Vergleich zu anderen Pro-
grammiersprachen einige didaktische Vorz¨uge:
 Python besitzt eine kompakte, einfach zu erlernende Syntax. Wir werden sehen:
Die Beschreibung der Algorithmen mit Python ist in den meisten F ¨allen weder
l¨anger noch schwerer verst¨andlich als eine Pseudocode-Beschreibung.
 Python besitzt eine interaktive ”Shell“, die es dem Leser erlaubt, die Algorith-
men interaktiv auszuprobieren. Dies befriedigt nicht nur den vielen Informatikern
eigenen ”Spieltrieb“, sondern ist auch ein didaktisch wertvolles Mittel, die Funk-
tionsweise der Algorithmen zu verstehen.
 Python l¨asst dem Programmierer die Wahl, objekt-orientiert, funktional oder klas-
sisch prozedural zu programmieren. Besonders funktionale Programmierkonstruk-
te wie Listenkomprehensionen oder Funktionen h ¨ohrerer Ordnung wie map oder
reduce erm¨oglichen in vielen F ¨allen eine sehr kompakte und verst ¨andliche Be-
schreibung von Algorithmen.
Algorithmen verstehen durch Ausprobieren
Neben dem im Buch vermittelten formalen Zugang zum Verst ¨andnis der Algorithmen
und Datenstrukturen bietet sich durch die beschriebenen Implementierungen in Python
auch ein spielerischer Zugang. So kann man sich beispielsweise dieFIRST- und FOLLOW-
Mengen von Grammatik-Variablen erzeugen lassen, die Laufzeit von Fibonacci-Heaps
mit Pairing-Heaps vergleichen, die Laufzeit einer Skip-Liste mit der Laufzeit eines AVL-

## Seite 7

VI
Baums vergleichen, sich große Rot-Schwarz-B ¨aume erzeugen und anzeigen lassen oder
sich eine ”gute“ L¨osung des Travelling-Salesman-Problems mit Ameisenalgorithmen er-
zeugen.
Objekt-orientierte Programmierung
Tats¨achlich vermeide ich in einigen F¨allen objekt-orientierte Programmiertechniken, die
manch Einer wom ¨oglich als sinnvoll empfunden h ¨atte, insbesondere die Konstruktion
einer Vererbungshierarchie f ¨ur B ¨aume und Suchb ¨aume. Objekt-orientierte Program-
mierung mag geeignet sein, Konzepte der realen Welt auf Datenstrukturen im Rechner
abzubilden. Sie ist jedoch weniger geeignet, ¨uberwiegend algorithmische Probleme an-
zugehen. OO-Programmierer verbringen erfahrungsgem ¨aß einen großen Teil ihrer Zeit
damit, die passende Klassenhierarchie und die passenden Interfaces zu entwerfen und
eher weniger Zeit damit, sich mit der algorithmischen Seite eines Problems zu befassen.
Umfang
Dieses Buch ist als eine Einf¨uhrung in die Algorithmik gedacht und kann (und will) nicht
alle Teilbereiche der Algorithmik abdecken. W¨ahrend es die wichtigsten (teils auch sehr
modernen) Sortier-, Such-, Graphen- und Sprach-/String-Algorithmen abdeckt und ein
ganzes Kapitel der in der Praxis h¨auﬁg ben¨otigten Verwendung von Heuristiken widmet,
deckt es die folgenden Algorithmenklassen nicht ab:
 Numerische Algorithmen: Fast-Fourier-Transformation, schnelle Matrixmultipli-
kation, Kryptographische Algorithmen, usw.
 Spiel- und KI-Algorithmen: Alpha-Beta-Pruning und optimierte Suche in zu kon-
struierenden B¨aumen
 Lineare Programmierung und lineare Optimierungsverfahren: Der Simplexalgo-
rithmus, die Ellipsoidmethode, usw.
 Randomisierte Algorithmen: Las-Vegas-Algorithmen, Monte-Carlo-Algorithmen,
usw.
 Parallele Algorithmen
Weitere Informationen
L¨osungen zu vielen der im Buch enthaltenen Aufgaben, den Code der pr ¨asentierten
Algorithmen, Foliens¨atze, Errata, usw. ﬁnden Sie auf meiner Homepage
www.tobiashaeberlein.net
Dank
Herzlichen Dank an alle, die die Entstehung dieses Buches erm ¨oglicht haben, insbeson-
dere an meine Familie (die mir den notwendigen Freiraum zugestanden hat) und meinen
Vater, Karl-Heinz H¨aberlein (f¨ur das m¨uhsame Korrekturlesen).
Ich w¨unsche allen Lesern viel Spaß bei der Lekt ¨ure und vor allem beim Ausprobieren
der Algorithmen.
Tobias H¨aberlein
Vorwort

## Seite 8

F¨ur Mona, Carlo und Matilda

## Seite 10

Inhaltsverzeichnis
1 Algorithmen-Grundlagen und Algorithmen-Implementierung 1
1.1 Laufzeitanalyse von Algorithmen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 1
1.1.1 Landau-Symbole . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 1
1.1.2 Worst-Case, Average-Case und amortisierte Laufzeit . . . . . . . . . . . . . . . . . . . 4
1.1.3 Praktisch l ¨osbar vs. exponentielle Laufzeit . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 4
1.2 Implementierung von Algorithmen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 6
1.2.1 Rekursive vs. iterative Implementierung. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 6
1.2.2 Warum Rekursion (statt Iteration)?. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 12
1.2.3 ”Kochrezept“ f¨ur das Entwickeln eines rekursiven Algorithmus . . . . . . . . . 12
1.3 Nicht-destruktive vs. In-place Implementierung . . . . . . . . . . . . . . . . . . . . . . . . 13
1.3.1 Warum nicht-destruktive Implementierungen? . . . . . . . . . . . . . . . . . . . . . . . . . . 14
1.4 Repr ¨asentation von Datenstrukturen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 14
1.4.1 Repr ¨asentation als Klasse . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 15
1.4.2 Repr ¨asentation als Liste . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 15
1.4.3 Repr ¨asentation als Dictionary . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 15
2 Sortieralgorithmen 17
2.1 Insertion Sort . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 17
2.1.1 Implementierung: nicht-destruktiv . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 17
2.1.2 In-place Implementierung . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 19
2.1.3 Laufzeit . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 19
2.2 Mindestlaufzeit von Sortieralgorithmen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 21
2.3 Quicksort . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 22
2.3.1 Divide-And-Conquer-Algorithmen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 22
2.3.2 Funktionsweise von Quicksort. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 23
2.3.3 Laufzeit . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 26
2.3.4 In-Place-Implementierung . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 27
2.3.5 Eliminierung der Rekursion . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 30
2.4 Mergesort . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 33
2.5 Heapsort und Priority Search Queues . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 34
2.5.1 Repr ¨asentation von Heaps . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 34
2.5.2 Heaps als Priority Search Queues . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 35
2.5.3 Konstruktion eines Heaps. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 39
2.5.4 Heapsort . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 43

## Seite 11

X Inhaltsverzeichnis
3 Suchalgorithmen 47
3.1 Bin ¨are Suchb¨aume. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 49
3.1.1 Repr ¨asentation eines bin¨aren Suchbaums . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 50
3.1.2 Suchen, Einf ¨ugen, L¨oschen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 51
3.1.3 Laufzeit . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 56
3.2 AVL-B ¨aume . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 57
3.2.1 Einf ¨ugeoperation . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 58
3.2.2 Grundlegende Balancierungsoperationen: Rotationen . . . . . . . . . . . . . . . . . . . 59
3.3 Rot-Schwarz-B ¨aume . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 63
3.3.1 Einf ¨ugen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 64
3.3.2 L ¨oschen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 69
3.4 Hashing . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 72
3.4.1 Hash-Funktionen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 73
3.4.2 Kollisionsbehandlung . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 77
3.4.3 Implementierung in Python . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 79
3.5 Bloomﬁlter . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 85
3.5.1 Grundlegende Funktionsweise . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 85
3.5.2 Implementierung . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 87
3.5.3 Laufzeit und Wahrscheinlichkeit falsch-positiver Antworten . . . . . . . . . . . . . 89
3.5.4 Anwendungen von Bloomﬁltern . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 91
3.6 Skip-Listen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 93
3.6.1 Implementierung . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 94
3.6.2 Laufzeit . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 98
3.7 Tries . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 100
3.7.1 Die Datenstruktur . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 100
3.7.2 Suche . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 102
3.7.3 Einf ¨ugen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 103
3.8 Patricia-Tries. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 104
3.8.1 Datenstruktur . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 104
3.8.2 Suche . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 105
3.8.3 Einf ¨ugen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 106
3.9 Suchmaschinen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 108
3.9.1 Aufbau einer Suchmaschine . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 108
3.9.2 Invertierter Index. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 109
3.9.3 Implementierung . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 109
3.9.4 Erweiterte Anforderungen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 111
4 Heaps 115
4.1 Bin ¨are Heaps . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 116
4.1.1 Repr ¨asentation bin¨arer Heaps. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 116
4.1.2 Einf ¨ugen eines Elements . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 117
4.1.3 Minimumsextraktion . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 117
4.1.4 Erh ¨ohen eines Schl¨usselwertes . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 118

## Seite 12

Inhaltsverzeichnis XI
4.2 Binomial-Heaps . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 119
4.2.1 Binomial-B ¨aume . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 120
4.2.2 Repr ¨asentation von Binomial-B¨aumen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 120
4.2.3 Struktur von Binomial-Heaps . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 121
4.2.4 Repr ¨asentation von Binomial-Heaps . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 122
4.2.5 Verschmelzung zweier Binomial-B ¨aume . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 122
4.2.6 Vereinigung zweier Binomial-Heaps . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 123
4.2.7 Einf ¨ugen eines Elements . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 126
4.2.8 Extraktion des Minimums . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 126
4.3 Fibonacci Heaps . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 127
4.3.1 Struktur eines Fibonacci-Heaps . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 128
4.3.2 Repr ¨asentation in Python . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 129
4.3.3 Amortisierte Laufzeit und Potenzialfunktion . . . . . . . . . . . . . . . . . . . . . . . . . . . 131
4.3.4 Verschmelzung . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 131
4.3.5 Einf ¨ugen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 132
4.3.6 Extraktion des Minimums . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 133
4.3.7 Erniedrigen eines Schl ¨usselwertes . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 136
4.3.8 Maximale Ordnung eines Fibonacci-Baums. . . . . . . . . . . . . . . . . . . . . . . . . . . . . 141
4.4 Pairing-Heaps . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 142
4.4.1 Struktur und Repr ¨asentation in Python . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 142
4.4.2 Einfache Operationen auf Pairing-Heaps . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 143
4.4.3 Extraktion des Minimums . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 144
5 Graphalgorithmen 147
5.1 Grundlegendes . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 147
5.1.1 Wozu Graphen? . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 147
5.1.2 Repr ¨asentation von Graphen. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 149
5.2 Breiten- und Tiefensuche . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 152
5.2.1 Breitensuche . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 152
5.2.2 Tiefensuche . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 154
5.2.3 Topologische Sortierung . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 159
5.3 K ¨urzeste Wege . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 161
5.3.1 Der Dijkstra-Algorithmus . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 162
5.3.2 Der Warshall-Algorithmus . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 165
5.4 Minimaler Spannbaum. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 169
5.4.1 Problemstellung . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 169
5.4.2 Der Algorithmus von Kruskal . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 170
5.4.3 Union-Find-Operationen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 174
5.5 Maximaler Fluss in einem Netzwerk. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 178
5.5.1 Netzwerke und Fl ¨usse . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 178
5.5.2 Der Algorithmus von Ford-Fulkerson . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 179
5.5.3 Korrektheit des Ford-Fulkerson-Algorithmus . . . . . . . . . . . . . . . . . . . . . . . . . . . 182

## Seite 13

XII Inhaltsverzeichnis
6 Formale Sprachen und Parser 185
6.1 Formale Sprachen und Grammatiken. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 185
6.1.1 Formales Alphabet, formale Sprache . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 185
6.1.2 Grammatik, Ableitung, akzeptierte Sprache, Syntaxbaum . . . . . . . . . . . . . . 186
6.2 Repr ¨asentation einer Grammatik in Python . . . . . . . . . . . . . . . . . . . . . . . . . . . . 190
6.2.1 Berechnung der FIRST-Mengen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 192
6.2.2 Berechnung der FOLLOW-Mengen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 195
6.3 Recursive-Descent-Parser . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 197
6.3.1 Top-Down-Parsing. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 197
6.3.2 Pr ¨adiktives Parsen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 198
6.3.3 Implementierung eines Recursive-Descent-Parsers . . . . . . . . . . . . . . . . . . . . . . 199
6.3.4 Vorsicht: Linksrekursion . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 201
6.4 Ein LR-Parsergenerator . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 202
6.4.1 LR(0)-Elemente . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 203
6.4.2 Die H ¨ullenoperation . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 203
6.4.3 Die GOTO-Operation . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 204
6.4.4 Erzeugung des Pr ¨aﬁx-Automaten . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 205
6.4.5 Berechnung der Syntaxanalysetabelle . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 208
6.4.6 Der Kellerautomat . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 210
7 Stringmatching 213
7.1 Primitiver Algorithmus . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 213
7.2 Stringmatching mit endlichen Automaten . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 214
7.3 Der Knuth-Morris-Pratt-Algorithmus . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 216
7.3.1 Suche mit Hilfe der Verschiebetabelle . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 217
7.3.2 Laufzeit . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 219
7.3.3 Berechnung der Verschiebetabelle . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 220
7.4 Der Boyer-Moore-Algorithmus . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 221
7.4.1 Die Bad-Character-Heuristik. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 221
7.4.2 Die Good-Suﬃx-Heuristik . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 224
7.4.3 Implementierung . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 227
7.4.4 Laufzeit . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 228
7.5 Der Rabin-Karp-Algorithmus . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 228
7.5.1 Rollender Hash . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 229
7.5.2 Implementierung . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 231
7.6 Der Shift-Or-Algorithmus. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 232
7.6.1 Implementierung . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 234
8 Schwere Probleme und Heuristiken 237
8.1 Das Travelling-Salesman-Problem . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 237
8.1.1 L ¨osung durch Ausprobieren . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 237

## Seite 14

Inhaltsverzeichnis XIII
8.1.2 L ¨osung durch Dynamische Programmierung . . . . . . . . . . . . . . . . . . . . . . . . . . . . 238
8.1.3 Laufzeit . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 240
8.2 Heuristiken f ¨ur das Travelling-Salesman-Problem . . . . . . . . . . . . . . . . . . . . . . . 241
8.3 Greedy-Heuristiken . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 241
8.3.1 Nearest-Neighbor-Heuristik . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 241
8.3.2 Nearest-, Farthest-, Random-Insertion . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 242
8.3.3 Tourverschmelzung . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 244
8.4 Lokale Verbesserung . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 246
8.4.1 Die 2-Opt-Heuristik . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 247
8.4.2 Die 2.5-Opt-Heuristik. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 248
8.4.3 Die 3-Opt- und k-Opt-Heuristik . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 250
8.5 Ein Genetischer Algorithmus . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 255
8.5.1 Knoten-Cross-Over . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 255
8.5.2 Kanten-Cross-Over . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 255
8.5.3 Die Realisierung des genetischen Algorithmus . . . . . . . . . . . . . . . . . . . . . . . . . . 257
8.6 Ein Ameisen-Algorithmus. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 258
8.6.1 Erster Ansatz . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 260
8.6.2 Verbesserte Umsetzung . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 263
A Python Grundlagen 267
A.1 Die Pythonshell . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 267
A.2 Einfache Datentypen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 267
A.2.1 Zahlen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 267
A.2.2 Strings . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 268
A.2.3 Variablen. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 268
A.2.4 Typisierung . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 268
A.2.5 Operatoren . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 269
A.3 Grundlegende Konzepte . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 270
A.3.1 Kontrollﬂuss . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 270
A.3.2 Schleifenabbruch . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 272
A.3.3 Anweisungen vs. Ausdr ¨ucke. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 273
A.3.4 Funktionen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 274
A.3.5 Referenzen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 276
A.4 Zusammengesetzte Datentypen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 277
A.4.1 Listen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 277
A.4.2 Sequenzen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 279
A.4.3 Tupel . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 282
A.4.4 Dictionaries . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 283
A.4.5 Strings (Fortsetzung) . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 285
A.4.6 Mengen: Der set-Typ . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 286
A.5 Funktionale Programmierung . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 287
A.5.1 Listenkomprehensionen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 288

## Seite 15

XIV Inhaltsverzeichnis
A.5.2 Lambda-Ausdr ¨ucke . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 290
A.5.3 Die map-Funktion . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 291
A.5.4 Die all - und die any-Funktion . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 292
A.5.5 Die enumerate-Funktion . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 292
A.5.6 Die reduce-Funktion . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 293
A.6 Vergleichen und Sortieren. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 295
A.6.1 Vergleichen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 295
A.6.2 Sortieren . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 296
A.7 Objektorientierte Programmierung . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 298
A.7.1 Spezielle Methoden . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 301
B Mathematische Grundlagen 303
B.1 Mengen, Tupel, Relationen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 303
B.1.1 Mengen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 303
B.1.2 Tupel . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 303
B.1.3 Relationen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 304
B.1.4 Vollst ¨andige Induktion. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 306
B.1.5 Summenformel . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 306
B.2 Fibonacci-Zahlen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 307
B.3 Grundlagen der Stochastik. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 309
B.3.1 Wahrscheinlichkeitsraum . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 309
B.3.2 Laplacesches Prinzip . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 310
B.3.3 Zufallsvariablen und Erwartungswert . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 311
B.3.4 Wichtige Verteilungen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 312
B.4 Graphen, B ¨aume und Netzwerke . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 314
B.4.1 Graphen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 314
B.5 Potenzmengen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 316
B.5.1 Permutationen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 317
B.5.2 Teilmengen und Binomialkoeﬃzient . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 319
Literaturverzeichnis 321
Index 323

## Seite 16

1 Algorithmen-Grundlagen und
Algorithmen-Implementierung
Wir skizzieren in diesem Abschnitt die Grundlagen der Laufzeitanalyse von Algorith-
men und gehen insbesondere der Frage nach, warum man den Formalismus der Groß-
Oh-Notation ben¨otigt, um die Laufzeit eines Algorithmus sinnvoll angeben zu k ¨onnen.
Wir erkl¨aren, was man unter praktisch l ¨osbaren Problemen versteht und skizzieren die
Eigenschaft der NP-Vollst¨andigkeit und einige wichtige NP-vollst¨andige Probleme.
Dieses Buch legt einen besonderen Augenmerk auf die Implementierung der Algorith-
men. Es gibt meistens mehrere M ¨oglichkeiten einen Algorithmus zu implementieren,
bzw. eine Datenstruktur zu repr ¨asentieren. Wir besprechen in diesem Abschnitt die
folgenden Implementierungsdimensionen:
 Iterative vs. rekursive Implementierung eines Algorithmus.
 Destruktive vs. nicht-destruktive Implementierung eines Algorithmus.
 Verwendung einer Klasse vs. Verwendung einer Liste, eines Tupel oder einer Hash-
tabelle zur Repr¨asentation einer Datenstruktur.
1.1 Laufzeitanalyse von Algorithmen
In der Informatik hat es sich seit Mitte der 60er Jahre eingeb ¨urgert, die sog. Landau-
Symbole zur Beschreibung der Laufzeit von Algorithmen zu verwenden.
1.1.1 Landau-Symbole
Die n¨utzlichste Methode, die Laufzeit von Algorithmen zu beschreiben, verwendet die
sog. Landau-Symbole, insbesondere die sog. ”Groß-Oh-Notation“, geschrieben O(...).
Nehmen wir an, ein Algorithmus wird auf einen Datensatz einer bestimmten Gr ¨oße n
angewendet, so sind wir zwar an der prinzipiellen Laufzeit dieses Algorithmus interes-
siert; wir wollen jedoch bei der grunds ¨atzlichen Analyse von Algorithmen die Laufzeit
auch so abstrakt angeben, dass sie . . .
. . . unabh ¨angig von dem konkreten Computer ist, auf dem der Algorithmus abl ¨auft.
. . . unabh ¨angig von dem konkreten Compiler ist, der den im Allgemeinen in Hoch-
sprache programmierten Algorithmus in vom Computer ausf ¨uhrbare Maschinen-
sprache ¨ubersetzt.

## Seite 17

2 1 Algorithmen-Grundlagen und Algorithmen-Implementierung
Nur wenn wir in der Lage sind, diese technologischen Details auszuklammern, k ¨onnen
wir von einer eigenst ¨andigen Disziplin ”Algorithmik“ ¨uberhaupt erst sprechen und
k¨onnen Algorithmen technologieunabh¨angig analysieren.
Die Laufzeit eines Algorithmus geben wir immer in Abh¨angigkeit von der ”Gr¨oße“ (was
auch immer Gr ¨oße im konkreten Fall bedeutet) der Eingabedaten an – oft auch als
Problemgr¨oße bezeichnet. Beim Sortieren einer aus n Eintr¨agen bestehenden Liste ist
beispielsweise die Problemgr ¨oße gleich n. Mit Hilfe der sog. ”Groß-Oh-Notation“ kann
man technologieunabh ¨angig die Laufzeit eines Algorithmus in Abh ¨angigkeit von der
Problemgr¨oße angeben. Behaupten wir beispielsweise unter Verwendung der Groß-Oh-
Notation, ein bestimmter Sortieralgorithmus habe eine Laufzeit von O(n2), so bedeutet
das eine Laufzeit, die (h ¨ochstens) quadratisch mit der Gr ¨oße der Eingabe – in diesem
Fall die L ¨ange der zu sortierenden Liste – zunimmt. Ausgeklammert wird dabei die
Frage, ob die Laufzeit bei einer Eingabegr ¨oße n etwa 2 ·n2 oder 4 ·n2 ist; aber ein
solches ”Detail“ (wie ein konstanter Multiplikationsfaktor) h ¨angt ja in der Tat von
der Leistungsf¨ahigkeit des ausf¨uhrenden Rechners ab, interessiert uns also – zumindest
wenn wir uns im Fachgebiet ”Algorithmik“ bewegen – weniger.
Die formale Deﬁnition zeigt, dass die Groß-Oh-Notation eigentlich eine (mathematische)
Menge von Funktionen beschreibt. Es gilt:
O(g(n)) := {f(n) |es gibt C ≥0 und n0 ∈N so dass f¨ur alle n≥n0 gilt:
|f(n)|≤ C·|g(n)|}
Ω(g(n) := {f(n) |es gibt C ≥0 und n0 ∈N so dass f¨ur alle n≥n0 gilt:
|f(n)|≥ C·|g(n)|}
Θ(g(n)) := O(g(n)) ∩ Ω(g(n)) .
Mit der Konstanten C bringt man mathematisch zum Ausdruck, dass Konstanten keine
Rolle spielen; bei der Frage, ob sich eine Funktion in O(g(n)) beﬁndet ist nur das
ungef¨ahre Wachstum entscheidend. Ist etwa g(n) = n3, so ist die Intention der Groß-
Oh-Notation, dass jede kubische Funktion inO(n3) ist, etwa auchf(n) = 9n3; in diesem
Falle m¨usste man C ≥9 w¨ahlen. Indem man verlangt, dass die gew ¨unschte Eigenschaft
nur von Funktionswerten ab einer bestimmten Gr¨oße (n≥n0) erf¨ullt wird, bringt man
zum Ausdruck, dass man nur an dem asymptotischen Wachstumsverhalten interessiert
ist, d. h. dem Wachstumsverhalten f ¨ur ”große“ Funktionswerte – durch Wahl von n0
kann man selbst bestimmten, was ”groß“ ist. F ¨ur die konstante Funktion f(x) = 5
w¨are beispielsweise f(x) ∈O(ln(x)), was sich durch Wahl von n0 = ⌈e5⌉= 149 leicht
best¨atigen l¨asst.
Es hat sich eingeb ¨urgert, statt f(n) ∈O(g(n)) einfach f(n) = O(g(n)) zu schreiben.
Man sollte jedoch nicht vergessen, dass das hier verwendete Symbol ”=“ eigentlich ein
”∈“ darstellt und daher auch nicht kommutativ ist.

## Seite 18

1.1 Laufzeitanalyse von Algorithmen 3
Aufgabe 1.1
Geben Sie konkrete Werte der Konstanten C und n0 an, die zeigen, dass gilt:
(a) 3n2 + 10 ∈O(n2)
(b) 3n2 + n+ 1 ∈O(n2)
Aufgabe 1.2
Entscheiden Sie die G ¨ultigkeit der folgenden Aussagen (nicht notwendigerweise for-
mal; sie d¨urfen auch intuitiv argumentieren):
(a) n100 = O(1.01n)
(b) 10 log n = O(2n)
(c) 10
√n = O(2n)
(d) 10 n = O(2n)
W¨ahrend Konstanten tats¨achlich oft technologische Besonderheiten widerspiegeln (mo-
derne Rechner sind etwa 10 bis 100 mal schneller als die Rechner vor 10 Jahren), so
spiegeln die durch die Groß-Oh-Notation ausgedr¨uckten Laufzeiten eher prinzipielle Ei-
genschaften der zugrunde liegenden Algorithmen wider. Beispielsweise w ¨urde der mo-
dernste und schnellste Rechner mit einem schlecht implementierten Sortieralgorithmus
(Laufzeit O(n2)) um Gr ¨oßenordnungen langsamer sortieren als ein sehr alter langsa-
mer Rechner, der einen schnellen Sortieralgorithmus (Laufzeit O(nlog(n))) verwendet
– wenn die L¨ange der zu sortierenden Liste nur lang genug ist.
Aufgabe 1.3
Wir lassen einen schnellen Rechner A(100 Millionen Instruktionen pro Sekunde) mit
einem langsamen Sortieralgorithmus (Laufzeit O(n2)) gegen einen sehr langsamen
Rechner B (100000 Instruktionen pro Sekunde) mit einem schnellen Sortieralgorith-
mus (Laufzeit O(nlog(n)) gegeneinander antreten.
F¨ullen Sie die folgende Tabelle mit den ungef ¨ahren Laufzeiten.
L¨ange der Liste
100000 1 Mio 10 Mio 100 Mio 1 Mrd
Rechner A
Rechner B

## Seite 19

4 1 Algorithmen-Grundlagen und Algorithmen-Implementierung
1.1.2 Worst-Case, Average-Case und amortisierte Laufzeit
In der Laufzeitanalyse von Algorithmen unterscheidet man h ¨auﬁg zwischen . . .
 Worst-Case-Laufzeit: Dies ist die Laufzeit, die der Algorithmus im schlechtest
denkbaren Fall brauchen w¨urde. Auch dann, wenn dieser ”schlechteste“ Fall sehr
unwahrscheinlich ist bzw. sehr selten auftritt, mag eine sehr ung ¨unstige Worst-
Case-Laufzeit – wenn man Wert auf konstantes, vorhersagbares Verhalten legt –
kritisch sein.
 Average-Case-Laufzeit: Dies ist die Laufzeit, die der Algorithmus im Mittel ben¨otigt,
mathematisch modelliert durch den Erwartungswert der Laufzeit. Bei der Berech-
nung dieses Erwartungswerts wird die Laufzeit aller Situationen nach der Wahr-
scheinlichkeit gewichtet, mit der die entsprechende Situation eintritt; die Laufzeit
unwahrscheinlicher Konstallationen f¨allt entsprechend weniger ins Gewicht als die
Laufzeit wahrscheinlicher Konstellationen.
H¨auﬁg interessiert man sich f ¨ur die Average-Case-Laufzeit eines Algorithmus.
 Amortisierte Laufzeit : Bei dieser Art der Laufzeitanalyse betrachtet man Folgen
von Operationen auf einer Datenstruktur; die Laufzeit einer Rechenzeit-aufw¨andi-
gen Operation kann hierbei durch die Laufzeit von weniger aufw¨andigen Funktio-
nen ausgeglichen werden. Es gibt mehrere Methoden eine amortisierte Laufzeit-
analyse durchzuf ¨uhren; f ¨ur die Laufzeitanalyse von Fibonacci-Heaps (siehe Ab-
schnitt 4.3 verwenden wir etwa die sog. Potentialmethode.
1.1.3 Praktisch l ¨osbar vs. exponentielle Laufzeit
Wir wollen Probleme, f ¨ur die es einen Algorithmus mit Laufzeit O(np) mit p ∈ N
gibt, als praktisch l ¨osbar bezeichnen; manchmal werden sie lax auch als polynomiell
bezeichnet, da ihre Laufzeit begrenzt ist durch ein Polynom in der Eingabegr ¨oße. Ge-
naugenommen w¨are jedoch ein Algorithmus mit Laufzeit von beispielsweise O(n100) f¨ur
große Werte von n eigentlich nicht wirklich ”praktisch“, denn schon f ¨ur eine Eingabe-
gr¨oße n = 10 w ¨are die Laufzeit f ¨ur die L ¨osung eines solchen Problems astronomisch
groß. Zwar kann man sich theoretisch f ¨ur jedes gegebene p∈N ein Problem konstruie-
ren, f¨ur dessen L¨osung ein Algorithmus mit Laufzeit O(np) n¨otig ist, f¨ur alle praktisch
relevanten Probleme ist, sofern sie polynomiell sind, jedoch p ≤4; insofern macht es
tats¨achlich Sinn polynomielle Probleme als ”praktisch l¨osbar“ zu bezeichnen.
In der Komplexit¨atstheorie wird die Menge aller Probleme, zu deren L¨osung ein polyno-
mieller Algorithmus existiert, als P bezeichnet. P ist ein Beispiel f¨ur eine Komplexit¨ats-
klasse. Probleme, f ¨ur die nur Algorithmen bekannt sind, deren Laufzeit exponentiell
mit der Gr¨oße der Eingabe steigt, m¨ogen zwar theoretisch nicht jedoch praktisch l¨osbar
sein.

## Seite 20

1.1 Laufzeitanalyse von Algorithmen 5
Aufgabe 1.4
Angenommen ein bestimmtes Problem, z. B. die Primfaktorzerlegung einern-stelligen
Zahl, ben ¨otigt O(2n) viele Schritte; die Laufzeit ist also exponentiell in der Gr ¨oße
der Eingabe.
(a) Angenommen, uns steht ein ¨außerst leistungsf¨ahiger Rechner zur Verf¨ugung, der
f¨ur eine elementare Operation 50 ps ben¨otigt. F ¨ullen Sie nun folgende Tabelle
mit den ungef¨ahren Laufzeiten aus:
L¨ange der zu zerlegenden Zahl
10 20 50 100 200 1000
Laufzeit
(b) Wir nehmen Kontakt zu einer außerirdischen Zivilisation auf, die der unseren
technologisch sehr ¨uberlegen ist. Sie k¨onnen Rechner bauen, die 1 Mio mal schnel-
ler sind als die unsrigen; nehmen wir weiter an, jeder Außerirdische auf dem mit
20 Mrd Individuen hoﬀnungslos ¨uberbev¨olkerten Planeten besitzt einen solchen
schnellen Rechner. Zudem sind sie in der Lage alle 20 Mrd Rechner zu einem
Cluster zusammen zu schließen, das dann tats¨achlich etwa 20 Mrd mal schneller
ein bestimmtes Problem l¨osen kann als ein einzelner Rechner. F¨ullen Sie nun die
folgende Tabelle mit den ungef¨ahren Laufzeiten aus, die dieses Alien-Cluster zur
Primfaktorzerlegung ben¨otigt.
L¨ange der zu zerlegenden Zahl
50 100 200 1000 5000
Laufzeit
Eine weitere wichtige Komplexit¨atsklasse ist die Klasse NP, die alle
Sortierproblem
K¨urzeste-Wege-
Problem
...
Probleme
NP-Vollst.NP
P
Probleme beinhaltet, die durch eine nicht-deterministische Rechen-
maschine in polynomieller Zeit ”berechnet“ werden k ¨onnen. Einer
nicht-deterministischen Rechenmaschine (mathematisch modelliert
durch eine nicht-deterministische Turingmaschine) kann man meh-
rere alternative Rechenwege zur Verf¨ugung stellen; die ”Ausf¨uhrung“
eines Programms auf einer solchen Maschine besteht darin, dass sie
sich (durch ”Magie“) immer die richtige zum Ziel f ¨uhrende Alterna-
tive ausw¨ahlt. Es gilt P ⊆NP, da jeder polynomielle Algorithmus
auch genauso gut auf einer nicht-deterministischen Maschine (oh-
ne jedoch dieses Nicht-Determinismus- ”Feature“ zu nutzen) in polynomieller Zeit aus-
gef¨uhrt werden kann. Interessanterweise konnte bisher noch nicht gezeigt werden, dass
P ̸= NP, auch wenn die meisten Spezialisten dies stark vermuten.
Es gibt eine Klasse von Problemen, die sog. NP-vollst¨andigen Probleme, die (intuitiv
gesprochen) ”schwersten“ Probleme in NP; zudem kann man (wiederum intuitiv ge-
sprochen) sagen, dass alle NP-vollst¨andigen Probleme in gewissem Sinne gleich schwer
sind. Wenn man f¨ur eines dieser NP-vollst¨andigen Probleme einen polynomiellen Algo-
rithmus ﬁnden w¨urde, so w¨are man in der Lage, dieses polynomielle Verfahren auf alle

## Seite 21

6 1 Algorithmen-Grundlagen und Algorithmen-Implementierung
anderen NP-vollst¨andigen Probleme zu ¨ubertragen und – da diese gewissermaßen die
schwersten Probleme in NP sind – somit auf alle Probleme in NP zu ¨ubertragen. Dann
h¨atte man gezeigt, dass P = NP. Bisher hat jedoch noch niemand einen polynomiellen
Algorithmus f¨ur ein solches NP-vollst¨andiges Problem gefunden und somit bleibt wei-
terhin unbewiesenermaßen zu vermuten, dass P ̸= NP ist.
Rabin Karp ”entdeckte“ diese ¨Ahnlichkeit der NP-vollst ¨andigen Probleme; in seinem
urspr¨unglichen Artikel [11] beschrieb er insgesamt 21 solche Probleme. Wir geben hier
eine kleine Auswahl davon an:
 3SAT: Das Erf ¨ullbarkeitsproblem (Satisﬁability) f ¨ur 3-KNF-Formeln, d. h. f ¨ur
boolesche Formeln in Konjunktiver Normalform (also Konjunktionen von Dis-
junktionen), wobei jede Klausel genau drei Variablen enth¨alt, besteht darin, nach
einer Belegung der Variablen zu suchen, so dass die Formel erf ¨ullt ist (d. h. den
Wahrheitswert ”True“ liefert).
 Rucksack-Problem: Das Problem besteht darin, aus einer Menge von Objekten,
die jeweils einen Wert und ein Gewicht haben, eine Teilmenge so auszuw ¨ahlen,
dass deren Gesamtgewicht eine vorgegebene Schwelle nicht ¨uberschreitet und der
Wert der Objekte maximal ist.
 Clique: Gegeben sei ein Graph. Das Problem besteht darin, einen vollst ¨andigen
Teilgraphen mit k Knoten zu ﬁnden. (Ein Graph heißt vollst ¨andig, wenn jeder
Knoten mit jedem anderen verbunden ist).
 Travelling-Salesman-Problem (Kurz: TSP). Das Problem besteht darin, eine Rei-
henfolge f¨ur den Besuch einer gegebenen Anzahl von Orten so auszuw ¨ahlen, dass
die zur¨uckgelegte Wegstrecke minimal ist.
1.2 Implementierung von Algorithmen
Insbesondere dann, wenn man Algorithmen in ausf ¨uhrbaren Programmiersprachen be-
schreiben m¨ochte, muss man sich Gedanken um die Implementierung machen. Es gibt
immer mehrere M ¨oglichkeiten einen Algorithmus zu implementieren. Man muss sich
entscheiden, ob man einen Algorithmus durch rekursive Funktionen oder durch Iterati-
on implementiert. Man muss sich entscheiden, ob ein Algorithmus eine Datenstruktur
ver¨andern soll, oder ob er die ”alte“ Struktur bel¨asst und als R¨uckgabewert eine ”neue“
Datenstruktur zur¨uckliefert. Und man muss sich entscheiden, ob man eine Datenstruk-
tur durch eine Klasse oder etwa durch eine Liste oder gar durch eine Hash-Tabelle
implementiert.
1.2.1 Rekursive vs. iterative Implementierung
Ein Funktion heißt genau dann rekursiv, wenn der Funktionsk ¨orper mindestens einen
Aufruf der Funktion selbst enth¨alt, die Funktion also die folgende Form hat:

## Seite 22

1.2 Implementierung von Algorithmen 7
def rekFunc(x):
...
... rekFunc(i) ...
...
Intuitiv vermutet man hier eine Endlos ”schleife“ (die Funktion ruft sich endlos selbst
auf) – wir werden jedoch gleich sehen, dass dies nicht notwendigerweise der Fall sein
muss.
Beispiel: Implementierung der Fakult¨atsfunktion. Betrachten wir als erstes Bei-
spiel die Implementierung einer Funktion, die die Fakult¨at einer Zahl n berechnet. Eine
iterative Implementierung k¨onnte folgendermaßen aussehen:
1 def facIter (n):
2 erg = 1
3 for i in range(1,n +1)
4 erg = erg*i
5 return erg
Aufgabe 1.5
Verwenden Sie die Python-Funktionreduce, um eine Funktionprod( lst ) zu deﬁnieren,
die als Ergebnis die Aufmultiplikation der Zahlen in lst zur¨uckliefert. Mathematisch
ausgedr¨uckt, sollte f¨ur prod gelten:
prod(lst)
!
=
∏
x∈lst
x
Implementieren Sie nun facIter mit Hilfe von prod.
Man kann die Fakult ¨atsfunktion auch rekursiv deﬁnieren, wie in Listing 1.1 gezeigt.
Man beachte, dass diese Funktionsdeﬁnition im Gegensatz zur iterativen Deﬁnition
keine Schleife ben¨otigt.
1 def fac(n):
2 if n==0:
3 return 1
4 else:
5 return n *fac(n -1)
Listing 1.1: Rekursive Implementierung der Fakult ¨atsfunktion
Um zu verstehen, wie fac einen Wert berechnet, zeigt Abbildung 1.1 im Detail an
einem Beispiel, wie etwa ein Aufruf von fac(4) abl ¨auft. F ¨ur den Programmierer ist
es interessant zu wissen, dass der rekursive Abstieg immer mit einer zunehmenden

## Seite 23

8 1 Algorithmen-Grundlagen und Algorithmen-Implementierung
Belegung des Stacks1 einhergeht; ein zu langer rekursiver Abstieg kann hierbei evtl. in
einem ”Stack Overﬂow“, d. h. einem ¨Uberlauf des Stackspeichers, enden.
1
1*1=1
3*2=6
2*1=2
fac(4)
return 4*fac(3)
return 3*fac(2)
return 2*fac(1)
return 1*fac(0)
return 1
4*6=24
4. Inst.
1. Instanz
2. Instanz
3. Instanz
Rekursiver Aufstieg
Rekursiver Abstieg
Abb. 1.1: Bei einem Aufruf von fac(4) wird (da 4==0 nicht zutriﬀt) sofort die Anweisung
return 4*fac(3) (Zeile 5, Listing 1.1) ausgef ¨uhrt, was zu dem Aufruf fac(3), also einem rekur-
siven Aufruf, f ¨uhrt. Ab diesem Zeitpunkt sind zwei Instanzen der Funktion fac zugleich aktiv:
Die erste Instanz wartet auf die Ergebnisse, die die zweite Instanz liefert und die Befehle der
zweiten Instanz werden aktuell ausgef ¨uhrt. Alle Anweisungen dieser zweiten Instanz sind in der
Abbildung einger¨uckt dargestellt. Bei diesem Aufruf von fac(3) wird (da 3==0 nicht zutriﬀt)
sofort die Anweisung return 3*fac(2) ausgef¨uhrt, was zu dem Aufruf fac(2), also einem wei-
teren rekursiven Aufruf f ¨uhrt, usw. Dieser Prozess des wiederholten rekursiven Aufrufs einer
Funktion (in Richtung auf den Rekursionsabbruch) nennt man auch den rekursiven Abstieg.
In der 5. Instanz schließlich ist mit dem Aufruf fac(0) der Rekursionsabbruch erreicht: nach
Beenden der 5. Instanz kann der Wert der return-Anweisung der 4. Instanz bestimmt wer-
den und anschließend die 4. Instanz beendet werden, usw. Diese sukzessive Beenden der durch
rekursive Aufrufe entstandenen Instanzen nennt man auch den rekursiven Aufstieg.
Damit eine rekursive Funktion sich nicht endlos immer wieder selbst aufruft, sollte sie
die beiden folgenden Eigenschaften haben:
1. Rekursionsabbruch: Es muss eine Abfrage vorhanden sein, ob das Argument des
Aufrufs ”klein“ genug ist –”klein“ muss in diesem Zusammenhang nicht notwendi-
gerweise ”numerisch klein“ bedeuten, sondern kann je nach involviertem Datentyp
auch strukturell klein bedeuten. In diesem Fall soll die Rekursion beendet wer-
den; es sollen also keine weiteren rekursiven Aufrufe stattﬁnden. In diesem Fall
sollte der R ¨uckgabewert einfach direkt berechnet werden. In Listing 1.1 besteht
der Rekursionsabbruch in Zeile 2 und 3 darin zu testen, ob die ¨ubergebene Zahl
eine Null ist – in diesem Fall ist die Fakult ¨at deﬁnitionsgem¨aß 1.
1Der Zustand der aufrufenden Funktion – dazu geh¨oren unter Anderem Werte von lokalen Variablen
und die Werte der Aufrufparameter – wird immer auf dem Stack des Rechners gespeichert. Jede Instanz
einer Funktion, die sich noch in Abarbeitung beﬁndet, belegt hierbei einen Teil des Stacks.

## Seite 24

1.2 Implementierung von Algorithmen 9
2. Rekursive Aufrufe sollten als Argument (strukturell oder numerisch) ”kleine-
re“ Werte ¨ubergeben bekommen. Handelt es sich bei den Argumenten etwa um
nat¨urliche Zahlen, so sollten die rekursiven Aufrufe kleinere Zahlen ¨ubergeben
bekommen. Handelt es sich bei den Argumenten etwa um Listen, so sollten die
rekursiven Aufrufe k ¨urzere Listen ¨ubergeben bekommen; handelt es sich bei den
Argumenten etwa um B¨aume, so sollten die rekursiven Aufrufe B¨aume geringerer
H¨ohe (oder B¨aume mit weniger Eintr¨agen) ¨ubergeben bekommen, usw.
Die in Listing 1.1 gezeigte rekursive Implementierung der Fakult¨atsfunktion erf¨ullt
diese Voraussetzung: Der rekursive Aufruf in Zeile 5 erfolgt mit einem Argument,
das um eins kleiner ist als das Argument der aufrufenden Funktion.
Rekursive Aufrufe mit kleineren Argumenten stellen einen rekursiven Abstieg sicher; der
Rekursionsabbruch beendet den rekursiven Abstieg und leitet den rekursiven Aufstieg
ein.
Oﬀensichtlich erf¨ullt also die in Listing 1.1 gezeigte rekursive Implementierung der Fa-
kult¨atsfunktion diese Eigenschaften und ist somit wohldeﬁniert.
Aufgabe 1.6
Angenommen, eine rekursive Funktion erh¨alt als Argument eine reelle Zahl. Warum
ist es f ¨ur eine korrekt funktionierende rekursive Funktion nicht ausreichend zu for-
dern, dass die rekursiven Aufrufe als Argumente kleinere reelle Zahlen erhalten als
die aufrufende Funktion?
Aufgabe 1.7
(a) Deﬁnieren Sie die Funktion sum(n), die die Summe der Zahlen von 1 bis n
berechnen soll, rekursiv.
(b) Deﬁnieren Sie die Funktion len( lst ), die die L¨ange der Liste lst berechnen soll,
rekursiv.
Beispiel: Beschriftung eines Meterstabs. Wir haben gesehen, dass das vorige Bei-
spiel einer rekursiv deﬁnierten Funktion auch ebenso einfach iterativ programmiert wer-
den konnte. Das gilt f¨ur die folgende Aufgabe nicht: Sie ist sehr einfach durch eine rekur-
sive Funktion umzusetzen; die Umsetzung durch eine iterative Funktion ist in diesem
Fall jedoch deutlich schwerer2. Wir wollen ein Programm schreiben, das Striche auf ein
Lineal folgendermaßen zeichnet: In der Mitte des Lineals soll sich ein Strich der H ¨ohe h
beﬁnden. Die linke H¨alfte und die rechte H¨alfte des Lineals sollen wiederum vollst¨andig
beschriftete Lineale sein, in deren Mitten sich jeweils Striche der H ¨ohe h−1 beﬁnden,
usw. Abbildung 1.2 zeigt solch ein Lineal (das mit dem Pythonskript aus Listing 1.2
gezeichnet wurde).
2Dies gilt allgemein auch f ¨ur alle nach dem sog. Divide-And-Conquer Schema aufgebauten Algo-
rithmen.

## Seite 25

10 1 Algorithmen-Grundlagen und Algorithmen-Implementierung
Abb. 1.2: Das durch Aufruf von lineal (0,1024,45) gezeichnete Lineal in dem durch
GraphWin("Ein Lineal",1024,50) (Zeile 3, Listing 1.2) erzeugten Fenster.
1 from graphics import *
2
3 linealCanv = GraphWin('Ein Lineal',1000,50)
4
5 def strich (x,h):
6 l = Line(Point(x,0),Point(x,h))
7 l .draw(linealCanv)
8
9 def lineal (l ,r,h):
10 step = 5
11 if (h<1): return
12 m = (l +r)/2
13 strich (m,h)
14 lineal (l ,m,h -step)
15 lineal (m,r,h -step)
Listing 1.2:Die rekursiv deﬁnierte Funktion lineal zeichnet das in Abbildung 1.2 dargestellte
Lineal.
Der Rekursionsabbruch der rekursiv deﬁnierten Funktionlineal beﬁndet sich in Zeile 11;
die rekursiven Aufrufe (mit kleinerem dritten Parameter) beﬁnden sich in Zeile 14 und
Zeile 15. Das verwendete graphics-Modul ist eine kleine, sehr einfach gehaltene Graphik-
Bibliothek, geschrieben von John Zelle, der es in seinem Python-Buch [19] verwendet.
Der Konstruktor GraphWin in Zeile 3 erzeugt ein Fenster der Gr¨oße 1000×50 Pixel; die
Funktion strich (x,h) zeichnet an Position x des zuvor erzeugten Fensters eine vertikale
Linie der L¨ange h.
Versucht man dieselbe lineal -Funktion dagegen iterativ zu programmieren, muss man
sich erheblich mehr Gedanken machen: Entweder muss man die rekursive Aufrufhierar-
chie unter Verwendung eines Stacks ”simulieren“ (in Abschnitt 2.3.5 ab Seite 30 zeigen
wir im Detail am Beispiel des Quicksort-Algorithmus wie man hierbei vorgehen kann)
oder man muss entschl¨usseln, welche H¨ohe ein Strich an Position x haben muss.
Aufgabe 1.8
Verwenden Sie Iteration um eine lineal -Funktion zu programmieren, die ¨aquivalent
zur lineal -Funktion aus Listing 1.2 ist.

## Seite 26

1.2 Implementierung von Algorithmen 11
Aufgabe 1.9
Zeichnen Sie durch eine rekursiv deﬁnierte Python-Funktion und unter Verwendung
der graphics-Bibliothek folgenden Stern:
Aufgabe 1.10
Schreiben Sie eine rekursive Prozedur baum(x,y,b,h) zum Zeichnen eines (bin ¨aren)
Baumes derart, dass die Wurzel sich bei (x,y) beﬁndet, der Baum b breit und h hoch
ist. Deﬁnieren Sie hierzu eine Python-Prozedur line (x1,y2,x2,y2), die eine Linie vom
Punkt ( x1,y2) zum Punkt ( x2,y2) zeichnet. Folgende Abbildung zeigt ein Beispiel
f¨ur die Ausgabe die der Aufruf baum(0,0,16,4) erzeugt.
16
4
3
2
1
(0,0)

## Seite 27

12 1 Algorithmen-Grundlagen und Algorithmen-Implementierung
Aufgabe 1.11
Das sog. Sierpinski-Dreieck kann folgendermaßen konstruiert werden. 1. Man w¨ahle
zun¨achst eine (eigentlich beliebige) Form – wir starten hier mit einem gleichschen-
keligen Dreieck, also einem beliebig großen Dreieck mit drei gleichlangen Seiten. 2.
Nun verkleinern wir diese Form um genau die H¨alfte ihrer urspr¨unglichen Gr¨oße und
positionieren zwei dieser Formen direkt nebeneinander und eine dritte mittig direkt
dar¨uber. 3. Man wiederhole nun mit der so erhaltenen Form den Schritt 2. rekursiv.
Das folgende Bild zeigt die ersten 5 Schritte beim Zeichnen eines Sierpinski-Dreiecks.
Schreiben Sie eine rekursive Prozedur sierpinski (x,y,n), die ein Sierpinski-Dreieck
der Seitenl¨ange n und Mittelpunkt ( x,y) zeichnet.
1.2.2 Warum Rekursion (statt Iteration)?
Rekursive Implementierungen m¨ogen f¨ur den Informatik-”Anf¨anger“ schwieriger zu ver-
stehen sein und f ¨ur manche Compiler/Interpreter problematischer zu ¨ubersetzen sein,
sie haben jedoch einen entscheidenden Vorteil: Man braucht sich nicht der L ¨osung des
kompletten Problems zu widmen, sondern es gen ¨ugt, sich ¨uber den ”Rekursionsschritt“
Gedanken zu machen. Man muss sich dabei ”nur“ ¨uberlegen, wie man sich aus einer
(bzw. mehrerer) ”kleineren“3 L¨osung(en) des Problems eine ”gr¨oßere“ L¨osung konstru-
ieren kann. Dies ist meist viel weniger komplex als sich zu ¨uberlegen, wie die L ¨osung
von Grund auf zu konstruieren ist.
1.2.3 ”Kochrezept“ f¨ur das Entwickeln eines rekursiven
Algorithmus
(a) Zun ¨achst kann man sich den Rekursionsabbruch ¨uberlegen, also:
 Was ist der ”triviale“, einfache Fall? ¨Ublicherweise ist der einfache Fall f ¨ur
eine Eingabe der Gr ¨oße n= 1, n= 0 oder einem anderen kleinen Wert f ¨ur n
gegeben.
 Was muss der Algorithmus noch tun, wenn er solch einen einfachen Fall vor-
liegen hat? ¨Ublicherweise sind nur noch (wenn ¨uberhaupt) einfache Manipu-
lationen der Eingabe vorzunehmen.
(b) Dann muss man sich eines Gedanken ”tricks“ bedienen. Man nehme an, dass die
Aufgabenstellung schon f ¨ur ein oder mehrere ”kleinere“ Probleme gel ¨ost sei und
¨uberlegt sich (unter dieser Annahme), wie man aus den L ¨osungen der kleineren
Aufgaben, die L¨osung der Gesamtaufgabe konstruieren kann. Die Implementierung
dieses Schritts wird auch als der ”Rekursionsschritt“ bezeichnet.
3Was auch immer ”kleiner“ im Einzelfall heißen mag; falls die Eingaben Listen w ¨aren, w¨urde man
darunter eine k¨urzere Liste verstehen.

## Seite 28

1.3 Nicht-destruktive vs. In-place Implementierung 13
(c) Das Ausprogrammieren der rekursiven L ¨osung erfolgt dann prinzipiell wie in fol-
gendem Pseudo-Python-Code-Listing gezeigt:
1 def rekAlg(x):
2 if groesse(x) is kleingenug:
3 return loesung(x)
4 else:
5 (x1,x2, ... ) = aufteilen(x) # len(x1) < x, len(x2) < x, ...
6 return rekSchritt(rekAlg(x1),rekAlg(x2), ... )
Die rekursive Funktion startet mit dem Test, ob die Rekursion abgebrochen werden
kann, was dann der Fall ist, wenn die Gr¨oße der Eingabe klein genug ist und so die
L¨osung einfach berechnet werden kann. Andernfalls wird der Algorithmus rekursiv
evtl. mehrmals aufgerufen um so Teill ¨osungen zu produzieren; die Entscheidung,
wie die Eingabe aufgeteilt werden soll, ¨uberlassen wir der Funktion aufteilen ,
die f ¨ur jeden rekursiven Algorithmus individuell ausprogrammiert werden muss.
Diese Teill¨osungen werden dann wieder zusammengef ¨ugt – hier dargestellt durch
Ausf¨uhrung der Funktion rekSchritt. In der Ausprogrammierung dieses Rekursi-
onsschritts besteht im Allgemeinen die eigentliche algorithmische Herausforderung
bei der L¨osung eines gegebenen Problems.
1.3 Nicht-destruktive vs. In-place Implementierung
Viele in imperativen Programmiersprachen wie C, C++ oder Python implementierte
Algorithmen operieren auf ihrer Eingabe ”destruktiv“, d. h. sie zerst ¨oren bzw. ¨uber-
schreiben ihre urspr ¨ungliche Form; sie ”bauen“ die Struktur des ¨ubergebenen Parame-
ters so um, dass das gew ¨unschte Ergebnis entsteht. Dies geschieht etwa, wenn man mit
Hilfe der in Python eingebauten Sortierfunktion sort() eine Liste sortiert. Eine Liste
wird dem Sortieralgorithmus ¨ubergeben, der diese in destruktiver Weise sortiert (”>>>“
ist die Eingabeauﬀorderung der Python-Shell):
>>> lst =[17, 46, 45, 47, 43, 25, 35, 60, 80, 62, 60, 41, 43, 14]
>>> lst . sort()
>>>print lst
[14, 17, 25, 35, 41, 43, 43, 45, 46, 47, 60, 60, 62, 80]
Nach Aufruf von lst . sort() werden die Werte, die urspr ¨unglich in lst standen ¨uber-
schrieben, und zwar so, dass eine sortierte Liste entsteht. Wir k ¨onnen nun nicht mehr
auf den urspr¨unglichen Wert von lst zugreifen. Der große Vorteil einer solchen”destruk-
tiven“ Implementierung ist jedoch, dass sie i. A. ”in-place“ – also ”an Ort und Stelle“ –
erfolgen kann, d. h. dass der Algorithmus (so gut wie) keinen weiteren Speicherbereich
belegen muss, sondern f ¨ur die Sortierung ausschließlich den Speicherbereich ben ¨otigt,
der durch lst bereits belegt ist.
Viele in funktionalen Sprachen, wie Haskell, ML oder Lisp, implementierte Algorithmen
dagegen verarbeiten die Eingabe”nicht destruktiv“, d. h. sie zerst¨oren die Eingabe nicht.
Stattdessen erzeugen sie sich als Ergebnis (d. h. als R¨uckgabewert; in Python durch das

## Seite 29

14 1 Algorithmen-Grundlagen und Algorithmen-Implementierung
return-Kommando ¨ubergeben) eine neue Struktur, die sich teilweise oder ganz in einem
neuen Speicherbereich beﬁndet.
Pythons eingebaute Funktion sorted(xs) verarbeitet ihre Eingabe nicht-destruktiv:
>>> lst =[17, 46, 45, 47, 43, 25, 35, 60, 80, 62, 60, 41, 43, 14]
>>> lst2 =sorted(lst1)
>>>print lst2
[14, 17, 25, 35, 41, 43, 43, 45, 46, 47, 60, 60, 62, 80]
Der Nachteil nicht-destruktiver Implementierungen ist oﬀensichtlich: sie brauchen mehr
Speicherplatz, als entsprechende In-place-Implementierungen.
1.3.1 Warum nicht-destruktive Implementierungen?
Wenn nicht-destruktive Implementierungen mehr Speicherplatz ben ¨otigen und daher
meist auch etwas langsamer sind als destruktive (d. h. In-place-)Implementierungen,
warum sollte man nicht-destruktive Implementierung ¨uberhaupt in Erw ¨agung ziehen?
Der Grund ist einfach: nicht-destruktive Implementierungen sind oft kompakter, leichter
zu verstehen und entsprechend schneller und fehlerfreier zu implementieren. Um den
Grund daf¨ur wiederum zu erkl ¨aren, m¨ussen wir etwas weiter ausholen:
 Jedes destruktive Update einer Datenstruktur ver ¨andert den internen Zustand
eines Programms.
 Je gr ¨oßer die Anzahl der m ¨oglichen Zust ¨ande im Laufe des Programmablaufs,
desto mehr potentielle Abfragen, und desto mehr potentielle Fehler k ¨onnen sich
einschleichen.
 Eine Funktion, die keine destruktiven Updates verwendet (die einer mathemati-
schen Funktion also relativ ¨ahnlich ist), f ¨uhrt keine Zust ¨ande ein; im optimalen
Fall ver¨andert ein gegebenes Programm den globalen Zustand ¨uberhaupt nicht,
und diese zustandsfreie Situation erlaubt es dem Programmierer, leichter den
¨Uberblick zu bewahren.
Viele moderne Compiler und Interpreter sind inzwischen schon ”intelligent“ genug, den
durch nicht-destruktive Implementierungen verwendeten Speicher selbstst¨andig wieder
freizugeben, wenn klar ist, dass Daten nicht mehr verwendet werden. Dies erm ¨oglicht
es, tats¨achlich Programme, die ausschließlich nicht-destruktive Updates beinhalten, in
praktisch genauso schnellen Maschinencode zu ¨ubersetzen wie Programme, die aus-
schließlich In-place-Implementierungen verwenden.
1.4 Repr ¨asentation von Datenstrukturen
M¨ochte man eine Datenstruktur repr ¨asentieren, die aus mehreren Informations-Kom-
ponenten besteht, so bieten sich in Python hierzu mehrere M ¨oglichkeiten an. Nehmen
wir beispielsweise an, wir wollen einen Baum repr¨asentieren, der aus den Komponenten
Schl¨usseleintrag, Werteintrag, linker Teilbaum und rechter Teilbaum besteht.

## Seite 30

1.4 Repr ¨asentation von Datenstrukturen 15
1.4.1 Repr ¨asentation als Klasse
Das Paradigma der Objektorientierten Programmierung schl ¨agt die Repr¨asentation als
Klasse vor, wie in Listing 1.3 gezeigt.
1 class Baum(object):
2 init ( self ,key,val , ltree=None,rtree=None):
3 self .key = key ; self . val=val
4 self . ltree = ltree ; self . rtree = rtree
Listing 1.3: Repr¨asentation eines Baums durch eine Klasse
Der rechts gezeigte einfache Baum kann dann folgendermaßen mittels des Klassenkon-
struktors erzeugt werden:
Baum(10,20,Baum(1,2),Baum(3,4))
10
31
Diese Art der Repr¨asentation ist in vielen F¨allen die sinnvollste; die Klassenrepr¨asenta-
tion wird in diesem Buch f¨ur viele B¨aume (außer f¨ur Heaps) und f¨ur Graphen verwendet.
1.4.2 Repr ¨asentation als Liste
Eine Klasse ist nicht die einzige M ¨oglichkeit der Repr¨asentation. Man k¨onnte auch ei-
ne Liste verwendet, um die (in diesem Fall vier) Informations-Komponenten zu einem
B¨undel, das dann den Baum darstellt, zusammenzufassen. Der Baum aus obiger Abbil-
dung ließe sich dann folgendermaßen deﬁnieren:
[10,20, [1,2 ], [3,4 ] ]
Mit ebenso viel Recht k ¨onnten wir uns aber auch dazu entscheiden, leere Teilb ¨aume
explizit aufzuf¨uhren und etwa durch”None“ zu repr¨asentieren. Dann h¨atte obiger Baum
die folgende Repr¨asentation:
[10,20, [ 1,2,None,None],[3,4,None,None ]]
Diese Art der Darstellung ist kompakter als die Darstellung ¨uber eine Klasse, und es
kann sich in einigen F ¨allen durchaus als vern ¨unftig herausstellen, diese Art der Re-
pr¨asentation zu w¨ahlen. Ein ”Problem“ ist jedoch oben schon angedeutet: Es gibt viele
Freiheitsgrade, wie diese Liste zu gestalten ist. Zus ¨atzlich ist eine Repr ¨asentation ¨uber
eine Klasse typsicherer: Der Wert Baum(10,20) ist immer ein Baum; der Wert [10,20]
k¨onnte dagegen ebenso eine einfache Liste sein.
Ein Repr¨asentation ¨uber Listen wurde in diesem Buch beispielsweise f¨ur Binomial-Heaps
gew¨ahlt (siehe Abschnitt 4.2).
1.4.3 Repr ¨asentation als Dictionary
Die Repr¨asentation als Dictionary stellt in gewissem Sinn einen Kompromiss zwischen
der mit verh¨altnism¨aßig viel Overhead verbundenen Repr¨asentation als Klasse und der

## Seite 31

16 1 Algorithmen-Grundlagen und Algorithmen-Implementierung
sehr einfachen aber nicht typsicheren Repr ¨asentation als Liste dar. Jede Informations-
Komponente erh¨alt hierbei eine Kennung (etwa einen String), und die Datenstruktur
stellt dann nichts anderes als eine Sammlung solcher mit Kennung versehener Kompo-
nenten dar. Der oben im Bild dargestellte Baum k¨onnte so folgendermaßen repr¨asentiert
werden:
{'key':10 , 'val':20 ,
'ltree': {'key':1 , 'val':2 , 'ltree':None , 'rtree':None} ,
'rtree': {'key':3 , 'val':4 , 'ltree':None , 'rtree':None}
}
Tats¨achlich erfolgt Python-intern der Zugriﬀ auf die Attribute und Methoden einer
Klasse nach dem gleichen Prinzip wie der Zugriﬀ auf die Eintr ¨age eines Dictionary-
Objektes: n¨amlich ¨uber eine Hash-Tabelle; diese Datenstruktur beschreiben wir in Ab-
schnitt 3.4 ab Seite 72). Insofern ist zumindest technisch gesehen die Repr ¨asentation
¨uber ein Dictionary schon recht nah an der Repr ¨asentation ¨uber eine Klasse.
Wir verwenden diese Art der Repr ¨asentation beispielsweise f ¨ur die Implementierung
von Fibonacci-Heaps (Abschnitt 4.3 auf Seite 127) und Pairing-Heaps (Abschnitt 4.4
auf Seite 142).

## Seite 32

2 Sortieralgorithmen
Laut Donald E. Knuth[12] sch¨atzten Computerhersteller in den 60er Jahren, dass mehr
als 25 Prozent der Rechenzeit eines durchschnittlichen Computers dazu verwendet wur-
de zu sortieren. In der Tat gibt es unz¨ahlige Anwendungen in denen Datens¨atze sortiert
werden m¨ussen: Unix gibt beispielsweise die Dateien in jedem Verzeichnis alphabetisch
sortiert aus; Sortieren ist vor dem Zuteilen von Briefen notwendig (etwa nach Post-
leitzahl, Bereich usw.); Suchmaschinen sortieren die Treﬀer nach Relevanz; Internet-
kaufh¨auser sortieren Waren nach den verschiedensten Kriterien, wie Beliebtheit, Preis,
usw.; Datenbanken m¨ussen in der Lage sein, Treﬀer von Suchanfragen nach bestimmten
Kriterien zu sortieren.
Wir stellen im Folgenden vier Sortieralgorithmen vor: Insertion Sort, Quicksort, Mer-
gesort und Heapsort. Insertion Sort ist ein sehr einfacher Sortieralgorithmus, den vie-
le der Leser ohne algorithmische Vorbildung – h ¨atten sie die Aufgabe gehabt, eine
Sortierroutine zu implementieren – wahrscheinlich programmiert h ¨atten. Die Beschrei-
bung von Quicksort benutzen wir dazu verschiedene Entwurfstechniken und Optimie-
rungsm¨oglichkeiten zu beschreiben und auch dazu, genau auf die Funktionsweise von
sog. Divide-And-Conquer-Algorithmen einzugehen. Im Zuge der Pr¨asentation des Heap-
sort-Algorithmus gehen wir auch kurz auf die Funktionsweise einer sog. Heapdatenstruk-
tur ein; detailliertere Beschreibungen von Heaps ﬁnden sich in einem eigenen Kapitel,
dem Kapitel 4 ab Seite 115.
2.1 Insertion Sort
Vermutlich verwenden die meisten Menschen Insertion Sort, wenn sie eine Hand voll
Karten sortieren wollen: Dabei nimmt man eine Karte nach der anderen und f ¨ugt die-
se jeweils in die bereits auf der Hand beﬁndlichen Karten an der richtigen Stelle ein;
im einfachsten Fall wird die ”richtige Stelle“ dabei einfach dadurch bestimmt, dass die
Karten auf der Hand sukzessive von links nach rechts durchlaufen werden bis die pas-
sende Stelle gefunden ist. Abbildung 2.1 veranschaulicht diese Funktionsweise anhand
der Sortierung einer Beispielliste nochmals graphisch.
2.1.1 Implementierung: nicht-destruktiv
Eine m¨ogliche Implementierung besteht aus zwei Funktionen: Der FunktioninsND(l,key),
die den Wert key in eine schon sortierte Liste l einf¨ugt. Das K¨urzel ”ND“ am Ende des
Funktionsnames steht f¨ur ”nicht-destruktiv“, d. h. die in Listing 2.1 gezeigte Implemen-
tierung ver¨andert die als Parameter ¨ubergebene Liste l nicht; sie liefert stattdessen als
R¨uckgabewert eine neue Liste, die eine Kopie der ¨ubergebenen Liste, mit dem Wert key

## Seite 33

18 2 Sortieralgorithmen
[6,53,63,94,56,8,72,44,70]
[6,53,63,94,56,8,72,44,70]
[6,53,63,94,56,8,72,44,70]
[53,6,63,94,56,8,72,44,70]1.
3.
4.
2. [6,8,53,56,63,94,72,44,70]
[6,53,56,63,94,8,72,44,70]
8.
7.
6.
5.
[6,8,53,56,63,72,94,44,70]
[6,8,44,53,56,63,72,94,70]
[6,8,44,53,56,63,70,72,94]Ergebnis:
Abb. 2.1: Veranschaulichung der Funktionsweise von Insertion Sort auf der anf ¨anglich un-
sortierten Liste [53, 6, 63, 94, 56, 8, 72, 44, 70]. Wie man sieht, wird immer das jeweils
n¨achste Element in den schon sortierten Teil der Liste (grau markiert) einsortiert.
an der ”richtigen“ Stelle, enth¨alt.
1 def insND(l,key):
2 return [x for x in l if x ≤key] + [key] + [x for x in l if x>key]
Listing 2.1: Einf¨ugen eines Wertes in eine schon sortierte Liste
Die Ergebnisliste besteht zun ¨achst aus allen Werten aus l, die kleiner oder gleich key
sind – diese werden in der linken Listenkomprehension gesammelt –, gefolgt von key,
gefolgt von allen Werten aus l, die gr ¨oßer als key sind – diese Werte werden in der
rechten Listenkomprehension gesammelt.
Listing 2.2 zeigt, wie nun der eigentliche Insertion-Sort-Algorithmus mit Hilfe voninsND
sehr einfach rekursiv implementiert werden kann.
1 def insertionSortRek(l ):
2 if len(l)≤1: return l
3 else: return insND(insertionSortRek(l[1:]), l [0])
Listing 2.2: Rekursive Implementierung von Insertion Sort
Zeile 2 deﬁniert den Rekursionsabbruch: eine einelementige oder leere Liste ist schon
sortiert und kann einfach zur ¨uckgeliefert werden. Zeile 3 deﬁniert den Rekursionsab-
stieg: eine Liste kann dadurch sortiert werden, indem das erste Element entfernt wird,
der Rest der Liste durch den rekursiven Aufruf insertionSortRek(l [1 :]) sortiert wird
und anschließend das entfernte Element l [0] wieder an der richtigen Stelle eingef ¨ugt
wird. F¨ur Neulinge der rekursiven Programmierung empﬁehlt sich f ¨ur das Verst¨andnis
der Funktionsweise von insertionSortRek das strikte Befolgen des in Abschnitt 1.2.3 be-
schriebenen ”Kochrezepts“: Man gehe einfach davon aus, dass insertionSortRek(l [1 :])
f¨ur die k¨urzere Teilliste l [1 :] das Richtige tut – n ¨amlich l [1 :] zu sortieren. Unter die-
ser Annahme sollte man sich ¨uberlegen, wie man das fehlende Element l [0] mit dieser
sortierten Teilliste kombinieren muss, damit eine sortierte Gesamtliste entsteht.

## Seite 34

2.1 Insertion Sort 19
Aufgabe 2.1
Implementieren Sie – ebenfalls unter Verwendung voninsND – eine iterative Variante
von insertionSortRek.
2.1.2 In-place Implementierung
Listing 2.3 zeigt als Alternative eine in-place Implementierung des Insertion-Sort-Algo-
rithmus – ohne die Verwendung von Zwischen-Listen (dies ist auch der Grund daf ¨ur,
dass die folgende Implementierung etwas schneller ist).
1 def insertionSort(l ):
2 for j in range(1,len(l )):
3 key = l [j ]
4 i = j -1
5 while i ≥ 0 and l[i ] > key:
6 l [i +1] = l[i]
7 i = i -1
8 l [i +1] = key
Listing 2.3: In-Place Implementierung des Insertion-Sort-Algorithmus
In der for-Schleife wird in der Variablen j jede Position der Liste durchlaufen; das
j-te Element ( l [j ]) ist dabei immer derjenige Wert, der in den schon sortierten Teil
der Liste eingef ¨ugt werden soll. Die while-Schleife zwischen Zeile 5 und 7 durchl ¨auft
dabei den schon sortierten Teil der Liste auf der Suche nach der passenden Stelle i –
gleichzeitig werden die durchlaufenen Elemente nach ”rechts“ verschoben, um Platz f¨ur
den einzuf¨ugenden Wert zu schaﬀen.
2.1.3 Laufzeit
Machen wir uns Gedanken ¨uber die Laufzeit von Insertion Sort zur Sortierung einer
Liste der L¨ange n:
Worst Case. Im ”schlimmsten“ denkbaren Fall muss die bereits sortierte Liste immer
jeweils vollst¨andig durchlaufen werden, um die richtige Einf ¨ugeposition zu ﬁnden. Im
ersten Durchlauf hat die bereits sortierte Liste die L ¨ange 1, im zweiten Durchlauf die
L¨ange 2, usw. Im letzten, also ( n−1)-ten, Durchlauf hat die bereits sortierte Liste die
L¨ange n−1. Insgesamt erhalten wir also als Laufzeit Lworst(n) bei einer Eingabe der
Gr¨oße n:
Lworst(n) =
n−1∑
k=1
k= (n−1)n
2 = O(n2)
Best Case. Im g ¨unstigsten Fall gen ¨ugt immer nur ein Vergleich, um die Einf ¨ugepo-
sition in den schon sortierten Teil der Liste zu bestimmen. Da es insgesamt n −1

## Seite 35

20 2 Sortieralgorithmen
Schleifendurchl¨aufe gibt, erhalten wir also als Laufzeit Lbest(n) im besten Fall bei einer
Eingabe der Gr¨oße n
Lbest(n) =
n−1∑
k=1
1 = n−1 = O(n)
Average Case. Wird eine k-elementige schon sortierte Liste linear durchlaufen um
die richtige Einf ¨ugeposition f ¨ur ein neues Element zu suchen, so ist es im besten Fall
m¨oglich, dass man nur einen Vergleich ben ¨otigt; es ist m ¨oglich, dass man 2 Verglei-
che ben ¨otigt, usw. Schließlich ist es auch (im ung ¨unstigsten Fall) m ¨oglich, dass man
k Vergleiche ben¨otigt. Geht man davon aus, dass all diese M ¨oglichkeiten mit gleicher
Wahrscheinlichkeit auftreten, so kann man davon ausgehen, dass die Anzahl der Ver-
gleiche im Durchschnitt
1 + ··· + k
k = k(k+ 1)/2
k = k+ 1
2
betr¨agt, d. h. in jedem der insgesamt n−1 Durchl¨aufe werden im Durchschnitt k+1
2
Vergleiche ben¨otigt. Summiert ¨uber alle Durchl¨aufe erh¨alt man also
n−1∑
k=1
k+ 1
2 = 1
2
n−1∑
i=1
(k+ 1) = 1
2
n∑
i=2
k= 1
2
(n(n+ 1)
2 −1
)
= n2 + n−2
4
Somit gilt f¨ur die Laufzeit Lav(n) im Durchschnittsfall bei einer Eingabe der Gr ¨oße n
Lav(n) = O(n2)
Insertion Sort vs. Pythons sort -Funktion. Tabelle 2.1 zeigt die Laufzeiten des im
vorigen Abschnitt implementierten Insertion-Sort-Algorithmus insertionSort im Ver-
gleich zur Laufzeit von Pythons mitgelieferter Suchfunktion list . sort() – Pythons
Standard- Sortierfunktion – f¨ur die Sortierung einer Liste mit 50 000 zuf¨allig gew¨ahlten
long int -Zahlen. Wie kann Pythons Standard- Sortierfunktion so viel schneller sein?
Implementierung Laufzeit (in sek)
insertionSort 244.65
list.sort 0.01
Tabelle 2.1: Laufzeiten des im letzten Abschnitt implementierten Insertion Sort Algorith-
mus im Vergleich zu Pythons Standard-Sortierfunktion sort () f¨ur ein Eingabe-Liste mit 50 000
long int-Zahlen
Im n¨achsten Abschnitt machen wir uns Gedanken dar ¨uber, wie schnell ein Sortieralgo-
rithmus eine Liste von n Zahlen maximal sortieren kann.

## Seite 36

2.2 Mindestlaufzeit von Sortieralgorithmen 21
Aufgabe 2.2
Die Funktion insertionSort durchsucht die bereits sortierte Liste linear nach der
Position, an die das n¨achste Element eingef¨ugt werden kann. Kann man die Laufzeit
von insertionSort dadurch verbessern, dass man eine bin ¨are Suche zur Bestimmung
der Einf ¨ugeposition verwendet, die Suche also in der Mitte der sortierten Teilliste
beginnen l¨asst und dann, abh ¨angig davon, ob der Wert dort gr ¨oßer oder kleiner als
der einzuf¨ugende Wert ist, in der linken bzw. rechten H ¨alfte weitersucht, usw.?
Falls ja: Was h¨atte solch ein Insertion-Sort-Algorithmus f¨ur eine Laufzeit? Implemen-
tieren Sie Insertion Sort mit bin ¨arer Suche.
2.2 Mindestlaufzeit von Sortieralgorithmen
Will man eine Liste [ a0 , ... ,an−1 ] von nElementen sortieren, so k¨onnen alle Sortieral-
gorithmen, die vorab keine besonderen Informationen ¨uber die zu sortierenden Ele-
mente besitzen, nur aus Vergleichen zwischen Elementpaaren Informationen ¨uber deren
sortierte Anordnung gewinnen. Der Durchlauf eines jeden Sortieralgorithmus kann als
Entscheidungsbaum modelliert werden; jeder Durchlauf durch den Entscheidungsbaum
repr¨asentiert dabei die Vergleiche, die durch einen Sortieralgorithmus ausgef ¨uhrt wer-
den, w¨ahrend eine konkrete Liste sortiert wird. F¨ur solch einen Entscheidungsbaum, wie
etwa der in Abbildung 2.2 gezeigt, gilt: Jeder innere Knoten repr ¨asentiert einen Ver-
gleich; der linke Teilbaum behandelt den Fall, dass der Vergleich positiv ausf ¨allt, und
der rechte Teilbaum behandelt den Fall, dass der Vergleich negativ ausf¨allt. So sind im
linken Teilbaum des mit a0 <a1 beschrifteten Wurzelknotens des Entscheidungsbaums
aus Abbildung 2.2 nur noch Sortierungen denkbar, in denen das 0-te Element links vom
1-ten Element steht.
Jeder Vergleich halbiert die Anzahl der bis zu diesem Zeitpunkt noch denkbaren m¨ogli-
chen Sortierungen. Ist ein Blatt erreicht, so hat der Sortieralgorithmus die passende
Sortierung gefunden. Jedes Blatt ist mit einer Permutation der Indizes i= 0,...n −1
markiert, die der gefundenen Sortierung entspricht.
Aufgabe 2.3
Erstellen Sie einen Entscheidungsbaum, der die Funktionsweise von Insertion Sort
beschreibt, zum Sortieren einer 3-elementigen Liste.
Aufgabe 2.4
W¨urde Insertion Sort, was die get ¨atigten Vergleiche betriﬀt, so vorgehen, wie durch
den in Abbildung 2.2 gezeigten Entscheidungsbaum beschrieben?
Die Worst-Case-Komplexit¨at eines Sortieralgorithmus entspricht genau dem l ¨angsten
Pfad von der Wurzel zu einem Blatt im entsprechenden Entscheidungsbaum, in ande-

## Seite 37

22 2 Sortieralgorithmen
a0 <a1
a1 <a2 a1 <a2
a2 <a3 a0 <a2 a0 <a2 a2 <a3
a0 <a3 a0 <a3 a2 <a3 a2 <a3 a0 <a3 a1 <a3
a1 <a3 a2 <a3 a0 <a3 a0 <a3 a0 <a3
a1 <a3 a1 <a3
(2 0 3 1)
(0 1 2 3)
(0 1 3 2)
(3 0 1 2)
(0 3 1 2)
(0 2 1 3) (0 2 3 1) (2 0 1 3)
(0 3 2 1) (2 3 0 1)
(3 0 2 1) (1 0 2 3)
(1 0 3 2) a1 <a3
(1 3 0 2) (3 1 0 2)
(1 2 0 3) a2 <a3
a1 <a3(1 2 3 0)
(1 3 2 0) (3 1 2 0)
(2 1 3 0)
(3 2 1 0)
(2 3 1 0)
(2 1 0 3)
(3 2 0 1)
Abb. 2.2:Ein m¨oglicher Entscheidungsbaum, der modelliert, welche Vergleiche notwendig sind,
um eine Liste [ a0 ,a1 ,a2 ,a3 ] der L ¨ange n= 4zu sortieren. An den Bl ¨attern beﬁnden sich alle
n! m¨oglichen Permutation. Ein Entscheidungsbaum zum Sortieren einer 4-elementigen Liste
muss eine Tiefe von mindestens ⌈log2 4!⌉= 5haben. Der gezeigte Entscheidungsbaum hat eine
Tiefe von 6, ist also in diesem Sinne nicht optimal.
ren Worten: die Worst-Case-Komplexit¨at entspricht der Tiefe des Entscheidungsbaums.
Ein Entscheidungsbaum, der die Sortierung einern-elementigen Liste modelliert, besitzt
n! Bl¨atter, d. h. er besitzt mindestens eine Tiefe von ⌈log2 n!⌉. Die ber ¨uhmte Stirling-
Formel zeigt uns, welches Wachstumsverhalten log2 n! besitzt. Die Stirling-Formel be-
sagt, dass n! f¨ur große n genauso schnell w ¨achst wie
√
2πn·(n/e)n, und zwar in dem
Sinne, dass gilt:
lim
n→∞
n!√
2πn·(n/e)n = 1
Somit ergibt sich als untere Schranke f ¨ur die Worst-Case-Komplexit¨at Lworst(n) eines
beliebigen Sortieralgorithmus
Lworst(n) ≥⌈log 2 n!⌉= O(log2 (
√
2πn·
(n
e
)n
))
= O(1
2 log2 2πn+ nlog2
n
e)
= O(log n) + O(nlog n) = O(nlog n)
2.3 Quicksort
Quicksort geh¨ort zur Klasse der sog Divide-And-Conquer-Algorithmen. Bevor wir die
Funktionsweise von Quicksort beschreiben, gehen wir in folgendem Abschnitt kurz auf
die Besonderheiten dieser Algorithmen ein.
2.3.1 Divide-And-Conquer-Algorithmen
”Divide et Impera“ (deutsch: Teile und Herrsche; englisch: Divide and Conquer) war Ju-
lius C¨asars erfolgreiche Strategie ein großes un¨uberschaubares Reich zu beherrschen. Ein

## Seite 38

2.3 Quicksort 23
Divide-And-Conquer-Algorithmus teilt ein Problem p der Gr¨oße n in mehrere kleinere
Teilprobleme tp0,...tp k−1 auf (h¨auﬁg ist, wie auch im Falle des Quicksort-Algorithmus,
k = 2); diese Teilprobleme werden rekursiv gel ¨ost und die so entstandenen Teill ¨osun-
gen tl0,...tl k−1 werden schließlich zu einer Gesamtl ¨osung zusammengef¨ugt. Folgendes
Listing formuliert dies nochmals in Python:
def divideAndConquer(p):
(tp0,...,tp k−1) =dividek(p)
tl0 = divideAndConquer(tp0)
... = ...
tlk−1 = divideAndConquer(tpk−1)
return combinek(tl0,...,tl k−1)
Die Laufzeit L(n) eines Divide-And-Conquer-Algorithmus kann am nat¨urlichsten durch
eine sog. Rekurrenzgleichung ausgedr¨uckt werden – wir nehmen hierbei der Einfachheit
halber an, dass der divide-Schritt das Problem in k gleichgroße Teile der Gr ¨oße n/k
zerlegt; Ldiv sei die Laufzeit der divide-Funktion, Lcomb sei die Laufzeit des combine-
Schritts.
L(n) = Ldiv(n) + k·L(n
k) + Lcomb(n)
2.3.2 Funktionsweise von Quicksort
Das Vorgehen von Quicksort bei der Sortierung einer Liste lst= [ a0 ,a1 , ... ,an−1 ] der
L¨ange n kann folgendermaßen beschrieben werden:
1. Quicksort w ¨ahlt zun¨achst ein beliebiges Element lst[j] mit 0 ≤j ≤n−1 aus der
zu sortierenden Liste lst aus. Dieses Element wird Pivot-Element genannt.
2. Der divide-Schritt: Quicksort zerteilt nun die Liste lst in zwei Teil-Listen lst l
und lst r . Die ”linke“ Teil-Liste lst l enth¨alt alle Elemente aus lst , deren Werte
kleiner (oder gleich) dem Pivotelement lst j sind; die ”rechte“ Teil-Liste enth¨alt
alle Elemente aus lst , deren Werte gr¨oßer dem Pivotelement lst j sind.
3. Die Listen lst l und lst r werden rekursiv mit Quicksort sortiert.
4. Der combine-Schritt: Die rekursiv sortierten Teil-Listen werden einfach zusam-
mengeh¨angt; das Pivotelement kommt dabei in die Mitte.
Diese Beschreibung der rekursiven Vorgehensweise l¨asst sich mittels zweier Listenkom-
prehensionen und entsprechender rekursiver Aufrufe direkt in Python implementieren:
Die Listenkomprehension [ x for x in lst [1 :] if x≤pivot ] berechnet hierbei die linke
Teilliste und die Listenkomprehension [ x for x in lst [1 :] if x>pivot] berechnet die
rechte Teilliste. Listing 2.4 zeigt die Implementierung.

## Seite 39

24 2 Sortieralgorithmen
1 def quicksort( lst ):
2 if len( lst )≤1: return lst # Rekursionsabbruch
3 pivot = lst [0]
4 lst l = [a for a in lst [1: ] if a ≤ pivot ]
5 lst r = [a for a in lst [1: ] if a > pivot ]
6 return quicksort( lst l ) + [pivot ] + quicksort( lst r )
Listing 2.4: Implementierung von Quicksort
Abbildung 2.3 zeigt als Beispiel die Ausf ¨uhrung von Quicksort veranschaulicht durch
zwei zusammengesetzte Bin¨arb¨aume; der obere Bin ¨arbaum modelliert den Rekursions-
abstieg, der untere Bin¨arbaum den Rekursionsaufstieg. Eine alternative aber ganz ¨ahn-
liche graphische Veranschaulichung der Ausf¨uhrung von Quicksort angewandt auf die-
selbe Liste ist in Abbildung 2.4 gezeigt.
[7,11,5,18] [29,31,23,21,67]
[11,18][5] [23,21] [31,67]
[18] [21] [] [] [67]
[]+[11]+[18] [21]+[23]+[] []+[31]+[67]
[21,23]+[29]+[31,67][5]+[7]+[11,18]
[5,7,11,18]+[19]+[21,23,29,31,67]
[]
Rek.-Abbruch
Aufstieg
Rek.-
Rek.-
Abstieg
[19,29,31,7,11,23,5,18,21,67]
Abb. 2.3:Darstellung der Funktionsweise von Quicksort am Beispiel der Sortierung der Liste
[ 19,29,31,7,11,23,5,18,21,67 ]dargestellt durch zwei zusammengesetzte Bin ¨arb¨aume, getrennt
mit einer gestrichelten Linie, die den Rekursionsabbruch markiert. F ¨ur jeden mit einer Li-
ste lst markierten Knoten im oberen Bin ¨arbaum gilt: Der linke Teilbaum modelliert den re-
kursiven Aufruf quicksort ( lst l ) und der rechte Teilbaum modelliert den rekursiven Aufruf
quicksort( lst r ). Der Weg von der Wurzel des oberen Bin ¨arbaums zu den Bl ¨attern markiert
also den rekursiven Abstieg. Die Pivot-Elemente der Listen sind jeweils mit einem kleinen Pfeil
markiert. Eine Verzweigung im unteren Bin¨arbaum entspricht einem combine-Schritt, der zwei
sortierte Listen samt dem Pivot-Element zu einer Gesamtl ¨osung zusammensetzt.
Aufgabe 2.5
Um quicksort noch kompakter zu implementieren, verwenden Sie die Hilfsfunktion:
def o(x,s) : return [i for i in x if cmp(i,x[0])==s ]
(ein Funktions-Body mit nur einer Zeile ist m ¨oglich!)

## Seite 40

2.3 Quicksort 25
pivot=19
pivot=7
return qs([5])+[7]+qs([11,18])
=[5]
qs([19,29,31,7,11,23,5,18,21,2,67])
+ [19] + qs([29,31,23,21,67])
pivot=29
=
return qs([23,21]) +[29]+ qs([31,67])
pivot=31
return qs([])+[31]+qs([67])
=[] =[67]
=
= [21,23] +[29]+
[] +[31]+ [67]
[31,67]
[5,7,11,18]= +[19]+
lst l=[7,11,5,18]
lst r=[29,31,23,21,67]
lst l=[5]
lst r=[11,18]
lst l=[23,21]
lst r=[31,67]
pivot=23
return qs([21])+[23]+qs([])
=[21] =[]
[]+[23]+[21]
lst l=[21]
lst r=[]
lst l=[]
lst r=[67]
+[7]+[5]= [11,18]
return qs([7,11,5,18])
=[] =[18]
= [] [18]+[11]+
pivot=11
return qs([])+[11]+qs([18])
lst l=[]
lst r=[18]
[21,23,29,31,67]
Abb. 2.4: Darstellung der Funktionsweise von Quicksort am Beispiel der Sortierung der Liste [ 19,29,31,7,11,23,5,18,21,2,67 ] dar-
gestellt durch die ausgef ¨uhrten Kommandos und die Hierarchie der rekursiven Aufrufe. Die Ausdr ¨ucke, die den rekursiven Abstieg
einleiten (also die rekursiven Aufrufe initiieren), sind schwarz umrandet; die berechneten Werte dieser Ausdr ¨ucke, nachdem sie im
rekursiven Aufstieg bestimmt wurden, sind grau umrandet.

## Seite 41

26 2 Sortieralgorithmen
2.3.3 Laufzeit
Der g¨unstigste Fall entsteht dann, wenn die gew¨ahlten Pivotelemente die Listen immer
in jeweils zwei gleichgroße Teillisten aufteilen. In diesem Fall ist die Laufzeit Lbest(n)
von Quicksort:
Lbest(n) = 2 ·Lbest(n/2) + Ldiv(n) + Lcomb(n)  
O(n)
wobei Ldiv(n) die Laufzeit der Aufteilung in die beiden Teillisten darstellt undLcomb(n)
die Laufzeit der Kombination der rekursiv sortieren Teillisten darstellt. Die L ¨osung
dieser Rekurrenz-Gleichung ist O(nlog n) und damit ist die Laufzeit im bestm ¨oglichen
Fall in O(nlog n).
Interessanter ist jedoch der Average-Case-Fall:
Average Case. Wir gehen davon aus, dass die Wahrscheinlichkeit, dass das Pivot-
Element das i-kleinste Element von insgesamt n-Elementen ist, 1/n betr¨agt; d. h. wir
gehen hier von einer Gleichverteilung aus. Wird dasi-kleinste Element als Pivot-Element
gew¨ahlt, so hat die linke Teilliste eine Gr¨oße von i−1 und die rechte Teilliste eine Gr¨oße
von n−i; f¨ur die Average-Case-Laufzeit Lav(n) zur Sortierung einer n-elementigen Liste
durch die in Listing 2.4 gezeigte Funktion quicksort ergibt sich f ¨ur die Average-Case-
Laufzeit Lav(n) also folgende Rekurrenz-Gleichung:
Lav(n) = (n−1)
 
Partition
+ 1
n ·
n∑
i=1
(Lav(i−1) + Lav(n−i)) + 2
+-Ops
(2.1)
Da
n∑
i=1
(Lav(i−1) + Lav(n−i)) = Lav(0) + ... + Lav(n−1) + Lav(n−1) + ... + Lav(0)
– also jeder Term Lav(i) in der Summe zweimal vorkommt – kann man die Rekurrenz-
Gleichung (2.1) folgendermaßen vereinfachen:
Lav(n) = (n+ 1) + 2
n ·
n−1∑
i=0
Lav(i) (2.2)
Auf den ersten Blick scheint die Rekurrenz-Gleichung (2.2) schwer aufzul ¨osen; mit ei-
nigen ”Tricks“ ist sie aber einfacher in den Griﬀ zu bekommen, als so manch andere
Rekurrenz-Gleichung. Wir multiplizieren Lav(n+ 1) mit n+ 1 und Lav(n) mit n:
(n+ 1)Lav(n+ 1) = (n + 1)(n+ 2) + 2(n+ 1)
n+ 1
n∑
i=0
Lav(i) und
nLav(n) = n(n+ 1) + 2n
n
n−1∑
i=0
Lav(i)

## Seite 42

2.3 Quicksort 27
Zieht man nun vom (n+ 1)-fachen von Lav(n+ 1) das n-fache von Lav(n) ab, so erh¨alt
man eine einfachere Rekurrenz-Gleichung:
(n+ 1)Lav(n+ 1) −nLav(n) = 2(n + 1) + 2Lav(n) ⇐⇒
(n+ 1)Lav(n+ 1) = 2(n + 1) + (n+ 2)Lav(n)
Der Trick besteht nun darin, auf beiden Seiten 1 /(n+ 1)(n+ 2) zu multiplizieren; wir
erhalten dann:
Lav(n+ 1)/(n+ 2) = 2/(n+ 2) +Lav(n)/(n+ 1)
und solch eine Rekurrenz kann man einfach durch eine entsprechende Summation er-
setzen:
Lav(n)
(n+ 1) = 2
n+ 1 + 2
n + ... + Lav(0)
1  
=1
Um m¨oglichst unkompliziert einen konkreten Wert aus dieser Formel zu erhalten, kann
man diese Summe durch ein entsprechendes Integral approximieren und erh ¨alt dann:
2
n+1∑
i=1
1
i ≈2 ·
∫ n
1
1
xdx= 2 ·ln n= 2 ·log2 n
log2 e ≈1,386 log2 n
Insgesamt erhalten wir also konkret im Durchschnitt
Lav(n) ≈1.386nlog2 n
Vergleiche bei Quicksort bei einer zu sortierenden Eingabe der L ¨ange n. Dies ist –
zumindest was die Anzahl der Vergleiche betriﬀt – nur etwa 38.6%¨uber dem theoretisch
m¨oglichen Optimum.
2.3.4 In-Place-Implementierung
Wir stellen hier eine Quicksort-Implementierung vor, die keine neuen Listen anlegt, also
keinen zus¨atzlichen Speicher verwendet und entsprechend etwas performanter ist. Der
vorgestellte Algorithmus wird deutlich komplexer sein, als die in Listing 2.4 vorgestell-
te nicht-destruktive Implementierung. Wir teilen daher den Quicksort-Algorithmus in
zwei Teile auf: Zum Einen in die Funktion partitionIP, die den divide-Schritt ausf¨uhrt;
zum Anderen in eine Funktion quicksort, die eine Liste durch wiederholten Aufruf von
partitionIP sortiert.
Die in Listing 2.5 vorgestellte Funktion partitionIP bekommt neben der zu partitio-
nierenden Liste lst noch den Teil der Liste – mittels Indizes l und r – ¨ubergeben,
der partitioniert werden soll. Der Grund daf ¨ur, dass bei der In-Place-Implementierung
zus¨atzlich Bereiche mit ¨ubergeben werden, liegt darin, dass alle Aufrufe immer auf der
gesamten zu sortierenden Liste arbeiten; es muss entsprechend immer noch Information
mit ¨ubergeben werden auf welchem Bereich der Liste im jeweiligen Aufruf gearbeitet
wird.

## Seite 43

28 2 Sortieralgorithmen
1 def partitionIP( lst , l ,r ):
2 pivot=lst [l ]
3 i=l -1
4 j=r +1
5 while True:
6 while True:
7 j=j -1
8 if lst [j ]≤pivot : break
9 while True:
10 i=i +1
11 if lst [i ]≥pivot : break
12 if i<j:
13 lst [i ], lst [j ]=lst [j ], lst [i ]
14 else:
15 return j
Listing 2.5:C.A.R. Hoare’s urspr¨unglich vorgeschlagene Implementierung[10] einer In-Place-
Partition zur Verwendung mit Quicksort.
Auch hier wird zun ¨achst ein Pivot-Element pivot gew¨ahlt, und zwar (genau wie in
der nicht-destruktiven Implementierung) das Element, das sich am linken Rand des
zu partitionierenden Bereichs beﬁndet (Zeile 1: pivot=lst [l ]). Der Z ¨ahler j l¨auft vom
rechten Rand des Bereiches und der Z¨ahler i l¨auft vom linken Rand des Bereiches ¨uber
lst ; die beiden inneren ”while True“-Schleifen bewirken Folgendes:
 Nach Durchlaufen der ersten inneren ”while True“-Schleife (Zeilen 6-8) steht j
auf einem lst -Element, das kleiner-gleich dem Pivot-Element ist.
 Nach Durchlaufen der zweiten inneren ”while True“-Schleife (Zeilen 9-11) steht
i auf einem lst -Element, das gr¨oßer-gleich dem Pivot-Element ist.
Nun m¨ussen lst [i ] und lst [j ] getauscht werden – dies geschieht in Zeile 13. Falls i ≥j,
so wurde der zu partitionierende Bereich vollst¨andig durchlaufen und die Partitionierung
ist beendet. Der R ¨uckgabewert j markiert die Grenze zwischen der linken und der
rechten Partition.
Die Abbildung 2.5 veranschaulicht die Funktionsweise von partitionIP nochmals gra-
phisch.
Der eigentliche Quicksort-Algorithmus kann nun mit Hilfe der Funktion partitionIP
einfach implementiert werden:
1 def quicksortIP( lst , l ,r ):
2 if r>l:
3 i = partitionIP(lst , l ,r)
4 quicksortIP( lst , l , i)
5 quicksortIP( lst , i +1,r)

## Seite 44

2.3 Quicksort 29
[19,29,31,7,11,23,5,18,21,2,67]
[19,29,31,7,11,23,5,18,21,2,67]
[2,29,31,7,11,23,5,18,21,19,67]
[2,18,31,7,11,23,5,29,21,19,67]4. Durchlauf:
5. Durchlauf: [2,18,5,7,11,23,31,29,21,19,67]
Da nun j ≤i=⇒Schleifenabbruch
3. Durchlauf:
2. Durchlauf:
1. Durchlauf:
j = 11i= −1
i= 0 j = 8
j = 5
i= 1
i= 2
j = 6
j = 4 i= 5
Abb. 2.5: Darstellung der Funktionsweise von partitionIP am Beispiel der Sortierung der
Partitionierung der Liste [ 19,29,31,7,11,23,5,18,21,2,67 ]. Die ¨außere ”while True“-Schleife
wird dabei f¨unf Mal durchlaufen.
Aufgabe 2.6
Implementieren Sie eine randomisierte Variante von Quicksort
quicksortRandomisiert(lst , l ,r)
die eine H ¨aufung ung¨unstiger F¨alle dadurch vermeidet, dass das Pivot-Element der
Partitionierung von lst [l :r +1] zuf ¨allig aus den Indizes zwischen (einschließlich) l
und r gew¨ahlt wird.
Aufgabe 2.7
Implementieren Sie eine weitere randomisierte Variante von Quicksort
quicksortMedian(lst, l ,r)
die das Pivotelement folgendermaßen w ¨ahlt:
 Es werden zun¨achst drei zuf¨allige Elemente aus der zu partitionierenden Liste
(also aus lst [l :r +1]) gew ¨ahlt.
 Als Pivot-Element wird der Median – also das mittlere der zuf ¨allig gew¨ahlten
Elemente – ausgew¨ahlt.

## Seite 45

30 2 Sortieralgorithmen
Aufgabe 2.8
Vergleichen Sie nun die Algorithmen quicksortIP, quicksortRandomisiert und
quicksortMedian folgendermaßen:
 Generieren Sie 100 zuf ¨allig erzeugte 10.000-elementige Listen, die Werte aus
{1,... 100.000}enthalten und lassen sie diese 100 Listen durch die drei Quicksort-
Varianten sortieren.
 ”Merken“ Sie sich f¨ur jeden der Algorithmen jeweils die folgenden Daten:
1. Die durchschnittliche Zeit, die der jeweilige Algorithmus zum Sortieren
einer 10.000-elementigen Liste brauchte.
2. Die – aus den 100 Sortierdurchl ¨aufen – schnellste Zeit, die der jeweilige
Algorithmus zum Sortieren einer 10.000-elementigen Liste brauchte.
3. Die – aus den 100 Sortierdurchl ¨aufen – langsamste Zeit, die der jeweilige
Algorithmus zum Sortieren einer 10.000-elementigen Liste brauchte.
Bemerkung: Zum Erzeugen einer Liste mit zuf ¨allig gew¨ahlten Elementen k¨onnen Sie
das Python-Modul random verwenden. Der Aufruf random.randint(a,b) liefert eine
zuf¨allige int-Zahl zwischen einschließlich a und b zur¨uck.
Zur Zeitmessung k ¨onnen Sie das Python-Modul time verwenden. Der Aufruf
time.time() (unter Windows besser:time.clock()) liefert die aktuelle CPU-Zeit zur¨uck.
2.3.5 Eliminierung der Rekursion
Ein Performance-Gewinn kann durch die ¨Uberf¨uhrung der rekursiven Quicksort-Imple-
mentierung in eine iterative Implementierung erzielt werden. Warum aber ist ein itera-
tiver Algorithmus unter Umst¨anden schneller? Das h ¨angt damit zusammen, dass jeder
Unterprogrammaufruf mit relativ hohen Rechen ”kosten“ verbunden ist; bei jedem Un-
terprogrammaufruf wird ein neuer Stackframe auf dem Rechner-internen Stack erzeugt,
der alle notwendigen Informationen ¨uber das aufgerufene Unterprogramm enth ¨alt; da-
zu geh ¨oren unter Anderem die R ¨ucksprungadresse zur aufrufenden Prozedur, Werte
der lokalen Variablen und die Werte der ¨ubergebenen Parameter. Da das Anlegen eines
Stackframes viele Zugriﬀe auf den Hauptspeicher erfordert und da Hauptspeicherzu-
griﬀe im Verh¨altnis zu anderen CPU-internen Operationen sehr teuer sind, kann eine
Eliminierung der Rekursion die Performance steigern.
Anders als bei einer rekursiven Implementierung von beispielsweise der Fakult¨atsfunkti-
on, kann die Rekursion bei Quicksort jedoch nicht durch eine einfache Schleife aufgel¨ost
werden. Der Stack, der bei jedem Prozeduraufruf (insbesondere bei rekursiven Proze-
duraufrufen) verwendet wird, muss hier explizit modelliert werden, wenn die Rekursion
beseitigt werden soll. Auf dem Stack ”merkt“ sich der rekursive Quicksort (unter Ande-
rem) welche Arbeiten noch zu erledigen sind. Abbildung 2.6 zeigt nochmals im Detail,
wie sich der Programmstack bei jedem rekursiven Aufruf erh¨oht und wie sich der Stack
bei jedem R¨ucksprung aus einer Quicksort-Prozedur wieder verkleinert. Man sieht, dass

## Seite 46

2.3 Quicksort 31
die jeweiligen Stackframes die Informationen enthalten, welche Stackframes zu einem
evtl. sp¨ateren Zeitpunkt noch anzulegen sind.
Eliminieren wir die Rekursion, indem wir den Stack explizit modellieren, gibt uns das
mehr Kontrolle und Optimierungspotential: Zum Einen muss nicht jeder rekursive Auf-
ruf von Quicksort mit dem Speichern von Informationen auf dem Stack verbunden sein:
ein rekursiver Quicksort-Aufruf, der am Ende der Quicksort-Prozedur erfolgt, muss
nichts ”merken“, denn nach diesem Aufruf ist nichts mehr zu tun (denn die aufrufende
Prozedur ist danach ja zu Ende). Solche sog. endrekursiven Aufrufe (im Englischen als
tail-recursive bezeichnet) kann man einfach Eliminieren und durch Iteration ersetzten.
Nur die nicht end-rekursiven Aufrufe m¨ussen sich diejenigen Aufgaben auf einem Stack
merken, die nach Ihrer Ausf ¨uhrung noch zu erledigen sind.
Das folgende Listing 2.6 zeigt eine Quicksort-Implementierung ohne Verwendung von
Rekursion. Der Stack wird durch eine Liste modelliert; eine push-Operation entspricht
einfach der list .append-Methode, also dem Anf ¨ugen ans Ende der Liste; die pop-
Operation entspricht der list .pop-Methode, also dem Entnehmen des letzten Elements.
1 def quicksortIter ( lst ):
2 l=0
3 r=len(lst) -1
4 stack = []
5 while True:
6 while r>l:
7 i = partitionIP(lst , l ,r)
8 stack.append(i +1)
9 stack.append(r)
10 r=i
11 if stack==[]: break
12 r = stack.pop()
13 l = stack.pop()
Listing 2.6: Eine nicht-rekursive Implementierung von Quicksort unter Verwendung eines
expliziten Stacks
Die Funktion quicksortIter f¨uhrt im ersten Durchlauf der inneren Schleife das Kom-
mando
partitionIP( lst ,0, len( lst -1))
aus. Die push-Operationen in den Zeilen 8 und 9 ”merken“ sich die Grenzen der rechten
Teilliste; so kann die rechte Teilliste zu einem sp ¨ateren Zeitpunkt bearbeitet werden.
Mittels der Zuweisung r=i in Zeile 10 sind f ¨ur den n¨achsten Schleifendurchlauf die Li-
stengrenzen auf die linke Teilliste gesetzt. Es werden nun solange wie m ¨oglich (n¨amlich
bis r≥i, was in Zeile 6 getestet wird) linke Teillisten partitioniert. Anschließend holt
sich der Algorithmus die Grenzen der als N ¨achstes zu partitionierenden Teilliste vom
Stack; die geschieht mittels der beiden stack.pop()-Operationen in den Zeilen 12 und
13.

## Seite 47

32 2 Sortieralgorithmen
lst l=[]
pivot=2
lst r=[]
Stackframe1
Stackframe2
Stackframe3
Stackframe5
Stackframe6
Stackframe4
Stackframe0
pivot=19
qs([19,3,24,36,2,12])
lst l=[3,2,12]
lst r=[24,36]
pivot=3
lst l=[2]
lst r=[12]
→Aufruf von qs[3,2,12]
→Aufruf von qs[2]
→Aufruf von qs[]
...
...
...
...
→Aufruf von qs[]
→Aufruf von qs[12]
...
...
...
...
...
→push Stackframe0
→push Stackframe2
→pop Stackframe3
→pop Stackframe4
→pop Stackframe2
→pop Stackframe5
→pop Stackframe1
→pop Stackframe0
Stackframe0
Stackframe1
→push Stackframe1 Stackframe0
Stackframe0
Stackframe1
Stackframe2
Stackframe3
Stackframe2
Stackframe1
Stackframe0
Stackframe4
Stackframe2
Stackframe1
Stackframe0
Stackframe5
Stackframe1
Stackframe0
Stackframe6
Stackframe0
→pop Stackframe6 Stackframe0
→push Stackframe3
→push Stackframe5
→push Stackframe4
→Aufruf von qs[24,36] →push Stackframe6
Abb. 2.6:Darstellung der Aufrufhierarchie der rekursiven Instanzen des Quicksortalgorithmus
qs, ¨ahnlich dargestellt wie in Abbildung 2.4 nur diesmal linear in zeitlicher Reihenfolge und mit
dem jeweiligen Zustand des Programmstacks bei jedem rekursiven Aufruf von Quicksort. Wie
man sieht, ”merkt“ sich jede Instanz von Quicksort in ihrem jeweiligen Stackframe, welche
Arbeit sp¨ater noch zu erledigen ist. Der Aufruf qs( [ 19,3,24,36,2,12 ]) beispielsweise ruft rekur-
siv qs( [3,2,12 ]) auf; der Stackframe 0 enth¨alt implizit die Information, dass zu einem sp ¨ateren
Zeitpunkt noch der Aufruf qs( [24,36]) zu erledigen ist.

## Seite 48

2.4 Mergesort 33
Aufgabe 2.9
Vergleichen Sie die Laufzeiten von quicksortIter und quicksortIP miteinander. Er-
kl¨aren Sie Ihre Beobachtungen.
Aufgabe 2.10
(a) Wie viele Eintr ¨age k ¨onnte der Stack im Laufe der Sortierung einer Liste der
L¨ange n mittels der Funktion quicksortIter im ung¨unstigsten Falle haben?
(b) Man kann die Gr ¨oße des Stacks dadurch optimieren, indem man immer die
gr¨oßere der beiden entstehenden Teillisten auf dem Stack ablegt. Wie groß kann
dann der Stack maximal werden?
(c) Schreiben sie die Sortierfunktion quicksortIterMinStack so, dass immer nur die
gr¨oßere der beiden Teillisten auf dem Stack abgelegt wird und vergleichen sie
anschließend die Laufzeiten vom quicksortIter und quicksortIterMinStack.
2.4 Mergesort
Mergesort verwendet – wie Quicksort auch – einen klassischen Divide-And-Conquer
Ansatz zum Sortieren einer Liste lst . Wir erinnern uns, dass im divide-Schritt von
Quicksort der eigentliche Aufwand steckt; um die Liste zu teilen m¨ussen viele Vergleiche
ausgef¨uhrt werden. Der combine-Schritt dagegen ist bei Quicksort einfach: die beiden
rekursiv sortierten Teillisten mussten lediglich aneinander geh ¨angt werden.
Die Situation bei Mergesort ist genau umgekehrt. Bei Mergesort ist der divide-Schritt
einfach: hier wird die Liste einfach in der Mitte geteilt. Der eigentliche Aufwand steckt
hier im combine-Schritt, der die beiden rekursiv sortierten Listen zu einer großen sor-
tierten Liste kombinieren muss. Dies geschieht im”Reißverschlussverfahren“: die beiden
Listen m¨ussen so ineinander verzahnt werden, dass daraus eine sortierte Liste entsteht.
Dies wird in der englischsprachigen Literatur i. A. alsmerging bezeichnet. Das in Listing
2.7 gezeigte Python-Programm implementiert den Mergesort-Algorithmus.
1 def mergesort(lst ):
2 if len( lst )≤1: return lst
3 l1 = lst [: len( lst )/2]
4 l2 = lst [len( lst )/2: ]
5 return merge(mergesort(l1),mergesort(l2))
6
7 def merge(l1,l2 ):
8 if l1==[]: return l2
9 if l2==[]: return l1
10 if l1 [0] ≤l2 [0]: return [l1[0]] +merge(l1[1:],l2)
11 else: return [l2[0]] +merge(l1,l2[1:])
Listing 2.7: Implementierung von Mergesort

## Seite 49

34 2 Sortieralgorithmen
Aufgabe 2.11
Geben Sie eine iterative Variante der Funktion merge an.
2.5 Heapsort und Priority Search Queues
Ein Heap ist ein fast vollst ¨andiger1 Bin¨arbaum mit der folgenden Eigenschaft: Der
Schl¨ussel eines Knotens ist gr ¨oßer als die Schl ¨ussel seiner beiden Kinder. Einen sol-
chen Bin ¨arbaum nennt man auch oft Max-Heap und die eben erw ¨ahnte Eigenschaft
entsprechend die Max-Heap-Eigenschaft. Dagegen ist ein Min-Heap ein vollst ¨andiger
Bin¨arbaum, dessen Knoten die Min-Heap-Eigenschaft erf¨ullen: Der Schl ¨ussel eines Kno-
tens muss also kleiner sein als die Schl ¨ussel seiner beiden Kinder.
Abbildung 2.7 zeigt jeweils ein Beispiel eines Min-Heaps und eines Max-Heaps.
23
18
19
21
9 7 5
3 642
(a) Ein Max-Heap.
23
71
64
13
3829 98
3995 33 77 76 82 99 (b) Ein Min-Heap.
Abb. 2.7: Beispiel eines Min-Heaps und eines Max-Heaps: Beides sind bin ¨are B¨aume, die
der Min-Heap- bzw. Max-Heap-Bedingung gen ¨ugen. Im Falle des Max-Heaps lautet die Heap-
bedingung: ”Der Schl¨ussel jedes Knotens ist gr ¨oßer als die Schl ¨ussel seiner beiden Kinder“. Im
Falle des Min-Heaps lautet die Heapbedingung: ”Der Schl¨ussel jedes Knotens ist kleiner als die
Schl¨ussel seiner beiden Kinder“.
2.5.1 Repr ¨asentation von Heaps
Man k ¨onnte Heaps explizit als Baumstruktur repr ¨asentieren – ¨ahnlich etwa wie man
einen bin¨aren Suchbaum repr¨asentieren w¨urde (siehe Abschnitt 3.1). Heaps sind jedoch
per Deﬁnition vollst¨andige Bin¨arb¨aume (d. h. innere Knoten besitzen genau zwei Nach-
folger), haben also eine statische Struktur und k¨onnen somit Ressourcen-schonender als
”ﬂache“ Liste repr¨asentiert werden; hierbei schreibt man die Eintr¨age des Heaps von der
Wurzel beginnend ebenenweise in die Liste, wobei die Eintr ¨age jeder Ebene von links
nach rechts durchlaufen werden. Wir werden gleich sehen, dass es bei der Repr ¨asenta-
tion von Heaps g¨unstig ist, den ersten Eintrag der repr¨asentierenden Liste freizuhalten.
Zwei Beispiele:
1Mit ”fast vollst¨andig“ ist die folgende Eigenschaft gemeint: Alle ”Ebenen“ des Bin ¨arbaums sind
vollst¨andig gef¨ullt, bis auf die unterste Ebene; diese ist evtl. nur teilweise ”linksb¨undig“ gef¨ullt.

## Seite 50

2.5 Heapsort und Priority Search Queues 35
 Der Max-Heap aus Abbildung 2.7(a) wird durch folgende Liste repr ¨asentiert:
[None ,23,18,21,9,7,19,5,2,4,3,6 ]
 Der Min-Heap aus Abbildung 2.7(b) wird durch folgende Liste repr ¨asentiert:
[None ,13,23,64,29,38,71,98,95,33,77,39,76,82,99 ]
Repr¨asentiert man also einen Heap als Liste lst , so ist leicht nachvollziehbar, dass das
linke Kind von lst [i ] der Eintrag lst [2*i ] und das rechte Kind der Eintrag lst [2*i +1]
ist.
Aufgabe 2.12
Welche der folgenden Listen sind Repr¨asentationen von Min-Heaps bzw. Max-Heaps?
 [None,13]
 [None,100,99,98, ... ,1 ]
 [None ,100,40,99,1,2,89,45,0,1,85 ]
 [None,40,20,31,21]
Aufgabe 2.13
(a) Implementieren Sie die Funktion leftChild , die als Argument eine Liste lst und
einen Index i ¨ubergeben bekommt und, falls dieser existiert, den Wert des linken
Kindes von lst [i ] zur¨uckgibt; falls lst [i ] kein linkes Kind besitzt, soll leftChild
den Wert None zur¨uckliefern.
(b) Implementieren Sie die Funktion rightChild, die als Argument eine Liste lst
und einen Index i ¨ubergeben bekommt und, falls dieser existiert, den Wert des
rechten Kindes von lst [i ] zur¨uckgibt; falls lst [i ] kein rechtes Kind besitzt, soll
rightChild den Wert None zur¨uckliefern.
(c) Implementieren Sie eine Funktion father, die als Argument eine Liste lst und
einen Index i ¨ubergeben bekommt und den Wert des Vaters von lst [i ] zur¨uck-
liefert.
2.5.2 Heaps als Priority Search Queues
Es gibt viele Anwendungen, f¨ur die es wichtig ist, eﬃzient das gr¨oßte Element aus einer
Menge von Elementen zu extrahieren. Beispielsweise muss ein Betriebssystem st ¨andig
(und nat¨urlich unter Verwendung von m¨oglichst wenig Rechenressourcen) festlegen, wel-
cher Task bzw. welcher Prozess als N¨achstes mit der Ausf¨uhrung fortfahren darf. Dazu
muss der Prozess bzw. Task mit der h ¨ochsten Priorit¨at ausgew¨ahlt werden. Außerdem

## Seite 51

36 2 Sortieralgorithmen
kommen st¨andig neue Prozesse bzw. Tasks hinzu. Man k¨onnte die entsprechende Funk-
tionalit¨at dadurch gew¨ahrleisten, dass die Menge von Tasks nach jedem Einf ¨ugen eines
Elementes immer wieder sortiert wird, um dann das gr¨oßte Element eﬃzient extrahieren
zu k¨onnen; Heaps bieten jedoch eine eﬃzientere M ¨oglichkeit, dies zu implementieren.
H¨ohe eines bin ¨aren Heaps. F¨ur sp ¨atere Laufzeitbetrachtungen ist es wichtig zu
wissen, welche H¨ohe ein n-elementiger bin¨arer Heap hat. Auf der 0-ten Ebene hat eine
Heap 20 = 1 Elemente, auf der ersten Ebene 2 1 Elemente, usw. Ist also ein Heap der
H¨ohe h vollst¨andig gef¨ullt, so kann er
h−1∑
i=0
2i = 2h −1
Elemente fassen. Oder andersherum betrachtet: Ein vollst ¨andig gef ¨ullter Heap mit n
Elementen besitzt eine H ¨ohe von log2 n. Ist der Heap nicht ganz vollst ¨andig gef¨ullt, so
muss man bei der Berechnung der H ¨ohe entsprechend aufrunden. Es gilt also f ¨ur die
H¨ohe h eines Heaps mit n Elementen die folgende Beziehung:
h= ⌈log2 n⌉
Zu den wichtigsten Operationen auf Heaps geh ¨oren das Einf¨ugen eines neuen Elements
in einen Heap und die Extraktion (d. h. das Suchen und anschließende L ¨oschen) des
maximalen Elements bei Max-Heaps bzw. die Extraktion des minimalen Elements bei
Min-Heaps. Im Folgenden stellen wir die Implementierung dieser zwei Operationen f ¨ur
Min-Heaps vor.
Einf¨ugen. Soll ein neues Element in einen als Liste repr ¨asentierten bin¨aren Heap ein-
gef¨ugt werden, so wird es zun ¨achst an das Ende der Liste angef ¨ugt. Dadurch wird im
Allgemeinen die Heap-Eigenschaft verletzt. Um diese wiederherzustellen, wird das ein-
gef¨ugte Element sukzessive soweit wie n ¨otig nach ”oben“ transportiert. Abbildung 2.8
zeigt an einem Beispiel den Ablauf des Einf ¨ugens und das anschließenden Hochtrans-
portieren eines Elementes in einem Heap.
23
71
64
13
3829 98
3995 33 77 76 82 47
47
98
23
71
64
13
3829
3995 33 77 76 82 98
64
4723
71
13
3829
3995 33 77 76 82
Abb. 2.8: Das Element 47 wird in einen Heap eingef¨ugt. Anf¨anglich wird das Element ”hinten“
an den Heap angef ¨ugt (linkes Bild). Die Heapbedingung ist verletzt; daher wird das Element
sukzessive durch Tauschen nach oben transportiert und zwar solange bis die Heapbedingung
wieder erf¨ullt ist.

## Seite 52

2.5 Heapsort und Priority Search Queues 37
Listing 2.8 zeigt eine Implementierung der Einf ¨ugeoperation.
1 def insert(heap, x):
2 heap.append(x)
3 i = len(heap)-1
4 while heap[i/2]>heap [i]:
5 heap[i/2], heap[i ] = heap[i],heap[i/2]
6 i = i/2
Listing 2.8: Einf¨ugen eines Elementes in einen als Liste repr ¨asentierten Min-Heap
Wir gehen davon aus, dass die als Parameter ¨ubergebene Liste heap einen Heap re-
pr¨asentiert. Das einzuf¨ugende Element x wird zun¨achst hinten an den Heap angeh ¨angt
(heap.append(x) in Zeile 2); anschließend wird das eingef ¨ugte Element solange durch
Tausch mit dem jeweiligen Vaterknoten die Baumstruktur hochtransportiert, bis die
Heapbedingung erf¨ullt ist. Die while-Schleife wird hierbei solange ausgef ¨uhrt, wie der
Wert des eingef¨ugten Knotens kleiner ist, als der Wert seines Vaterknotens, d. h. solange
die Bedingung lst [i/2]>lst [i ] gilt.
Aufgabe 2.14
Die in Listing 2.8 gezeigte Implementierung der Einf ¨uge-Operation ist destruktiv
implementiert, d. h. der ¨ubergebene Parameter heap wird ver¨andert. Geben Sie ei-
ne alternative nicht-destruktive Implementierung der Einf¨ugeoperation an, die einen
”neuen“ Heap zur¨uckliefert, der das Element x zus¨atzlich enth¨alt.
Aufgabe 2.15
Wie arbeitet die Funktion insert, wenn das einzuf ¨ugende Element x kleiner ist als
die Wurzel des Heaps lst [1]? Spielen Sie den Algorithmus f ¨ur diesen Fall durch und
erkl¨aren Sie, warum er korrekt funktioniert.
Die H¨ohe des Heaps begrenzt hierbei die maximal notwendige Anzahl der Vergleichs-
und Tauschoperationen. Die Worst-Case-Laufzeit der Einf ¨ugeoperation eines Elements
in einen Heap mit n Elementen liegt also in O(log n).
Minimumsextraktion. Entfernt man das minimale Element, also die Wurzel, aus
einem Min-Heap, dann geht man am eﬃzientesten wie folgt vor: Das letzte Element
aus einer den Heap repr ¨asentierenden Liste heap, also heap[ -1], wird an die Stelle der
Wurzel gesetzt. Dies verletzt im Allgemeinen die Heap-Bedingung. Die Heap-Bedingung
kann wiederhergestellt werden, indem man dieses Element solange durch Tauschen mit
dem kleineren der beiden Kinder im Baum nach unten transportiert, bis die Heap-
Bedingung wiederhergestellt ist. Abbildung 2.9 veranschaulicht an einem Beispiel den
Ablauf einer solchen Minimumsextraktion.

## Seite 53

38 2 Sortieralgorithmen
72
72
29
72
72
2. 3.
4. 5.
1.
38
47
23
64
82 76 39 77 33 95
95 33 76 82
71
39 77
713829
23 47
64 29
95 33 77 39 76 82
7138
47
64
23
95
33
29
38
39 77 76 82
71
47
64
23
95 33 77 39 76 82 72
713829
23 47
64
13
Abb. 2.9: Ablauf einer Minimumsextraktion. 1: Das minimale Element des Heaps, das sich
aufgrund der Min-Heap-Bedingung immer an der Wurzel des Heaps beﬁndet, wird gel ¨oscht
und an dessen Stelle das ”letzte“ Element des Heaps gesetzt, in unserem Falle ist dies der
Knoten mit Schl ¨usselwert ”72“. 2: In Folge dessen, ist jedoch im unter 2. dargestellten Heap
die Heap-Bedingung verletzt. 3, 4, 5: Diese kann wiederhergestellt werden, indem man den
an der Wurzel beﬁndlichen Knoten durch Tausch-Operationen nach unten transportiert; und
zwar wird immer mit dem kleineren der beiden Kinder getauscht. Nach einigen solcher Tausch-
Operationen beﬁndet sich der Knoten mit Schl ¨usselwert ”72“ an der ”richtigen“ Position, d. h.
an einer Position, an der er die Heap-Bedingung nicht mehr verletzt – in diesem Falle wird er
zum Wurzelknoten.
Die in Listing 2.9 gezeigte FunktionminExtract implementiert die Minimumsextraktion.
In der Variablen n ist w¨ahrend des ganzen Programmablaufs immer der Index des ”letz-
ten“ Elements des Heaps gespeichert. In den Zeilen 3 und 4 wird das ”letzte“ Element
des Heaps an die Wurzel gesetzt. Die Durchl¨aufe der while-Schleife transportieren dann
das Wurzel-Element solange nach ”unten“, bis die Heap-Bedingung wieder erf ¨ullt ist.
Am Anfang der while-Schleife zeigt die Variable i immer auf das Element des Heaps,
das m¨oglicherweise die Heap-Bedingung noch verletzt. In Zeile 9 wird das kleinere seiner
beiden Kinder ausgew¨ahlt; falls dieses Kind gr¨oßer ist als das aktuelle Element, d. h. falls
lst [i ]≤lst [k ], so ist die Heap-Bedingung erf ¨ullt und die Schleife kann mittels break
abgebrochen werden. Falls jedoch dieses Kind kleiner ist als der aktuelle Knoten, ist
die Heapbedingung verletzt, und Vater und Kind m ¨ussen getauscht werden (Zeile 11).
Durch die Zuweisung i=j fahren wir im n ¨achsten while-Schleifendurchlauf damit fort,
den getauschten Knoten an die richtige Position zu bringen.

## Seite 54

2.5 Heapsort und Priority Search Queues 39
1 def minExtract(lst ):
2 returnVal=lst[1]
3 lst [1]= lst [ -1] # letztes Element an die Wurzel
4 del( lst [ -1])
5 n=len(lst) -1 # n zeigt auf das letzte Element
6 i=1
7 while i≤n/2:
8 j=2 *i
9 if j<n and lst[j]>lst[j +1]: j +=1 # w¨ahle kleineres der beiden Kinder
10 if lst [i ]≤lst [j ]: break
11 lst [i ], lst [j ]=lst [j ], lst [i ]
12 i=j
13 return returnVal
Listing 2.9:Implementierung der Minimumsextraktion, bei der das Wurzel-Element des Heaps
entfernt wird.
Was die Laufzeit der Minimumsextraktion betriﬀt, gilt ¨Ahnliches wie f ¨ur die Einf ¨uge-
Operation: Die H¨ohe des Heaps begrenzt die maximal notwendige Anzahl der Vergleichs-
und Tauschoperationen. Damit ist die Worst-Case-Laufzeit des AlgorithmusminExtract
in O(log n).
Aufgabe 2.16
Implementieren Sie die zwei Heap-Operationen ”Einf¨ugen“ und ”Maximumsextrak-
tion“ f¨ur Max-Heaps.
2.5.3 Konstruktion eines Heaps
Man kann Heaps f ¨ur den Entwurf eines eﬃzienten Sortieralgorithmus verwenden, der
bei der Sortierung einer Liste lst folgendermaßen vorgeht: Zun ¨achst wird lst in eine
Heapdatenstruktur umgewandelt. Anschließend wird mittels der Minimumsextraktion
ein Element nach dem anderen aus dem Heap entfernt und sortiert in die Liste hinten
eingef¨ugt. Verwendet man Min-Heaps, so kann man eine Liste absteigend sortieren;
verwendet man Max-Heaps, so kann man eine Liste aufsteigend sortieren.
Wenden wir uns zun ¨achst dem Aufbau einer Heapdatenstruktur aus einer gegebenen
beliebigen Liste lst zu. Man kann die hintere H¨alfte der Liste (also lst [len( lst )/2 :]) als
eine Sammlung von len( lst )/2 Heaps betrachten; nun m¨ussen wir ”nur“ noch ¨uber den
vorderen Teil der Liste laufen und alle verletzten Heap-Bedingungen wiederherstellen.
Wir programmieren zun¨achst eine Funktion, die f¨ur einen gegebenen Knoten die Heap-
bedingung herstellt; anschließend ist der eigentliche Heapsort-Algorithmus in einer ein-
fachen Schleife leicht zu programmieren. F¨ur die Herstellung der Heap-Bedingung gehen
wir so vor, wie schon in der while-Schleife aus Listing 2.9 implementiert: Die Knoten,

## Seite 55

40 2 Sortieralgorithmen
die die Heap-Bedingung verletzen, werden solange nach ”unten“ durchgereicht, bis die
Heap-Bedingung wiederhergestellt ist. Wir k¨onnten eigentlich die while-Schleife aus Li-
sting 2.9 ¨ubernehmen; der besseren ¨Ubersicht halber, verwenden wir aber die in Listing
2.10 vorgestellte rekursiv implementierte Funktion minHeapify.
1 def minHeapify(heap,i):
2 l = 2 *i
3 r = l +1
4 n = len(heap)-1
5 nodes = [(heap [v],v) for v in [i , l ,r ] if v≤n]
6 nodes.sort()
7 smallestIndex = nodes[0][1]
8 if smallestIndex ̸= i :
9 heap[i ], heap[smallestIndex ] = heap[smallestIndex ],heap[i]
10 minHeapify(heap,smallestIndex)
Listing 2.10: Die Funktion minHeapify, die den Knoten an Index i soweit sinken l ¨asst, bis
die Heap-Bedingung des Heaps ”heap“ wiederhergestellt ist.
Die Funktion minHeapify stellt die Heap-Bedingung, falls diese verletzt ist, f ¨ur den
Knoten an Index i des Heaps heap wieder her, und zwar dadurch, dass der Knoten
im Heap solange nach ”unten“ gereicht wird, bis die Heap-Bedingung wieder erf ¨ullt
ist. Die in Zeile 2 und 3 deﬁnierten Variablen l und r sind die Indizes der Kinder des
Knotens an Index i. In Zeile 5 wird mittels einer Listenkomprehension eine i. A. drei-
elementige Liste nodes aus den Werten des Knotens an Indexi und seiner beiden Kinder
erstellt; um den Knoten mit kleinstem Wert zu bestimmen, wird nodes sortiert; danach
beﬁndet sich der Wert des kleinsten Knotens in nodes[0][0] und der Index des kleinsten
Knotens in nodes[0][1]. Falls der Wert des Knotens i der kleinste der drei Werte ist, ist
die Heap-Bedingung erf ¨ullt und die Funktion minHeapify kann verlassen werden; falls
andererseits einer der Kinder einen kleineren Wert hat (d. h. falls smallestIndex̸=i), so
ist die Heap-Bedingung verletzt und der Knoten an Index i wird durch Tauschen mit
dem kleinsten Kind nach ”unten“ gereicht; anschließend wird rekursiv weiterverfahren.
Aufgabe 2.17
Verwenden Sie die in Listing 2.10 vorgestellte FunktionminHeapify, um die in Listing
2.9 programmierte while-Schleife zu ersetzen und so eine kompaktere Implementie-
rung der Funktion extraktHeap zu erhalten.

## Seite 56

2.5 Heapsort und Priority Search Queues 41
Aufgabe 2.18
Beantworten Sie folgende Fragen zu der in Listing 2.10 gezeigten FunktionminHeapify:
 In welchen Situationen gilt len(nodes)==3, in welchen Situationen gilt
len(nodes)==2 und in welchen Situationen gilt len(nodes)==1?
 K¨onnen Sie sich eine Situation vorstellen, in der len(nodes)==0 gilt? Erkl¨aren
Sie genau!
 Die Funktion minHeapify ist rekursiv deﬁniert. Wo beﬁndet sich der Rekursi-
onsabbruch? Und: In welcher Hinsicht ist das Argument des rekursiven Aufrufs
”kleiner“ als das entsprechende Argument in der aufrufenden Funktion.
Denn, wie in Abschnitt 1.2.1 auf Seite 6 besprochen, m ¨ussen die rekursiven Aufrufe ”kleine-
re“ (was auch immer ”kleiner“ im Einzelnen bedeutet) Argumente besitzen als die aufrufende
Funktion, um zu vermeiden, dass die Rekursion in einer Endlosschleife endet.
Aufgabe 2.19
Programmieren Sie eine Funktion maxHeapify, die als Argumente einen als Liste
repr¨asentierten Heap heap und einen Index i bekommt und die Max-Heap-Bedingung
des Knotens an Index i (bei Bedarf) wiederherstellt.
Aufgabe 2.20
Eliminieren Sie die Listenkomprehension in Zeile 5 und deren Sortierung in Zeile 6
und verwenden Sie stattdessen if-Anweisungen mit entsprechenden Vergleichen um
das kleinste der drei untersuchten Elemente zu bestimmen.
Aufgabe 2.21
Programmieren Sie nun eine iterative Variante der Funktion minHeapify; Sie k¨onnen
sich dabei an der while-Schleife aus Listing 2.9 orientieren.
Mittels minHeapify k¨onnen wir nun einfach eine Funktion schreiben, die einen Heap aus
einer gegebenen Liste erzeugt. Listing 2.10 zeigt die entsprechende Python-Implemen-
tierung.
1 def buildHeap(lst ): # Es muss lst[0]==None gelten
2 for i in range(len( lst )/2,0, -1):
3 minHeapify(lst,i)
Listing 2.11: Konstruktion eines Heaps aus einer gegebenen Liste lst .

## Seite 57

42 2 Sortieralgorithmen
Die Funktion buildHeap l¨auft nun ¨uber alle Elemente, die keine Bl ¨atter sind (also Ele-
mente mit Index zwischenlen( lst )/2 und einschließlich 1), beginnend mit den”unteren“
Knoten. Der Aufrufrange(len( lst )/2,0, -1) erzeugt hierbei die Liste der zu untersuchen-
den Knoten in der richtigen Reihenfolge. Der Algorithmus arbeitet sich entsprechend
sukzessive nach ”oben“ vor, bis als letztes die Heap-Bedingung der Wurzel sichergestellt
wird. Folgendermaßen k¨onnte die Funktion buildHeap verwendet werden:
1 >>> l=[None, 86, 13, 23, 96, 6, 37, 29, 56, 80, 5, 92, 52, 32, 21]
2 >>>buildHeap(l)
3 >>>print l
4 [None, 5, 6, 21, 56, 13, 32, 23, 96, 80, 86, 92, 52, 37, 29]
Abbildung 2.10 zeigt die Funktionsweise von buildHeap bei der Anwendung auf eben
diese Beispiel-Liste.
13 23
96 37 29
56 80 5 92 52 32 21
6
i=7
86
i=4 i=5 i=6
(a) Die Schleifendurchl¨aufe f¨ur i = 7 ,..., 4.
13 23
80 92 5296
56 5
6
32
37
21
29
i=3i=2
86
(b) Die Schleifendurchl ¨aufe f ¨ur i = 3
und i = 2.
80 92 5296
56 32
37 29
5
6
13
21
23
i=186
(c) Der Schleifendurchlauf f¨ur i = 1.
80 92 5296
56 32
37 29
21
23
6
13
86
5
(d) Der durch Anwendung von
buildHeap entstandene Heap: Alle
Heapbedingungen sind erf ¨ullt.
Abb. 2.10: Funktionsweise von buildHeap bei Anwendung auf die Liste
[None, 86, 13, 23, 96, 6, 37, 29, 56, 80, 5, 92, 52, 32, 21]. Die Blatt-Knoten f ¨ur sich
genommen bilden schon Heaps; f ¨ur diese trivialen Heaps k ¨onnen keine Heap-Bedingungen ver-
letzt sein. Sei hdie H¨ohe des Heaps; da f ¨ur die Bl¨atter also nichts zu tun ist, beginnt buildHeap
damit, ¨uber die Knoten der Ebene h−1 zu laufen und verletzte Heap-Bedingungen wieder
herzustellen; dies entspricht, wie in Abbildung 2.10(a) zu sehen, den for-Schleifendurchl¨aufen
f¨ur i = 7 (also len( lst )/2) bis i = 4 aus Listing 2.11; Abbildung 2.10(b) zeigt den dadurch
entstandenen Baum und das Herstellen der Heap-Bedingungen der Knoten in Ebene 1. Ab-
bildung 2.10(c) zeigt den daraus entstandenen Baum und das Herstellen der Heap-Bedingung
des Wurzel-Knotens. Abbildung 2.10(d) zeigt den so entstandenen (Min-)Heap.

## Seite 58

2.5 Heapsort und Priority Search Queues 43
Da h¨ochstens O(n) Aufrufe der Funktion minHeapify stattﬁnden, und jeder dieser Auf-
rufe h¨ochstens O(log n) Schritte ben ¨otigt, gilt: buildHeap ben¨otigt O(nlog n) Schritte.
Diese Aussage ist zwar korrekt, da die O-Notation immer eine obere Schranke f ¨ur das
Wachstum angibt2. Tats¨achlich ist es aber so, dass die meisten Aufrufe an minHeapify
”kleine“ Argumente haben; man kann zeigen, dass buildHeap f¨ur das Aufbauen eines
Heaps aus einer n-elementigen Liste tats¨achlich nur O(n) Schritte ben¨otigt.
2.5.4 Heapsort
Das Listing 2.12 zeigt die Implementierung eines eﬃzienten Sortieralgorithmus unter
Verwendung von Heaps:
1 def heapSort(lst ):
2 buildHeap(lst )
3 for i in range(len( lst ) -1,1, -1):
4 lst [1], lst [i ] = lst [i ], lst [1]
5 minHeapify3(lst,1, i -1)
Listing 2.12: Implementierung von Heapsort
Hierbei funktioniert minHeapify3 eigentlich genauso wie minHeapify, außer dass der
dritte Parameter zus¨atzlich angibt, bis zu welchem Index die ¨ubergebene Liste als Heap
betrachtet werden soll. Das Listing implementiert ein in-place-Sortierverfahren unter
Verwendung von Heaps und geht dabei folgendermaßen vor: Zun ¨achst wird aus der
¨ubergebenen unsortierten Liste ein Heap generiert. Dann wird, in einer Schleife, immer
das kleinste Element vom Heap genommen und an den hinteren Teil von lst , in dem
die sortierte Liste aufgebaut wird, angeh ¨angt.
Oft kann man ¨uber die Formulierung vonSchleifeninvarianten geschickt argumentieren,
warum ein bestimmter Algorithmus korrekt ist. Eine Schleifeninvariante ist einfach eine
bestimmte Behauptung, die an einer bestimmten Stelle in jedem Durchlauf einer Schlei-
fe g¨ultig ist. ¨Uber automatische Theorembeweiser kann man so sogar die Korrektheit
einiger Algorithmen formal beweisen; wir nutzen hier jedoch Schleifeninvarianten nur,
um die Korrektheit von Algorithmen informell zu erkl ¨aren. Im Falle des in Listing 2.12
gezeigten Heapsort-Algorithmus gilt folgende Schleifeninvariante: Zu Beginn jedes for-
Schleifendurchlaufs bildet die Teilliste lst [1 :i +1] einen Min-Heap, der die i gr¨oßten
Elemente aus lst enth¨alt; die Teilliste lst [i +1 :] enth ¨alt die n -i kleinsten Elemente
in sortierter Reihenfolge. Da dies insbesondere auch f ¨ur den letzten Schleifendurchlauf
gilt, sieht man leicht, dass die Funktion heapSort eine sortierte Liste zur ¨uckl¨asst.
2Oder in anderen Worten: die Aussage f(n) = O(g(n)) bedeutet, dass die Funktion f(n) h¨ochstens
so schnell w¨achst wie g(n), also evtl. auch langsamer wachsen kann; g(n) kann man aus diesem Grund
auch als ”oberer Schranke“ f¨ur das Wachstum von f(n) bezeichnen.

## Seite 59

44 2 Sortieralgorithmen
Aufgabe 2.22
Implementieren Sie – indem Sie sich an der Implementierung von minHeapify orien-
tieren – die f ¨ur Heapsort notwendige Funktion minHeapify3(i,n), die die ¨ubergebene
Liste nur bis zu Index n als Heap betrachtet und versucht die Heapbedingung an
Knoten i wiederherzustellen.
Aufgabe 2.23
Lassen Sie die Implementierungen von Quicksort und Heapsort um die Wette laufen
– wer gewinnt? Versuchen Sie Ihre Beobachtungen zu erkl ¨aren.
Heaps in Python
Die Standard-Modul heapq liefert bereits eine fertige Implementierung von Heaps. Fol-
gende Funktionen sind u. A. implementiert:
 heapq.heapify( lst ): Transformiert die Liste lst in-place in einen Min-Heap; ent-
spricht der in Listing 2.11 implementierten Funktion buildHeap.
 heapq.heappop(lst): Enfernt das kleinste Element aus dem Heap lst ; dies ent-
spricht somit der in Listing 2.9 implementierten Funktion minExtract.
 heapq.heappush(lst ,x): F ¨ugt ein neues Element x in den Heap lst ein; dies ent-
spricht somit der in Listing 2.8 implementierten Funktion insert.

## Seite 60

2.5 Heapsort und Priority Search Queues 45
Aufgaben
Aufgabe 2.24
Schreiben Sie eine m ¨oglichst performante Python-Funktion
smallestn( lst ,n)
die die kleinesten n Elemente der Liste n zur¨uckliefert.
Aufgabe 2.25
Schreiben Sie eine Funktion allInvTupel, die f¨ur eine gegebene Liste von Zahlen lst=
[a1,a2,...,a n] alle Paare (x,y ) zur¨uckliefert, mit x ∈lst und y ∈lst und x ist das
Einerkomplement von y.
1. Anmerkung: Das Einerkomplement einer Zahl x entsteht dadurch, dass man
jedes Bit in der Bin ¨ardarstellung invertiert, d. h. eine 0 durch eine 1 und eine
1 durch eine 0 ersetzt.
2. Anmerkung: Verwenden Sie zur Implementierung dieser Funktion die Python-
Funktion sort().

## Seite 62

3 Suchalgorithmen
Es gibt viele Anwendungen, deren Kern-Anforderung die Realisierung einer schnellen
Suche ist. Tats¨achlich ist ¨uberhaupt einer der wichtigsten Einsatzzwecke eines Compu-
ters die Speicherung großer Datenmengen in sog. Datenbanken und das schnelle Wie-
derﬁnden (engl: Retrieval) von Informationen in dieser Datenmenge.
Ungeschickt implementierte Suchfunktio-
Abb. 3.1:Ein Karteikartensystem. Datenbank-
und Information-Retrieval-Systeme sind digita-
le ”Nachbauten“ solcher (und ¨ahnlicher) Syste-
me.
nen kommen schon bei einigen Gigabyte
an Daten an ihre Grenzen und werden
bei sehr großen Datenmengen vollkom-
men nutzlos. Und wir haben es mit zu-
nehmend riesigen Datenmengen zu tun,
die noch vor 10 Jahren unvorstellbar wa-
ren. Ein Vergleich mit der gr¨oßten Biblio-
thek der Welt – der British Library, deren
Lesesaal in Abbildung 3.2 zu sehen ist,–
kann ein ”Gef¨uhl“ daf¨ur geben, mit wel-
chen Datenmengen wir es zu tun haben:
Die British Library hat mehr als 150 Mio. Exemplare (also B ¨ucher, Zeitschriften usw.).
Gehen wir von 1500 Byte an Daten pro Buchseite aus, und einer durchschnittlich 300
Abb. 3.2: Der Lesesaal der ber ¨uhmten ”British Library“ – der gr ¨oßten Bibliothek der Welt
mit einem Bestand von mehr als 150 Mio Exemplaren.
Seiten pro Buch, so ¨uberschlagen wir, dass die British Library etwa 75000 Gigabyte oder
75 Terabyte an Daten gespeichert hat. Das Unternehmen Google, dagegen, unterh ¨alt
weltweit laut groben Sch¨atzungen ¨uber eine Million Server auf denen, davon k¨onnen wir

## Seite 63

48 3 Suchalgorithmen
ausgehen, durchschnittlich mehrere Terabyte an Daten gespeichert sind; wir k¨onnen al-
so grob sch¨atzen, dass Google deutlich mehr als 1000000 Terabyte, also mehr als 1000
Petabyte an Daten auf den Firmen-internen Servern gespeichert hat, d. h. deutlich¨uber
10000 mal, vielleicht sogar 100000 mal, mehr Daten als sich in der gesamten British Li-
brary beﬁnden; Abbildung 3.3 deutet einen graphischen Vergleich dieser Datenmengen
an. Ferner geht eine Studie von Cisco davon aus, dass in 2 bis 3 Jahren t¨aglich mehr
Server
Googles
British
Library
+ noch
mehr
10000-mal
1000- bis
Abb. 3.3: Große Datenmengen im Vergleich.
als 2000 Petabyte an Daten ¨ubers Internet verschickt werden.
Das Durchsuchen einer einfachen Liste der L ¨ange n ben¨otigt O(n) Schritte. Sind ¨uber
die Liste keine besonderen Eigenschaften bekannt, kommt man nicht umhin, die ganze
Liste einfach linear von ”vorne“ bis ”hinten“ zu durchsuchen. Hat man es mit einer
großen Datenmenge zu tun – etwa mit einer Gr ¨oße von mehreren Giga-, Tera- oder
Petabyte – so ist ein Algorithmus mit Suchdauer von O(n) vollkommen nutzlos.
Aufgabe 3.1
Angenommen, ein (nehmen wir sehr recht schneller) Rechner kann ein Byte an Daten
in 50 ns durchsuchen. Wie lange braucht der Rechner, um eine Datenbank einer Gr¨oße
von 100 GB / 100 TB / 100 PB zu durchsuchen, wenn der Suchalgorithmus
(a) . . . eine Laufzeit von O(n) hat?
(b) . . . eine Laufzeit von O(log(n)) hat – nehmen Sie an, die Laufzeit w ¨are propor-
tional zu log 2 n (was durchaus sinnvoll ist, denn meistens werden bei solchen
Suchen bin¨are Suchb¨aume verwendet)?
In diesem Kapitel lernen wir die folgenden Suchtechniken kennen:
1. Suchen mittels bin¨aren Suchb¨aumen. Mittlere Suchlaufzeit (vorausgesetzt die B¨au-
me sind balanciert) ist hier O(log n).
2. Suchen mittels speziellen balancierten bin ¨aren Suchb¨aumen: den AVL-B ¨aumen
und den rot-schwarz-B¨aumen. Worst-Case-Suchlaufzeit ist hier O(log n).
3. Suchen mittels Hashing. Die Suchlaufzeit ist hier (unter gewissen Voraussetzun-
gen) sogar O(1).
4. Unterst ¨utzung von Suchen mittels eines Bloomﬁlters, einer sehr performanten
randomisierten Datenstruktur die allerdings falsche (genauer: falsch-positive) Ant-
worten geben kann.

## Seite 64

3.1 Bin ¨are Suchb¨aume 49
5. Suchen mittels Skip-Listen. Eine Skip-Liste ist eine randomisierte Datenstruktur,
deren Struktur (auf den ersten Blick) einer verketteten Liste gleicht. Die Such-
laufzeit ist hier allerdings O(log n).
6. Suchen mittels Tries und Patricia. Diese Datenstrukturen sind besonders f¨ur text-
basierte Suchen geeignet und in vielen Suchmaschinen verwendet. Die Suchlaufzeit
ist hier nicht abh¨angig von der Anzahl der enthaltenen Datens¨atze sondern alleine
von der L¨ange des zu suchenden Wortes und betr ¨agt O(Wortl¨ange).
3.1 Bin ¨are Suchb¨aume
Bin¨are Suchb¨aume stellen die wohl oﬀen-
sichtlichste, zumindest am l ¨angsten be-
kannte Art und Weise dar, Schl¨ussel-Wert-
Paare so zu ordnen, dass eine schnel-
le Suche nach Schl ¨usselwerten m ¨oglich
ist. Bin ¨are Suchb¨aume wurden Ende der
50er Jahre parallel von mehreren Perso-
nen gleichzeitig entdeckt und verwendet.
Die Performanz der Suche kann jedoch be-
eintr¨achtigt sein, wenn der bin ¨are Such-
baum zu unbalanciert ist, d. h. wenn sich
die H¨ohe des linken Teilbaums zu sehr von
der H ¨ohe des rechten Teilbaums unter-
scheidet – der Knoten mit der Markierung
”44“ in dem rechts dargestellten bin ¨aren
Suchbaum ist etwa recht unbalanciert: Die
H¨ohe des linken Teilbaums ist 0; die H¨ohe
des rechten Teilbaums ist dagegen 6.
22
20 160
13
11 16
4
0 8
14 19
43 164
29 134
24 38
26
27
35 42
30
67 137
44 69
65
47
45 56
46 48 59
53 58 61
57
71
70 114
76 129
73 92
87 112
80 88
77 86
84
106 113
96 110
93 104
98
111
117
115 119
136 141
140 154
138 146 155
144 150
151
178
169
166 171
167 170 172
174
Ein bin ¨arer Suchbaum ist ein Baum, dessen Knoten Informationen enthalten. Jeder
Knoten erh¨alt einen eindeutigen Wert, auch Schl¨ussel genannt, ¨uber den man die ent-
haltenen Daten wiederﬁnden kann. Wir nehmen also an, dass in einem Suchbaum jedem
Knoten v ein bestimmter Schl¨usselwert v.key zugeordnet ist. Ein bin¨arer Suchbaum ist
ein Suchbaum mit folgenden beiden Eigenschaften:
1. Jeder Knoten hat h ¨ochstens zwei Kinder.
2. F ¨ur jeden inneren Knoten v, d. h. Knoten mit Kindern, gilt: f¨ur jeden Knoten ldes
linken Teilbaums ist l.key ≤v.key und f¨ur jeden Knoten r des rechten Teilbaums
ist r.key≥v.key.
Abbildung 3.4 zeigt ein Beispiel eines bin ¨aren Suchbaums.
Ein bin¨arer Suchbaum wird oft verwendet, um (den abstrakten Datentyp des) Dictio-
naries zu implementieren. Ein Dictionary enth ¨alt eine Sammlung von Schl ¨ussel-Wert-
Paaren und unterst¨utzt eﬃzient eine Suchoperation nach Schl¨usseln, eine Einf¨ugeopera-
tion und eine L¨oschoperation. Pythons Dictionaries sind jedoch nicht ¨uber Suchb¨aume,

## Seite 65

50 3 Suchalgorithmen
5
72
8 19
1811
14
15
23
28
41
Abb. 3.4:Beispiel eines bin¨aren Suchbaums. Man sieht, dass alle Schl ¨ussel im linken Teilbaum
eines jeden Knotens immer kleiner, und alle Werte im rechten Teilbaum eines jeden Knotens
immer gr¨oßer sind als der Wert des jeweiligen Knotens.
sondern ¨uber Hash-Tabellen realisiert.
3.1.1 Repr ¨asentation eines bin¨aren Suchbaums
Es gibt mehrere M ¨oglichkeiten, B¨aume, insbesondere bin ¨are B¨aume, in Python zu re-
pr¨asentieren. Am einfachsten ist die Verwendung von geschachtelten Listen bzw. ge-
schachtelten Tupeln oder geschachtelten Dictionaries – siehe auch Abschnitt 1.4 f ¨ur
weitere Details hierzu. So k ¨onnte beispielsweise das folgende geschachtelte Tupel den
Bin¨arbaum aus Abbildung 3.4 repr ¨asentieren:
tSkript2 = (15, (8, (5, 2, 7), (11, (), 14) \
(19, (18,(),()), (28, 23, 41)
Dies ist eine einfache und ¨ubersichtliche Darstellung, die wir auch tats¨achlich an anderer
Stelle bei der Repr ¨asentation von Binomial-Heaps so verwenden (siehe Abschnitt 4.2)
die jedoch zwei entscheidende Nachteile hat, die in diesem Falle relativ schwer wiegen:
Zum Einen ist sie wenig typsicher und bringt entsprechend viele Freiheitsgrade mit
sich: Ob man beispielsweise ein Blatt als (18,(),()) , als (18, None,None) oder einfach
als 18 repr¨asentiert, ist nicht direkt festgelegt. Zum Anderen ist sie schlecht erweiterbar:
M¨ochte man etwa bestimmte Eigenschaften (wie etwa die H ¨ohe oder die Farbe) eines
Knoten mitverwalten, so l¨auft man hier Gefahr den gesamten Code ¨andern zu m¨ussen.
Man kann die Repr¨asentation von Bin¨arb¨aumen typsicherer gestalten, indem man eine
eigens deﬁnierte Klasse verwendet. Wir nennen diese BTree; die Deﬁnition der Klasse
zusammen mit der zugeh¨origen Konstruktorfunktion
init ist in Listing 3.1 gezeigt.
1 class BTree(object):
2 def init ( self , key, ltree=None, rtree=None, val=None):
3 self . ltree = ltree
4 self . rtree = rtree
5 self .key = key
6 self . val = val
Listing 3.1: Ein Ausschnitt der Deﬁnition der Klasse BTree

## Seite 66

3.1 Bin ¨are Suchb¨aume 51
Hierbei sind die Parameter ltree, rtree und val der Funktion init sog. benannte
Parameter (siehe Anhang A.3.4).
Ein einfacher Bin¨arbaum, bestehend aus nur einem Knoten mit Schl ¨usselwert 15, kann
folgendermaßen erzeugt werden:
b = BTree(15)
Die benannten Parameter werden nicht speziﬁziert und erhalten daher ihren Default-
Wert ”None“.
Der in Abbildung 3.4 dargestellte bin ¨are Suchbaum k¨onnte in Python durch folgenden
Wert repr¨asentiert werden.
binTree = BTree(15,BTree(8, BTree(5, BTree(2), BTree(7)),
BTree(11, None, BTree(14))),
BTree(19, BTree(18),
BTree(28, BTree(23), BTree(41))))
Der Einfachheit halber wurden den einzelnen Knoten nur Schl ¨usselwerte (das key-
Attribut) gegeben, jedoch keine eigentlichen Daten (das val-Attribut).
Man sollte Zugriﬀs- und Updatefunktionen f¨ur die Klasse BTreehinzuf¨ugen, indem man
entsprechende Instanzen der Klassenfunktionen
getitem und setitem implemen-
tiert; zus¨atzlich k¨onnte auch eine Instanz der Klassenfunktion str n¨utzlich sein, die
eine gut lesbare Form eines BTrees als String zur ¨uckliefert. Diese Implementierungsar-
beit ¨uberlassen wir dem Leser.
Aufgabe 3.2
Implementieren Sie eine Instanz der Klassenfunktion str , die BTrees in einer gut
lesbaren Form ausgeben kann.
Aufgabe 3.3
Implementieren Sie als Klassenfunktion von BTreeeine Funktion height, die die H¨ohe
des jeweiligen Bin¨arbaums zur¨uckliefert.
Aufgabe 3.4
Instanziieren Sie die Klassenfunktion len f¨ur die Klasse BTree, die die Anzahl
der Knoten des jeweiligen BTrees zur¨uckliefern soll.
3.1.2 Suchen, Einf ¨ugen, L¨oschen
Suchen. Am einfachsten kann die Suche implementiert werden. Angenommen der
Schl¨ussel key soll gesucht werden, so wird zun ¨achst der Schl¨ussel r.key des Wurzelkno-
tes r mit key verglichen. Falls key mit dem Schl¨ussel des Wurzelknotens ¨ubereinstimmt,

## Seite 67

52 3 Suchalgorithmen
wird der im Wurzelknoten gespeicherte Wert r. val zur¨uckgegeben. Ist key<r.key, so
muss sich aufgrund der Eigenschaften eines bin ¨aren Suchbaums der Schl ¨usselwert im
linken Teilbaum beﬁnden, es wird also rekursiv im linken Teilbaum weitergesucht; ist
key>r.key, wird rekursiv im rechten Teilbaum weitergesucht. Listing 3.2 zeigt eine Im-
plementierung als Methode search der Klasse BTree.
1 class BTree(object):
2 ...
3 def search( self , key):
4 if key==self.key:
5 return self # Rek.Abbr.: s gefunden.
6 elif key < self .key:
7 if self . ltree==None:
8 return None # Rek.Abbr.: s nicht gefunden.
9 else:
10 return self. ltree .search(key) # Rekursiver Aufruf
11 elif key > self .key:
12 if self . rtree==None:
13 return None # Rek.Abbr.: s nicht gefunden.
14 else:
15 return self. rtree.search(key) # Rekursiver Aufruf
Listing 3.2: Implementierung der Suche im Bin ¨arbaum durch die Klassenfunktion
BTree.search(key);
In Zeile 4 wird getestet, ob der Schl ¨ussel der Wurzel des aktuellen Bin ¨arbaums gleich
dem zu suchenden Schl¨ussel ist; dann wird der Wert des Knotens self . val zur¨uckgelie-
fert. Falls der Schl¨ussel kleiner als der Schl¨ussel des aktuellen Knotens ist (Zeile 6), wird
rekursiv im linken Teilbaum self . ltree weitergesucht. Falls der Suchschl¨ussel gr¨oßer ist
(Zeile 11), wird rekursiv im rechten Teilbaum self . rtree weitergesucht. Falls es keinen
linken bzw. rechten Teilbaum mehr gibt, so wurde der Schl ¨ussel nicht gefunden und es
wird None zur¨uckgeliefert (Zeile 8 und Zeile 12).
Aufgabe 3.5
Schreiben Sie die Funktion search iterativ.
Aufgabe 3.6
Schreiben Sie eine Methode BinTree.minEl() und eine MethodeBinTree.maxEl(), die
eﬃzient das maximale und das minimale Element in einem bin¨aren Suchbaum ﬁndet.
Einf¨ugen. Soll der Schl¨ussel key in einen bestehenden Bin¨arbaum eingef¨ugt werden, so
wird der Baum von der Wurzel aus rekursiv durchlaufen – ¨ahnlich wie bei der in Listing
3.2 gezeigten Suche. Sobald dieser Durchlauf bei einem Blatt v angekommen ist, wird

## Seite 68

3.1 Bin ¨are Suchb¨aume 53
ein neuer Knoten an dieses Blatt angeh ¨angt; entweder als linkes Blatt, falls v.key>key,
oder andernfalls als rechtes Blatt. Listing 3.3 zeigt die Implementierung als Methode
insert (key,val) der Klasse BTree.
1 class BTree(object):
2 ...
3 def insert( self ,key,val ):
4 if key < self .key:
5 if self . ltree == None:
6 self . ltree = BTree(key,None,None,val) # Rek.Abbr: key wird eingef ¨ugt
7 else: self . ltree . insert (key,val)
8 elif key > self .key:
9 if self . rtree == None:
10 self . rtree = BTree(key,None,None,val) # Rek.Abbr: key wird eingef ¨ugt
11 else: self . rtree. insert (key,val)
Listing 3.3: Implementierung der Einf ¨uge-Operation im Bin ¨arbaum durch die Methode
insert (key, val).
Falls der einzuf¨ugende Schl¨ussel key kleiner ist, als der Schl¨ussel an der Wurzel des Bau-
mes self .key, und noch kein Blatt erreicht wurde, wird im linken Teilbaum self . ltree
durch einen rekursiven Aufruf (Zeile 7) weiter nach der Stelle gesucht, an die der
einzuf¨ugende Schl ¨ussel passt. Falls der einzuf ¨ugende Schl ¨ussel key gr¨oßer ist, als der
Schl¨ussel an der Wurzel des Baumes und noch kein Blatt erreicht wurde, so wird im rech-
ten Teilbaum (Zeile 11) weiter nach der passenden Einf¨ugestelle gesucht. Falls die Suche
an einem Blatt angelangt ist (falls also giltself . ltree==None bzw. self . rtree==None),
so wird der Schl ¨ussel key als neues Blatt eingef ¨ugt – zusammen mit den zugeh ¨origen
Informationen val, die unter diesem Schl ¨ussel abgelegt werden sollen. Dies geschieht in
Listing 3.3 in den Zeilen 6 und 10.
Aufgabe 3.7
(a) In den in Abbildung 3.4 dargestellten bin ¨aren Suchbaum soll der Schl ¨ussel 22
eingef¨ugt werden. Spielen Sie den in Listing 3.3 gezeigten Algorithmus durch;
markieren Sie diejenigen Knoten, mit denen der Schl¨usselwert 22 verglichen wur-
de und stellen Sie dar, wo genau der Schl ¨usselwert 22 eingef¨ugt wird.
(b) F ¨ugen Sie in den in Abbildung 3.4 dargestellten bin¨aren Suchbaum nacheinander
die Werte 4 −13 −12 −29 ein. Spielt die Einf ¨ugereihenfolge eine Rolle?
(c) F ¨ugen Sie in den in Abbildung 3.4 dargestellten bin¨aren Suchbaum nacheinander
derart 8 Werte so ein, so dass der Baum danach eine H ¨ohe von 10 hat.

## Seite 69

54 3 Suchalgorithmen
Aufgabe 3.8
Der in Listing 3.2 gezeigte Algorithmus zum Einf ¨ugen in einen Bin ¨arbaum ber ¨uck-
sichtigt nicht den Fall, dass der einzuf¨ugende Schl¨ussel x bereits im Baum vorhanden
ist.
Erweitern Sie die Methode insert so, dass dieser Fall sinnvoll angefangen wird.
Aufgabe 3.9
Schreiben Sie die Methode insert iterativ.
L¨oschen. Welches Verfahren zum L¨oschen eines Knotens vin einem bin¨aren Suchbaum
angewendet wird, h¨angt davon ab, ob der zu l ¨oschende Knoten ein Blatt ist, ein Kind
besitzt oder zwei Kinder besitzt:
 Handelt es sich bei dem zu l¨oschenden Knoten um ein Blatt, so wird dieses einfach
gel¨oscht.
 Hat der zu l ¨oschende Knoten ein Kind, so wird einfach dieses Kind an die Stelle
des zu l¨oschenden Knotens gesetzt.
 Hat der zu l¨oschende Knoten zwei Kinder – dies ist der schwierigste Fall – so geht
man wie folgt vor: Man ersetzt den zu l ¨oschenden Knoten mit dem minimalen
Knoten des rechten Teilbaums. Dieser minimale Knoten des rechten Teilbaums
hat h ¨ochstens ein (rechtes) Kind und kann somit einfach verschoben werden –
analog wie beim L ¨oschen eines Knotens mit nur einem Kind.
In Abbildung 3.5 ist der L ¨oschvorgang f¨ur die beiden F ¨alle, in denen der zu l ¨oschende
Knoten Kinder hat, graphisch veranschaulicht.
Es gibt hier, wie in vielen anderen F ¨allen auch, grunds ¨atzlich zwei M¨oglichkeiten, das
L¨oschen zu implementieren: nicht-destruktiv oder destruktiv. Bei einer nicht-destrukti-
ven Implementierung bleibt der ”alte“ bin¨are Suchbaum unangetastet. Stattdessen wird
als R¨uckgabewert ein ”neuer“ bin¨arer Suchbaum konstruiert (der durchaus Teile des”al-
ten“ Suchbaums enthalten kann), der das zu l¨oschende Element nicht mehr enth¨alt. Eine
Funktion, die nicht-destruktive Updates verwendet entspricht also am ehesten einer ma-
thematischen Funktion: Sie bekommt einen Eingabewert (hier: einen zu modiﬁzierenden
Bin¨arbaum) und produziert einen Ausgabewert (hier: einen Bin ¨arbaum, aus dem das
gew¨unschte Element gel¨oscht wurde). Nicht-destruktive Implementierungen sind h¨auﬁg
anschaulich und kompakt; ein Nachteil ist jedoch der h ¨ohere Speicherplatzverbrauch.
Ein guter Compiler und ein raﬃniertes Speichermanagement kann diesen jedoch in
Grenzen halten. Listing 3.4 zeigt die Implementierung als Methode der Klasse BTree.
1 class BTree(object):
2 ...
3 def deleteND(self,key):
4 if self .key==key:
5 if self . ltree==self.rtree==None: return None # 0 Kinder
6 elif self . ltree==None: return self.rtree # 1 Kind
7 elif self . rtree==None: return self.ltree

## Seite 70

3.1 Bin ¨are Suchb¨aume 55
96 96
38 38
2
58
52 92
49
89
9917
382
58
38
52 92
30
49
89
9917
103
2
58
52
49
89
9917
1032
58
52 92
30
49
89
9917
103
103
30
96
96
(a)
(b)
v
v
19
19
19
19
33
33
33
33
Abb. 3.5: L¨oschen eines Knotens in einem bin¨aren Suchbaum. Abbildung (a) zeigt das L¨oschen
eines Knotens v = 92, der nur ein Kind besitzt. Hier wird einfach das Kind von v (n¨amlich
der Knoten mit dem Schl ¨ussel 96) an dessen Stelle gesetzt. Abbildung (b) zeigt das L ¨oschen
des Knotens v = 30, der zwei Nachfolger besitzt. Hier wird der minimale Knoten des rechten
Teilbaums von v – das ist in diesem Fall der Knoten mit dem Schl ¨ussel 33 – an die Stelle von
v gesetzt. Man sieht, dass der minimale Knoten selbst noch ein Kind hat; dieser wird, wie in
Fall (a) beschrieben, an dessen Stelle gesetzt.
8 else: # 2 Kinder
9 z=self. rtree.minEl()
10 return BTree(z.key,self. ltree , self . rtree.deleteND(z.key), z. val)
11 else:
12 if key<self.key:
13 return BTree(self.key, self . ltree .deleteND(key), self . rtree, self . val)
14 elif key>self.key:
15 return BTree(self.key, self . ltree , self . rtree.deleteND(key), self . val)
Listing 3.4: Implementierung der L ¨osch-Operation im Bin¨arbaum durch die Klassenfunktion
BTree.deleteND(key).
Entspricht der Schl¨ussel self .key des aktuellen Knotens nicht dem zu l¨oschenden Schl¨us-
sel key, so wird weiter nach dem zu l ¨oschenden Knoten gesucht – entweder im linken
Teilbaum (Zeile 13) oder im rechten Teilbaum (Zeile 15). Falls jedoch der Schl ¨ussel
des aktuellen Knotens dem zu l ¨oschenden Schl¨ussel entspricht, so wird dieser Knoten
gel¨oscht (Zeile 4–10). Ist der Knoten ein Blatt, so wird er einfach gel ¨oscht (Zeile 5).
Besitzt er ein Kind, so wird dieses Kind, also self . ltree bzw. self . rtree, an dessen
Stelle gesetzt (Zeile 6 und 7). In Zeile 9 und 10 beﬁndet sich der Code, um einen
Knoten mit zwei Kindern zu l ¨oschen: Das minimale Element des rechten Teilbaums
(hier: self . rtree.minEl(); siehe Aufgabe 3.6) wird an die Stelle des aktuellen Kno-
tens gesetzt. Zus ¨atzlich wird dieser minimale Knoten durch einen rekursiven Aufruf
( self . rtree.deleteND(z.key)) von seiner urspr ¨unglichen Position gel¨oscht.

## Seite 71

56 3 Suchalgorithmen
Aufgabe 3.10
Man kann ein destruktives L ¨oschen unter Anderem unter Verwendung einer ”R¨uck-
w¨artsverzeigerung“ implementieren, d. h. unter Verwendung einer M ¨oglichkeit, den
Vaterknoten eines Knotens v anzusprechen.
Implementieren Sie diese M ¨oglichkeit, indem Sie die Klasse BTree um ein Attribut
parent erweitern. Man beachte, dass dies weitere ¨Anderungen nach sich zieht: Die
Methode insert muss etwa angepasst werden.
Aufgabe 3.11
Implementieren Sie eine Methode BTree.delete(v), die auf destruktive Art und Weise
einen Knoten mit Schl ¨usselwert v aus einem bin¨aren Suchbaum l¨oscht.
Aufgabe 3.12
Implementieren Sie eine MethodeinsertND(v) der KlasseBinTree, die nicht-destruktiv
einen Knoten in einen bin ¨aren Suchbaum einf ¨ugt; ein Aufruf bt .insertND(v) sollte
bt nicht ver¨andern, sondern einen neuen bin¨aren Suchbaum zur¨uckliefern, der bt mit
eingef¨ugtem v entspricht.
3.1.3 Laufzeit
Die Suche braucht O(h) Schritte, wobei h die H¨ohe1 des bin¨aren Suchbaums ist, denn
es wird mindestens ein Vergleich f ¨ur jede Stufe des Baumes ben ¨otigt. Gleiches gilt f ¨ur
das Finden des maximalen bzw. minimalen Elements.
Was ist die H¨ohe eines bin¨aren Suchbaums? Das l¨asst sich
nicht pauschal beantworten, denn die H¨ohe h¨angt von der
Reihenfolge ab, in der Schl¨ussel in einen Baum eingef¨ugt
werden. Man kann zeigen, dass bei einer zuf ¨allig gew¨ahl-
ten Einf¨ugereihenfolge von nZahlen im Durchschnitt ein
bin¨arer Suchbaum mit einer H¨ohe von c·log2 nentsteht,
d. h. im Durchschnitt ist die H ¨ohe eines bin ¨aren Such-
baums, dessen Einf ¨uge- und L ¨oschoperationen wie oben
beschrieben implementiert sind, in O(log n).
Bei einer ung ¨unstigen Einf ¨ugereihenfolge ist es aber
m¨oglich, dass ein bin¨arer Suchbaum der H¨ohe nentsteht,
mit einer Strukur wie etwa in Abbildung 3.6 gezeigt.
Abb. 3.6: Ein ”entarteter“
(extrem unbalancierter)
bin¨arer Suchbaum, wie
er durch ungeschicktes
Einf¨ugen entstehen kann.
1Die H¨ohe eines Baumes ist die Anzahl von Kanten von der Wurzel bis zu dem ”tiefsten“ Blatt;
siehe Anhang B.4.1 f ¨ur mehr Details.

## Seite 72

3.2 AVL-B ¨aume 57
Aufgabe 3.13
Gegeben seien die Schl ¨ussel 51,86,19,57,5,93,8,9,29,77.
(a) Welche H ¨ohe hat der Baum, wenn die Schl ¨ussel in der oben angegebenen Rei-
henfolge in einen anf ¨anglich leeren Baum eingef ¨ugt werden?
(b) Finden Sie eine Einf ¨ugereihenfolge, bei der ein Baum der H ¨ohe 9 entsteht.
(c) Finden Sie eine Einf ¨ugereihenfolge, bei der ein Baum minimaler H ¨ohe entsteht.
In den folgenden beiden Abschnitten werden Techniken vorgestellt, wie man bin ¨are
Suchb¨aume m¨oglichst balanciert halten kann.
3.2 AVL-B ¨aume
137
78 229
44 106
23 62
13 34
4 18
2 11
1 3 7 12
5
15 20
19 22
26 39
24 31
25 27 33
36 43
35 37 40
54 66
51 57
47 52
48 53
55 61
56
65 73
64 67 77
90 120
84 95
80 86
79 82 85 88
89
92 99
91 93
94
98 104
96 100
112 126
109 118
107 111
108
114 119
113
124 130
121 128 134
127
167 264
156 197
146 163
142 152
141 143
138 144
147 154
153 155
160 165
159 161 164 166
177 217
173 193
170 176
169 171
186 194
185 189
192
196
208 225
201 214
198 202
200 205
210 215
222 226
223 228
245 282
236 252
234 239
233 235 238 244
243
248 256
246 249 254 260
253 257 262
274 290
269 277
266 271
265 268 270 273
272
275 278
281
286 293
285 289
288
292 297
291 294 298
AVL-B¨aume sind balancierte bin ¨are Suchb¨aume. Sie sind benannt nach den Erﬁndern,
Georgi Adelson-Velski und Jewgeni Landis, zwei russischen Mathematikern und Infor-
matikern, die 1962 erstmals beschrieben, wie bin ¨are Suchb¨aume mittels sog. ”Rotatio-
nen“ balanciert gehalten werden k ¨onnen.
Ein AVL-Baum ist ein bin ¨arer Suchbaum, f ¨ur den gilt, dass sich die H ¨ohe des linken
Teilbaums und die H ¨ohe des rechten Teilbaums eines jeden Knotens um h ¨ochstens
einen Betrag von 1 unterscheiden darf. Wir gehen hier von der im letzten Abschnitt
beschriebenen Implementierung eines bin¨aren Suchbaums aus und deﬁnieren zus¨atzlich
f¨ur jeden Knoten v ein Attribut v. height, das die H ¨ohe des Knotens speichert, und ein
Attribut v.balance, das den Balance-Wert des Knotens speichert.
Seien lheight die H¨ohe des linken Teilbaums undrheight die H¨ohe des rechten Teilbaums
eines Knoten v, dann sind die beiden Attributev. height und v.balance wie folgt deﬁniert:
v. height = 1 +max(rheight, lheight ) (3.1)
v.balance = -lheight + rheight (3.2)
Die Tatsache, dass ein AVL-Baum balanciert ist, bedeutet, dass f ¨ur jeden Knoten v
eines AVL-Baums
v.balance ∈{−1,0,1}
gelten muss.

## Seite 73

58 3 Suchalgorithmen
Listing 3.5 zeigt die Implementierung der init -Methode der Klasse AVLTree, die
von der im letzten Abschnitt vorgestellten Klasse BTree erbt. Diese init -Funktion
f¨uhrt dieselben Kommandos aus, wie die init -Funktion der Elternklasse BTree –
dies wird durch den entsprechenden Aufruf in Zeile 4 sichergestellt. Zus ¨atzlich werden
die H¨ohen- und Balance-Werte des Knotens berechnet – dies geschieht durch den Aufruf
der Funktion calcHeight in Zeile 5.
1 class AVLTree(BTree):
2
3 def init ( self , key, ltree=None, rtree=None, val=None):
4 BTree. init ( self , key, ltree , rtree, val)
5 self . calcHeight()
6
7 def
calcHeight( self ):
8 rheight = -1 if not self . rtree else self . rtree. height
9 lheight = -1 if not self . ltree else self . ltree . height
10 self . height = 1 +max(rheight,lheight)
11 self .balance = -lheight +rheight
Listing 3.5: Implementierung der Klasse AVLTree, die von BTree – der Klasse, die unbalan-
cierte bin¨are Suchb¨aume implementiert, – erbt.
Die Funktion calcHeight berechnet die H¨ohe und den Balance-Wert gem ¨aß der in den
Gleichungen (3.1) und (3.2) dargestellten Beziehungen. Das ‘ ’-Zeichen, mit dem der
Methodenname beginnt, deutet an, dass es sich hier um eine interne Methode handelt,
die zwar von anderen Methoden verwendet wird, jedoch ¨ublicherweise nicht von einem
Benutzer der Klasse.
3.2.1 Einf ¨ugeoperation
Sowohl beim Einf¨ugen als auch beim L¨oschen kann die Balance eines Knoten bzw. meh-
rerer Knoten auf dem Pfad von der Einf ¨uge- bzw. L ¨oschposition bis zur ¨uck zur Wur-
zel zerst ¨ort sein. Abbildung 3.7 veranschaulicht, welche Knoten re-balanciert werden
m¨ussen.
1. insert (z)
2. balance()
z
Abb. 3.7: Nach einer Einf ¨ugeoperation m¨ussen die Knoten auf dem Pfad von der Einf ¨ugepo-
sition bis hin zur Wurzel rebalanciert werden.

## Seite 74

3.2 AVL-B ¨aume 59
Wir gehen von einer – wie im letzten Abschnitt in Listing 3.3 beschriebenen – insert-
Funktion aus. Stellen wir sicher, dass vor jedem Verlassen derinsert-Funktion die Funk-
tion balance() aufgerufen wird, so erfolgt die Balancierung w¨ahrend des rekursiven Auf-
stiegs; dies entspricht genau der Rebalancierung der Knoten von der Einf ¨ugeposition
bis hin zur Wurzel wie in Abbildung 3.7 gezeigt.
Das folgende Listing 3.6 zeigt die Implementierung:
1 def insert( self ,x, val=None):
2 if x < self .key:
3 if self . ltree == None:
4 self . ltree = AVLTree(x,None,None,val)
5 else:
6 self . ltree . insert (x, val)
7 elif x > self .key:
8 if self . rtree == None:
9 self . rtree = AVLTree(x,None,None,val)
10 else:
11 self . rtree. insert (x, val)
12 self . calcHeight()
13 self . balance()
Listing 3.6: Implementierung der Einf ¨ugeoperation bei AVL-B¨aumen.
Beim rekursiven Aufstieg wird zun ¨achst H¨ohe und Balance-Wert neu berechnet (Zeile
12) und dann (falls notwendig) rebalanciert (Zeile 13).
Aufgabe 3.14
Implementieren Sie nach ¨ahnlichem Prinzip eine balancierende L ¨oschfunktion
3.2.2 Grundlegende Balancierungsoperationen:
Rotationen
Die Balancierungsoperationen werden Rotationen2 genannt. Man unterscheidet zwi-
schen Einfachrotationen und Doppelrotatonen, die prinzipiell die Hintereinanderaus-
f¨uhrung zweier Einfachrotationen darstellen.
Man beachte, dass ein Knoten a immer genau dann rebalanciert wird, wenn sich die
H¨ohe des rechten und die H ¨ohe des linken Teilbaums um einen Betrag von genau 2
unterscheiden, d. h. wenn a.balance ∈{−2, 2}. Der Grund daf ¨ur, dass der Betrag des
Balance-Werts immer genau 2 betr ¨agt, ist, dass wir sicherstellen, dass immer sofort
nach dem Einf¨ugen eines Knotens bzw. dem L ¨oschen eines Knotens rebalanciert wird.
2Das Wort ”Rotation“ wird in diesem Zusammenhang wohl eher deshalb verwendet, weil die Ver-
wendung dieses Begriﬀs in der wissenschaftlichen Literatur zur Gewohnheit wurde und weniger weil es
oﬀensichtliche Analogien zu der Drehbewegung einer Rotation gibt.

## Seite 75

60 3 Suchalgorithmen
Abbildung 3.8 zeigt die vier verschiedenen Arten von Rotationen: Zwei symmetrische
F¨alle der Einfachrotationen in Abbildungen 3.8(a) (f ¨ur den Fall a.balance = 2) und
3.8(b) (f¨ur den Fall a.balance = −2) und die zwei symmetrischen F ¨alle der Doppelro-
tationen in Abbildungen 3.8(c) (f ¨ur und Fall a.balance = 2) und 3.8(d) (f ¨ur den Fall
a.balance = −2).
t1
t4
t1 t4t23
a
ba
t23
b
(a) Einfache Links-Rotation: a.balance = 2 und
innerer Enkel nicht h¨oher.
a
t4
b
a
t23 t4t1
b
t1
t23
(b) Einfache Rechts-Rotation: a.balance = −2
und innerer Enkel nicht h ¨oher.
c
b
c
a
t1
b
a
t1
t2
t4
t3
t2 t3 t4
(c) Doppel-Links-Rotation: a.balance = 2 und innerer Enkel h ¨oher.
a c
t1
b
c
t1
t2 t3
t4
b a
t2 t3 t4
(d) Doppel-Rechts-Rotation: a.balance = −2 und innerer Enkel
h¨oher.
Abb. 3.8: Die vier verschiedenen Rotationen: Zwei Einfach- und zwei Doppelrotationen.
Die Einfachrotationen (Abbildungen 3.8(a) und 3.8(b)) k ¨onnen immer dann angewen-
det werden, wenn der innere, im h¨oheren Teilbaum beﬁndliche, Enkel von a nicht h¨oher
ist als der ¨außere Enkel. Doppelrotationen (Abbildungen 3.8(c) und 3.8(d)), die im
Prinzip eine Hinteranderausf¨uhrung von zwei Einfachrotationen darstellen, m¨ussen ent-
sprechend bei einer Rebalancierung angewendet werden, wenn der innere im h ¨oheren
Teilbaum beﬁndliche Enkel vona h¨oher ist als der ¨außere Enkel. Die eben beschriebenen
Kriterien, wann welche Rotation anzuwenden ist, sind in der in Listing 3.7 gezeigten
Methode
balance() implementiert.

## Seite 76

3.2 AVL-B ¨aume 61
1 def balance( self ):
2 if self .balance == 2: # rechts h¨oher
3 t23 = self . rtree. ltree ; t4 = self . rtree. rtree
4 if not t23: self . simpleLeft()
5 elif t4 and t23.height ≤ t4. height : self . simpleLeft()
6 else: self . doubleLeft()
7 if self .balance == -2: # links h¨oher
8 t23 = self . ltree . rtree ; t1 = self . ltree . ltree
9 if not t23: self . simpleRight()
10 elif t1 and t23.height ≤ t1. height : self . simpleRight()
11 else: self . doubleRight()
Listing 3.7: Die Methode balance() entscheidet, ob ¨uberhaupt balanciert werden muss und
wenn ja, welche der vier Rotationen angewendet werden soll.
Wir beschreiben im Folgenden exemplarisch zwei der vier verschiedenen Rotationen im
Detail:
Einfache Linksrotation (Abbildung 3.8(a)): Hier ist der innere im h¨oheren Teilbaum
beﬁndliche Enkel t23 von a nicht h¨oher als der ¨außere Enkel t4. Der schwach ge-
zeichnete Teil der Abbildung deutet an, dass der innere Enkel auch gleich hoch
sein kann als der ¨außere Enkel. Die Rotation ”hebt“ nun as rechtes Kind b samt
dessen rechten Teilbaum t4 um eine Ebene nach oben, indem b zur neuen Wurzel
gemacht wird. Entscheidend ist hier, dasst4 – der Teilbaum, durch den der H¨ohen-
unterscheid von 2 entsteht – nach der Rotation eine Ebene h ¨oher aufgeh¨angt ist
als vor der Rotation. Der Knoten a wird zum linken Kind von b (da a<b bleibt
die Eigenschaft eines Suchbaums erhalten) und a beh¨alt seinen linken Teilbaum
t1; dadurch sinkt das H ¨ohenniveau von t1 durch die Rotation. Das ist jedoch
unkritisch, da die H ¨ohe von t1 um 2 geringer war als die H ¨ohe von t2. Der Teil-
baum t23 wird zum rechten Teilbaum von a. Da alle Schl ¨usselwerte in t23 kleiner
als a.key und gr¨oßer als b.key sind, bleibt auch hier die Eigenschaft des bin ¨aren
Suchbaums erhalten. Folgendes Listing zeigt eine entsprechende Implementierung
in Form einer Methode
simpleLeft() der Klasse AVLTree:
1 def simpleLeft( self ):
2 a = self ; b = self . rtree
3 t1 = a. ltree
4 t23 = b. ltree
5 t4 = b.rtree
6 newL = AVLTree(a.key, t1, t23, a.val)
7 self .key = b.key ; self . ltree = newL ; self. rtree = t4 ; self . val = b.val
Doppelte Linksrotation (Abbildung 3.8(c)): Hier ist der innere im h¨oheren Teilbaum
beﬁndliche Enkel (der seinerseits aus t2 und t3 besteht) von a h¨oher als der ¨außere
Enkel t4. Der schwach gezeichnete Teil der Abbildung deutet an, dass einer der

## Seite 77

62 3 Suchalgorithmen
beiden Teilb¨aume des Enkels auch um eins niedriger sein kann als der andere
Teilbaum. Hier wird zun ¨achst eine Rechtsrotation des Teilbaums mit Wurzel b
ausgef¨uhrt; dies bringt zwar noch nicht den gew ¨unschten H¨ohenausgleich, jedoch
wird so die Voraussetzung f ¨ur die Ausf ¨uhrung einer Einfachrotation hergestellt:
der innere Enkel ist nicht mehr h ¨oher als der ¨außere Enkel. Eine anschließende
Linksrotation f¨uhrt dann zum Erfolg. Folgendes Listing zeigt eine entsprechende
Implementierung in Form einer Methode
doubleLeft() der Klasse AVLTree:
1 def doubleLeft( self ):
2 a = self ; b = self . rtree ; c = self . rtree. ltree
3 t1 = a. ltree
4 t2 = c. ltree
5 t3 = c.rtree
6 t4 = b.rtree
7 newL = AVLTree(a.key, t1, t2, a.val)
8 newR = AVLTree(b.key, t3, t4, b.val)
9 self .key = c.key ; self . ltree = newL ; self. rtree = newR ; self.val = c.val
Aufgabe 3.15
Implementieren Sie . . .
(a) . . . eine Methode simpleRight der Klasse AVLTree, die eine einfache Rechtsro-
tation realisiert.
(b) . . . eine Methode doubleRight der Klasse AVLTree, die eine Doppel-Rechts-Ro-
tation realisiert.
Aufgabe 3.16
Um wie viel kann sich die L ¨ange des l ¨angsten Pfades mit der L ¨ange des k ¨urzesten
Pfades (von der Wurzel zu einem Blatt) eines AVL-Baums h¨ochstens unterscheiden?

## Seite 78

3.3 Rot-Schwarz-B ¨aume 63
3.3 Rot-Schwarz-B ¨aume
110
43 145
21 89
9 30
6 17
2 7
1 3
12 19
16 18
27 38
24 28
29
33 42
31 36
75 106
58 84
49 70
45 54
52 55
50
65 74
63 69
60 64 67
82 86
80 83
78 81
85 88
96 108
91 99
90 93
92 94
95
97 102
98 101 103
107 109
129 164
123 135
115 126
114 118
117 121
124 127
131 139
130 132
134
137 142
138 140
156 180
149 159
148 153
151 154
150
157 161
169 190
167 173
166 168 171 176
170 172 175 178
186 193
183 189
182 184
181 185
187
192 197
196 199
Ein Rot-Schwarz-Baum, ist ein balancierter bin ¨arer Suchbaum; jeder Knoten in einem
Rot-Schwarz-Baum enth¨alt eine zus¨atzliche Information, die angibt, ob der Knoten rot
oder schwarz ist. Rot-Schwarz-B ¨aume generieren im Vergleich zu AVL-B ¨aumen einen
etwas geringeren Balancierungsaufwand, neigen auf der anderen Seite jedoch dazu, etwas
gr¨oßere Pfadl¨angendiﬀerenzen aufzuweisen als AVL-B¨aume.
Man kann einen Rot-Schwarz-Baum ganz ¨ahnlich implementieren, wie einen gew ¨ohnli-
chen bin¨aren Suchbaum, nur dass zus ¨atzlich ein Attribut self .c mitgef¨uhrt wird, das
die Farbe des jeweiligen Knotens speichert.
1 RED,BLACK = 0,1
2 class RBTree(object):
3 def init ( self , color, key, ltree=None, rtree=None, val=None):
4 self . l = ltree
5 self .r = rtree
6 self . val = val
7 self .c = color
8 self .key = key
Der ¨Ubersichtlichkeit halber verzichten wir darauf, die Klasse RBTreevon BTreeerben
zu lassen. Die Gemeinsamkeiten dieser beiden Klassen sind ohnehin etwas geringer als
die Gemeinsamkeit zwischen AVLTreeund BTree.
F¨ur jeden Knoten eines Rot-Schwarz-Baumes m ¨ussen die folgenden beiden Invarianten
gelten:
1. Invariante: Kein roter Knoten hat einen roten Elternknoten.
2. Invariante: Jeder Pfad von der Wurzel zu einem Blatt enth ¨alt die gleiche Anzahl
schwarzer Knoten.
Diese Invarianten m¨ussen ggf. nach einer Einf¨uge- oder L¨oschoperation wiederhergestellt
werden.
Diese beiden Invarianten garantieren, dass sich die H ¨ohen der beiden Teilb ¨aume eines
Knotens nicht zu stark unterscheiden k¨onnen. Deshalb rechnet man Rot-Schwarz-B¨aume
auch der Klasse der balancierten B ¨aume zu. Zwei verschiedene Pfade von der Wurzel
zu einem Blatt k ¨onnen sich um h ¨ochsten den Faktor ”Zwei“ unterscheiden, da beide
die gleiche Anzahl schwarzer Knoten enthalten m¨ussen und zwischen je zwei schwarzen

## Seite 79

64 3 Suchalgorithmen
Knoten auf diesem Pfad sich h¨ochstens ein roter Knoten beﬁnden kann. Die H¨ohe eines
Rot-Schwarz Baumes ist daher auch im schlechtesten Fall O(log n); insofern kann man
Rot-Schwarz-B¨aume als balancierte bezeichnen.
Abbildung 3.9 zeigt ein Beispiel eines Rot-Schwarz-Baums.
30
103
58
17
19 33
31 38
52
70
63 81
89
99
92
96 90
2
49
Abb. 3.9: Beispiel eines Rot-Schwarz-Baumes; man sieht, dass es sich zun ¨achst um einen
bin¨aren Suchbaum handelt, man sieht, dass kein roter Knoten einen roten Elternknoten besitzt,
und dass jeder Pfad von der Wurzel zu einem Blatt die gleiche Anzahl schwarzer Knoten enth ¨alt
– in diese Falle sind dies drei schwarze Knoten (bzw. vier schwarze Knoten, wenn wir uns
die leeren Knoten schwarzgef ¨arbt denken). Außerdem ist angedeutet, dass wir uns die leeren
Knoten alle als schwarze Knoten denken; folglich sind f ¨ur die Blattknoten prinzipiell beide
Farben m¨oglich.
3.3.1 Einf ¨ugen
Da Rot-Schwarz-B¨aume bin¨are Suchb¨aume sind, ist die Suchfunktion bei Rot-Schwarz-
B¨aumen genau gleich wie die Suchfunktion bei bin ¨aren Suchb¨aumen. Bei der Realisie-
rung der Einf¨ugeoperation muss jedoch darauf geachtet werden, dass durch das Einf¨ugen
eines neuen Knotens die beiden Invarianten nicht verletzt werden. Wir gehen beim
Einf¨ugen eines neuen Knotens v so vor, dass wir zun ¨achst v als neuen roten Knoten
so in den Rot-Schwarz-Baum einf ¨ugen, wie wir dies auch bei herk ¨ommlichen bin¨aren
Suchb¨aumen getan haben. Dadurch ist zwar Invariante 2 erhalten (da wir keinen neuen
schwarzen Knoten einf ¨ugen, bleibt die Anzahl der schwarzen Knoten auf jedem Pfad
unver¨andert), Invariante 1 k¨onnte dadurch jedoch verletzt werden. Abbildung 3.10 zeigt
als Beispiel die Situation, nachdem der Schl ¨usselwert ”42“ in den Rot-Schwarz-Baum
aus Abbildung 3.9 eingef ¨ugt wurde – als Folge wird dabei tats ¨achlich Invariante 1 ver-
letzt.
Folgendermaßen eliminieren wir nach solch einer Einf¨ugeoperation m¨ogliche Verletzun-
gen der Invariante 1: Wir laufen vom eingef ¨ugten Blatt bis hin zur Wurzel durch den
Rot-Schwarz-Baum und eliminieren in O(log n) Schritten sukzessive alle Verletzungen
der Invariante 1 auf diesem Pfad. Hierbei muss tats ¨achlich der ganze Pfad (der L ¨ange
O(log n)) ¨uberpr¨uft werden, da die Eliminierung einer Verletzung auf H¨ohe ieine weitere
Verletzung auf H¨ohe i−1 nach sich ziehen kann.

## Seite 80

3.3 Rot-Schwarz-B ¨aume 65
30
103
58
17
19 33
31 38
52
70
63 81
89
99
92
96 90
2
49
42 ⇒Invariante 1 verletzt
Abb. 3.10: Situation, nachdem ein neuer (roter) Knoten mit Schl ¨ussel k = 42 in den Rot-
Schwarz-Baum aus Abbildung 3.9 wie in einen herk ¨ommlichen bin ¨aren Suchbaum eingef ¨ugt
wurde. Wie man sieht, wird dadurch Invariante 1 verletzt.
Abbildung 3.11 zeigt alle vier m ¨oglichen Konstellationen, die die Invariante 1 verletzen
und die eine Rebalancierung erfordern.
In Abbildung 3.10 liegt an der ”Stelle“, die zur Verletzung der Invariante 1 f ¨uhrt, die
vierte Konstellation vor. Abbildung 3.12 zeigt den Rot-Schwarz-Baum nach Wiederher-
stellen der Invariante 1, die durch Abbildung der vierten Konstellation auf die einheit-
liche Form entsteht.
Implementierung. Listing 3.8 zeigt eine m¨ogliche Implementierung der Einf¨uge-Ope-
ration RBTree.insert.
1 class RBTree(object):
2 ...
3 def insert( self ,x, val=None):
4 self . insert (x, val)
5 self .c = BLACK
6
7 def insert ( self ,x, val=None):
8 if x < self .key:
9 if not self . l :
10 self . l= RBTree(RED,x)
11 else:
12 self . l . insert (x)
13 elif x > self .key:
14 if not self .r:
15 self .r = RBTree(RED,x)
16 else:
17 self .r. insert (x)
18 self . balance()
Listing 3.8: Implementierung der Einf ¨uge-Operation in einen Rot-Schwarz-Baum

## Seite 81

66 3 Suchalgorithmen
y
z x
a b c d
y
x c
b a
d x
y
2.
d
a
z
y
3.
a
d
c b
y
z
4.
a
b
c d
1.
=⇒ =⇒
z z x x
=⇒ =⇒
b c
Abb. 3.11:Alle vier Situationen, in denen beim rekursiven Aufstieg rebalanciert werden muss.
Jede dieser vier Konstellationen kann durch Abbildung auf eine einheitliche – im Bild unten
dargestellte – Form ”repariert“ werden.
Die Wurzel des Baumes wird nach Ausf ¨uhrung der Einf ¨ugeoperation stets schwarz
gef¨arbt (Zeile 5). Die eigentliche rekursiv implementierte Einf¨ugeoperation beﬁndet sich
in der Funktion insert . Zun¨achst wird in Zeile 8 bzw, Zeile 13 ¨uberpr¨uft, ob der ein-
zuf¨ugende Schl¨usselwert x in den linken Teilbaum (fallsx < self .key) oder in den rechten
Teilbaum (fallsx > self .key) einzuf¨ugen ist. Ist der linke bzw. rechte Teilbaum leer (d. h.
gilt not self . l bzw. not self .r), so wird ein neuer ein-elementiger Rot-Schwarzbaum
mit rotem Knoten erzeugt und als linkes bzw. rechtes Kind eingef ¨ugt – dies geschieht
in Zeile 10 bzw. Zeile 15. Ist der linke bzw. rechte Teilbaum nicht leer, so wird insert
rekursiv aufgefrufen. Ganz am Ende der Einf ¨ugeprozedur – und damit beim rekursi-
ven Aufstieg – wird die Funktion balance aufgerufen, die bei Bedarf die Invarianten
wiederherstellt und damit rebalanciert.
Listing 3.9 zeigt die Implementierung der balance-Funktion, die die Invarianten wie-
derherstellt.
In den Zeilen 6, 9, 12 und 15 wird jeweils getestet, ob eine der in Abbildung 3.11 gra-
phisch dargestellten vier Situationen zutriﬀt. Wir w ¨ahlen f¨ur die weiteren Erkl¨arungen
als Beispiel den f¨ur die Situation 1 zust¨andigen Code aus; die drei anderen F¨alle k¨onnen
analog erkl¨art werden. Situation 1 liegt genau dann vor, wenn . . .
1. . . . der linke Teilbaum vons und wiederum dessen linker Teilbaum nicht leer sind,
d. h. wenn ”not s.l“ und ”not s.l . l“ gelten3.
2. . . . und wenns. l und s. l . l rot gef¨arbt sind, wenn also gilt, dass”s. l .c == s. l . l .c
== RED“.
3Pythons Wert ”None“ entspricht in booleschen Formeln dem logischen Wert ”Falsch“; daher kann
mittels ”if not s.l ... “ ¨uberpr¨uft werden, ob s. l auf einen Rot-Schwarz-Baum zeigt, oder stattdessen
einen None-Wert enth¨alt.

## Seite 82

3.3 Rot-Schwarz-B ¨aume 67
33
38
30
58
17
19 522
49
33
38
42
...
31
Instanzen:
a =
b =
c =
d =
x =
y =
z = 42
31
Abb. 3.12:Der Rot-Schwarz-Baum nach Einf¨ugen des Schl¨usselwertes 42 und nach Wiederher-
stellen der Invariante 1. In diesem Falle ist hierf ¨ur nur eine einzige Rebalancierung notwendig.
Rechts im Bild sind f ¨ur den einen durchgef ¨uhrten Rebalancierungs-Schritt – dieser entspricht
Situation 4 – die notwendigen Instanzen f ¨ur die in Abbildung 3.11 verwendeten Platzhalter
angegeben, also f¨ur die Teilb¨aume a,b,c,d und f¨ur die Knoten x,y,z aus Abbildung 3.11.
In Abbildung 3.13 ist nochmals die Situation 1 zusammen mit den darauf zu mappenden
Zweigen des Baumes s dargestellt.
y
x c
b a
d
z
s. l . l . l
s.r
s. l .r
s. l . l .r
s
s. l . l
s. l
Abb. 3.13: Die erste der vier m ¨oglichen Situationen, in denen rebalanciert werden muss.
Die Abbildung stellt die Zuordnung der Variablen x,y,z und a,b,c,d auf die entsprechenden
Knoten bzw. Teilb¨aume des Baumes s dar, die mittels Indizierung angesprochen werden k ¨onnen
– nat¨urlich aber nur, wenn die Methode getitem entsprechend deﬁniert wurde.
Liegt Situation 1 vor, so wird also der Variablen x die in s. l . l gespeicherten Werte, der
Variablen y die in s. l gespeicherten Werte und der Variablen z die in s gespeicherten
Werte zugewiesen. W ¨ahrend die Variablen x, y und z Knoten-Werte (d. h. das key-
Attribut als erste Komponente zusammen mit demval-Attribut eines Knotens als zweite
Komponente) enthalten, sollten den Variablena, b, c und d ganze Teilb¨aume zugewiesen
werden – dies ist auch aus der Darstellung in Abbildung 3.11 ersichtlich. Variable a
erh¨alt in Situation 1 den Wert s. l . l . l, Variable b erh¨alt den Wert s. l . l .r, Variable c
erh¨alt den Wert s. l .r und Variable d erh¨alt den Wert s.r. Schließlich wird in den Zeilen
20 und 21 in Listing 3.9 gem ¨aß den in Abbildung 3.11 gezeigten Regeln der neue linke
und der neue rechte Teilbaum erzeugt. Schließlich wird in Zeile 22 die rebalancierte
Variante des Rot-Schwarz-Baumes generiert.

## Seite 83

68 3 Suchalgorithmen
1 class RBTree(object):
2 ...
3 def balance( self ):
4 s = self
5 if s.c==RED: return s
6 if s. l and s.l. l and s.l.c == s.l.l .c == RED: # Fall 1:
7 y = (s.l .key, s. l . val) ; x = (s.l . l .key, s. l . l . val) ; z = (s.key, s. val)
8 a = s.l . l . l ; b = s.l . l .r ; c = s.l .r ; d = s.r
9 elif s. l and s.l.r and s.l.c == s.l.r.c == RED: # Fall 2:
10 x = (s.l .key, s. l . val) ; y = (s.l .r.key, s. l .r. val) ; z = (s.key,s. val)
11 a = s.l . l ; b = s.l .r. l ; c = s.l .r.r ; d = s.r
12 elif s.r and s.r.l and s.r.c == s.r.l.c == RED: # Fall 3:
13 x = (s.key, s. val) ; y = (s.r. l .key, s.r. l . val) ; z = (s.r.key, s.r. val)
14 a = s.l ; b = s.r. l . l ; c = s.r. l .r ; d = s.r.r
15 elif s.r and s.r.r and s.r.c == s.r.r.c == RED: # Fall 4:
16 x = (s.key, s. val) ; y = (s.r.key, s.r. val) ; z = (s.r.r.key, s.r.r. val)
17 a = s.l ; b = s.r. l ; c = s.r.r. l ; d = s.r.r.r
18 else:
19 return s
20 newL = RBTree(BLACK,x[0], a, b, x[1])
21 newR = RBTree(BLACK,z[0], c, d, z[1])
22 self .c = RED ; self.key = y[0] ; self . l = newL ; self.r = newR ; self.val = y[1]
Listing 3.9:Implementierung der Rebalancierung, d. h. Eliminierung von Verletzungen der In-
variante 1, die beim Einf ¨ugen eines neuen roten Blattes in einen Rot-Schwarz-Baum entstehen
k¨onnen.
Aufgabe 3.17
(a) Wie hoch w ¨are ein (fast) vollst¨andiger bin¨arer Suchbaum, der 300000 Elemente
enth¨alt?
(b) Wie hoch k ¨onnte ein Rot-Schwarz-Baum maximal sein, der 300000 Elemente
enth¨alt?
Aufgabe 3.18
Schreiben Sie eine Methode RBTree.inv1Verletzt, die testet, ob es einen Knoten im
Rot-Schwarz-Baum gibt, f ¨ur den die Invariante 1 verletzt ist, d. h. ob es einen ro-
ten Knoten gibt, dessen Vorg ¨anger ebenfalls ein roter Knoten ist. Ein Aufruf von
inv1Verletzt soll genau dann True zur¨uckliefern, wenn die Invariante 1 f ¨ur minde-
stens einen Knoten verletzt ist.

## Seite 84

3.3 Rot-Schwarz-B ¨aume 69
Aufgabe 3.19
Schreiben Sie eine Methode, die ¨uberpr¨uft, ob die Invariante 2 verletzt ist.
(a) Schreiben Sie hierf ¨ur zun¨achst eine Methode RBTree.anzSchwarzKnoten, die ein
Tupel (x,y) zur¨uckliefern soll, wobei in x die minimale Anzahl schwarzer Knoten
auf einem Pfad von der Wurzel zu einem Blatt und in y die maximale Anzahl
schwarzer Knoten auf einem Pfad von der Wurzel zu einem Blatt zur¨uckgegeben
werden soll.
(b) Schreiben Sie nun eine Methode RBTree.inv2Verletzt, die genau dannTrue zur¨uck-
liefern soll, wenn die Invariante 2 f ¨ur den entsprechenden Rot-Schwarz-Baum
verletzt ist.
Aufgabe 3.20
Vergleichen Sie die Performance des Python-internen dict-Typs mit der vorgestellten
Implementierung von rot-schwarz B¨aumen folgendermaßen:
(a) F ¨ugen sie 1 Mio zuf ¨allige Zahlen aus der Menge {1,... 10Mio}jeweils in einen
Python-dict und in einen Rot-Schwarz-Baum ein, messen sie mittels time() je-
weils die verbrauchte Zeit und vergleichen sie.
(b) F ¨uhren sie nun 1 Mio Suchdurchg¨ange auf die in der vorigen Teilaufgabe erstell-
ten Werte aus, und messen sie wiederum mittels timeit die verbrauchte Zeit und
vergleichen sie.
3.3.2 L ¨oschen
Das L¨oschen eines Knoten v in einem Rot-Schwarz-Baum besteht grunds¨atzlich aus drei
Schritten:
Schritt 1: Ein Knoten v in einem Rot-Schwarz-Baum wird zun¨achst gel¨oscht als w¨are
es ein Knoten in einem herk ¨ommlichen bin¨aren Suchbaum: Besitzt der zu l ¨oschende
Knoten zwei (nicht-leere) Kinder als Nachfolger, so ersetzt man das Schl¨ussel-Wert-Paar
von v durch das Schl¨ussel-Wert-Paar des minimalen Knotens m des rechten Teilbaums
und l¨oscht anschließend m – dies entspricht der Darstellung von Fall (b) in Abbildung
3.5 auf Seite 55. Da m mindestens einen Blattknoten besitzt, kann man so das Problem
auf das L¨oschen eines Knotens mit mindestens einem Blattknoten reduzieren.
Ist m ein schwarzer Knoten, so wird durch L ¨oschen von m die Invariante 2 verletzt,
die vorschreibt, dass jeder Wurzel-Blatt-Pfad in einem Rot-Schwarz-Baum die gleiche
Anzahl schwarzer Knoten besitzen muss. Dies wird vor ¨ubergehend dadurch ”ausgegli-
chen“, indem das eine schwarze Blatt von m einen doppelten Schwarz-Wert zugewiesen
bekommt.
Schritt 2: Nun propagiert man doppelte Schwarz-Werte den Baum soweit durch An-
wendung bestimmter Regeln (die unten aufgef ¨uhrten drei F ¨alle) nach oben, bis diese

## Seite 85

70 3 Suchalgorithmen
aufgel¨ost werden k ¨onnen. In der graphischen Darstellung dieser Regeln markieren wir
Doppelschwarze Knoten hierbei durch eine zus ¨atzliche Schwarz-Markierung ( ■). Ein
roter Knoten mit einer Schwarz-Markierung kann durch schwarz-f¨arben des roten Kno-
tens aufgel¨ost werden. Man beachte dass in den im Folgenden aufgef ¨uhrten drei F¨allen
der doppelschwarze Knoten immer das Linke Kind ist. Die F ¨alle, in denen der doppel-
schwarze Knoten das rechte Kind ist, sind symmetrisch, und nicht getrennt aufgef ¨uhrt.
(a) Der Geschwisterknoten eines doppelschwarzen Knotens ist schwarz und es gibt einen
roten Neﬀen. Dies ist der ”g¨unstigste“ Fall; die Schwarz-Markierung kann aufgel¨ost
werden.
b c d b
c db c
d
x
a
z
y
yza
x
a
x
zy
(b) Der Geschwisterknoten eines doppelschwarzen Knotens ist schwarz und beide Neﬀen
sind schwarz. Durch folgende Rotation kann die Schwarz-Markierung nach oben
weitergereicht werden.
y
b c
a
x
b c
a
x
y
(c) Der Geschwisterknoten eines doppelschwarzen Knotens ist rot. Dies erfordert zun¨achst
eine Rotation und verweist anschließend auf entweder Fall (a) oder Fall (b).
b c
y
a b
ca
x
xy
Schritt 3: Beﬁndet sich die Schwarz-Markierung an der Wurzel, wird sie einfach gel¨oscht.
Abbildung 3.14 zeigt als Beispiel die L ¨oschung eines schwarzen Knotens und das an-
schließende Rebalancieren gem¨aß obiger Regeln.

## Seite 86

3.3 Rot-Schwarz-B ¨aume 71
103
58
70
63 81
89
99
92
96 90
...
(a) Der Knoten mit Schl ¨usselwert ”63“ soll
gel¨oscht werden.
103
58
70
89
99
92
90
81
...
96
(b) Eines der Bl ¨atter dieses gel ¨oschten Kno-
tens wird doppelschwarz gef ¨arbt. Der Bruder
des doppelschwarzen Knotens ist rot; daher
kann die Rotation aus Fall (c) angewendet wer-
den.
103
58
89
99
92
96
...
81
70
90
(c) Der Geschwisterknoten des doppelschwar-
zen Knotens ist schwarz; Neﬀen existieren
nicht. Fall (b) wird also angewendet und die
Schwarz-Markierung wandert nach oben.
103
58
89
99
92
96 90
...
81
70
(d) Hier triﬀt die Schwarz-Markierung auf
einen roten Knoten und kann aufgel ¨ost wer-
den.
103
58
89
99
92
96 90
...
81
70
(e) Invariante 2 ist wiederhergestellt.
Abb. 3.14: Beispiel f¨ur das L ¨oschen eines Knotens aus einem Rot-Schwarz-Baum.

## Seite 87

72 3 Suchalgorithmen
3.4 Hashing
Auch das Hashing verfolgt (wie alle anderen in diesem Kapitel vorgestellten Suchalgo-
rithmen) das Ziel, das Einf ¨ugen, Suchen und L ¨oschen von Elementen aus einer großen
Menge von Elementen eﬃzient zu realisieren. Hashing verwendet jedoch ein im Vergleich
zu den bisher vorgestellten Methoden vollkommen anderes und noch dazu einfach zu
verstehendes Mittel, um diese Operationen zu implementieren. Die Methode des Ha-
shing ist in vielen Situationen sehr performant. Mittels Hashing ist es m ¨oglich, das
Einf¨ugen, Suchen und L ¨oschen4 mit verh¨altnism¨aßig einfachen Mitteln mit einer Lauf-
zeit von O(1) zu implementieren. Auch die dem Python Typ dict zugrunde liegende
Implementierung verwendet Hashing. Zur Veranschaulichung werden wir in diesem Ab-
schnitt das dem dict-Typ zugrundeliegende Hashing nachprogrammieren und einem
eigenen Typ OurDict zugrunde legen.
F¨ur die Implementierung des Hashing ist es zun ¨achst erforderlich, ein gen¨ugend großes
Array (bzw. in Python: eine gen¨ugend große Liste der L¨ange n) zur Verf¨ugung zu stellen,
die sog. Hash-Tabelle t . Die Grundidee besteht darin, einen (Such-)Schl ¨ussel k mittels
einer sog. Hash-Funktion h auf einen Index h(k) der Hash-Tabelle abzubilden; optima-
lerweise sollte dann der zu k geh¨orige Wert v an diesem Index der Tabelle gespeichert
werden; mittels t [h(k) ] kann man also in konstanter Zeit – der Zeit n ¨amlich, um den
R¨uckgabewert von h zu berechnen – auf den Wert v zugreifen. Abbildung 3.15 zeigt
diese Situation.
Hashtabelle t . . . t[n−2]
geh¨orender Eintrag
Zu Schl¨ussel k
t[n−1]. . .t[1]t[0] t[h(k)]
Abb. 3.15:Hashtabelle t der Gr ¨oße n. Der zum Suchschl ¨ussel k passende Eintrag beﬁndet sich
(optimalerweise) an Tabellenposition h(k), wobei h die verwendete Hashfunktion ist.
Sind die Schl¨ussel allesamt ganze Zahlen, so w ¨are die einfachst denkbare Hashfunktion
einfach die Identit¨at, also h(i) = i, d. h. jeder Schl¨ussel k w¨urde so auf den k-ten Eintrag
in der Hashtabelle abgebildet werden. In der Praxis ist dies jedoch in der Regel nicht
sinnvoll: werden etwa 64 Bit f ¨ur die Darstellung einer Ganzzahl verwendet, so gibt es
264 verschiedene Schl¨ussel. W¨urde man die Identit¨at als Hash-Funktion w¨ahlen, so h¨atte
diese auch 264 verschiedene m¨ogliche Werte und man m¨usste folglich eine Hash-Tabelle
mit 264 Eintr¨agen zur Verf¨ugung stellen. Dies entspricht einer Hash-Tabelle der Gr ¨oße
von ca. 16 Mio Terabyte, vorausgesetzt man veranschlagt nur ein Byte Speicherplatz pro
Tabelleneintrag. ¨Ublicherweise ist also der Wertebereich aller (sinnvollen und praktisch
eingesetzten) Hash-Funktion viel kleiner als deren Deﬁnitionsbereich.
4Gelegentlich werden diese drei Operationen, n ¨amlich Einf¨ugen, Suchen, L¨oschen, auch als die sog.
”Dictionary Operations“ bezeichnet.

## Seite 88

3.4 Hashing 73
3.4.1 Hash-Funktionen
Eine sinnvolle, praktisch einsetzbare Hashfunktion sollte folgende Eigenschaften besit-
zen:
1. Sie sollte jeden Schl ¨ussel k auf einen Wert aus {0,...,n −1}abbilden.
2. Sie sollte ”zufallsartig“ sein, d. h. sie sollte, um Kollisionen zu vermeiden, vorhan-
dene Schl¨ussel m¨oglichst gleichm¨aßig ¨uber die Indizes streuen.
3. Sie sollte m ¨oglichst einfach und schnell berechenbar sein.
Aufgabe 3.21
Welche dieser Eigenschaften erf ¨ullt die ”einfachst denkbare Hashfunktion“, also die
Identit¨at? Welche Eigenschaften werden nicht erf¨ullt?
Wir stellen im Folgenden zwei unterschiedliche Methoden vor, Hash-Funktionen zu ent-
werfen.
Die Kongruenzmethode. Zun¨achst wandelt man den Schl ¨ussel k in eine Zahl
x = integer(k) um und stellt anschließend mittels Restedivision durch eine Primzahl
p sicher, dass der berechnete Hashwert sich im Bereich {0,..., p -1}beﬁndet, wobei
optimalerweise p die Gr¨oße der zur Verf¨ugung stehenden Hash-Tabelle ist. Es gilt also
h(k) = integer(k) % p
(wobei ”%“ Pythons Modulo-Operator darstellt). Und tats ¨achlich erf ¨ullt diese Hash-
Funktion die obigen drei Kriterien: Man kann zeigen, dass sie – vorausgesetzt p ist
eine Primzahl – zufallsartig ist, sie bildet den Schl ¨ussel auf den Indexbereich der Hash-
Tabelle ab und sie ist einfach zu berechnen.
Da es oft der Fall ist, dass die Schl ¨usselwerte vom Typ String sind, betrachten wir als
Beispiel die Umwandlung eines Strings in eine Zahl. Hat man es mit verh ¨altnism¨aßig
kurzen Strings zu tun, so k ¨onnte man die integer-Funktion einfach dadurch implemen-
tieren, dass man die ASCII-Werte der einzelnen Buchstaben ”nebeneinander“ schreibt
und dadurch eine (recht große) Zahl erh ¨alt, die man mittels Modulo-Rechnung in die
Index-Menge {0,..., p −1}einbettet. So w¨are etwa
integer('KEY') = 0 b 01001011
 
ord('K')
01000101  
ord('E')
01011001

 
ord('Y')
= 4932953
W¨ahlt man f¨ur p etwa den Wert 163, erh¨alt man so:
h('KEY') = 4932953 %163 = 84
Ein entsprechender Hash-Algorithmus mit zugrundeliegender Hash-Tabelle t mit
len(t) == 163 w ¨urde somit den zum Schl ¨ussel 'KEY' geh¨orenden Wert in t[84] su-
chen.
Folgendes Listing zeigt die Implementierung dieser Hash-Funktion in Python.

## Seite 89

74 3 Suchalgorithmen
1 def hashStrSimple(s,p):
2 v=0
3 for i in range(len(s )):
4 j = len(s) -1 -i
5 v += ord(s[j]) <<(8 *i)
6 return v %p
Listing 3.10: Implementierung einer einfachen Hash-Funktion auf Strings
Pythons ”<<“-Operator schiebt alle Bits einer Zahl um eine bestimmte Anzahl von
Positionen nach links. In der for-Schleife ab Zeile 3 lassen wir die Laufvariable i ¨uber
alle Indexpositionen des Strings laufen und berechnen so die folgende Summe (wobei
n= len(s)):
∑n−1
i=0 ord(sn−1−i)<<(8*i) (3.3)
= ord(sn−1)<<0 + ord(sn−2)<<8 + ... + ord(s0)<<(8*(n -1)) (3.4)
zur¨uckgeliefert wird diese Zahl modulo der ¨ubergeben Zahl p, die optimalerweise eine
Primzahl sein sollte.
Aufgabe 3.22
Schreiben Sie mittels einer Listenkomprehension die in Listing 3.10 gezeigte Funktion
hashStrSimple als Einzeiler.
Alternativ k¨onnte der in Listing 3.10 implementierte Algorithmus durch das sog. Horner-
Schema implementiert werden.
∑n−1
i=0 ord(sn−1−i)<<(8*i)
= ord(sn−1) + (ord(sn−2) + (ord(sn−3) + (...) <<8)<<8)<<8
Beispielsweise k¨onnte nun die Berechnung des Hash-Werts von 'longKey' folgender-
maßen erfolgen:
ord(y) + (ord(e) + (ord(K) + (ord(g) + (ord(n) + (ord(o) +ord(l)< <8)< <8)< <8)< <8)< <8)%p
Das Horner-Schema kann man in Python elegant unter Verwendung derreduce-Funktion
implementieren:
1 def horner(l,b):
2 return reduce(lambda x,y: y +(x<<b), l)
Listing 3.11:Implementierung des Horner-Schemas mittels der higher-order reduce-Funktion.

## Seite 90

3.4 Hashing 75
Die reduce-Funktion ist eine higher-order-Funktion. Sie benutzt die als erstes Argument
¨ubergebene Funktion dazu, die Elemente der als zweites Argument¨ubergebenen Sequenz
zu verkn ¨upfen. Das erste Argument x, der Argument-Funktion, steht hierbei f ¨ur den
bereits aus den restlichen Elementen berechneten Wert; das zweite Argument y der
Argument-Funktion steht hierbei f¨ur ein Element aus l.
Aufgabe 3.23
Implementieren Sie das Horner-Schema in einer Schleife – anstatt, wie in Listing 3.11
die Python-Funktion reduce zu verwenden.
W¨ahrend die Gr¨oße des berechneten Hashwerts beschr¨ankt ist (denn:h(k) ∈{0,..., p -1}),
k¨onnen jedoch, je nach L ¨ange des gehashten Strings, sehr große Zwischenergebnisse
entstehen. Man k¨onnte eine weitere Steigerung der Performance (und sei es nur Platz-
Performance) erreichen, indem man das Entstehen sehr großer Zwischenergebnisse ver-
meidet. Dazu k¨onnen die folgenden Eigenschaften der Modulo-Funktion ausgenutzt wer-
den:
(a +b) %p = ( a%p +b%p) % p
(a*b) % p = ( a%p * b%p) % p
Man kann also, ohne das Endergebnis zu beeinﬂussen, in jedem Schleifendurchlauf auf
das Zwischenergebnis eine Modulo-Operation anwenden und so sicherstellen, dass keine
Zahlen entstehen, die gr¨oßer als psind. Listing 3.12 zeigt eine Python-Implementierung
des Horner-Schemas, die zus ¨atzlich die eben beschriebene Eigenschaft der Modulo-
Funktion ausnutzt.
1 def horner2(l,b,p):
2 return reduce(lambda x,y: y +(x<<b)%p, l) %p
Listing 3.12: Implementierung einer f ¨ur lange Strings performanteren Hash-Funktion un-
ter Verwendung des Horner-Schemas und der eben vorgestellten Eigenschaften der Modulo-
Funktion
Mittels horner2 kann eine im Vergleich zu der in Listing 3.10 gezeigten Funktion
hashStrSimple performantere Hash-Funktion geschrieben werden:
1 def hashStr(s,p):
2 return horner2(map(ord,s),8,p)
Aufgabe 3.24
Verwenden Sie, statt reduce und map, eine Schleife, um die in Listing 3.12 gezeigte
Funktion hashStr zu implementieren.

## Seite 91

76 3 Suchalgorithmen
Aufgabe 3.25
Ganz oﬀensichtlich ist nicht, welche der Funktionen horner und horner2 tats¨achlich
schneller ist – auf der einen Seite vermeidet horner2 die Entstehung großer Zahlen
als Zwischenergebnisse; andererseits werden in horner2 aber auch sehr viel mehr
Operationen (n¨amlich Modulo-Operationen) ausgef ¨uhrt als in horner.
Ermitteln Sie empirisch, welcher der beiden Faktoren bei der Laufziet st¨arker ins Ge-
wicht f¨allt. Vergleichen Sie die Laufzeiten der beiden Funktionen horner und horner2
mit Listen der L¨ange 100, die Zufallszahlen zwischen 0 und 7 enthalten, mit Parame-
ter b = 3 und einer dreistelligen Primzahl. Verwenden Sie zur Zeitmessung Pythons
timeit-Modul.
Empirisches ”Bit-Mixen“. Die Kongruenzmethode liefert zwar i. A. gute Resultate,
in der Praxis sieht man jedoch des ¨ofteren andere, theoretisch zwar weniger gut ab-
gesicherte (bzgl. der ”Zuf¨alligkeit“) jedoch sehr performante und sich gut bew ¨ahrende
Hash-Funktionen. Eine solche Hash-Methode verwendet Python intern f¨ur das Hashing
in dict-Objekten. Listing 3.13 zeigt eine Nachimplementierung [14] des Algorithmus den
Python f¨ur das Hashing von Strings verwendet:
1 class string :
2 def hash ( self ):
3 if not self : return 0 # Der leere String
4 value = ord(self [0]) << 7
5 for char in self :
6 value = c mul(1000003, value) ^ ord(char)
7 return value ^ len( self )
8
9 def c mul(a, b):
10 return eval(hex((long(a) *b) &0xFFFFFFFFL)[: -1])
Listing 3.13: Implementierung des dem Python dict-Datentyp zugrundeliegenden Hash-
Algorithmus f¨ur Strings
Hierbei soll die Funktion c mul eine ¨ubliche C-Multiplikation simulieren, die zwei 32-Bit
Ganzzahlen multipliziert. Die Funktion hash liefert eine 32-Bit-Zahl zur ¨uck, deren
Bits (hoﬀentlich) m ¨oglichst gut ”durchgew¨urfelt“ wurden. Der ˆ-Operator verkn ¨upft
seine beiden Argumente bitweise durch eine logische XOR-Funktion; bitweise XOR-
Verkn¨upfungen sind ein h ¨auﬁg angewandtes Mittel, um die Bits einer Zahl m ¨oglichst
durcheinander zu w¨urfeln.
Um sp¨ater sicherzustellen, dass ein bestimmter Hashwert auch tats ¨achlich ein g¨ultiger
Index-Wert aus der gegebenen Hashtabelle t darstellt, also im Bereich {0,..., len(t)}
liegt, werden wir sp¨ater die iniederwertigsten Bits aus dem Hashwert extrahieren. Daf¨ur
ist es jedoch auch notwendig, dass die Gr ¨oße der Hash-Tabelle nicht eine Primzahl p,
sondern immer eine Zweierpotenz 2 i ist. Wir zeigen sp ¨ater in diesem Kapitel, wie eine
Implementierung dies mit einfachen Mitteln sicherstellen kann.

## Seite 92

3.4 Hashing 77
3.4.2 Kollisionsbehandlung
Die ”Zuf¨alligkeit“ der Hash-Funktion soll sicherstellen, dass unterschiedliche Schl ¨ussel
k und k′ mit k ̸= k′ mit m¨oglichst geringer Wahrscheinlichkeit auf den selben Index
abgebildet werden, d. h. dass mit m ¨oglichst geringer Wahrscheinlichkeit h(k) = h(k′)
gilt. Nehmen wir an, die Hash-Tabellethabe eine Gr¨oße von nEintr¨agen und mEintr¨age
sind bereits besetzt. Je gr ¨oßer der Belegungsgrad β = m/n einer Hashtabelle, desto
wahrscheinlicher werden jedoch Kollisionen – auch bei einer Hash-Funktion die eine
optimale ”Zuf¨alligkeit“ garantiert.
Als Kollision wollen wir die Situation bezeichnen, in der ein neu einzuf¨ugender Schl¨ussel
k durch die Hash-Funktion auf einen bereits belegten Eintrag in der Hashtabelle abge-
bildet wird, also t[h(k)] bereits mit dem Wert eines anderen Schl ¨ussls k′belegt ist, f ¨ur
den h(k) = h(k′) gilt.
Es gibt mehrere M ¨oglichkeiten, wie man mit dem Problem m ¨oglicher Kollisionen um-
gehen kann. Wir stellen zwei davon vor: Getrennte Verkettung und einfaches bzw. dop-
peltes Hashing.
Getrennte Verkettung. Bei der getrennten Verkettung legt man jeden Eintrag der
Hash-Tabelle als Liste an. Tritt eine Kollision ein, so wird der Eintrag einfach an die
Liste angeh¨angt. Abbildung 3.16 zeigt ein Beispiel einer Hash-Tabelle der Gr¨oße n= 11,
die eine bestimmte Menge von Schl¨usselwerten (vom Typ ”String“) enth¨alt, die mittels
getrennter Verkettung eingef¨ugt wurden. Der Index der Schl ¨ussel wurde dabei jeweils
mittels der Hash-Funktion h(k) = hashStr(k,11) bestimmt.
'du'
'you'
'er'
'sie'
1 0 2 3 4 5 6 7 8 9 10
'ihr'
'we'
'she'
'i'
'he'
'ich'
'wir'
'it''es'
Abb. 3.16: Eine Hash-Tabelle der Gr ¨oße n = 11, gef ¨ullt mit den String-
Werten [ 'ich','du','er','sie','es','wir','ihr','sie','i','you','he','she', 'it','we' ].
Als Hash-Funktion wurde die in Listing 3.12 beschriebene Funktion hashStr verwendet. Der
Belegungsfaktor ist in diesem Fall β = 13/11.
Anders als beim einfachen bzw. doppelten Hashing ist bei der getrennten Verkettung
theoretisch ein beliebig großer Belegungsfaktor m ¨oglich. Man kann ¨uber stochastische
Methoden zeigen, dass bei zuf¨allig gew¨ahlten Schl¨usseln, die durchschnittliche L¨ange der
Listen β betr¨agt, also gleich dem Belegungsfaktor ist. Das bedeutet, dass die Laufzeit
f¨ur eine. . .
. . . erfolglose Suche nach einem Schl ¨ussel c+ β betr¨agt, wobei c die Laufzeit f ¨ur die
Berechnung des Hash-Wertes des zu suchenden Schl¨ussel ist. Die an einem Eintrag
beﬁndliche Liste muss vollst¨andig durchsucht werden, bis festgestellt werden kann,
dass der Schl¨ussel sich nicht in der Hash-Tabelle beﬁndet.

## Seite 93

78 3 Suchalgorithmen
. . . erfolgreiche Suche nach einem Schl ¨ussel c+ β/2 betr ¨agt, denn im Durchschnitt
muss die Liste, die sich an einem Eintrag beﬁndet, bis zur H ¨alfte durchsucht
werden, bis der gesuchte Wert gefunden wurde.
Aufgabe 3.26
Wie groß ist die durchschnittliche Listenl¨ange f¨ur die Hashtabelle aus Abbildung 3.16
in der Theorie und konkret am Beispiel?
Einfaches und Doppeltes Hashing. Beim Einfachen bzw. Doppelten Hashing wird
bei einer Kollision ein alternativer freier Tabellenplatz gesucht. Das hat zur Folge, dass
bei diesen beiden Verfahren der Belegungsfaktor h ¨ochstens 1 sein kann, dass also stets
β ≤1 gelten muss.
Das einfache Hashing geht folgendermaßen vor: Soll der Schl ¨ussel k gespeichert werden
und ist die Hash-Tabellenposition h(k) bereits belegt, so wird versucht, k in der Tabel-
lenposition ( h(k) +1) %n zu speichern; ist diese wiederum belegt, so wird versucht k in
der Tabellenposition ( h(k) +2) %n zu speichern, usw.
Bei der getrennten Verkettung werden bei der Suche nach einem Schl ¨ussel k evtl. auch
weitere Schl¨ussel k′ untersucht, aber nur solche, die auf die gleiche Tabellenposition
gehasht werden; beim einfachen Hashing jedoch, kann es vorkommen, dass auch noch
Schl¨ussel mituntersucht werden, die auf andere Tabellenpositionen gehasht werden. Au-
ßerdem hat das einfache Hashing den Nachteil, dass eine starke Tendenz zur ”Clu-
sterung“ der belegten Eintr ¨age besteht; insbesondere unter diesen Clustern kann die
Suchperformance sehr leiden. Im Falle des einfachen Hashing betr ¨agt die Laufzeit . . .
 . . . f¨ur eine erfolglose Suche nach einem Schl ¨ussel 1
2 + 1
2(1−β)2 Schritte,
 . . . f¨ur eine erfolgreiche Suche nach einem Schl ¨ussel 1
2 + 1
2(1−β) Schritte.
wobei β jeweils den Belegungsfaktor der verwendeten Hash-Tabelle bezeichnet. Zur
Begr¨undung hierf ¨ur w¨are eine aufw ¨andige stochastische Rechnung notwendig, die wir
hier der Einfachheit halber nicht auﬀ ¨uhren.
Aufgabe 3.27
(a) F ¨ugen Sie mittels einfachem Hashing und Hash-Funktion h(k) = hashStr(k,11)
die folgenden Schl¨ussel in der angegebenen Reihenfolge in eine Hash-Tabelle der
Gr¨oße 11 ein:
'er', 'ihr', 'es', 'we', 'he', 'it', 'ich'
(b) Wie viele Schritte braucht man danach, um nach dem Schl¨ussel 'ord' zu suchen?
(c) Wie viele Schritte braucht man danach, um nach dem Schl ¨ussel 'le' zu suchen?

## Seite 94

3.4 Hashing 79
Beim sog. doppelten Hashing versucht man diese Cluster-Bildung zu vermeiden. Tritt in
Tabellenposition h(k) eine Kollision beim Suchen oder Einf¨ugen von Schl¨ussel k auf, wird
hierbei, statt bei der Position ( h(k) +1) %p fortzufahren, an der Position ( h(k) +u) %k
fortgefahren. Hierbei kann h(k) = ( k +u) %p als zweite Hash-Funktion betrachtet wer-
den, weshalb dieses Verfahren sich doppeltes Hashing nennt. Man kann tats¨achlich auch
zeigen, dass doppeltes Hashing im Durchschnitt weniger Tests erfordert als lineares Aus-
testen.
3.4.3 Implementierung in Python
Wir wollen die Funktionsweise des Python dict-Typs, der intern doppeltes Hashing ver-
wendet, hier nachprogrammieren. Wir erreichen dabei nat ¨urlich nicht die Performance
des dict-Typs, denn dieser ist in der Programmiersprache C implementiert; Python-
Code ist, da interpretiert, zwar nicht deutlich, aber immer noch etwas langsamer als
auf Performance optimierter C-Code.
Zun¨achst kann man f ¨ur die Eintr ¨age der Hash-Tabelle eine eigene Klasse deﬁnieren;
Listing 3.14 zeigt eine passende Klassendeﬁnition zusammen mit deren Konstruktor-
funktion init .
1 class Entry(object):
2 def init ( self ):
3 self .key = None
4 self .value = None
5 self .hash = 0
Listing 3.14: Deﬁnition der Klasse Entry f ¨ur die Eintr ¨age in die Hash-Tabelle
Jeder Eintrag besteht also aus einem Schl¨ussel, dem zugeh¨origen Wert und dem f¨ur den
Schl¨ussel berechneten Hash-Wert; aus Performance-Gr ¨unden ist es durchaus sinnvoll,
sich diesen zu merken anstatt ihn jedesmal neu zu berechnen.
Aufgabe 3.28
Deﬁnieren Sie sich eine Instanz der Methode str , um sich die f ¨ur den Benutzer
relevanten Daten von Objekten vom Typ Entry anzeigen zu lassen.
Listing 3.15 zeigt einen Teil der Deklaration der Klasse OurDict. Unser Ziel ist es,
durch diese Klasse OurDict die Funktionsweise des Python-internen Typs dict nachzu-
programmieren.
1 MINSIZE = 8
2 class OurDict(object):
3 def init ( self ):
4 self .used = 0
5 self . table=[]
6 while len(self . table)<MINSIZE:

## Seite 95

80 3 Suchalgorithmen
7 self . table .append(Entry())
8 self .mask = 7
9 self . size = MINSIZE
Listing 3.15: Deﬁnition der Klasse OurDict
Das Attribut used soll immer angeben, wie viele Schl¨ussel-Wert-Paare sich in der Hash-
Tabelle beﬁnden; das Attribut table speichert die eigentliche Hash-Tabelle; diese wird
in den Zeilen 6 und 7 initialisiert indem sie mit leeren Eintr ¨agen (die mittels Entry()
erzeugt werden) gef ¨ullt wird. Das Attribut mask enth¨alt eine Bit-Maske, die sp ¨ater
dazu verwendet wird, den zur Hash-Tabellengr¨oße passenden Teil eines Hash-Wertes zu
selektieren; dazu sp¨ater mehr.
Aufgabe 3.29
In den Zeilen 6 und 7 in Listing 3.15 werden die Eintr ¨age der Hash-Tabelle zun¨achst
mit leeren Entry()-Werten initialisiert. Was spricht dagegen, statt derwhile-Schleife,
dazu den *-Operator auf Listen zu verwenden, d. h. die Zeilen 5, 6 und 7 in Listing
3.15 zu ersetzen durch
self . table = [Entry()] * MINSIZE ?
Den zu einem Schl¨ussel geh¨orenden Wert kann man mittels der in Listing 3.16 gezeigten
Methode lookup nachschlagen.
1 class OurDict(object):
2 ...
3 def lookup( self , key):
4 hashKey = hashStr(key)
5 i = hashKey &self.mask # Selektion der ben ¨otigten Bits
6 entry = self . table [i ]
7 if entry.key==None or entry.key==key: # gefunden!
8 return entry
9
10 # Falls entry.key != key: wende zweite Hashfunktion an.
11 perturb = hashKey
12 while True:
13 i = (i<<2) + i +perturb +1
14 entry = self . table [i & self .mask]
15 if entry.key==None or entry.key==key:
16 return entry
17 perturb = perturb >> PERTURB SHIFT
Listing 3.16: Implementierung der lookup-Methode, die einen gegebene Schl ¨ussel im Dictio-
nary nachschl¨agt und den Eintrag zur ¨uckliefert

## Seite 96

3.4 Hashing 81
Zeile 4 berechnet zun ¨achst den Hash des Schl ¨ussels und verwendet dazu den in Listing
3.13 angegebenen Algorithmus. In Zeile 5 selektieren wir mittels der bitweisen Und-
Operation ”&“ die ben ¨otigten Bits des Hashs. Welche Bits aktuell ben ¨otigt werden,
h¨angt wiederum von der momentanen Gr ¨oße der Hash-Tabelle ab. In den Zeilen 7 und
8 wird schließlich der in self . table [i ] beﬁndliche Eintrag zur¨uckgeliefert, falls entweder
der Schl¨ussel dieses Eintrags mit dem Suchschl ¨ussel ¨ubereinstimmt, oder der Eintrag
noch leer war; stimmt der Schl ¨ussel jedoch nicht mit dem Suchschl ¨ussel ¨uberein, so
k¨onnte es sich um eine Kollision handeln, und es wird mittels einer zweiten Hash-
Funktion weiter nach einem Eintrag gesucht, der zu dem Schl ¨ussel passt. Hierbei gilt
f¨ur die zweite Hash-Funktion ein ¨ahnliches pragmatisches Prinzip wie f ¨ur die ”erste“
Hash-Funktion: die Bits m¨ussen m¨oglichst gut durcheinandergew¨urfelt werden, um eine
optimale Streuung zu gew ¨ahrleisten, um Clusterung zu vermeiden.
Aufgabe 3.30
Angenommen, unsere Hash-Tabelle hat eine Gr¨oße von 220 und enth¨alt 900 000 Werte.
Angenommen, wir w ¨urden keine zweite Hash-Funktion verwenden wollen, sondern
stattdessen einfaches Hashing.
(a) Passen Sie hierf ¨ur die while-Schleife in Zeile 12 aus Listing 3.16 so an, dass sie
den Schl¨ussel key unter der Annahme sucht, dass die Hash-Tabelle mit linearem
Hashing bef¨ullt wurde.
(b) Wie oft m ¨usste die so implementierte while-Schleife im Durchschnitt durchlau-
fen werden, bis ein in der Hash-Tabelle beﬁndlicher Schl ¨ussel gefunden wird?
(c) Wie oft m ¨usste die so implementierte while-Schleife im Durchschnitt durchlau-
fen werden, bis die lookup-Funktion ”merkt“, dass der zu suchende Schl ¨ussel
key sich nicht in der Hash-Tabelle beﬁndet?
Aufgabe 3.31
Passt man nicht genau auf, so kann es passieren, dass die while-Schleife in Zeile 12
aus Listing 3.16 eine Endlosschleife wird. Wie k ¨onnte dies passieren und wie genau
kann man sicherstellen, dass diese Schleife immer terminiert?
Wie werden aber die relevanten Bits des Hashs selektiert? Starten wir mit einem lee-
ren Dictionary, so hat zu Beginn die Hash-Tabelle 8 Eintr ¨age (siehe Zeile 1 und 9 in
Listing 3.15); um einen Schl ¨ussel auf eine Hash-Tabellenposition abzubilden, m ¨ussen
wir hier die letzten 3 Bits selektieren ( self .mask m¨usste in diesem Fall also den Wert
7 haben). Nehmen wir beispielsweise an, der Hash-Wert eines Schl ¨ussel w¨urde sich zu
hashKey = 18233 ergeben. Schreibt man nun den Inhalt von hashKey, self .mask und i
in Bin¨ardarstellung auf, so sieht man leicht, dass sich f¨ur den Wert von i durch bitweise
Und-Verkn¨upfung der Wert ”1“ ergibt:

## Seite 97

82 3 Suchalgorithmen
hashKey = 18233 = 0100 0111 0011 1001
self.mask = 7 = 0000 0000 0000 0111 &
i = 0000 0000 0000 0001
Allgemein kann man durch Wahl von self .mask= 2i−1 mittels hashKey &self.mask die
niederwertigsten i Bits von haskKey selektieren und diese Selektion als g ¨ultigen Index
in einer 2i-großen Hash-Tabelle interpretieren. Wichtig hierf¨ur ist, sicherzustellen, dass
die Gr¨oße n der Hash-Tabelle immer eine Zweierpotenz ist, d. h. dass n = 2i f¨ur eine
i∈N gilt.
Aufgabe 3.32
Die Selektion der i niederwertigsten Bits entspricht eigentlich der Operation ”% 2i“.
Dies widerspricht eigentlich der Empfehlung aus Abschnitt 3.4.1, man solle als Hash-
Funktion ”% p“ mit p als Primzahl verwenden. Argumentieren Sie, warum dies hier
durchaus sinnvoll ist.
Mit Hilfe der lookup-Funktion ist, wie in Listing 3.17 zu sehen, das Einf¨ugen eines neuen
Elements bzw. Ersetzen eines bestehenden Elements relativ einfach zu realisieren:
1 class OurDict(object):
2 ...
3 def insert ( self ,key,value ):
4 entry = self . lookup(key)
5 if entry.value==None: self.used += 1
6 entry.key = key
7 entry.hash = hashStr(key)
8 entry.value = value
Listing 3.17: Die insert -Methode ist eine ”interne“ Funktion, mit der ein Element in eine
OurDict-Objekt eingef¨ugt werden kann
Die Funktion lookup liefert denjenigen Eintrag zur ¨uck, der mit dem einzuf ¨ugenden
Schl¨ussel-Wert-Paar zu f ¨ullen ist. In Zeile 5 wird der ”F¨ullstandsanzeiger“ der Hash-
Tabelle self .used angepasst, aber nur dann, wenn auch tats ¨achlich ein neuer Wert ein-
gef¨ugt (und nicht ein alter ersetzt) wurde. Die insert -Methode sollte jedoch nicht direkt
vom Benutzer verwendet werden; die Schnittstelle f¨ur das Einf¨ugen eines Elementes bie-
tet die setitem -Methode; Listing 3.18 zeigt eine Implementierung. Stellt eine Klasse
eine Implementierung der setitem -Methode zur Verf¨ugung, so wird eine Zuweisung
der Form x [key]=value automatisch in einen Aufruf der Form
x. setitem (key, value) ¨uberf¨uhrt. In Zeile 5 in Listing 3.18 ﬁndet das eigentliche
Einf¨ugen des ¨ubergebenen Schl ¨ussel-Wert-Paares statt. Wozu aber der Code in den
Zeilen 7 und 8?
Ein Problem beim Hashing besteht darin, dass die Gr ¨oße der Hash-Tabelle eigentlich
fest vorgegeben werden sollte. Bei der Deklaration und Verwendung einesdict-Objektes
”weiß“ Python jedoch nicht im Voraus, wie viele Werte in der Hash-Tabelle gespeichert

## Seite 98

3.4 Hashing 83
1 class OurDict(object):
2 ...
3 def setitem ( self ,key,value ):
4 oldUsed = self.used
5 self . insert (key,value)
6 # Muss die Hashtabellengr ¨oße angepasst werden?
7 if ( self .used>oldUsed and self.used*3 ≥( self .mask +1) *2):
8 self . resize (2 *self .used)
Listing 3.18:Mit Hilfe der setitem -Methode kann der Benutzer komfortabel ein Schl¨ussel-
Wert-Paar in ein Objekt vom Typ OurDict einf ¨ugen.
werden sollen; diese Information kann nicht statisch5 bestimmt werden, sondern sie
ergibt sich erst dynamisch, also w ¨ahrend das Programm ausgef ¨uhrt wird (sprich: zur
”Ausf¨uhrungszeit“).
Aufgabe 3.33
Die Implementierung des Python-internen dict-Typs unterscheidet bei der Anpas-
sung der Gr¨oße der Hash-Tabelle die folgenden beiden F ¨alle:
(a) Ist die L ¨ange der momentanen Hash-Tabelle gr¨oßer als 4096, so wird, falls erfor-
derlich die Gr¨oße immer verdoppelt.
(b) Ist die L ¨ange der momentanen Hash-Tabelle kleiner als 4096, so wird, falls er-
forderlich, die Gr¨oße immer vervierfacht.
Passen Sie die in Listing 3.18 gezeigte Implementierung entsprechend an.
Listing 3.19 zeigt die Implementierung der Gr ¨oßenanpassung der Hash-Tabelle.
1 class OurDict(object):
2 ...
3 def resize ( self , minused):
4 newsize=MINSIZE
5 while newsize≤minused and newsize>0: newsize=newsize<<1
6 oldtable = self . table
7 newtable = []
8 while len(newtable) < newsize:
9 newtable.append(Entry())
5Der Informatiker spricht von ”statisch“, wenn er meint: vor der Ausf¨uhrung eines Programms bzw.
zur ”Compilezeit“, also w¨ahrend der Analyse des Programmcodes. Es gibt viele Informationen, die vor
Ausf¨uhrung des Programms nur sehr schwer oder auch gar nicht bestimmt werden k ¨onnen. So ist es
i. A. unm¨oglich statisch zu bestimmen, ob ein Programm anhalten wird oder in eine Endlosschleife l¨auft
– dies wird in der Literatur h ¨auﬁg als das sog. ”Halteproblem“ bezeichnet.

## Seite 99

84 3 Suchalgorithmen
10 self . table = newtable
11 self .used = 0
12 for entry in oldtable :
13 if entry.value==None:
14 self . insert init (entry)
15 self .mask = newsize -1
16 self . size = newsize
Listing 3.19:Mit Hilfe der resize -Methode kann die L¨ange der Hash-Tabelle, falls notwendig,
vergr¨oßert werden.
Man sieht, dass diese Gr ¨oßenanpassung der Hash-Tabelle ein kritischer Punkt in der
Performance des dict-Typs bzw. des OurDict-Typs ist. Denn hier wird eine neue Ta-
belle mit mindestens doppelter Gr ¨oße der alten Tabelle neu angelegt (Zeilen 4–9) und
anschließend alle vorhandenen Eintr¨age aus der alten Tabelle in die neue Tabelle ko-
piert (Zeilen 11–14). Die Funktion resize hat oﬀensichtlich eine Laufzeit von O(n),
wobei n die Gr¨oße der Hash-Tabelle ist, was bei sehr großen Hash-Tabellen durchaus
kritisch sein kann. Aus Performance-Gr¨unden wird beim Einf¨ugen der Eintr¨age aus der
alten Tabelle in die Neue nicht die insert -Funktion verwendet, sondern eine eigens f¨ur
diese Situation geschriebene Einf ¨uge-Funktion insert init ; diese berechnet die (schon
berechneten) Hash-Werte der Eintr¨age nicht neu, sondern verwendet die schon vorhan-
denen entry.hash-Werte; außerdem vermeidet insert init zur weiteren Optimierung
Funktionsaufrufe.
Aufgabe 3.34
Programmieren Sie die Funktion insert init .
Aufgabe 3.35
Deﬁnieren Sie f ¨ur den OurDict-Typ die Methode getitem , mit deren Hilfe man
einfach den Wert eines Schl¨ussels durch Indizierung erh¨alt.
Aufgabe 3.36
Implementierung Sie f ¨ur den OurDict-Typ eine M ¨oglichkeit, Elemente zu l ¨oschen,
d. h. deﬁnieren Sie eine Instanz der Methode delitem . Auf was m ¨ussen Sie dabei
besonders achten?

## Seite 100

3.5 Bloomﬁlter 85
Aufgabe 3.37
Warum ist es nicht sinnvoll, dem Python-Typlist eine Implementierung der hash -
Methode zu geben? In anderen Worten: warum k ¨onnen Listen nicht als Index eines
dict-Objekt dienen? Was k¨onnte schief gehen, wenn man auf ein Element mittels eine
Liste zugreifen m¨ochte, wie etwa in folgendem Beispiel:
>>> lst = [1,2,3 ]
>>>d = {lst :14, 'Hugo':991 }
3.5 Bloomﬁlter
Die erstmals von Burton Bloom [2] vorgestellte Datenstruktur, bietet ( ¨ahnlich wie die
sp¨ater beschriebene Union-Find-Datenstruktur) eine sowohl sehr platz- als auch zeit-
eﬃziente M¨oglichkeit, zu testen, ob sich ein Datensatz in einer bestimmten Datenmenge
beﬁndet. Bloomﬁlter bieten lediglich zwei Operationen an: das Hinzuf¨ugen eines Daten-
satzes und einen Test, ob ein bestimmter Datensatz bereits enthalten ist – im Weiteren
auch oft mit Membership-Test bezeichnet. Es ist dagegen nicht m ¨oglich, ein Element
aus einem Bloomﬁlter zu l ¨oschen.
Ein Bloomﬁlter ist eine probabilistische Datenstruktur und kann falsche Antworten auf
einen Membership-Test liefern: Beﬁndet sich ein Datensatz in der Menge, so antwortet
das Bloomﬁlter immer korrekt. Beﬁndet sich jedoch ein Datensatznicht in der Menge, so
kann (i. A. mit geringer Wahrscheinlichkeit) das Bloomﬁlter eine falsch-positive Antwort
liefern.
3.5.1 Grundlegende Funktionsweise
Ein Bloomﬁlter besteht aus einem Array A der Gr ¨oße m mit booleschen Eintr ¨agen.
Das einzuf¨ugende Element e wird auf eine Familie von k Hash-Funktionen h0,...h k−1
angewendet. Um eschließlich einzuf¨ugen, werden die Array-Eintr¨age an den Positionen
h0(e) %m,...,h k−1(e) %m des Arrays A auf True gesetzt.
Nehmen wir als Beispiel an, wir h ¨atten zwei Hashfunktionen h0 und h1, ein Array mit
10 Positionen, und wir wollten die Strings eine, Einf¨ uhrungund Informatik einf¨ugen.
Nehmen wir folgende Hash-Werte der Strings an:
h0(eine) = 3, h0(Einf¨ uhrung) = 1,h0(Informatik) = 6
h1(eine) = 1, h1(Einf¨ uhrung) = 8,h1(Informatik) = 7
Abbildung 3.17 zeigt, was beim Einf ¨ugen der drei Strings in das Bloomﬁlter geschieht.
Will man ¨uberpr¨ufen, ob ein Element eim Bloomﬁlter enthalten ist, so ¨uberpr¨uft man,
ob A[h0(e)] = A[h1(e)] = ... = A[hk−1(e)] = True gilt. Es gibt zwei F ¨alle:
 Mindestens einer der Eintr ¨age A[h0(e)],...A [hk−1(e)] hat den Wert False. In
diesem Fall k ¨onnen wir sicher davon ausgehen, dass e bisher noch nicht in das

## Seite 101

86 3 Suchalgorithmen
Einf¨ugen von
eine
FalseFalse False False FalseFalse False
0 1 2 3 4 5 6 7 8 9
True True True
0 1 2 3 4 5 6 7 8 9
FalseFalse FalseFalse False True True TrueTrue True
0 1 2 3 4 5 6 7 8 9
False False False False FalseFalse False True True False
False False False False FalseFalse False False False
0 1 2 3 4 5 6 7 8 9
False
Einf¨ugen von
Einf¨ uhrung
Einf¨ugen von
Informatik
=h1(eine)
=h0(Einf¨ uhrung) =h1(Einf¨ uhrung)
=h0(Informatik)
=h1(Informatik)
=h0(eine)
Abb. 3.17:Einf¨ugen der drei Elemente eine, Einf¨ uhrungund Informatik in ein Bloomﬁlter
der L¨ange 10 unter Verwendung der beiden Hash-Funktionen h0 und h1.
Bloomﬁlter eingef ¨ugt wurde; andernfalls h ¨atten n¨amlich alle diese Eintr ¨age den
Wert True.
 Alle Eintr¨age A[h0(e)],...A [hk−1(e)] haben den WertTrue. In diesem Fall k¨onnen
wir annehmen, dass e schon in das Bloomﬁlter eingef ¨ugt wurde. Diese Annahme
entspricht jedoch nicht mit 100%-Wahrscheinlichkeit der Wahrheit. Es kann vor-
kommen, dass alle diese Eintr ¨age zuf ¨allig in Folge anderer Einf ¨ugeoperationen
schon auf True gesetzt wurden.
Nehmen wir obiges Beispiel und ¨uberpr¨ufen das durch Einf¨ugen von eine, Einf¨ uhrung
und Informatik entstandenen Bloomﬁlter daraufhin, ob es die beiden Strings
Algorithmik und praktisch enth¨alt. Wir gehen von folgenden Hash-Werten aus:
h0(Algorithmik) = 9, h0(praktisch) = 1,
h1(Algorithmik) = 3, h1(praktisch) = 7,
Abbildung 3.18 zeigt wie es zu falsch-positiven Antworten kommen kann. Das Bloomﬁl-
ter liefert f ¨alschlicherweise die Aussage, dass der String praktisch bereits ins Bloom-
ﬁlter eingef¨ugt wurde (denn h0(praktisch) = True und h1(praktisch) = True).
Aufgabe 3.38
Worin unterscheidet sich einfaches Hashing von einem Bloomﬁlter mit k= 1?

## Seite 102

3.5 Bloomﬁlter 87
praktisch ∈
?
Algorithmik ∈
= h1(Algorithmik)
= h0(Algorithmik)
FalseFalse FalseFalse False
0 1 2 3 4 5 6 7 8 9
True True True True True
= h1(praktisch)
= h0(praktisch)
?
False FalseFalse
0 1 2 3 4 5 6 7 8 9
True True TrueTrue TrueFalse False
⇒praktisch ∈A (da sowohl A[5] = True als auch A[7] = True)
⇒Algorithmik /∈A (da A[9] = False)
Abb. 3.18: Zwei Membership-Tests des Bloomﬁlters aus Abbildung 3.17 auf die Strings
Algorithmik und praktisch. Der zweite Test, der pr ¨uft, ob praktisch bereits ins Bloomﬁlter
eingef¨ugt wurde, liefert ein falsches Ergebnis.
3.5.2 Implementierung
Listing 3.20 zeigt die Implementierung eines Bloomﬁlters in Python:
1 class BloomFilter(object):
2 def init ( self , h, m):
3 self .k = len(h) ; self .h = h
4 self .A = [False ] *m
5 self .m = m
6
7 def insert( self ,x):
8 for hashFkt in self .h: self .A[hashFkt(x)] = True
9
10 def elem(self ,x):
11 return all([ self .A[hashFkt(x)] for hashFkt in self .h])
Listing 3.20: Implementierung eines Bloomﬁlters.
Das Bloomﬁlter wird durch die Klasse BloomFilter implementiert. Die Liste self .h
speichert die k Hashfunktionen; die Liste self .A enth¨alt die Array-Eintr¨age des Bloom-
ﬁlters; alle Eintr¨age werden in Zeile 4 mit False initialisiert.
Die Einf¨uge-Operation ist durch die Methode insert implementiert. Die for-Schleife in
Zeile 8 durchl¨auft in der Variablen hashFkt die k Hashfunktionen des Bloomﬁlters; der
Ausdruck hashFkt(x) deﬁniert eine der k Positionen des Arrays self .A, die im Zuge der
Einf¨uge-Operation auf True gesetzt werden m¨ussen.
¨Ahnlich einfach ist die Implementierung der Methode elem, die testet, ob ein Element
x sich im Bloomﬁlter beﬁndet. Die Listenkomprehension in Zeile 13 sammelt alle k
relevanten Eintr¨age von self .A in einer Liste auf; haben alle Werte dieser Liste den
Wahrheitswert True, so wird angenommen, dass x sich im Bloomﬁlter beﬁndet.

## Seite 103

88 3 Suchalgorithmen
Aufgabe 3.39
(a) Erkl ¨aren Sie, warum folgender Methode der Klasse BloomFilter nicht geeignet
ist, ein Element aus dem Bloomﬁlter zu entfernen:
def delete( self ,x):
for i in range(0, self .k): self .A[self .h[i ](x) % self .m] = False
(b) Schreiben Sie die Methode delete so um, dass sie ebenfalls das Element x l¨oscht,
jedoch mit m¨oglichst wenig ”Seiteneﬀekten“.
(c) Warum ist selbst die in der letzten Teilaufgabe programmierte L ¨osch-Funktion
in vielen F¨allen nicht sinnvoll?
Aufgabe 3.40
Eine bessere M ¨oglichkeit (als die in Aufgabe 3.39 vorgestellte), eine L ¨osch-Funktion
in einem Bloomﬁlter zu implementieren, besteht darin, sich die gel ¨oschten Elemente
in einem zweiten Bloomﬁlter zu merken.
(a) Schreiben Sie eine Methode deleteSB die eine solche L ¨osch-Funktion implemen-
tiert. Passen Sie dabei, wenn n ¨otig, die Klasse BloomFilter an; passen Sie die
Methode elem entsprechend an.
(b) Kann durch das L ¨oschen mittels deleteSB auch eine Situation entstehen, in der
falsch-negative Antworten auf Membership-Tests gegeben werden? Vergleichen
Sie diese L¨osch-Funktion mit der in Aufgabe 3.39 vorgestellten L ¨osch-Funktion.
Aufgabe 3.41
Eine bessere M ¨oglichkeit (als die in Aufgabe 3.40 vorgestellte), eine L ¨osch-Funktion
zu implementieren, ist die Verwendung eines sog. Countingﬁlters. Ein Countingﬁl-
ter ist ein Bloomﬁlter, dessen Eintr ¨age keine Bitwerte (d. h. True oder False) sind,
sondern Z¨ahler. Anf¨anglich sind alle Eintr¨age 0; mit jeder Einf¨uge-Operation werden
die durch die Hash-Funktion bestimmten Eintr¨age des Bloomﬁlter-Arrays jeweils um
Eins erh¨oht.
(a) Implementieren Sie, angelehnt an die in Listing 3.20 gezeigte Implementierung
der Klasse BloomFilter, eine Klasse CountingFilter, die einen Countingﬁlter im-
plementiert. Implementieren Sie eine Methode insert, die ein Element einf ¨ugt,
und eine Methode elem, die testet, ob ein Element in dem Bloomﬁlter enthalten
ist.
(b) Implementieren Sie eine Methode delete, die ein Element in einem Bloomﬁlter
l¨oscht.

## Seite 104

3.5 Bloomﬁlter 89
Aufgabe 3.42
Gegeben seien zwei Bloomﬁlter B1 und B2, mit len(B1 .array) == len(B2 .array)
(d. h. die Arrays der Bloomﬁlter haben die gleiche L ¨ange) und B1 .h ==B2 .h (d. h.
die beiden Bloomﬁlter verwenden die gleiche Menge von Hash-Funktionen).
(a) Erkl ¨aren Sie, wie man die Mengen, die die beiden Bloomﬁlter B1 und B2 re-
pr¨asentieren, in einem neuen Bloomﬁlter vereinigen kann.
Schreiben Sie eine entsprechende Python-Funktion unionBF(B1,B2), die diese
Vereinigung implementiert.
(b) Erkl ¨aren Sie, wie man die Mengen, die die beiden Bloomﬁlter B1 und B2 re-
pr¨asentieren, in einem neuen Bloomﬁlter schneiden kann.
Schreiben Sie eine entsprechende Python-Funktion intersectBF(B1,B2), die die-
sen Schnitt implementiert.
3.5.3 Laufzeit und Wahrscheinlichkeit falsch-positiver
Antworten
Sowohl das Einf ¨ugen, als auch der Membership-Test ben ¨otigen jeweils O(k) Schritte,
um die k Hash-Funktionen zu berechnen. Die Laufzeit ist also – und das ist das ei-
gentlich Bemerkenswerte an einem Bloomﬁlter – unabh ¨angig von der Anzahl n der im
Bloomﬁlter enthaltenen Eintr¨age.
Eine entscheidende Frage bzgl. der Performance eines Bloomﬁlters bleibt jedoch: Wie
groß ist die Wahrscheinlichkeit eines falsch-positiven Membership-Tests? Wir gehen im
Folgenden von der (nur n ¨aherungsweise korrekten) Annahme aus, die Funktionswerte
der kHash-Funktionen seien alle unabh¨angig und perfekt pseudo-zuf¨allig verteilt. Dann
k¨onnen wir annehmen, dass die Wahrscheinlichkeit, ein bestimmtes Bit aus den mEin-
tr¨agen des Bit-Arrays w ¨urde durch eine bestimmte Hash-Funktion hi gesetzt, genau
1/mist; die Gegenwahrscheinlichkeit, d. h. die Wahrscheinlichkeit, dass dieses Bitnicht
gesetzt wird, ist entsprechend 1 −1/m. Die Wahrscheinlichkeit, dass dieses Bit durch
keine der k Hashfunktionen h0,...h k−1 gesetzt wird, ist also (1 −1/m)k. Beﬁnden sich
bereits n Elemente im Bloomﬁlter, so ist die Wahrscheinlichkeit, dass dieses Bit durch
keine der n Einf¨ugeoperationen gesetzt wurde (1 −1/m)kn. Die Gegenwahrscheinlich-
keit, d. h. die Wahrscheinlichkeit, dass dieses Bit durch eine der n Einf¨ugeoperationen
gesetzt wurde, ist 1 −(1 −1/m)kn.
Die Wahrscheinlichkeit FPT eines falsch-positiven Tests, d. h. die Wahrscheinlichkeit
dass alle f¨ur einen Eintrag relevanten k Bits bereits gesetzt wurden ist also
FPT =
(
1 −(1 −1/m)kn)k
F¨ur den Designer eines Bloomﬁlters stellen sich zwei entscheidende Fragen:
1. Welcher Wert sollte f¨ur k gew¨ahlt werden?. Wie viele Hash-Funktionen sollten
optimalerweise f ¨ur ein Bloomﬁlter der Gr ¨oße m und einer erwarteten Anzahl von n

## Seite 105

90 3 Suchalgorithmen
Eintr¨agen verwendet werden, d. h. welche Anzahlkvon Hash-Funktionen minimiert die
Wahrscheinlichkeit falsch-positiver Aussagen?
Um diese Fragen zu beantworten, m ¨ussen wir zun¨achst den Ausdruck der Wahrschein-
lichkeit eines falsch-positiven Tests etwas vereinfachen. Da (1 −1/m)x ≈e−x/m (durch
Taylorreihenentwicklung einfach nachzuvollziehen.) gilt f¨ur die WahrscheinlichkeitFPT
eines falsch-positiven Tests:
FPT =
(
1 −(1 −1/m)kn)k
≈
(
1 −e−kn/m
)k
=: FPT≈
Will man das Minimum dieses Ausdrucks – betrachtet als Funktion nach k – ﬁnden,
so sucht man die Nullstellen der Ableitung; leichter ist es jedoch (was sich erst nach
einiger Rechnerei herausstellt), den Logarithmus dieses Ausdruck zu minimieren. Leiten
wir zun¨achst den Logarithmus von FPT nach k ab
ln(FPT≈)′=
[
k·ln(1 −e−kn/m)
]′
= ln(1 −e−kn/m) + kn
m · e−kn/m
1 −e−kn/m
Eine Nullstelle liegt bei k= (ln 2)·m
n, und man kann auch tats¨achlich zeigen, dass dies
ein Minimum ist.
2. Welcher Wert sollte f¨ur m gew¨ahlt werden?. Oft m¨ochte man die Fehlerrate
eines Bloomﬁlters begrenzen. Die entscheidende Frage hierzu ist: Wie groß sollte das
Bloomﬁlter-Array gew ¨ahlt werden, wenn man – bei einer erwarteten Anzahl von n
Eintr¨agen – sicherstellen m¨ochte, dass die Wahrscheinlichkeit falsch-positiver Aussagen
h¨ochstens p sein wird?
Die Herleitung einer entsprechenden Formel ist noch aufw ¨andiger als obige Herleitung
der optimalen Wahl vonkund wir ¨uberlassen es dem interessierten Leser sich in entspre-
chender Literatur [4] dar¨uber zu informieren. Folgende Formel liefert die Mindestgr ¨oße
meines Bloomﬁlters mit ngespeicherten Elementen, die die Wahrscheinlichkeit falsch-
positiver Aussagen auf h ¨ochstens p beschr¨ankt.
m≥nlog2(1/p)
Aufgabe 3.43
Beantworten Sie die folgenden Fragen:
(a) Wie viele Hash-Funktionen sollte man verwenden, bei einem Bloomﬁlter der
Gr¨oße 1 MBit, das etwa 100000 Elemente speichern soll?
(b) Wie viele Bits pro gespeichertem Eintrag werden von einem Bloomﬁlter ben¨otigt,
dessen Fehlerrate h¨ochstens bei 1% liegen soll?
(c) Wie viele Bits pro gespeichertem Eintrag werden von einem Bloomﬁlter ben¨otigt,
dessen Fehlerrate h¨ochstens bei 0.1% liegen soll?

## Seite 106

3.5 Bloomﬁlter 91
Aufgabe 3.44
(a) Erkl ¨aren Sie, wie man mit Hilfe eines Bloomﬁlters eine schnelle und speicheref-
ﬁziente Rechtschreibpr¨ufung implementieren kann.
(b) Gehen wir von einem W ¨orterbuch mit 100000 Eintr¨agen aus; wir wollen sicher-
stellen dass die Rechtschreibpr ¨ufung nur bei h ¨ochstens jedem 1000sten Wort
einen Fehler begeht. Wie groß muss das Bloomﬁlter gew ¨ahlt werden? Wie viele
Hash-Funktionen sollten optimalerweise verwendet werden?
(c) Implementieren Sie die Rechtschreibpr ¨ufung. Verwenden Sie die in Listing 3.20
gezeigte Implementierung von Bloomﬁltern. Recherchieren Sie, welche Hash-
Funktionen sinnvoll sein k ¨onnten und verwenden Sie diese; evtl. ist es auch
sinnvoll aus einer einzelnen Hash-Funktion durch Gruppierung der Bits mehre-
re Hash-Funktionen zu generieren. Implementieren Sie eine Funktion richtig (s),
die mit Hilfe des Bloomﬁlters testet, ob der Strings sich im W¨orterbuch beﬁndet.
3.5.4 Anwendungen von Bloomﬁltern
Sehr beliebt ist der Einsatz von Bloomﬁltern, um die Antwortzeiten von Datenbanken
oder langsamen Massenspeichern zu beschleunigen. Ferner gibt es eine wachsende Zahl
von Anwendungen, deren Anwendungsf¨alle nicht auf das klassische Paradigma einer re-
lationalen Datenbank passen; hierzu wurde in neuster Zeit der BegriﬀNoSQL (f¨ur: ”Not
only SQL“) gepr¨agt. Bloomﬁlter stellen eine h¨auﬁg gew¨ahlte Technik dar, um Daten in
nicht-relationalen Datenbanken, wie etwa dokumentenorientiert verteilte Datenbanken,
zu strukturieren.
Um eines (von sehr vielen) Beispielen zu geben: Bloomﬁlter werden in Googles
BigTable [5], einem verteilten Ablagesystem f ¨ur unstrukturierte Daten, verwendet, um
die Anzahl von Suchaktionen zu reduzieren. Hierbei wird jede Anfrage an die Datenbank
zun¨achst an ein Bloomﬁlter gegeben, das alle in der Datenbank enthaltenen Schl ¨ussel-
werte enth ¨alt. Beﬁndet sich ein Schl ¨ussel nicht in der Datenbank, so antwortet das
Bloomﬁlter korrekt (und sehr schnell, n ¨amlich mit konstanter Laufzeit) und die An-
frage muss nicht weiter von der langsameren Datenbank bearbeitet werden. Beﬁndet
sich der Schl¨ussel im Bloomﬁlter, so muss allerdings direkt auf die Datenbank bzw. den
Massenspeicher zugegriﬀen werden (zum Einen um auszuschließen, dass das Bloomﬁlter
eine falsch-positive Antwort gegeben hat; zum Anderen um den zum Schl ¨ussel passen-
den Wert aus der Datenbank zu holen und zur ¨uckzuliefern). Abbildung 3.19 zeigt diese
Technik nochmals graphisch.
Es gibt eine Reihe von Netzwerk-Anwendungen, in denen die Verwendung eines Bloom-
ﬁlters sehr sinnvoll sein kann. Wir geben eines (von vielen m ¨oglichen) Beispielen – die
Implementierung eines sog. Web-Proxys. Die Hauptaufgabe eines Web-Proxys ist die
Reduktion von Web-Traﬃcs, also der ¨uber das Netzwerk bzw. Internet verschickten
Datenmenge. Wird diese Datenmenge verringert, so kann damit i. A. die Zugriﬀsge-
schwindigkeit auf Web-Seiten verbessert werden. Diese Geschwindigkeitserh¨ohung wird
durch Caching h¨auﬁg genutzter Seiten erreicht, d. h. auf den Proxys beﬁndliche sog.
Web-Caches speichern h ¨auﬁg genutzte Web-Dokumente und sind so f ¨ur Rechner die

## Seite 107

92 3 Suchalgorithmen
Speicher
Bloomﬁlter
samer
lang-
w∈S?
nein
x∈S?
ja
ja
y∈S?
ja nein
z∈S?nein
Abb. 3.19: Ein Bloomﬁlter kann dazu verwendet werden, die Zugriﬀe auf einen langsamen
Massenspeicher (wie etwa eine Festplatte oder ein noch langsameres Bandlaufwerk) zu redu-
zieren. In den meisten F ¨allen, in denen sich ein Element nicht auf dem langsamen Speicher
S beﬁndet, kann so bei einer Anfrage der Zugriﬀ auf S vermieden werden; in dem Beispiel
ist dies bei den Anfragen ”w ∈S?“ und ”z ∈S?“ der Fall. Nur wenn das Bloomﬁlter eine
positive Antwort liefert, muss direkt auf S zugegriﬀen werden, zum Einen um auszuschließen,
dass es sich bei der Antwort des Bloomﬁlters um eine falsch-positive Aussage handelte (das ist
im Beispiel bei der Anfrage ”y ∈S?“ der Fall); zum Anderen nat ¨urlich um die angefragten
Informationen aus S zu holen und dem Benutzer zur ¨uckzuliefern.
den Web-Proxy nutzen schneller erreichbar als wenn sie von Ihrer urspr¨unglichen Quel-
len geladen werden m¨ussten. Dieses Proxy-Konzept kann noch um ein Vielfaches eﬀek-
tiver gestaltet werden, wenn sich Web-Proxys untereinander Informationen ¨uber den
Inhalt ihrer Caches austauschen: Im Falle eines Cache-Miss6 versucht der Web-Proxy
das angeforderte Web-Dokument aus dem Cache eines anderen Web-Proxys zu bezie-
hen. Hierzu m¨ussen Proxys ¨uber den Inhalt der Caches anderer Proxy bescheid wissen.
Anstatt aber die kompletten Inhalte der Caches ¨uber das Internet auszutauschen (was
aufgrund deren Gr ¨oße sehr teuer w ¨are), werden in regelm ¨aßigen zeitlichen Abst ¨anden
Bloomﬁlter verschickt, die die Eintr ¨age der Caches beinhalten. Der prominente ”Squid
Web Proxy Cache“ verwendet beispielsweise Bloomﬁlter.
Aufgabe 3.45
Erkl¨aren Sie, warum in diesem Falle der Implementierung eines Web-Proxys die Ei-
genschaft der Bloomﬁlter, mit einer gewissen Wahrscheinlichkeit falsch-positive Ant-
worten zu geben, vollkommen unproblematisch ist.
6Mit Cache-Miss bezeichnet man die Situation, dass sich eine angeforderte Seite nicht im Cache des
jeweiligen Proxys beﬁndet.

## Seite 108

3.6 Skip-Listen 93
3.6 Skip-Listen
Die erst 1990 von William Pugh [16] eingef¨uhrten Skip-Listen bilden eine einfache und in
vielen F¨allen sehr eﬃziente Implementierung der Dictionary-Operationen ”Einf¨ugen“,
”Suchen“ und ”L¨oschen“. Tats¨achlich erweisen sich Skip-Listen oft als die einfachere
und eﬃzientere Alternative zu einer Implementierung ¨uber balancierte Baumstruktu-
ren. Skip-Listen stellen eine sog. randomisierte Datenstruktur dar: Beim Aufbau einer
Skip-Liste bzw. beim Einf ¨ugen von Elementen in eine Skip-Liste werden gewisse Zu-
fallsentscheidungen getroﬀen, auf die wir sp ¨ater genauer eingehen werden.
¨Ahnlich wie bei einfachen verketteten Listen sind die Eintr¨age in einer Skip-Liste durch
Zeiger verkettet. Es besteht jedoch ein wesentlicher Unterschied zu verketteten Listen:
Ein Element einer Skip-Liste kann mehrere Vorw ¨artszeiger enthalten. Abbildung 3.20
zeigt ein Beispiel. Die Anzahl der Vorw ¨artszeiger eines Eintrags bezeichnen wir als die
7 13
19 30
32
34
39
91
9362
44
76
81
Abb. 3.20: Beispiel einer Skip-Liste der H ¨ohe 3.
H¨ohe des Knotens. Als die H¨ohe einer Skip-Liste bezeichnen wir die maximale H ¨ohe
eines Eintrags der Liste (ausgenommen des initialen Eintrags).
Eine Skip-Liste muss folgende Eigenschaft besitzen: Greift man einen Eintrag aus ei-
ner Skip-Liste zuf ¨allig heraus, so sollte die Wahrscheinlichkeit, auf einen Eintrag mit
i Vorw¨artszeigern zu treﬀen, genau pi−1 ·(1 −p) sein, wobei 0 < p <1 eine vorher
festgelegte Wahrscheinlichkeit ist. Das bedeutet, jeder 1
p-te Eintrag mit i Vorw¨artszei-
gern hat auch (mindestens) i+ 1 Vorw¨artszeiger. W¨ahlt man etwa p = 1/2, so h ¨atte
durchschnittlich jeder 2. Eintrag zwei Vorw ¨artszeiger (entspricht der Wahrscheinlich-
keit (1/2) 1), jeder 4. Eintrag drei Vorw ¨artszeiger (entspricht der Wahrscheinlichkeit
(1/2)2), jeder 8. Eintrag vier Vorw¨artszeiger (entspricht der Wahrscheinlichkeit (1/2)3),
usw. Die folgende Python-Funktion randHeight() erzeugt eine zuf ¨allige H¨ohe f¨ur einen
neuen Eintrag genau so, dass obige Eigenschaften gelten.
1 from random import random
2 p = ... # feste Wahrscheinlichkeit mit 0 <p< 1
3 def randHeight():
4 i=1
5 while random()≤p: i +=1
6 return min(i,MaxHeight)
Listing 3.21: Die Funktion randHeight() erzeugt mit einer vorher festgelegten Konstanten
0 <p<1 eine zuf¨allige H ¨ohe.
Die Funktion random() erzeugt normalverteilt (d. h. alle Zahlen sind gleichwahrschein-
lich) eine zuf¨allige Gleitpunktzahl zwischen 0 und 1. Aus der Tatsache, dass alle Gleit-
punktzahlen gleichwahrscheinlich sind, folgt, dass random()≤p mit Wahrscheinlichkeit

## Seite 109

94 3 Suchalgorithmen
p gilt. Die Wahrscheinlichkeit, dass randHeight den Wert 1 zur ¨uckliefert ist also 1−p,
die Wahrscheinlichkeit, dass randHeight den Wert 2 zur¨uckliefert entspricht der Wahr-
scheinlichkeit, dass random()≤p beim ersten Durchlauf und random()>p beim zweiten
Durchlauf gilt, was mit einer Wahrscheinlichkeit von p ·(1 −p) der Fall ist, usw.
3.6.1 Implementierung
Wir deﬁnieren eine Klasse SLEntry, die einen einzelnen Eintrag in einer Skip-Liste
repr¨asentiert, bestehend aus einem Schl ¨ussel key, einem Wert val und einer Liste ptrs
von Vorw¨artszeigern.
1 class SLEntry(object):
2 def init ( self , key, ptrs=[], val=None):
3 self .key = key ; self . ptrs = ptrs ; self . val = val
Listing 3.22: Deﬁnition der Klasse SLEntry, die einen Eintrag der Skip-Liste repr ¨asentiert.
Des Weiteren deﬁnieren wir eine Klasse SkipList, die eine Skip-Liste repr ¨asentiert.
1 class SkipList( object ):
2 def init ( self ):
3 self . tail = SLEntry(Infty)
4 self .head = SLEntry(None,[self.tail for in range(MaxHeight+1)])
5 self . height = 0
Listing 3.23: Deﬁnition der Klasse SkipList, die eine Skip-Liste repr ¨asentiert.
Eine Skipliste sl besitzt ein spezielles Anfangselement sl .head, das eineMaxHeight lange
Liste von Vorw ¨artszeigern enth¨alt, die anf ¨anglich alle auf das Ende-Element sl . tail
zeigen. Das spezielle Ende-Element sl . tail hat als Schl ¨ussel den Wert ”∞“7 und ist
ansonsten leer.
Suche. Am einfachsten ist die Implementierung der Suche. Listing 3.24 zeigt die Im-
plementierung der Suche nach einem Eintrag mit Schl ¨ussel key.
1 class SkipList( object ):
2 ...
3 def search( self , key):
4 x = self .head
5 for i in range(self . height , -1, -1):
6 while x.ptrs [i ]. key < key: x = x.ptrs [i ]
7 x = x.ptrs [0]
8 if x.key == key: return x.val
9 else: return None
Listing 3.24: Implementierung der Suche nach einem Eintrag mit Schl ¨ussel key
7Der Wert ”∞“ kann in Python durch den Ausdruck ﬂoat ('inf') erzeugt werden.

## Seite 110

3.6 Skip-Listen 95
Zun¨achst werden die Vorw ¨artszeiger auf der h ¨ochstm¨oglichen Stufe, also auf Stufe
self . height, solange gelaufen, bis der Suchschl ¨ussel kleiner ist als der Schl ¨ussel des
momentanen Elements; dies bewirkt die while-Schleife in Zeile 6. Anschließend werden
die Vorw¨artszeiger auf der n ¨achstniedrigeren Stufe entsprechend lange gelaufen, usw.
Ist schließlich die unterste Stufe 0 erreicht, so beﬁndet sich die Suche direkt vor dem
gesuchten Eintrag – vorausgesetzt nat ¨urlich, der Schl¨ussel key beﬁndet sich ¨uberhaupt
in der Skip-Liste.
Einf¨ugen. Beim Einf¨ugen eines Elementes in eine Skip-Liste w ¨ahlen wir die H¨ohe die-
ses Elementes durch eine Zufallsentscheidung, die wir schon oben durch die Funktion
randHeigth implementiert haben. Die Struktur der Skip-Liste ist nicht alleine durch die
einzuf¨ugenden Elemente determiniert, sondern wird zus ¨atzlich durch Zufallsentschei-
dungen beim Aufbau der Liste bestimmt. Die Zuweisung in Zeile 13 in Listing 3.25 ist
auch tats¨achlich das einzige Kommando in den pr ¨asentierten Algorithmen ¨uber Skip-
Listen, das mit Zufallszahlen arbeitet.
1 class SkipList( object ):
2 ...
3 def insert( self ,key,val ):
4 updatePtrs = [ self .head] *(MaxHeight +1)
5 x = self .head
6 for i in range(self . height , -1, -1):
7 while x.ptrs [i ]. key < key: x = x.ptrs [i ]
8 updatePtrs[i ] = x
9 x = x.ptrs [0]
10 if x.key == key: # bestehenden Eintrag ver¨andern
11 x. val = val
12 else: # neuen Eintrag einf ¨ugen
13 newheight = randHeight()
14 self . height = max(self.height, newheight)
15 entry = SLEntry(key,[updatePtrs [i].ptrs[i ] for i in range(newheight)], val)
16 for i in range(0,newheight +1):
17 updatePtrs[i ]. ptrs [i ] = entry
Listing 3.25: Implementierung der Einf ¨uge-Operation eines Schl ¨ussel-Wert-Paares in eine
Skip-Liste
Bis zur Zeile 12 wird, ¨ahnlich wie in der search-Methode, nach der richtigen Einf¨ugepo-
sition gesucht. Zus¨atzlich werden in der Liste updatePtrs diejenigen Elemente der Skip-
List gespeichert, deren Vorw ¨artszeiger bei einem Einf ¨ugen m ¨oglicherweise angepasst
werden m¨ussen; Abbildung 3.21 zeigt dies an einer Beispielsituation; die in updatePtrs
beﬁndlichen Vorw¨artszeiger sind hierbei dunkel markiert. In Zeile 13 und 14 wird durch
eine Zufallsentscheidung eine H ¨ohe f¨ur das einzuf ¨ugende Element bestimmt und, falls
diese H¨ohe gr¨oßer als die bisher maximale H ¨ohe eines Elementes in der Skip-Liste ist,
die H¨ohe der Skip-Liste angepasst. In Zeile 15 wird der neue Eintrag erzeugt. Der i-te
Vorw¨artszeiger des neuen Eintrags ist hierbei der i-te Vorw¨artszeiger des i-ten Eintrags

## Seite 111

96 3 Suchalgorithmen
in updatePtrs f¨ur 0 ≤i≤newheight; dies ist in Abbildung 3.21(b) an der Beispielsi-
tuation veranschaulicht. Schließlich werden die Zeiger der in updatePtrs beﬁndlichen
Elemente so angepasst, dass sie auf den neu erzeugten Eintrag zeigen; dies geschieht in
den Zeilen 16 und 17.
7
19 30
32
34
39
91
9362
44
76
81
13
updatePtrs[3]
updatePtrs[2]
updatePtrs[1]
updatePtrs[0]
(a) Die Situation vor der Einf ¨uge-Operation: In updatePtrs[i ] ist das Element der Skip-Liste
gespeichert, dessen i-ter Vorw¨artszeiger, in der Abbildung grau eingef ¨arbt, beim Einf ¨ugen des
neuen Elementes angepasst werden muss.
91
93
81
7
19 30
32
34
39 62
44
76
13
79
(b) Die Situation nach der Einf ¨uge-Operation: Die i-ten Vorw¨artszeiger von updatePtrs[i ] f¨ur 0 ≤i≤
newheight sind jetzt die i-ten Vorw¨artszeiger des neu eingef ¨ugten Elements.
Abb. 3.21:Einf¨ugen eines neuen Elements mit Schl ¨usselwert 79 und der (mittels der Funktion
randHeight() zuf¨allig erzeugten) H ¨ohe 3 in eine Skip-Liste.
L¨oschen. Beim L¨oschen werden in der Such-Phase ebenfalls diejenigen Elemente ge-
merkt, deren i-ter Vorw¨artszeiger eventuell angepasst werden muss. Listing 3.26 zeigt
die Implementierung der L¨osch-Funktion.
1 class SkipList( object ):
2 ...
3 def delete( self ,key):
4 updatePtrs = [ self .head] *(MaxHeight +1)
5 x = self .head
6 for i in range(self . height , -1, -1):
7 while x.ptrs [i ]. key < key: x = x.ptrs [i ]
8 updatePtrs[i ] = x
9 x = x.ptrs [0] # x ist das zu l ¨oschende Element
10 if x.key == key:
11 heightx = len(x.ptrs) -1
12 for i in range(0,heightx +1):
13 updatePtrs[i ]. ptrs [i ] = x.ptrs [i ]
14 while self . height ≥ 0 and self.head.ptrs [ self . height ] == self. tail :
15 self . height -= 1
Listing 3.26: Implementierung der L ¨osch-Funktion.

## Seite 112

3.6 Skip-Listen 97
Die Methode delete funktioniert sehr ¨ahnlich wie die Methode insert. Einer Erw¨ahnung
Wert sind allenfalls die Zeilen 14 und 15, in der die H ¨ohe des Skip-Liste genau dann
angepasst wird, wenn das Element mit der maximalen H ¨ohe gel ¨oscht wurde. Hierbei
gen¨ugt es nicht, die H ¨ohe einfach um Eins zu erniedrigen, denn der H ¨ohenunterschied
zum n¨achst tieferen Element k¨onnte mehr als Eins betragen. Stattdessen muss dashead-
Element der Skip-Liste untersucht werden: Der h¨ochstgelegene Zeiger, der nicht auf das
tail -Element zeigt, ist die neue H ¨ohe der Skip-Liste.
Aufgabe 3.46
Implementieren Sie die Funktion str , so dass Skip-Listen folgendermaßen ausge-
geben werden:
>>>print skiplist
>>> [ (30|1), (33 |4), (40 |3), (77 |1), (98 |1), (109 |1), (193 |3) ]
Ausgegeben werden soll also der Schl ¨ussel jedes Elements zusammen mit der H ¨ohe
des Elements.
Aufgabe 3.47
(a) Schreiben Sie eine Methode keys(), die eine Liste der in der Skip-Liste gespei-
cherten Schl¨usselwerte zur¨uckliefert.
(b) Schreiben Sie eine Methode vals (), die eine Liste der in der Skip-Liste gespei-
cherten Werte zur¨uckliefert.
Aufgabe 3.48
Oft wird eine eﬃziente Bestimmung der L ¨ange einer Skip-Liste ben ¨otigt. Erweitern
Sie die Klasse SkipList um ein Attribut length, passen Sie entsprechend die Methoden
insert und delete an und geben Sie eine Implementierung der Methode len an,
so dass die len-Funktion auf Skip-Listen anwendbar ist.
Aufgabe 3.49
(a) Schreiben Sie eine Funktion numHeights(h), die die Anzahl der Elemente mit
H¨ohe n zur¨uckliefert.
(b) Schreiben Sie eine Funktion avgHeight(s), die die durchschnittliche H ¨ohe eines
Elementes der Skip-Liste s berechnet.

## Seite 113

98 3 Suchalgorithmen
3.6.2 Laufzeit
F¨ur alle Operationen auf einer Skip-Liste dominiert immer die Laufzeit der Suche nach
der richtigen Einf¨uge- bzw. L ¨oschposition. Es gen ¨ugt also, wenn wir uns bei der Lauf-
zeitanalyse auf die Untersuchung der Laufzeit der Suche in einer Skip-Liste beschr¨anken.
Die erwartete H ¨ohe einer Skip-Liste. Wir werden im Folgenden sehen, dass die
H¨ohe einer Skip-Liste entscheidend f ¨ur die Laufzeit der Suche ist. Da Skip-Listen eine
randomisierte Datenstruktur darstellen, ist die H ¨ohe einer Skip-Liste keine vorherbe-
stimmte Gr¨oße. Mathematisch l¨asst sich die H¨ohe als Zufallsvariable8 H(n) modellieren.
Wir k¨onnen also nie mit Sicherheit vorhersagen, welche H¨ohe eine bestimmte Skip-Liste
haben wird. Wir beschr¨anken uns daher darauf, zu fragen, was die erwartete9 H¨ohe H(n)
einer Skip-Liste mit n Elementen ist. Wir f ¨uhren hierzu den Ausdruck numHeights(h)
ein, der die durchschnittliche Anzahl von Elementen einer n-elementigen Skip-Liste
repr¨asentiert, die eine H¨ohe von ≥h haben. Es gilt:
numHeights(0) = n·p0, numHeights(1) = n·p1, numHeights(2) = n·p2, ...
Wir setzen dies nun soweit fort, bis wir eine H ¨ohe h gefunden haben, f ¨ur die es durch-
schnittlich weniger als ein Element mit dieser H ¨ohe gibt:
numHeights(log1/p(n) + 1) = n·plog1/p(n) ·p= n
n ·p= p< 1
Aus der Tatsache, dass es durchschnittlich weniger als ein Element in der Skip-Liste
gibt, das eine H ¨ohe von mindestens log 1/p(n) + 1 aufweist, k¨onnen wir schließen, dass
log1/p(n) die H¨ohe (d. h. die maximale H¨ohe eines Elementes der Skip-Liste) einer durch-
schnittlichen Skip-Liste mit n Elementen ist, also:
H(n) ≈log1/p(n) + 1
F¨ur die h¨auﬁg gew¨ahlte Wahrscheinlichkeit p= 1
2 gilt H(n) ≈log2(n) + 1.
Aufgabe 3.50
(a) Schreiben Sie eine Methode numHeights(h) der Klasse SkipList, die von einer
gegebenen Skipliste die Anzahl der Elemente mit H ¨ohe n zur¨uckliefert.
(b) Schreiben Sie eine Funktion avgHeight() der Klasse SkipList, die die durch-
schnittliche H¨ohe eines Elementes der Skip-Liste berechnet.
Die erwartete L¨ange eines Suchpfades. Die entscheidende Idee, die durchschnitt-
liche L¨ange eines Suchpfades zu ermitteln, besteht darin, den Suchpfad r ¨uckw¨arts zu
betrachten. Wir starten beginnend vom Zeiger der H ¨ohe 0, der direkt auf das gesuchte

## Seite 114

3.6 Skip-Listen 99
7
19
13
23
30
32
34
39 62
44
76
81
91
9378
Abb. 3.22: Darstellung eines Suchpfades. Wie man sieht, gibt es f ¨ur jeden Schritt immer zwei
m¨ogliche ”Richtungen“ um sich auf dem Pfad vom zu suchenden Element hin zum Listenkopf zu
bewegen: entweder horizontal oder nach oben. Die Frage die bleibt ist: Wie viele der horizontalen
Schritte m¨ussen durchschnittlich gegangen werden, bis man ”oben“ ankommt?
Element zeigt und laufen r¨uckw¨arts bis wir am Kopf der Skip-Liste angelangt sind. Ab-
bildung 3.22 zeigt solch einen ”R¨uckw¨arts“-Pfad ausgehend vom zu suchenden Element,
in diesem Fall ”76“, zum Kopf der Liste.
Beﬁndet man sich bei einem Element der H ¨ohe i so geht der R ¨uckw¨arts-Pfad solange
in vertikaler Richtung weiter, bis er auf ein Element der Skip-Liste st¨oßt, das eine H¨ohe
von (mindestens) i+1 besitzt. Dann geht der Pfad um eine Stufe nach oben, usw. Es ist
hilfreich, sich folgenden (ﬁktiven) Algorithmus vorzustellen, der diesen R¨uckw¨arts-Pfad
durchl¨auft:
x = zuSuchendesElement
while x ̸= self .head
if nachOben(x) moeglich:
x = nachObenWeiter(x)
else:
x = vertikalWeiter(x)
Listing 3.27: Fiktiver Algo-
rithmus zum Durchlaufen des
R¨uckw¨arts-Pfades
Wie oben beschrieben, wird in diesem Algorithmus in jedem while-Schleifendurchlauf
das Kommando nachObenWeiter(x) mit Wahrscheinlichkeitpausgef¨uhrt und das Kom-
mando vertikalWeiter(x) mit Wahrscheinlichkeit 1−p. Die entscheidende Frage ist: Wie
viele vertikalWeiter(x)-Schritte werden (durchschnittlich) gegangen, bis der Pfad sich
eine Ebene nach oben bewegt? Bezeichnen wir als X die Zufallsvariable, die die Anzahl
der verticalWeiter(x)-Schritte angibt, bis die H ¨ohe ansteigt. Diese Zufallsvariable ist
geometrisch verteilt mit E[X] = 1/p. Wir wissen, dass auf dem R ¨uckw¨artspfad sich die
H¨ohe H(n)-mal erh¨ohen muss bis das head-Element erreicht ist. Die Laufzeit der Suche
betr¨agt also
1
p ·H(n) ≈1
p ·log1/pn+ 1 = O(log n)
8F¨ur weitere Details zu Zufallsvariablen siehe Abschnitt B.3.3.
9Gefragt ist hier also der Erwartungswert. Der Erwartungswert H(n) der H ¨ohe ist nichts anderes
als die durchschnittliche H¨ohe einer Skip-Liste, gemittelt ¨uber sehr viele Skip-Listen.

## Seite 115

100 3 Suchalgorithmen
3.7 Tries
Tries sind B ¨aume, deren
Kanten mit Buchstaben
(bzw. sequentialisierten
Teilen der Suchschl ¨ussel)
beschriftet sind. Be-
sonders dann, wenn
Suchschl¨ussel aus langen
Zeichenketten bestehen
sind Tries vielen anderen
in diesem Kapitel vorge-
stellten Datenstrukturen
¨uberlegen, sowohl was die
Suchzeit als auch was die
Speichereﬃzienz betriﬀt.
Besonders interessant ist,
dass die Laufzeit zur Su-
che eines Schl ¨ussels nicht
von der Gesamtzahl der
Eintr¨age im Trie abh¨angt,
sondern alleine von der
L¨ange des Suchschl¨ussels.
a b k l s t z
a b u
c
15
l
h
e
21
n
b e
2
a
30
r
r t
5
a o
r
14
a
s
c
20
h
a i
h
20
r
10
u
20
n h
14
m s t v
a e
u
100
s
r
11
r
t
e
l
l
17
e
e r
19
n a
e
g
e
22
r
o
r
h
a
b
e
22
n
20
s
20
o a
n
g
e
s
W
o
r
20
t
a o u
h
n
20
e
h l
l
20
e
20
e
20
l
e s
h
n
20
e
20
i
i r
20
e
20
i
20
e
20
p
e o
t
t
e
99
l
r
20
o
Die Suche nach einem kurzen String ben ¨otigt in einem Trie also immer die gleiche An-
zahl (weniger) Schritte, unabh¨angig davon, ob sich im Trie 1000, 100 000 oder mehrere
Millarden Eintr¨age beﬁnden.
Daher werden Tries und Trie-¨ahnliche Datenstrukturen sehr h ¨auﬁg bei der Implemen-
tierung von (Text-)Suchmaschinen eingesetzt. Außerdem werden sie oft verwendet, um
eﬃziente Lookups in Routing-Tabellen zu implementieren, die beispielsweise f ¨ur die
Funktionsweise des Internets unerl¨asslich sind.
3.7.1 Die Datenstruktur
Bin¨are Suchb¨aume bew¨ahren sich in der Praxis genau dann sehr gut, wenn sich Schl¨ussel
eﬃzient vergleichen lassen. Dies ist im Allgemeinen dann der Fall, wenn Werte eines
”einfachen“ Typs verglichen werden, wie etwa Integer-Werte oder einzelne Zeichen; je-
doch kann ein Vergleich ”teuer“ werden, wenn Werte komplexerer zusammengesetzter
Typen verglichen werden, wie etwa (m ¨oglicherweise lange) Zeichenketten; aber selbst
einfache Vergleiche k¨onnen in objektorientierten Sprachen verh¨altnism¨aßig teuer sein, da
der Vergleichsoperator ¨ublicherweise ¨uberladen ist und, bevor der eigentliche Vergleich
ausgef¨uhrt wird, zun¨achst die f¨ur die verwendeten Typen passende Methode dynamisch
(also w¨ahrend der Laufzeit) ausgew ¨ahlt werden muss. Dieser sog. dynamic dispatch ist
verh¨altnism¨aßig rechenaufw¨andig.
Handelt es sich bei den Schl ¨usselwerten also um komplexe Werte etwa eines zusam-
mengesetzten Typs, insbesondere um Strings, so ist die sog. Trie10-Datenstruktur, ei-
10Der Name ”Trie“ leitet sich ab aus dem englischen Wort”retrieval“, dem Finden bzw. Wiederﬁnden
von Informationen.

## Seite 116

3.7 Tries 101
ne Baumstruktur, oft die beste Wahl Schl ¨ussel-Wert-Paare eﬃzient zu speichern und
wieder zu ﬁnden. Anders als bei Suchb ¨aumen, sind in den Knoten eines Tries nicht die
Schl¨ussel selbst gespeichert, sondern die Position des Knotens innerhalb des Trie-Baums
bestimmt, welcher Schl ¨ussel im Knoten gespeichert ist. Angenommen die Strings, aus
denen die Schl¨usselwerte bestehen, setzen sich zusammen aus Kleinbuchstaben zwischen
a und z. Dann sind alle Kinder v.children eines Knoten v im Trie markiert mit einem
Element aus {a,..., z}. Den zu einem Schl¨usselwert passenden Eintrag in einem Trie ﬁn-
det man nun einfach dadurch, dass man von der Wurzel beginnend den mit den Zeichen
im String markierten Kanten nachl ¨auft. Abbildung 3.23 zeigt einen einfachen Trie, der
die Schl¨usselwerte 'bahn', 'bar', 'bis', 'sole', 'soll', 'tri', 'trie' und 'trip'
speichert.
a
b
i
r
o
s
r
t
e e ln p
s l ih
Abb. 3.23: Beispiel eines Tries, der die Strings 'bahn', 'bar', 'bis', 'sole', 'soll',
'tri', 'trie' und 'trip' speichert. Nur die Knoten mit doppelter Umrandung entsprechen
einem enthaltenen Schl ¨ussel und k ¨onnen tats¨achlich einen Wert speichern.
Aufgabe 3.51
Zeichnen Sie einen Trie, der die Schl ¨ussel gans, ganz, galle, leber, lesen,
lesezeichen, zeichnen, zeilenweise, adam, aaron speichert und beantworten Sie
die folgenden Fragen:
(a) Wie viele Schritte ben ¨otigt eine Suche in diesem Trie minimal?
(b) Wie viele Schritte ben ¨otigt eine Suche in diesem Trie maximal?
Aufgabe 3.52
Beantworten Sie die folgenden Fragen:
(a) Wie viele Character-Vergleiche ben ¨otigt eine Suche in einem Trie h¨ochstens, der
1 Mio verschiedene Schl¨usselwerte mit einer L¨ange von h¨ochstens 14 enth¨alt?
(b) Wie viele Character-Vergleiche ben ¨otigt eine Suche in einem bin ¨aren ausgegli-
chenen Suchbaum, der 1 Mio verschiedene Schl ¨usselwerte mit einer L ¨ange von
h¨ochstens 14 enth¨alt?

## Seite 117

102 3 Suchalgorithmen
Listing 3.28 zeigt die Deﬁnition der Python-Klasse Trie:
1 class Trie(object ):
2 def init ( self ):
3 self . children = {}
4 self . val = None
Listing 3.28: Klasse Trie mit der init -Methode
Jeder Trie t enth¨alt also ein Attribut t . val, das die im jeweiligen Knoten beﬁndliche
Information speichert, und ein Attribut t . children, das die Menge der Kinder des Kno-
tens speichert. Diese Kinder-Menge wird in Listing 3.28 als dict-Wert repr¨asentiert, der
Kantenmarkierungen auf Kinder-Tries abbildet. Es w ¨are wohl auch die Repr ¨asentati-
on als Liste denkbar, die aus Kantenmarkierungen und Kinder-Tries bestehende Tupel
enth¨alt, jedoch erweist sich die Verwendung eines dict-Wertes als eﬃzientere Wahl.
3.7.2 Suche
Die beiden wichtigsten Operationen auf einen Trie sind das Einf ¨ugen und das Suchen.
Beginnen wir, da einfacher, mit der Implementierung der Suche. Listing 3.29 zeigt eine
rekursive Implementierung der Methode search:
1 class Trie(object ):
2 ...
3 def search( self ,key):
4 if not key: return self. val
5 c = key[0]
6 if c not in self . children: return None
7 return self. children [c ]. search(key[1: ])
Listing 3.29: Rekursive Implementierung der Suche in einem Trie.
Zeile 4 in Listing 3.29 implementiert den Rekursionsabbruch, der dann eintritt, wenn
der Suchstring key leer ist. In diesem Fall gehen wir davon aus, dass die Suche am
Ziel angelangt ist und liefern daher als R ¨uckgabewert den im momentanen Knoten
gespeicherten Wert self . val zur¨uck. Andernfalls versuchen wir dem Zweig nachzulaufen,
der mit dem ersten im Suchschl ¨ussel gespeicherten Zeichen, also mit key[0] bzw. c,
markiert ist. Falls kein solcher Zweig vorhanden ist, d. h. falls c nicht im Dictionary
self . children enthalten ist, wird einfach None zur¨uckgeliefert. Andernfalls fahren wir
in Zeile 8 rekursiv mit der Suche des verbleibenden Suchschl ¨ussels key[1 :] fort, solange
eben, bis der Suchschl ¨ussel leer ist.

## Seite 118

3.7 Tries 103
3.7.3 Einf ¨ugen
Nur wenig schwieriger ist die in Listing 3.30 gezeigte Implementierung der Einf ¨uge-
Operation:
1 class Trie(object ):
2 ...
3 def insert( self ,key,val ):
4 if not key:
5 self . val=val
6 else:
7 if key[0] not in self . children:
8 self . children [key[0] ] = Trie()
9 self . children [key[0] ]. insert (key[1: ], val)
Listing 3.30:Rekursive Implementierung einer Funktion insert , die ein neues Schl¨ussel-Wert-
Paar in einen Trie einf ¨ugt.
Ist der Schl ¨usselstring leer, so wurde bereits an die passende Stelle des Tries navigiert
und der als Parameter ¨ubergebene Wert val kann eingef¨ugt werden – dies geschieht in
Zeile 5. Andernfalls wird, wie bei der Suche auch, das n ¨achste Zeichen des Schl ¨ussel-
strings (also key[0]) dazu benutzt um sich der passenden Stelle im Trie weiter zu n¨ahern
– dies geschieht in Zeile 9 in Listing 3.30: Gibt es noch keinenkey[0]-Eintrag im children-
Dictionary, so wird ein solcher Eintrag erzeugt. Anderfalls wird dem key[0]-Eintrag
des im aktuellen Knoten gespeicherten children-Dictionaries gefolgt und f ¨ur den dort
gespeicherten Trie die insert-Methode rekursiv mit dem restlichen Schl ¨ussel key[1 :]
aufgerufen.
Aufgabe 3.53
Implementieren Sie eine Methodekeys(), die eine Liste aller in einem Trie beﬁndlichen
Schl¨usselwerte zur¨uckliefert.
Dass die vorgestellte Trie-Datenstruktur sehr eﬃzient ist, zeigt ein (nat ¨urlich sehr
Rechner-ab¨angiger) Laufzeit-Vergleich f¨ur das Suchen von 1000 W ¨orter der L ¨ange 100
einmal in einem Trie und einmal in einer Instanz des Python-internen dict-Typs:
Implementierung Laufzeit
dict-Typ 0.348
Trie-Typ 0.353
Man beachte jedoch: Die dict-Implementierung ist dadurch ungleich bevorteilt, dass
sie direkt in C implementiert. Die Tatsache, dass die Laufzeiten der beiden Implemen-
tierungen trotzdem in etwa gleich sind, deutet darauf hin, dass die Trie-Struktur f ¨ur
diesen Anwendungsfall prinzipiell die eﬃzientere Methode ist.

## Seite 119

104 3 Suchalgorithmen
3.8 Patricia-Tries
  
91
A
11
CCEPT
81
T
57 b   c   d 93gain  kti   
l
25
m
82n 70
pplikationen
  r   s 74ttribut   u
82arbeitung  b 71 er 65
frage
3
gebrochen
  
l
  
s
37
ildung
40
ruch
94
en
26
kriterium
62
n
  
a
53
eitung
17
gesystem
59
uf
97
plan
72
s
56
sschritt
  
ch
  
t
9
alten
  
n
9
eiden
84
itt
65
e
23
s
48
n
96
and
  
i
48
raktionslevel
  
s
34
graph
66
wert
62
e
85
s
75
eg
12
mmung
9
c
4
yclic
48dition  
jazenz
23
ministrator
92
ressen
1
liste
10
matrix
24
s
52 on 83
vist
79
en
20
stabelle
72 an  g 36
l
2
phabet
47
s
24
t
25ebraische  
orit
  
hm
89
mus
57
en
82
ik
26
us
43
klassen
21
e
51
gemein
31
en
22
en
32
s
99
o
28
er
10
nativ
62
e
37
n
67
eise
91
n
  al   d 27eignung  f 47genommen61
hang
  
le
34
nahme
50
ordnung
98
passung
  
s
59twort   
we
58
y
  
z
72
og
  
ys
50
ie
41
n
62
e
26
ieren
13
n
  
er
15
rew
28
e
42
nfalls
87
s
54
n
52
rseits
90
s
17
ang
91
orderungen
55
rage
43
s
7
buchstaben
73
element
12
knoten
69
symbole
60
teil
38
zustand
10
n
85
gen
6
hnung
92 en 29
atz
  
ch
90
pruch
  
t
93
aulichkeit
5
ein
37
att
81
euerung
48
ssoftware
60
en
83
zeiten
86
isung
  
nd
3
en
  
s
26
block
93
folgen
24
er
59
ung
58
programm
35
sicht
30
en
  
s
25
beispiel
10
fall
45
programm
21
e
42
ahl
42
iehen
46beit 2
chiv
77
gument
  
ithme
72
ray
30
t
69
en
  
s
71
speicher
5
umgebungen
98
verzeichnis
57
ses
41
s
42
ation
48
e
22
ieren
44
n
73
ntik
9
tik
75
s
1
en
31
ikel
  
k
35
pekte
30
tronomie
56
epte
54
pekte
46
n
74
e
77
n
90
ch
45
f
14
gen
90
ruf
48s
26bau  g 10listung46
multiplikation
32
ruf
79
stieg
  
t
96
wand
22
zaehlungen
27
en
20
abe
85
rund
51
n
68
stellung
7 e 68
hierarchie
6
parameter
83
s
49
n
44
eilung
42
reten
38
merk
69
druck
32
filtern
  
g
66
kunft
93
lastung
26
s
  
a
  
e
55
be
  
ngs
83
wert
  
k
90
punkt
19
tour
78
ante
68
noten
85
n
31
geben
33
hend
4
klammert
77
staltung
Ein Patricia (auch h ¨auﬁg als Patricia-Trie bezeichnet) ist einem Trie sehr ¨ahnlich, nur
dass ein Patricia auf eine kompaktere Darstellung Wert legt. Dies geht zwar etwas
auf Kosten der Laufzeit – die Einf ¨ugeoperation und die L ¨oschoperation werden etwas
langsamer und die Implementierung komplexer. In vielen F¨allen werden diese Nachteile
aber wenig ins Gewicht fallen, und der Vorteil der kompakteren Speicherung ¨uberwiegt.
Oben dargestellter Patricia speichert etwa die lexikographisch ersten 200 in diesem Buch
vorkommenden W¨orter.
3.8.1 Datenstruktur
Es gibt den einen problematischen Fall, dass sich viele W ¨orter in einem Trie (bzw. in
einem Teilbaum des Tries) beﬁnden, die sich einen langen gemeinsamen Pr ¨aﬁx teilen,
d. h. die alle mit der gleichen Buchstabenkombination beginnen. In diesem Fall”beginnt“
der Baum mit einer langen Kette von Knoten, wobei jeder Knoten jeweils nur ein Kind
hat. Abbildung 3.24(a) zeigt einen Trie, dessen Eintr ¨age alle den Pr ¨aﬁx 'bau' haben.
Patricia-Tries stellen eine Optimierung der Tries dar. Man kann n ¨amlich Knoten mit
Grad 1 (also mit nur einem Kind) in denen sich keine Informationen beﬁnden mit
dem jeweiligen Kind-Knoten verschmelzen und so eine kompaktere Darstellung eines
Tries erhalten. Die verbleibenden Knoten speichern dann den gemeinsamen Pr¨aﬁx aller
im entsprechenden Teilbaum beﬁndlichen Knoten. Abbildung 3.24(b) zeigt ein Beispiel
eines Patricia-Trie:
Aufgabe 3.54
F¨ugen Sie in den Patricia-Trie aus Abbildung 3.24(b) die Schl ¨usselwerte
baustellplatz und bautr¨ agerein.
Wir implementieren Patricia-Tries als KlassePatricia. Die Konstruktor-Funktion init
ist mit der Konstruktorfunktion der Klasse Trie identisch.
1 class Patricia( object ):
2 def init ( self ):
3 self . children = {}
4 self . val = None
Listing 3.31: Klassendeﬁnition Patricia

## Seite 120

3.8 Patricia-Tries 105
a
h
e
m
t
e
s
e
n
t
u
a
b
r
r
u
s l
l
e
(a) Ein Trie.
err aus
bau
stelle m tenh
(b) Ein Patricia-Trie.
Abb. 3.24: Ein Trie und ein Patricia-Trie, die die jeweils gleichen Schl ¨usselwerte gespeichert
haben, n¨amlich 'bau', 'bauhaus', 'bauherr', 'baum', 'baustelle', 'bauten'. Jeder Kno-
ten des Patricia-Trie h ¨alt den Pr ¨aﬁx gespeichert, den alle in seinem Teilbaum gespeicherten
Schl¨usselwerte gemeinsam haben.
3.8.2 Suche
Wie man leicht sieht, ist sowohl das Einf ¨ugen, insert, als auch das Suchen, search, im
Falle der Patricia-Tries komplizierter zu implementieren als im Falle der Tries. Das liegt
daran, dass nun nicht mehr sofort klar ist, welchen Zweig man eigentlich zu laufen hat –
man muss nach passenden Zweigen erst suchen. Listing 3.32 zeigt die Implementierung
der Suchfunktion.
1 class Patricia( object ):
2 ...
3 def search( self , key):
4 if not key:
5 return self. val
6 preﬁxes = [k for k in self . children if key. startswith (k) ]
7 if not preﬁxes:
8 return None
9 else:
10 preﬁx = preﬁxes [0]
11 return self. children [ preﬁx ]. search(key[len( preﬁx ): ])
Listing 3.32: Implementierung der Suchfunktion f ¨ur Patricias.
Man beachte zun¨achst, dass die Implementierung rekursiv ist. Der Rekursionsabbruch
erfolgt, wenn der zu suchende Schl¨usselwert key der leere String ist, also not key gilt. In
diesem Fall gehen wir davon aus, dass der gesuchte Knoten des Patricia-Tries erreicht
wurde und geben einfach den darin gespeicherten Wert self . val zur¨uck – dies geschieht

## Seite 121

106 3 Suchalgorithmen
in Zeile 5. Andernfalls suchen wir in self . children nach einem Schl ¨usselwert, der ein
Pr¨aﬁx von key ist. Gibt es kein solches Attribut (das ist der Fall, wenn preﬁxes ==[]
bzw. not prefxes), so gilt der Schl¨usselwert key als nicht gefunden, die Suche wird abge-
brochen und None zur¨uckgeliefert – dies geschieht in Zeile 8. Andernfalls wird der mit
dem gefundenen Schl¨usselwert beschrifteten Kante self . children [ preﬁx ] nachgelaufen
und die Suchprozedur mit entsprechend verk¨urztem Schl¨ussel key[len(prefx) :] rekursiv
aufgerufen – dies geschieht in Zeile 11.
3.8.3 Einf ¨ugen
Insbesondere die Implementierung der Einf ¨ugeoperation ist f ¨ur Patricias komplexer als
f¨ur einfache Tries. Listing 3.33 zeigt die Implementierung eines Patricia-Tries.
1 class Patricia( object ):
2 ...
3 def insert( self ,key,val ):
4 v = self
5 prefx = [k for k in v. children.keys() if k. startswith (key[0]) ] if key else [ ]
6 if prefx ̸= [ ]:
7 prefx = prefx[0]
8 if not key.startswith(prefx ): # Fall 3 ⇒umstrukturieren
9 i = preﬁxLen(key, prefx)
10 t1 = v.children [prefx ]
11 del(v.children [prefx ])
12 v. children [key[: i ] ] = Patricia()
13 v. children [key[: i ] ]. children [prefx [i : ] ] = t1
14 if key[i : ]==[]:
15 v. children [key[: i ] ]. val = val
16 return
17 v. children [key[: i ] ]. children [key[i : ] ] = Patricia()
18 v. children [key[: i ] ]. children [key[i : ] ].val = val
19 else: # Fall 2 ⇒einfach weiterlaufen
20 key = key[len(prefx): ]
21 if key==[]:
22 v. val = val
23 return
24 v = v.children [prefx ]
25 v. insert (key, val)
26 else: # Fall 1 ⇒neuen Eintrag generieren
27 v. children [key] = Patricia()
28 v. children [key]. val = val
Listing 3.33: Implementierung eines Patricia-Trie

## Seite 122

3.8 Patricia-Tries 107
Auch die Implementierung von insert ist rekursiv; der rekursive Aufruf ist in Zeile 25
in Listing 3.33 zu sehen. In jedem Aufruf von insert auf einen Knoten v sind drei F¨alle
zu unterscheiden:
1. Fall: Es gibt keinen Eintrag in v. children dessen Schl¨ussel einen mit key gemein-
samen Pr¨aﬁx hat. Dies ist der einfachste Fall. Es muss lediglich ein neuer Eintrag
in v. children erzeugt werden mit Schl ¨ussel key dessen Wert val ist. Dieser Fall
wird in den Zeilen 27 und 28 aus Listing 3.33 behandelt.
2. Fall: Es gibt in v. children einen Eintrag commonPrae der ein Pr ¨aﬁx von key
ist d. h. f¨ur den gilt, dass commonPrae==key[ :i] (mit i=len(commonPrae)). In
diesem Fall muss einfach dieser mitkey[ :i ] markierten Kante nachgelaufen werden
und anschließend mit dem verbleibenden Suﬃx von key weitergesucht werden.
Dieser Fall wird in den Zeilen 20 bis 25 in Listing 3.33 behandelt.
3. Fall: Es gibt in v. children einen Eintrag prefx, der zwar kein vollst¨andiger Pr¨aﬁx
von key ist; jedoch haben prefx und key einen gemeinsamen Pr¨aﬁx, d. h. es gibt
ein 0 <i<len(prefx) mit prefx [ :i ] == key[ :i]. Dies ist der aufw ¨andigste Fall,
denn hier muss der bisherige Patricia umgebaut werden. Die Beschriftung prefx
muss zun¨achst zu prefx [ :i ] verk¨urzt werden. An dem durch prefx [ :i ] erreichten
Knoten werden zwei Zweige erzeugt. Der eine wird mit prefx [i :] beschriftet und
enth¨alt die Informationen, die auch vorher unter dem Schl ¨ussel preﬁx erreichbar
waren – also den Teilbaum t1. Der andere Zweig wird mit key[i :] beschriftet und
enth¨alt den Wert zum neu eingef ¨ugten Schl¨ussel key.
Abbildung 3.25 zeigt nochmals bildlich, was zu tun ist und was entsprechend auch
in Listing 3.33 zwischen den Zeilen 9 und 18 implementiert ist.
Aufgabe 3.55
Beantworten Sie die folgenden beiden Fragen bzgl. der Suche nach allen in children
enthaltenen Schl¨usselwerten, die ein Pr¨aﬁx von key sind:
(a) In Zeile 5 in Listing 3.33 gezeigten Listenkomprehensionen werden alle Schl¨ussel-
eintr¨age im Kantendictionary children gesucht, die mit dem Anfangsbuchstaben
des Schl¨ussels, also mit key[0], beginnen. Argumentieren Sie, warum sich dar-
unter die gesuchten Schl¨usseleintr¨age beﬁnden m ¨ussen.
(b) Argumentieren Sie, warum die in Zeilen 5 in Listing 3.33 und in Zeile 6 in Listing
3.32 verwendeten Listenkomprehensionen entweder leer oder einelementig sein
m¨ussen.
Der Vorteil des Patricia-Tries gegen¨uber der einfachen Trie-Datenstruktur besteht aber
darin, dass eine kompaktere Repr ¨asentation m¨oglich wird; die Geschwindigkeit leidet
darunter, jedoch nur geringf¨ugig, wie folgende Tabelle zeigt:

## Seite 123

108 3 Suchalgorithmen
t1
t1
......
... ...
Fall 3
max i mit
prefx [ :i ] == key[ :i]
... ... ...
v
... ... ...
Fall 1 Fall 2
insert (key[i :])
prefx [i :] key[i :]
prefx
prefx [ :i ]
key[ :i ]
key
key[ :i ]
v.insert(key)
Abb. 3.25: Graﬁsche Darstellung der drei verschiedenen F ¨alle die beim Einf ¨ugen in einen
Patricia-Trie zu unterscheiden sind.
Implementierung Laufzeit
dict-Typ 0.348
Patricia-Typ 0.3924
3.9 Suchmaschinen
Suchmaschinen verwenden Methoden des Information Retrieval, einem Forschungsge-
biet mit mittlerweile langer Tradition, das sich allgemein mit der Wiedergewinnung
(engl: ”Re-Trieval“) von Informationen besch ¨aftigt, die in großen Datenbest ¨anden f¨ur
den Benutzer ansonsten praktisch ”verloren“ w¨aren. Wir besch ¨aftigen uns hier jedoch
nur mit einem sehr kleinen Teil des Information Retrieval, mit rein lexikalischen (also
rein textbasierten) Suchtechniken. Viele Suchmaschinen verwenden dar ¨uberhinaus se-
mantische Suchtechniken, die Informationen aus verschiedenen Wissensbereichen mit
einﬂießen lassen und mit Hilfe dieser Zusatzinformationen das Suchen eﬀektiver gestal-
ten k¨onnen.
Eine f¨ur das Programmieren von Suchmaschinen sehr n ¨utzliche Datenstruktur ist der
Trie und dessen Verfeinerung, der Patricia.
3.9.1 Aufbau einer Suchmaschine
Abbildung 3.26 zeigt den typischen Aufbau einer Suchmaschine. Der Crawler l¨auft
hierbei ¨uber die Dokumentenbasis, der Indexer parst die Dokumente und extrahiert die
zu indizierenden Elemente, i. A. W¨orter oder Phrasen, und die Suchanfrage-Bearbeitung

## Seite 124

3.9 Suchmaschinen 109
IndexCrawler Suchanfrage
BearbeitungIndexer GUI
Web
Dateisystem
Datenbank
Abb. 3.26: Typischer Aufbau einer Suchmaschine.
extrahiert die f¨ur die Anfrage notwendigen Daten aus der Indexstruktur.
In realen Suchmaschinen k ¨onnen die einzelnen Teile sehr komplex werden: oft arbeitet
der Crawler ¨uber verschiedene Rechner verteilt. Der Indexer muss m ¨oglichst viele Do-
kumente erkennen k ¨onnen und wom ¨oglich in der Lage sein, die Dokumentenstruktur
(also: was ist ¨Uberschrift, was ist einfacher Text, ...) erkennen k ¨onnen usw. Außerdem
muss er ein sog. Stemming betreiben, d. h. nur die Wortst ¨amme sollten ber ¨ucksichtigt
werden und nicht etwa f¨ur Akkusativ, Dativ oder Mehrzahl verschiedene Index-Eintr¨age
des eigentlich gleichen Wortes erzeugt werden.
3.9.2 Invertierter Index
Der sog. invertierte Index bildet das ”Herz“ jeder Suchmaschine; diese Datenstruktur
erm¨oglicht das schnelle Finden von W ¨ortern und Suchbegriﬀen. Dieser Index ordnet
jedem Wort von Interesse Informationen ¨uber dessen Position in der Dokumentenbasis
zu. Oft wird hierbei jedem Wort aus dem Index die Liste aller Vorkommen dieses Wortes
(i. A. ist dies eine Liste von Dokumenten) zugeordnet. Jedes Dokument, auf das hierbei
referenziert wird, besitzt innerhalb des Systems eine eindeutige Identiﬁkationsnummer.
Jedes dieser Vorkommen ihrerseits k¨onnte wiederum eine Liste von Positionen innerhalb
des Dokuments referenzieren, in denen das Wort auftaucht. Abbildung 3.27 zeigt die
Struktur eines solchen invertierten Indexes nochmals graphisch.
Hashtabelle
Heap
Heapsort
Insertion Sort
. . .
. . .
[430,102,344,982, ... ]
[101,72,
...
]
Hornerschema
Liste aller W¨orter
[10,
...
]
[...
]
[...
]
Abb. 3.27: Darstellung des Invertierten Indexes
3.9.3 Implementierung
Es gibt mehrere M¨oglichkeiten, den Index in Python zu implementieren. Wir verwenden
der Einfachheit halber hier Pythons dict-Typ, um den invertierten Index zu implemen-
tieren. Jedes Wort w des Indexes stellt hierbei einen Schl ¨ussel des dict-Objekts ind dar
– dies ist in Listing 3.34 zu sehen. In einem Eintrag ind[w] werden nun alle Dokumente
gespeichert, in denen das Wort w auftaucht. Wir wollen uns zus ¨atzlich auch noch alle

## Seite 125

110 3 Suchalgorithmen
Positionen innerhalb eines Dokuments merken. Diese k ¨onnten wir prinzipiell als Liste
in ind[w] hinterlegen. Wir wollen jedoch zus¨atzlich f¨ur jedes Dokument uns alle Positio-
nen, in unserem Falle zun¨achst nur Zeilennummern, innerhalb des Dokuments merken,
in denen das entsprechende Wort vorkommt. Folglich ist es am g¨unstigsten als Eintr¨age
in ind[w] wiederum dict-Objekte zu w¨ahlen, die jedem Dokument in dem w vorkommt,
die relevanten Positionen innerhalb des Dokuments zuordnen.
1 import os
2
3 class Index(object ):
4 def init ( self , path=''):
5 self .docId = 0
6 self .ind = {}
7 self .docInd = {}
8 if path̸='0': self .crawl(path)
9
10 def toIndex( self , ( word,pos), docId):
11 if word not in self .ind:
12 self .ind[word] = {docId : [ pos] }
13 elif docId not in self .ind[word]:
14 self .ind[word][docId ] = [ pos]
15 else:
16 self .ind[word][docId ].append(pos)
17
18 def addFile( self , ﬁle , tmp=''):
19 def tupl(x,y): return (x,y)
20 if tmp=='': tmp=ﬁle
21 print "Adding", ﬁle
22 self .docInd[self .docId] = ﬁle
23 ﬁleHandle = open(tmp) ; ﬁleCont = ﬁleHandle. readlines() ; ﬁleHandle . close ()
24 ﬁleCont = map(tupl, xrange(0,len(ﬁleCont )), ﬁleCont )
25 words = [(word.lower(),pos) for (pos, line ) in ﬁleCont
26 for word in line . split ()
27 if len(word) ≥3 and word.isalpha() ]
28 for word,pos in words:
29 self .toIndex((word,pos), self .docId)
30 self .docId+=1
31
32 def crawl( self , path):
33 for dirpath, dirnames, ﬁlenames in os.walk(path):
34 for ﬁle in ﬁlenames:
35 f = os.path.join(dirpath, ﬁle )
36 if isPdf(f ):
37 tmpFile = os.path.join(dirpath, 'tmp.txt')
38 os.popen('pdftotext \'' +f +'\' ' +'\'' +tmpFile +'\'')

## Seite 126

3.9 Suchmaschinen 111
39 self .addFile(f ,tmpFile)
40 os.popen('rm \'' +tmpFile +'\'') # und wieder loeschen ...
41 if isTxt(f ):
42 self .addFile(f)
43
44 def ask( self , s ):
45 if s in self .ind:
46 return [self.docInd[d] for d in self .ind[s ]. keys() ]
47 else: return []
Listing 3.34: Die Klasse Index implementiert eine sehr einfache Suchmaschine unter Ver-
wendung von Dictionaries
Das ”Herz“ der Implementierung stellt die Funktion toIndex dar, die ein Wort dem In-
dex hinzuf¨ugt. Jeder Eintrag des Indexes enth ¨alt zum Einen Informationen, in welchen
Dokumenten das entsprechende Wort vorkommt und zum Anderen enth ¨alt es Infor-
mationen an welchen Positionen im jeweiligen Dokument es vorkommt; dies entspricht
genau dem in Abbildung 3.27 dargestellten doppelt invertierten Index. Beim Einf ¨ugen
eines Wortes word in den Index sind die folgenden drei F ¨alle zu beachten: 1. Es gibt
noch keinen Eintrag word; dann muss zun ¨achst ein neues Dictionary angelegt werden
mit einem Eintrag. 2. Es gibt schon einen Eintragword, jedoch gibt es noch keinendocId-
Eintrag f¨ur word; dann muss ein neuer Eintrag docId in ind[word] angelegt werden mit
einem Positionseintrag. 3. Es gibt schon einen Eintrag word und f¨ur word einen Eintrag
docId; dann muss die neue Positionsinformation an die Liste der schon bestehenden
Positionen angeh¨angt werden.
Die Funktion addFile erzeugt f¨ur alle relevanten W¨orter des ¨ubergebenen Textﬁles ﬁle
Eintr¨age im Index. Der Parameter tmp wird nur dann mit ¨ubergeben, wenn eine tem-
por¨are Datei erzeugt wurde – dies ist beispielsweise bei der Verarbeitung von PDF-
Dateien der Fall, die mittels eines externen Programms in Textdateien umgewandelt
werden. In der in Zeile 25 in Listing 3.34 mittels einer Listenkomprehension erzeugten
Liste words beﬁnden sich alle W¨orter von ﬁle die dem Index hinzugef¨ugt werden sollen.
Die Funktion crawl implementiert den Crawler; in unserem Fall l¨auft der Crawler ¨uber
die Verzeichnisstruktur und f¨ugt alle Dateien, die textuelle Information enthalten, dem
Index hinzu; in dieser einfachen Variante kann crawl lediglich pdf- und Textdateien
indizieren.
Aufgabe 3.56
Erkl¨aren Sie die Listenkomprehension in Zeile 25 in Listing 3.34: wozu die beiden
for-Schleifen, wozu die if-Anweisung?
3.9.4 Erweiterte Anforderungen
Erweiterte Anforderungen, die im Rahmen der Aufgaben noch nicht angedacht wurden,
die aber von den ”großen“ Suchmaschinen, unter anderem vom Opensource Framework
Lucene [13] und Google’s Suchmaschinenalgorithmen verwendet werden.

## Seite 127

112 3 Suchalgorithmen
1. Insbesondere dann, wenn die Anzahl der zu indizierenden Dokumente und folglich
auch die Gr ¨oße des Indexes die Ressourcen eines einzelnen Rechners ¨ubersteigt,
muss man dar¨uber nachdenken den Crawler, Indexer und die Indizes verteilt ¨uber
mehrere Maschinen arbeiten zu lassen. Das von Google beschriebene MapReduce-
Framework bietet hierf¨ur eine n¨utzliche Schnittstelle [7, 15].
2. Wenn man die Usability11 verbessern will, dann ist es hilfreich, einen Dokumenten-
Cache12 mit zu verwalten, d. h. kleine Textteile, die einen m¨oglichst repr¨asentati-
ven Auszug aus einem Dokument bilden, werden f¨ur den schnellen Zugriﬀ eﬃzient
gespeichert.
3. Um die Qualit ¨at der Suchergebnisse zu verbessern k ¨onnte man die Textstruktur
beim Indizieren mit ber ¨ucksichtigen: So k¨onnte man etwa Vorkommen eines Wor-
tes in ¨Uberschriften anders gewichten, als die Vorkommen eines Wortes in einem
Paragraphen.
Aufgabe 3.57
Die in Listing 3.34 vorgestellte Implementierung einer Suchmaschine verwendet als
Datenstruktur f¨ur den Index den Python-Typ dict, d. h. Hashtabellen. Reale Such-
maschinen verwenden dagegen sehr oft Tries bzw. Patricia-Tries.
(a) Verwenden Sie statt dem Python dict-Typ f¨ur self .ind besser den im vorigen
Abschnitt vorgestellten Trie. Vergleichen Sie nun Laufzeit und Gr¨oße der als In-
dex entstehenden Datenstruktur bei Verwendung von dict und bei Verwendung
von Trie.
(b) Verwenden Sie statt dem Python dict-Typ f¨ur self .ind besser den im vorigen
Abschnitt vorgestellten Patricia-Trie. Vergleichen Sie nun Laufzeit und Gr ¨oße
der als Index entstehenden Datenstruktur bei Verwendung von dict und bei
Verwendung von Patricia.
Aufgabe 3.58
Erweitern Sie den Indexer so, dass auch die Position innerhalb einer Zeile mit ber¨uck-
sichtigt wird.
11Als Usability bezeichnet man oft auch in der deutschsprachigen Literatur die Benutzbarkeit aus An-
wendersicht; dazu geh¨oren Eigenschaften wie Verst¨andlichkeit, Fehlertoleranz, ¨Ubersichtlichkeit, usw.
12Als Cache bezeichnet man in der Informatik in der Regel einen schnellen kleinen Speicher, der
diejenigen Teile eines gr ¨oßeren Datenspeichers zwischenspeichert, von denen zu erwarten ist, dass sie
momentan bzw. in Zukunft oft verwendet werden; viele Festplatten verwenden Cache-Speicher und auch
viele Rechner verwenden schnelle Cache-Speicher um die Zugriﬀsperformance auf den Hauptspeicher
zu optimieren.

## Seite 128

3.9 Suchmaschinen 113
Aufgabe 3.59
Implementieren Sie eine Methode Index.askHTML so, dass ein HTML-Dokument
zur¨uckgeliefert wird, in dem die Treﬀer als Hyperlinks auf die jeweiligen Dokumente
dargestellt sind.
Aufgabe 3.60
(a) Die Methode Index.ask gibt die Treﬀer f ¨ur ein Suchwort beliebig zur ¨uck. Mo-
diﬁzieren Sie Index.ask so, dass die Treﬀer (also die Dokumente, in denen das
das Suchwort enthalten ist) nach Gewicht sortiert ausgegeben werden. Hierbei
soll das Gewicht gleich der Anzahl der Vorkommen des Suchworts im jeweiligen
Dokument sein.
(b) Geben Sie die Treﬀer nun sortiert nach der relativen H¨auﬁgkeit des Vorkommens
des Suchworts zur ¨uck. Bei der relativen H ¨auﬁgkeit wird einfach die Gr ¨oße des
Dokuments noch mit ber ¨ucksichtigt, d. h.
rel. H¨auﬁgkeit = H¨auﬁgkeit
Dokumentengr¨oße
Aufgabe 3.61
(a) Programmieren Sie eine Funktion Index.remove(ﬁle ), mit der man eine im Index
beﬁndliche Datei wieder entfernen kann.
(b) Programmieren Sie eine Funktion Index.update( ﬁle ), mit der man eine im Index
beﬁndliche wom¨oglich veraltete Datei auf den neusten Stand bringen kann.
Aufgabe 3.62
Implementieren Sie ein einfaches Stemming, indem Sie die h ¨auﬁgsten Endungen
'ung', 'ungen', 'en', 'er', 'em' und 'e' abschneiden. Dies muss dann nat ¨urlich
auch bei der Suche mit ber ¨ucksichtigt werden, d. h. Suchw¨orter m ¨ussen vor der ei-
gentlichen Suche mit dem selben Algorithmus gestemmt werden.

## Seite 129

114 3 Suchalgorithmen
Aufgabe 3.63
Suchmaschinen indizieren aus Eﬃzienzgr¨unden ¨ublicherweise nicht alle W¨orter. Viele
kurze W¨orter, die es nahezu in jedem Dokument gibt, werden ignoriert. Diese W¨orter
werden im Information Retrieval oft als Stoppw ¨orter bezeichnet. Erweitern Sie die
Methode Index.addtoIndex so, dass ein Wort nur dann eingef ¨ugt wird, wenn es nicht
aus einer vorgegebenen Menge von Stoppw ¨ortern stammt.
Tipp: Verwenden Sie als Stoppw ¨orter entweder einfach die wichtigsten bestimmten
und unbestimmten Artikel, Pr¨apositionen, Konjunktionen und Negationen; oder, al-
ternativ, besorgen Sie sich aus Quellen wie etwa [1] eine Liste von Stoppw ¨ortern.
Aufgabe 3.64
Bisher wurden lediglich pdf-Dateien und reine Textdateien indiziert.
(a) Parsen und indizieren sie zus ¨atzlich HTML-Dateien.
(b) Parsen und indizieren sie zus ¨atzlich Openoﬃce-Dateien.
(c) Parsen und indizieren sie zus ¨atzlich MS-Oﬃce-Dateien.
(d) Parsen und indizieren sie zus ¨atzlich TEX-Dateien.
Aufgabe 3.65
Realisieren Sie die M ¨oglichkeit den erzeugten Index abzuspeichern und einen abge-
speicherten Index wieder zu laden; je gr ¨oßer der Index, desto sinnvoller ist es, ihn
persistent, d. h. dauerhaft und ¨uber die Laufzeit des Programms hinausgehend, zu
speichern. Python stellt hierf ¨ur die Module pickle, shelve und/oder marshal zur
Verf¨ugung.

## Seite 130

4 Heaps
Es gibt eine Vielzahl von Anwendungen, die eﬃzient das gr ¨oßte bzw. kleinste Element
aus einer Menge von Elementen ﬁnden und extrahieren m ¨ussen. Eine Datenstruktur,
die eine eﬃziente Maximumsextraktion (bzw. Minimumsextraktion), Einf ¨ugeoperation
und L¨oschoperation anbietet, nennt man Priorit¨atswarteschlange.
Anwendungen von Priorit¨atswarteschlangen. Beispielsweise muss ein Betriebssy-
stem st¨andig (und nat¨urlich unter Verwendung von m¨oglichst wenig Rechenressourcen)
entscheiden, welcher Prozess als N ¨achstes mit der Ausf ¨uhrung fortfahren darf. Dazu
muss der Prozess mit der h ¨ochsten Priorit¨at ausgew ¨ahlt werden. Außerdem kommen
st¨andig neue Prozesse bzw. Tasks hinzu. Man k ¨onnte die entsprechende Funktionalit¨at
dadurch gew¨ahrleisten, dass die Menge von Tasks nach jedem Einf¨ugen eines Elementes
immer wieder neu sortiert wird, um dann das gr ¨oßte Element eﬃzient extrahieren zu
k¨onnen; Heaps bieten jedoch eine eﬃzientere M ¨oglichkeit dies zu implementieren.
Auch einige Algorithmen, wie beispielsweise der Dijkstra-Algorithmus zum Finden k¨urz-
ester Wege oder Prims Algorithmus zum Finden eines minimalen Spannbaums, verwen-
den Priorit¨atswarteschlangen und sind auf eine eﬃziente Realisierung der Einf ¨ugeope-
ration und der Minimumsextraktion angewiesen.
Heaps als Implementierungen von Priorit ¨atswarteschlangen. Als Heap be-
zeichnet man in der Algorithmik einen Baum, dessen Knoten der sog. Min-Heap-Be-
dingung (bzw. Max-Heap-Bedingung – abh ¨angig davon, ob man sich f ¨ur die minima-
len oder maximalen Werte interessiert) gen ¨ugen. Ein Knoten gen ¨ugt genau dann der
(Min-)Heap-Bedingung, wenn sein Schl¨usselwert kleiner ist als die Schl¨usselwerte seiner
Kinder.
Die in diesem Abschnitt vorgestellten Datenstrukturen stellen allesamt m¨ogliche Imple-
mentierungen von Priorit ¨atswarteschlagen dar, die die Operationen ”Einf¨ugen“, ”Mi-
nimumsextraktion“, ”L¨oschen“ und evtl. ”Erniedrigen eines Schl ¨usselwerts“ eﬃzient
unterst¨utzen. Die in Abschnitt 4.1 beschriebenen bin ¨aren Heaps stellen hierbei die
”klassische“ Implementierung von Priorit ¨atswartschlangen dar. Bin ¨are Heaps wurden
eigentlich schon in Kapitel 2 bei der Beschreibung des Heapsort-Algorithmus verwendet,
werden aber in diesem Kapitel der Vollst ¨andigkeit halber nochmals vorgestellt.
Binomial-Heaps (siehe Abschnitt 4.2), Fibonacci-Heaps (siehe Abschnitt 4.3) und Pai-
ring-Heaps (siehe Abschnitt 4.4) sind zus ¨atzlich in der Lage die Verschmelzung zweier
Heaps eﬃzient zu unterst ¨utzen. Eine solche Verschmelzungsoperation spielt beispiels-
weise beim Prozessmanagement von Rechnern mit parallelen Prozessoren bzw. paralle-
len Threads eine Rolle: Gibt ein Prozessor seine”Arbeit“ an einen anderen Prozessor ab,
so erfordert dies u. A. die Verschmelzung der Prozesswarteschlangen beider Prozessoren.

## Seite 131

116 4 Heaps
4.1 Bin ¨are Heaps
3
5 58
65 10 85 98
67 82 49 23 136 195 127 138
177 169 219 103 130 87 79 161 254 272 232 253 185 141 164 208
244 239 291 193 297 289 202 298 162 178 104 111 129 205 285 180 266 288 279
Abb. 4.1: Beispiel eines bin ¨aren Min-Heaps der n= 50Elemente enth¨alt.
Bin¨are Heaps stellen wahrscheinlich die am h¨auﬁgsten verwendete Art der Implementie-
rung von Priorit¨atswarteschlangen dar. Wie f¨ur jeden anderen Heap auch, muss f¨ur jeden
Knoten v eines bin¨aren Heaps die Min-Heap-Bedingung erf ¨ullt sein, d. h. die Schl¨ussel-
werte der Kinder von v m¨ussen gr¨oßer sein als der Schl ¨usselwert von v. Zus¨atzlich ist
ein bin¨arer Heap immer ein vollst ¨andiger Bin¨arbaum, dessen Ebenen alle vollst ¨andig
gef¨ullt sind; nur die unterste Ebene des Heaps ist, falls die Anzahlnder im Heap enthal-
tenen Elemente keine Zweierpotenz (minus Eins) ist, linksb ¨undig unvollst¨andig gef¨ullt.
Abbildung 4.1 zeigt ein Beispiel eines Min-Heaps.
Obwohl einige Operationen (wie beispielsweise die Einf ¨ugeoperation oder das Ernied-
rigen eines Schl ¨usselwertes) f ¨ur bin ¨are Heaps eine schlechtere (asymptotische) Lauf-
zeitkomplexit¨at besitzen als f ¨ur alternative Implementierungen, wie Fibonacci-Heaps
oder Pairing-Heaps, stellen sie trotzdem in vielen F ¨allen die sinnvollste Implementie-
rung dar: Zum Einen weil die in der O-Notation der Laufzeit versteckten Konstanten
relativ ”klein“ sind; zum Anderen weil wegen dessen fester Struktur ein bin ¨arer Heap
in einem zusammenh¨angenden festen Speicherbereich gehalten werden kann. Zus¨atzlich
werden wir sehen, dass die Implementierung der meisten Operationen relativ (zumindest
im Vergleich zur Implementierung der entsprechenden Operationen f¨ur Binomial-Heaps
und Fibonacci-Heaps) einfach ist.
4.1.1 Repr ¨asentation bin¨arer Heaps
Bin¨are Heaps sind laut Deﬁnition immer vollst¨andige Bin¨arb¨aume, haben also eine feste
Struktur, die nicht explizit gespeichert werden muss. Es bietet sich daher eine ”struk-
turlose“ Repr¨asentation als Liste an. Hierbei schreibt man die Eintr ¨age des Heaps von
der Wurzel beginnend ebenenweise in die Liste, wobei die Eintr ¨age jeder Ebene von
links nach rechts durchlaufen werden. Wir werden gleich sehen, dass es hier g ¨unstig ist,
den ersten Eintrag der den Heap repr ¨asentierenden Liste freizuhalten; konkret setzen
wir diesen auf ”None“. Der Min-Heap aus Abbildung 4.1 wird beispielsweise durch die
folgende Liste repr¨asentiert:
[None ,3,5,58,65,10,85,98,67,82,49,23,136,195,127, ... ]

## Seite 132

4.1 Bin ¨are Heaps 117
Repr¨asentiert man also einen Heap als Liste l, so ist leicht nachvollziehbar, dass das
linke Kind von l [i ] der Eintrag l [2*i ] und das rechte Kind der Eintrag l [2*i +1] ist.
Aufgrund der Struktur des bin¨aren Heaps gilt, dass die H¨ohe eines Heaps dernElemente
enth¨alt immer ⌈log2 n⌉ist, also in O(log n) ist.
4.1.2 Einf ¨ugen eines Elements
Das in Listing 4.1 gezeigte Programm implementiert die Operation ”Einf¨ugen“ eines
Elementes in einen als Liste repr ¨asentierten Heap.
1 def insert(heap, x):
2 heap.append(x)
3 i = len(heap)-1
4 while heap[i/2]>heap [i]:
5 heap[i/2], heap[i ] = heap[i],heap[i/2]
6 i = i/2
Listing 4.1: Einf¨ugen eines Elementes in einen als Liste repr ¨asentierten Min-Heap
Das einzuf ¨ugende Element x wird zun¨achst hinten an den Heap angeh ¨angt; dies ent-
spricht dem Kommandoheap.append(x) in Zeile 2. Anschließend wird das eingef¨ugte Ele-
ment solange durch Tausch mit dem Vaterknoten die Baumstruktur”hoch“transportiert,
bis die Heapbedingung erf ¨ullt ist. Die while-Schleife wird solange durchlaufen wie der
Wert des eingef¨ugten Knotens kleiner ist als der Wert seines Vaterknotens, d. h. sie wird
solange durchlaufen wie die Bedingung heap[i/2]>heap [i] gilt.
Da die Anzahl der Tauschungen durch die H¨ohe des Heaps begrenzt ist, ist die Laufzeit
dieser Operation oﬀensichtlich in O(log n).
4.1.3 Minimumsextraktion
Das minimale Element eines bin¨aren Heaps wird wie folgt extrahiert: Das letzte Element
aus einer den Heap repr ¨asentierenden Liste heap, also heap[ -1], wird an die Stelle
der Wurzel, also heap[1], gesetzt. Dies verletzt i. A. die Heap-Bedingung. Die Heap-
Bedingung kann wiederhergestellt werden, indem man dieses Element solange durch
Tauschen mit dem kleineren der beiden Kinder nach ”unten“ transportiert, bis die
Heap-Bedingung wiederhergestellt ist.
Listing 4.2 zeigt eine Implementierung der Minimumsextraktion. In der Variablen n
ist w¨ahrend des ganzen Programmablaufs immer der Index des ”letzten“ Elements des
Heaps gespeichert. In den Zeilen 3 und 4 wird das ”letzte“ Element des Heaps an die
Wurzel gesetzt. Die Durchl ¨aufe der while-Schleife transportieren dann das Wurzel-
Element solange nach ”unten“, bis die Heap-Bedingung wieder erf ¨ullt ist. Am Anfang
der while-Schleife zeigt die Variable i immer auf das Element des Heaps, das m ¨ogli-
cherweise die Heap-Bedingung noch verletzt. In Zeile 9 wird das kleinere seiner beiden
Kinder ausgew ¨ahlt; falls dieses Kind gr ¨oßer ist als das aktuelle Element, d. h. falls
lst [i ]≤lst [k ], so ist die Heap-Bedingung erf ¨ullt und die Schleife kann mittels break

## Seite 133

118 4 Heaps
1 def minExtract(lst ):
2 returnVal=lst[1]
3 lst [1]= lst [ -1] # letztes Element an die Wurzel
4 del( lst [ -1])
5 n=len(lst) -1 # n zeigt auf das letzte Element
6 i=1
7 while i≤n/2:
8 j=2 *i
9 if j<n and lst[j]>lst[j +1]: j +=1 # w¨ahle kleineres der beiden Kinder
10 if lst [i ]≤lst [j ]: break
11 lst [i ], lst [j ]=lst [j ], lst [i ]
12 i=j
13 return returnVal
Listing 4.2:Implementierung der Minimumsextraktion, bei der das Wurzel-Element des Heaps
entfernt wird.
abgebrochen werden. Falls jedoch dieses Kind kleiner ist als der aktuelle Knoten, ist
die Heapbedingung verletzt, und Vater und Kind m ¨ussen getauscht werden (Zeile 11).
Durch die Zuweisung i=j fahren wir im n ¨achsten while-Schleifendurchlauf damit fort,
den getauschten Knoten an die richtige Position zu bringen.
Die H¨ohe des Heaps begrenzt die maximal notwendige Anzahl der Vergleichs- und Tau-
schoperationen auch bei der Minimumsextraktion. Damit ist die Laufzeit der Minimum-
sextraktion auch in O(log n).
4.1.4 Erh ¨ohen eines Schl¨usselwertes
Soll ein Element heap[i] eines als Liste repr ¨asentierten Heaps heap erh¨oht werden, so
ist die Heap-Bedingung nach dem Erh ¨ohen evtl. verletzt. Die Heap-Bedingung kann
dadurch wiederhergestellt werden, indem man das Element soweit im Heap ”sinken“
l¨asst (d. h. sukzessive mit einem der Kinder tauscht), bis die Heap-Bedingung wieder-
hergestellt ist. Die in Listing 4.3 gezeigte Funktion minHeapify implementiert dies.
Die Funktion minHeapify stellt die Heap-Bedingung, falls diese verletzt ist, f ¨ur den
Knoten an Index i des Heaps heap wieder her, und zwar dadurch, dass der Knoten
im Heap solange nach ”unten“ gereicht wird, bis die Heap-Bedingung wieder erf ¨ullt
ist. Die in Zeile 2 und 3 deﬁnierten Variablen l und r sind die Indizes der Kinder des
Knotens an Index i. In Zeile 5 wird mittels einer Listenkomprehension eine i. A. drei-
elementige Liste nodes aus den Werten des Knotens an Indexi und seiner beiden Kinder
erstellt. Um den Knoten mit kleinstem Wert zu bestimmen, wird nodes sortiert; danach
beﬁndet sich der Wert des kleinsten Knotens in nodes[0][0] und der Index des kleinsten
Knotens in nodes[0][1]. Falls der Wert des Knotens i der kleinste der drei Werte ist, ist
die Heap-Bedingung erf ¨ullt und die Funktion minHeapify kann verlassen werden; falls
andererseits einer der Kinder einen kleineren Wert hat (d. h. smallestIndex̸=i) so ist
die Heap-Bedingung verletzt und der Knoten an Index i wird durch Tauschen mit dem
kleinsten Kind nach ”unten“ gereicht; anschließend wird rekursiv weiterverfahren.

## Seite 134

4.2 Binomial-Heaps 119
1 def minHeapify(heap,i):
2 l = 2 *i
3 r = l +1
4 n = len(heap)-1
5 nodes = [(heap [v],v) for v in [i , l ,r ] if v≤n]
6 nodes.sort()
7 smallestIndex = nodes[0][1]
8 if smallestIndex ̸= i :
9 heap[i ], heap[smallestIndex ] = heap[smallestIndex ],heap[i]
10 minHeapify(heap,smallestIndex)
Listing 4.3:Die Funktion minHeapify, die den Knoten an Index i soweit sinken l ¨asst, bis die
Heap-Bedingung des Heaps ”heap“ wiederhergestellt ist.
Auch die Laufzeit dieser Operation ist durch die H ¨ohe des bin¨aren Heaps begrenzt und
liegt in O(log n).
4.2 Binomial-Heaps
6
18 20 15 203 384 866
26 28 317 232 139 97 168 483 537 22 374 501 352 925 720
167 410 186 507 325 305 517 559 932 502
217 267 835 616 649 535
574 638 772
984
718
383 715 581
738
964
223 103 293 316 262 498
518 801 998
975
599
36 485 385
306
630
23
200 52 400 346
464 247 970 565 331 701
486 744 257
533
909
209
359 677
707
Bildquelle:
http://www.di.ens.fr/ jv/
Ein Binomial-Heap besteht aus mehreren Binomial-B ¨aum-
en, deren Knoten jeweils die Heap-Bedingung erf ¨ullen. Diese
B¨aume besitzen eine festgelegte rekursive Struktur, die eine
einfache Verschmelzung zweier B¨aume erlaubt.
Binomial-Heaps wurden 1978 [18] von Jean Vuillemin, Pro-
fessor f¨ur Informatik an der an der Ecole Normale Superieure
in Paris, eingef¨uhrt.
Wie schon zu Beginn des Kapitels erw¨ahnt, gibt es einige Anwendungen, die eine eﬃzien-
te Vereinigung zweier Heaps ben¨otigen; man denke etwa an Mehrkern-Prozessorsysteme,
die je nach Auslastung der Prozessoren Prozess-Priorit¨atswarteschlangen aufteilen bzw.
vereinigen m¨ussen. W¨ahrend herk¨ommliche bin¨are Heaps keine ”schnelle“ Vereinigung
(in O(log n) Schritten) unterst¨utzen, sind Binomial-Heaps gerade auf die Unterst¨utzung
einer eﬃzienten Vereinigung hin entworfen.

## Seite 135

120 4 Heaps
Aufgabe 4.1
Implementieren Sie die Vereinigungs-Operation mergeHeaps, die zwei bin ¨are Heaps
miteinander vereinigt. Welche Laufzeit hat ihre Implementierung?
4.2.1 Binomial-B ¨aume
Ein Binomial-Heap besteht aus mehreren Binomial-B¨aumen. Wir beginnen zun¨achst mit
der Deﬁnition von Binomial-B¨aumen. Die Struktur eines Binomial-Baums der Ordnung
k kann folgendermaßen induktiv deﬁniert werden:
 Ein Binomial-Baum der Ordnung ”0“ besteht aus einem einzelnen Knoten.
 Ein Binomial-Baum der Ordnung k besteht aus einem Wurzelknoten mit k Nach-
folgern: Der erste Nachfolger ist ein Binomial-Baum der Ordnung k, der zweite
Nachfolger ist eine Binomial-Baum der Ordnung k−1, usw.; der letzte Nachfolger
ist ein Binomial-Baum der Ordnung ”0“, also ein einzelner Knoten.
Ein Binomial-Baum beispielsweise der Ordnung 4 hat folgende Struktur:
Ein Binomial-Baum der Ordnung k enth¨alt genau 2k Elemente; dies kann man einfach
¨uber vollst¨andige Induktion zeigen – siehe hierzu Aufgabe 4.2.
Aufgabe 4.2
Wie viele Knoten hat ein Binomial-Baum der Ordnung k?
(a) Schreiben Sie eine rekursive Python-Funktion anzKnotenBinomial(k), die die
Anzahl der Knoten eines Binomial-Baums der Ordnung k zur¨uckliefert; diese
Funktion sollte sich an der induktiven Deﬁnition eines Binomial-Baums orien-
tieren.
(b) Zeigen Sie mit Hilfe der vollst ¨andigen Induktion, dass ein Binomial-Baum der
Ordnung k genau 2k Elemente enth¨alt.
4.2.2 Repr ¨asentation von Binomial-B¨aumen
Es gibt – wie auch bei vielen anderen Datenstrukturen – mehrere M¨oglichkeiten der Re-
pr¨asentation. Binomial-B¨aume k¨onnen in Python etwa als Klasse repr¨asentiert werden.

## Seite 136

4.2 Binomial-Heaps 121
Legt man Wert auf eine klare Darstellung der Algorithmen, so scheint eine m¨oglichst ein-
fache Repr¨asentation am g ¨unstigsten, etwa die Repr ¨asentation eines Binomial-Baums
als Tupel. Die erste Komponente des Tupels enth ¨alt das Element an der Wurzel des
Binomial-Baums und die zweite Komponente ist eine Liste der Unterb¨aume des Binomial-
Baums. Die Repr ¨asentation eines Binomial-Baums der Ordnung k h¨atte in Python al-
so das folgende Aussehen (wobei x der an der Wurzel gespeicherte Wert und bti ein
Binomial-Baum der Ordnung i darstellt):
(x, [btk−1 , btk−2 , btk−3 , ... , bt1 , bt0 ])
Ist bt ein Binomial-Baum der Ordnung k, so muss also immer len(bt [1]) == k sein.
Zwei einfache Beispiele: Ein Binomial-Baum der Ordnung 0
72
77 91
89
Abb. 4.2: Binomial-
Baum der Ord. 2.
dessen Wurzel die Zahl”13“ enth¨alt entspricht somit dem Python-
Wert (13, [ ]); der in Abbildung 4.2 gezeigte Binomial-Baum der
Ordnung 2 entspricht dem folgenden Python-Wert:
bt2 = (72,[(77, [(89, [ ]) ] ),(91, [ ]) ])
Aufgabe 4.3
Implementieren Sie eine Python-Funktion isBinomial(bt), die genau dann ”True“
zur¨uckliefert, wenn das Argument bt ein g¨ultiger Binomial-Baum ist.
Aufgabe 4.4
Implementieren Sie eine Python-Funktion bt2str (bt), die einen Binomial-Baum bt in
eine geeignete Stringrepr¨asentation umwandelt.
4.2.3 Struktur von Binomial-Heaps
Jeder Binomial-Heap besteht aus mehreren Binomial-B ¨aumen verschiedener Ordnun-
gen; f ¨ur jeden der Binomial-B ¨aume muss zus ¨atzlich die Heapbedingung erf ¨ullt sein,
d. h. (im Falle von Min-Heaps) muss ein Knoten immer einen gr ¨oßeren Wert gespei-
chert haben als seine Kinderknoten.
Wollen wir n Elemente in einem Binomial-Heap speichern, so ist die Struktur dieses
Binomial-Heaps bestimmt durch die Bin ¨ardarstellung der Zahl n. Angenommen wir
wollen 22 (in Bin ¨ardarstellung: ”10110“) Elemente in einem Binomial-Heap speichern,
so muss dieser Binomial-Heap genau einen Binomial-Baum der Ordnung 4 (das von
rechts gesehen, von Null an gez¨ahlte Bit an Position ”4“ von ”10110“ ist gesetzt), einen
Binomial-Baum der Ordnung 2 (das Bit an Position ”2“ von ”10110“ ist gesetzt) und
einen Binomial-Baum der Ordnung 1 (das Bit an Position ”1“ von ”10110“ ist gesetzt)
enthalten. Ebenso wie die Bin¨ardarstellung der Zahl 22 eindeutig bestimmt ist, ist auch
die Struktur des Binomial-Heaps (nicht jedoch notwendigerweise die Anordnung der
Elemente im Heap) eindeutig bestimmt. Abbildung 4.3 zeigt ein Beispiel eines Binomial-
Heap, der 22 Elemente enth ¨alt.

## Seite 137

122 4 Heaps
k= 3 k= 2k= 4 k= 1 k= 0
13
64 19 16
59
8041
5772 69 99 71 27
91 87 77 112
89
37
49 58
90
Abb. 4.3: Beispiel eines Binomial-Heap mit 22 Elementen, dessen Knoten der Min-Heap-
Bedingung gen¨ugen.
4.2.4 Repr ¨asentation von Binomial-Heaps
Oﬀensichtlich kann man einen Binomial-Heap in Python einfach als Liste von Binomial-
B¨aumen repr ¨asentieren; der in Abbildung 4.3 gezeigte Binomial-Heap beispielsweise
w¨are durch folgenden Python-Wert repr¨asentiert:
[bt4, None, bt2, bt1, None]
wobei bt1, bt2 und bt4 jeweils die in Abbildung 4.3 gezeigten Binomial-B ¨aume der
Ordnung 1, 2 bzw. 4 darstellen.
Aufgabe 4.5
Geben Sie die Pythonrepr ¨asentation des in Abbildung 4.3 gezeigten Binomial-Heaps
an.
Aufgabe 4.6
Implementieren Sie eine Python-Funktion isBinHeap(bh), die genau dann ”True“
zur¨uckliefert, wenn bh ein g¨ultiger Binomial-Heap ist.
4.2.5 Verschmelzung zweier Binomial-B ¨aume
Die Struktur der Binomial-B ¨aume ist genau deshalb algorithmisch so interessant, weil
man zwei Binomial-B ¨aume bt1 und bt2 der Ordnung k sehr einfach in O(1) Schritten
zu einem Binomial-Baum der Ordnung k+ 1 verschmelzen kann. Angenommenbt1<bt2
(d. h. der an der Wurzel von bt1 gespeicherte Wert ist kleiner als der in der Wurzel
von bt2 gespeicherte Wert). Dann besteht die Verschmelzungsoperation einfach darin,
bt2 als linkesten Teilbaum unter den Binomial-Baum bt1 zu h¨angen. Der Wurzelknoten
dieses neuen Baums hat k+1 Kinder, die jeweils Binomial-B¨aume der Ordnung k, k−1,
..., 0 darstellen – ist also ein Binomial-Baum der Ordnung k+ 1. Abbildung 4.4 zeigt

## Seite 138

4.2 Binomial-Heaps 123
die Verschmelzung zweier Binomial-B ¨aume der Ordnung 3 zu einem Binomial-Baum
der Ordnung 4.
∪ =37
49
10
58
59
80
16
90
64
72
91 87
69
77
89
99
72
91 87
69
77
89
99
64 37
49 58
59
80
16
10
90
Abb. 4.4: Verschmelzung zweier Binomial-B ¨aume der Ordnung k zu einem Binomial-Baum
der Ordnung k+ 1– hier ist k= 3.
Auch die entsprechende in Listing 4.4 gezeigte Implementierung in Python ist relativ
simpel. Die Funktion meltBinTree liefert einen neuen Binomial-Baum zur ¨uck, der die
1 def meltBinTree(bt0,bt1):
2 # Voraussetzung: bt0<bt1
3 root = lambda x : x[0]
4 subtrees = lambda x : x[1]
5 return ( root(bt0 ), [ bt1 ] +subtrees(bt0) )
Listing 4.4: Verschmelzung zweier Binomial-B¨aume
Verschmelzung der beiden Binomial-B ¨aume bt0 und bt1 darstellt; dieser wird direkt
nach dem return-Kommando generiert und besteht einfach aus dem Wurzelknoten
root(bt0) des Baumes bt0; der linkeste Unterbaum ist der komplette Binomial-Baum
bt1; die weiteren Unterb ¨aume sind die Unterb ¨aume des Binomial-Baums bt0, n¨amlich
subtrees(bt0).
4.2.6 Vereinigung zweier Binomial-Heaps
Die Verschmelzung zweier Binomial-Heaps hat große¨Ahnlichkeit mit der Addition zwei-
er Bin¨arzahlen: Ein gesetztes Bit an der k-ten bin¨aren Stelle entspricht dem Vorhanden-
sein eines Binomial-Baums der Ordnung k im Binomial-Heap; ein nicht-gesetztes Bit
an der k-ten bin¨aren Stelle entspricht dagegen einem None-Eintrag an der von rechts
gesehen k-ten Stelle der Python-Liste, die den Binomial-Heap repr ¨asentiert. Auch das
Verwenden eines Carry-Bits und die bitweise Berechnung der einzelnen Stellen durch
einen Volladdierer hat eine Entsprechung bei der Vereinigung zweier Binomial-Heaps.

## Seite 139

124 4 Heaps
Abbildung 4.5 zeigt ein Beispiel f ¨ur die Vereinigung zweier Binomial-Heaps; auch die
Darstellung in dieser Abbildung ist angelehnt an die Addition zweier Bin ¨arzahlen.
W¨ahrend der Vereinigung entstehen zwei Carry-B ¨aume, die genau wie ein Carry-Bit
in den f¨ur die n¨achste Stelle zust¨andigen Volladdierer einﬂießen.
Listing 4.5 zeigt die Implementierung eines ”Volladdierers“, der zwei Binomial-B¨aume
und einen Carry-Baum addiert und ein Tupel bestehend aus einem dem Summen-Bit
entsprechenden Binomial-Baum und einem dem Carry-Bit entsprechenden Binomial-
Baum zur¨uckliefert. Ein nicht-gesetztes Bit entspricht wiederum dem Wert ”None“, ein
gesetztes Bit entspricht einem Binomial-Baum der Ordnung k.
1 def fullAddB(bt0,bt1,c):
2 bts = sorted([b for b in [bt0,bt1,c ] if b ])
3 if len(bts)≥2:
4 c = meltBinTree(bts[0],bts [1])
5 return (None if len(bts)==2 else bts[2], c)
6 else:
7 return (None if len(bts)==0 else bts[0], None)
Listing 4.5: Implementierung des Pendants eines Volladdierers zur Vereinigung zweier
Bin¨arb¨aume und eines Carry-Baums.
Zun¨achst werden in Zeile 2 die None-Werte mittels der Bedingung ”if b“ in der Li-
stenkomprehension ausgeﬁltert und die ¨ubergebenen Binomial-B ¨aume der Gr ¨oße nach
sortiert in der Liste bts abgelegt. Da die Sortierung stets lexikographisch erfolgt (sie-
he auch Anhang A.6 auf Seite 295) erh ¨alt man dadurch in bts [0] den Baum mit dem
kleinsten Wurzelelement und in bts [2] den Baum mit dem gr ¨oßten Wurzelelement;
diese Information ist f ¨ur die Verschmelzungsoperation in Zeile 4 wichtig. Immer dann,
wenn der FunktionfullAddB zwei oder mehr Binomial-B¨aume der Ordnung k¨ubergeben
werden, wird in Zeile 4 ein Carry-Baum der Ordnung k+ 1 erzeugt, der dann zusam-
men mit dem Summenbaum in Zeile 5 zur ¨uckgeliefert wird. Wurden weniger als zwei
Binomial-B¨aume ¨ubergeben, so wird als Carry-Baum ”None“ und als Summen-Baum
der eine ¨ubergebene Binomial-Baum ¨ubergeben (bzw. ”None“ falls nur ”None“-Werte
¨ubergeben wurden).
Die Verschmelzung zweier Binomial-Heaps erfolgt nun einfach durch die stellenweise
Ausf¨uhrung von fullAddB. Listing 4.6 zeigt eine Implementierung.
1 def merge(h1,h2):
2 h1 = [None ] *(len(h2) -len(h1)) +h1
3 h2 = [None ] *(len(h1) -len(h2)) +h2
4 erg=[None ] *(len(h1) +1) ; c = None
5 for i in range(len(h1)) [ ::-1]:
6 (s,c) = fullAddB(h1[i],h2[i ], c)
7 erg[i +1]=s
8 erg[0]= c
9 return erg
Listing 4.6: Verschmelzung zweier Binomial-Heaps

## Seite 140

4.2 Binomial-Heaps 125
Carry-Baum
Baum
Carry-
∪
k= 5 k= 4 k= 3 k= 2 k= 1 k= 0
heap1 heap2 heap1 ∪heap2
27
35 31 70
55 43 47
89
16
67 22
69
69
16
37 67 22
49 58
90
13
19 1641
112
5771 2772 69 99
91 87 77
89
64
59
80
59
80
37
49 58
90
16
72 69 99
91 87 77
89
64 19
112
71 27
41
57
49
90
58
22
16
3727
13
35 31 70
55 43 47
89
69
67
35 31 70
55 43 47
89
69
67
16
27 37
49
90
58
22
Abb. 4.5: Vereinigung zweier Binomial-Heaps. Der obere Heap enth ¨alt 22 = 10110b Elemente, der untere Heap enth ¨alt 12 = 01100b
Elemente. Die Vereinigung der beiden Heaps hat ¨Ahnlichkeit mit der bin ¨aren Addition von 10110 bund 01100 b. Betrachten wir die stel-
lenweise Addition beginnend mit dem niederwertigsten (rechten) in zu h¨oherwertigsten (linken) Bit. Anf¨anglich ist – wie bei jeder Additi-
on – das Carry-Bit ”0“ und es wird zun¨achst fullAdd (0,0,0) berechnet – dies entspricht der Berechnung von fullAddB(None,None,None)
bei der Heap-Vereinigung. Zur Berechnung der zweiten Stelle der Addition wird fullAdd (1,0,0) berechnet – dies entspricht der Berech-
nung fullAddB ((59,[(80, [ ]) ] ),None,None); die Summe entspricht hierbei einfach dem ersten Argument, das neue Carry-Bit bleibt
None. Bei der Addition an Stelle k = 2entsteht ein Carry-Baum (dargestellt in einem weißen Kasten), der in die Addition an Stelle
k= 3wieder einﬂießt. Auch bei der Addition an Stelle k= 3entsteht wieder ein Carry-Baum der seinerseits in die Addition an Stelle
k= 4einﬂießt. Ergebnis ist schließlich ein Binomial-Heap der einen Eintrag mehr besitzt als seine beiden Summanden.

## Seite 141

126 4 Heaps
In den Zeilen 2 und 3 werden die beiden ¨ubergebenen Heaps auf die gleiche L ¨ange
gebracht, indem gegebenenfalls ”None“-Werte links (also an den h ¨oherwertigen ”Bit“-
Positionen) eingef¨ugt werden. In der Variablen erg speichern wir das Ergebnis der Ver-
schmelzung und f ¨ullen diese zun ¨achst mit len(h1) +1 ”None“-Werten auf, also einer
Stelle mehr, als der l ¨angere der beiden ¨ubergebenen Binomial-Heaps. Analog zur bit-
weisen Addition zweier Bin¨arzahlen, setzen wir anf¨anglich den Carry-Baum auf ”None“.
Die for-Schleife ab Zeile 5 l ¨auft ¨uber die Stellen der Binomial-Heaps und f ¨uhrt f¨ur je-
de Stelle eine Volladdition durch. Schließlich wird der zuletzt entstandene ¨Ubertrag
der h¨ochstwertigen Stelle von erg zugewiesen. Man beachte, dass in der for-Schleife ab
Zeile 5 die Binomial-Baum-Listen von ”hinten“ nach ”vorne“ durchlaufen werden, also
tats¨achlich von der niederwertigsten Stelle h1[ -1] bzw. h2[ -1] bis zur h¨ochstwertigsten
Stelle h1[0] bzw. h2[0].
Die Laufzeit der Verschmelzung zweier Binomial-Heaps mit jeweilsnbzw. mElementen
liegt oﬀensichtlich in O(log(n+ m)): Die for-Schleife ab Zeile 5 wird len(h) ≤log2(n+
m)-mal durchlaufen und die Ausf¨uhrung der Funktion fullAddB ben¨otigt O(1) Schritte.
4.2.7 Einf ¨ugen eines Elements
Man kann ein Element x einfach dadurch in einen Binomial-Heap bh einf¨ugen, indem
man aus x einen einelementigen Binomial-Heap (bestehend aus einem einelementigen
Binomial-Baum der Ordnung 0) erzeugt und diesen dann mit bt verschmilzt.
Aufgabe 4.7
Implementieren Sie eine Funktion insertBinomialheap(bh,x) die als Ergebnis einen
Binomial-Heap zur¨uckliefert, der durch Einf¨ugen von x in bh entsteht.
Die Einf¨ugeoperation hat oﬀensichtlich eine Worst-Case-Laufzeit vonO(log n), die etwa
dann eintritt, wenn durch den Verschmelzungsprozess alle ”Bits“ des Binomial-Heap bh
von Eins auf Null ”umkippen“, wenn also in einen Binomial-Heap mit 2n−1 enthaltenen
Elementen ein neues Element hinzugef ¨ugt wird. Da dieser Fall jedoch selten eintritt,
kann man zeigen, dass die amortisierte Laufzeit in O(1) liegt. Um diese theoretisch
m¨ogliche (amortisierte) Laufzeit voo O(1) zu erreichen, m ¨usste jedoch die in Listing
4.6 gezeigte Implementierung angepasst werden; siehe hierzu auch die folgende Aufgabe
4.8.
Aufgabe 4.8
...
4.2.8 Extraktion des Minimums
Ein Heap, der dazu verwendet wird, eine Priorit ¨atswarteschlange zu implementieren,
sollte eﬃzient das Finden und die Extraktion des minimalen Elements unterst ¨utzen.

## Seite 142

4.3 Fibonacci Heaps 127
Zun¨achst k ¨onnen wir feststellen, dass das Finden des minimalen Elements O(log n)
Schritte ben ¨otigt: Alle Wurzelelemente der O(log n) Binomial-B ¨aume m ¨ussen hierf ¨ur
verglichen werden.
Nehmen wir an, das minimale Wurzelelement ist das Wurzelelement eines Binomial-
Baums btk der Ordnung k. Das anschließende L¨oschen dieses Elements erzeugt k”freie“
Binomial-B¨aume. Diese werden dann in einem Binomial-Heap (der 2 k −1 Elemente
enth¨alt) zusammengefasst und mit dem urspr ¨unglichen Binomial-Heap (ohne btk) ver-
schmolzen.
Listing 4.7 zeigt die Implementierung der Extraktion des minimalen Elements.
1 def minExtractB(bh):
2 (bt ,k) = min([(bt,k) for k,bt in enumerate(bh) if bt ̸=None])
3 bh2 = [None if i==k else bt2 for i,bt2 in enumerate(bh)]
4 return minEl,merge(bh2,bt[1])
Listing 4.7: Implementierung der MinExtract-Funktion
Zun¨achst wird in Zeile 2 derjenige Binomial-Baumbt gesucht, der das minimale Element
als Wurzelelement besitzt – dies kann inO(log n) Schritten erfolgen. Das Wurzelelement
bt [0] dieses Binomial-Baums wird dann in Zeile 4 zusammen mit dem Binomial-Heap
zur¨uckgegeben, der durch L¨oschen von bt [0] entsteht.
4.3 Fibonacci Heaps
535 51
98 76
83
167 91 138
29
61 84 70 61 185 55
252 360 119 167 155
185
33 328 63 96
98 101 176
90 29 400 279 312
335
297 681
293 202 184
216
233 95
862
84 107 64 112 76
101 98 128 205
104 107 501 284
111 568 210
358 726 521
187
122 134 428
759 240
663
156 143
217
270
178
115 188
88 96 141 644
151 89 318
179 226
330
104
254 272
325
229
99 175
103 532
124
134
167
102 707
637
210
221
116 145 136
127 125 326
230 140
245
161
367
276 769
389 573
406
137 256
172
301 209
648 407
minFH
Michael Fredman und Robert Tarjan entwickelten im Jahr 1984 die Fibonacci-Heaps
und publizierten ihre Entdeckung im Jahre 1987 [9].
Fibonacci-Heaps sind Binomial-Heaps ¨ahnlich, und tats¨achlich waren Fibonacci-Heaps
von Tarjan und Fredman auch als eine Art”Verbesserung“ von Binomial-Heaps gedacht.
Wie an obiger Abbildung eines Fibonacci-Heaps schon zu erkennen, sind sie etwas we-
niger strukturiert als Binomial-Heaps. Sie besitzen f ¨ur einige wichtige Operationen wie
die Verschmelzung und die Minimumsbestimmung eine bessere (amortisierte) Laufzeit
als Binomial-Heaps.
Ebenso wie Binomial-Heaps bestehen auch Fibonacci-Heaps aus einer Menge von ein-
zelnen B¨aumen, die jeweils der Heap-Bedingung gen ¨ugen. Jedoch ist die Struktur eines

## Seite 143

128 4 Heaps
Fibonacci-Heaps ﬂexibler und einige notwendige Restrukturierungs-Operationen etwa
bei der Verschmelzung zweier Fibonacci-Heaps werden geschickt auf einen sp ¨ateren
Zeitpunkt verschoben; durch dieses ”Verschieben“ kann eine erstaunlich gute amorti-
sierte Laufzeit vieler Operationen erreicht werden: Die Verschmelzung zweier Heaps,
etwa, ist so in einer amortisierten Laufzeit von O(1) m ¨oglich; das Erniedrigen eines
Schl¨usselwertes ist ebenfalls in O(1) m¨oglich.
4.3.1 Struktur eines Fibonacci-Heaps
Ein Fibonacci-Heap besteht aus einer Liste einzelner B ¨aume, die jeweils die
(Min-)Heap-Bedingung erf ¨ullen – also ihrerseits Heaps sind. Es gilt also, dass der
Schl¨usselwert eines Knotens immer kleiner sein muss als die Schl ¨usselwerte seiner Kin-
der. Diese B¨aume, aus denen ein Fibonacci-Heap besteht, bezeichnen wir im Folgenden
auch als Fibonacci-B¨aume. Genau wie im Falle der Binomial-Heaps deﬁniert man die
Ordnung eines Fibonacci-Baums als die Anzahl der Kinder, die das Wurzelelement be-
sitzt.
Zus¨atzlich wird ein Zeiger auf den Fibonacci-Baum mitgef¨uhrt, dessen Wurzel das mini-
male Element des Fibonacci-Heaps enth¨alt. Dies erm¨oglicht etwa eine Implementierung
der getMin-Funktion in O(1) Schritten.
Aufgabe 4.9
Erkl¨aren Sie, warum der Knoten mit minimalem Schl ¨usselwert sich immer an der
Wurzel eines Fibonacci-Baums beﬁnden muss.
Einige Knoten des Fibonacci-Heaps sind markiert – in Abbildung 4.6 sind dies die
grau-gef¨ullten Knoten.
minFH
80 75
97
3059
88
40 65
99
94
85
89
83
Abb. 4.6: Beispiel eines Fibonacci-Heaps, der aus vier Fibonacci-B ¨aumen besteht: einem
Fibonacci-Baum der Ordnung 1, einem Fibonacci-Baum der Ordnung 3 und zwei Fibonacci-
B¨aumen der Ordnung 0. Der Fibonacci-Heap enth¨alt einen Zeiger, der auf den Fibonacci-Baum
zeigt, der das minimale Element Fibonacci-Heaps als Wurzelelement enth ¨alt.
Wie wir in Abschnitt 4.3.8 zeigen werden, stellen alle Operationen auf Fibonacci-Heaps
sicher, dass der maximale Grad aller Knoten in O(log n) ist. Genauer: Der Grad aller
Knoten eines Fibonacci-Heaps mitnElementen ist immer≤logφ(n) mit φ= (1+
√
5)/2.

## Seite 144

4.3 Fibonacci Heaps 129
4.3.2 Repr ¨asentation in Python
Es gibt viele m ¨ogliche Arten Fibonacci-Heaps in Python zu repr ¨asentieren:
 Der klassische objektorientierte Ansatz besteht darin, eine Klasse (etwa mit Na-
men FibonacciHeap) zu deﬁnieren, alle Komponenten der Datenstruktur (also die
einzelnen B¨aume, der Zeiger auf den Baum, der das minimale Element enth ¨alt,
Information dar ¨uber, ob ein Knoten markiert ist) als Attribute der Klasse zu
deﬁnieren und alle Operationen auf Fibonacci-Heaps als Methoden der Klasse
FibonacciHeap zu deﬁnieren. Zwar hat diese Art der Repr¨asentation in Python ei-
nige Vorteile; beispielsweise man kann sich einfacher mittels der str -Methode
eine String-Repr¨asentation deﬁnieren; man kann typsicherer programmieren, usw.
Wir bevorzugen jedoch eine andere Art der Repr¨asentation, die eine knappere und
damit pr¨agnantere Formulierung der meisten hier beschriebenen Algorithmen er-
laubt.
 Eine Repr ¨asentation ¨ahnlich der f ¨ur Binomial-Heaps w ¨are denkbar; im Gegen-
satz zu einem Binomial-Heap besteht jedoch ein Fibonacci-Heap aus mindestens
zwei Komponenten (die Liste der B ¨aume und der Zeiger auf den Baum, der das
minimale Element enth¨alt). Auch ein einzelner Knoten m¨usste noch die Zusatzin-
formation mit sich f ¨uhren, ob er markiert ist und – wie wir sp ¨ater sehen werden
– ben¨otigt er einen Zeiger auf seinen Elternknoten.
 Auch eine Repr¨asentation unter Verwendung von Pythons dict-Typs ist m¨oglich.
Diese ist der Art der Repr ¨asentation, die wir bei den Binomial-Heaps im letzten
Kapitel verwendet haben, ¨ahnlich; jedoch lassen sich so die einzelnen Komponen-
ten eines Fibonacci-Heaps bzw. eines Fibonacci-Baums expliziter benennen. Wir
verwenden f¨ur die Repr¨asentation von Fibonacci-Heaps im Weiteren diese Art der
Repr¨asentation.
Ein Fibonacci-Heap besteht aus zwei Komponenten:
 Der ”treesFH“-Eintrag enth¨alt die Liste der Fibonacci-B ¨aume, aus denen der Fi-
bonacci-Heap besteht
 Der ”minFH“-Eintrag enth ¨alt den Index desjenigen Fibonacci-Baums, der das
minimale Element des Fibonacci-Heaps enth ¨alt.
Ein Fibonacci-Baum besteht seinerseits aus vier Komponenten:
 Der ”rootFT“-Eintrag enth¨alt den im jeweiligen Knoten gespeicherten Schl ¨ussel-
wert.
 Der ”subtreesFT“-Eintrag enth¨alt die Liste der Kinder des Knotens.
 Der ”markedFT“-Eintrag enth¨alt einen booleschen Wert, der anzeigt, ob der je-
weilige Knoten markiert ist.
 Der ”parentFT“-Eintrag enth¨alt den Verweis auf den Elternknoten bzw. den Wert
None, falls es sich um einen Wurzelknoten handelt.
Ein Fibonacci-Heap ﬁbonacciHeap und ein Fibonacci-Baum ﬁbonacciTree kann man
sich also (schemahaft) wie folgt deﬁniert denken, wobei die Variablen ft , ft0, ft1, usw.
Fibonacci-B¨aume, b einen booleschen Wert und i einen Indexwert enthalten sollten.
ﬁbonacciHeap = {treesFH : [ ft0 , ft1 , ... ] , minFH : i }
ﬁbonacciTree = {rootFT : x , subtreesFT : [ ft0 , ft2 , ... ],
markedFT : b, parentFT : ft}

## Seite 145

130 4 Heaps
Die Schl¨usselwerte treesFH, minFH, rootFT und subtreesFT, markedFT und parentFT
der dict-Objekte ﬁbonacciHeap und ﬁbonacciTree k¨onnen etwa folgendermaßen vorde-
ﬁniert werden:
treesFH, minFH, rootFT, subtreesFT, markedFT, parentFT = range(6)
Der in Abbildung 4.6 gezeigte Fibonacci-Heap h¨atte somit die folgende Python-Repr¨asen-
tation, wobei an der mit”[ ... ]“ markierten Stelle noch die Repr¨asentation der Teilb¨aume
des zweiten Fibonacci-Baums einzusetzen w¨are; die ”{..}“-Eintr¨age stellen Verweise auf
den Elternknoten dar.
{treesFH: [{rootFT: 59, subtreesFT: [ {rootFT: 88, subtreesFT: [ ], markedFT: False,
parentFT: {..}}],
markedFT: False, parentFT: None},
{rootFT: 30, subtreesFT: [ ... ], markedFT: False, parentFT: {..}},
{rootFT: 40, subtreesFT: [ ], markedFT: False, parentFT: {..}},
{rootFT: 65, subtreesFT: [ ], markedFT: False, parentFT: {..}}],
minFH: 1}
Aufgabe 4.10
Vervollst¨andigen Sie den oben gezeigten Wert so, dass er den in Abbildung 4.6 ge-
zeigten Fibonacci-Heap vollst¨andig repr¨asentiert.
Aufgabe 4.11
(a) Implementieren Sie eine Funktion
FT2str(ft), die aus einem Fibonacci-
Baum eine gut lesbare Stringform
produziert. Schreiben Sie die Funktion
so, dass etwa aus dem rechts darge-
stellten Fibonacci-Baum der folgende
String produziert wird:
260 193
221
191
197 209
256
185
'185-(260 ; 191-197 ; 193-(#221 ; 209-#256))'
Die Liste der Teilb ¨aume soll also immer in runden Klammern eingeschlossen
sein; die einzelnen Teilb¨aume sollen durch ';' getrennt sein; markierten Knoten
soll ein '#' vorangestellt werden.
(b) Implementieren Sie eine Funktion FH2str(fh), die aus einem Fibonacci-Heap
eine gut lesbare Stringform produziert; verwenden Sie hierzu die in der letzten
Teilaufgabe beschriebene Funktion FT2str.

## Seite 146

4.3 Fibonacci Heaps 131
Aufgabe 4.12
Schreiben Sie eine Funktion FH2List, die die in einem Fibonacci-Heap enthaltenen
Elemente als Liste zur ¨uckliefert.
Mittels des Zeigers auf den Fibonacci-Baum, der das minimale Element enth ¨alt, kann
die Operation getMin oﬀensichtlich in konstanter Zeit implementiert werden:
def getMinFH(fh):
return fh[treesFH][fh [minFH]][rootFT ]
4.3.3 Amortisierte Laufzeit und Potenzialfunktion
Die amortisierte Laufzeit einer bestimmten Operation bezieht sich nicht auf die ein-
malige Ausf¨uhrung dieser Operation, sondern entweder auf die wiederholte Ausf¨uhrung
dieser Operation oder auf die wiederholte Ausf ¨uhrung der Operation in Kombination
mit der Ausf¨uhrung weiterer Operationen auf der Datenstruktur.
Eine M¨oglichkeit, die amortisierte Laufzeit verschiedener Operationen einer Datenstruk-
tur in Kombination zu bestimmen, besteht in der Verwendung einer sog. Potential-
Funktion. Wir verwenden hier die Potential-Funktion Φ( fh), wobei fh ein Fibonacci-
Heap ist. Die Potential-Funktion ist folgendermaßen deﬁniert:
Φ(fh) = t(fh) + 2·m(fh) (4.1)
Hierbei ist t(fh) die Anzahl der Fibonacci-B ¨aume aus denen fh besteht, und m(fh)
bezeichnet die Anzahl der markierten Knoten in fh.
Die amortisierte Laufzeit einer Operation auf einem Fibonacci-Heap setzt sich nun zu-
sammen aus der klassisch bestimmten Laufzeit plus der durch diese Operation bewirkten
Potential-¨Anderung.
4.3.4 Verschmelzung
Das Verschmelzen zweier Fibonacci-Heaps fh1 und fh2 ist denkbar einfach: Die Li-
sten fh1 [treesFH] und fh2 [treesFH] der Fibonacci-B ¨aume der beiden Heaps werden
einfach vereinigt, und der Zeiger auf den Baum, der das minimale Element enth ¨alt,
wird ggf. angepasst. Eventuell notwendige Restrukturierungsmaßnahmen werden auf
”sp¨ater“ verschoben. Durch wiederholte Ausf ¨uhrung von Verschmelzungsoperationen
kann man so Fibonacci-Heaps erzeugen, die aus sehr vielen Fibonacci-B ¨aumen beste-
hen. Das Mitf ¨uhren des Zeigers auf den Fibonacci-Baum der das minimale Element
enth¨alt, stellt jedoch immer ein eﬃzientes Finden des minimalen Elements sicher. Li-
sting 4.8 zeigt die Implementierung der Verschmelzungsoperation in Python.
1 def mergeFH(fh1,fh2):
2 if getMinFH(fh1) < getMinFH(fh2):
3 i = fh1[minFH]

## Seite 147

132 4 Heaps
4 else:
5 i = len(fh1[treesFH]) -1 +fh2 [minFH]
6 return {treesFH : fh1[treesFH] +fh2[treesFH] , minFH : i }
Listing 4.8: Implementierung der Verschmelzung zweier Fibonacci-Heaps
Die Fibonacci-B¨aume des Ergebnis-Heaps sind einfach die Vereinigung der Fibonacci-
B¨aume von fh1 mit den Fibonacci-B ¨aumen von fh2, also fh1 [treesFH] +fh2[treesFH].
Der Zeiger auf das minimale Element des Ergebnis-Heaps ist entweder der infh1 [minFH],
falls das minimale Element von fh1 kleiner ist als das minimale Element von fh2 – falls
also getMinFH(fh1) < getMinFH(fh2); oder fh2 [minFH] zeigt auf den Heap, der das
minimale Element des Fibonacci-Heaps enth ¨alt.
Aufgabe 4.13
Die in Listing 4.8 gezeigte Implementierung stellt eine nicht-destruktive Realisie-
rung der Verschmelzungs-Operation dar. Implementieren Sie eine destruktive Ver-
sion mergeFHD(fh1,fh2), die keinen ”neuen“ Fibonacci-Heap als R ¨uckgabewert er-
zeugt, sondern nichts zur ¨uckliefert und stattdessen den Parameter fh1 (destruktiv)
so ver¨andert, dass dieser nach Ausf¨uhrung von mergeFHD den Ergebnis-Heap enth¨alt.
4.3.5 Einf ¨ugen
Um eine neues Element x in einen Fibonacci-Heap fh einzuf¨ugen, erzeugt man zun¨achst
einen Fibonacci-Baum, der lediglich den Wert x enth¨alt; dies geschieht in Listing 4.9 in
Zeile 2 mittels der Funktion makeFT. Dieser einelementige Fibonacci-Baum wird dann
der Liste der Fibonacci-B ¨aume von fh angef¨ugt – dies geschieht in Zeile 3. In Zeile 5
wird der fh [minFH] ggf. angepasst.
1 def insert(x,fh ): # O(1)
2 ft = makeFT(x)
3 fh [treesFH].append(ft)
4 if getMinFH(fh) > x: # min−Pointer anpassen
5 fh [minFH] = len(fh[treesFH]) -1
Listing 4.9: Implementierung der Einf ¨ugeoperation.
Amortisierte Laufzeit. Die einfache Laufzeit der insert-Funktion ist in O(1), denn
sowohl Generierung eines einelementigen Fibonacci-Baums als auch das Anf ¨ugen und
die erneute Minimumsbestimmung (die ja nur den bisherigen Minimumswert und den
neu eingef¨ugten Knoten in Betracht zieht) ben¨otigen eine konstante Laufzeit. Die durch
insert-Funktion bewirkte Potenzialver¨anderung ist
∆Φ = 1 = O(1)
Die amortisierte Laufzeit ist somit in O(1) + O(1) = O(1).

## Seite 148

4.3 Fibonacci Heaps 133
Aufgabe 4.14
Implementieren Sie die Funktion makeFT, die in Zeile 2 in Listing 4.9 ben ¨otigt wird.
Aufgabe 4.15
Die insert-Funktion aus Listing 4.9 ist destruktiv, d. h. sie ver ¨andert ihr Argument
fh und liefert keinen Wert zur¨uck. Implementieren Sie eine nicht-destruktive Variante
dieser insert-Funktion, die ihr Argument fh nicht ver¨andert und stattdessen einen
neuen Fibonacci-Heap zur ¨uckliefert, in den das Element x eingef¨ugt wurde.
4.3.6 Extraktion des Minimums
Die Extraktion des minimalen Elements eines Fibonacci-Heaps verl¨auft in zwei Phasen.
Phase 1: Das minimale Element des Fibonacci-Heap fh wird zun ¨achst gefunden und
gel¨oscht (dargestellt in Abbildung 4.7(a)); dadurch zerf ¨allt der Fibonacci-
Baum ft , dessen Wurzel dieses minimale Element war, in len( ft [subtreesFT])
Unterb¨aume. Diese Unterb¨aume werden zun¨achst dem Fibonacci-Heap fh an-
gef¨ugt (dargestellt in Abbildung 4.7(b)).
Phase 2: Nun werden die B ¨aume des Fibonacci-Heaps sukzessive so miteinander ver-
schmolzen, dass am Ende keine zwei B ¨aume dieselbe Ordnung haben (darge-
stellt in Abbildungen 4.7(c) bis 4.7(h)).
Listing 4.10 zeigt die Implementierung der Extraktion des minimalen Elements.
1 def extractMin(fh):
2 m = getMinFH(fh)
3 newsubtrees = fh[treesFH][fh [minFH]][subtreesFT ]
4 del fh [treesFH][fh [minFH]]
5 ordTab = {}
6 for t in newsubtrees +fh [treesFH]:
7 o = len(t [subtreesFT])
8 while o in ordTab:
9 t = mergeFT(t,ordTab[o])
10 del ordTab[o]
11 o += 1
12 ordTab[o] = t
13 fh [treesFH] = ordTab.values()
14 fh [minFH] = min([(t [rootFT],i) for i,t in enumerate(fh[treesFH])])[1] #O(log n)
15 return m
Listing 4.10:Implementierung der Extraktion des minimalen Elements eines Fibonacci-Heaps.

## Seite 149

134 4 Heaps
minFH
30
80
40
75
97
59
88
65
94
85
89
83
(a) Zun¨achst wird das minimale
Element gel¨oscht, . . .
8059
88
94
85 75
97
89
83
40 65
(b) . . . die Unterb ¨aume dem
Fibonacci-Heap hinzugef¨ugt, . . .
0: 1:
ordTab
8059
88
94
85 75
97
89
83
40 65
(c) . . . dann die einzelnen
Fibonacci-B¨aume geordnet nach
ihrem jeweiligen Rang in ein
dict-Objekt ordTab gespeichert,
. . .
0: 1:
ordTab
59
88
80
94
85 75
97
89
83
65 40
(d) . . . und dabei B¨aume gleicher
Ordnung verschmolzen; bei Un-
tersuchung des dritten Baumes
(der die Ordnung 1 hat) wird – da
ordTab[1] bereits einen Eintrag
besitzt – erkannt, dass es schon
einen Baum dieser Ordnung gibt,
. . .
ordTab
0: 2:
80 59
88
94
85
75
97
89
83
40 65
(e) . . . und diese beiden B ¨aume
werden miteinander verschmol-
zen, wodurch ein Fibonacci-Baum
der Ordnung 2 entsteht.
ordTab
0: 3:
80 59
88
94
85 75
97
65 40
89
83
(f) Auch der als N¨achstes zu un-
tersuchende Baum der Ordnung
zwei wird mit dem bereits in
ordTab existierenden (im letzten
Schritt entstandenen) Baum der
Ordnung 2 verschmolzen; es ent-
steht ein Baum der Ordnung 3.
ordTab
1: 3:
59
88
94
85 75
97
65 40
89
80
83
(g) Der als N ¨achstes zu untersu-
chende Baum der Ordnung null
wird mit dem bereits in ordTab
beﬁndlichen Baum der Ordnung
null zu einem Baum der Ordnung
eins verschmolzen.
ordTab
1: 3: 0:
59
88
94
85 75
97
65 40
89
80
83
(h) Schließlich beﬁnden sich
nur noch drei Fibonacci-B ¨aume
unterschiedlicher Ordnung im
Fibonacci-Heap.
Abb. 4.7: Extraktion des Minimums eines Fibonacci-Heaps. Im Zuge dieser Operation wer-
den auch Restrukturierungsmaßnahmen durchgef ¨uhrt und Fibonacci-B ¨aume gleicher Ordnung
zusammengef¨ugt.

## Seite 150

4.3 Fibonacci Heaps 135
Das minimale Element wird in Zeile 2 in der Variablen m gespeichert und am Ende
in Zeile 15 zur ¨uckgeliefert. In der Variablen newsubtrees werden die Unterb ¨aume des
minimalen Elements gespeichert; in Zeile 4 wird der komplette Baum, der das minimale
Element enth¨alt, aus der Liste der Fibonacci-B ¨aume des Fibonacci-Heaps fh gel¨oscht.
Die for-Schleife ab Zeile 6 durchl¨auft nun alle Fibonacci-B¨aume (inklusive der durch die
L¨oschung hinzugekommenen). Die Variable o enth¨alt immer die Ordnung des Baumes
der gerade bearbeitet wird. Gibt es bereits einen Eintrag ”o“ in ordTab (d. h. gibt es
unter den bisher untersuchten B¨aumen bereits einen Fibonacci-Baum t der Ordnung o),
so wird dieser mit dem aktuellen Baum verschmolzen (diese Verschmelzung wird in Zeile
9 durchgef¨uhrt) und der Eintrag ”o“ aus ordTab gel¨oscht. Durch diese Verschmelzung
entsteht ein Fibonacci-Baum der Ordnung o +1; o wird entsprechend um Eins erh ¨oht.
Die while-Schleife ab Zeile 8 pr¨uft nun, ob es auch schon einen Baum der Ordnung o +1
in ordTab gibt, usw. Die while-Schleife bricht erst dann ab, wenn es keinen Eintrag ”o“
in ordTabmehr gibt. Dann wird der aktuelle Fibonacci-Baum t in ordTab[o] gespeichert
und mit dem n ¨achsten Baum fortgefahren.
Nach Abbruch der for-Schleife haben die in ordTab gespeicherten Fibonacci-B¨aume (al-
so ordTab.values()) alle unterschiedliche Ordnung; es sind genau die”neuen“ Fibonacci-
B¨aume, aus denen der Fibonacci-Heap nach Extraktion des minimalen Elements beste-
hen soll. Jetzt muss nur noch der Zeiger auf das minimale Element ggf. angepasst werden
– dies geschieht in Zeile 14.
Aufgabe 4.16
Implementieren Sie die in Zeile 9 in Listing 4.10 ben ¨otigte Funktion mergeFT, die
zwei Fibonacci-B¨aume ft1 und ft2 so verschmilzt, dass die Heap-Bedingung erhalten
bleibt.
Amortisierte Laufzeit. Sei Ord(n) der maximale Grad eines Fibonacci-Baums in ei-
nem Fibonacci-Heap mit insgesamt n Knoten; nach L ¨oschen des minimalen Elements
werden dem Fibonacci-Heap also O(Ord(n)) Fibonacci-B ¨aume hinzugef ¨ugt. In Ab-
schnitt 4.3.8 zeigen wir, dass Ord(n) = O(log n). Die einfache Laufzeit der in Listing
4.10 gezeigten Implementierung h ¨angt entscheidend ab von der Anzahl der Schleifen-
durchl¨aufe der for-Schleife ab Zeile 6; diese wird t(fh) + O(Ord(n)) mal durchlaufen.
Innerhalb der for-Schleife werden Fibonacci-B¨aume verschmolzen; aber auch hier gibt
es h¨ochstens O(t(fh)) + O(Ord(n)) Verschmelzungsoperationen. Somit ist die einfache
Laufzeit in O(t(fh)) + O(Ord(n)).
Am Ende der Verschmelzungsphase gibt esO(log n) Fibonacci-B¨aume (denn jeder Baum
hat eine unterschiedliche Ordnung). An den Knotenmarkierungen ¨andert sich nichts. Es
gilt also ∆Φ = t(fh) −O(log n). Insgesamt erhalten wir also eine amortisierte Laufzeit
von
O(t(fh)) + O(Ord(n)) −(t(fh) −O(log n)) = O(Ord(n)) + O(log n) = O(log n)

## Seite 151

136 4 Heaps
4.3.7 Erniedrigen eines Schl ¨usselwertes
Das Erniedrigen eines Schl ¨usselwertes ist vor allem deshalb eine wichtige Operation,
weil man dar¨uber in der Lage ist, einen Knoten aus einem Fibonacci-Heap zu l ¨oschen.
Man braucht den Schl ¨usselwert eines Knotens lediglich auf −∞zu erniedrigen und
anschließend den Knoten mit minimalem Schl ¨ussel mittels der minExtract-Funktion
aus Listing 4.10 aus dem Heap zu entfernen.
Jeder Knoten muss einen Zeiger auf seinen Elternknoten mitf ¨uhren; nur so kann ¨uber-
pr¨uft werden, ob durch das Erniedrigen die Heap-Bedingung verletzt wird und nur so
k¨onnen die im Folgenden beschriebenen Operationen durchgef ¨uhrt werden. Wir erwei-
tern hierf¨ur die Repr ¨asentation eines Fibonacci-Baums um einen Eintrag ”parentFT“,
der auf den Elternknoten eines Fibonacci-Teilbaums zeigt. Wir k ¨onnen uns also ab
sofort einen Fibonacci-Baum (schemahaft) wie folgt deﬁniert denken:
ﬁbonacciTree = {rootFT : x , subtreesFT : [ ft0 , ft2 , ... ] ,
markedFT : b , parentFT : ft
}
Bei allen Operationen auf Fibonacci-Heaps muss man sicherstellen, dass die
”Vorw¨arts“verzeigerung mittels subtreesFT mit der ”R¨uckw¨arts“verzeigerung mittels
parentFT ¨ubereinstimmt, dass also immer ft in ft [parentFT][subtreesFT] gilt.
Aufgabe 4.17
Schreiben Sie eine Python-FunktionisConsistent(fh), die ¨uberpr¨uft, ob die Vorw¨arts-
und R¨uckw¨artsverzeigerung in allen B¨aumen eines Fibonacci-Heaps fh konsistent ist.
Angenommen, wir wollen den Schl ¨usselwert der Wurzel eines Teilbaums ft eines Fi-
bonacci-Heaps erniedrigen. Wird dadurch die Heap-Bedingung nicht verletzt, d. h. gilt
weiterhin, dass ft [parentFT][rootFT]< ft[rootFT], so ist nichts weiter zu tun – ein
Beispiel einer solchen Situation ist in Abbildung 4.8 dargestellt.
minFH
ft
80 75
3059
88
40
99
65
94
85
89
8387
Abb. 4.8: Die Min-Heap-Bedingung wird durch das Erniedrigen des Schl¨usselwertes der Wur-
zel des Teilbaums ft (von 97 auf 87) nicht verletzt; in diesem Fall ist nichts weiter zu tun.
Wird die Min-Heap-Bedingung durch Erniedrigen des Schl ¨usselwertes der Wurzel von
ft verletzt, gilt also ft [parentFT][rootFT]> ft[rootFT] dann muss der Fibonacci-Heap

## Seite 152

4.3 Fibonacci Heaps 137
so modiﬁziert werden, dass die Min-Heap-Bedingung wiederhergestellt wird. Es sind
zwei F¨alle zu unterscheiden:
Fall 1: Der Elternknoten von ft ist nicht markiert. Abbildung 4.9 zeigt ein Beispiel
einer solchen Situation.
In diesem Fall wird der Teilbaum ft einfach vom Elternkoten getrennt, der
Elternknoten markiert und anschließend ft an Liste der Fibonacci-B ¨aume des
Fibonacci-Heaps angeh¨angt. Ist ft [rootFT] kleiner als das bisher minimale Ele-
ment, so muss der fh [minFH] angepasst werden.
Fall 2: Der Elternknoten von ft ist bereits markiert, d. h. es gilt ft [parentFT][markedFT ].
Abbildung 4.10 zeigt ein Beispiel einer solchen Situation.
In diesem Fall wird der Teilbaum ft ebenfalls vom Elternknoten ft [parentFT]
getrennt und an die Liste der Fibonacci-B ¨aume des Fibonacci-Heaps angef ¨ugt.
Anschließend wird auch der Elternknoten ft [parentFT] von seinem Elternkno-
ten getrennt und an die Liste der Fibonacci-B ¨aume des Fibonacci-Heaps hin-
zugef¨ugt. Ist der Elternknoten des Elternknotens nicht markiert – d. h. gilt
ft [parentFT][parentFT][markedFT ] – so wird dieser markiert. Ist auch dieser
bereits markiert, so wird auch der Elternknoten des Elternknotens von dessen
Elternknoten getrennt, usw..
Listing 4.11 zeigt eine Implementierung der Erniedrigung eines Schl¨usselwertes um delta
eines durch pos speziﬁzierten Knotens eines Fibonacci-Heaps fh. Die Positionsangabe
pos ist ein Tupel. Die erste Komponente, also pos[0] speziﬁziert den Fibonacci-Baum
des Fibonacci-Heaps fh, in dem sich der zu erniedrigende Knoten beﬁndet. Die zweite
Komponente, also pos[1] enth¨alt eine Liste von Zahlen, die einen von der Wurzel begin-
nenden Pfad speziﬁzieren. Die Liste ”[ ]“ (also der leere Pfad) beispielsweise speziﬁziert
die Wurzel des Fibonacci-Baums. Die Liste ”[1,0,2 ]“ beispielsweise speziﬁziert von der
Wurzel ausgehend den 1-ten Teilbaum, davon den 0-ten Teilbaum und davon wieder-
um den 2-ten Teilbaum, also ft [subtreesFT][1][ subtreesFT][0][ subtreesFT][1], wobei
ft der pos[0]-te Teilbaum des Fibonacci-Heaps fh sei. Genau genommen speziﬁziert pos
einen Teilbaum, der sich nach Ausf¨uhrung der for-Schleife in Zeile 4 in der Variablen ft
beﬁndet. In Zeile 6 wird die Wurzel dieses Teilbaums, also ft [rootFT] und den Betrag
delta erniedrigt.
Die Struktur des Fibonacci-Heaps muss nun genau dann angepasst werden, wenn die
Heap-Bedingung durch dieses Erniedrigen verletzt wird; dies pr ¨uft die if-Abfrage in
Zeile 7.
Muss die Struktur angepasst werden, so h ¨angt die ”while True“-Schleife ab Zeile 8
solange den Knoten, den Elternknoten, den Eltern-Elternknoten usw. vom aktuellen
Baum ab und f ¨ugt diesen Knoten als weiteren Fibonacci-Baum in fh [treesFH] ein, bis
entweder ein nicht-markierter Knoten gefunden wird – dieser Fall wird in Zeile 21 und
22 abgehandelt, oder bis ein Wurzelknoten erreicht wird – dieser Fall wird in Zeile 11
und 12 abgehandelt.
Das Aush¨angen eines Teilbaums ft geschieht folgendermaßen: Zun¨achst wird eine even-
tuelle Markierung von ft gel¨oscht (Zeile 14), da ft zu einem neuen Baum des Fibonacci-
Heaps gemacht wird und die Wurzeln der B ¨aume grunds ¨atzlich nicht markiert sein

## Seite 153

138 4 Heaps
minFH
ft
80 75
3059
88
40
99
65
94
85
89
8327
(a) Der Schl¨usselwert an der Wurzel des Teil-
baums ft wird von 97 auf 27 erniedrigt. Da-
durch wird die Min-Heap-Bedingung verletzt.
Diese muss wiederhergestellt werden.
minFH
80
3059
88
99
65 40
94
85
89
83
75
27
(b) Da der Elternknoten (mit Schl ¨usselwert
75) nicht markiert ist, kann der Teilbaum ft
einfach vom Elternknoten getrennt werden.
Der Elternknoten wird danach markiert.
minFH
80
3059
88 99
65 40 27
94
85
89
83
75
(c) Der abgetrennte Teilbaum ft wird nun einfach an die Teilbaumliste des
Fibonacci-Heaps angef ¨ugt. Der Zeiger auf das minimale Element muss danach
nach einem Vergleich mit dem bisherigen Minimum getMinFH(fh) ggf. angepasst
werden.
Abb. 4.9: Erniedrigen eines Schl ¨usselwertes, das die Min-Heap-Bedingung verletzt. Es han-
delt sich hier um den einfacheren Fall: Der Elternknoten des Knotens, dessen Schl ¨usselwert
erniedrigt werden soll, ist nicht markiert.
d¨urfen. In Zeile 15 wird der R¨uckw¨artszeiger von ft gel¨oscht, in Zeile 16 wird ft aus der
Liste der Teilb ¨aume seines Elternknotens gel ¨oscht. In Zeile 17 wird ft der Baumliste
der Fibonacci-Heaps hinzugef¨ugt. In Zeile 19 wird (falls erforderlich) der Zeiger auf den
Baum angepasst, der das minimale Element des Fibonacci-Heaps enth ¨alt.
Es gibt noch einen Sonderfall, der nicht vergessen werden darf: Soll der Schl¨usselwert der
Wurzel eines Fibonacci-Baums erniedrigt werden, gilt also pos[1]==[], und ist dieser
neue Schl¨usselwert kleiner als das bisherige Minimum, so muss der Zeiger fh [minFH]
angepasst werden.
Aufgabe 4.18
Erstellen Sie eine Funktion allPaths(fh), die die Liste aller g ¨ultigen Pfade eines
Fibonacci-Heaps erzeugt – und zwar so, dass jeder dieser Pfade als m ¨oglicher zweiter
Parameter der in Listing 4.11 gezeigten Funktion decKey dienen k¨onnte.

## Seite 154

4.3 Fibonacci Heaps 139
minFH
ft
80
3059
88
40
88
99
94
85 75
83
71
27
(a) Durch Erniedrigen von ft [rootFT] wird
die Heap-Bedingung verletzt.
minFH
80
3059
88
40
88
99
27
94
85 75
83
71
(b) Der Teilbaum wird vom Elternknoten ge-
trennt und der Liste der Fibonacci-B¨aume hin-
zugef¨ugt.
minFH
80
3059
88
40
88
99
27
94
85 75
8371
(c) Da der Elternknoten (mit Schl ¨usselwert
83) markiert ist, wird auch dieser von sei-
nem Elternknoten getrennt und der Liste der
Fibonacci-B¨aume hinzugef¨ugt.
minFH
80
3059
88
88
40
99
27
94
85
758371
(d) Auch dessen Elternknoten (mit Schl¨ussel-
wert 75) ist markiert und darum wird auch
dieser von seinem Elternknoten getrennt und
der Liste der Fibonacci-B ¨aume hinzugef¨ugt.
Abb. 4.10: Erniedrigen eines Schl ¨usselwertes, das die Min-Heap-Bedingung verletzt. Der
Elternknoten des Knotens, dessen Schl ¨usselwert erniedrigt werden soll. ist bereits markiert.
Aufgabe 4.19
Verwenden Sie die eben implementierte FunktionallPaths, um ein zuf¨allig ausgew¨ahl-
tes Element eines Fibonacci-Heaps um einen bestimmten Betrag zu erniedrigen – dies
ist etwa zu Testzwecken hilfreich; auch der am Anfang dieses Abschnitts gezeigte
Fibonacci-Heap wurde (neben zuf ¨alligen Einf¨ugeoperationen und Minimumsextrak-
tionen) so erzeugt.
Amortisierte Laufzeit. Angenommen fh sei der Fibonacci-Heap vor Erniedrigung
des Schl¨usselwerts und fh′ der Fibonacci-Heap nach Erniedrigung des Schl ¨usselwerts.
Nehmen wir an, die while-Schleife in Listing 4.11 (ab Zeile 8) wird c mal durchlaufen,
d. h. es werden c Knoten von ihren jeweiligen Elternknoten getrennt. Dann gilt, dass
 t(fh′) = t(fh) +cdenn jeder der cKnoten wird an die Liste der Fibonacci-B ¨aume
von fh angeh¨angt.
 m(fh′) = m(fh) −(c−2) denn die Markierung jedes Knotens der von seinem
Elternknoten getrennt wird, wird gel¨oscht – denn dieser Knoten wird ja zur Wurzel
eines Fibonacci-Baums und alle Wurzeln m ¨ussen grunds¨atzlich unmarkiert sein.
Auf diese Weise wird die Markierung von c−1 gel¨oscht. Der Elternknoten des

## Seite 155

140 4 Heaps
1 def decKey(fh,pos,delta ):
2 # pos = (x,[x0,x1,x2, ...])
3 ft = fh[treesFH][pos [0]]
4 for x in pos[1]:
5 ft = ft [subtreesFT][x ]
6 ft [rootFT] -= delta
7 if ft [parentFT] and ft[parentFT][rootFT] > ft[rootFT]:
8 while True:
9 ftParent = ft [parentFT]
10 if not ftParent: # ft ist Wurzel
11 ft [markedFT] = False
12 break
13 else:
14 ft [markedFT] = False
15 ft [parentFT] = None # ft trennen
16 ftParent[subtreesFT].remove(ft)
17 fh [treesFH].append(ft) # ... ft wird neue Wurzel
18 if ft [rootFT]<getMinFH(fh):
19 fh [minFH] = len(fh[treesFH]) -1
20 if not ftParent[markedFT]:
21 if ftParent[parentFT]̸=None: ftParent[markedFT] = True
22 break
23 ft = ftParent # weiter mit Elternknoten
24 elif ft [rootFT]<getMinFH(fh): fh[minFH] = pos[0]
Listing 4.11:Implementierung der Erniedrigung des Schl¨usselwertes an der Wurzel des (Teil)-
Fibonacci-Baums.
zuletzt getrennten Knotens wird markiert und darum ver ¨andert sich die Zahl der
markierten Knoten um c−2.
Somit ergibt sich folgende Potenzialver¨anderung:
∆Φ = t(fh) + 2·m(fh) −(t(fh) + c+ 2(m(fh) −(c−2)))
= 4 −c
Insgesamt ergibt sich also eine amortisierte Laufzeit von
O(c) + 4−c= O(1)
An diesem Punkt sehen wir klarer, warum die Anzahl der markierten Knoten in der
Potenzialfunktion mit dem Faktor ”2“ auftaucht.
 Der eine markierte Knoten verrechnet sich mit dem Trennen des Knotens von
seinem Elternknoten und dem nachfolgenden L ¨oschen der Markierung.

## Seite 156

4.3 Fibonacci Heaps 141
 Der andere markierte Knoten verrechnet sich mit dem Potenzialanstieg aufgrund
des zus¨atzlich eingef¨ugten Fibonacci-Baums.
Aufgabe 4.20
Die in Zeile 18 in Listing 4.11 durchgef ¨uhrt ¨Uberpr¨ufung, ob ft [rootFT] kleiner ist
als das bisherige Minimum des Fibonacci-Heaps braucht eigentlich nicht in jedem
Durchlauf der ¨außeren while-Schleife durchgef¨uhrt werden. Passen Sie die in Listing
4.11 gezeigte Implementierung so an, dass diese ¨Uberpr¨ufung nur einmal stattﬁndet.
4.3.8 Maximale Ordnung eines Fibonacci-Baums
Woher Fibonacci-Heaps ihren Namen haben, sehen wir in diesem Abschnitt. Es bleibt
noch zu zeigen, dass die maximale Ordnung – im Folgenden als Ord(n) bezeichnet –
eines in einem n-elementigen Fibonacci-Heap beﬁndlichen Fibonacci-Baums in O(log n)
ist. Wir werden im Speziellen zeigen, dass gilt:
Ord(N) ≤logφn, mit φ= 1 +
√
5
2
Wir bezeichnen als s(ft ) die Anzahl der im Fibonacci-Baum ft beﬁndlichen Elemente.
Sei o die Ordnung dieses Fibonacci-Baums – also o= len( ft [subtreesFT]). Wir zeigen,
dass
s(ft ) ≥Fo+2
gelten muss. Hierbei ist Fk ist die k-te Fibonacci-Zahl1. Um diese Aussage zu zeigen,
verwenden wir vollst¨andige Induktion2 ¨uber die H¨ohe h von ft :
h= 0 : In diesem Fall ist s(ft ) = 1 ≥F2.
<h →h: Wir nehmen also an, ft besitzt eine H ¨ohe h> 0 und muss damit eine Ord-
nung o >0 haben. Seien ft 0,ft 1,..., ft o−1 die Teilb¨aume von ft , geordnet nach
dem Zeitpunkt zu dem diese ft hinzugef¨ugt wurden. Sei oi = len( ft i[subtreesFT])
– d. h. oi ist die Ordnung von ft i. Man kann zeigen, dass oi ≥i−1:
Z. z. oi ≥i−1 : Als ft i zu ft hinzugef¨ugt wurde, waren also ft 0,..., ft i−1 be-
reits Teilb¨aume von ft und ft hatte somit eine Ordnung voni. Da B¨aume nur
dann verschmolzen werden, wenn sie gleiche Ordnung besitzen, mussft i auch
eine Ordnung von igehabt haben. Seit dem Zeitpunkt dieser Verschmelzung
wurde h¨ochstens ein Teilbaum von ft i entfernt (aufgrund der Handhabung
von Markierungen ist es nicht m ¨oglich, mehr als einen Teilbaum zu entfer-
nen); die momentane Ordnung von ft i ist also ≥i−1.
1Siehe auch Anhang B.2 auf Seite 307
2Siehe auch Anhang B.1.4 auf Seite 306

## Seite 157

142 4 Heaps
Da die H¨ohen der ft i kleiner sind als die H ¨ohe hvon ft , k¨onnen wir auf diese die
Induktionshypothese anwenden und annehmen, dass s(ft i) ≥Foi+2 = Fi+1. Der
Induktionsschritt l¨asst sich dann folgendermaßen zeigen:
s(ft ) =
Wurzel von ft

1 + s(ft 0) + s(ft 1) + ... + s(ft o−1)
≥ 1 + Fo0+2 + Fo1+2 + ... + Foo−1+2
= 1 + F1 + F2 + ... + Fo
Satz 2= Fo+2
Nach Satz 3 (aus Anhang B.2) gilt, dass Fo+2 ≥ϕo und damit s(ft ) ≥ϕo, wobei
– wir erinnern uns – o die maximale Ordnung eines Knotens in ft bezeichnet.
Aufgel¨ost nach o gilt somit
o≤logϕs(ft )
oder anders ausgedr ¨uckt
Ord(n) ≤logϕ(n)
wobei Ord(n) die maximale Ordnung eines Fibonacci-Baums mit n Elementen
bezeichnet.
4.4 Pairing-Heaps
183
226 286 241 190 187 184 210 354
274 366 234 263 197 247 276 204 207 235 193 383 208 203 277 199 213 186 280 291
360 322 347 358 249 329 220 269 349 298 377 315 353 215 308 281 278 257 217
351 290 254 337 397
345
388 230 243 320 295 317 282 359 266 385 381 297 236 348 307
390 376 395
304 363 380 268 262
391 272 270
370 399 211 212 244 223 287 246 285 293 191 202
324 303 362 327 336 356 261 283 219 221 264 250 216 301
398 331 273
346 321
311 306 386 231 340 350 375
372 252
334
382 368 394
Pairing-Heaps wurden urspr¨unglich von Tarjan, Fredman, Sedgewick und Sleator [8] als
eine einfachere Variante von Fibonacci-Heaps vorgeschlagen. Sie sind einfacher zu imple-
mentieren als Binomial-Heaps und Fibonacci-Heaps. Noch dazu zeigen Pairing-Heaps in
den meisten praktischen Anwendungen eine hervorragende Performance. Experimente
zeigen, dass Pairing Heaps etwa verwendet in Prim’s Algorithmus zur Berechnung des
minimalen Spannbaums, tats¨achlich schneller zu sein scheinen, als alle anderen bekann-
ten Alternativen. Trotz ihrer einfachen Funktionsweise stellt sich eine Laufzeitanalyse
als ¨außert schwierig heraus: Bis heute ist eine abschließende Laufzeitanalyse noch ein
oﬀenes Problem der Informatik.
4.4.1 Struktur und Repr ¨asentation in Python
Ein Pairing-Heap ist entweder leer oder besteht aus einem Wurzelelement zusammen mit
einer Liste von Teilb ¨aumen; jeder Knoten muss zus ¨atzlich die (Min-)Heap-Bedingung
erf¨ullen, d. h. sein Schl¨usselwert muss kleiner sein als die Schl¨usselwerte seiner Teilb¨aume.

## Seite 158

4.4 Pairing-Heaps 143
Eine solche Struktur kann in Python am einfachsten als Tupel repr ¨asentiert werden3.
Der folgende Python-Ausdruck repr¨asentiert hierbei etwa
den rechts davon abgebildeten Pairing-Heap.
(14, [(28, [ ] ), \
(43, [(67, [ ] ),(77, [ ]) ] ),\
(21, [(87, [ ] ),(54, [ ]) ]))
14
43 2128
67 77 87 54
Zus¨atzlich gehen wir im Folgenden davon aus, dass ein leerer Heap durch den Wert
None repr¨asentiert ist.
F¨ur die Lesbarkeit der in diesem Abschnitt pr ¨asentierten Algorithmen ist es g ¨unstig,
wenn wir deﬁnieren:
rootPH, subtreesPH = 0,1
Um auf das Wurzelelement eines Pairing-Heapsph zuzugreifen, schreiben wir im Folgen-
den statt ph[0] der Lesbarkeit halber besser ph[rootPH]. Um auf die Liste der Teilb¨aume
zuzugreifen, schreiben wir im Folgenden statt ph[1] besser ph[subtreesPH].
Aufgabe 4.21
Schreiben Sie eine Funktion ph2str, die einen Pairing-Heap als Argument ¨ubergeben
bekommt und eine gut lesbare String-Repr ¨asentation dieses Pairing-Heaps zur ¨uck-
liefert. Die String-Repr ¨asentation des Pairing-Heaps aus Abbildung 4.11(a) sollte
hierbei beispielsweise folgende Form haben:
'26-[48-49-[99,95],74,50-61,73,31-[39,69]]'
Die Teilbaumlisten sollten also – vorausgesetzt sie bestehen aus mehr als einem Baum
– in eckige Klammern eingeschlossen werden; das Wurzelelement sollte mit einem'-'
von seiner Teilbaumliste getrennt sein.
4.4.2 Einfache Operationen auf Pairing-Heaps
Die Implementierung der meisten Operationen auf Pairing-Heaps ist sehr simpel, ins-
besondere verglichen mit der Implementierung der entsprechenden Operationen auf
Binomial-Heaps oder Fibonacci-Heaps und sogar auf bin ¨aren Heaps.
Zun¨achst beﬁndet sich das minimale Element immer an der Wurzel des Pairing-Heaps.
Entsprechend einfach ist die Implementierung der getMin-Funktion auf Pairing-Heaps:
1 def getMin(ph):
2 if ph: return ph[rootPH]
Durch die if-Abfrage wird hier sichergestellt, dass kein Laufzeitfehler entsteht, wenn
getMin auf einen leeren Heap angewendet wird.
3Selbstverst¨andlich ist auch eine Repr ¨asentation ¨uber eine Klasse m ¨oglich; siehe Aufgabe 4.23.

## Seite 159

144 4 Heaps
Zwei Pairing-Heaps werden verschmolzen, indem einfach der Heap mit dem gr ¨oßeren
Wurzelelement als neuer Teilbaum unter den Heap mit dem kleineren Wurzelelement
geh¨angt wird. Listing 4.12 zeigt eine Implementierung der Verschmelzungsoperation.
1 def merge(ph1,ph2):
2 if not ph1: return ph2
3 if not ph2: return ph1
4 if ph1<ph2:
5 return (ph1[rootPH], ph1[subtreesPH] + [ph2])
6 else:
7 return (ph2[rootPH], ph2[subtreesPH] + [ph1])
Listing 4.12: Verschmelzung zweier Pairing-Heaps
Aufgabe 4.22
Die oben gezeigte Implementierung der merge-Operation ist nicht-destruktiv imple-
mentiert: Die ¨ubergebenen Parameterwerte werden (durch Zuweisungen bzw. de-
struktive Listenoperationen) nicht ver¨andert; als R¨uckgabewert wird eine neuer Pai-
ring-Heap konstruiert.
Erstellen Sie nun eine destruktive Implementierung, in dem der ph1-Parameter de-
struktiv so ver ¨andert wird, dass er nach Ausf ¨uhrung der Funktion das gew ¨unschte
Ergebnis enth¨alt. Erkl¨aren Sie, warum und wie sie die oben beschriebene Repr ¨asen-
tation von Pairing-Heaps hierf¨ur anpassen m¨ussen.
4.4.3 Extraktion des Minimums
Tats¨achlich stellt die Extraktion des Minimums die einzige nicht-triviale Operation
auf Pairing-Heaps dar. Durch das L ¨oschen des Wurzelelements ph[rootPH] entstehen
len(ph[subtreesPH]) ”freie“ B¨aume. Es gibt mehrere sinnvolle M¨oglichkeiten, in welcher
Weise diese B¨aume wieder zu einem Pairing-Heap zusammengef¨ugt werden. Eine h¨auﬁg
verwendete M¨oglichkeit wollen wir hier vorstellen: das paarweise Verschmelzen der”frei-
en“ B¨aume von links nach rechts inph[subtreesPH] und das anschließende Verschmelzen
der so entstandenen B¨aume von rechts nach links.
Listing 4.13 zeigt eine funktionale (d. h. nicht-destruktive) Implementierung der Mini-
mumsextraktion. Die FunktionextractMinND ver¨andert also ihr Argumentph nicht son-
dern konstruiert stattdessen mittels der Funktion pairmerge einen neuen Pairing-Heap
der durch Extraktion des minimalen Elements entsteht und liefert diesen als Ergebnis
zur¨uck. Die Funktion extractMinND liefert also ein Tupel zur ¨uck dessen erste Kompo-
nente das minimale Element ist und dessen zweite Komponente der neue Pairing-Heap
ist der durch L¨oschen des minimalen Elements entsteht.
Die erste if-Abfrage in Zeile 2 deckt den einfachsten Fall ab: Ein leerer Heap liefert das
Tupel (None,None) zur¨uck, gibt also kein minimales Element zur¨uck und liefert wieder-
um den leeren Heap. Zeile 3 behandelt einen weiteren Sonderfall, den einelementigen

## Seite 160

4.4 Pairing-Heaps 145
1 def extractMinND(ph):
2 if not ph: return (None,None)
3 if not ph[subtreesPH]: return ph[rootPH], None
4 return ph[rootPH],pairmerge(ph[subtreesPH])
5
6 def pairmerge(phs):
7 if len(phs)==0: return None
8 if len(phs)==1: return phs[0]
9 return merge(merge(phs[0],phs[1]),pairmerge(phs[2:]))
Listing 4.13: Implementierung der Minimums-Extraktion.
Heap. Hier wird der Wert an der Wurzel (also ph[rootPH]) und der leere Heap zur ¨uck-
geliefert. Andernfalls werden die Teilb ¨aume von ph mittels der Funktion pairmerge zu
einem neuen Heap verschmolzen.
Die Implementierung von pairmerge ist rekursiv, rein funktional (d. h. verwendet keine
Zuweisungen) und erstaunlich einfach. Besteht die der Funktion pairmerge ¨ubergebene
Liste von Pairing-Heaps phs aus nur einem Baum, so wird dieser eine Baum einfach
zur¨uckgeliefert – dies ist der Rekursionsabbruch. Andernfalls werden die ersten bei-
den Pairing-Heaps phs[0] und phs[1] verschmolzen und der resultierende Pairing-Heap
mit dem mittels pairmerge auf den restlichen Pairing-Heaps erstellten Heap verschmol-
zen. Der rekursive Abstieg f¨uhrt die paarweisen Verschmelzungen von links nach rechts
durch. Der darauf folgende rekursive Aufstieg f¨uhrt die abschließenden Verschmelzungen
von rechts nach links durch.
Abbildung 4.11 veranschaulicht den Ablauf einer Minimumsextraktion anhand eines
Beispiel-Heaps. Man kann zeigen, dass die Minimums-Extraktion O(log n) Schritte
ben¨otigt; die Herleitung dieser Tatsache ist jedoch nicht trivial, und wir verzichten
hier auf eine entsprechende Darstellung.
Aufgabe 4.23
Repr¨asentieren Sie einen Pairing-Heap durch eine KlassePairingHeap und implemen-
tieren Sie die beschriebenen Funktion als Methoden dieser Klasse.

## Seite 161

146 4 Heaps
50 73
61
26
74 48
49
99 95
31
69 39
(a)
48
49
99 95
74 50
61
31
69 39
73
(b)
50
61
73
49
99 95
48 31
69 3974
(c)
50
61 73
31
39 69
48
49
99 95
74
(d)
31
69 39 50
61 7399 95
48
74 49
(e)
31
39 50
61 73
69
74 49
99 95
48
(f)
Abb. 4.11: Darstellung der Funktionsweise der Minimumsextraktion anhand eines Beispiel-
Heaps. Nach L ¨oschen des Wurzelelements (Abbildung 4.11(a)) entstehen im Beispiel 5 lo-
se B ¨aume; diese werden zun ¨achst paarweise von links nach rechts verschmolzen (Abbildun-
gen 4.11(b) und 4.11(c)) und anschließend die so entstandenen B ¨aume von rechts nach
links verschmolzen (Abbildungen 4.11(d) und 4.11(e)). Aufgrund der Funktionsweise der
Verschmelzungs-Operation erf¨ullen die Knoten des so entstandenen Baums (siehe Abbildung
4.11(f)) wieder die Min-Heap-Bedingung.

## Seite 162

5 Graphalgorithmen
Wir lernen in diesem Abschnitt . . .
 . . . was Graphen sind und wozu man sie braucht (Abschnitt 5.1.1).
 . . . wie man Graphen in einer Programmiersprache repr¨asentiert (Abschnitt 5.1.2).
 . . . wie man einen Graphen systematisch durchlaufen kann (Abschnitt 5.2).
 . . . wie man den k¨urzesten Weg zwischen zwei (oder mehreren) Knoten berechnet
(Abschnitt 5.3).
 . . . wie man einen minimalen Spannbaum – eine Art ”kosteng¨unstigsten“ Verbin-
dungsgraphen – berechnet (Abschnitt 5.4).
 . . . wie man einen maximal m¨oglichen (Waren-)Fluss in einem Netzwerk aus Kno-
ten und Flusskapazit¨aten berechnet (Abschnitt 5.5).
Voraussetzung f¨ur das Verst ¨andnis der in diesem Kapitel vorstellten Algorithmen ist
die Kenntnis der grundlegenden mathematischen Konzepte die der Graphentheorie zu-
grunde liegen. Anhang B.4 liefert den notwendigen ¨Uberblick.
5.1 Grundlegendes
5.1.1 Wozu Graphen?
Ein Graph ist ein mathematisches Objekt, bestehend aus Knoten und Verbindungen
zwischen Knoten, genannt Kanten. Weitere mathematische Details zu Graphen ﬁnden
sich in Anhang B.4.
Graphen sind in der Informatik das Mittel der Wahl um eine Vielzahl von Ph¨anomenen
der realen Welt zu repr ¨asentieren. Es gibt eine Vielzahl von Beispielen f ¨ur ”Dinge“,
die sich angemessen durch Graphen repr ¨asentieren lassen, etwa ein Straßennetz (Kno-
ten: St¨adte, Kanten: Verbindungen zwischen St ¨adten), Mobilfunkteilnehmer (Knoten:
Handys oder Basisstationen; Kanten: Verbindungen zwischen Handy und Basisstation),
ein Ablaufplan (Knoten: Zustand; Kanten: m ¨oglicher ¨Ubergang von einem Zustand zu
einem anderen) oder das Internet (Knoten: Websites; Kanten: Link einer Website zu
einer anderen) oder Hierarchische Beziehungen (Knoten: Begriﬀe; Kanten: Beziehun-
gen zwischen Begriﬀen wie etwa ”ist ein“), usw. Als Beispiel ist in Abbildung 5.1 ein
Graph zu sehen, der einen Teil des Semantic Web zeigt; in Abbildung 5.2 ist ein kleiner

## Seite 163

148 5 Graphalgorithmen
As of July 2009
Link edCT
Reactome
Tax onom y
KEGG
PubMed
GeneID
Pfam
UniProt
OMIM
PDB
Symbol
ChEBI
Daily 
Med
Disea-
some
CA S
HGNC
Inter
Pro
Drug 
Bank
UniP arc
UniR ef
ProDom
PROSITE
Gene 
Ontology
Homolo
Gene
Pub
Chem
MGI
UniST S
GEO
Species
Jamendo
BBC
Programmes
Music-
brainz
Magna-
tune
BBC
Later +
TOTP
Surge
Radio
MySpace
Wrapper
Audio-
Scrobbler
Linked
MDB
BBC
John
Peel
BBC
Playcount
Data
Gov-
Track
US 
Census 
Data
riese
Geo-
names
lingvoj
World 
Fact-
book
Euro-
stat
flickr
wrappr
Open 
Calais
RevyuSIOC
Sites
Doap-
space
Flickr
exporter
FOAF
profiles
Crunch
Base
Sem-
Web-
Central
Open-
Guides
Wiki-
company
QDOS
Pub 
Guide
RDF 
ohloh
W3C
WordNet
Open
Cyc
UMBEL
Yago
DBpedia
Freebase
Virtuoso 
Sponger
DBLP
Hanno ver
IRIT 
Toulouse
SW
Conference
Corpus
RDF Book 
Mashup
Project 
Guten-
berg
DBLP
Berlin
LAA S- 
CNRS
Buda-
pest
BME
IEEE
IBM
Resex
Pisa
New -
castle
RAE 
2001
CiteSeer
ACM
DBLP 
RKB
Explorer
eprints
LIBRIS
Semantic
Web .org
Eurécom
RKB
ECS 
South-
ampton
CORDIS
ReSIST 
Project
Wiki
National
Science
Foundation
ECS 
South-
ampton
Linked
GeoData
BBC Music
Abb. 5.1: Ein Ausschnitt des sog. Semantic Web, einem Teil des WWW, in dem sich Infor-
mationen beﬁnden ¨uber die Bedeutung verschiedener Begriﬀe und deren Beziehungen unterein-
ander; die Knoten stellen Gruppen von Begriﬀen dar; die Kanten geben an, zwischen welchen
Begriﬀsgruppen Beziehungen bestehen.
adhocracy
pylons
client base64
logging
urllib
urllib2
analyse
os
rewebsetup
migrate
routing
routes
middleware
beaker
paste
environment
mako
sqlalchemy
watch
formencode
datetime
meta
refs
authorization
api
root
proposal
instance_filter
delegateable
poll
user
event
simplejson
tag
math
unicodedata
instance
babel
selection
badge
operator
repoze
search
page
milestone
admin
delegation
comment
message
static
time
lxml
abuse
openidauth
webob
openid
error
cgi
twitteroauth
oauth
hashlib
test_forms
testtools
random
string
test_instance test_poll
test_editor
test_watch
test_user
test_root
test_vote
test_twitteroauth
test_admin
test_search
test_issue
test_delegation
test_auth
test_motion
test_event
test_comment
test_badges
test_instances
test_proposals
test_text
test_decision
test_delegation_node
extra_strings
GPG
StringIO
popen2
types
oauthtwitter
twitter
tally
vote
group
permission
tagging
text
revision
userbadges
update
amqp
collections
json
membership
common
openidstore
cli
microblog
version
pkg_resources
recommendations
pager
templating
rfc822
tiles
auth
sorting
broadcast
queue
mail
email
smtplib
util
uuid
shutil
base
app_globals
memcache
install
watchlist
logo
cache
delegation_helper
page_helpermilestone_helper
text_helper
user_helper
urlwebhelpers selection_helper
site_helper
poll_helper
comment_helper
instance_helper
delegateable_helper
proposal_helper
tag_helper
abuse_helper
instance_auth_tkt
csrf
decorator
norm
variant
authentication
comment_tiles
milestone_tiles
page_tiles
delegateable_tiles
user_tiles
selection_tiles
proposal_tiles
poll_tiles
tag_tiles
delegation_tiles
event_tiles
instance_tiles
text_tiles
decision_tiles
revision_tiles
invalidate
decision
delegation_node
formatting
rss
stats
filters
notification
sources
sinks
diff
itertools
normalize
render
markdown2
discriminator
index
solr
query
httplib2
sunburnt
amqplib
Abb. 5.2: Ein Aussschnitt aus den als Graph modellierten Importbeziehungen eines gr ¨oße-
ren Python-Projektes, des Liquid-Democracy-Tools ”Adhocracy’, modelliert als ungerichteter
Graph.
Saarland
Berlin
Bayern
Thueringen
Sachsen
hamburg
NiedersachsenHessen
Rheinland-Pfalz
Bremen
Mecklenburg-
Vorpommern
Brandenburg
Schleswig-
Holstein
Nordrhein-
Westfalen
Baden-
Wuerttemberg
Sachsen-
Anhalt
Abb. 5.3: Ein Graph der die Nachbarschaftsbeziehung der Bundesl ¨ander modelliert.

## Seite 164

5.1 Grundlegendes 149
Teil der Importbeziehungen der Module eines gr ¨oßeren Softwareprojektes zu sehen; der
Graph aus Abbildung 5.3 zeigt die Nachbarschaftsbeziehung der Bundesl¨ander. Wichtig
ist dabei sich vor Augen zu halten, dass die mathematische Struktur ”Graph“ i. A. von
der r¨aumlichen Anordnung der Knoten abstrahiert, d. h. es spielt keine Rolle, ob ein
Knoten vi links von einem Knoten vj gezeichnet wird oder rechts. Alleine entscheidend
ist nur die Information, welche Knoten miteinander verbunden sind.
5.1.2 Repr ¨asentation von Graphen
Es gibt zwei grunds ¨atzlich verschiedene
M¨oglichkeiten der Darstellung eines Gra-
phen im Rechner; jede hat Ihre Vor- und
Nachteile und man muss sich je nach anzu-
wendendem Algorithmus und je nach”Dich-
te“ des Graphen von Fall zu Fall neu ent-
scheiden, welche der beiden Darstellungsfor-
men man f¨ur die Repr¨asentation eines Gra-
phen G = (V,E ) verwendet, wobei V die
Menge der Knoten und E die Menge der
Kanten darstellt.
1. Darstellung als Adjazenzmatrix:
Der Graph wird in Form einer Matrix Are-
pr¨asentiert, wobei der Eintrag in der i-ten
Zeile und der j-ten Spalte 1 ist, falls es ei-
ne Verbindung von i nach j im Graphen G
gibt; formaler ausgedr¨uckt muss f¨ur die Ad-
jazenzmatrix A= (aij) gelten:
aij =
{
1, falls (i,j) ∈E
0, sonst
Abbildung 5.5 zeigt ein Beispiel.
2. Darstellung als Adjazenzliste:
Der Graph wird als Liste seiner Knoten ge-
speichert. Jeder Eintrag in der Liste zeigt
auf die zum jeweiligen Knoten benachbar-
ten (d. h. adjazenten) Knoten. Abbildung
5.6 zeigt ein Beispiel.
52
3 4
1
Abb. 5.4: Ein einfacher gerichte-
ter Graph.


0 1 1 1 0
0 1 1 0 0
0 0 0 1 0
0 0 0 0 1
1 0 0 0 0


Abb. 5.5: Repr¨asentation des in
Abbildung 5.4 gezeigten Graphen
als Adjazenzmatrix.
{2,3,4}
{2,3}
{4}
{5}
{1}
1
2
3
4
5
Abb. 5.6: Repr¨asentation des in
Abbildung 5.4 gezeigten Graphen
als Adjazenzliste.
Besitzt der Graph relativ ”wenige“ Kanten (im Vergleich zum vollst ¨andigen Graphen
K = (V,V ×V)), so ist die Repr ¨asentation als Adjazenzmatrix sehr verschwenderisch,
was den Speicherbedarf betriﬀt, und die Adjazenzmatrix w ¨are eine sog. d¨unn besetzte
Matrix, d. h. eine Matrix, in der die meisten Eintr ¨age 0 sind. In solchen F ¨allen, insbe-
sondere dann, wenn der Graph viele Knoten hat, empﬁehlt sich die Repr ¨asentation als
Adjazenzliste.
Bestimmte grundlegende Operationen sind je nach Darstellungsform unterschiedlich

## Seite 165

150 5 Graphalgorithmen
aufw¨andig. Der Test, ob eine bestimmte Kante (i,j) im Graphen enthalten ist, braucht
nur O(1) Schritte, wenn der Graph als Adjazenzmatrix repr¨asentiert ist, jedochO(deg(i)),
wenn der Graph als Adjazenzliste gespeichert ist. Andererseits ben ¨otigt das Durchlau-
fen der Nachbarschaft eines Knotens i – eine h ¨auﬁg durchgef¨uhrte Operation bei der
Breiten- und Tiefensuche – nur O(deg(i)) Schritte, wenn der Graph als Adjazenzliste
gespeichert ist, jedoch O(n) Schritte, wenn der Graph als Adjazenzmatrix gespeichert
ist, wobei i. A. deg(i) ≪n gilt.
In Python sind diese Repr ¨asentationen einfach zu ¨ubertragen. Eine Adjazenzmatrix
kann einfach als Liste von Zeilen (die wiederum Listen sind) deﬁniert werden. Eine
Adjazenzliste ist entsprechend eine Liste von Nachbarschaften der jeweiligen Knoten.
Eine ”Nachbarschaft“ kann man nun wiederum als Liste darstellen. Um einen schnelleren
Zugriﬀ auf einen bestimmten Nachbarn zu gew ¨ahrleisten ist es jedoch g ¨unstiger die
Nachbarschaft eines Knotens in einem dict-Objekt zu speichern.
Wir wollen deﬁnieren einen Graphen mittels einer Klasse Graph:
1 class Graph(object):
2 def init ( self ,n):
3 self . vertices = []
4 self .numNodes = n
5 for i in range(0,n +1):
6 self . vertices .append({})
Wir legen uns schon bei der Initialisierung des Graphen auf dessen Gr ¨oße fest und
¨ubergeben der init -Funktion die Anzahl n der Knoten im Graphen. Neben dem
Attribut numNodes, enth¨alt der Graph noch die Adjazenzliste vertices; jeder Eintrag
dieser Adjazenzliste wird zun ¨achst mit einer leeren Knotenmenge {}(in Python durch
ein leeres Dictionary repr ¨asentiert) initialisiert.
Listing 5.1 zeigt die Implementierung der wichtigsten Graphmethoden.
1 class Graph(object):
2 ...
3 def addEdge(self,i , j ,weight=None):
4 self . vertices [i ] [j ] = weight
5 def isEdge(self , i , j ):
6 return j in self . vertices [i ]
7 def G(self, i ):
8 return self. vertices [i ]. keys()
9 def V(self ):
10 return [i for i in range(0, self .numNodes+1)]
11 def E(self ):
12 return [(i,j) for i in self .V() for j in self .G(i)]
Listing 5.1: Implementierung der wichtigsten Graphmethoden.
Die Methode Graph.addEdge(i,j) f¨ugt dem Graphen eine Kante ( i , j) hinzu – optional
mit einem Gewicht weight; die Methode Graph.isEdge(i,j) testet, ob die Kante ( i , j)

## Seite 166

5.1 Grundlegendes 151
im Graphen enthalten ist; die Methode Graph.G(i) liefert die Liste der Nachbarn des
Knotens i zur¨uck. Und schließlich wird die Methode Graph.V() implementiert, die ein-
fach die Liste aller Knoten zur ¨uckliefert und die Methode Graph.E(), die die Liste aller
Kanten des Graphen zur ¨uckliefert.
Um nun etwa den Beispielgraphen in Abbildung 5.7 zu erzeugen, kann man die folgenden
Anweisungen verwenden:
g2 = Graph(11)
for i , j in [ (1,2),(1,4),(1,5),(2,3),(3,6),(6,5),
(6,9),(5,9),(5,8),(8,7),(8,11),(11,10) ]:
g2.addEdge(i,j)
1
2
3
4
6 9
8
7 10
115
Abb. 5.7: Ein Beispielgraph.
Aufgabe 5.1
Erweitern Sie die Klasse Graph um die Methode Graph.w(i,j), die das Gewicht der
Kante ( i , j) zur¨uckliefert (bzw. None, falls die Kante kein Gewicht besitzt).
Aufgabe 5.2
Erweitern Sie die Klasse Graph um die folgenden Methoden:
(a) Eine Methode Graph.isPath(vs), die eine Knotenlistevs ¨ubergeben bekommt und
pr¨uft, ob es sich hierbei um einen Pfad handelt.
(b) Eine Methode Graph.pathVal(vs), die eine Knotenliste vs ¨ubergeben bekommt.
Handelt es sich dabei um einen g ¨ultigen Pfad, so wird der ”Wert“ dieses Pfades
(d. h. die Summe der Gewichte der Kanten des Pfades) zur¨uckgeliefert. Andern-
falls soll der Wert ∞(in Python: ﬂoat ('inf')) zur ¨uckgeliefert werden. Verwen-
den Sie hierbei das folgende ”Ger¨ust“ und f¨ugen Sie an der mit ” ... “ markierten
Stelle die passende Listenkomprehension ein.
def pathVal(self , xs ):
if len(xs)<2: return 0
return sum([... ])

## Seite 167

152 5 Graphalgorithmen
Aufgabe 5.3
Schreiben Sie eine Klasse GraphM, die dieselbe Schnittstelle wie die Klasse Graph
bereitstellt (also ebenfalls Methoden addEdge, isEdge, G, und die einen Graphen als
Adjazenzmatrix implementiert.
5.2 Breiten- und Tiefensuche
4
15
11
56
17
12
19
23
8
7
9
16
13
18
20
14
24
27
10
25
31
26
36
21
30
22
32
41
38
33
34
37
42
47
28
29
46
39
35
43
40
44
50
52
53
45
49
51
55
54
Mit einer Breiten- bzw. Tiefensuche kann man einen Graphen in systematischer Weise
durchlaufen. Viele Algorithmen verwenden als ”Ger¨ust“ eine Breiten- oder Tiefensuche,
wie etwa die in sp ¨ateren Abschnitten behandelte Topologische Sortierung, oder das
Finden von Zyklen in einem Graphen.
Obige Abbildung zeigt eine Tiefensuche durch einen gr¨oßeren Beispielgraphen mit |V|=
60 Knoten.
5.2.1 Breitensuche
Queues
F¨ur die Implementierung einer
Breitensuche empﬁehlt es sich, eine
Warteschlange zu verwenden, auch
im Deutschen oft als eine Queue
bezeichnet. Eine Queue ist eine
Datenstruktur, die ¨uberlicherwei-
se die folgenden Operationen un-
terst¨utzt:
enqueue dequeue
Abb. 5.8: Eine Queue; neue Elemente (bzw. Leu-
te) m¨ussen sich ”hinten“ einreihen; ”vorne“ werden
Elemente entnommen.
1. Das Einf¨ugen enqueue(x) eines Elementes x; 2. das Entfernen dequeue() desjenigen
Elementes, das sich am l ¨angsten in der Queue beﬁndet; 3. einen Test isEmpty() ob die
Queue leer ist. Entscheidend ist die folgende Eigenschaft von Queues: Es wird immer
dasjenige Element als N ¨achstes zur Bearbeitung aus der Queue entfernt, das sich am
l¨angsten in der Queue beﬁndet, das also als erstes in die Queue eingef ¨ugt wurde. Eine
Queue zeigt also das gleiche Verhalten, das jede Warteschlange im allt ¨aglichen Leben
auch zeigen sollte. Da das Element, das zeitlich gesehen als erstes eingef¨ugt wurde auch

## Seite 168

5.2 Breiten- und Tiefensuche 153
als erstes an der Reihe ist, wird eine Queue auch als FIFO (= ﬁrst-in, ﬁrst-out) Da-
tenstruktur bezeichnet. Queues werden etwa bei der Abarbeitung von Druckauftr ¨agen
verwendet, oder auch bei der ”gerechten“ Zuteilung sonstiger Ressourcen, wie Rechen-
zeit, Speicher usw.
Aufgabe 5.4
Implementieren Sie eine Klasse Queue, die die Operationen enqueue(x), dequeue()
und isEmpty unterst¨utzt.
Implementierung der Breitensuche. Eine Breitensuche erh ¨alt als Eingabe einen
Graphen G= (V,E) und einen Startknoten s ∈V. Als Ergebnis der Breitensuche wer-
den die Listen d und pred zur¨uckgeliefert. Nach Ausf ¨uhrung der Breitensuche enth ¨alt
der Eintrag d[i ] den ”Abstand“ des Knotens i vom Startknoten s; der Eintrag pred[i ]
enth¨alt den Vorg¨anger zu Knoten i auf einem Breitensuche-Durchlauf durch den Gra-
phen.
Listing 5.2 zeigt die Implementierung der Breitensuche (engl: Breadth First Search oder
kurz: BFS).
1 def bfs(s,graph):
2 q = Queue()
3 d = [ -1 if i̸=s else 0 for i in range(graph.numNodes)]
4 pred = [None for in range(graph.numNodes)]]
5 v = s
6 while v ̸=None:
7 for u in [u for u in graph.G(v) if d[u]== -1]:
8 d[u] = d[v] +1
9 pred[u] = v
10 q.enqueue(u)
11 if not q.isEmpty():
12 v = q.dequeue()
13 else:
14 v = None
15 return d,pred
Listing 5.2: Implementierung der Breitensuche.
Jeder Knoten v durchl¨auft hierbei in der for-Schleife in Zeile 7 diejenigen seiner Nach-
barn, die bisher noch nicht besucht wurden, d. h. deren Distanzwert d noch den Wert
-1 hat. Jeder der noch nicht besuchten Nachbarn wird durch Setzen des Distanzwer-
tes und des pred-Arrays als besucht markiert. Schließlich ”merkt“ sich die Breitensuche
den Knoten u in der Queue, um zu einem sp ¨ateren Zeitpunkt (nachdem die restlichen
Nachbarn von v abgearbeitet wurden) die Breitensuche beim Knoten u fortzufahren.
Nach Beendigung der for-Schleife gibt es keine Nachbarn von v mehr, die noch nicht

## Seite 169

154 5 Graphalgorithmen
besucht wurden. Die Breitensuche holt sich nun den n ¨achsten in der Queue vorgemerk-
ten Knoten und f ¨ahrt mit diesem fort. Sollte die Queue allerdings leer sein, so gibt es
f¨ur die Breitensuche nichts mehr zu tun; der Algorithmus bricht ab.
Nach Durchlauf der Breitensuche beﬁndet sich in Eintrag d[i ] die L¨ange des k¨urzesten
Pfades vom Startknoten s zum Knoten i und die Kantenmenge {(i,j) |pred[i ] = j }
bildet einen Spannbaum des Graphen.
Abbildung 5.9 zeigt den Ablauf einer Breitensuche f ¨ur den Beispielgraphen aus Abbil-
dung 5.7.
Aufgabe 5.5
Verwenden Sie die Breitensuche, um alle Zusammenhangskomponenten eines Gra-
phen zu bestimmen; implementieren Sie eine entsprechende Funktion allComps, die
eine Liste aller Zusammenhangskomponenten zur ¨uckliefert. Eine Zusammenhangs-
komponenten soll hierbei wiederum als Menge (etwa repr¨asentiert als Liste oder set-
Objekt) von Knoten repr ¨asentiert sein, die die entsprechende Zusammenhangskom-
ponente bilden. Beispiel:
>>>allComps(graph)
>>> [ [a,b,c ], [d,e ], [ f ] ]
graph=
a
b
c d
e
f
5.2.2 Tiefensuche
Stacks
F¨ur eine (iterative) Implementierung der Tiefensu-
che empﬁehlt es sich einen Stapelspeicher, auch in
der deutschen Literatur oft mit dem englischen Wort
Stack bezeichnet, zu verwenden. Einen Stack kann
man sich vorstellen als einen Stapel Papier auf einem
Schreibtisch; jedes Papier bedeutet gewisse Arbeit,
die durchzuf¨uhren ist. Kommt neue Arbeit hinzu, so
legt man diese ¨ublicherweise – wie in Abbildung 5.10
angedeutet – oben auf dem Stapel ab und will man
ein neues Blatt bearbeiten, so entnimmt man dieses
auch von oben.
pop
push
Abb. 5.10: Ein Stapelspeicher;
neue Elemente (bzw. Bl ¨atter)
werden immer oben abgelegt und
von oben entnommen.
In der Informatik ist ein Stack eine Datenstruktur, die ¨ublicherweise die folgenden
Operationen unterst ¨utzt. 1. Das Einf ¨ugen push(x) eines Elementes in einen Stack; 2.
Das Entnehmen pop() des obersten Elements; 3. Der Test isEmpty(), ob der Stack
leer ist. Entscheidend ist die folgende Eigenschaft von Stacks: Es wird immer dasjenige
Element als N ¨achstes zur Bearbeitung vom Stack entfernt, das sich am k ¨urzesten im
Stack beﬁndet, d. h. das als letztes in den Stack gelegt wurde. Aus diesem Grund wird
diese Datenstruktur gerne als LIFO (= last-in, ﬁrst-out) bezeichnet.

## Seite 170

5.2 Breiten- und Tiefensuche 155
1 1
1
v = 1
unvisitedNeighb = [2,4,5 ]
q = -
1
2
3
4
6 9
8
7 10
115
(a)
1 1
1
v = 2
unvisitedNeighb = [3]
q =
2
2 4 5
1
2
3
4
6 9
8
7 10
115
(b)
1 1
1
q =
v = 4
unvisitedNeighb = [ ]
2
4 5 3
1
2
3
4
6 9
8
7 10
115
(c)
1 1
1
q =
2
2 2
v = 5
unvisitedNeighb = [8,9 ]
4 5 3
1
2
3
4
6 9
8
7 10
115
(d)
1 1
1
q =
2
2 23
v = 3
unvisitedNeighb = [6]
3 8 9
1
2
3
4
6 9
8
7 10
115
(e)
1 1
1
q =
2
2 23
v = 8
unvisitedNeighb = [7,11 ]
3
3
8 9 7 11
1
2
3
4
6 9
8
7 10
115
(f)
. . . . . . . . . . . . . . . . . . . . .
1 1
1
q =
2
2 23
3
3
v = 11
unvisitedNeighb = [10]
4
11
1
2
3
4
6 9
8
7 10
115
(g)
Abb. 5.9: Ablauf einer Breitensuche durch den in Abbildung 5.7 dargestellten Beispielgra-
phen. F ¨ur jeden Durchlauf ist der Wert des aktuellen Knotens v, seine noch nicht besuchten
Nachbarn unvisitedNeighb und der Wert der Warteschlange q angegeben. Die fett gezeichneten
Kanten sind die in Liste pred aufgef ¨uhrten Kanten, also Kanten, die im bisherigen Verlauf
der Breitensuche gegangen wurden. Neben bisher besuchten Knoten sind die jeweiligen Werte
der d-Liste aufgef ¨uhrt, also der Liste, die im Laufe der Breitensuche f ¨ur jeden Knoten den
Abstandswert berechnet.

## Seite 171

156 5 Graphalgorithmen
Aufgabe 5.6
Implementieren Sie eine Klasse Stack, die die Operationen push(x), pop(x) und
isEmpty() unterst¨utzt.
Implementierung der Tiefensuche. Die Tiefensuche erh¨alt als Eingabe einen Gra-
phen G= (V,E) und einen Startknoten s ∈V. Als Ergebnis der Tiefensuche wird die
Liste pred zur¨uckgeliefert. Die Kantenmenge {(i,j) |pred[i ] = j }beschreibt hierbei
den von der Tiefensuche gegangenen Weg durch den Graphen G.
Im Gegensatz zur Breitensuche, l¨auft die Tiefensuche ausgehend vom Startknoten einem
Pfad solange als m ¨oglich nach; wenn es nicht mehr ”weitergeht“ (weil der betreﬀende
Knoten keine nicht besuchten Nachbarn mehr hat) so setzt die Tiefensuche zur¨uck, d. h.
sie l¨auft den gegangenen Pfad solange r ¨uckw¨arts, bis sie wieder einen Knoten ﬁndet,
f¨ur den es noch etwas zu tun gibt. Dieses ”Zur¨ucksetzen“ nennt man in der Informatik
auch Backtracking.
Listing 5.3 zeigt die Implementierung der Tiefensuche.
1 def dfs(s,graph):
2 pred = []
3 n = graph.numNodes
4 pred = [None for in range(n)]
5 st = Stack()
6 v = s
7 while True:
8 unvisitedNeighb = [u for u in graph.G(v) if pred[u]==None and u ̸=s]
9 if unvisitedNeighb ̸= [ ]:
10 u = unvisitedNeighb[0]
11 st .push(v)
12 pred[u] = v
13 v = u
14 elif not st.isEmpty():
15 v = st.pop()
16 else:
17 break
18 return pred
Listing 5.3: Implementierung der Tiefensuche
Zun¨achst werden die verwendeten Variablen pred, st und v initialisiert. Der eigentliche
Algorithmus beginnt ab Zeile 7. In Zeile 8 werden zun ¨achst die Nachbarn des aktuellen
Knotens v gesucht, die noch nicht besucht wurden und in der Liste unvisitedNeighb
gespeichert. Es gibt drei F ¨alle: 1. Die Liste unvisitedNeighb enth¨alt mindestens ein
Element, d. h. es gibt einen noch nicht besuchten Nachbarnu von v. In diesem Fall wirdv
auf den Stack gelegt, in der Annahme, es k¨onne zu einem sp¨ateren Zeitpunkt ausgehend
von v noch mehr zu tun geben. Die Kante (v, u) wird anschließend zur ”Menge“ pred

## Seite 172

5.2 Breiten- und Tiefensuche 157
der durch die Tiefensuche gegangenen Kanten hinzugef ¨ugt; schließlich wird mit dem
Knoten u fortgefahren. 2. Die Liste unvistedNeigb ist leer, d. h. es gibt keinen noch nicht
besuchten Nachbarn von v, d. h. ausgehend vom Knoten v gibt es f ¨ur die Tiefensuche
nichts mehr zu tun. Falls es noch auf dem Stack st hinterlegte ”Arbeit“ gibt, wird diese
vom Stack geholt. 3. Falls sowohl die Liste invisitedNeigb, als auch der Stack leer ist,
ist die Tiefensuche beendet und die while-Schleife wird verlassen.
Aufgabe 5.7
Es gibt eine entscheidende Ineﬃzienz in der in Listing 5.3 vorgestellten Implemen-
tierung der Tiefensuche: Obwohl in jedem Schleifendurchlauf der while-Schleife nur
ein einziger noch nicht besuchter Nachbar von v zur weiteren Bearbeitung ben ¨otigt
wird, wird in der Listenkomprehension in Zeile 8 immer die gesamte Menge der noch
nicht besuchten Nachbarn berechnet.
Verbessern sie die Implementierung der Tiefensuche, indem sie diese Ineﬃzienz ent-
fernen.
Abbildung 5.11 zeigt den Ablauf einer Tiefensuche f ¨ur den Beispielgraphen aus Abbil-
dung 5.7.
Die ”nackte“ Tiefensuche liefert zwar keine eigentlich n¨utzliche Information zur¨uck, je-
doch dient die Tiefensuche als”Ger¨ust“ f¨ur eine Vielzahl wichtiger Graphenalgorithmen,
unter Anderem der topologischen Sortierung, der Suche nach Zyklen in einem Graphen
oder der Auswertung als B ¨aume repr¨asentierter arithmetischer Ausdr¨ucke.
Aufgabe 5.8
Das sog. Springerproblem besteht darin, auf einem sonst leeren n×n Schachbrett
eine Tour f¨ur einen Springer zu ﬁnden, auf der dieser jedes Feld genau einmal besucht.
Wir w¨ahlen zun¨achst besser n< 8 (andernfalls sind
sehr lange Rechenzeiten zu erwarten). Finden Sie ei-
ne L ¨osung f ¨ur das Springerproblem, indem sie wie
folgt vorgehen:
1: Repr¨asentieren Sie das Problem als Graph. Jedes
Feld des Schachbretts sollte einen Knoten darstel-
len und jeder m¨ogliche Zug sollte als Kante zwischen
zwei Knoten dargestellt werden; sie k ¨onnen entwe-
der die Kanten von Hand eintragen oder ein Pro-
gramm schreiben, das das erledigt. 2: Verwenden Sie
eine Variante der Tiefensuche, die verbietet, dass ein
Knoten mehr als einmal besucht wird und ﬁnden Sie
damit eine L¨osung des Springerproblems.
Ein Graph der alle m ¨oglichen
Z¨uge eines Springers auf einem
8 ×8 Schachbrett repr¨asentiert.

## Seite 173

158 5 Graphalgorithmen
v = 1
unvisitedNeighb = [2,4,5 ]
s = -
1
1
2
3
4
6 9
8
7 10
115
(a)
v = 2
unvisitedNeighb = [3]
s =
1
2
1
1
2
3
4
6 9
8
7 10
115
(b)
s =
v = 7
unvisitedNeighb = [ ]
1
2
3
4
5
6
1 2 3 6 5 8
1
2
3
4
6 9
8
7 10
115
(c)
v = 8
unvisitedNeighb = [11]
s =
1
2
3
4
5
6
7
1
2
3
4
6 9
8
7 10
115
1 2 3 6 5 8
(d)
s =
v = 11
unvisitedNeighb = [10]
1
2
3
4
5 7
6 8
1
2
3
4
6 9
8
7 10
115
1 2 3 6 5 8 11
(e)
s =
v = 10
unvisitedNeighb = [ ]
1
2 3 4
5
6
7
8
1
2
3
4
6 9
8
7
115
1 2 3 6 5 8 11
10
(f)
s =
v = 6
unvisitedNeighb = [9]
1
2
3
4
5
6
7
8
9
1
2
3
4
6 9
8
7
115
1 2 3
10
6
(g)
s =
v = 1
unvisitedNeighb = [4]
1
2
3
4
5
6 8
7
9
101
2
3
4
6 9
8
7
115
1
10
(h)
Abb. 5.11: Ablauf einer Tiefensuche durch den in Abbildung 5.7 dargestellten Beispielgraphen.
F¨ur jede Situation ist der Wert des aktuellen Knotens v, seine noch nicht besuchten Nachbarn
unvisitedNeighb und der Wert des Stacks s angegeben. Die fett gezeichneten Kanten sind die
in Liste pred aufgef ¨uhrten Kanten, also Kanten, die im bisherigen Verlauf der Tiefensuche
gegangen wurden. Der ¨Ubersichtlichkeit halber wurden die Kanten in der von der Tiefensuche
gegangenen Reihenfolge nummeriert – diese Nummerierung erfolgt lediglich der Anschaulichkeit
halber; sie wird im Algorithmus selbst nicht protokolliert. Man beachte, dass einige Schritte in
der Darstellung ¨ubersprungen wurden, und zwar drei Schritte zwischen 5.11(b) und 5.11(c),
vier Schritte zwischen 5.11(f) und 5.11(g) und vier Schritte zwischen 5.11(g) und 5.11(h).

## Seite 174

5.2 Breiten- und Tiefensuche 159
Aufgabe 5.9
Statt explizit einen Stack zu verwenden, l ¨asst sich die Tiefensuche elegant rekursiv
implementieren. Implementieren Sie eine rekursive VariantedfsRek, des in Listing 5.3
gezeigten Algorithmus dfs.
5.2.3 Topologische Sortierung
Eine topologische Sortierung ist eine Anordnung der Knoten eines DAG, d. h. eines
gerichteten azyklischen Graphen G = ( V,E), so dass f ¨ur jede Kante (i,j ) ∈E gilt,
dass Knoten j nach Knoten i angeordnet ist. DAGs werden oft verwendet, wenn man
eine Rangordnungen zwischen bestimmten Elementen oder Ereignissen darstellen will.
Beispielsweise ließe sich der Graph aus Abbildung 5.7 auf Seite 151 topologisch sortieren
durch die folgende Anordnung seiner Knoten:
1,4,2,3,6,5,9,8,7,11,10
Der Graph ließe sich dann entsprechend so zeichnen, dass jede Kante von links nach
rechts verl¨auft:
1 4 2 3 6 5 9 8 7 11 10
Man kann eine topologische Sortierung folgendermaßen einfach berechnen: Man beginnt
eine Tiefensuche durch einen Graphen mit einem Knoten, der keinen Vorg¨anger besitzt;
solch ein Knoten muss existieren, wenn der Graph keinen Zyklus besitzt. Sobald bei solch
einem Tiefensuche-Durchlauf ein bestimmter Knotenv ”abgeschlossen“ wurde, f¨uge die-
sen mittels append hinten an eine Liste an. Oder genauer formuliert: Sobald f ¨ur einen
Knoten v der w¨ahrend der Tiefensuche in Listing 5.3 berechneten Liste unvisitedNeighb
(Zeile 8) leer ist, wird dieser Knoten v an die eine topologische Anordnung der Knoten
repr¨asentierende Ergebnisliste hinten angeh ¨angt. Nach der Tiefensuche enth ¨alt diese
Ergebnisliste die f ¨ur die topologische Sortierung erforderliche Rangordnung. Dies kann
ganz einfach folgendermaßen implementiert werden (in den mit ... markierten Berei-
chen beﬁndet sich Code der identisch zu dem Code der Tiefensuche aus Listing 5.3
ist):
1 def topSort(s,graph): #s: Knoten ohne Vorg¨anger
2 topLst = []
3 ...
4 while True:
5 ...
6 if unvisitedNeighb ̸= [ ]:
7 ...
8 elif not st.isEmpty():
9 topLst.append(v)
10 v = st.pop()

## Seite 175

160 5 Graphalgorithmen
11 else:
12 topLst.append(v)
13 break
14 topLst.reverse()
15 return topLst
Listing 5.4: Berechnung einer topologischen Sortierung eines DAG. Der Startknoten s muss
hierbei so gew ¨ahlt sein, dass s keinen Vorg ¨anger besitzt.
Der elif- und else-Zweig wird gegangen, wenn der betreﬀende Knoten v abgeschlossen
ist; genau zu diesem Zeitpunkt wird v in die Liste topLst der topologisch sortierten
Knoten eingef¨ugt.
Aufgabe 5.10
(a) Welche Anordnung der Knoten liefert der in Listing 5.4 dargestellte Algorithmus
als topologische Sortierung?
(b) Versuchen Sie herauszuﬁnden, wie viele verschiedene topologische Sortierungen
es f¨ur den in Abbildung 5.7 dargestellten Graphen gibt.
Aufgabe 5.11
Beim Anziehen von Kleidungsst ¨ucken m¨ussen manche Teile unbedingt vor anderen
angezogen werden. Die folgenden Beziehungen sind vorgegeben:
 Das Unterhemd vor dem Pullover
 Die Unterhose vor der Hose
 Den Pullover vor dem Mantel
 Die Hose vor dem Mantel
 Die Hose vor den Schuhen
 Die Socken vor den Schuhen
(a) Modellieren Sie diese Abh ¨angigkeiten als Graphen.
(b) Nummerieren Sie die Knoten so, dass sich die daraus ergebende Rangordnung
der Knoten eine topologische Sortierung darstellt – gibt hier mehrere L ¨osungen.
(c) Bestimmen Sie diejenige topologische Sortierung, die sich durch Ausf ¨uhrung von
dem in Listing 5.4 gezeigten Algorithmus ergibt.

## Seite 176

5.3 K ¨urzeste Wege 161
Aufgabe 5.12
Die topologische Sortierung erwartet als Eingabe einen Knoten, der keinen Vorg¨anger
besitzt. Implementieren Sie eine Funktion startNodes(graph), die alle Knoten des
Graphen graph zur¨uckliefert, die keinen Vorg¨angerknoten besitzen.
Aufgabe 5.13
Der in Listing 5.4 gezeigte Algorithmus funktioniert nur auf zusammenh ¨angenden
DAGs. Erweitern Sie den Algorithmus so, dass er auch auf nicht zusammenh¨angenden
DAGs funktioniert.
Aber warum liefert dieser Algorithmus eine topologische Sortierung? Wir m ¨ussen dazu
Folgendes zeigen: Beﬁndet sich eine Kante (u,v) im Graphen G= (V,E), so wird zuerst
topLst.append(v) und danach erst topLst.append(u) ausgef¨uhrt. Durch die Anweisung
topLst.reverse() in Zeile 14 in Listing 5.4 werden dann schließlich u und v in die rich-
tige Reihenfolge gebracht – n ¨amlich u vor v. Warum also wird topLst.append(v) vor
topLst.append(u) ausgef¨uhrt?
Wird im Rahmen der Tiefensuche der Knoten u erstmalig betrachtet, so gibt es zwei
M¨oglichkeiten. 1. Es gilt: v in unvisitedNeighb. In diesem Fall wird u auf den Stack
gelegt (Zeile 11) und die Tiefensuche mit dem Knoten v weiter durchlaufen, und zwar
so lange, bis v abgeschlossen wird und keine nicht besuchten Nachbarn mehr besitzt
(d. h. unvisitedNeighb == [] gilt) und somit topLst.append(v) ausgef ¨uhrt wird. Erst
danach wird der Knoten u fertig bearbeitet und somit folgt erst danach die Anweisung
topLst.append(u).
2. Es gilt: v not in unvisitedNeighb. Der Knoten v wurde also schon besucht. Kann
es dann sein, dass v noch nicht abgeschlossen ist (und folglich topLst.append(u) vor
topList .append(v) ausgef¨uhrt werden w¨urde)? W¨are dem so, dann w¨urde sich in diesem
Fall v noch im Stack st beﬁnden, d. h. st h¨atte folgendes Aussehen:
[. . . ,v, . . . ,u ]
Folglich m¨usste es einen Pfad von v nach u geben. Zusammen mit der Kante ( u,v)
w¨urde dies einen Kreis ergeben, was aber nach Voraussetzung (es handelt sich um einen
DAG, also einen kreisfreien Graphen) unm ¨oglich ist.
5.3 K ¨urzeste Wege
Eine der oﬀensichtlichsten Anwendungen der Graphentheorie besteht in der Aufgabe,
die k ¨urzest m¨oglichen Wege in einem kantenbewerteten Graphen G = (V,E) mit der
Gewichtsfunktion w : E →R + zwischen zwei Knoten zu berechnen. Die Funktion w
ordnet jeder Kante eine (positive) Zahl zu; so kann man etwa den Abstand zwischen
zwei St ¨adten abbilden. Es ist nicht zuletzt der Eﬃzienz und Eleganz des Dijkstra-
Algorithmus zu verdanken, dass die Berechnung des k ¨urzesten Weges zwischen zwei

## Seite 177

162 5 Graphalgorithmen
Ortschaften durch ein Navigationssystem oder ein Online-Routenplanungssystem so
schnell und unkompliziert m¨oglich ist.
Wir stellen in diesem Abschnitt zwei unterschiedliche Algorithmen zur Berechnung
der k ¨urzesten Wege in einem Graphen G = (V,E ) vor: Zum Einen den Dijkstra-
Algorithmus, der die k¨urzesten Wege ausgehend von einem bestimmten Knotenu∈V zu
allen anderen Knoten im Graphen berechnet; zum Anderen den Warshall-Algorithmus,
der die k ¨urzesten Wege zwischen allen Knotenpaaren u,v ∈V berechnet – in der eng-
lischsprachigen Literatur wird diese Aufgabe auch als ”All Pairs Shortest Paths“ be-
zeichnet.
5.3.1 Der Dijkstra-Algorithmus
Will man einen k¨urzesten Pfad von einem Knoten uzu ei-
Abb. 5.12: Edsger Dijkstra
(1930 - 2002).
nem anderen Knoten v berechnen, so k ¨onnte dieser Pfad
im Allgemeinen alle anderen Knoten ber ¨uhren. Es macht
daher durchaus Sinn, f¨ur die L¨osung dieses Problems einen
Algorithmus zu entwerfen, der die k ¨urzesten Wege von
Knoten u zu jedem anderen Knoten des Graphen berech-
net. Der sog. Dijkstra-Algorithmus, entdeckt von dem nie-
derl¨andischen Informatik-Pionier Edsger Dijkstra, ist ein
eﬃzienter Algorithmus der alle von u ausgehenden k ¨urz-
esten Wege berechnet. Dijkstra war unter Anderem auch
der Wegbereiter der strukturierten Programmierung und
der parallelen Programmierung (er verwendete erstmals
Semaphoren, eine spezielle Datenstruktur, die dazu ein-
gesetzt wird, parallel laufende Prozesse zu synchronisieren).
Der Dijkstra Algorithmus ist ein typischer sog. Greedy-Algorithmus. Greedy-Algorith-
men schlagen zum Finden einer optimalen L¨osung eine einfache Vorgehensweise ein: Es
wird in einem Schritt immer nur eine bestimmte Teill¨osung berechnet. Um die Teill¨osun-
gen zu erweitern und sich dadurch einen Schritt Richtung Gesamtl ¨osung zu bewegen,
werden nur diejenigen M ¨oglichkeiten in Betracht gezogen, die ”lokal“ zum jeweiligen
Zeitpunkt am g ¨unstigsten erscheinen. Nicht immer f ¨uhrt die Strategie eines Greedy-
Algorithmus zur Berechnung des Optimums – jedoch im Falle des Dijkstra-Algorithmus
schon.
Dies ist genau die Vorgehensweise des Dijkstra-Algorithmus zum Finden der k ¨urzesten
Wege ausgehend von einem bestimmten Knoten u in einem Graphen G = (V,E ). In
jedem Schritt wird immer derjenige noch nicht fertig bearbeitete Knoten betrachtet,
der den momentan geringsten Abstandswert zu u hat.
Der Dijkstra-Algorithmus liefert als Ergebnis die Abst ¨ande l[v] aller Knoten v ∈V zu
Knoten u und zus¨atzlich in Form der Menge F alle Kanten, aus denen die k ¨urzesten
Wege bestehen. In der Menge W merkt sich der Algorithmus die noch zu bearbeitenden
Knoten; in jedem Durchlauf des Dijkstra-Algorithmus wird ein Knoten aus W entfernt
und zwar immer derjenige mit dem momentan geringsten Abstand zuu. Nach |V|vielen
Durchl¨aufen hat der Algorithmus also alle k ¨urzesten Wege berechnet. In jedem der |V|
Durchl¨aufe wird immer derjenige Knoten v als N¨achstes bearbeitet, der den momentan

## Seite 178

5.3 K ¨urzeste Wege 163
geringsten Abstand l[v] vom Startknoten u besitzt – genau dieser Schritt macht den
Algorithmus zu einem Greedy-Algorithmus. In diesem Schritt wird immer jeweils die
gesamte Nachbarschaft Γ(v) des Knotens vdurchlaufen und versucht die Abstandswerte
der Nachbarn zu verbessern. Hierbei wird der Abstandswert eines Nachbarn v′∈Γ(v)
genau dann angepasst, falls entweder noch kein Abstandswert berechnet wurde oder
falls
l[v] + w(v,v′) <l[v′]
gilt, d. h. falls ein Weg ¨uber v zu v′k¨urzer ist als der bisher berechnete Weg.
Listing 5.5 zeigt die Implementierung des Dijkstra-Algorithmus.
1 def dijkstra (u,graph):
2 n = graph.numNodes
3 l = {u:0}; W = graph.V()
4 F = [] ; k = {}
5 for i in range(n):
6 lv ,v = min([ (l [node],node) for node in l if node in W ])
7 W.remove(v)
8 if v̸=u: F.append(k[v])
9 for neighb in ﬁlter (lambda x:x in W, graph.G(v)):
10 if neighb not in l or l [v ] +graph.w(v,neighb) < l[neighb]:
11 l [neighb] = l [v ] +graph.w(v,neighb)
12 k [neighb] = ( v,neighb)
13 return l,F
Listing 5.5: Der Dijkstra-Algorithmus
Die for-Schleife ab Zeile 5 implementiert die |V|vielen Durchl¨aufe. In Zeile 6 wird be-
stimmt, welcher Knoten in dem aktuellen Durchlauf bearbeitet wird, n ¨amlich derjenige
Knoten v, mit minimalem Abstandswert l [v ]. Dieser Knoten wird aus der Menge W der
zu bearbeitenden Knoten gel¨oscht (Zeile 7) und die entsprechende aus Richtung u kom-
mende Kante k [v ] zur Kantenmenge F hinzugef¨ugt. In Zeile 12 beginnt die for-Schleife,
die die Nachbarschaft des Knotens v durchl¨auft und alle suboptimalen Abstandswer-
te anpasst. F ¨ur jeden angepassten Nachbarknoten neighb merkt sich der Algorithmus
zus¨atzlich in Zeile 12 die Kante (v,neighb), die zu dieser Anpassung f¨uhrte; diese Kante
wird sp¨ater eventuell (falls diese Anpassung sp ¨ater nicht noch weiter optimiert wird)
zur Kantenmenge F der k¨urzesten Wege hinzugef¨ugt.
Abbildung 5.13 zeigt den Ablauf des Dijkstra-Algorithmus f ¨ur einen gewichteten unge-
richteten Beispielgraphen.

## Seite 179

164 5 Graphalgorithmen
W = {a,b,c,d,e,f,g,u}
l[u]=0
a
b d
c
e
u f
g
4
2
1
2
5
3
5
82
11
3 4
10
7
(a)
W = {a,b,c,d,e,f,g }
l[c]=11 l[u]=0 l[f]=2
l[e]=7 l[g]=5l[d]=4
a
b d
c
e
u f
g
4
2
1
2
5
3
5
82
11
3 4 7
10
(b)
l[c]=11 l[u]=0 l[f]=2
l[e]=7
W = {a,b,c,d,e,g }
l[g]=3l[d]=4
a
b d
c
e
u f
g
4
2
1
2
5
3
5
82
11
3 4 7
10
(c)
l[c]=11 l[u]=0 l[f]=2
l[e]=7 l[g]=3
W = {a,b,c,d,e}
l[d]=4
a
b d
c
e
u f
g
4
2
1
2
5
3
5
82
11
3 4 7
10
(d)
l[u]=0 l[f]=2
l[g]=3l[e]=6
l[c]=9
W = {a,b,c,e }
l[b]=14 l[d]=4
a
b d
c
e
u f
g
4
2
1
2
5
3
5
82
11
3 4 7
10
(e)
l[u]=0 l[f]=2
l[g]=3l[e]=6
l[c]=9l[a]=11
l[b]=13
W = {a,b}
l[d]=4
a
b d
c
e
u f
g
4
2
1
2
5
3
5
82
11
3 4 7
10
(f)
Abb. 5.13:Ablauf des Dijkstra-Algorithmus auf einem gewichteten ungerichteten Graphen. Ab-
bildung 5.13(a) zeigt die Ausgangssituation: Es existiert nur f ¨ur den Startknoten ein Abstands-
wert von 0. Im ersten Schritt, gezeigt in Abbildung 5.13(b), wird der Startknoten u bearbeitet
da dieser initial den kleinsten Abstandswert hatte. Die Nachbarschaft von u wird durchlaufen,
die Abstandswerte aller Nachbarn werden angepasst und die entsprechenden Kanten in k vor-
gemerkt. Diese Kanten sind in den Abbildungen immer fett gezeichnet. Im n ¨achsten Schritt
(Abbildung 5.13(c)) wird, da l [f ] minimal ist, der Knoten f bearbeitet. Die Nachbarschaft des
Knotens f wird also durchlaufen; hierbei wird der Abstandswert des Knotens g angepasst, denn
l [f ] +w(f,g) ist kleiner als l [g ]; die Abstandswerte der restlichen Nachbarn bleiben gleich. Als
N¨achstes (Abbildung 5.13(d)) wird der Knoten g bearbeitet, da l [g ] minimal ist, usw.

## Seite 180

5.3 K ¨urzeste Wege 165
Aufgabe 5.14
In jedem der |V|vielen Durchl¨aufe des Dijkstra-Algorithmus muss der Knoten mit
minimalem Abstandswert l bestimmt werden. Dies geschieht in Algorithmus 5.5 mit-
tels der min-Anweisung in Zeile 9.
(a) Welche Laufzeit hat diese min-Anweisung?
(b) Statt das Minimum aus einer Liste zu bestimmen ist es i. A. eﬃzienter ein Heap-
Datenstruktur zu verwenden und mittels minExtract das Minimum zu extrahie-
ren. Welche Laufzeit h ¨atte das Finden des Knotens mit minimalem Abstands-
wert, falls statt einer einfachen Liste eine Heap-Datenstruktur verwendet wird?
(c) Geben sie eine Python-Implementierung des Dijkstra-Algorithmus an, zum Fin-
den des minimalen Abstandswertes Heaps verwendet.
5.3.2 Der Warshall-Algorithmus
Gegeben sei, genau wie beim Dijkstra-Algorithmus, ein kantenbewerteter Graph G =
(V,E) mit der Gewichtsfunktion w: E →R +. Der Warshall-Algorithmus berechnet die
k¨urzesten Wege zwischen allen Knotenpaaren in G. Wir gehen von einer Knotenmenge
V = {1,...,n }aus.
Entscheidend f¨ur den Warshall-Algorithmus ist folgende ¨Uberlegung. Man betrachtet
zun¨achst k¨urzeste Wege, f¨ur die gewisse Einschr¨ankungen gelten. Diese ”Einschr¨ankun-
gen“ sollten optimalerweise zwei Eigenschaften erf¨ullen: 1: Die Berechnung der k¨urzesten
Wege, f¨ur die diese Einschr¨ankungen (die wir gleich genau erl¨autern) gelten, sollte sinn-
vollerweise einfacher sein, als die Berechnung der k ¨urzesten Wege ohne Einschr¨ankun-
gen. 2: Es sollte m¨oglich sein, diese Einschr¨ankungen schrittweise zu entfernen, bis man
schließlich die k¨urzesten Wege (f¨ur die gar keine Einschr ¨ankungen mehr gelten) erh ¨alt.
Wir sehen nun diese Einschr¨ankungen im Falle des Warshall-Algorithmus aus? Anf¨ang-
lich berechnen wir die k¨urzesten Wege, die keine Zwischenknoten enthalten (also nur Di-
rektverbindungen); diese ”Berechnung“ ist sehr einfach, denn diese Direktverbindungen
sind in Form der Adjazenzmatrix des Graphen schon vorhanden. Im n ¨achsten Schritt
berechnen wir die k ¨urzesten Wege, deren Zwischenknoten aus der Knotenmenge {1}
kommen. Im folgenden Schritt berechnen wir, aus den im vorigen Schritt berechneten
Informationen, die k¨urzesten Wege, deren Zwischenknoten aus der Knotenmenge {1,2}
kommen, usw. Im letzten Schritt berechnen wir schließlich die k ¨urzesten Wege, de-
ren Zwischenknoten aus der Knotenmenge {1,...,n }kommen, d. h. f¨ur diese k¨urzesten
Wege gibt es keine Einschr ¨ankungen mehr. In diesem letzten Schritt werden also die
gesuchten k¨urzesten Wege berechnet.
Wir m¨ussen uns nur noch ¨uberlegen, wie man vom (k−1)-ten Schritt zum k-ten Schritt
”kommen“ kann, d. h. wie man aus dem k ¨urzesten Pfad zwischen Knoten i ∈V und
Knoten j ∈V, dessen innere Knoten ausschließlich aus der Knotenmenge {1,...,k −1}
kommen, den k ¨urzesten Pfad zwischen i und j berechnen kann, dessen innere Knoten
aus der Knotenmenge {1,...,k }kommen. Bei der Konstruktion dieser Berechnung ist
es sinnvoll zwei F¨alle zu unterschieden.

## Seite 181

166 5 Graphalgorithmen
Pfad mit Knoten aus {1,...,k −1}
Pfad mit Knoten aus {1,...,k }
i j
k
Abb. 5.14:Darstellung der beiden M ¨oglichkeiten f¨ur die Konstruktion eines k ¨urzesten Pfades
zwischen Knoten i und Knoten j der ausschließlich Knoten aus {1,...k }enth¨alt. Entweder
enth¨alt dieser Pfad tats ¨achlich k als inneren Knoten, oder solch ein Pfad enth ¨alt den Knoten
k nicht. Der Warshall-Algorithmus w ¨ahlt in jedem Schritt immer den k ¨urzeren dieser beiden
m¨oglichen Pfade.
1: Der k¨urzeste Pfad zwischen i und j mit inneren Knoten aus {1,...,k }enth¨alt den
inneren Knoten k nicht. In diesem Fall gilt einfach, dass der k ¨urzeste Pfad zwischen
Knoten i und Knoten j mit inneren Knoten aus {1,...,k −1}gleich dem k ¨urzesten
Pfad zwischen i und j mit inneren Knoten aus {1,...,k }ist.
2: Der k ¨urzeste Pfad zwischen i und j mit inneren Knoten aus {1,...k }enth¨alt den
inneren Knoten k; dieser setzt sich zusammen aus dem k¨urzesten Pfad von inach kmit
inneren Knoten aus {1,...,k −1}und dem k ¨urzesten Pfad von k nach j mit inneren
Knoten aus {1,...,k −1}. Abbildung 5.14 veranschaulicht diesen Sachverhalt graphisch.
Wir bezeichnen mit Wk[i,j] die L ¨ange des k ¨urzesten Pfads zwischen Knoten i und
Knoten j mit inneren Knoten ausschließlich aus {1,...,k }. Dann gilt nach den vorigen
¨Uberlegungen also folgende Beziehung:
Wk[i,j] := min{Wk−1[i,j], Wk−1[i,k] + Wk−1[k,j] } (5.1)
Wir sind also in der Lage Wk aus Wk−1 zu berechnen. Die gew¨unschte L¨osung, also alle
k¨urzesten Wege, erhalten wir durch Berechnung von Wn, das bzgl. der inneren Knoten
eines jeden Pfades keine Beschr¨ankung mehr auferlegt. Wir beginnen die Berechnungen
mit der Matrix W0, die nichts anderes ist als die Adjazenzmatrix des Graphen G. Es
ergibt sich also folgender Algorithmus:
1 def warshall(graph):
2 n = graph.numNodes+1
3 W = [[graph.w(i , j) for j in graph.V()] for i in graph.V() ] # W0
4 for k in range(1,n): # Berechnung von Wk
5 for i in range(1,n):
6 for j in range(1,n):
7 W[i][j ] = min( W[i][j ] , W[i][k ] +W[k][j ] )
8 return W
Listing 5.6: Implementierung des Warshall-Algorithmus
Die geschachtelte Listenkomprehension in Zeile 3 erzeugt zun ¨achst die Matrix W0, also
die Adjazenzmatrix von graph. Wichtig zu wissen ist hier, dass die Methode V() der
Klasse Graph die Liste der im Graph vorhandenen Knoten zur ¨uckliefert; die Metho-
de w(i, j) der Klasse Graph muss so implementiert sein, dass graph.w(i, i) den Wert

## Seite 182

5.3 K ¨urzeste Wege 167
0 zur ¨uckliefert (der Abstand eines Knotens i zu sich selbst ist sinnvollerweise 0) und
graph.w(i, j) den Wert ∞zur¨uckliefert (in Python i. A. repr ¨asentiert durch den spezi-
ellen Wert inf1), falls ( i , j) /∈E; in allen anderen F ¨allen soll graph.w(i, j) das Gewicht
der Kante ( i , j) zur ¨uckliefern. Die Matrix W wird nun in n -1 Schleifendurchl¨aufen
schrittweise erweitert. Zeile 7 entspricht einer direkten Umsetzung der Formel (5.1).
Der Algorithmus liefert in Zeile 8 die Matrix Wn in Form der Variablen W zur¨uck;
W[i][j ] enth¨alt dann die L ¨ange des k ¨urzesten Weges von Knoten i zu Knoten j. Ab-
bildung 5.15 zeigt die Zwischenergebnisse des Warshall-Algorithmus, d. h. die Matrizen
Wk f¨ur die Berechnung der k ¨urzesten Wege eines Beispielgraphen.
Aufgabe 5.15
Implementieren Sie eine Methode w(i, j) der Klasse Graph in der f ¨ur den Warshall-
Algorithmus erforderlichen Weise.
Aufgabe 5.16
Die transitive H¨ulle eines gerichteten Graphen G= (V,E) ist deﬁniert als die Matrix
H = (hij) mit
hij =
{
1, Falls es einen gerichteten Pfad von i nach j in G gibt
0, sonst
Implementieren Sie eine FunktiontransHuelle(graph) die die transitive H¨ulle des Gra-
phen graph als Ergebnis zur¨uckliefert.
Tipp: Sie k ¨onnen transHuelle relativ einfach dadurch programmieren, indem sie
warshall an geeigneter Stelle etwas modiﬁzieren.
Die Laufzeit des Warshall-Algorithmus ist aus oﬀensichtlichen Gr ¨unden O(|V|3), denn
die |V|×|V |große Adjazenzmatrix muss genau |V|mal durchlaufen werden.
1Dieser spezielle Wert inf kann in Python durch den Aufruf ﬂoat ('inf') erzeugt werden; dies sollte
in den meisten Python-Installationen m¨oglich sein; es ist jedoch m¨oglich, dass ¨altere Python-Versionen
(Versionsnummer ¡ 2.4) diesen speziellen Wert noch nicht unterst ¨utzen.

## Seite 183

168 5 Graphalgorithmen
3
5
4
2
1
2
5
3
5
82
11
3 4
10
1
2 4
6
7
8



0 3 2 ∞∞∞∞∞
3 0 4 10 ∞∞∞∞
2 4 0 5 ∞∞∞ 11
∞10 5 0 2 3 ∞ 4
∞∞∞ 2 0 ∞ 8 7
∞∞∞ 3 ∞ 0 1 2
∞∞∞∞ 8 1 0 5
∞∞ 11 4 7 2 5 0



k= 1



0 3 2 ∞∞∞∞∞
3 0 4 10 ∞∞∞∞
2 4 0 5 ∞∞∞ 11
∞10 5 0 2 3 ∞ 4
∞∞∞ 2 0 ∞ 8 7
∞∞∞ 3 ∞ 0 1 2
∞∞∞∞ 8 1 0 5
∞∞ 11 4 7 2 5 0



k= 2




0 3 2 13 ∞∞∞∞
3 0 4 10 ∞∞∞∞
2 4 0 5 ∞∞∞ 11
13 10 5 0 2 3 ∞ 4
∞ ∞∞ 2 0 ∞ 8 7
∞ ∞∞ 3 ∞ 0 1 2
∞ ∞∞ ∞8 1 0 5
∞ ∞11 4 7 2 5 0




k= 3




0 3 2 7 ∞∞∞ 13
3 0 4 9 ∞∞∞ 15
2 4 0 5 ∞∞∞ 11
7 9 5 0 2 3 ∞ 4
∞ ∞ ∞2 0 ∞ 8 7
∞ ∞ ∞3 ∞ 0 1 2
∞ ∞ ∞∞8 1 0 5
13 15 11 4 7 2 5 0




k= 4



0 3 2 7 9 10 ∞11
3 0 4 9 11 12 ∞13
2 4 0 5 7 8 ∞ 9
7 9 5 0 2 3 ∞ 4
9 11 7 2 0 5 8 6
10 12 8 3 5 0 1 2
∞ ∞ ∞∞8 1 0 5
11 13 9 4 6 2 5 0



k= 5



0 3 2 7 9 10 17 11
3 0 4 9 11 12 19 13
2 4 0 5 7 8 15 9
7 9 5 0 2 3 10 4
9 11 7 2 0 5 8 6
10 12 8 3 5 0 1 2
17 19 15 10 8 1 0 5
11 13 9 4 6 2 5 0



k= 6



0 3 2 7 9 10 11 11
3 0 4 9 11 12 13 13
2 4 0 5 7 8 9 9
7 9 5 0 2 3 4 4
9 11 7 2 0 5 6 6
10 12 8 3 5 0 1 2
11 13 9 4 6 1 0 3
11 13 9 4 6 2 3 0



k= 7



0 3 2 7 9 10 11 11
3 0 4 9 11 12 13 13
2 4 0 5 7 8 9 9
7 9 5 0 2 3 4 4
9 11 7 2 0 5 6 6
10 12 8 3 5 0 1 2
11 13 9 4 6 1 0 3
11 13 9 4 6 2 3 0



k= 8
Abb. 5.15: Die vom Warshall-Algorithmus berechneten Matrizen Wk f¨ur k = 1,..., 8
f¨ur den oben dargestellten Beispielgraphen. Die fett gedruckten Eintr ¨age wurden im jewei-
ligen Schritt angepasst. Ist also ein Eintrag Wk[i,j] fett gedruckt dargestellt, so gilt, dass
Wk−1[i,k] +Wk−1[k,j] < Wk−1[i,j] ist, d. h. es gilt dass es einen Weg ¨uber den Knoten k
gibt der kleiner als der bisher berechnete Weg ist.

## Seite 184

5.4 Minimaler Spannbaum 169
5.4 Minimaler Spannbaum
210
11
16
12
20
21
3
6
15
5
7
17
13
23
22
8
9
18
24
28
27
30
14
19
25
26
29
35
3136
37
33
39
43
32
34
38
40
41
45
42
44
48
47
51
53
49
50
52
54
62
58
61
46
56
55
59
57
66
60
68
63
6467
70
69
74
71
75 72
76
65
73
78
77
80
79
83
85
82
81
84
86
Neben dem systematischen Durchlaufen eines Graphen und dem Finden von k ¨urzesten
Wegen ist das Finden von minimalen (bzw. maximalen) Spannb ¨aumen das in der
Praxis wichtigste graphentheoretische Problem. Die Anwendungsbeispiele hierf ¨ur sind
vielf¨altig, etwa das Finden eines m ¨oglichst preisg¨unstigen zusammenh¨angenden Netz-
werkes.
Wir stellen in diesem Abschnitt den Algorithmus von Kruskal vor, der wie der Algo-
rithmus von Dijkstra, auch ein Greedy-Algorithmus ist. Im Verlauf des Algorithmus
von Kruskal muss eine Kantenmenge eines Graphen wiederholt daraufhin ¨uberpr¨uft
werden, ob sie Zyklen enth ¨alt. Dieser Test ist zwar relativ einfach durch eine Tie-
fensuche realisierbar; es gibt jedoch eine eﬃzientere M ¨oglichkeit, als diese wiederholte
Durchf¨uhrung der Tiefensuche. Wir stellen hierzu eine Implementierung der sog. Union-
Find-Operationen vor (in der deutschen Literatur manchmal auch als Vereinigungs-
Suche bezeichnet) mit deren Hilfe ein eﬃzienterer Test auf Zyklenfreiheit m ¨oglich ist.
5.4.1 Problemstellung
Gegeben sei wiederum ein kantengewichteter Graph G= (V,E) mit Gewichtsfunktion
w : E →R +. Gesucht ist nun die mit den geringsten Kosten verbundene M ¨oglichkeit,
alle Knoten in G mit Kanten aus E zu verbinden. Man kann sich leicht ¨uberlegen,
dass solch ein Verbindungsgraph ein Spannbaum sein muss2. Abbildung 5.16 gibt ein
Beispiel eines minimalen Spannbaums – der ¨ubrigens nicht immer eindeutig bestimmt
ist; es kann durchaus mehrere minimale Spannb ¨aume geben.
Aufgabe 5.17
(a) Finden Sie einen weiteren minimalen Spannbaum des Beispielgraphen aus Ab-
bildung 5.16.
(b) Finden Sie einen maximalen Spannbaum des Beispielgraphen aus Abbildung
5.16.
2Ein einfacher Beweis ¨uber Widerspruch: Angenommen solch eine kosteng ¨unstigste Verbindung
w¨urde einen Kreis enthalten; entfernt man aber eine Kante emit w(e) >0 aus diesem Kreis, so ist der
Graph immer noch zusammenh¨angend, verbindet also alle Knoten miteinander, und hat ein geringeres
Gewicht. Folglich war diese urspr¨ungliche Verbindungsm¨oglichkeit auch nicht die kosteng¨unstigste; was
ein Widerspruch zur Annahme ist. Die kosteng¨unstigste Verbindungsm¨oglichkeit kann also keinen Kreis
enthalten.

## Seite 185

170 5 Graphalgorithmen
1
3
2
2
2
4
5
6
1
7
8
9
3
31
2
4
3 1
1
1
5
(a)
1
3
22
4
5
6
7
8
9
3 2
4
3 1
1
5
11 3 1
2
(b)
Abb. 5.16: Ein ungerichteter gewichteter Beispielgraph zusammen mit einem minimalen
Spannbaum.
Es gibt wichtige Anwendungen f ¨ur dieses Problem. Wir geben zwei Beispiele hierf ¨ur
an. 1: Das Finden eines m¨oglichst preisg¨unstigen zusammenh¨angenden Netzwerkes. Die
Kantengewichte geben hierbei jeweils Auskunft dar¨uber, wie teuer es ist, zwischen zwei
Orten eine Netzwerkverbindung zu installieren. Die Suche nach einem minimalen Spann-
baum w¨urde dann der Suche nach der kosteng ¨unstigsten Netzwerkinstallation entspre-
chen, die alle Teilnehmer verbindet.
2: F¨ur einige Netzwerkprotokolle stellt es ein Problem dar, wenn es mehrere m ¨ogliche
Pfade f¨ur das Versenden eines Datenpaketes von einem Netzknoten izu einem anderen
Netzknoten j gibt. In bestimmten Netzwerken k ¨onnen aus dieser Redundanz Inkonsi-
stenzen entstehen. Um solche redundanten Pfade zu vermeiden, muss ein Spannbaum
(vorzugsweise ein minimaler Spannbaum) ¨uber alle beteiligten Netzwerkknoten gefun-
den werden.
5.4.2 Der Algorithmus von Kruskal
Der Kruskal-Algorithmus verwendet eine typische Greedy-Strategie: ”gr¨oßere“ L¨osun-
gen werden schrittweise aus ”kleineren“ L¨osungen aufgebaut. In jedem dieser Schritte
wird eine L ¨osung immer aus der in diesem Moment am besten erscheinenden Erwei-
terung angereichert. Im Falle des Kruskal-Algorithmus sieht diese Strategie konkret
folgendermaßen aus: In jedem Schritt wird immer diejenige Kante mit dem minimalen
Gewicht zur Menge der Kanten hinzugef ¨ugt, die am Ende den minimalen Spannbaum
bilden sollen – jedoch nur dann, wenn durch dieses Hinzuf ¨ugen kein Kreis entsteht (ein
Spannbaum muss ja ein zusammenh ¨angender kreisfreier Teilgraph sein; siehe hierzu
auch Anhang B.4.1). Abbildung 5.17 zeigt ein Beispiel f ¨ur den Ablauf des Kruskal-
Algorithmus auf einem Beispielgraphen.
Korrektheit. Die folgenden beiden Eigenschaften (mit Hilfe derer die Korrektheit des
Kruskal-Algorithmus leicht zu zeigen ist) gelten f ¨ur jeden minimalen Spannbaum.
1. Die Kreiseigenschaft. Sei C ein beliebiger Kreis und e eine Kante aus C mit
maximalem Gewicht. Dann gilt, dass der minimale Spannbaum e nicht enth¨alt.
Beweis: Wir nehmen an, e w¨are im minimalen Spannbaum enthalten. Entfernen wir
e, so zerf ¨allt der Spannbaum in zwei Komponenten K und K′. In C gibt es jedoch
(da C ein Kreis ist) eine andere Kante e′, die K und K′miteinander verbindet. Durch
Wahl von e′erhalten wir also wiederum einen Spannbaum. Da w(e) >w(e′) hat jedoch
der neue Spannbaum ein geringeres Gewicht als der urspr ¨ungliche; somit konnte der
urspr¨ungliche Spannbaum nicht minimal gewesen sein.

## Seite 186

5.4 Minimaler Spannbaum 171
1
3
2
2
2
4
5
6
7
8
9
3
31
2
4
3 1
1
1
5
1
(a)
1
3
2
2
2
4
5
6
7
8
9
3
31
2
4
3 1
1
1
5
1
(b)
1
3
2
2
2
4
5
6
7
8
9
3
31
2
4
3 1
1
5
1 1
(c)
1
3
2
2
2
4
5
6
7
8
9
3
31
2
4
3
1
5
1 1
1
(d)
1
3
2
2
2
4
5
6
7
8
9
3
3
2
4
3
1
5
1 1
1
1
(e)
1
3
2
2
2
4
5
6
7
8
9
3
3
2
4
3
1
5
1 1
1
1
(f)
1
3
22
4
5
6
7
8
9
3 2
4
3
1
5
1 1
1
1
2
3
(g)
1
3
22
4
5
6
7
8
9
3 2
4
3
1
5
1 1
1
1
2
3
(h)
Abb. 5.17:Ablauf des Kruskal-Algorithmus f ¨ur den Beispielgraphen aus Abbildung 5.16. Wie
man sieht, wird in jedem Schritt immer diejenige Kante (aus der Menge der verbleibenden
Kanten) ausgew¨ahlt die das minimale Gewicht besitzt und die zusammen mit den bisher aus-
gew¨ahlten Kanten keinen Zyklus bildet. Zun ¨achst werden im Beispiel alle Kanten mit Gewicht
1 ausgew¨ahlt; anschließend wird mit den Kanten mit Gewicht 2 fortgefahren. In Schritt 5.17(h)
wird jedoch die Kante mit minimalem Gewicht (2,5) nicht ausgew ¨ahlt, da sie zusammen mit
den bisher ausgew ¨ahlten Kanten einen Zyklus bilden w ¨urde. Stattdessen muss eine Kante mit
Gewicht 3 ausgew ¨ahlt werden – in diesem konkreten Fall wird (6,7) gew¨ahlt; es w ¨are aber hier
ebenso m¨oglich gewesen die Kante (1,4) auszuw¨ahlen.
w(e) >w(e′) ⇒w(T) >w(T′)
e
e′
e
e′
T T′
Abb. 5.18: Durch Ersetzen der Kante e mit maximalem Gewicht durch die ”kleinere“ Kante
e′ entsteht ein ”kleinerer“ Spannbaum T′.
2. Die Schnitteigenschaft. Sei S eine beliebige Teilmenge von Knoten. Es sei edieje-
nige Kante mit minimalem Gewicht, die genau einen Endpunkt in S besitzt. Dann gilt,
dass der minimale Spannbaum e enthalten muss.
Beweis: Wir nehmen an, e w¨are im minimalen Spannbaum nicht enthalten. F¨ugen wir
nun die Kante e dem Spannbaum hinzu, so erhalten wir einen Kreis C. Entfernen wir
nun eine andere Kante e′mit genau einem Endpunkt in S aus dem Kreis C, so erhalten

## Seite 187

172 5 Graphalgorithmen
wir wiederum einen Spannbaum, der jedoch ein geringeres Gewicht als der urspr ¨ungli-
che Spannbaum hat (da w(e′) >w(e)); der urspr¨ungliche Spannbaum konnte also nicht
minimal gewesen sein.
e
e′
Se
e′
S
T
w(e′) <w(e) ⇒w(T′) <w(T)
T′
Abb. 5.19: Durch Ersetzen der Kante e′ mit nicht minimalem Gewicht durch die ”kleinere“
Kante e entsteht ein ”kleinerer“ Spannbaum T′.
Mit Hilfe dieser beiden Eigenschaften k ¨onnen wir zeigen, dass jede Kante, die vom
Kruskal-Algorithmus ausgew¨ahlt wird, tats¨achlich zum minimalen Spannbaum geh¨oren
muss. Wir unterscheiden zwei F¨alle:
1. Angenommen, die ausgew¨ahlte Kante eerzeugt einen Kreis C. Da alle anderen Kan-
ten dieses Kreises zu einem fr ¨uheren Zeitpunkt ausgew¨ahlt wurden, ist edie Kante mit
maximalem Gewicht in C, kann also nicht zum minimalen Spannbaum geh ¨oren, wird
also vom Kruskal-Algorithmus zu Recht nicht ausgew¨ahlt.
2. Angenommen, die ausgew¨ahlte Kante e= {i,j}erzeugt keinen Kreis. Sei K die Men-
ge der Knoten der (Zusammenhangs-)Komponente der i angeh¨ort. Die Kante e besitzt
genau einen Endpunkt in K und ist gleichzeitig die Kante mit minimalem Gewicht, die
genau einen Endpunkt in K hat, wird also nach der Schnitteigenschaft zu Recht vom
Kruskal-Algorithmus ausgew¨ahlt.
Implementierung. Listing 5.7 zeigt eine einfache Implementierung des Kruskal-Algo-
rithmus.
1 def kruskal(graph):
2 allEdges = [(graph.w(i ,j ), i , j) for i , j in graph.E undir()]
3 allEdges . sort(reverse=True) # absteigend sortieren
4 spannTree= []
5 while len(spannTree)< len(graph.V())-1 and allEdges̸=[]:
6 (w,i , j) = allEdges.pop()
7 if not buildsCircle(spannTree,(i, j )):
8 spannTree.append((i,j))
9 return spannTree
Listing 5.7: Einfache Implementierung des Kruskal-Algorithmus
Mittels der Listenkomprehension in Zeile 2 wird die Liste allEdges aller Kante inklu-
sive ihrer Gewichte erzeugt und in Zeile 3 nach ihren Gewichten absteigend sortiert.
In jedem while-Schleifendurchlauf wird dann mittels allEdges .pop() immer diejenige
noch nicht betrachtete Kante mit minimalem Gewicht ausgew¨ahlt und genau dann zum
Spannbaum spannTreehinzugef¨ugt, falls dadurch kein Kreis erzeugt wird.

## Seite 188

5.4 Minimaler Spannbaum 173
Zwei Punkte sind jedoch an dieser Implementierung zu bem ¨angeln bzw. unvollst¨andig:
1: Das Sortieren aller Kanten nach deren Gewicht hat eine Laufzeit von O(|E|log |E|)
und ist damit ineﬃzienter als die Verwendung einer Heap-Struktur: Der Aufbau des
Heaps ben¨otigt O(|E|) Schritte; es werden jedoch nur |V|−1 Elemente aus dem Heap
entnommen und wir erhalten daher eine Laufzeit von O(|E|+|V|log |E|); f¨ur den h¨auﬁ-
gen Fall, dass |E|≫| V|ist dies wesentlich g¨unstiger als die Laufzeit von O(|E|log |E|).
Zur Implementierung siehe Aufgabe 5.18.
2: Wir haben in Listing 5.7 oﬀen gelassen, wie die Funktion buildsCircle zu imple-
mentieren ist, die testet, ob durch das Hinzuf ¨ugen der Kante ( i , j) zur Kantenmenge
spannTreeein Kreis entsteht. Es w ¨are m¨oglich diesen Test mit Hilfe einer Tiefensuche
durchzuf¨uhren; es geht jedoch schneller ¨uber eine sog. Union-Find-Datenstruktur.
Aufgabe 5.18
Eine verbesserte Implementierung des Kruskal-Algorithmus w ¨urde es vermeiden die
gesamte Kantenmenge zu sortieren, sondern stattdessen einen Heap verwenden, um
in jedem Durchlauf eﬃzient die Kante mit dem minimalen Gewicht auszuw ¨ahlen.
Passen Sie die Implementierung des in Listing 5.7 gezeigten Skripts entsprechend an.
Aufgabe 5.19
Implementieren Sie eine Funktion buildsCircle ( tree ,( i , j )), die testet, ob der Graph
graph einen Zyklus enth¨alt. Verwenden Sie hierzu als Basis eine Tiefensuche.
Aufgabe 5.20
Welche Laufzeit hat die in Listing 5.7 gezeigte Implementierung des Kruskal-Algo-
rithmus, falls buildsCircle ¨uber eine Tiefensuche implementiert wird und . . .
(a) . . . die Kante mit dem geringsten Gewicht durch eine entsprechende Sortierung
der Kantenmenge erhalten wird.
(b) . . . die Kante mit dem geringsten Gewicht durch Aufbau einer Heapstruktur¨uber
die Kantenmenge erhalten wird.
Aufgabe 5.21
(a) Kann man den minimalen Spannbaum auch ﬁnden, indem man genau umgekehrt
wie der Kruskal-Algorithmus vorgeht, d. h. man beginne mit allen im Graphen
enthaltenen Kanten und entfernt Kanten mit dem momentan h ¨ochsten Gewicht
– aber nur dann, wenn man dadurch den Graphen nicht auseinanderbricht?
(b) Geben Sie eine Implementierung des ”umgekehrten“ Kruskal-Algorithmus an.

## Seite 189

174 5 Graphalgorithmen
5.4.3 Union-Find-Operationen
¨Uber eine eﬃziente Implementierung der sog. Union-Find-Operationen, d. h. der Men-
genoperationen ”Vereinigung“ zweier Mengen und ”Suche“ eines Elementes in einer
Menge, erh ¨alt man sogleich eine eﬃziente Methode zum Testen, ob durch das Hin-
zuf¨ugen einer Kante {i,j}zu einer kreisfreien Kantenmenge S ein Zyklus entsteht;
genau dieser Test muss im Verlaufe des Kruskal-Algorithmus wiederholt durchgef ¨uhrt
werden.
Die eﬃzientesten Implementierungen der Union-Find-Operationen modellieren die Men-
genzugeh¨origkeit durch Graphen und sehen die Relation ”geh¨ort zur selben Menge wie“
im Graphen modelliert als ”geh¨ort zur selben (Zusammenhangs-)Komponente wie“.
In einer Union-Find-Datenstruktur wird eine Menge von Objekten v1,...v n verwaltet.
Anfangs sieht man die Objekte als einelementige Mengen. Im Verlauf der Benutzung
der Datenstruktur k¨onnen die Mengen vereinigt werden; es wird also immer eine Men-
ge von disjunkten 3 Teilmengen verwaltet. Es werden die folgende beiden Operationen
unterst¨utzt:
 ﬁnd(v): Diese Funktion liefert eine eindeutige Repr ¨asentation derjenigen Menge
zur¨uck, zu der v geh¨ort.
 union(x,y): Vereinigt die beiden Mengen, deren eindeutige Repr¨asentationen x und
y sind.
Abbildung 5.20 zeigt ein Beispiel f¨ur den Aufbau einer Union-Find-Datenstruktur; diese
spezielle Folge von Vereinigungsschritten w ¨urde sich w ¨ahrend der in Abbildung 5.17
gezeigten Ausf¨uhrung des Kruskal-Algorithmus ergeben.
Mit der Union-Find-Datenstruktur kann man w ¨ahrend der Ausf ¨uhrung des Kruskal-
Algorithmus protokollieren, welche Zusammenhangskomponenten sich aus dem bisher
berechneten (Teil-)Spannbaum ergeben; aus dieser Information wiederum kann man
in jedem Schritt des Kruskal-Algorithmus leicht nachpr ¨ufen, ob durch das Hinzuf ¨ugen
einer Kante ein Kreis entsteht. Zu Beginn enth ¨alt spannTree keine Kanten, alle Kno-
ten stehen daher einzeln da und spannTreehat folglich 9 Zusammenhangskomponenten.
Dies entspricht dem in Abbildung 5.20 gezeigten Anfangszustand. In jedem Schritt wird
durch den Kruskal-Algorithmus nun die Kante {i , j}mit dem geringsten Gewicht aus-
gew¨ahlt. Es gibt zwei F ¨alle:
1. Es gilt ﬁnd(i)==ﬁnd(j). D. h. i und j beﬁnden sich schon in derselben Zusammen-
hangskomponente (d. h. es gibt in spannTreeeinen Weg von i nach j). Ein Hinzuf¨ugen
der Kante {i , j}w¨urde daher einen Kreis entstehen lassen.
2. Es gilt ﬁnd(i)̸= ﬁnd(j). D. h. das Hinzuf ¨ugen der Kante {i , j}w¨urde zwei bisher
getrennte Komponenten verbinden, d. h. spannTree w¨urde kreisfrei bleiben. Der Al-
gorithmus w ¨urde also die Kante zu spannTree hinzuf¨ugen und durch Ausf ¨uhren von
union(ﬁnd(i ), ﬁnd(j )) in der Union-Find-Datenstruktur protokollieren, dass sich nun
i und j in der gleichen Komponente (bzw. Menge) beﬁnden.
3Die Mengen M1 und M2 heißen disjunkt, wenn sie keine gemeinsamen Elemente besitzen, d. h.
wenn Ihr Schnitt gleich der leeren Menge ist. In Formeln: wenn M1 ∩M2 = ∅gilt.

## Seite 190

5.4 Minimaler Spannbaum 175
(d):ﬁnd(4) ∪ﬁnd(8)
(c):ﬁnd(7) ∪ﬁnd(9)
(f):ﬁnd(1) ∪ﬁnd(3)
(g):ﬁnd(2) ∪ﬁnd(1)
(h):ﬁnd(6) ∪ﬁnd(7)
(e):ﬁnd(5) ∪ﬁnd(6)
(a):ﬁnd(3) ∪ﬁnd(6)
(b):ﬁnd(8) ∪ﬁnd(9)
1 2 3 4 5 6 7 8 9
1 2 3 4 5 7 8 9
6
1 2 3 4 5 7 8
6 9
1 2 3 4 5
6
7
8
9
1 2 3
6
5
8
9
4
7
3
6
5
1
2
1 2 5
3
6
7
8
9
4
7
8
9
4
7
8
9
4
3
6
5
1 2
7
8
9
4
3
6
5
1 2
Abb. 5.20: Ein Beispiel f ¨ur den Aufbau einer Union-Find-Datenstruktur. Es werden 9 Ele-
mente verwaltet, die zu Beginn einzeln stehen. Wie man sieht, wird die Mengenzugeh ¨origkeit
durch die Union-Find-Datenstruktur als Menge von B ¨aumen repr¨asentiert. Beﬁnden sich zwei
Elemente im selben Baum, so heißt dies, dass die beiden Elemente derselben Menge angeh ¨oren.
Nach jedem union-Schritt werden (falls die zu vereinigenden Elemente sich in verschiedenen
Mengen beﬁnden) zwei B ¨aume miteinander verschmolzen. Beispielsweise wird in Schritt (d)
die Menge, der 4 angeh ¨ort (also ﬁnd (4)), was in diesem Falle einfach der Menge {4}ent-
spricht, vereinigt mit der Menge, der 8 angeh ¨ort (also ﬁnd (8), was in diesem Falle der Menge
{7,8,9}entspricht); als Folge werden die beiden entsprechenden B ¨aume verschmolzen. Man
beachte, dass dieser ”Verschmelzungsprozess“ nicht eindeutig ist. Es gibt immer zwei M ¨oglich-
keiten, wie zwei B ¨aume B1 und B2 miteinander verschmolzen werden k ¨onnen: Entweder man
h¨angt B1 als Kind unter die Wurzel von B2 oder man h¨angt B2 als Kind unter die Wurzel von
B1.
Angenommen uf sei eine Instanz der Klasse UF (deren Implementierung wir weiter un-
ten in Listing 5.8 pr ¨asentieren), erzeugt mittels
uf = UF(graph.numNodes)
Wir sollten also die Zeilen 7 und 8 in Listing 5.7 folgendermaßen ersetzen:
7 if not buildsCircle(spannTree,(i, j )):
8 spannTree.append((i,j)) =⇒
7 Mi = uf.ﬁnd(i)
8 Mj = uf.ﬁnd(j)
9 if Mi ̸=Mj:
10 spannTree.append((i,j))
11 uf.union(Mi,Mj)
Um festzustellen, ob durch Hinzunahme der Kante {i , j}ein Kreis entsteht, wird also
gepr¨uft, ob i und j zur selben Menge geh ¨oren. Ist dies nicht der Fall (falls n ¨amlich
Mi̸=Mj), so wird die Kante {i , j}zum Spannbaum hinzugef¨ugt (Zeile 10) und anschlie-
ßend die Menge, der j angeh¨ort, und die Menge, der i angeh¨ort, vereinigt (Zeile 11).
Listing 5.8 zeigt die Implementierung der Klasse UF.

## Seite 191

176 5 Graphalgorithmen
1 class UF(object):
2 def init ( self ,n):
3 self .parent = [0] *n
4 def ﬁnd( self ,x):
5 while self .parent[x ] > 0: x = self .parent[x ]
6 return x
7 def union(self ,x,y):
8 self .parent[y] = x
Listing 5.8: Implementierung der Union-Find-Datenstruktur.
Eine Kante in dem ”Wald“ der durch die Union-Find-Datenstruktur dargestellt wird,
wird durch die Liste parent repr¨asentiert. Der i-te Eintrag in parent enth¨alt den Vater
des Knotens i. Falls parent[i ] gleich 0 ist, heißt dies, dass i die Wurzel des Baumes ist.
Initial werden alle parent-Eintr¨age auf 0 gesetzt (Zeile 3), d. h. alle verwalteten Elemente
sind Wurzeln, d. h. initial haben wir es mit einem Wald ausn B¨aumen zu tun, die jeweils
nur ein Element (n¨amlich das Wurzelelement) enthalten. Ein Aufruf vonunion(x,y) f¨ugt
zwei B¨aume zusammen, indem die Wurzel des einen Baumes (der y enth¨alt) als Kind
unter die Wurzel des anderen Baumes (der x enth¨alt) geh¨angt wird. Der Aufruf ﬁnd(x)
liefert die Wurzel des Baumes zur ¨uck, der x enth¨alt.
Aufgabe 5.22
Implementieren Sie f¨ur die in Listing 5.8 gezeigte Klasse UF die str-Funktion, die ein
Objekt der Klasse in einen String umwandelt. Die Ausgabe sollte gem ¨aß folgendem
Beispiel erfolgen:
>>>uf = UF(10)
>>>uf.union(1,2) ; uf.union(1,3) ; uf.union(5,6) ; uf.union(8,9)
>>> str(uf)
>>>'{1, 2, 3} {4} {5, 6} {7} {8, 9} '
Wir betrachten zwei M¨oglichkeiten, die Union-Find-Datenstruktur zu optimieren:
Balancierung. Im ung¨unstigsten Falle entwickeln sich in der Union-Find-Datenstruk-
tur entartete (d. h. stark unbalancierte) B¨aume. Ein ung¨unstiger Fall tritt immer dann
ein, wenn ein Baum der H ¨ohe h unter die Wurzel eines Baumes mit geringerer H ¨ohe
h′ geh¨angt wird, d. h. wenn union(x,y) ausgef¨uhrt wird, und die H ¨ohe des Baumes, in
dem sich x beﬁndet kleiner ist als die H ¨ohe des Baumes, in dem sich y beﬁndet. Wir
k¨onnen dies einfach dadurch vermeiden, indem wir pr¨ufen, welcher Baum h¨oher ist. Wir
wollen aus Performance-Gr¨unden vermeiden, wiederholt die H¨ohe zu berechnen. Daher
speichern wir immer die H ¨ohe jedes Baumes im parent-Eintrag der Wurzel – jedoch als
negative Zahl, um weiterhin in der Lage zu sein, die Wurzel eines Baumes ”erkennen“
zu k¨onnen. Damit bleibt auch die while-Schleife in Listing 5.8 in Zeile 5 g ¨ultig.

## Seite 192

5.4 Minimaler Spannbaum 177
Aufgabe 5.23
Verbessern Sie die in Abbildung 5.8 gezeigte Implementierung dadurch, dass Sie auf
die Balancierung der in der Union-Find-Datenstruktur verwalteten B ¨aume achten.
Der Baum ﬁnd(x) sollte also nur dann als Kind unter die Wurzel des Baums ﬁnd(y)
geh¨angt werden, wenn die H ¨ohe von ﬁnd(x) kleiner ist als die H ¨ohe von ﬁnd(y);
andernfalls sollte ﬁnd(y) unter die Wurzel von ﬁnd(x) geh¨angt werden.
Pfad-Komprimierung. Ein Aufruf von ﬁnd(x) ﬁndet immer den Pfad vonx zur Wur-
zel des Baumes in dem sichx beﬁndet. Nach solch einem Aufruf ist es g¨unstig eine direkte
Kante von x zur Wurzel einzuf¨ugen, um bei einem sp¨ateren erneuten Aufruf von ﬁnd(x)
zu vermeiden, dass wiederum der gleiche Pfad bis zur Wurzel gelaufen werden muss.
Diese Technik nennt man Pfadkomprimierung. Zur Implementierung der Pfadkompri-
mierung muss lediglich die ﬁnd-Methode der Klasse UF angepasst werden. Listing 5.9
zeigt die Implementierung der ﬁnd-Methode, die zus ¨atzlich eine Pfadkomprimierung
durchf¨uhrt.
1 class UF(object):
2 ...
3 def ﬁnd( self ,x):
4 i=x
5 while self .parent[x ] > 0: x = self .parent[x ]
6 while self .parent[i ] > 0:
7 tmp=i ; i=self.parent[i ] ; self .parent[tmp]=x
8 return x
Listing 5.9: Implementierung der Pfadkomprimierung in der ﬁnd-Methode.
Zun¨achst wird, wie in der urspr¨unglichen Implementierung der ﬁnd-Methode, die Wur-
zel des als Parameter ¨ubergebenen Elements x gesucht. Anschließend wird in den Zeilen
6 und 7 der gegangene Pfad nochmals abgelaufen und die parent-Eintr¨age aller Kno-
ten auf diesem Pfad direkt auf die Wurzel x des Baumes gesetzt. Dadurch wird eine
Erh¨ohung der Laufzeit f ¨ur sp¨atere ﬁnd-Aufrufe erm¨oglicht.
Laufzeit. Obwohl die Funktionsweise der Union-Find-Datenstruktur verh ¨altnism¨aßig
einfach nachvollziehbar ist, ist eine Laufzeitanalyse komplex. Wir beschr¨anken uns hier
deshalb darauf, lediglich die Ergebnisse der Laufzeitanalyse zu pr ¨asentieren. Die Kom-
bination der beiden vorgestellten Optimierungen, Pfad-Komprimierung und Balancie-
rung, erm¨oglicht eine (zwar nicht ganz, aber nahezu) lineare Laufzeit f¨ur die Erzeugung
eine Union-Find-Datenstruktur aus |E|Kanten.
Damit ergibt sich f ¨ur den Kruskal-Algorithmus eine Laufzeit von O(|E|log(|E|)): Die
while-Schleife wird im ung¨unstigsten Fall |E|mal ausgef¨uhrt; in jedem Durchlauf wird
die Kante mit dem geringsten Gewicht aus der Heap-Struktur entfernt, was O(log(|E|))
Schritte ben ¨otigt; insgesamt ergibt sich daraus die Laufzeit von O(|E|log(|E|)). Die
Tests auf Entstehung der Kreise brauchen insgesamt (wie eben erw¨ahnt) O(|E|) und der

## Seite 193

178 5 Graphalgorithmen
anf¨angliche Aufbau des Heaps ebenfalls O(|E|) Schritte (was aber durch O(|E|log(|E|))
”geschluckt“ wird).
Aufgabe 5.24
Schreiben Sie die folgenden Funktionen, um Performance-Tests auf dem Kruskal-
Algorithmus durchzuf¨uhren:
(a) Schreiben Sie eine Funktion genRandGraph(n,m,k), die einen zuf¨alligen Graphen
G= (V,E) generiert mit |V|= n, |E|= m und w: E →{1,...,k }.
(b) Testen Sie nun die Laufzeit des Kruskal-Algorithmus auf einem Graphen
genGraph(1000,5000,1000), dessen Implementierung . . .
1. . . . die Kanten sortiert (statt Heaps zu verwenden) und die Tiefensuche
verwendet.
2. . . . die Kanten sortiert und statt der Tiefensuche eine einfache Union-Find-
Struktur verwendet.
3. . . . die Kanten sortiert und eine optimierte Union-Find-Struktur verwendet.
4. . . . Heaps verwendet und eine optimierte Union-Find-Struktur verwendet.
5.5 Maximaler Fluss in einem Netzwerk.
Wir behandeln hier in diesem Abschnitt eine sowohl in wirtschaftswissenschaftlichen als
auch in naturwissenschaftlichen Kontexten h¨auﬁg auftretende Fragestellung. Es geht um
das Problem, wie und wie viel”Material“ (das kann je nach Kontext Waren, Mitarbeiter,
elektrischer Strom oder eine Fl ¨ussigkeit sein) durch ein Netzwerk von Knoten gelenkt
werden kann.
5.5.1 Netzwerke und Fl ¨usse
Ein Netzwerk ist ein gewichteter gerichteter Graph G = (V,E ) mit Gewichtsfunktion
w: E →R +, d. h. jeder Kante ist eine positive reelle Zahl zugeordnet. Wir interpretieren
die einer Kante zugeordnete Zahl als Kapazit¨at. Diese Kapazit ¨at sagt uns, wie viel
Material (bzw. Strom, Fl ¨ussigkeit, usw.) maximal ¨uber diese Kante ”ﬂießen“ kann. Es
seien zwei Kanten s,t ∈V speziell ausgezeichnet und wir nennen s die Quelle und t
die Senke des Netzwerkes. Außerdem sei ein Fluss gegeben, modelliert als Funktion
f : V ×V →R +, der die folgenden Bedingungen erf ¨ullen sollte:
1. Aus der Kapazit ¨at ergibt sich die maximal m ¨oglich Menge ”Material“, die ¨uber
eine Kante ﬂießen kann, d. h.
f(u,v) ≤w(u,v) f¨ur alle (u,v) ∈E

## Seite 194

5.5 Maximaler Fluss in einem Netzwerk. 179
2. Der Fluss in R ¨uckw¨artsrichtung hat immer den negativen Wert des Flusses in
Vorw¨artsrichtung, d. h.
f(u,v) = −f(v,u) f¨ur alle (u,v) ∈E
3. Das ”Material“, das in einen Knoten hineinﬂießt, muss auch wieder hinausﬂießen,
d. h.
F¨ur jeden Knoten v∈V \{s,t }muss gelten:
∑
u∈V
f(u,v) = 0
Diese Bedingung wird manchmal auch als das Kirchhoﬀ’sche Gesetz oder das
Gesetz der Flusserhaltung bezeichnet. Wir wollen also ein Szenario modellieren,
in dem alle Knoten (ausgenommensund t) lediglich das hineinﬂießende”Material“
weitergeben, also weder ”Material“ konsumieren, noch neues ”Material“ erzeugen
k¨onnen. Lediglich die Quelle skann ”Material“ produzieren und die Senke tkann
”Material“ konsumieren.
Aufgabe 5.25
Warum hat die den Fluss modellierende Funktion f nicht den ”Typ“ f : E →R +,
sondern den Typ f : V ×V →R +?
Der Wert eines Flusses ist deﬁniert als ∑
u∈V f(s,u) also die Menge an Material, die
von der Quelle erzeugt wird. Da f¨ur alle Knoten (aus sund t) Flusserhaltung gilt, muss
genau dieser Fluss auch bei der Senke wieder ankommen, d. h. es muss gelten, dass∑
u∈V f(s,u) = ∑
u∈V f(u,t). In vielen Anwendungen ist der maximal m ¨ogliche Fluss
gesucht, d. h. die maximal m¨ogliche Menge an Material, die (unter Ber¨ucksichtigung der
Kapazit¨aten der Kanten) durch ein Netzwerk geschleust werden kann. Abbildung 5.21
zeigt ein Beispiel, das zeigt, wie man sich diesem maximalen Fluss ann ¨ahern kann.
5.5.2 Der Algorithmus von Ford-Fulkerson
Die Idee des sog. Algorithmus von Ford-Fulkerson ist recht einfach und schon in Ab-
bildung 5.21 angedeutet: Solange es einen Pfad von der Quelle zur Senke gibt, mit
noch verf ¨ugbarer Kapazit ¨at auf allen Kanten des Pfades, so schicken wir (m ¨oglichst
viel) ”Material“ ¨uber diesen Pfad. Genauer: Wurde im letzten Schritt ein g ¨ultiger
Fluss f des Netzwerks G = (V,E ) (mit Kapazit ¨atsfunktion w) gefunden, so wird im
n¨achsten Schritt zun ¨achst das sog. Restnetzwerk Gf = (V,E f) berechnet, das man
einfach aus dem ”alten“ Netzwerk G durch Berechnung der neuen Kapazit ¨atsfunktion
wf(i,j) = w(i,j) −f(i,j)4 erh¨alt. Anschließend versucht der Algorithmus in Gf einen
Pfad pvon snach tin Gf zu ﬁnden, so dass wf(i,j) >0 f¨ur alle (i,j) ∈p; einen solchen
Pfad nennt man auch Erweiterungspfad. Gibt es keinen Erweiterungspfad, so bricht der
4Es kann hierbei sogar passieren, dass das Restnetzwerk Gf einen Fluss von j nach ierlaubt, auch
wenn G keinen Fluss von j nach i erlaubt hatte: Falls f(i,j) > 0 und w(j,i) = 0 dann ist n ¨amlich
wf (j,i) = w(j,i) −f(j,i) = −f(j,i) = f(i,j) > 0; die R ¨uckrichtung hat somit in Gf eine positive
Kapazit¨at und ein Fluss von j nach i w¨are in Gf m¨oglich.

## Seite 195

180 5 Graphalgorithmen
0/10
0/12
0/100/5
0/5
0/10 0/5
1
2
3
4
5
6
0/12
(a) Fluss mit Wert 0.
0/5
0/510/10
10/10
10/12
5/5
5/10
1
2
3
4
5
6
5/12
(b) Verbesserter Fluss mit
Wert 15.
10/10 10/12
5/5
5/5
5/10
5/5
10/10
1
2
3
4
5
6
10/12
(c) Der maximale Fluss mit
Wert 20.
Abb. 5.21:Drei verschiedene sukzessiv vergr¨oßerte Fl¨usse in einem Netzwerk. Wie man sieht
kann man aus dem ”leeren“ Fluss (dargestellt in Abbildung 5.21(a)) relativ einfach einen Fluss
mit Wert 15 generieren: ¨Uber den Pfad (1,3,5,6) kann man einen Fluss mit Wert 10 (ent-
sprechend dem minimalen Kantengewicht auf diesem Pfad) ﬂießen lassen und ¨uber den Pfad
(1,2,4,6) kann man einen Fluss mit Wert 5 (wiederum entsprechend dem minimalen Kan-
tengewicht auf diesem Pfad) ﬂießen lassen; dies ergibt zusammengenommen den in Abbildung
5.21(b) gezeigten Fluss mit Wert 10+5=15. Nicht ganz so oﬀensichtlich ist die in Abbildung
5.21(c) gezeigte M ¨oglichkeit, diesen Fluss zu vergr ¨oßern. ¨Uber den Pfad (1,2,5,3,4,6) kann
man einen zus ¨atzlichen Fluss mit Wert 5 schicken; man beachte, dass dieser Pfad die Kante
(5,3) beinhaltet, also die im urspr ¨unglichen Graphen vorhandenen Kante (3,5) in R¨uckw¨arts-
richtung durchlaufen wird. Laut Bedingung 2 gilt f¨ur den Fluss aus Abbildung 5.21(b) ¨uber diese
Kante: f(3,5) = −f(5,3) = −10; dieser Fluss ¨uber diese Kante auf dem Pfad (1,2,5,3,4,6)
kann von -10 auf den Wert -5 vergr ¨oßert werden. Insgesamt ergibt sich also ein Fluss mit Wert
20, dargestellt in Abbildung 5.21(c).
Algorithmus ab und die bisher gefundenen Fl ¨usse zusammengenommen bilden einen
maximalen Fluss. Konnte dagegen ein Erweiterungspfad p gefunden werden, so wird
f¨ur alle Kanten ( i,j) ∈p der Fluss f′ auf den Wert min{wf(i,j) |(i,j) ∈p}gesetzt,
anschließend wieder das Restnetzwerk berechnet, usw.
Listing 5.10 zeigt die Implementierung in Python. In jedem Durchlauf derwhile-Schleife
wird zun¨achst der Fluss f ¨uber den (im letzten Schritt) berechneten Erweiterungspfad
path bestimmt; wie schon oben beschrieben entspricht der Wert dieses Flusses dem
minimalen in path beﬁndlichen Kantengewicht. Dieser Fluss f wird zum bisherigen Ge-
samtﬂuss ﬂow hinzuaddiert (Zeile 7). Anschließend wird in der for-Schleife (Zeile 9 bis
15) das Restnetzwerk graphf des zu Beginn der while-Schleife betrachteten Netzwerkes
graph berechnet, d. h. f¨ur jede Kante (i , j) ∈path m¨ussen die Kapazit¨aten entsprechend
des Flusses f folgendermaßen angepasst werden: Besitzt eine Kante ( i , j) im Graphen
graph die Kapazit ¨at w, so erh ¨alt diese im Graphen graphf die Kapazit ¨at w -f; falls
w -f == 0 (d. h. die Kapazit ¨at verschwindet), so wird die Kante mittels delEdge aus
dem Graphen entfernt. Der Grund daf ¨ur, dass wir die Kante in diesem Falle l ¨oschen,
liegt darin, dass im Falle von Netzwerken die Tatsache, dass eine Kante ( i , j) nicht
existiert gleichbedeutend ist mit der Tatsache, dass eine Kante ( i , j) die Kapazit ¨at 0
hat. Aus dem gleichen Grund weisen wir dem Gewicht der R ¨uckw¨artskante ( j , i) in
Zeile 11 den Wert 0 zu, falls diese nicht existiert. In den Zeilen 14 und 15 wird die
R¨uckw¨artskante entsprechend angepasst und – analog zur Vorw ¨artskante – gel ¨oscht,
falls deren Wert 0 wird.

## Seite 196

5.5 Maximaler Fluss in einem Netzwerk. 181
1 def maxFlow(s,t,graph):
2 path = ﬁndPath(s,t ,graph)
3 ﬂow = 0
4 while path ̸=[ ]:
5 # Bestimme gr¨oßtm¨oglichen Fluss ¨uber path
6 f = min(graph.w(i,j) for i , j in path)
7 ﬂow += f
8 # Restnetzwerk berechnen
9 for i , j in path:
10 w = graph.w(i,j)
11 wBack = graph.w(j,i) if graph.isEdge(j, i) else 0
12 if w -f == 0: graph.delEdge(i,j)
13 else: graph.addEdge(i,j,w -f)
14 if wBack +f == 0: graph.delEdge(j,i)
15 else: graph.addEdge(j,i,wBack +f)
16 # Pfad im Restnetzwerk ﬁnden
17 path = ﬁndPath(s,t ,graph)
18 return ﬂow
Listing 5.10: Implementierung des Ford-Fulkerson-Algorithmus.
In Zeile 17 wird schließlich nach einem Erweiterungspfad von s nach t durch das eben
berechnete Restnetzwerk gesucht und mit diesem dann im n ¨achsten while-Schleifen-
durchlauf analog verfahren.
Dieser Algorithmus funktioniert im Allgemeinen gut. Gibt es aber mehrere Pfade von s
nach t dann kann es, abh¨angig davon welcher Pfad gew¨ahlt wird, zu einer sehr schlechten
Worst-Case-Laufzeit kommen. Im ung¨unstigsten Fall kann die Laufzeit sogar vom Wert
des gr ¨oßten Flusses selbst abh ¨angen. Abbildung 5.22 zeigt ein Beispiel eines solchen
problematischen Falles. Man kann zeigen, dass dieser ung¨unstige Fall einfach vermieden
werden kann, indem man als Erweiterungspfad grunds ¨atzlich einen Pfad mit m ¨oglichst
wenig Kanten w¨ahlt.
Aufgabe 5.26
F¨ur die in Listing 5.10 gezeigte Implementierung des Ford-Fulkerson-Algorithmus
wird eine Funktion ben ¨otigt, die eine Kante eines Graphen l ¨oschen kann – siehe
Zeilen 12 und 14.
F¨ugen Sie der Klasse Graph eine Methode delEdge(i, j) hinzu, die die Kante ( i , j)
aus dem Graphen l ¨oscht.

## Seite 197

182 5 Graphalgorithmen
0/100 0/100
1
2
3
0/1000/100
40/1
(a) Fluss mit Wert 0.
0/100 1/100
1
2
3
0/100
4
1/100
1/1
(b) Fluss mit Wert 1.
1/1001/100
1
2
3
4
1/100 1/100
0/1
(c) Fluss mit Wert 2.
Abb. 5.22: Dieses Beispiel zeigt einen ung ¨unstigen Verlauf des Ford-Fulkerson-Algorithmus,
der zwar letztendlich zum richtigen Ergebnis f ¨uhrt, jedoch eine (unn ¨otig) langen Laufzeit auf-
weist. Gesucht ist ein maximaler Fluss von der Quelle 1 zur Senke 4. Wird (1,2,3,4) als erster
Erweiterungspfad gew¨ahlt, so kann der Fluss nur um den Wert ”1“ verbessert werden (denn:
max(w(1,2),w(2,3),w(3,4)) = 1), gezeigt in Abbildung 5.22(b). Wird im n¨achsten Schritt der
g¨ultige Pfad (1,2,3,4) des Restnetzwerkes (das sich aus dem im vorigen Schritt gefundenen
Flusses ergibt) gew ¨ahlt, so kann der Fluss wiederum nur um den Wert ”1“ erh ¨oht werden,
gezeigt in Abbildung 5.22(c). Verf ¨ahrt man so weiter, so w ¨urde der Algorithmus 200 Schritte
ben¨otigen. Durch Wahl der Pfade (1,2,4) und (1,3,4) h¨atte man den maximalen Fluss aber in
lediglich zwei Schritten berechnen k ¨onnen.
Aufgabe 5.27
Implementieren Sie die in Zeile 17 in Listing 5.10 ben ¨otigte Funktion ﬁndPath, die
nach einem g¨ultigen Pfad von s nach t im Restnetzwerk sucht.
Hinweis: Um das in Abbildung 5.22 erw ¨ahnte Problem zu vermeiden, muss eine
Breitensuche verwendet werden – erkl¨aren Sie warum!
5.5.3 Korrektheit des Ford-Fulkerson-Algorithmus
Dass ein Erweiterungspfad p mit f(i,j) > 0 f ¨ur alle (i,j ) ∈p den bestehenden Fluss
verbessern kann, ist leicht einzusehen. Die entscheidende Frage ist aber: Falls es kei-
nen Erweiterungspfad mehr gibt, ist dann auch garantiert der maximal m ¨ogliche Fluss
gefunden? Dass diese Antwort ”Ja“ ist, ist nicht ganz so leicht einzusehen; dies kann
am einfachsten ¨uber einen ”Umweg“ gezeigt werden, der uns ¨uber das sog. Max-Flow-
Min-Cut-Theorem f¨uhrt. Dieses Theorem besagt, dass der maximale Fluss gleich dem
minimalen Schnitt des Netzwerkes ist, oder in anderen Worten: Es besagt, dass der
maximale Fluss genau gleich der Gr ¨oße des ”Flaschenhalses“ des Netzwerkes ist.
Deﬁnieren wir zun¨achst, was wir formal unter einem Schnitt (in einem Graphen) verste-
hen. Ein Schnitt eines Graphen G= (V,E) ist eine Knotenmenge S ⊂V. Die Kanten
des Schnittes sind deﬁniniert als
e(S) := {(i,j) ∈E |i∈S und j ∈V \S }
also als die Menge aller Kanten mit genau einem Endpunkt in S. Der Wert (bzw. die

## Seite 198

5.5 Maximaler Fluss in einem Netzwerk. 183
Kapazit¨at) eines Schnittes S ist deﬁniert als
w(S) :=
∑
e∈e(S)
w(e)
also als die Summe aller Gewichte (bzw. Kapazit ¨aten) aller im Schnitt enthaltenen
Kanten. Als s-t-Schnitt bezeichnet man einen Schnitt S, f¨ur den s ∈S und t ∈V \S
gilt. Der Fluss f(S) eines s-t-Schnittes S ist deﬁniert als die Summe der Fl ¨usse aller
Kanten des Schnittes, also f(S) := ∑
e∈e(S) f(e) Abbildung 5.23 zeigt ein Beispiel
eines Schnittes (der ¨ubrigens nicht der minimale Schnitt ist) in einem Graphen.
1
3
2
2
2
4
5
6
7
8
9
3
1
3 1
1
1
5
1 3
2
4
Abb. 5.23: Der Schnitt S = {4,5,6,7,8,9}durch einen Beispielgraphen.
Aufgabe 5.28
Betrachten Sie den in Abbildung 5.23 dargestellten Graphen und den Schnitt S und
beantworten Sie die folgenden Fragen:
(a) Geben Sie e(S) an, d. h. die zu dem Schnitt geh ¨orige Kantenmenge.
(b) Geben Sie w(S) an, d. h. die Kapazit¨at des Schnittes S.
Aufgabe 5.29
(a) Deﬁnieren Sie eine Python-Funktion cut(C,graph), die eine den Schnitt deﬁnie-
rende Knotenmenge C und einen Graphen graph ¨ubergeben bekommt und eine
Liste aller Kanten zur¨uckliefert die sich im Schnitt beﬁnden. Versuchen Sie eine
Implementierung als ”Einzeiler“, also in der Form
def cut(C,graph):
return ...
(b) Deﬁnieren Sie eine Python-Funktion cutVal(C,graph), die den Wert des Schnittes
zur¨uckliefert, der durch die KnotenmengeC deﬁniert ist. Versuchen Sie wiederum
eine Implementierung als Einzeiler.

## Seite 199

184 5 Graphalgorithmen
Man kann zeigen: F ¨ur jeden beliebigen s-t-Schnitt A eines Netzwerkes G = (V,E )
gilt immer, dass f(A) = f, d. h. egal welchen s-t-Schnitt durch das Netzwerk man
betrachtet, der Fluss des Schnittes hat immer den selben Wert, n¨amlich den des Flusses.
Diese Aussage kann man leicht durch Induktion ¨uber die Anzahl der Knoten im Schnitt
zeigen; wir ¨uberlassen den Beweis dem interessierten Leser.
Aufgabe 5.30
Zeigen Sie die eben aufgestellte Behauptung, die besagt dass – f ¨ur einen gegebenen
Fluss f – der Fluss jedes beliebigen Schnittes S immer denselben Wert hat.
Außerdem ist klar, dass f ¨ur jeden s-t-Schnitt Ades Netzwerkes gilt: f(A) ≤w(A), d. h.
f¨ur jeden Schnitt gilt, dass der Fluss des Schnittes kleiner oder gleich der Kapazit ¨at
des Schnittes ist, einfach deshalb, weil f¨ur jede einzelne Kante edes Schnittes gilt, dass
f(e) ≤w(e). Es ist aber nicht oﬀensichtlich, dass es immer einen Fluss und einen Schnitt
gibt, f¨ur die f(A) = w(A) gilt.
Endlich haben wir die Voraussetzungen, das Max-Flow-Min-Cut-Theorem zu beweisen.
Wir zeigen, dass die folgenden beiden Aussagen ¨aquivalent5 sind:
(1) f(A) = w(A) f¨ur einen s-t-Schnitt A und einen Fluss f.
(2) Es gibt keinen Erweiterungspfad von s nach t in Gf
K¨onnen wir zeigen, dass diese beiden Aussagen ¨aquivalent sind, haben wir die Kor-
rektheit des Ford-Fulkerson-Algorithmus gezeigt: Kann der Algorithmus keinen Erwei-
terungspfad mehr ﬁnden, so k ¨onnen wir sicher sein, dass der maximale Fluss gefunden
wurde.
Der Beweis gliedert sich in zwei Teile:
(1)⇒(2) Wir nehmen also an, f(A) = w(A). Im Restnetzwerk Gf gilt folglich, dass
wf(i,j) = 0 f ¨ur alle (i,j ) mit i ∈A und j ∈V \A. Folglich ist kein Knoten in
V \A von einem Knoten aus A aus erreichbar, insbesondere ist t nicht von s aus
erreichbar, d. h. es gibt keinen Erweiterungspfad von s nach t in Gf.
(2)⇒(1) Gibt es keinen Erweiterungspfad von snach tin Gf, so w¨ahle man A= {i∈
V |i ist von s aus erreichbar}, d. h. der Schnitt A bestehe aus allen von s aus
erreichbaren Knoten. F¨ur alle Knoten i∈Aund j ∈V \Amuss also wf(i,j) = 0
sein. Aus der Art und Weise wie das RestnetzwerkGf konstruiert wird, folgt auch,
dass wf(i,j) = w(i,j) −f(i,j). Also gilt w(i,j) −f(i.j) = 0 ⇔w(i,j) = f(i,j)
f¨ur alle Kanten (i,j ) ∈e(A). Also ist auch w(A) = f(A) = f und somit ist f der
maximal m¨ogliche Fluss in G.
5Wenn man behauptet zwei Aussagen Aund Bseien ¨aquivalent, so meint man, dass beide Aussagen
”gleichbedeutend“ seien, d. h. wenn die AussageAwahr ist, dann ist auchBwahr, und wenn die Aussage
B wahr ist, dann ist auch A wahr.

## Seite 200

6 Formale Sprachen und Parser
Eine wichtige Klasse von Algorithmen in der Informatik befasst sich damit, Texte zu
durchsuchen, zu erkennen und zu analysieren. Die ¨Uberpr¨ufung, ob ein Text einer be-
stimmten – h¨auﬁg in Form einer formalen Grammatik festgelegten – Struktur entspricht,
bezeichnet man als Syntaxanalyse oder synonym als Parsing. Diese Algorithmen wer-
den beispielsweise im Umfeld des sog. Data Mining oder im Compilerbau zur formalen
Analyse von Programmtexten eingesetzt. Ein Compiler ¨ubersetzt ein Programm einer
h¨oheren Programmiersprache auf Basis seiner formalen Struktur (die oft in Form ei-
nes Syntaxbaums repr¨asentiert wird) in Maschinensprache, also derjenigen Sprache, die
direkt vom Prozessor eines Computers verstanden werden kann.
In Abschnitt 6.1 besch ¨aftigen wir uns mit den Grundlagen formaler Syntaxbeschrei-
bungen: mit formalen Sprachen und Grammatiken, den mathematischen Pendants der
”nat¨urlichen“ Sprachen und Grammatiken. Besonders interessant f ¨ur uns sind die sog.
Typ-2-Sprachen und die in gewissem Sinne weniger komplexen Typ-3-Sprachen. Ab-
schnitt 6.2 beschreibt die Repr ¨asentation von Grammatiken in Python und zeigt die
Implementierung einiger grundlegender Funktionen auf den Nichtterminalen von Gram-
matiken, n¨amlich FIRSTund FOLLOW; diese werden in den darauﬀolgenden Abschnitten
ben¨otigt.
Die folgenden Abschnitte 6.3 und 6.4 beschreiben die in der Praxis am h ¨auﬁgsten ver-
wendeten Algorithmen zum Erkennen und Analysieren von Programmiersprachen: Zum
Einen pr¨adiktive Parser, insbesondere Recursive-Descent-Parser, in Abschnitt 6.3; zum
Anderen LR-Parser in Abschnitt 6.4 wie sie etwa in Parsergeneratoren wie Yacc zum
Einsatz kommen.
6.1 Formale Sprachen und Grammatiken
6.1.1 Formales Alphabet, formale Sprache
Wir ben¨otigen im restlichen Kapitel die folgenden Deﬁnitionen:
 Ein (formales ) Alphabet A ist eine nicht-leere endliche Menge. Folgende Mengen
sind beispielsweise Alphabete:
A1 = {a,b,...,z }, A2 = {0,1}, A3 = {if,then,begin,end,stmt,ausdr}
 Das leere Wort, das aus keinen Buchstaben besteht, wird als ε bezeichnet.
 Ein Buchstabe ist ein Element eines Alphabets. Beispiele: 0 ist also ein Buchstabe
aus A2; then ist ein Buchstabe aus A3.

## Seite 201

186 6 Formale Sprachen und Parser
 Ein Wort entsteht durch Hintereinanderschreiben mehrerer Buchstaben eines Al-
phabets. Beispiele: aabaxist ein Wort ¨uber dem Alphabet A1; 010001 ist ein Wort
¨uber dem Alphabet A2.
Folgende Operatoren auf W¨ortern und Alphabeten sind relevant:
 Sei w ein Wort; |w|ist die Anzahl der Buchstaben in w. Beispiele: |001|= 3,
|ε|= 0, |if ausdr then stmt|= 4.
 Sei A ein Alphabet. Dann ist A∗die Menge aller W ¨orter mit Buchstaben aus A.
Es gilt immer auch ε∈A∗. Beispiel:
{a,b}∗= {ε,a,b,aa,ab,ba,bb,aaa,... }
 Gilt L⊆A∗, so nennt man L auch Sprache ¨uber dem Alphabet A.
 Ist w∈A∗ein Wort ¨uber dem Alphabet A. Dann ist wn das Wort, das durch n-
maliges Hintereinanderschreiben des Wortes wentsteht. Oﬀensichtlich gilt |wn|=
n·|w|.
Aufgabe 6.1
Geben Sie den Wert der folgenden Ausdr ¨ucke an:
(a) {ε}∗ (b) |{w∈{a,b,c}∗||w |= 2 }| (c) |{0,1}∗|
6.1.2 Grammatik, Ableitung, akzeptierte Sprache,
Syntaxbaum
Eine formale (Typ-2-)Grammatik1 den allgemeinsten Typ-0-GrammatikenGbesteht aus
vier Komponenten, mathematisch beschrieben als 4-Tupel ( S,T,V,P ), wobei
 T die Menge der sog. Terminalsymbole ist,
 V die Menge der sog. Nichtterminalsymbole ist, (manchmal auch Variablen oder
Metasymbole genannt)
 S ∈V das Startsymbol ist,
1Tats¨achlich kann man eine ganze Hierarchie von Grammatik-Typen deﬁnieren, die ¨uber die Form
der jeweils zugelassenen Produktionen deﬁniert werden kann. Bei Typ-0-Grammatiken unterliegen die
Produktionen keinerlei Einschr ¨ankungen: Linke und rechte Seite der Produktionen d ¨urfen beliebige
Zeichenfolgen aus V ∪T sein. Bei Typ-1-Grammatiken darf die rechte Seite einer Produktion nicht
k¨urzer sein als die linke Seite (ausgenommen sind Produktionen, deren rechte Seite ε ist). Bei Typ-
2-Grammatiken darf die Linke Seite jeder Regel aus nur einer Variablen bestehen und bei Typ-3-
Grammatiken gibt es zus ¨atzliche Einschr¨ankungen f¨ur die rechte Seite.

## Seite 202

6.1 Formale Sprachen und Grammatiken 187
 P ⊆V ×(T ∪V)∗ die Menge der sog. Produktionen ist; Produktionen sind also
Tupel, deren erste Komponente ein Element aus V und deren zweite Komponente
eine Sequenz von Elementen aus T ∪V ist.
Die Elemente von P sind mathematisch zwar als Tupel (siehe Anhang B) modelliert,
die beiden Tupel-Komponenten werden jedoch i. A. mit einem ”→“ als Trenner notiert;
f¨ur (A,abA) ∈P schreibt man also ¨ublicherweise A→abA ∈P.
Beispiel 6.1: Grammatik
Die Grammatik G= (S,{ausdr,ziﬀer},{+,-,0,..., 9},P) mit
P = { ausdr →ausdr + ausdr
ausdr →ausdr - ausdr
ausdr →ziﬀer
ziﬀer →0
... →...
ziﬀer →9 }
beschreibt einfache arithmetische Ausdr¨ucke.
Ableitung. Informell ausgedr¨uckt, ist die ”Bedeutung“ einer Produktion A →α mit
A ∈ V und α ∈ (V ∪T)∗ die, dass man jedes Vorkommen von A in einem Wort
w ∈(V ∪T)∗ durch die rechte Seite der Produktion α ersetzen darf. Dies wird durch
den Begriﬀ des Ableitungsschritts in Form der Relation ”⇒“ zum Ausdruck gebracht.
Es gilt:
x⇒y gdw. ∃β,γ ∈(V ∪T)∗,mit x= βAγ, y= βαγ
und A→α∈P (6.1)
Der Begriﬀ der Ableitung wird durch die transitive H¨ulle (siehe Abschnitt B.1.3 f¨ur eine
Deﬁnition des Begriﬀs der transitiven H¨ulle) von ⇒modelliert, d. h. durch die”kleinste“
transitive Relation, in der ⇒enthalten ist. Die transitive H ¨ulle von ”⇒“ schreibt man
als ”⇒∗“. Man kann die Relation ”⇒∗“ auch direkt folgendermaßen deﬁnieren:
x⇒∗y gdw. x= y oder x⇒y
oder ∃w0,...,w n: x⇒w0 ⇒... ⇒wn ⇒y (6.2)
Die durch eine Grammatik G= (S,T,V,P ) erzeugte Sprache L(G) ist folgendermaßen
deﬁniert:
L(G) := {w∈T∗|S ⇒∗w}
Die Sprache L(G) besteht also aus allen W ¨ortern (d. h. Folgen von Terminalzeichen,
d. h. Elementen aus T∗), die aus der Startvariablen S ableitbar sind.

## Seite 203

188 6 Formale Sprachen und Parser
Da es sich bei den in diesem Abschnitt behandelten Grammatiken eigentlich um sog.
Typ-2-Grammatiken handelt, nennen wir gelegentlich auch eine durch eine solche Gram-
matik erzeubare Sprache eine Typ-2-Sprache.
Ein aus sowohl Terminalen als auch Nichtterminalen bestehende Zeichenfolge, die in
einem Zwischenschritt einer Ableitung auftaucht, nennt man Satzform.
Beispiel 6.2: Ableitungsschritt, Ableitung, Sprache
Sei G die in Beispiel 6.1 deﬁnierte Grammatik. Dann gelten beispielsweise folgende
Aussagen:
ziﬀer ⇒0 denn: mit β,γ = ε und α = 0 und A = ziﬀer gilt
Voraussetzung aus Deﬁnition 6.1.
ausdr + ausdr ⇒∗ziﬀer + 9 denn: es gilt ausdr + ausdr ⇒ ziﬀer + ausdr ⇒
ziﬀer + ziﬀer ⇒ziﬀer + 9.
9 + 4 - 2∈L(G) denn: Das Wort l ¨asst sich aus dem Startsymbol ausdr
ableiten, d. h. ausdr ⇒∗ 9 + 4 - 2 und das
Wort besteht nur aus Terminalsymbolen, d. h.
9 + 4 - 2∈T∗.
9 -ziﬀer /∈L(G) denn: Es gilt zwar ausdr ⇒∗9 -ziﬀer aber 9 -ziﬀer /∈
T∗.
Syntaxb¨aume. Ein Syntaxbaum f ¨ur ein Wort w ∈L(G) ist ein Baum, dessen innere
Knoten mit Nichtterminalen beschriftet sind, dessen Bl ¨atter mit Buchstaben aus w
beschriftet sind, dessen Wurzel mit dem Startsymbol der Grammatik beschriftet ist
und jeder der inneren Knoten in folgender Weise einer Produktion A→x0 ...x n (mit
xi ∈ V ∪T) der Grammatik entspricht: Der innere Knoten ist mit ”A“ beschriftet
und die Kinder sind in der Reihenfolge von links nach rechts mit jeweils x0, . . . , xn
beschriftet. Abbildung 6.1 zeigt f ¨ur die Grammatik aus Beispiel 6.1 einen Syntaxbaum
f¨ur das Wort 9 + 4 - 3.
ausdr
ausdr
9 + 4
ausdr
- 3
ausdr
ziﬀer ziﬀerziﬀer
ausdr
Abb. 6.1: Ein Syntaxbaum f ¨ur das Wort 9 + 4 - 3.
Eine Grammatik G heißt mehrdeutig, falls es ein Wort w ∈L(G) gibt, f ¨ur die es zwei
verschiedene Syntaxb¨aume gibt. Die Grammatik aus Beispiel 6.1 ist beispielsweise mehr-
deutig (siehe auch Aufgabe 6.2).

## Seite 204

6.1 Formale Sprachen und Grammatiken 189
Aufgabe 6.2
F¨ur das Wort 9 + 4 - 3gibt es neben dem in Abbildung 6.1 abgebildeten Syntaxbaum
noch einen weiteren Syntaxbaum. Zeichnen Sie diesen auf.
Beispiel 6.3: Grammatik f¨ur verschachtelte Listen
Wir beschreiben eine Grammatik GListe, die alle g¨ultigen m¨oglicherweise verschach-
telten Python-Ziﬀernlisten erzeugt; also folgende W ¨orter sollten beispielsweise in
L(GListe) enthalten sein:
[], [1,5,2,6], [1,[[2]],[9,2],[],[[]],[0]]
Die folgende Grammatik GListe = (S,V,T,P ) mit
S = Liste ,
V = {Liste,elemente,element,ziﬀer},
T = {,,[,],0,..., 9}
und einer Menge P, bestehend aus den folgenden Produktionen, beschreibt eine
solche Sprache:
Liste →[ elemente ] |[ ]
elemente →element |element , elemente
element →Liste |ziﬀer
ziﬀer →0 |... |9
Die erste Produktion beschreibt eine Liste als entweder zwischen den Terminalen [
und ] eingeschlossene W¨orter, die durch das Nichtterminal elemente erzeugt wer-
den oder als das Wort ”[ ]“. Die zweite Produktion beschreibt das Nichtterminal
elemente: Dieses ist entweder ein einzelnes Element, beschrieben durch das Nicht-
terminal element, oder eine durch Kommata getrennte Liste von Elementen. Man
beachte, dass das Nichtterminal elemente rekursiv deﬁniert ist; zum Verst ¨andnis
hilft auch hier das in Abschnitt 1.2.1 beschriebene Denk ”rezept“ f¨ur die Erstellung
rekursiver Funktionen: Ausgehend von der Annahme, das Nichtterminal elemente
auf der rechten Seite der Produktion erzeugt die gew ¨unschten W¨orter, so m ¨ussen
wir die Produktionen so w¨ahlen, dass unter dieser Annahme die gew¨unschten W¨orter
erzeugt werden k¨onnen.
Die Produktionen f¨ur das Nichtterminal element beschreiben die Tatsache, dass ein
einzelnes Element schließlich wiederum eine vollst ¨andige Liste ist (auch hier ge-
hen wir gem ¨aß des eben schon erw ¨ahnten Denkrezepts davon aus, dass durch das
Nichtterminal Liste auf der rechten Seite alle wohlgeformten Listen erzeugt werden
k¨onnen) oder eine einzelne Ziﬀer.
Das Wort [ 1 , [ 5 , 1 ] , [ ] ]hat beispielsweise den in Abbildung 6.2 gezeigten
Syntaxbaum.

## Seite 205

190 6 Formale Sprachen und Parser
1 , [ 5 , 1 ] , [ ] ][
elemente
element
elemente
element
Liste
elemente
Liste
elemente elemente
element
Liste
elementelement
ziﬀerziﬀer ziﬀer
Abb. 6.2: Syntaxbaum des Wortes [ 1 , [ 5 , 1 ] , [ ] ].
Aufgabe 6.3
Erweitern Sie die Grammatik so, dass alle (m ¨oglicherweise geschachtelte) Ziﬀer-
Tupellisten (in Python-Notation) erzeugt werden. Folgende W¨orter sollten beispiels-
weise in der durch die Grammatik erzeugten Sprache enthalten sein:
([1,(1,2)],(2,),[2],[],()) ([1],) [1,2] (1,[2])
Beachten Sie, dass ein-elementige Tupel mit einem Komma am Ende notiert werden.
Aufgabe 6.4
Zeichnen Sie den Syntaxbaum f ¨ur das Wort [ [ [ 1 , [ ] ] ] , 1 ].
6.2 Repr ¨asentation einer Grammatik in Python
Wir repr¨asentieren eine Grammatik folgendermaßen als Python-Klasse:
1 class Grammatik(object):
2 def init ( self ,S,V,T,P=[]):
3 if '$' not in T: T.append('$')
4 if S not in V: V.append(S)
5 self .S = S ; self .V = V ; self .T = T ; self .P = []
6 for p in P: self . addP(p)

## Seite 206

6.2 Repr ¨asentation einer Grammatik in Python 191
7
8 def addP(self,s ):
9 (l , ,r) = s. partition ('->')
10 l = l. split () [0] ; r = r. split ()
11 assert all ( [x in self .V +self.T for x in [l ] +r]):
12 self .P.append((l,r))
Wir gehen davon aus, dass V und T jeweils Stringlisten sind und P eine Liste von
Tupeln darstellt, deren erste Komponente die jeweilige linke Seite eine Produktion und
deren zweite Komponente die rechte Seite einer Produktion in Form einer Stringliste
enth¨alt. Die Anweisungen in den Zeilen 3 und 4 stellen sicher, dass sich die Startvariable
S auch tats¨achlich in der Variablenmenge V beﬁndet und dass sich das Endesymbol
'$' auch tats¨achlich in der Menge der Terminalsymbol beﬁndet – wir gehen n ¨amlich
(aus praktischen Gr ¨unden) davon aus, dass jede Eingabe mit dem Endezeichen '$'
abschließt. In den Zeilen 5 und 6 werden die Objektattribute S, V und T gesetzt.
In Zeile 6 werden schließlich die Produktionen dem Objektattribut P hinzugef¨ugt. Dies
erfolgt ¨uber die interne Methode
addP, die es erlaubt, eine Produktion nach dem Sche-
ma ”linkeSeite'->'rechteSeite “ zu ¨ubergeben. Mittels s. partition ('->') wird die linke
Seite l und die rechte Seite r getrennt. Mittels l . split () bzw. r. split () werden an-
schließend die einzelnen Symbole getrennt. Damit eine Trennung der einzelnen Gram-
matiksymbole mittels split funktioniert, sollten Terminale und Nichtterminale immer
¨uber Leerzeichen getrennt ¨ubergeben werden.
Beispiel 6.4
Wir k¨onnen die Grammatik G= (D,{D,E,T ,F },{+,*,(,),id},P) mit
P = { D →E |E + T |T
T →T * F |F
F →( E ) |id }
also folgendermaßen in der Pythonklasse Grammatik repr¨asentieren:
>>>G = Grammatik('D', list('DETF'), ['id' ] +list('+*()'), '''D -> E
E -> E + T
E -> T
T -> T * F
T -> F
F -> ( E )
F -> id''' . split ('\n'))
Die Produktionen sind anschließend im Grammatik-Objekt G folgendermaßen re-
pr¨asentiert:
>>>G.P
[ ( 'D', [ 'E' ]), ( 'E', [ 'E', '+', 'T' ]), ( 'E', [ 'T' ]), ( 'T', [ 'T', '*', 'F' ]),
('T', [ 'F' ]), ( 'F', [ '(', 'E', ')' ]), ( 'F', [ 'id' ]) ]

## Seite 207

192 6 Formale Sprachen und Parser
Aufgabe 6.5
Schreiben Sie f ¨ur die Klasse Grammatik die Methode repr , um eine angemes-
sene String-Repr¨asentation einer Grammatik zu deﬁnieren. Orientieren Sie sich an
folgender Ausgabe:
>>>print G
D --> E
E --> E + T
E --> T
T --> T * F
T --> F
F --> ( E )
F --> id
6.2.1 Berechnung der FIRST-Mengen
Einige Algorithmen auf Grammatiken ben ¨otigen f¨ur jedes Nichtterminal (bzw. f¨ur jede
Satzform) die sog. FIRST- und FOLLOW-Mengen. Hierbei steht FIRST(A) f¨ur die Menge
aller Anfangssymbole von W¨ortern, die aus Aableitbar sind. Meist geht man davon aus,
dass die FIRST-Funktion auch ¨uber Satzformen α∈V ∪T deﬁniert ist; FIRST(α) steht
entsprechend f ¨ur die Menge aller Anfangssymbole von W ¨ortern, die aus α ableitbar
sind. Formaler:
FIRST(α) := {a ∈T |∃w : α⇒∗w ∧ w∈T∗ ∧ w beginnt mit a }
Beispiel 6.5: FIRST-Mengen
F¨ur die Grammatik aus Beispiel 6.4 gilt: FIRST(D) = FIRST(E) = FIRST(T) =
FIRST(F) = {(,id}
Aufgabe 6.6
Gegeben sei die folgende Grammatik G = (S,{a,b,c}, {},P) gegeben, wobei P aus
folgenden Produktionen besteht:
S →XYX |c
X →aXa |ε
Y →Yb |ε
Berechnen Sie FIRST(S),FIRST(X) und FIRST(Y).

## Seite 208

6.2 Repr ¨asentation einer Grammatik in Python 193
Wiederhole die folgenden Schritte f ¨ur alle X ∈V, bis sich keine der Mengen FIRST(X)
mehr ver¨andert.
1. Gibt es eine Produktion X →ε, so setze FIRST(X) := FIRST(X) ∪{ε}
2. Gibt es eine Produktion X →Y0Y1 ...Y n , dann:
(a) Falls Y0 ∈V: Setze FIRST(X) := FIRST(X) ∪FIRST(Y0)
Falls Y0 ∈T: Setze FIRST(X) := FIRST(X) ∪{Y0}
(b) F ¨ur alle i∈{1,...,n }: Falls ε∈FIRST(Y0),...,ε ∈FIRST(Yi−1) :
Falls Yi ∈V: Setze FIRST(X) := FIRST(X) ∪FIRST(Yi)
Falls Yi ∈T: Setze FIRST(X) := FIRST(X) ∪{Yi}
(c) Falls ε∈FIRST(Yi) f¨ur i= 0,...,n , so setze FIRST(X) := FIRST(X) ∪{ε}.
Abb. 6.3: Algorithmus zur Berechnung von FIRST(X) f¨ur X ∈V.
Da diese Deﬁnition noch kein Berechnungsverfahren festlegt, geben wir zus¨atzlich in Ab-
bildung 6.3 einen Algorithmus zur Berechnung von FIRST(X), f¨ur X ∈V an. Wie man
sieht, m¨ussen wir zur Berechnung derFIRST-Menge eines Nichtterminals also sukzessive
alle rechten Seiten der Produktionen f ¨ur dieses Terminal untersuchen (Fall 2.) und –
falls die jeweilige rechte Seite mit einem Terminal beginnt, diese in die FIRST-Menge
mit aufnehmen (Fall 2(a)). Beginnt die rechte Seite mit einem Nichtterminal, so m¨ussen
alle Elemente der FIRST-Menge dieses Nichtterminals in die FIRST-Menge mit aufge-
nommen werden. Dies gilt auch f ¨ur folgende Nichtterminale, falls alle linksstehenden
Nichtterminale ε ableiten (Fall 2(b)).
Dies kann man direkt in Python umsetzen; wir speichern die berechnetenFIRST-Mengen
in einem Dict-Objekt self . ﬁrst ab, dessen Schl¨ussel die Nichtterminale der Grammatik
sind und die dazugeh ¨orenden Werte die FIRST-Mengen. Listing 6.2.1 zeigt die notwen-
digen Erg¨anzungen in Form von vier zus ¨atzlichen Zeilen in der
init -Funktion:
1 def init ( self ,S,V,T,P=[]):
2 ... # Code von Listing 6.2
3 self . ﬁrst = {}
4 for X in self .V:
5 self . ﬁrst [X] = set()
6 self . ﬁrstCalc ()
In Zeile 4 werden alle Eintr ¨age von self . ﬁrst auf die leere Menge set () gesetzt. Wie
schon durch den Algorithmus in Abbildung 6.3 angedeutet, werden wir h ¨auﬁg die
Vereinigungs-Operation ben¨otigen; der set-Typ eignet sich hier folglich besser als der
list -Typ.
In Zeile 6 wird die Methode ﬁrstCalc verwendet, um self . ﬁrst [X] f¨ur alle X ∈self .V
zu berechnen. Das folgende Listing 6.1 zeigt die Implementierung dieser ﬁrstCalc -
Methode:

## Seite 209

194 6 Formale Sprachen und Parser
1 def ﬁrstCalc ( self ):
2 while True:
3 oldFirst = deepcopy(self. ﬁrst )
4 for X,alpha in self .P:
5 for Y in alpha:
6 if Y in self .T:
7 self . ﬁrst [X].add(Y)
8 break
9 if Y in self .V:
10 self . ﬁrst [X] = self. ﬁrst [X].union(self . ﬁrst [Y])
11 if '' not in self . ﬁrst [Y]:
12 break
13 if all ( [Y in self .V and '' in self. ﬁrst [Y] for Y in alpha]):
14 self . ﬁrst [X].add('')
15 if oldFirst == self. ﬁrst :
16 break
Listing 6.1: Python-Implementierung des in Abbildung 6.3 gezeigten Algorithmus.
Zun¨achst wird in Zeile 3 eine Kopie aller momentanen FIRST-Mengen erstellt, um am
Ende in Zeile 15 und 16 feststellen zu k ¨onnen, ob das Abbruchkriterium erf ¨ullt ist:
Abgebrochen wird n ¨amlich dann, wenn sich keine der FIRST-Mengen mehr ver ¨andert
hat. Ohne die Verwendung der deepcopy-Funktion w¨urde lediglich die Referenz auf
das self . ﬁrst -Dictionary kopiert und ein Gleichheitstest mittels des Vergleichsope-
rators ”==“ w¨urde entsprechend immer ”True“ liefern. Die Verwendung der deepcopy-
Funktion erzwingt das Erstellen einer tats ¨achlichen vollst¨andigen Kopie.
Die for-Schleife in Zeile 4 l¨auft ¨uber alle Produktionen p; die linke Seite wird jeweils an
die Variable X, die rechte Seite an die Variable alpha gebunden. F¨ur jede Produktion
werden alle Symbole Y der rechten Seite alpha durchlaufen; dies geschieht in der for-
Schleife in Zeile 5. Es werden zwei F ¨alle unterschieden:
 if-Anweisung in Zeile 6: Ist Y ein Terminal, wird dieses Terminal der Menge
ﬁrst [X] hinzugef¨ugt – dies entspricht der Zuweisung FIRST(X) := FIRST(X) ∪
{Yi}in Algorithmus aus Abbildung 6.3. Die weiteren Symbole aus alpha brauchen
dann nicht mehr betrachtet zu werden, und die for-Schleife wird mittels break
verlassen.
 if-Anweisung in Zeile 9: Ist Y dagegen ein Nichtterminal, so wird jedes Element
aus ﬁrst [Y] in ﬁrst [X] eingef¨ugt – dies entspricht der Zuweisung FIRST(X) :=
FIRST(X)∪FIRST(Yi) in Algorithmus aus Abbildung 6.3. Sollteεnicht in ﬁrst [Y]
enthalten sein (Pr¨ufung in Zeile 11), so brauchen die nachfolgenden Symbole aus
alpha nicht weiter betrachtet zu werden und die for-Schleife wird mittels break
verlassen.

## Seite 210

6.2 Repr ¨asentation einer Grammatik in Python 195
Aufgabe 6.7
Wo und wie genau wird der Fall 1. in dem in Abbildung 6.3 dargestellten Algorithmus
in der in Listing 6.1 Implementierung abgedeckt.
Einige Parse-Algorithmen ben ¨otigen die FIRST-Menge einer Satzform. Basierend auf
dem dict-Objekt ﬁrst l¨asst sich einfach eine Methode ﬁrstSatzform implementieren,
die die entsprechende FIRST-Menge einer Satzform α zur¨uckliefert – siehe hierzu auch
Aufgabe 6.8.
Aufgabe 6.8
Erstellen Sie eine Methode ﬁrstSatzform der Klasse Grammatik. Hierbei soll
ﬁrstSatzform (α) die FIRST-Menge der Satzform α zur¨uckliefern.
6.2.2 Berechnung der FOLLOW-Mengen
Die Menge FOLLOW(X) einer Grammatik G = ( S,V,T,P ) f ¨ur ein Nichtterminal X
enth¨alt alle Terminalsymbole, die in irgendeinem Ableitungsschritt unmittelbar rechts
von X stehen k¨onnen. Formaler:
FOLLOW(X) := {a∈T |∃α,β : S ⇒∗αXaβ }
Man beachte, dass $ ∈FOLLOW(X), falls S ⇒∗αX.
Da diese Deﬁnition noch kein Berechnungsverfahren festlegt, geben wir zus ¨atzlich in
Abbildung 6.4 einen Algorithmus zur Berechnung von FOLLOW(Y), f¨ur alle Y ∈V an.
1. Setze FOLLOW(S) := {$}
2. Wiederhole die folgenden Schritte f ¨ur alle Y ∈ V, bis sich keine der Mengen
FOLLOW(Y) mehr ver¨andert.
(a) F ¨ur jede Produktion der Form X →αYβ:
setze FOLLOW(Y) := FOLLOW(Y) ∪FIRST(β) \{ε}
(b) F ¨ur jede Produktion der Form X →αY oder X →αYβ, mit β ⇒∗ε:
setze FOLLOW(Y) := FOLLOW(Y) ∪FOLLOW(X).
Abb. 6.4: Algorithmus zur Berechnung von FOLLOW(X) f¨ur alle X ∈V.
Aufgabe 6.9
Sind die beiden F ¨alle 2(a) und 2(b) des in Abbildung 6.4 gezeigten Algorithmus
disjunkt?

## Seite 211

196 6 Formale Sprachen und Parser
Auch die Berechnung der FOLLOW-Mengen k¨onnen wir direkt in Python umsetzen.
Zun¨achst erweitern wir die init -Methode der Klasse Grammatik um die folgenden
Zeilen:
1 def init ( self ,S,V,T,P=[]):
2 ... # Code von Listing 6.2 und Listing 6.2.1
3 self . follow = {}
4 for X in self .V:
5 self . follow [X] = set()
6 self .followCalc()
Analog zur Repr¨asentation der FIRST-Mengen, verwenden wir auch bei der Repr¨asenta-
tion der FOLLOW-Mengen ein Dictionary-Objekt, dessen Schl¨ussel Elemente aus self .T
und dessen Werte set-Objekte sind. Zun¨achst werden in den Zeilen 4 und 5 alle Eintr¨age
self . follow [X], f¨ur X ∈T auf die leere Menge set () gesetzt.
Die in Listing 6.2 gezeigte MethodefollowCalc implementiert die eigentliche Berechnung
der FOLLOW-Mengen.
1 def followCalc( self ):
2 oldFollow = {}
3 self . follow [ self .S].add('$') # Fall 1.
4 while oldFollow ̸= self . follow :
5 oldFollow = deepcopy(self. follow )
6 for (X,Y,beta) in [(p[0], p[1] [i ], p[1] [i +1:]) for p in self .P
7 for i in range(len(p[1]))
8 if p[1] [i ] in self .V]:
9 ﬁrstBeta = self . ﬁrstSatzform (beta)
10 if beta: # Fall 2.(a)
11 ﬁrstBetaD = ﬁrstBeta . diﬀerence( ['' ])
12 self . follow [Y] = self. follow [Y].union(ﬁrstBetaD)
13 if not beta or '' in ﬁrstBeta : # Fall 2.(b)
14 self . follow [Y] = self. follow [Y].union(self . follow [X])
Listing 6.2: Python-Implementierung des in Abbildung 6.4 gezeigten Algorithmus.
¨Ahnlich wie bei der Berechnung der FIRST-Mengen, wird auch hier in jeder Iteration
mittels deepcopy eine vollst¨andige Kopie der FOLLOW-Mengen angelegt und nur dann
eine weitere Iteration durchgef ¨uhrt, wenn sich mindestens eine der FOLLOW-Mengen
ver¨andert hat. Die for-Schleife in Zeile 6 durchl ¨auft alle Variablen X und Y, f¨ur die es
eine Produktion der Form X →αYβ gibt. Die Variable ﬁrstBeta wird in Zeile 9 auf
FIRST(β) gesetzt. Ist β ̸= ε (dies entspricht der if-Abfrage in Zeile 10), so tritt der in
Algorithmus 6.4 unter 2(a) beschriebene Fall ein und es wird der Menge FOLLOW(Y)
die Menge FIRST(β) \{ε}hinzugef¨ugt – diese geschieht in Zeile 12. Ist β = ε oder ε∈
FIRST(β) (entspricht der if-Abfrage in Zeile 13), so tritt der in Algorithmus 6.4 unter
2(b) beschriebene Fall ein und es wird der Menge FOLLOW(Y) die Menge FOLLOW(X)
hinzugef¨ugt.

## Seite 212

6.3 Recursive-Descent-Parser 197
Aufgabe 6.10
Gegeben sei die Grammatik G= (Z,{a,b,c}, {Z,S,A,B },P}, wobei P aus den fol-
genden Produktionen besteht:
Z →S |ε
S →BASc |aSa
A →bAb
B →cBc |ε
Berechnen Sie die FOLLOW-Mengen aller Nichtterminale.
6.3 Recursive-Descent-Parser
Wir f ¨uhren in diesem Abschnitt die vielleicht einfachste Art der Syntax ¨uberpr¨ufung
f¨ur Typ-2-Sprache ein: Die Erstellung eines Recursive-Descent-Parsers. Ein Recursive-
Descent-Parser ben ¨otigt keine explizite Repr ¨asentation der Grammatik wie im letz-
ten Abschnitt gezeigt, sondern repr ¨asentiert eine Grammatik in Form einer Sammlung
von (eigens f ¨ur die jeweilige Grammatik) erstellten Prozeduren; eine Ableitung wird
durch Aufrufen von rekursiven Prozeduren ”simuliert“. Entsprechend ist ein Recursive-
Descent-Parser auch nicht generisch, sondern immer auf eine bestimmte Grammatik
zugeschnitten.
Ganz anders verh ¨alt es sich mit dem in Abschnitt 6.4 vorgestellten LR-Parser; dieser
ist generisch und eben nicht auf eine bestimmte Grammatik beschr¨ankt; er erwartet als
Eingabe eine in Python repr ¨asentierte Grammatik in der in Abschnitt 6.2 vorgestellten
Form und erstellt daraus automatisch einen Parser; LR-Parser sind beliebte Methoden
Parsergeneratoren (wie beispielsweise Yacc einer ist) herzustellen.
6.3.1 Top-Down-Parsing
Es gibt zwei grunds ¨atzlich unterschiedliche Vorgehensweisen, einen Text basierend auf
einer formalen Grammatik zu parsen und einen entsprechenden Syntaxbaum zu erzeu-
gen:
 Bottom-Up-Parsing: Hier wird der Syntaxbaum von unten nach oben erzeugt und
die Produktionen der Grammatik quasi von links nach rechts angewendet, solange
bis man bei der Startvariablen (also der Wurzel des Syntaxbaums) angelangt ist.
Bottom-Up-Parser (wie etwa der in Abschnitt 6.4 vorgestellte LR-Parser) sind
i. A. komplexer zu programmieren, k¨onnen aber eine gr ¨oßere Teilmenge von Typ-
2-Sprachen erkennen.
 Top-Down-Parsing: Hier wird der Syntaxbaum von oben nach unten erzeugt und
zun¨achst mit der Startproduktion begonnen. Top-Down-Parser sind i. A. leicht
zu programmieren, k¨onnen jedoch nur eine verh¨altnism¨aßig kleine Teilmenge von
Typ-2-Sprachen erkennen.

## Seite 213

198 6 Formale Sprachen und Parser
Beispiel 6.6: Top-Down-Parsing
Gegeben sei die folgende Grammatik, die die syntaktische Struktur einfache Has-
kell2-Datentypen beschreibt.
typ → einfach | [ typ ] | ( typ typLst )
einfach → Integer | Char | Bool
typLst → , typ typLst | ε
Folgende Abbildung zeigt den Anfangsteil eines Top-Down-Parsevorgangs f¨ur die Er-
kennung des Wortes ”( Char , Integer )“. Die obere H ¨alfte zeigt einen Teil des
Syntaxbaums der bisher aufgebaut wurde; die untere H ¨alfte zeigt die jeweiligen Po-
sitionen im Eingabewort an der sich der Parsevorgang beﬁndet.
( , Integer)Char( Char, Integer)
( typ typLst )
typ
( typ typLst )
typ
einfach
Char
( typ typLst )
typ
⇒ ⇒ ( Char Integer ), ⇒ ( Char Integer ),
typ ⇒ ⇒ ⇒
einfach
Char
, typ typLst
⇒...
⇒...
6.3.2 Pr ¨adiktives Parsen
Im allgemeinen Fall ist nicht sichergestellt, dass beim Betrachten des n ¨achsten Ein-
gabezeichens eindeutig klar ist, welche Produktion ausgew ¨ahlt werden muss. F ¨ur eine
allgemeine Typ-2-Grammatik muss ein solcher Parser m¨oglicherweise mit Backtracking
arbeiten: Sollte es sich im weiteren Verlauf des Parsevorgangs herausstellen, dass die
Auswahl einer Produktion (aus mehreren m ¨oglichen) falsch war, so muss der Parsevor-
gang zur¨uckgesetzt werden, eine andere Alternative gew¨ahlt und mit dieser fortgefahren
werden. Dies entspricht einer Tiefensuche durch den Baum aller m¨oglichen Parse-Wege,
die im schlechtesten Fall exponentielle Laufzeit haben kann. Eigentlich m¨ochte man, dass
immer nur h¨ochstens eine m¨ogliche Produktion zur Auswahl steht, dass also der”Baum“
aller m¨oglichen Parse-Wege eine simple Liste ist. Welche Eigenschaften muss eine ent-
sprechende Grammatik haben um ein solches sog. Pr¨adiktives Parsen zu erm¨oglichen?
Angenommen, das n¨achste zu expandierende Nichtterminal-Symbol sei Aund das n¨ach-
ste Eingabezeichen sei x; die Produktionen der verwendeten Grammatik, deren linke
Seite Aist, seien A→α1, A→α2, . . . ,A→αn. Es ist klar, dass eine solche Produktion
ausgew¨ahlt werden muss aus deren rechter Seite αi das Terminal x als erstes Zeichen
ableitbar ist; in anderen Worten: Es muss eine Produktion A →αi gew¨ahlt werden
mit x ∈FIRST(αi). Ist diese als N ¨achstes zu w ¨ahlende Produktion immer eindeutig
bestimmt, so bezeichnet man die Grammatik als pr ¨adiktiv.
2Die Programmiersprache Haskell ist wohl der prominenteste Vertreter der reinen funktionalen Pro-
grammiersprachen.

## Seite 214

6.3 Recursive-Descent-Parser 199
Es ist klar, dass f¨ur jede pr¨adiktive Grammatik folgende Bedingung gelten muss: F¨ur je
zwei Produktionen A→α und A→β mit gleichen linken Seiten A muss gelten, dass
FIRST(α) ∩FIRST(β) = ∅
d. h. die FIRST-Mengen der rechten Seiten m ¨ussen paarweise disjunkt sein.
6.3.3 Implementierung eines Recursive-Descent-Parsers
Ein Recursive-Descent-Parser arbeitet das Eingabewort¨uber den Aufruf rekursiver Pro-
zeduren ab. Jedes Nichtterminal der Grammatik wird als Prozedur implementiert. Um
einen Recursive-Descent-Parser f ¨ur die Grammatik aus Beispiel 6.6 (die Sprache ein-
facher Haskell-Typen) zu erstellen, m ¨ussen Prozeduren typ, typLst und einfach erstellt
werden. Jedem Nichtterminal auf der rechten Seite einer Produktion entspricht ein
Prozeduraufruf, jedem Terminal auf der rechten Seite einer Prozedur entspricht einer
Match-Operation, die pr¨uft, ob das aktuelle Zeichen der Eingabe mit dem entsprechen-
den Terminalsymbol ¨ubereinstimmt.
Listing 6.3 zeigt die Implementierung eines Recursive-Descent-Parsers f¨ur die Gramma-
tik aus Beispiel 6.6. Auf der linken Seite sind immer die zum jeweiligen Code-Fragment
passenden Produktionen der Grammatik zu sehen.
Die in Zeile 27 durch Benutzereingabe deﬁnierte Variable s enth¨alt die Liste der zu
parsenden Eingabesymbole; es wird immer der Wert None an das Ende dieser Liste
angeh¨angt; dieser Wert wird von dem Parser als Ende-Symbol interpretiert und ent-
spricht dem '$'-Symbol in der in Abschnitt 6.2 pr ¨asentieren Grammatik. Die Variable
lookahead zeigt immer auf das n ¨achste vom Parser zu lesende Symbol aus s.
Der Parse-Vorgang wird durch das Ausf¨uhren der Prozedur S – die dem Startsymbol S
entspricht – in Gang gesetzt. Man beachte: ¨Ahnlich wie bei dem im n¨achsten Abschnitt
beschriebenen LR-Parser ist man auch hier angehalten, f¨ur das Startsymbol – in diesem
Fall: typ – eine zus¨atzliche spezielle Produktion – in diesem Fall:S →typ $ – einzuf¨ugen,
die das Ende der Eingabe erkennt.
Dieser Recursive-Descent-Parser ist tats ¨achlich auch ein pr ¨adiktiver Parser: In jeder
Prozedur – dies triﬀt insbesondere f ¨ur die Prozedur typ zu – kann durch Lesen des
n¨achsten Eingabesymbols s [lookahead] immer eindeutig die passende Produktion aus-
gew¨ahlt werden.

## Seite 215

200 6 Formale Sprachen und Parser
S →typ
typ →einfach
typ →[ typ ]
typ →( typ typLst )
einfach →Integer |...
typLst →, typ typLst
typLst →ε
1 def match(c):
2 global lookahead
3 if s [lookahead] == c: lookahead += 1
4 else: print "Syntaxfehler"
5
6 def S():
7 typ() ; match(None)
8
9 def typ ():
10 if s [lookahead] in ['Integer','Char','Bool' ]:
11 einfach()
12 elif s [lookahead] == '[':
13 match('[') ; typ() ; match(']')
14 elif s [lookahead] == '(':
15 match('(') ; typ() ; typLst() ; match(')')
16 else: print "Syntaxfehler"
17
18 def einfach ():
19 match(s[lookahead])
20
21 def typLst():
22 if s [lookahead] == ',':
23 match(',') ; typ() ; typLst()
24 else:
25 pass
26
27 s = raw
input('Haskell-Typ? ').split () + [None]
28 lookahead = 0
29 S()
Listing 6.3:Recursive-Descent-Parser W¨orter der Gramma-
tik aus Beispiel 6.6 erkennt.

## Seite 216

6.3 Recursive-Descent-Parser 201
6.3.4 Vorsicht: Linksrekursion
Eine Produktion heißt linksrekursiv, falls das am weitesten links stehende Symbol der
rechten Seite mit dem Symbol der linken Seite identisch ist; eine Grammatik heißt
linksrekursiv, falls sie linksrekursive Produktionen enth ¨alt.
Beispiel 6.7: Linksrekursive Grammatik
Folgende linksrekursive Grammatik beschreibt die Syntax einfacher arithmetischer
Ausdr¨ucke, bestehend aus +,-,0,... 9.
ausdr →ausdr + ziﬀer |ausdr - ziﬀer
ausdr →ziﬀer
ziﬀer →0 |1 |... |9
Aufgabe 6.11
Erstellen Sie einen Syntaxbaum f ¨ur den Ausdruck
9 + 5 - 2
basierend auf der Grammatik aus Beispiel 6.7.
Betrachten wir einen linksrekursiven ”Teil“ einer Grammatik, d. h. eine Produktion der
Form A → Aα |β mit dem linksrekursiven ”Fall“ Aα und dem ”Abbruch“-Fall β –
wobei wir voraussetzen, dass α,β ∈V ∪T und α und β nicht mit dem Nichtterminal
A beginnen. Diese Produktion erzeugt beliebig lange Folgen von αs, die mit einem β
beginnen. Ein entsprechender Syntaxbaum ist in Abbildung 6.5(a) zu sehen. Eine solche
mit einem β beginnende α-Folge, k¨onnte man aber auch mit den nicht linksrekursiven
Produktionen A → βR , R → αR | ε erzeugen; ein entsprechender Syntaxbaum
ist in Abbildung 6.5(b) zu sehen. Enthalten die Produktionen f ¨ur ein Nichtterminal
mehrere linksrekursive F¨alle, so k ¨onnen diese in analoger Weise in nicht linksrekursive
Produktionen umgewandelt werden; Tabelle 6.2 zeigt nochmals diese in und die oben
beschriebene Transformation zur Elimination von Linksrekursion.
Linksrekursive
Produktionen
Nicht links-
rekursive Prod.
A→ Aα |β =⇒ A→βR
R→αR |ε
A→ Aα |Aβ |γ =⇒ A→γR
R→αR |βR |ε
Tabelle 6.2: Transformationsschemata zur Elimination von Linksrekursion aus einer Gram-
matik. Hierbei gilt, dass α,β ∈V ∪T und sowohl α als auch β beginnen nicht mit dem Nicht-
terminal A.

## Seite 217

202 6 Formale Sprachen und Parser
β α
A
A
A
α ...
A
α
(a) Syntaxbaum des Wortes
βαα...α durch die linksrekursive
Produktion.
β α α
A
R
R
...
R
α
R
ε
(b) Syntaxbaum des Wortes βαα...α
durch die Produktion mit eliminierter
Linksrekursion.
Abb. 6.5:Syntaxb¨aume des Worts βαα...α f¨ur die linksrekursiven Produktionen A→ Aα |β
und f¨ur die entsprechenden nicht linkrekursiven Produktionen A→βR; R→αR |ε.
Aufgabe 6.12
Gegeben sei die folgende linksrekursive Grammatik
ausdr →ausdr + term
ausdr →ausdr - term
ausdr →term
term →0 |1 |... |9
(a) Eliminieren Sie die Linksrekursion aus dieser Grammatik.
(b) Implementieren Sie einen Recursive-Descent-Parser, der die durch diese Gram-
matik beschriebene Sprache erkennt.
6.4 Ein LR-Parsergenerator
Ein LR-Parser arbeitet seine Eingabe von links nach rechts ab (daher das ”L“) und er-
zeugt Rechtsableitungen (daher das ”R“), d. h. immer das am weitesten rechts stehende
Nichtterminal wird durch die rechte Seite einer Produktion ersetzt.
Technik: Wir erstellen zun ¨achst einen endlichen Automaten (sehr ¨ahnlich einem sog.
Kreuzprodukt-Automaten), der g¨ultige Pr¨aﬁxe der durch die Grammatik beschriebenen
Sprache erkennt. Auf dessen Basis erstellen wir schließlich eine Syntaxtabelle, mit deren
Hilfe die Sprache eﬃzient erkannt werden kann.

## Seite 218

6.4 Ein LR-Parsergenerator 203
6.4.1 LR(0)-Elemente
Ein LR(0)-Element einer Grammatik Gist eine Produktion aus Gzusammen mit einer
Position auf der rechten Seite dieser Produktion; diese Position markieren wir mit einem
”“. Ein LR(0)-Element der Grammatik aus Beispiel 6.4 w ¨are etwa
⟨F →(  E )⟩
Ein LR(0)-Element enth¨alt Informationen dar ¨uber, an welcher ”Stelle“ sich ein Parse-
Vorgang beﬁndet. Wir k ¨onnen uns also vorstellen, dass das LR(0)-Element
⟨F →(  E )⟩den Status eines Parsevorgangs widerspiegelt, der gerade dabei ist zu
versuchen, das Nichtterminal F zu erkennen und vorher schon das Terminal ( erkannt
hat und als N ¨achstes versuchen wird das Nichtterminal E zu erkennen.
In Python kann ein LR(0)-Element einer Grammatik Grammatik(S,T,V,P) als Tupel
(i , j) repr ¨asentiert werden, wobei i ∈ range(len( self .P)) die Nummer der entspre-
chenden Produktion und j ∈range(len( self .P[i ] [1]) +1) die Position des ”“ auf der
rechten Seite der Produktion speziﬁziert. Geht man von der in Beispiel 6.4 gezeigten
Repr¨asentation der Grammatik aus, so w ¨urde man das LR(0)-Element ⟨F →(  E )⟩
durch das Tupel (5,1) repr ¨asentieren – die ”5“ steht f ¨ur den Indexposition der Pro-
duktion F →(E ) innerhalb der Produktionenliste self .P und die ”1“ steht f ¨ur die
Position des ”“-Zeichens (n ¨amlich rechts des erstens Symbols der rechten Seite der
Produktion).
Aufgabe 6.13
Implementieren Sie f ¨ur die Klasse Grammatik eine Methode printElement(i,j), das
das durch ( i , j) repr ¨asentierte LR(0)-Element in gut lesbarer Form auf dem Bild-
schirm ausgibt, wie etwa in folgender Beispielanwendung:
>>>G.printElement(5,1)
'F -> ( . E )'
6.4.2 Die H ¨ullenoperation
Beﬁndet sich ein Parsevorgang vor einem NichtterminalY – haben wir es also mit einem
LR(0)-Element der Form ⟨X →α Yβ ⟩zu tun – versucht der Parser als N¨achstes, das
Nichtterminal Y zu erkennen. Beﬁndet sich in dieser Grammatik eine Produktion der
Form Y →γ, so entspricht die Situation das Nichtterminal Y zu erkennen, auch dem
LR(0)-Element ⟨Y → γ⟩.
Die H¨ullenoperation huelle (E) f¨uhrt eine entsprechende Erweiterung einer Sammlung
E von LR(0)-Elementen durch; huelle (E) enth¨alt also immer LR(0)-Elemente, die der-
selben Parse”situation“ entsprechen. Listing 6.4 zeigt eine Implementierung in Python.
Die Methode huelle sammelt in der Listenvariablen E huelle alle zur H ¨ulle der LR(0)-
Elemente geh ¨orenden Elemente auf; in E neu beﬁnden sich immer in der jeweiligen
Iteration neu hinzugekommenen Elemente. Die while-Schleife in Zeile 5 wird so lange

## Seite 219

204 6 Formale Sprachen und Parser
wiederholt, bis keine weiteren Elemente hinzukommen. Zu Beginn jeder Iteration werden
zun¨achst alle in der letzten Iteration neu aufgesammelten LR(0)-Elemente zu E huelle
hinzugef¨ugt. Die in Zeile 7 deﬁnierte Liste Ys enth¨alt alle Elemente Y ∈V f¨ur die es ein
LR(0)-Element der Form ⟨X →α  Yβ ⟩∈ E neu gibt. Die in Zeile 9 deﬁnierte Liste
E neu sammelt nun alle LR(0)-Elemente der Form ⟨Y → γ⟩auf, die sich noch nicht
in der bisher berechneten H ¨ulle beﬁnden. K ¨onnen der H ¨ulle keine weiteren Elemente
hinzugef¨ugt werden, so bricht diewhile-Schleife ab und es wirdE huelle als set-Struktur
zur¨uckgeliefert.
1 class Grammatik(object):
2 ...
3 def huelle ( self ,E):
4 E huelle = [] ; E neu = E[:]
5 while E neu:
6 E huelle += E neu
7 Ys = [ self .P[i ] [1] [j ] for (i , j) in E neu
8 if j<len(self .P[i ] [1]) and self.P[i ] [1] [j ] in self .V]
9 E neu = [(i,0) for i in range(len( self .P))
10 if self .P[i ] [0] in Ys and (i,0) not in E huelle ]
11 return set(E huelle)
Listing 6.4: Implementierung der H ¨ullenoperation
6.4.3 Die GOTO-Operation
Entscheidend f¨ur die Konstruktion eines LR-Parsers ist die GOTO-Operation: F¨ur Y ∈
(V ∪T) (d. h. Terminal oder Nichtterminal) ist GOTO(E,Y ) deﬁniert als die H ¨ulle
aller LR(0)-Elemente ⟨X →αY  β⟩, mit ⟨X →α  Yβ ⟩∈ E. Listing 6.5 zeigt die
Implementierung in Python.
1 class Grammatik(object):
2 ...
3 def goto( self ,E,Y):
4 return self. huelle ( [(i , j +1) for (i, j) in E
5 if j<len(self .P[i ] [1]) and self.P[i ] [1] [j ]==Y])
Listing 6.5: Implementierung der GOTO-Operation in Python
Das Tupel ( i , j) durchl¨auft alle LR(0)-Elemente aus E, deren rechte Seiten an der Po-
sition neben dem ”“ (das ist die Position j) das Symbol Y stehen haben. Ist ( i , j) die
Repr¨asentation des LR(0)-Elements ⟨X →α  Yβ ⟩, so ist ( i , j +1) die Repr¨asentation
des entsprechenden LR(0)-Elements in GOTO(Y). Die Methode goto liefert nun einfach
die H¨ulle all dieser LR(0)-Elemente zur ¨uck.

## Seite 220

6.4 Ein LR-Parsergenerator 205
6.4.4 Erzeugung des Pr ¨aﬁx-Automaten
Als n¨achsten Schritt auf dem Weg hin zu einem LR-Parser konstruieren wir einen deter-
ministischen endlichen Automaten (kurz: DEA), der Pr¨aﬁxe aller aus dem Startsymbol
rechts-ableitbaren Satzformen erkennt – vorausgesetzt jeder Zustand wird als m¨oglicher
Endzustand interpretiert.
Nach Ausf¨uhrung der in Listing 6.6 ab Zeile 16 gezeigten Methode automaton() enth¨alt
Attribut self .Es die Sammlung von Elementmengen, die die Zust ¨ande des Pr¨aﬁxauto-
maten darstellen. Jede dieser Elementmengen repr¨asentiert einen Zustand w¨ahrend des
Parsevorgangs.
1 class Grammatik(object):
2 ...
3 def automatonRek(self,state):
4 for X in self .V +self.T:
5 goto = self .goto(state ,X)
6 if not goto: continue
7 if goto not in self .Es:
8 self .Es.append(goto)
9 gotoInd = len( self .Es) -1
10 self .edges[gotoInd] = []
11 self .edges[ self .Es.index(state ) ].append((X,gotoInd))
12 self .automatonRek(goto)
13 else:
14 self .edges[ self .Es.index(state ) ].append((X,self.Es.index(goto)))
15
16 def automaton(self):
17 start = self . closure( [(0,0) ])
18 self .Es.append(start)
19 self .edges[0]=[]
20 self .automatonRek(start)
Listing 6.6: Erzeugung des Pr ¨aﬁx-erkennenden Automaten
Als Startzustand interpretieren wir die H ¨ulle des initialen LR(0)-Elements ⟨S′→ S⟩,
repr¨asentiert durch das Tupel (0,0). In Zeile 18 wird diese in die (zu erzeugende) Menge
von Elementen self .Es eingef¨ugt und die Methode automatonRek mit diesem Zustand
gestartet. Eine Randbemerkung ist an dieser Stelle angebracht: Will die von einer ge-
gebenen Grammatik mit Startsymbol S erzeugte Sprache durch einen Parser erkennen,
so sollte man grunds¨atzlich eine zus¨atzliche ”k¨unstliche“ Produktion S′→S einf¨uhren;
nur mittels dieser k ¨unstlichen Produktion kann der Parser erkennen, dass die Eingabe
beendet ist; auch bei dem Recursive-Descent-Parser aus Abschnitt 6.3 war dies notwen-
dig.
Die Methode automatonRek konstruiert nun rekursiv den Pr¨aﬁxautomaten wie folgt: In
der for-Schleife in Zeile 4 wird f ¨ur jedes Grammatiksymbol X ∈V ∪T die Element-
menge GOTO(state,X) berechnet, die – falls nichtleer – einem weiteren Zustand des

## Seite 221

206 6 Formale Sprachen und Parser
Pr¨aﬁxautomaten entspricht. Es k¨onnen drei F¨alle unterschieden werden:
1. Zeile 6: Es gilt GOTO(state,X) = ∅, d. h. es gibt keine von state ausgehende mit
X beschriftete Kante. In diesem Fall ist nichts weiter zu tun und die for-Schleife
wird mittels der continue-Anweisung mit dem n ¨achsten Symbol X ∈ V ∪T
fortgesetzt.
2. Zeile 7: Die Elementmenge GOTO(state,X) beﬁndet sich noch nicht in self .Es:
GOTO(state,X) wird in self .Es eingef¨ugt (Zeile 8) und die Variable gotoInd auf
die Nummer dieses neuen Zustands gesetzt (Zeile 9). Der neue Zustand enth ¨alt
noch keine ausgehenden Kanten, d. h. self .edges[gotoInd] wird die leere Liste [ ]
zugewiesen und in die Sammlung der ausgehenden Kanten des Zustandsstate wird
der neue Zustand zusammen mit dem Grammatiksymbol X mit aufgenommen
(Zeile 11). In Zeile 12 erfolgt die Rekursion: self .automatonRek(goto) erzeugt
rekursiv alle vom neu erzeugten Zustand ausgehenden Kanten und die folgenden
Zust¨ande.
3. Zeile 13: Die Elementmenge GOTO(state,X) beﬁndet sich bereits in self .Es. In
diesem Fall wird lediglich die Kante vom Zustand state (mit Nummer
self .Es.index(state )) zum Zustand GOTO(state,X) in self .edges eingef¨ugt.
Aufgabe 6.14
Durchl¨auft der in Listing 6.6 gezeigte Algorithmus die Zust¨ande des Pr¨aﬁxautomaten
. . .
(a) . . . in der Reihenfolge einer Tiefensuche?
(b) . . . in der Reihenfolge einer Breitensuche?
(c) . . . weder in der Reihenfolge einer Tiefen- noch der Reihenfolge einer Breitensu-
che?
Beispiel 6.8
Abbildung 6.6 zeigt den Pr ¨aﬁxautomaten f¨ur die Grammatik G= (E′,T,V,P ) mit
T = {+,*,(,),id}und V = {E′,E,T,F }und folgenden in P enthaltenen Produk-
tionen:
E′ →E
E →E + T |T
T →T * F |F
F →( E ) |id
Wir spielen die ersten Schritte bei der Erstellung des Pr ¨aﬁxautomaten durch. Wir
starten mit der als Anfangszustand betrachteten Elementmenge

## Seite 222

6.4 Ein LR-Parsergenerator 207
H¨ULLE(⟨E′ →  E⟩) – in Abbildung 6.6 entspricht dies genau der als Zustand E0
bezeichneten Elementmenge. Nun werden die GOTO-Mengen berechnet, angefangen
mit GOTO(E0,E′), die jedoch leer ist. Darum wird zum n ¨achsten Nichtterminal E
¨ubergegangen und GOTO(E0,E) = {⟨E′ →E ⟩,⟨E →E  + T⟩}berechnet und
ein neuer dieser Elementmenge entsprechender Zustand erzeugt; in Abbildung 6.6
entspricht dies Zustand E1. Durch einen rekursiven Aufruf (Zeile 12 in Listing 6.6)
werden zun¨achst alle vom Zustand E1 ausgehenden Kanten und die nachfolgenden
Zust¨ande bestimmt. Danach wird mit dem n ¨achsten Nichtterminal T fortgefahren
und GOTO(E0,T) zu {⟨T →T  * F ⟩,⟨E →T  ⟩}berechnet; diese Elementmenge
entspricht dem Zustand E9 in Abbildung 6.6. Diese Erzeugung von Kanten und ent-
sprechenden Zust¨anden wird so f¨ur die verbleibenden Symbole aus V ∪T fortgef¨uhrt
und die Erstellung des Pr ¨aﬁxautomaten anschließend beendet.
⟨F →(E)  ⟩E8
⟨T →  F ⟩
⟨E’ →  E ⟩
⟨F →  id ⟩
⟨E →  T ⟩
⟨F →  (E) ⟩
⟨E →  E+T ⟩
⟨T →  T *F ⟩
E0 ⟨T →T *  F ⟩
⟨F →  id ⟩
⟨F →  (E) ⟩
E4
⟨T →T  *F ⟩
⟨E →T  ⟩
E9
⟨F →(E  ) ⟩
⟨E →E  +T ⟩
E7
⟨T →T *F  ⟩E5
⟨E →E+T  ⟩
⟨T →T  *F ⟩
E3
T E
+
F
⟨F →id  ⟩
T
E11
⟨T →F  ⟩
)
E
id
E10
T
id
*
(
F
id
F
id
F
⟨E’ →E  ⟩
⟨E →E  +T ⟩
E1
⟨E →E+  T ⟩
⟨T →  T *F ⟩
⟨F →  id ⟩
⟨F →  (E) ⟩
⟨T →  F ⟩
E2
+
+
⟨T →  T *F ⟩
⟨F →  id ⟩
⟨E →  T ⟩
⟨F →  (E) ⟩
⟨F →(  E) ⟩
⟨E →  E+T ⟩
⟨T →  F ⟩
E6
(
(
(
Abb. 6.6: Pr¨aﬁxautomat der Grammatik G. Die Elementmengen E0, E1, . . . ,E11 entsprechen
genau den durch in Listing 6.6 gezeigten Funktion automaton() berechneten Elementmengen
self .Es[0], self .Es[1], . . . , self .Es[11].

## Seite 223

208 6 Formale Sprachen und Parser
Aufgabe 6.15
Welche der folgenden Satzformen (d. h. W ¨orter aus V ∪T) der in Beispiel 6.8 ver-
wendeten Grammatik k¨onnen durch den Pr¨aﬁxautomaten erkannt werden? – voraus-
gesetzt, jeder Zustand des Pr ¨aﬁxautomaten ist ein aktzeptierender Zustand.
(a) id+id (b) E+id (c) id (d) E+T +(
(e) (E+(( (f) (T *(
6.4.5 Berechnung der Syntaxanalysetabelle
Aus dem Pr ¨aﬁxautomaten kann nun die Syntaxanalysetabelle erstellt werden, auf der
das eigentliche LR-Parsing basiert. Die Syntaxanalysetabelle besteht aus zwei Teilen:
der Aktionstabelle (in der Implementierung aus Listing 6.7: self .aktionTab) und der
Sprungtabelle (in der Implementierung aus Listing 6.7: self .sprungTab). Tabelle 6.3
zeigt Aktions- und Sprungtabelle f ¨ur die Grammatik aus Beispiel 6.8. Der eigentliche
LR-Parser arbeitet als Kellerautomat (dessen Implementierung wir im n ¨achsten Ab-
schnitt vorstellen): Triﬀt der Parser auf einen Shift-Eintrag – das sind die mit ”s“ be-
ginnenden Eintr¨age in Tabelle 6.3 –, so wird der entsprechende Zustand auf den Keller
geladen; triﬀt der Parser auf einen Reduce-Eintrag – das sind die mit ”r“ beginnenden
Eintr¨age –, so wird mit der entsprechenden Produktion reduziert, d. h. die rechte Seite
α (die sich zu diesem Zeitpunkt auf dem Stack beﬁnden sollte) der Produktion A→α
wird durch die Variable A ersetzt; f¨ur den Kellerautomaten bedeutet dies, dass die zu
den Symbolen der rechten Seite geh ¨orenden Zust¨ande vom Keller entfernt werden und
dadurch der Keller um |α|Eintr¨age schrumpft.
Beﬁndet sich der LR-Parser beispielsweise im Zustand E2 und liest das ”(“-Zeichen, so
l¨adt er den Zustand 6 (bzw. in dem von uns implementierten Kellerautomaten das Tupel
(6,'(')) auf den Keller. Beﬁndet sich der LR-Parser beispielsweise im Zustand E3 und
liest das ”)“-Zeichen, so reduziert er mit Produktion self .P[1], also der Produktion
E →E+T .
Aufgabe 6.16
Erkl¨aren Sie einige der Eintr ¨age der Syntaxanalysetabelle (Tabelle 6.3):
(a) Warum ist Aktionstabelle[E0,(] = s6?
(b) Warum ist Sprungtabelle[E6,T ] = 9?
(c) Warum ist Aktionstabelle[E8,)] = r5?
Das Skript in Listing 6.7 berechnet die Syntaxanalysetabelle und verwendet dabei den
in Listing 6.6 berechneten Pr¨aﬁxautomaten bestehend aus den Knoten self .Es und den
Kanten self .edges.

## Seite 224

6.4 Ein LR-Parsergenerator 209
Aktionstabelle Sprungtabelle
+ ( ) id * $ E’ E T F
E0 s6 s11 1 9 10
E1 s2 Acc
E2 s6 s11 3 10
E3 r1 r1 s4 r1
E4 s6 s11 5
E5 r3 r3 r3 r3
E6 s6 s11 7 9 10
E7 s2 s8
E8 r5 r5 r5 r5
E9 r2 r2 s4 r2
E10 r4 r4 r4 r4
E11 r6 r6 r6 r6
Tabelle 6.3:Syntaxanalysetabelle f¨ur die Grammatik aus Beispiel 6.8 basierend auf dem ent-
sprechenden Pr¨aﬁxautomaten aus Abbildung 6.6
1 class Grammatik(object):
2 ...
3 def tabCalc( self ):
4 for i in range(len( self .Es)):
5 for X,j in self .edges[i ]:
6 if X in self .T: self .aktionTab[i] [X] = (SHIFT, j)
7 if X in self .V: self .sprungTab[i][X ] = j
8 if (0,1) in self .Es[i ]: self .aktionTab[i] ['$' ] = ACCEPT
9 for (aS,jS) in [(a,j) for (j ,k) in self .Es[i ]
10 if k == len(self.P[j ] [1]) and self.P[j ] [0] ̸= self .V[0]
11 for a in self . follow [ self .P[j ] [0] ] ]:
12 self .aktionTab[i] [aS] = (REDUCE, jS)
Listing 6.7: Berechnung der Syntaxanalysetabelle
F¨ur jeden Zustand Ei in der durch automaton() berechneten Sammlung von Element-
mengen self .Es (das ist die ”for i“-Schleife in Zeile 4) wird f ¨ur jede mit einem Symbol
X beschriftete ausgehende Kante zu einem Zustand j (das ist die ”for X,j“-Schleife in
Zeile 5) ein Eintrag in der Syntaxanalysetabelle erzeugt: Falls X ∈self .T so wird der
Eintrag ”sj“ in der Aktionstabelle erzeugt (Zeile 6); falls X ∈ self .V wird ein Ein-
trag ”j“ in der Sprungtabelle erzeugt (Zeile 7). In Zeile 8 wird der Eintrag ACCEPT
in der Syntaxanalysetabelle erzeugt: Beﬁndet sich der Automat in einem Zustand, der
das LR(0)-Element S′→S enth¨alt und erh ¨alt der Automat als n ¨achste Eingabe das
Endezeichen '$', so wird die Eingabe erkannt.
Ab Zeile 9 werden die Reduce-Eintr ¨age in der mit Ei markierten Zeile erzeugt: F ¨ur
jedes LR(0)-Element in Ei der Form ⟨A → α ⟩mit A ̸= S′ (dies entspricht dem

## Seite 225

210 6 Formale Sprachen und Parser
Test self .P[j ] [0] ̸= self .V[0]) wird in Spalte X ein Reduce-Eintrag erzeugt, falls
X ∈FOLLOW(A) – nur falls X ∈FOLLOW(A) kann n¨amlich X ein erlaubtes N ¨achstes
Zeichen im Parse-Prozess sein.
Aufgabe 6.17
Schreiben Sie eine Funktion printTab als Methode der Klasse Grammatik, die die
durch tabCalc berechnete Syntaxanalysetabelle in lesbarer Form ausgibt. Beispiel:
>>>print G.printTab()
| + ( ) id * $ E’ E T F
0 | s6 s11 1 9 10
1 | s2 acc
2 | s6 s11 3 10
3 | r1 r1 s4 r1
... ...
6.4.6 Der Kellerautomat
Das in Listing 6.8 gezeigte Skript implementiert den eigentlichen Parser in Form eines
Kellerautomaten. Dieser Kellerautomat greift in jedem Schritt auf Eintr ¨age der Synta-
xanalysetabelle zu und bestimmt daraus die n ¨achste auszuf¨uhrende Aktion.
1 class Grammatik(object):
2 ...
3 def parse(self ,s ):
4 s = s. split () + ['$' ]
5 stack = [(0, None)] ; zustand = 0 ; i=0 ; prods=[]
6 while True:
7 x = s[i ]
8 if x not in self .aktionTab[zustand]:
9 print "error at",x
10 return
11 aktion = self .aktionTab[zustand][x ]
12 if aktion [0] == SHIFT:
13 stack.append((aktion[1], x))
14 i +=1
15 elif aktion [0] == REDUCE:
16 p = self .P[aktion[1]] # Reduktion mit p= A→α
17 prods.append(p)
18 stack = stack[: -len(p[1])] # Stack um |α|erniedrigen
19 stack.append((self .sprungTab[stack[ -1][0]][ p[0]], p[0])) # stack.append(GOTO(A),A)
20 elif aktion [0] == ACCEPT:
21 return prods
22 zustand = stack[ -1][0]
Listing 6.8: Implementierung des Kellerautomaten

## Seite 226

6.4 Ein LR-Parsergenerator 211
Die Variable s enth¨alt das zu parsende Wort in Form einer Liste von Terminalsymbolen.
Der Stack wird in der Variablen stack gehalten. Innerhalb der while-Schleife wird das
Wort s durchlaufen. Hierbei enth ¨alt x immer den aktuellen Buchstaben. Der Zustand
zustand des Kellerautomaten ist immer der im obersten Tupel des Stacks gespeicherte
Zustand (siehe Zeile 22).
Sollte die Syntaxanalysetabelle f ¨ur den aktuellen Zustand zustand und das aktuelle
Zeichen x keinen Eintrag enthalten, (der entsprechende Test erfolgt in Zeile 8) so wird
eine Fehlermeldung ausgegeben. Andernfalls enth¨alt aktion die durchzuf¨uhrende Aktion;
hier sind 3 F ¨alle zu unterscheiden:
1. aktion ist eine Shift-Operation – dies wird in Zeile 12 gepr ¨uft: In diesem Fall wird
der Zustand aktion [1] zusammen mit dem aktuellen Eingabezeichen als Tupel auf
den Stack gelegt.
2. aktion ist eine Reduce-Operation – dies wird in Zeile 15 gepr¨uft: In diese Fall wird
mit der Produktion p = self .P[aktion[1]] reduziert. Hierbei wird zun ¨achst der
Stack um die L ¨ange der rechten Seite α von p reduziert (Zeile 18); mit Hilfe des
nun oben auf dem Stack liegenden Zustands stack [ -1][0] und der linken Seite
A der Produktion p wird aus der Sprungtabelle der Folgezustand bestimmt und
diesen zusammen mit A auf den Stack gelegt (Zeile 19).
3. aktion ist die Accept-Operation – dies wird in Zeile 20 gepr ¨uft. Dies bedeutet,
dass die Eingabe akzeptiert wird und die parse-Funktion mit der R ¨uckgabe der
f¨ur den Parse-Vorgang verwendeten Produktionen abbricht.
Der vollst¨andige Ablauf einer Parse-Operation des Beispielworts ”( id * id )“ ist in
Abbildung 6.7 gezeigt.

## Seite 227

212 6 Formale Sprachen und Parser
( * id )id
stack
(0,None)
( * id )id
stack
(0,None)
(6,'(')
s11
( * id )id
stack
(0,None)
(6,'(')
(11,'id')
r{F →id}
( * id )id
stack
(0,None)
(6,'(')
(9,'T')
( * id )id( * id )id
(0,None)
(6,'(')
(9,'T')
(4,'*')
(11,'id')
( * id )id
(0,None)
(6,'(')
(9,'T')
(4,'*')
(10,'F')
stack
( * id )id
(0,None)
(6,'(')
(9,'T')
stack
( * id )id
(0,None)
(6,'(')
(7,'E')
( * id )id
(0,None)
(10,'F')
( * id )id( * id )id
(0,None)
(9,'T')
stack
(0,None)
(1,'E')
( * id )id
(0,None)
(6,'(')
(7,'E')
(8,')')
stack r{F →(E)}
( * id )id
(0,None)
(6,'(')
(10,'F')
( * id )id
(0,None)
(6,'(')
(9,'T')
(4,'*')
(5,'F')
s6
s4
(0,None)
(6,'(')
(9,'T')
(4,'*')
s11stack s11stack
stack s8
stack r{T →F } stack r{E →T } Acc
stackr{T →F }
stack r{F →id}
r{E →T *F } r{E →T }
Abb. 6.7: Darstellung aller Aktionen des Kellerautomaten, um das Wort ”( id * id )“ zu
parsen. In jedem Schritt wird der Zustand des Stacks, die momentane Position innerhalb des zu
parsenden Wortes und die aus der Syntaxanalysetabelle ausgelesene Aktion (innerhalb des ab-
gerundeten K¨astchens) dargestellt. Die Shift-Operationen beginnen mit einem ”s“, die Reduce-
Operationen mit einem ”r“. Bei den Reduce-Schritten wurde statt der Nummer der Produktion
(mit der die auf dem Stack beﬁndliche Satzform reduziert werden soll) aus Gr¨unden der besseren
Lesbarkeit jeweils gleich die Produktion selbst (statt deren Nummer innerhalb der Produktio-
nenliste self .P) angegeben.
Nehmen wir als Beispiel den dritten Schritt: Der Kellerautomat beﬁndet sich immer in dem im
obersten Stackelement enthaltenen Zustand, hier also in Zustand E11; es wird das Zeichen *
gelesen. Der entsprechende Eintrag in der Syntaxanalysetabelle, also self .aktionTab[11]['*' ],
ist ”r6“ (siehe auch Tabelle 6.3); der besseren Lesbarkeit halber ist die sechste Produktion, also
self .P[6], ausgeschrieben als ”F →id“. Diese Reduce-Aktion bewirkt, dass der Stack zun ¨achst
um |id|= 1 erniedrigt wird; mit dem Zustand, den das oberste Stackelement dann enth ¨alt,
das ist hier der Zustand E6, und mit der linken Seite der zu reduzierenden Produktion, das
ist hier F, wird dann in der Sprungtabelle der Folgezustand self .sprungTab[6]['F' ]=10 nach-
geschlagen; dieser wird zusammen mit F auf den Stack gelegt und mit dem n ¨achsten Schritt
fortgefahren.

## Seite 228

7 Stringmatching
Gegeben sei ein Muster M mit der L¨ange m und ein Text T der L¨ange n. Ziel des String-
matching ist das Finden aller Stellen i in T, an denen sich das Muster M beﬁndet. For-
maler gesprochen sollen alle Stellen i gefunden werden, f¨ur die T[i :i +m -1]== M gilt.
Die folgende Abbildung veranschaulicht das Ergebnis eines Stringmatches des Musters
M = kakaokaki mit einem Text T. Das Ergebnis des Matches ist i= 3 und i= 37.
kakaokaki
i= 3
M =
T = diekakaokakiistkakaomitkakiweshalbsiekakaokakiheisst
i= 37
In diesem Abschnitt lernen wir teilweise sehr unterschiedliche Techniken f ¨ur schnelles
(d. h. deutlich schneller als O(n·m)) Stringmatching kennen:
 Stringmatching mit endlichen Automaten (Abschnitt 7.2).
 Eine Verfeinerung davon, der Knuth-Morris-Pratt-Algorithmus (Abschnitt 7.3).
 ¨Ahnlich funktioniert auch der Boyer-Moore-Algorithmus, nur wird das Muster von
der anderen Richtung ¨uber den Text geschoben (Abschnitt 7.4).
 Der Rabin-Karp-Algorithmus verwendet eine ganz andere Technik, n ¨amlich Ha-
shing (Abschnitt 7.5).
 Auch der Shift-Or-Algorithmus verwendet eine von den anderen Algorithmen
grundauf verschiedene bitbasierte Technik (Abschnitt 7.6).
7.1 Primitiver Algorithmus
Ein primitiver Algorithmus ist schnell gefunden und implementiert:
1 def match(M,T):
2 matches = [ ]
3 for i in range(len(T) -len(M)):
4 if all (T[i +j]==M[j] for j in range(len(M))):
5 matches.append(i)
6 return matches
Listing 7.1: Die Funktion match ﬁndet alle Stellen in T, die das Muster M enthalten

## Seite 229

214 7 Stringmatching
kakaokakiM =
T =
Mismatch
kakakaokakigibtsnicht
Abb. 7.1: Eine Beispielsituation w ¨ahrend eines Stingmatchings: Hier k ¨onnte man gleich an
Position 3 weitersuchen.
Alle Treﬀer, d. h. Stellen in T an denen sich eine Kopie von M beﬁndet, werden in der
Liste matches aufgesammelt. Die for-Schleife ab Zeile 3 durchl¨auft alle Positionen i des
Textes T und f ¨ugt die Stelle i genau dann zu matches hinzu, falls die nachfolgenden
len(M) Zeichen mit den jeweiligen Zeichen aus M ¨ubereinstimmen.
Aufgabe 7.1
Die in Listing 7.1 gezeigte Funktion match kann auch durch eine einzige Listenkom-
prehension implementiert werden. Schreiben Sie die Funktion entsprechend um, und
f¨ullen sie hierzu die in folgendem Listing freigelassene L ¨ucke:
def match(M,T):
return [ ... ]
Die Laufzeit dieses primitiven Stringmatching-Algorithmus ist sowohl im Worst-Case-
Fall als auch im Average-Case-Fall inO(n·m), wobei m= len(M) und n= len(T). F¨ur
jede der n Textpositionen in T m¨ussen im schlechtesten Fall O(m) Vergleiche durch-
gef¨uhrt werden, um Klarheit dar ¨uber zu erhalten, ob sich an der jeweiligen Position
eine Kopie von M beﬁndet oder nicht.
Wir werden sehen, dass die Laufzeit der schnellsten Stringmatching-Algorithmen in
O(n+ m) liegen.
7.2 Stringmatching mit endlichen Automaten
Entdeckt der primitive Stringmatching-Algorithmus aus Listing 7.1 einen Mismatch
an Position i, so f ¨ahrt er mit der Suche an Position i+ 1 fort. Passt jedoch der Teil
des Musters, der sich vor dem Mismatch befand, zu einem Anfangsteil des Musters,
so k ¨onnte man – verglichen mit der Funktionsweise des primitiven Stringmatching-
Algorithmus – Vergleiche sparen. Betrachten wir als Beispiel die folgende in Abbildung
7.1 dargestellte Situation. Hier w ¨are es ineﬃzient nach diesem Mismatch an Position 1
von T weiterzusuchen, denn oﬀensichtlich stellen die zuletzt gelesenen Zeichen kak ein
Pr¨aﬁx, d. h. ein Anfangsst¨uck, eines Matches dar.
Man kann einfach einen deterministischen endlichen Automaten konstruieren, der die
zuletzt gelesenen Zeichen als Pr¨aﬁx des n¨achsten Matches deuten kann. W¨ahrend es bei
einem nichtdeterministischen endlichen Automaten f ¨ur ein gelesenenes Eingabezeichen

## Seite 230

7.2 Stringmatching mit endlichen Automaten 215
eventuell mehrere (oder auch gar keine) M ¨oglicheiten geben kann, einen Folgezustand
auszuw¨ahlen, muss bei einem deterministischen endlichen Automaten immer eindeutig
klar sein, welcher Zustand als N¨achstes zu w¨ahlen ist, d. h. jeder Zustand muss f¨ur jedes
Zeichen des ”Alphabets“ (das je nach Situation {0,1}, die Buchstaben des deutschen
Alphabetes, oder jede andere endlichen Menge von Symbolen sein kann) genau eine
Ausgangskante besitzen. Dies triﬀt auch auf den in Abbildung 7.2 dargestellten deter-
ministischen endlichen Automaten zu, der eﬃzient alle Vorkommen von kakaokaki in
einem Text T erkennt. Der Automat startet in Zustand ”1“; dies ist durch die aus dem
”Nichts“ kommende Eingangskante angedeutet. Basierend auf den aus T gelesenen Zei-
chen ver¨andert der Automat gem ¨aß den durch die Pfeile beschriebenen Zustands ¨uber-
gangsregeln seinen Zustand. Immer dann, wenn er sich im Endzustand (darstellt durch
den Kreis mit doppelter Linie) beﬁndet, ist ein Vorkommen von kakaokaki in T er-
kannt. Eine Kantenmarkierung von beispielsweise ”[^ok]“ bedeutet – in Anlehnung an
regul¨are Ausdr¨ucke – dass der entsprechende ¨Ubergang bei allen Eingabezeichen außer
”o“ und ”k“ gew¨ahlt wird.
Wie wird ein solcher Automat konstruiert? Um dies besser nachvollziehen zu k¨onnen be-
kk
k a k a
k
k
k
a k i
[^k]
[^ka] [^k] [^ak] [^ok] [^k] [^ak] [^k][^k]
a
o
k
1 2 3 4 5 6 7 8 9 10
Abb. 7.2: Endlicher Automat, der ein eﬃzientes Erkennen aller Vorkommen des Wortes
kakaokaki erlaubt.
trachteten wir beispielsweise die Ausgangskanten des Zustands ”5“: Die Ausgangskante
mit Markierung ”o“ geh ¨ort zum sog. Skelettautomaten , dessen Kantenbeschriftungen
von links nach rechts gelesen genau dem zum matchenden Wortkakaokakientsprechen.
Wird im Zustand ”5“ das Zeichen ”k“ gelesen, so muss in den Zustand ”4“ gesprungen
werden – und nicht etwa in Zustand ”2“ oder gar Zustand ”1“, denn: Beﬁndet sich
obiger Automat in Zustand ”5“ heißt dies immer, dass das zuletzt gelesene Zeichen ein
”a“ und das vorletzte Zeichen ein ”k“ war; diese beiden Zeichen k¨onnten ein Anfangsteil
des zu suchenden Wortes kakaokaki darstellen und dies wird dadurch ber ¨ucksichtigt,
indem der Automat nach Lesen von ”k” als N¨achstes in Zustand ”4“ springt.
Man kann die Funktionsweise eines endlichen Automaten direkt in einem Programm
umsetzen:
1 def dfa(T):
2 zustand = 1
3 for t in T:
4 if zustand == 1:
5 if t ̸="k": zustand = 1
6 if t == "k": zustand = 2
7 if zustand == 2:

## Seite 231

216 7 Stringmatching
8 if t == "k": zustand = 2
9 elif t == "a": zustand = 3
10 else: zustand = 1
11 ...
Listing 7.2: Ein Teil der Implementierung des endlichen Automaten aus Abbildung 7.2.
Aufgabe 7.2
Vervollst¨andigen Sie die in Listing 7.2 gezeigte Implementierung des endlichen Au-
tomaten aus Abbildung 7.2.
Aufgabe 7.3
Sie wollen alle Vorkommen des Strings ananas in einem Text suchen:
(a) Erstellen Sie den passenden endlichen Automaten, der immer dann in einem
Endzustand ist, wenn er ein Vorkommen des Strings gefunden hat.
(b) Erstellen Sie eine entsprechendes Python-Skript, das die Funktionsweise dieses
endlichen Automaten implementiert.
Die Laufzeit setzt sich zusammen aus der Konstruktion des deterministischen endlichen
Automaten und dem anschließenden Durchlauf des Automaten bei der Eingabe des
Textes T. Dieser Durchlauf ben¨otigt oﬀensichtlich O(n) Schritte, denn genau daraufhin
wurde der Automat ja konstruiert: Bei jedem Eingabezeichen f ¨uhrt der Automat einen
wohl-deﬁnierten Zustands¨ubergang durch. Um den Automaten eﬃzient zu konstruieren,
ist jedoch ein raﬃnierter Algorithmus notwendig. Wir gehen jedoch nicht n ¨aher darauf
ein, da der im folgenden Abschnitt beschriebene Algorithmus zwar dasselbe Prinzip
verwendet, jedoch auf die Konstruktion des Automaten verzichten kann.
7.3 Der Knuth-Morris-Pratt-Algorithmus
Der Knuth-Morris-Pratt-Algorithmus verfolgt prinzipiell die gleiche Idee, wie sie bei der
Konstruktion eines deterministischen endlichen Automaten zum Tragen kommt; nur
vermeidet er, die aufw ¨andige Konstruktion eines kompletten deterministischen endli-
chen Automaten und beschr¨ankt sich auf das Wesentliche: die Suche nach Pr¨aﬁxen des
Musters innerhalb des Musters selbst. Ein solches Pr ¨aﬁx liegt innerhalb des Musters
beispielsweise dann vor, wenn sich der deterministische Automat aus Abbildung 7.2 in
Zustand ”5“ beﬁndet – dann wurden als letzte Zeichen n ¨amlich ”ka“ gelesen, was ein
Pr¨aﬁx von ”kakaokaki“ ist. Immer dann, wenn sich innerhalb des Musters ein Pr ¨aﬁx
des Musters beﬁndet, kann um mehr als eine Position weitergeschoben werden; dies ist
etwa in der in Abbildung 7.1 dargestellten Situation der Fall. Die Information, um wie

## Seite 232

7.3 Der Knuth-Morris-Pratt-Algorithmus 217
viele Positionen das Muster bei einem Mismatch weitergeschoben werden kann, wird in
der sog. Verschiebetabelle P festgehalten, die wie folgt deﬁniert ist:
P[i ] := max( [k for k in range(len(M)) if M[ :k]==M[i -k +1 :i+1]] +[0]) (7.1)
An der Stelle i der Verschiebetabelle ist also die L ¨ange des (maximalen) Pr ¨aﬁxes ge-
speichert, der sich vor Position i beﬁndet. Die folgende Abbildung verdeutlicht dies:
i
M
k
M[ :k] M[i -k +1 :i+1]==
Aufgabe 7.4
Schreiben Sie auf Basis der (bereits Python-artig formulierten) Formel (7.1) eine
Python-Funktion, die die Verschiebetabelle eines als Parameter¨ubergebenen Musters
berechnet.
Als Beispiel betrachten wir die Verschiebetabelle f ¨ur das Muster M = kakaokaki:
i : 0 1 2 3 4 5 6 7 8
P[i] : 0 0 1 2 0 1 2 3 0
M[i] : k a k a o k a k i
Der Eintrag P[7] ist beispielsweise deshalb ”3“, weil die drei Zeichen vor der Position 7
(n¨amlich 'kak' ein Pr¨aﬁx des Musters sind; zwar ist auch das eine Zeichen (n¨amlich 'k')
an Position 7 ein Pr ¨aﬁx des Musters, Formel (7.1) stellt durch die Maximumsbildung
jedoch sicher, dass immer das l ¨angste Teilwort vor Position i gew¨ahlt wird, das ein
Pr¨aﬁx des Musters ist.
Aufgabe 7.5
Erstellen Sie die Verschiebetabelle f ¨ur die folgenden W ¨orter:
(a) ananas
(b) 010011001001111
(c) ababcabab
7.3.1 Suche mit Hilfe der Verschiebetabelle
Abbildung 7.3 zeigt Situationen in einem Lauf des Knuth-Morris-Pratt-Algorithmus, in
denen das Muster auf Basis der in der Verschiebetabelle enthaltenen Werte weitergescho-

## Seite 233

218 7 Stringmatching
k k k k ia a o a
k k k k ia a o a
q= 7
P[q] = 3
P[q] = 2
q= 3
⇒Match!
q= 7
k k a a o k a k a k a o k a k
k k a a o k a k a k a o k a k
k a k a k a k i
i
i
k
k
k a k a o k a k i
o
q
q
Situation 1:
Situation 2:
Situation 3: k k a a o k a k a k a o k a k i k
q
k a k a o k a k i
Abb. 7.3: Drei ausgew¨ahlte Schritte bei der Suche nach einem Vorkommen von kakaokaki
mit dem Knuth-Morris-Pratt-Algorithmus. Die Zeichen des Musters werden mit den Zeichen
des Textes verglichen. Tritt schließlich ein Mismatch auf (d. h. stimmt ein Zeichen des Musters
nicht mit dem entsprechenden Zeichen des Textes ¨uberein), so wird das Muster weitergeschoben.
Um wie viele Stellen das Muster weitergeschoben werden kann, ist in der Verschiebetabelle P
hinterlegt.
ben wird. Das sind immer Situationen, in denen die jeweilige Stelle von Text und Muster
nicht ¨ubereinstimmen (d. h. Situationen, in denen die Bedingung der while-Schleife in
Listing 7.3 erf ¨ullt ist). Sei q immer die Position im Muster, die zuletzt erfolgreich auf
Gleichheit mit dem Text ¨uberpr¨uft wurde. Betrachten wir die drei in Abbildung 7.3
dargestellten Situationen im Detail:
Situation 1: Muster M und Text T stimmen bisher bis zur Stelle q = 7 ¨uberein. Beim
Vergleich des n¨achsten Zeichens von M mit der n¨achsten Textposition tritt
ein Mismatch auf. Aus der Verschiebetabelle P geht nun hervor, dass die
P[q] = 3 letzten Zeichen vor dem Mismatch ein Pr¨aﬁx (genauer: das maxi-
mal lange Pr¨aﬁx) des Musters darstellen – diese drei Zeichen und auch das
darauf passende Pr ¨aﬁx des Musters sind in Abbildung 7.3 in einem hell
gef¨ullten Rechteck dargestellt. Um mit der Suche fortzufahren, wird nun
die Variable q auf ”3“ gesetzt, was einer Verschiebung des Musters ent-
spricht, wie sie unten in Situation 1 in hell gedruckter Schrift dargestellt
ist.
Situation 2: Muster M und Text T stimmen bisher bis zur Stelle q = 3 ¨uberein. Beim
Vergleich des n¨achsten Zeichens von M mit der n¨achsten Textposition tritt
ein Mismatch auf. Aus der Verschiebetabelle P geht nun hervor, dass die
P[q] = 2 letzten Zeichen vor dem Mismatch ein Pr¨aﬁx des Musters darstel-
len – diese zwei Zeichen und auch das darauf passende Pr ¨aﬁx des Musters
sind in Abbildung 7.3 in einem gelben Rechteck dargestellt. Um mit der
Suche fortzufahren, wird die Variable qauf ”2“ gesetzt, was einer Verschie-
bung des Musters entspricht, wie sie unten in Situation 2 in hell gedruckter
Schrift dargestellt ist.

## Seite 234

7.3 Der Knuth-Morris-Pratt-Algorithmus 219
Situation 3: Muster M und Text T stimmen bisher bis zur Stelle q= 3 ¨uberein. Da sich
auch beim Vergleich von M[−1] mit der entsprechenden Stelle des Textes
T Gleichheit ergab, wird ein Match zur ¨uckgeliefert.
Listing 7.3 zeigt eine Implementierung des Knuth-Morris-Pratt-Algrithmus.
1 def KMP(M,T):
2 P = ... # Berechnung der Verschiebetabelle
3 erg = []
4 q= -1
5 for i in range(len(T)):
6 while q≥0 and M[q +1]̸=T [i]: q=P[q]
7 q +=1
8 if q==len(M) -1:
9 erg.append(i+1 -len(M))
10 q=P[q]
11 return erg
Listing 7.3: Implementierung des Knuth-Morris-Pratt-Algorithmus
In Zeile 2 wird die Verschiebetabelle P berechnet; einen schnellen Algorithmus hierf ¨ur
beschreiben wir im n ¨achsten Abschnitt. Wie auch im Beispiel aus Abbildung 7.3 gehen
wir davon aus, dass q immer die Position im Muster M enth¨alt, die zuletzt erfolgreich
auf Gleichheit mit der entsprechenden Textposition gepr ¨uft wurde; zu Beginn setzen
wir in Zeile 3 also q auf den Wert -1 – es wurde ja noch keine Position des Musters
erfolgreich auf Gleichheit getestet. Die for-Schleife ab Zeile 4 durchl¨auft alle Positionen
des Textes T. Immer dann, wenn die aktuelle Position im Text, alsoT[i] mit der aktuell
zu vergleichenden Position im Muster, also M[q +1], ¨ubereinstimmt, wird q um eins
erh¨oht und die for-Schleife geht in den n¨achsten Durchlauf und es wird mit der n¨achsten
Textposition verglichen. Wenn jedoch M[q +1] nicht mit T[i] ¨ubereinstimmt, so wird
q auf den entsprechenden in der Verschiebetabelle eingetragenen Wert erniedrigt; dies
kann durchaus wiederholt geschehen, solange bis Muster und Text in der nachfolgenden
Position ¨ubereinstimmen.
Aufgabe 7.6
Verwenden Sie Pythons timeit-Modul, um die Laufzeit der in Listing 7.1 gezeig-
ten primitiven Implementierung mit der Knuth-Morris-Pratt-Algorithmus an einigen
praktischen Beispielen zu vergleichen. Was f¨allt auf?
7.3.2 Laufzeit
Wir stellen zun¨achst fest, dass in einem Durchlauf (der insgesamtn= len(T) Durchl¨aufe)
der for-Schleife, die while-Schleife schlimmstenfalls m= len(M)-mal durchlaufen wird,
q also schimmstenfalls in Einerschritten bis -1 erniedrigt wird. Die Gesamtkomplexit ¨at

## Seite 235

220 7 Stringmatching
des Algorithmus ist jedoch nicht in Θ( n·m)1; dies zeigt folgende einfache Amortisati-
onsanalyse.
Die Variable q kann nicht bei jedem Durchlauf der for-Schleife um m Werte erniedrigt
werden. Die Bedingung derwhile-Schleife stellt sicher, dassq immer nur bis zum Wert -1
erniedrigt werden kann. Um es daraufhin erneut zu erniedrigen, muss es zun¨achst erh¨oht
worden sein. Jede Erh ¨ohung von q kann aber nur mit einer nachfolgenden Erh ¨ohung
von i einhergehen. Ein schlimmster denkbarer Fall w ¨are also der, dass q immer in Ei-
nerschritten erniedrigt und danach (zusammen mit i) wieder erh¨oht wird. Der Verlauf
von i (auf der x-Achse) und q (auf der y-Achse) zeigt die folgende Abbildung:
-1
0
i
n1
m
m
1
q
Man erkennt, dass insgesamtnSchritte nach ”oben“ (verursacht durch eine gemeinsame
Erh¨ohung von q und i außerhalb der while-Schleife) und n Schritte nach unten (ver-
ursacht durch eine Erniedrigung von q innerhalb der while-Schleife) gegangen werden.
Der Algorithmus hat also eine worst-case-Komplexit ¨at von O(2 ·n) = O(n).
7.3.3 Berechnung der Verschiebetabelle
Die Berechnung der Verschiebetabelle erfolgt analog zur Knuth-Morris-Pratt-Suche, nur
dass hier das Muster nicht in einem Text, sondern im Muster selbst gesucht wird. Listing
7.4 zeigt eine Implementierung.
1 def VerschTab(M):
2 q = -1 ; P = [q ]
3 for i in range(1,len(M)):
4 while q≥0 and M[q]̸=M[i]: q=P[q]
5 q +=1
6 P.append(q)
7 return P
Listing 7.4: Implementierung der Berechnung der Verschiebetabelle.
1W¨ahrend man mit dem Landau-Symbol O eine obere Schranke beschreibt, kann man mit dem
Landau-Symbol Θ die – bis auf multiplikative und additive Konstanten – exakte Laufzeit eines Algo-
rithmus beschreiben; zur Deﬁnition der Landau-Symbole siehe Abschnitt 1.1.1

## Seite 236

7.4 Der Boyer-Moore-Algorithmus 221
Die Variable i durchl¨auft alle Positionen des Musters M; Die Variable q zeigt immer
auf das Ende des l ¨angsten Pr¨aﬁxes, das mit den Zeichen vor der Position i im Muster
M ¨ubereinstimmt. Unmittelbar nach Zeile 5 gilt immer, dass alle Positionen vor q mit
den q Positionen vor i ¨ubereinstimmen, d. h. es gilt M[ :q]== M[i -q +1 :i+1], d. h. die
Zeichen vor Position i bilden ein Pr ¨aﬁx der L ¨ange q des Musters. Ein entsprechender
Eintrag in die Verschiebetabelle erfolgt in Zeile 6.
Die Laufzeitbetrachtung ist analog zur Suche und betr¨agt Worst-Case O(2·m) = O(m).
7.4 Der Boyer-Moore-Algorithmus
Der Boyer-Moore-Algorithmus wurde einige Jahre nach dem Knuth-Morris-Pratt-Algo-
rithmus entdeckt [3]. Er l ¨asst das Muster von links nach rechts ¨uber den Text laufen
und versucht das Muster bei einem Mismatch um m ¨oglichst viele Positionen weiterzu-
schieben. Er nutzt jedoch die Tatsache aus, dass man mehr Informationen ¨uber Ver-
schiebem¨oglichkeiten erhalten kann, wenn man die Musterpositionen von rechts nach
links mit den aktuellen Textpositionen vergleicht, d. h. Nach einer Verschiebung des Mu-
sters M wird zuerst das Zeichen M[ -1] mit der entsprechenden Textposition verglichen,
dann das Zeichen M[ -2], usw. Durch dieses R¨uckw¨artsvergleichen ist der Boyer-Moore-
Algorithmus – zumindest was die Average-Case-Komplexit¨at betriﬀt – eﬃzienter als der
im letzten Abschnitt vorgestellte Knuth-Morris-Pratt-Algorithmus.
Um nach einem Mismatch zu entscheiden, um wie viele Positionen das Muster weiter-
geschoben werden kann, verwendet der Algorithmus zwei Tabellen: die erste Tabelle
liefert einen Vorschlag gem¨aß der sog. Bad-Character-Heuristik, die zweite Tabelle lie-
fert einen Vorschlag gem¨aß der sog. Good-Suﬃx-Heuristik. Beide Tabellen k¨onnen unter
Umst¨anden verschiedene Vorschl¨age dar¨uber abgeben, wie weit das Muster geschoben
werden kann; der Boyer-Moore-Algorithmus schiebt das Muster um den gr ¨oßeren der
beiden vorgeschlagenen Werte weiter.
7.4.1 Die Bad-Character-Heuristik
Am einfachsten zu konstruieren ist die Sprungtabelle delta1 gem¨aß der sog. Bad-Cha-
racter-Heuristik; diese basiert alleine auf dem Zeichen c des zu durchsuchenden Textes
T, das den Mismatch verursacht hat, d. h. auf dem ersten Zeichen von rechts gesehen,
das nicht mit der entsprechenden Stelle im Muster ¨ubereinstimmt. Kommt c¨uberhaupt
nicht im Muster vor, so kann das Muster an die Stelle nach dem Mismatch weitergescho-
ben werden. Dies tritt etwa in der in Abbildung 7.4 gezeigten ”Situation 2“ ein, die eine
Stringsuche ausschließlich basierend auf der Bad-Character-Heuristik zeigt. Kommt das
Zeichen c, das den Mismatch verursacht, im Muster vor, so wird das Muster so weit nach
rechts verschoben, dass das von rechts gesehen erste Vorkommen von c im Muster mit
dem Mismatch-verursachenden Zeichen c im Text gleichauf liegt. Es kann vorkommen,
dass die Bad-Charakter-Heuristik eine Linksverschiebung des Musters vorschl¨agt – dies
w¨are etwa in ”Schritt 5“ der Fall: das von rechts gesehen erste Vorkommen von ”a“ im
Muster beﬁndet sich hier rechts des Zeichens ”a“ im Text, das den Mismatch ausgel ¨ost
hat; in diesem Fall wird das Muster einfach um eine Position weiterger ¨uckt.

## Seite 237

222 7 Stringmatching
k a k a o k a k i
k a k ik a k a o
k a k ik a k a o
k k k k a o a ok a k a o k o k i x
k k k k a o a ok a k a o k o k i x
k k k k a o a ok a k a o k o k i x
k a k a o k a k i
k k k a o a - i s t - oSchritt 1:
Schritt 5:
k a k a o k a k i
Schritt 3:
Schritt 4:
Schritt 2: k k k k a o a - i s t - ok a k a o k o k i x
- i s t -
k k k k a o a - i s t - ok a k a o k o k i x
k a k a k a k i
k a k a k a k i
k a k a o a k i a
a
a
k a k a k a k i a s
s
s
s
Schritt 6:
- i s t - k a k a o a k i a s
- i s t - k a k a o a k i
k a k a o k a k i
a s
k xk a k a o k o k i
Abb. 7.4: Es sind die sechs Suchschritte dargestellt, die notwendig sind, um das Muster
kakaokaki in einem bestimmten Text alleine mit Hilfe der Bad-Charakter-Heuristik zu su-
chen. F ¨ur jeden Schritt ist jeweils immer der Text oben und das Muster unter dem Teil des
Textes dargestellt, der auf Gleichheit mit dem Muster ¨uberpr¨uft wird. Das Zeichen, das den
Mismatch verursacht und das dazu passende Zeichen im Muster ist jeweils farbig hinterlegt.
Aufgabe 7.7
Angenommen, wir suchen nach einem Muster M der L ¨ange m in einem Text T
der L¨ange n und angenommen alle mit M[−1] verglichenen Zeichen kommen nicht
im Muster vor – mit zunehmender Gr ¨oße des verwendeten Alphabets wird dieser
Fall nat¨urlich wahrscheinlicher. Wie viele Suchschritte ben ¨otigt der Boyer-Moore-
Algorithmus, bis er festgestellt hat, dass das Muster nicht im Text vorkommt?
Aufgabe 7.8
Es stehe an f¨ur die n-malige Wiederholung des Zeichens ”a“. Wie viele Suchschritte
ben¨otigt der Boyer-Moore-Algorithmus um . . .
(a) . . . das Muster ba9 (also das Muster baaaaaaaaa) im Text a1000 (also einem Text
bestehend aus 1000 as) zu ﬁnden?
(b) . . . das Muster a9b (also das Muster aaaaaaaaab) im Text a1000 zu ﬁnden?
(c) . . . das Muster a9b (also das Muster aaaaaaaaab) im Text c1000 zu ﬁnden?

## Seite 238

7.4 Der Boyer-Moore-Algorithmus 223
Folgendes Listing zeigt die Implementierung der Bad-Character-Heuristik.
1 def makedelta1(M):
2 delta1 = {}
3 for i in range(len(M) -1):
4 delta1 [M[i]] = i
5 return delta1
6
7 def badChar(delta1,c,j ):
8 if c in delta1 :
9 return j -delta1 [c ]
10 else:
11 return j +1
Listing 7.5: Berechnung der Sprungtabelle gem ¨aß der Bad-Character-Heuristik
Die Funktion makedelta1 erstellt f¨ur ein bestimmtes Muster M einmalig eine Sprungta-
belle delta1, die sie als Dictionary-Objekt repr ¨asentiert zur¨uckliefert. Die for-Schleife
ab Zeile 3 durchl ¨auft alle Positionen i des Musters und erstellt in der Sprungtabelle
f¨ur das i-te Zeichen M[i] des Musters einen Eintrag mit Wert i. Weiter rechts auftre-
tende Vorkommen dieses Zeichens ¨uberschreiben diesen Eintrag und so enth ¨alt nach
Ende der for-Schleife der Eintrag delta1 [c ] automatisch die von rechts gesehen erste
Position eines Vorkommens von c im Muster. Der Wert dieser Position ist entscheidend
zur Bestimmung der Verschiebepositionen des Musters.
Die Funktion badChar kann nun basierend auf der Verschiebetabelle delta1, dem ”Bad
Character“ c und der Position j des Mismatches im Muster die Anzahl der Postionen
bestimmen, die das Muster weitergeschoben werden darf. Gibt es einen Eintrag c in
delta1, d. h. kommt c im Muster vor, so kann das Muster um j -delta1[c] Positionen
nach rechts verschoben werden. Dadurch deckt sich das am weitesten rechts beﬁndliche
Vorkommen von c im Muster mit dem Mismatch des Textes. F ¨ur den Fall, dass dieser
Verschiebewert negativ ist (wie dies etwa in ”Situation 5“ aus Abbildung 7.4 der Fall
ist), wird einfach ”1“ zur ¨uckgegeben. Sollte delta1 keinen Eintrag f ¨ur das Zeichen c
enthalten, gilt also c not in delta1, so wird der else-Zweig ab Zeile 10 gegangen und
der Wert j +1 zur ¨uckgeliefert. Das Muster kann in diesem Fall also an die auf den
Mismatch folgende Stelle weitergeschoben werden.
Tabelle 7.1 zeigt die R ¨uckgabewerte von delta1 und der Funktion badChar f¨ur die in
Abbildung 7.4 dargestellten Beispielsituationen. Wie man sieht, entspricht der R ¨uck-
gabewert der Funktion badChar genau den Verschiebepositionen des Musters in der
jeweiligen Situation.

## Seite 239

224 7 Stringmatching
Situation 1 Situation 2 Situation 3
delta1 ['o' ]=4 delta1 ['x' ]=KeyError delta1 ['-' ]=KeyError
badChar(d1,'o',6)=2 badChar(d1,'x',8)=9 badChar(d1,'-',7)=8
Situation 4 Situation 5 Situation 6
delta1 ['o' ]=4 delta1 ['a' ]=6 delta1 ['s' ]=KeyError
badChar(d1,'o',8)=4 badChar(d1,'a',5)=max(-1,1) badChar(d1,'s',8)=9
Tabelle 7.1:R¨uckgabewerte der in Listing 7.5 gezeigten Funktionen f¨ur die Beispielsituationen
aus Abbildung 7.4.
Aufgabe 7.9
(a) Geben Sie eine alternative Implementierung der in Listing 7.5 gezeigten Funktion
makedelta1 an, die f¨ur jedes Zeichen des verwendeten Alphabets einen passenden
Eintrag enth ¨alt und so eine entsprechende Abfrage in der Funktion badChar
vermeidet.
(b) Testen sie die Perfomance der beiden Implementierungen aus den ersten bei-
den Teilaufgaben zusammen mit der in Listing 7.5 gezeigten Implementierung.
Welche Variante ist die schnellste? Warum?
7.4.2 Die Good-Suﬃx-Heuristik
Die etwas komplexer zu konstruierende zweite Tabelle gibt Verschiebevorschl¨age gem¨aß
der sog. Good-Suﬃx-Heuristik. W ¨ahrend die Bad-Character-Heuristik das Zeichen c,
das den Mismatch verursacht, in Betracht zieht, zieht die Good-Suﬃx-Heuristik den
¨ubereinstimmenden Teil von Muster und Text rechts des Zeichens c in Betracht – den
”hinteren“ Teil des Musters also, sprich: das Suﬃx. Die Good-Suﬃx-Heuristik schl ¨agt
eine Verschiebung des Musters so vor, so dass ein weiter links stehender mit diesem
”Good-Suﬃx“ ¨ubereinstimmender Teil des Musters auf dieser Textstelle liegt. Abbil-
dung 7.5 zeigt als Beispiel das Muster”entbenennen“ und einige Mismatch-Situationen.
Wie man sieht, wird nach jedem Mismatch das Muster so verschoben, dass ein weiter
links stehender Teil des Musters, auf dem ”Good-Suﬃx“ (d. h. den Suﬃx des Musters,
der mit dem Text ¨ubereinstimmt) liegt.
Schauen wir uns nun etwas systematischer an, wie die Verschiebetabelle f ¨ur das Bei-
spielmuster M='entbenennen' erstellt wird. Wir bezeichnen hierf ¨ur mit j die L¨ange
des mit dem Text ¨ubereinstimmenden Suﬃxes des Wortes entbenennen; j = 0 bedeutet
also, dass schon das von rechts gesehen erste Zeichen des Musters nicht mit dem Text
¨ubereinstimmt; j = len(M) -1 bedeutet, dass alle Zeichen des Musters mit dem Text
¨ubereinstimmen, d. h. ein Match gefunden wurde. Das von rechts gesehen erste nicht
mehr matchende Zeichen des Suﬃxes stellen wir durchgestrichen dar. Den im Muster
weiter links beﬁndlichen Teil, der mit dem Suﬃx – inklusive der Mismatch-Stelle –
¨ubereinstimmt, stellen wir unterstrichen dar. Wir stellen uns ferner virtuelle Muster-
positionen vor dem ersten Eintrag M[0] des Musters vor, die wir mit ”·“ notieren; wir

## Seite 240

7.4 Der Boyer-Moore-Algorithmus 225
e n t b e n e n n e nf e h l e r - s e h e-n e n - k l e i n e n n - i m - n e n t b e n e n n e n
e n t b e n e n n e nf e h l e r - s e h e-n e n - k l e i n e n n - i m - n e n t b e n e n n e n
f e h l e r - s e h e-n e n - k l e i n e n n - i m - n e n t b e n e n n e ne n t b e n e n n e n
f e h l e r - s e h e-n e n - k l e i n e n n - i m - n e n t b e n e n n e ne n t b e n e n n e n
e n t b e n e n n e nf e h l e r - s e h e-n e n - k l e i n e n n - i m - n e n t b e n e n n e n
Situation 12
Situation 3
Situation 2
Situation 1
Situation 13
Abb. 7.5: Beispiele f ¨ur Mismatch-Situationen und entsprechende Verschiebungen gem ¨aß der
Good-Suﬃx-Heuristik.
nehmen an, dass das Zeichen ”·“ mit jedem beliebigen Zeichen (auch mit einem durch-
gestrichenen) matcht; diese virtuellen Musterpositionen werden etwa in F ¨allen i ≥4
mit einbezogen.
j = 0: Das matchende Suﬃx ist also n. Der am weitesten rechts beﬁndliche Teilstring
von entbenennen, der auf n passt, ist das Zeichen ”e“ an Stringposition 9. Durch
Verschiebung des Musters um eine Position kann dieses Zeichen mit n in Deckung
gebracht werden. Daher schl¨agt die Good-Suﬃx-Strategie hier eine Verschiebung
um eine Position vor.
j = 1: Das matchende Suﬃx ist also en. Der am weitesten rechts beﬁndliche passende
Teilstring ist entbenennen. Durch eine Verschiebung um 2 Positionen kann dieser
mit dem matchenden Suﬃx in Deckung gebracht werden.
j = 2: Das matchende Suﬃx ist also nen. Der am weitesten rechts beﬁndliche passende
Teilstring ist entbenennen. Durch eine Verschiebung um 5 Postionen kann dieser
mit dem Suﬃx in Deckung gebracht werden.
j = 3: Das matchende Suﬃx ist also nnen. Der passende Teilstring ist entbenennen.
Durch eine Verschiebung um 3 Positionen kann dieser mit dem matchenden Suﬃx
in Deckung gebracht werden.
j = 4: Das matchende Suﬃx ist also ennen. Eigentlich gibt es keinen passenden Teil-
string; durch oben beschriebene Expansion des Musters kann man sich den ”pas-
senden“ Teilstring jedoch denken als ···entbennenen. Um den ”passenden“ Teil
···en mit dem matchenden Suﬃx in Deckung zu bringen, muss das Muster um 9
Positionen nach rechts verschoben werden.

## Seite 241

226 7 Stringmatching
j = 5: Das matchende Suﬃx ist also nennen. Genau wie im Fall j = 4 ist auch hier der
passende Teilstring ···· entbennenen; entsprechend wird auch hier eine Verschie-
bung um 9 vorgeschlagen.
j = 6,j = 7,j = 8,j = 9: Mit analoger Argumentation wird auch hier jeweils eine Ver-
schiebung um 9 vorgeschlagen.
Die in Listing 7.6 gezeigte Funktion makedelta2 implementiert die Berechnung der
Verschiebetabelle (die als Dictionary-Objekt delta2 zur¨uckgeliefert wird) gem ¨aß der
Good-Suﬃx-Heuristik. Im j-ten Durchlauf der for-Schleife ab Zeile 9 wird der Eintrag
delta2 [j ] berechnet; dieser gibt die Verschiebung an, falls ein ”Good-Suﬃx“ der L¨ange
j erkannt wurde. Die Variable suﬃx enth¨alt immer die Zeichen des ”Good-Suﬃx“ und
die Variable mismatch enth¨alt das von rechts gesehen erste Zeichen, das nicht mehr
gematcht werden konnte (oben immer durch ein durchgestrichenes Zeichen notiert). In
der for-Schleife ab Zeile 12 werden dann alle Musterpositionen k von rechts nach links
durchlaufen und mittels der unify-Funktion ¨uberpr¨uft, ob der an Stelle k beﬁndliche
Teilstring des Musters zu dem ”Good-Suﬃx“ passt. Falls ja, wird der passende Ver-
schiebebetrag in delta2 [j ] gespeichert und die ”for k“-Schleife mittels break verlassen
– so ist sichergestellt, dass der am weitesten rechts beﬁndliche Teilstring von M gefun-
den wird, der auf das Suﬃx passt. Immer dann, wenn zwischen der Position k und der
Position 0 sich weniger als j Zeichen beﬁnden, werden links von Position 0 entsprechend
viele ”DOT“s angeh¨angt; dies geschieht in Zeile 13.
1 DOT=None
2 def unify(pat,mismatch,suﬃx):
3 def eq(c1,c2): return c1==DOT or c1==c2
4 def not eq(c1,c2): return c1==DOT or c1̸=c2
5 return not eq(pat[0],mismatch) and all(map(eq,pat[1:], suﬃx ))
6
7 def makedelta2(M):
8 m = len(M) ; delta2 = {}
9 for j in range(0,m): # Suﬃx der L ¨ange j
10 suﬃx = [] if j==0 else M[ -j:]
11 mismatch = M[ -j -1]
12 for k in range(m-1,0, -1):
13 pat = [DOT for i in range(-k +j)] +list(M[max(0,k -j):k +1])
14 if unify(pat,mismatch,suﬃx): # Good−Suﬃx im Muster gefunden!
15 delta2 [j ]=m -1 -k ; break
16 if j not in delta2: delta2 [j ]=m
17 return delta2
Listing 7.6: Implementierung der Good-Suﬃx-Heuristik

## Seite 242

7.4 Der Boyer-Moore-Algorithmus 227
Aufgabe 7.10
Beantworten Sie folgende Fragen zu Listing 7.6:
(a) Erkl ¨aren Sie die Zuweisung in Zeile 10; was w ¨urde passieren, wenn diese einfach
” suﬃx = M[ -j :]“ heißen w ¨urde?
(b) Welchen Typ hat der Paramter pat im Aufruf der Funktion unify in Zeile 13?
Welchen Typ hat der Parameter suﬃx ?
(c) Es sei M = 'ANPANMAN'. Was sind die Werte von suﬃx und mismatch und in
welchem Durchlauf bzw. welchen Durchl ¨aufen der ”for k“-Schleife liefert dann
der Aufruf von unify den Wert True zur¨uck, wenn wir uns . . .
1. . . . im for-Schleifendurchlauf f¨ur j=1 beﬁnden.
2. . . . im for-Schleifendurchlauf f¨ur j=2 beﬁnden.
Die Funktion unify pr¨uft, ob der Teilstring pat des Musters (der ggf. links mit DOTs
aufgef¨ullt ist) mit dem ”Good-Suﬃx“ suﬃx und dem den Mismatch verursachenden
Zeichen mismatch ”vereinbar“ ist. Wichtig ist, dass die eigens deﬁnierten Gleichheits-
und Ungleichheitstests eq bzw. not eq bei einem Vergleich mitDOT immer True zur¨uck-
liefern.
7.4.3 Implementierung
Listing 7.7 zeigt die Implementierung der Stringsuche mit Hilfe der Bad-Character-
Heuristik delta1 und der Good-Suﬃx-Heuristik delta2. F¨ur jeden Durchlauf der while-
Schleife ist i die Position im Text T und j die Position im Muster M die miteinander
verglichen werden. Die Variable i old enth¨alt immer die Position im Text, die als erstes
mit dem Muster verglichen wurde (d. h. die Position im Text, die ¨uber dem rechtesten
Zeichen des Musters M liegt). Nach Durchlauf der while-Schleife in Zeile 7 zeigen i
und j auf die von rechts gesehen erste Mismatch-Stelle von Text und Muster. Gibt
es keine Mismatch-Stelle (gilt also j== -1 nach dem while-Schleifendurchlauf) wurde
das Muster im Text gefunden. Andernfalls wird i in Zeile 13 um den durch die Bad-
Character-Heuristik bzw. die Good-Suﬃx-Heuristik vorgeschlagenen Verschiebebetrag
erh¨oht.
1 def boyerMoore(T,M):
2 delta1 = makedelta1(M)
3 delta2 = makedelta2(M)
4 m = len(M) ; n = len(T) ; i=m -1
5 while i < n:
6 i old =i ; j=m -1
7 while j≥0 and T[i] == M[j]:
8 i -=1 ; j -=1
9 if j== -1:
10 print "Treffer: ",i +1

## Seite 243

228 7 Stringmatching
11 i = i old +1
12 else:
13 i = i old +max(badChar(delta1,T[i],j), delta2[m -1 -j])
Listing 7.7: Implementierung des Boyer-Moore-Algorithmus
Aufgabe 7.11
Modiﬁzieren Sie die in Listing 7.7 vorgestellte Funktion boyerMoore so, dass sie die
Liste aller Matches des Musters M im Text T zur¨uckliefert.
Aufgabe 7.12
Gerade f¨ur den Fall, dass man mit einem bestimmten Muster komfortabel mehrere
Suchen durchf¨uhren m¨ochte, bietet sich eine objekt-orientierte Implementierung mit-
tels einer Klasse BoyerMoore an, die man beispielweise folgendermaßen anwenden
kann:
>>>p = BoyerMoore('kakaokaki')
>>>p.search(T1)
... .
>>>p.search(T2)
Implementieren Sie die Klasse BoyerMoore.
7.4.4 Laufzeit
Wie viele Suchschritte ben ¨otigt der Boyer-Moore-Algorithmus zum Finden aller Vor-
kommen des Musters M (mit m= len(M)) im Text T (mit n= len(T))?
Im g¨unstigsten Fall sind dies lediglich O(n/m) Schritte – dann n¨amlich, wenn entweder
”viele“ Zeichen des Textes gar nicht im Muster vorkommen oder wenn ”viele“ Suﬃxe
kein weiteres Vorkommen im Muster haben; in diesen F ¨allen wird eine Verschiebung
um m Positionen vorgeschlagen.
Im Worst-Case ben¨otigt der Boyer-Moore-Algorithmus etwa 3nSchritte; die mathema-
tische Argumentation hierf¨ur ist nicht ganz einfach und es brauchte auch immerhin bis
ins Jahr 1991, bis diese gefunden wurde; wir f ¨uhren diese hier nicht aus und verweisen
den interessierten Leser auf die entsprechende Literatur [6]. Die Worst-Case-Laufzeit
ist also in O(n).
7.5 Der Rabin-Karp-Algorithmus
Der Rabin-Karp-Algorithmus geht einen ganz anderen Weg, um ein Muster in einem
Text zu suchen: Er berechnet unter Verwendung einer Hashfunktion h den Hashwert

## Seite 244

7.5 Der Rabin-Karp-Algorithmus 229
h(M) des Musters M, und sucht nach Stellen im Text T, die denselben Hashwert auf-
weisen. Wird die Hashfunktion hgeschickt gew¨ahlt, so ist mit diesem Algorithmus eine
gute Laufzeit gesichert.
Der Rabin-Karp-Algorithmus ist zwar in vielen F ¨allen – was die Performance betriﬀt –
dem Boyer-Moore-Algorithmus unterlegen, es gibt jedoch einige F¨alle, in denen sich der
Einsatz des Rabin-Karp-Algorithmus lohnt. Dies betriﬀt insbesondere die Suche sehr
langer (evtl. auch mehrerer) Muster in einem Text. Denkbar w ¨are etwa der Einsatz
in einer Software, die Dokumente automatisch nach Plagiaten ¨uberpr¨uft, indem sie
mehrere l¨angere (Original-)Textausschnitte in dem zu ¨uberpr¨ufenden Text sucht.
7.5.1 Rollender Hash
Ein rollender Hash ist eine Hashfunktion, die ihre Eingabe aus einem ”Fenster“ kon-
stanter Gr¨oße bezieht, das von links nach rechts ¨uber die Eingabe geschoben wird.
f e h l e r - s e h e-n e n - k l e i n e n n - i m - n e n t b e n e n n e n
f e h l e r - s e h e-n e n - k l e i n e n n - i m - n e n t b e n e n n e n
f e h l e r - s e h e-n e n - k l e i n e n n - i m - n e n t b e n e n n e nh(nen-kleinen)
h(en-kleinen-)
h(n-kleinen-f)
Zur Implementierung des Rabin-Karp-Algorithmus gen ¨ugt die Verwendung einer sehr
einfachen rollenden Hashfunktion h, die einen String s folgendermaßen abbildet:
h(s) = Bk−1s[0] + Bk−2s[1] + ... + B1s[k−2] + B0s[k−1] mod p (7.2)
Um das aufw ¨andige Rechnen mit sehr großen Zahlen zu vermeiden, rechnet die Has-
hfunktion mit modularer Arithmetik; entscheidend ist hier die Wahl der Basis B und
die Wahl von p. Aus Performance-Gr¨unden ist es sinnvoll eine Zweierpotenz als p, d. h.
p = 2k, zu w ¨ahlen. Die modulare Arithmentik mit einer solchen Zweierpotenz 2 k ent-
spricht n¨amlich einfach dem Abschneiden der bin¨aren Stellen ab Position k. Dies kommt
der nat ¨urlichen Funktionsweise eines Rechner auf Ebene der Maschinensprache nahe:
Entsteht bei einer arithmetischen Berechnung ein¨Uberlauf, so werden die h¨oherwertigen
Stellen einfach abgeschnitten. In Python k ¨onnen wir dieses Abschneiden der h ¨oherwer-
tigen Stellen durch eine bin¨are Und-Verkn¨upfung mit der Zahl 2 k−1 erreichen. Es gilt
also:
x mod 2k = x & 11 ······ 1
 
k−mal
b = x & (2k −1)
Wir w¨ahlen also im Folgenden p= M = 2k−1 und ein k ∈N. Konkret k ¨onnten B und
M etwa wie folgt gew¨ahlt werden:
B = 103
M= 2**16 -1

## Seite 245

230 7 Stringmatching
Aufgabe 7.13
W¨are auch die Konstante sys.maxint (aus dem Modul sys) ein sinnvoller Wert f ¨ur
M? Begr¨unden Sie.
Listing 7.8 zeigt eine primitive Implementierung dieser Hashfunktion. Die for-Schleife
durchl¨auft den zu hashenden String s r¨uckw¨arts; die Variable i enth¨alt hierbei immer
den von rechts gez ¨ahlten Index, der als Potenz der Basis B verwendet wird. In jedem
while-Schleifendurchlauf wird durch die Zuweisung h = h &M sichergestellt, dass nur
die k niederwertigsten Bits weiter verwendet werden (um das aufw ¨andige Rechnen mit
sehr großen Zahlen zu vermeiden).
Durch Verwendung des sog. Horner-Schemas (siehe auch Abschnitt 3.4.1 auf Seite 74)
kann die Berechnung dieses Hashwertes deutlich schneller erfolgen. Anstatt Formel 7.2
direkt zu implementieren ist es g ¨unstiger, die folgende Form zu verwenden, in der die
B-Werte soweit als m¨oglich ausgeklammert sind:
h(s) = (((s[0] ·B+ s[1]) ·B+ ...) ·B+ s[k−2]) ·B+ s[k−1] mod p (7.3)
Listing 7.9 zeigt die Implementierung des Horner-Schemas mittels der reduce-Funktion.
1 def rollhash(s ):
2 h = 0
3 for i ,c in enumerate(s[:: -1]):
4 h += (B**i) *ord(c)
5 h = h &M
6 return h
Listing 7.8: Primitive Berech-
nung der Hashfunktion
1 def rollhash2(s ):
2 return reduce(
3 lambda h,c: (c +B *h) &M,
4 map(ord,s))
Listing 7.9: Berechnung der Hashfunktion mittels
des Horner-Schemas
Aufgabe 7.14
Verwenden sie Pythons timeit-Modul, um die Laufzeiten der in Listing 7.8 und 7.9
gezeigten Funktionen rollhash und rollhash2 zu vergleichen. Vergleichen Sie die Werte
der timeit-Funktion f¨ur einen String S mit L¨ange 10, L¨ange 20 und L ¨ange 50.
Angenommen in einem langen Suchtext T ist momentan der Hash h eines ”Fensters“
an Position i der L ¨ange l berechnet, d. h. es gilt h = h(s[i : i+ l]). Will man nun
dieses ”Fenster“ dessen Hash h berechnet werden soll nach rechts bewegen, so erh ¨alt
man den entsprechenden neuen Hashwert durch Subtraktion des Wertes bl−1s[i], einer
nachfolgenden Multiplikation dieses Wertes mit der Basis b und einer Addition mit
s[i+ l]; alle Rechnungen erfolgen mit modularer Arithmetik; der Wert h muss also
folgendermaßen angepasst werden:
h= (h−Bl−1s[i]) ·B+ s[i+ l] (7.4)

## Seite 246

7.5 Der Rabin-Karp-Algorithmus 231
Will man dagegen dieses ”Fenster“ dessen Hash h berechnet werden soll nach links
bewegen, so erh ¨alt man den entsprechenden neuen Hashwert durch Subtraktion des
Wertes b0s[i+ l−1], einer nachfolgenden Division durch die Basis b (d. h. einer Multi-
plikation mit b−1) und einer abschließenden Addition mit bl−1s[i−1]; der Wert hmuss
also folgendermaßen angepasst werden:
h= (h−B0s[i+ l−1]) ·B−1 + Bl−1s[i−1] (7.5)
7.5.2 Implementierung
Listing 7.10 zeigt eine Implementierung des Rabin-Karp-Algorithmus in Form der Funk-
tion rabinKarp. Diese erh¨alt zwei Parameter: eine Liste von Mustern Ms, und ein Text
T, der nach Vorkommen der Muster durchsucht werden soll. Wir gehen hier davon aus,
dass alle in Ms beﬁndlichen Mustern die gleiche L ¨ange haben.
1 def rabinKarp(Ms,T):
2 hashs = set(map(rollhash,Ms))
3 l = len(Ms[0])
4 h = rollhash(T[:l ])
5 i=0
6 if h in hashs:
7 if T[i:i +l] in Ms: print "Treffer bei", i
8 while i +l<len(T) -1:
9 h = (h -ord(T[i]) *B**(l-1)) *B +ord(T[i +l]) &M
10 i +=1
11 if h in hashs:
12 if T[i:i +l] in Ms: print "Treffer bei", i
Listing 7.10: Implementierung des Rabin-Karp-Algorithmus
In Zeile 2 wird mittels der map-Funktion der Hashwert jedes in Ms gespeicherten
Musters berechnet und in einer Menge hashs gespeichert; die Verwendung eines set-
Objektes macht hier insbesondere aus Performance-Gr¨unden Sinn, da so unter Anderem
der Test auf Enthaltensein (der ja innerhalb der while-Schleife in Zeile 11 wiederholt
durchgef¨uhrt werden muss) laufzeitoptimiert ist. Anfangs wird in Zeile 4 der Hashwert
der ersten l Zeichen des Textes T berechnet. Jeder while-Schleifendurchlauf schiebt
dann das ”Fenster“ der zu hashenden Zeichen in T um eine Position nach rechts. In
Zeile 9 wird hierf ¨ur der Hashwert gem ¨aß Formel (7.4) angepasst. Immer dann, wenn
der Hashwert h des ”Fensters“ in der Menge hashs zu ﬁnden ist, ist es wahrscheinlich –
jedoch keineswegs sicher –, dass eines der Muster gefunden wurde; um sicher zu gehen,
dass sich an dieser Stelle auch tats ¨achlich eines der Muster beﬁndet, muss der unge-
hashte Text mit den Mustern abgeglichen werden; dies geschieht in den Zeilen 7 und
12.
Wurden die Basis B und das Modul M geschickt gew¨ahlt, so sollte es sehr selten vor-
kommen, dass ”h in hashs“ jedoch nicht ”T[i :i +l] in Ms“ gilt. Somit kann man davon
ausgehen, dass die Laufzeit des Rabin-Karp-Algorithmus in O(n) liegt.

## Seite 247

232 7 Stringmatching
7.6 Der Shift-Or-Algorithmus
Der erst 1992 beschriebene Shift-Or-Algorithmus [17] nutzt Bitoperationen und arbeitet
entsprechend ¨außerst eﬃzient. Eine Variante dieses Stringmatching-Algorithmus ver-
wendet das Unixtool grep.
Der Shift-Or-Algorithmus simuliert einen nichtdeterministischen endlichen Automaten
(NEA) . Im Gegensatz zum deterministischen endlichen Automaten (DEA), der f ¨ur je-
des Eingabezeichen immer eindeutig einen Zustands¨ubergang w¨ahlt, also jeder Zustand
genau |A|Ausgangskanten – eine f¨ur jedes Zeichen des Alphabets – besitzen muss, gibt
es solche Beschr¨ankungen bei NEAs nicht. Beispielsweise erkennt folgender NEA Vor-
kommen des Wortes ananas:
a a n n a s
A
2 31 0 1 4 5 6
Der Nichtdeterminismus dieses Automaten zeigt sich beispielsweise dann, wenn er sich
in Zustand ”0“ beﬁndet und das Eingabezeichen ”a“ liest; dann gibt es n ¨amlich zwei
m¨ogliche Zustands ¨uberg¨ange: Er kann entweder ¨uber die mit ”a“ beschriftete Kante
in Zustand ”1“ wechseln oder er kann ¨uber die mit ”A“ beschriftete Kante 2 im Zu-
stand ”0“ verbleiben. Man sagt, ein NEA akzeptiert ein bestimmtes Wort w, wenn der
Endzustand durch Lesen der Buchstaben in w erreichbar ist.
Aufgabe 7.15
Erstellen Sie einen deterministischen endlichen Automaten, der Vorkommen des Wor-
tes ananas erkennt.
Enth¨alt der nichtdeterministische Automat m Zust¨ande, so wird die Menge der nach
Lesen der ersten jZeichen des Textes (also nach Lesen vonT[ :j]) erreichbaren Zust¨ande
in einem m-Bit-breiten Datenwort Z kodiert. Hierbei enth¨alt das von rechts geseheni-te
Bit von Z genau dann eine Eins, wenn Zustand i∈{0,...,m −1}des NEA durch Lesen
von T[ :j] erreichbar ist. Wird ein Zustand Z erreicht, dessen Bit an Position ”Null“
gesetzt ist (d. h. Z = 1 z1 z2 ··· zm−1), dann ist der Endzustand m−1 erreichbar, und
es wurde an der momentanen Textposition ein Vorkommen des Wortes erkannt.
Wie genau wird nun die Funktionsweise des NEA simuliert? Hierf¨ur assoziieren wir mit
jedem Buchstaben x∈Ades Alphabets Aeinen sog. charakteristischen Vektor b[x], der
folgendermaßen deﬁniert ist:
b[x]i =
{
1, falls M[ -i]== x
0, sonst
2Kanten k¨onnen auch mit Zeichen-Mengen beschriftet sein; eine solche Kante kann immer dann
gegangen werden, wenn eines der in der Menge beﬁndlichen Zeichen gelesen wurde.

## Seite 248

7.6 Der Shift-Or-Algorithmus 233
F¨ur das Muster ananas ¨uber dem Alphabet A= {a,..., z}h¨atten die charakteristischen
Vektoren die folgende Form:
b[a] = 0 1 0 1 0 1
b[n] = 0 0 1 0 1 0
b[s] = 1 0 0 0 0 0
b[x] = 0 0 0 0 0 0 f¨ur x∈A\{a, n,s}
Der Shift-Or-Algorithmus speichert die charakteristischen Vektoren – ebenso wie die
Zust¨ande – in einem Datenwort der Breite m.
Der Algorithmus beginnt in Zustand”0 0 0 0 0 0“, initialisiert die VariableZ also mit dem
Wert ”0“. Beﬁndet sich der Algorithmus nach Lesen der ersten j Zeichen des Textes
T in Zustand Z und liest er anschließend das Zeichen T[j], so erh ¨alt man den neuen
Zustand dadurch, indem man die folgenden bit-basierten Operationen ausf ¨uhrt:
1. Die Bits des alten Zustands werden um eine Position nach links verschoben – dies
entspricht beim NFA dem Weitr ¨ucken um (jeweils) einen Zustand im Skelettau-
tomaten. Zus¨atzlich wird das rechteste Bit auf Eins gesetzt – dies entspricht dem
Weiterr¨ucken des Zustands ”0“ in den Zustand ”1“.
2. Dieses Weiterr ¨ucken ist jedoch nur dann ”erlaubt“, wenn das Zeichen, mit dem
der Zustands ¨ubergang markiert ist, gelesen wurde. Daher erfolgt eine bitwei-
se UND-Verkn¨upfung der verschobenen Bits mit dem charakteristischen Vektor
b [T[j] ] des aktuellen Zeichens T[j]. Nur dann n ¨amlich, wenn die passenden Zu-
stands¨uberg¨ange mit dem Zeichen T[j] markiert sind, k ¨onnen die Zust ¨ande eine
Position weiterger¨uckt werden.
Betrachten wir zur Illustration die folgende Beispielsituation: Wir nehmen an, dass
durch den bisher gelesenen Text im NEA die Zust ¨ande ”1“, ”3“ und ”5“ erreichbar
w¨aren und als N¨achstes das Zeichen ”n“ gelesen wird – diese Situation ist in Abbildung
7.6(a) dargestellt. Der entsprechende Kreuzproduktautomat des obigen Beispiel-NEA
hat insgesamt 2m Zust¨ande, die mit Teilmengen der Zust ¨ande des NEA markiert sind.
Dieser Kreuzproduktautomat w¨urde sich in eben beschriebener Beispielsituation in Zu-
stand ”{1,3,5}“ beﬁnden; dies w ¨urde im Falle des Shift-Or-Algorithmus dem Zustand
Z = 0 1 0 1 0 1 (bzw. in DezimalschreibweiseZ = 21) entsprechen – also das von rechts
gesehen erste, dritte und f ¨unfte Bit des Zustands w ¨aren gesetzt; durch Lesen des Zei-
chens ”n“ gelangt der Kreuzproduktautomat in Zustand ”{2,4}“ – der entsprechende
Ausschnitt des Kreuzproduktautomaten ist in Abbildung 7.6(b) dargestellt. Abbildung
7.6(c) zeigt das Weiterr¨ucken der Zust¨ande auf Bitebene (durch Anwendung der Opera-
tion ”< <1|1“) und das anschließende Ausﬁltern derjenigen ¨Uberg¨ange, die durch Lesen
des Zeichens ”n“ erlaubt sind; dies geschieht durch die bitweise UND-Verkn ¨upfung mit
dem charakteristischen Vektor b[n]).
Abbildung 7.7 zeigt einen Beispiellauf des Shift-Or-Algorithmus, der zeigt, wie das Mu-
ster ”ananas“ im Text ”anananas“ gesucht wird. Es ist f¨ur jeden Leseschritt immer das
Ergebnis der ”< <1|1“-Operation, der charakteristische Vektor des gelesenen Zeichens
und deren bitweise UND-Verkn¨upfung dargestellt, woraus sich der n ¨achste Zustand er-
gibt.

## Seite 249

234 7 Stringmatching
a a n n a s
A
1 61 3 52 40
(a) Beispiel-Situation w¨ahrend eines Durchlaufs des NEA.
n{1,3,5} {2, 4}
(b) Beispiel-Situation w¨ahrend des Durchlaufs des entsprechenden Kreuzproduktautomaten.
0 1 0 1 0 1
< <1 |1
−→ 1 0 1 0 1 1−→
Z : 1 0 1 0 1 1
b[n] : 0 0 1 0 1 0&
0 0 1 0 1 0
(c) Entsprechende Bit-basierte Operationen um vom alten Zustand ”{1,3,5}“ nach Lesen des Eingabe-
zeichens ”n“ zum neuen Zustand ”{2,4}“ zu kommen. Im ersten Schritt werden die Bits um eine Position
nac links verschoben und durch die Oder-Operation das rechteste Bit gesetzt. Im zweiten Schritt erfolgt
eine bitweise UND-Verkn¨upfung mit dem charakteristischen Vektor des gelesenen Zeichens ”n“.
Abb. 7.6: Darstellung der folgenden Beispielsituation: Nach dem Lesen des bisherigen Einga-
betextes sind die Zust ¨ande ”1“, ”3“ und ”5“ des NEA erreichbar und das Zeichen ”n“ wurde
gelesen. Abbildung 7.6(a) stellt dies am NEA direkt dar, Abbildung 7.6(b) stellt dies am ent-
sprechenden Kreuzproduktautomaten dar und Abbildung 7.6(c) zeigt die entsprechenden Bit-
Operationen des Shift-Or-Algorithmus.
Aufgabe 7.16
Konstruieren sie sich den (Teil-)Kreuzproduktautomat, der f¨ur den in Abbildung 7.7
gezeigten Lauf des NEA relevant ist.
7.6.1 Implementierung
Listing 7.11 zeigt eine Implementierung des Shift-Or-Algorithmus. Zwischen Zeile 3 und
Zeile 6 werden die charakteristischen Vektoren in Form einesdict-Objektes b berechnet.
In Zeile 4 werden zun¨achst alle Eintr¨age von b mit 0 initialisiert. Dann wird das Muster
M einmal durchlaufen und f ¨ur jedes Zeichen c des Musters wird im charakteristischen
Vektor b [c ] das Bit an der entsprechenden Position gesetzt – dies geschieht in Zeile 6.
Ab Zeile 8 erfolgt die Simulation des NEA: Zun¨achst wird der Anfangszustand Z auf ”0“
gesetzt; der Endzustand des simulierten NEA wird in der Variablen endZst gespeichert.
Die for-Schleife ab Zeile 9 durchl ¨auft nun den zu durchsuchenden Text T zeichenweise
und f ¨uhrt bei jedem Durchlauf die im letzten Abschnitt beschriebenen Operationen
durch. In Zeile 12 wird durch bitweise UND-Verkn ¨upfung mit endZst gepr¨uft, ob der
Endzustand erreichbar ist. Ist dies der Fall, so wird der entsprechende Index – hier
i -len(M) +1 – der Ergebnisliste matches angef¨ugt.
Der Algorithmus hat oﬀensichtlich eine Laufzeit von O(n).

## Seite 250

7.6 Der Shift-Or-Algorithmus 235
0 0 0 0 0 0
a
−→
< <1 |1 0 0 0 0 0 1
b[a] 0 1 0 1 0 1
0 0 0 0 0 1
n
−→
< <1 |1 0 0 0 0 1 1
b[n] 0 0 1 0 1 0
0 0 0 0 1 0
a
−→
< <1 |1 0 0 0 1 0 1
b[a] 0 1 0 1 0 1
0 0 0 1 0 1
n
−→
< <1 |1 0 0 1 0 1 1
b[n] 0 0 1 0 1 0
0 0 1 0 1 0
a
−→
< <1 |1 0 1 0 1 0 1
b[a] 0 1 0 1 0 1
0 1 0 1 0 1
n
−→
< <1 |1 1 0 1 0 1 1
b[n] 0 0 1 0 1 0
0 0 1 0 1 0
a
−→
< <1 |1 0 1 0 1 0 1
b[a] 0 1 0 1 0 1
0 1 0 1 0 1
s
−→
< <1 |1 1 0 1 0 1 1
b[s] 1 0 0 0 0 0
1 0 0 0 0 0
Abb. 7.7: Erkennen des Musters ”ananas“ im Text ”anananas“ durch Ausf ¨uhrung der Bit-
operationen des Shift-Or-Algorithmus. Das Muster ist immer dann erkannt, wenn – in diesem
Fall – das sechste Bit von rechts gesetzt wurde, wenn also der Zustand ”6“ des entsprechenden
NEA erreichbar ist.
1 def shiftOr(M,T):
2 # Berechnung der charakteristischen Vektoren
3 b={}
4 for i in range(256): b [chr(i) ]=0
5 for i ,c in enumerate(M):
6 b [c ] = b[c] | 1<<i
7 # Simulation des NEA
8 Z=0 ; endZst = 1<<(len(M)-1) ; matches = []
9 for i ,c in enumerate(T):
10 Z = Z<<1 |1
11 Z = Z & b [c ]
12 if Z &endZst: matches.append(i -len(M) +1)
13 return matches
Listing 7.11: Implementierung des Shift-Or-Algorithmus
Aufgabe 7.17
F¨uhren Sie einen direkten Performance-Vergleich der bisher vorgestellten String-
Algorithmen durch.
 Der Vergleich sollte mit einem relativ kurzen Muster (10 Zeichen) und einem
relativ langen Muster (50 Zeichen) auf einer relativ kleinen Datenmenge (1000
Zeichen) und einer relativ großen Datenmenge (ca. 1 Million Zeichen) durch-
gef¨uhrt werden.
 Der Vergleich sollte mit dem naiven String-Matching-Algorithmus, dem Knuth-
Morris-Pratt-Algorithmus, dem Boyer-Moore-Algorithmus, dem Rabin-Karp-
Algorithmus und dem Shift-Or-Algorithmus durchgef ¨uhrt werden.

## Seite 252

8 Schwere Probleme und
Heuristiken
8.1 Das Travelling-Salesman-Problem
Berlin
Hamburg
Bremen
Hannover
Bielefeld
DortmundBochumEssenDuisburg
DüsseldorfWuppertal
Köln
Bonn
Frankfurt am Main
Mannheim
Stuttgart
München
Nürnberg
Leipzig
Dresden
Berlin
Abb. 8.1: Eine L¨osung des Travelling-Salesman-
Problems f¨ur die 20 gr ¨oßten St¨adte Deutschlands.
Die L ¨ange dieser Tour betr ¨agt 2430 km. Diese
L¨osung wurde mit dem in Listing 8.2 gezeigten Co-
de berechnet.
Ein f ¨ur viele logistische Anwendun-
gen relevantes Problem ist das Pro-
blem des Handlungsreisenden, auch
in der deutschsprachigen Literatur oft
als das Travelling-Salesman-Problem
(kurz: TSP) bezeichnet. Gegeben ist ei-
ne Menge von St¨adten und Abst¨anden
zwischen den St ¨adten, modelliert in
der Regel als kantengewichteter Graph.
Gesucht ist die k¨urzeste Rundtour, die
jede Stadt genau einmal besucht. Ab-
bildung 8.1 zeigt eine k ¨urzeste Tour
durch die 20 gr¨oßten deutschen St¨adte.
Das TSP ist ein NP-vollst¨andiges Pro-
blem. Man kann also davon ausgehen,
dass es keinen eﬃzienten Algorithmus
zur L¨osung des TSP gibt, d. h. keinen
Algorithmus mit polynomieller Lauf-
zeit. Schon f ¨ur eine Problemgr ¨oße von
n= 50 St¨adten w¨are der f¨ur die in Ab-
bildung 8.1 gezeigte L¨osung verwende-
te Algorithmus nicht mehr geeignet ei-
ne L¨osung innerhalb einer vern¨unftigen
Zeitspanne (etwa zu Lebzeiten der Le-
ser) zu berechnen – siehe hierzu auch
Aufgabe 8.4.
8.1.1 L ¨osung durch Ausprobieren
Die einfachste, aber auch denkbar langsamste M ¨oglichkeit, das TSP zu l ¨osen, besteht
darin, alle m ¨oglichen Touren, d. h. alle Permutationen der Knotenmenge V, durchzu-
probieren und die minimale Tour zur ¨uckzuliefern. Eine solche auch oft als Brute-Force
bezeichnete L¨osung zeigt Listing 8.1.

## Seite 253

238 8 Schwere Probleme und Heuristiken
1 def TSPBruteForce(graph):
2 nodeList = graph.V()[1:]
3 return min([graph.pathVal(perm+ [perm[0]]) for perm in perms(nodeList)])
Listing 8.1: Implementierung des brute-force-Algorithmus, der alle m ¨oglichen Touren durch-
probiert.
Die Funktion perms(xs), wie in Listing B.1 auf Seite 318 gezeigt, liefert eine Liste al-
ler Permutationen der Liste xs zur¨uck. Die Methode pathVal der Klasse Graph (siehe
Aufgabe 5.2 auf Seite 151) berechnet den Wert bzw. die L ¨ange eines als Knotenliste
¨ubergebenen Pfades. Der Ausdruck perm+perm[0] erzeugt aus der Knotenpermutation
perm eine Rundtour.
8.1.2 L ¨osung durch Dynamische Programmierung
F¨ur das Travelling-Salesman-Problem gilt das sog. (Bellmannsche) Optimalit ¨atsprin-
zip: Eine optimale L ¨osung setzt sich aus ”kleineren“ optimalen L ¨osungen zusammen.
Probleme, f¨ur die dieses Optimalit ¨atsprinzip gilt, k¨onnen durch Dynamische Program-
mierung gel¨ost werden. In gewissem Sinne muss man ein Problem, das¨uber Dynamische
Programmierung gel¨ost werden soll, genau invers durchdenken als wenn es ¨uber Rekur-
sion gel¨ost werden soll: W ¨ahrend man bei einer rekursiven Implementierung L ¨osungen
gedanklich top-down konstruiert, geht man bei einer L ¨osung ¨uber Dynamische Pro-
grammierung bottom-up vor. Man berechnet zun¨achst die L¨osungen der ”kleinen“ Teil-
probleme und speichert diese Zwischenergebnisse in einer Tabelle. Bei der Berechnung
der gr¨oßeren Teilprobleme (insbesondere des Gesamtproblems) greift man auf die in der
Tabelle gespeicherten Werte zur¨uck.
Im Falle des Travelling-Salesman-Problems gilt, dass sich die k ¨urzeste Rundtour ¨uber
die Knoten aus der Menge S zusammensetzt aus einem Startknoten j und einer um eins
kleineren k ¨urzesten Rundtour ¨uber alle Knoten aus S, ausgenommen dem Knoten j.
Nennen wir T(i,S) den Wert der k¨urzesten Tour, startend bei Knoten i, die alle Knoten
aus S genau einmal besucht und schließlich bei Knoten 1 endet; dann gilt also, dass
T(i,S) = min
j∈S
(
w(i,j) + T(j,S \{j})
)
(8.1)
Modellieren wir die ”Tabelle“ T als Python-Dictionary und nehmen an, dass der Graph
als Python-Objekt graph gegeben sei, so l¨asst sich dies analog in Python folgendermaßen
formulieren:
T[(i,S)] = min( graph.w(i,j) +T[(j, diﬀ (S, [j ])) ] for j in S) (8.2)
Der Wert T(1,{2,...n }) ist der gesuchte Wert der k ¨urzesten Rundtour.
Formel (8.2) ließe sich zwar direkt in einer rekursiven Implementierung umsetzen, diese
ist aber in diesem Fall ineﬃzient, da eine sehr große Zahl rekursiver Aufrufe entstehen
w¨urde1. Hier ist also eine Implementierung ¨uber Dynamische Programmierung sinnvoll.
1Genauer: es w¨aren |S|−1 rekursive Aufrufe notwendig, um die Instanz T(i,S) zu berechnen. Schon
der Vergleich mit der rekursiven Implementierung von Quicksort, die bei jeder Instanz h ¨ochstens 2
rekursive Aufrufe ben¨otigt, zeigt, dass die |S|−1 Aufrufe sehr ”viel“ ist.

## Seite 254

8.1 Das Travelling-Salesman-Problem 239
Aufgabe 8.1
Geben Sie eine direkt rekursive Implementierung einer L¨osung des Travelling-Salesman-
Problems in Python an, basierend auf Formel (8.2).
Listing 8.2 zeigt die Verwendung Dynamischer Programmierung bei der L ¨osung des
Travelling-Salesman-Problems.
1 def tsp(graph):
2 n = graph.numNodes
3 T = {}
4 for i in range(1,n +1): T[(i,()) ] = graph.w(i,1)
5 for k in range(1,n -1):
6 for S in choice(range(2,n +1),k):
7 S = tuple(S) # Listen nicht hashbar ⇒umwandeln in Tupel
8 for i in diﬀ (range(2,n +1),S): # for i∈S
9 T[(i,S)]= min( graph.w(i,j) +T[(j,diﬀ(S, [j ])) ] for j in S )
10 S = tuple(range(2,n +1))
11 return min( graph.w(1,j)+T[(j,diﬀ(S,[ j ])) ] for j in range(2,n +1) )
Listing 8.2: Implementierung eines Algorithmus, basierend auf Dynamischer Programmie-
rung, zur L ¨osung des Travelling-Salesman-Problems
Diese Implementierung verwendet ein Dictionary T, um die schon berechneten k¨urzeren
optimalen Touren zu speichern. Die Schl ¨ussel sind hierbei Tupel ( i ,S) bestehend aus
einem Startknoten i und einer Knotenmenge S, die als Tupel repr¨asentiert ist (in Python
ist es nicht m¨oglich, Listen als Schl¨usselwerte zu verwenden); T[(i,S)] sollte also immer
die k¨urzeste Rundtour durch Knoten aus S, beginnend bei i, und endend bei Knoten
1 enthalten. In Zeile 4 werden zun ¨achst die ”einfachsten“ Eintr¨age in T erzeugt, die
n¨amlich, f¨ur die S = ∅gilt.
Das in Zeile 6 verwendete choice(range(2,n +1),k) liefert die Liste aller k-elementigen
Teilmengen (jeweils repr ¨asentiert als Python-Listen) der Menge {2,...,n }(ebenfalls
repr¨asentiert als Python-Liste) zur ¨uck. Eine Implementierung von choice – eingebettet
in eine kurze Einf ¨uhrung in Binomialkoeﬃzienten und kombinatorische Grundlagen –
ﬁndet sich in Listing B.2.
Zun¨achst berechnet der Algorithmus die Eintr¨age T(i,S) f¨ur alle ”kleinen“ Teilmengen
von {2,...,n }– also zun¨achst f¨ur alle 1-elementigen Teilmengen (Schleifendurchlauf f¨ur
k = 1 der in Zeile 5 beginnenden for-Schleife), dann f ¨ur alle 2-elementigen (Schleifen-
durchlauf f¨ur k = 2), usw. Die eigentliche Berechnung von T(i,S) erfolgt nach Formel
(8.2) – Zeile 9 in Listing 8.2 entspricht genau Formel (8.2). Wurden, nach Beendi-
gung der in Zeile 5 beginnenden for-Schleife, die Werte T(i,S) aller Touren f ¨ur alle
S ⊆{2,...,n }(und alle i ∈
S) berechnet, so kann schließlich der Wert der minima-
len Rundtour T(1,{2,...,n }) in Zeile 11 berechnet werden – dies geschieht wiederum
gem¨aß Formel (8.2).

## Seite 255

240 8 Schwere Probleme und Heuristiken
Aufgabe 8.2
Modiﬁzieren Sie den in Listing 8.2 gezeigten Algorithmus so, dass er – zus ¨atzlich zur
L¨ange der k¨urzesten Route – die k ¨urzeste Route selbst als Liste von zu besuchenden
Knoten zur¨uckliefert.
8.1.3 Laufzeit
Es gibt 2 n−1 Teilmengen der Menge {2,...,n }. F¨ur jede dieser Teilmengen S und f¨ur
jedes i ∈S muss eine Minimums-Bestimmung durchgef ¨uhrt werden, die |S|Schritte
ben¨otigt. Die Teilmengen S und ebenso deren inverse Mengen S haben im Mittel eine
Gr¨oße von n/2 – entsprechend dem Median der Binomialverteilung. F¨ur jede Teilmenge
m¨ussen also im Mittel n/2 (durchschnittlicher Wert von |S|) Minimumsbestimmungen
durchgef¨uhrt werden. Jede Minimumsbestimmung ihrerseits ben ¨otigt im Mittel n/2
(durchschnittlicher Wert von|S|) Schritte um die|S|Schritte miteinander zu vergleichen.
Ingesamt ben¨otigt die auf Dynamischer Programmierung beruhende Implementierung
tsp also
(n/2)2 ·2n−1 = O(n22n)
Schritte.
Aufgabe 8.3
Vergleichen Sie die Implementierung in Listing 8.1, die eine L¨osung des TSP-Problems
durch Ausprobieren aller M¨oglichkeiten berechnet, mit der Implementierung aus Li-
sting 8.2, die Dynamische Programmierung verwendet.
(a) Zur Berechnung der in Abbildung 8.1 gezeigten L ¨osung, die k ¨urzeste Rundtour
durch die 20 gr ¨oßten St ¨adte Deutschlands zu ﬁnden, hat der tsp-Algorithmus
aus Listing 8.2 auf dem Rechner des Autors etwa 4 Minuten ben ¨otigt. Sch¨atzen
Sie ab, wie lange der Algorithmus aus Listing 8.1 zur Berechnung dieser L ¨osung
ben¨otigen w¨urde.
(b) Wie viel mal mehr Schritte ben ¨otigt der Algorithmus aus Listing 8.1 wie der
auf Dynamsicher Programmierung basierende Algorithmus um eine Rundreise
durch n St¨adte zu berechnen?
Aufgabe 8.4
Sch¨atzen Sie ab, wie lange der in Listing 8.2 gezeigte, auf Dynamische Programmie-
rung beruhende Algorithmus ben ¨otigen w¨urde, um die k ¨urzeste Rundtour ¨uber 30,
40, 50 und 60 St ¨adte zu berechnen.
Gehen Sie wiederum davon aus, dass der in Listing 8.2 gezeigte Algorithmus zur
Berechnung einer k¨urzesten Tour durch 20 St¨adte etwa 4 Minuten ben ¨otigt.

## Seite 256

8.2 Heuristiken f ¨ur das Travelling-Salesman-Problem 241
8.2 Heuristiken f ¨ur das
Travelling-Salesman-Problem
Als ”Heuristik“ bezeichnet man eine Strategie, um eine ”gute“ – jedoch i. A. keine
optimale – L¨osung eines i. A. schweren Problems in relativ kurzer Zeit zu ﬁnden. Hier-
bei werden spezielle Eigenschaften der Problemstellung ausgenutzt. Aufgrund der NP-
Vollst¨andigkeit des Travelling-Salesman-Problems hat man zur Berechnung von Rund-
touren ¨uber mehr als 30 St¨adte eigentlich keine andere Wahl als Heuristiken zu verwen-
den und sich mit einer evtl. nicht-optimalen L¨osung zufrieden zu geben – siehe Aufgabe
8.4.
Wir pr¨asentieren im Folgenden mehrere Heuristiken zur L¨osung des Travelling-Salesman-
Problems, die in allgemeinerer Form auch zur L ¨osung anderer schwerer Probleme ver-
wendet werden k¨onnen.
8.3 Greedy-Heuristiken
Mit dem Dijkstra-Algorithmus (siehe Listing 5.5 auf Seite 163) und dem Kruskal-Al-
gorithmus (siehe 5.7 auf Seite 172) haben wir schon zwei sog. Greedy-Algorithmen
kennengelernt, die in jedem Schritt einfach die momentan am besten erscheinende Er-
weiterung zur L¨osung w¨ahlen. Im Falle des Dijkstra- und Kruskal-Algorithmus gelangt
man ¨uber diese Greedy-Strategie tats ¨achlich zur optimalen L¨osung.
Dies funktioniert f ¨ur das Travelling-Salesman-Problem nicht: Eine Greedy-Strategie
f¨uhrt hier i. A.nicht zu einer optimalen L¨osung – jedoch in vielen F¨allen zu einer L¨osung
die f ¨ur viele Anwendungen gen ¨ugend nahe am Optimum liegt. F ¨ur das Travelling-
Salesman-Problem sind mehrere Greedy-Heuristiken denkbar.
8.3.1 Nearest-Neighbor-Heuristik
Die vielleicht einfachste M ¨oglichkeit besteht darin, von der Stadt aus, in der man sich
aktuell beﬁndet, immer die dazu n ¨achstliegende noch nicht besuchte Stadt zu w ¨ahlen.
Diese Heuristik liefert jedoch nur m¨aßig gute Werte: Verh¨altnism¨aßig gute Verbindungen
werden relativ fr¨uh (aufgrund noch besserer Verbindungen) ausgeblendet; Folge ist, dass
gegen Ende einer Nearest-Neighbor-Tour oft sehr lange Wegstrecken in Kauf genommen
werden m¨ussen. Im Falle eines nicht vollst ¨andigen Graphen (d. h. eines Graphen, bei
dem nicht alle St ¨adte miteinander verbunden sind) kann diese Heuristik gar in eine
Sackgasse f¨uhren.
Die Laufzeit der Nearest-Neighbor-Heuristik betr¨agt O(n2) (nMinimumsﬁndungen aus
durchschnittlich n/2 Elementen).

## Seite 257

242 8 Schwere Probleme und Heuristiken
Aufgabe 8.5
Implementieren Sie die Nearest-Neighbor-Heuristik f¨ur das Travelling-Salesman-Pro-
blem und testen Sie diese durch Berechnung der k ¨urzesten Tour durch die . . .
(a) . . . gr¨oßten 20 deutschen St¨adte.
(b) . . . gr¨oßten 40 deutschen St¨adte.
Hinweis: Die einfachste M¨oglichkeit, sich einen Graphen zu erzeugen, der die 20 bzw.
40 gr¨oßten deutschen St¨adte enth¨alt, besteht in der Verwendung des Python-Moduls
pygeodb. Mittels pygeodb.distance erh¨alt man etwa den Abstandswert zweier St¨adte.
8.3.2 Nearest-, Farthest-, Random-Insertion
Eine in vielen F¨allen etwas bessere Strategie liefert die folgende Greedy-Heuristik: Man
beginnt mit einer sehr kurzen (z. B. zwei St ¨adte umfassenden) Tour und man f ¨ugt suk-
zessive weitere Knoten zu der bestehenden Tour m¨oglichst gut ein. Es gibt nun mehrere
M¨oglichkeiten, nach welchen Kriterien der n ¨achste einzuf ¨ugende Knoten ausgew ¨ahlt
werden kann:
 ”Nearest Insertion“: Als n ¨achtes wird derjenige Knoten zur bestehenden Tour
hinzugef¨ugt, der zur momentanen Tour den geringsten Abstand hat.
 ”Farthest Insertion”: Als n ¨achtes wird derjenige Knoten zur bestehenden Tour
hinzugef¨ugt, der zur momentanen Tour den gr ¨oßten Abstand hat.
 ”Random Insertion”: Als n ¨achtes wird zuf¨allig ein noch nicht in der Tour beﬁnd-
licher Knoten zur Tour hinzugf¨ugt.
Die Abbildungen 8.2 und 8.3 zeigen jeweils Momentaufnahmen bei dem Aufbau einer
Tour nach der Nearest- bzw. Farthest-Insertion-Heuristik.
1
2
6
3
4
5
Abb. 8.2: Momentaufnahme beim Aufbau
einer Tour mittels der Nearest-Insertion-
Heuristik.
1
5
2
6
3
4
Abb. 8.3: Momentaufnahme beim Aufbau
einer Tour mittels der Farthest-Insertion-
Heuristik.
Tats¨achlich liefert schon die Random-Insertion-Heuristik sehr gute Ergebnisse – ins-
besondere bessere als die Nearest-Insertion-Heuristik. Das folgende Listing zeigt eine
Implementierung der Random-Insertion-Heuristik:

## Seite 258

8.3 Greedy-Heuristiken 243
1 from random import choice
2 def tspRandomInsertion(graph):
3 n = graph.numNodes
4 (w,a,b) = min([(graph.w(i,j ), i , j)
5 for i in range(1,n +1) for j in range(1,n +1) if i̸=j])
6 tour = [a,b ]
7 while len(tour)<n:
8 v = choice([i for i in range(1,n +1) if i not in tour])
9 pos = min([ (graph.w(tour [i],v) +graph.w(v,tour[i +1]) -graph.w(tour[i],tour[i +1]), i)
10 for i in range(0,len(tour) -1) ]) [1]
11 tour. insert (pos+1,v)
12 tour = tour + [tour [0] ] # Rundtour daraus machen
13 return pathVal(graph,tour), tour
Listing 8.3: Implementierung der Random-Insertion-Heuristik
Die Listenkomprehension in den Zeilen 4 und 5 bestimmt die beiden Knoten mit der
k¨urzesten Verbindung im Graphen. Wir beginnen mit einer aus diesen beiden Knoten
bestehenden Tour [ a,b ]. In der in Zeile 7 beginnenden while-Schleife werden nun suk-
zessive Knoten zur Tour hinzugef¨ugt, bis schließlich eine komplette Rundtour entsteht.
Die Listenkomprehension in Zeile 8 erzeugt alle Knoten, die sich noch nicht in der bis-
herigen Tour beﬁnden und daraus wird mittels der Funktion choice zuf¨allig ein Knoten
ausgew¨ahlt. In den Zeilen 9 und 10 wird die optimale Einf¨ugeposition in die bestehende
Tour bestimmt. Man f ¨ugt einfach an derjenigen Position ein, die die bestehende Tour
am geringsten vergr ¨oßert; man w ¨ahlt also diejenige Position i der Tour tour, die den
Ausdruck
w(touri,v) + w(v,touri+1) −w(touri,touri+1)
minimiert. Die Listenkomprehension in den Zeilen 9 und 10 generiert hierzu eine Liste
von Tupeln, deren erste Komponente jeweils die zu minimierende Tourvergr¨oßerung ist
– die Miniumsbildung l¨auft auch ¨uber diese erste Komponente – und deren zweite Kom-
ponente jeweils die Einf ¨ugeposition ist. ¨Uber die Indizierung min(... ) [1] erhalten wir
schließlich die zweite Komponente des optimalen Tupels – die optimale Einf¨ugeposition
also.
Die Laufzeit des in Listing 8.3 gezeigten Algorithmus ist O(n2): Es gibt n−2 while-
Schleifendurchl¨aufe und in jedem Schleifendurchlauf muss die (vorl¨auﬁge) Tour zur Be-
stimmung der optimalen Einf¨ugeposition durchlaufen werden; deren L¨ange der vorl¨auﬁ-
gen Tour ist im i-ten Schleifendurchlauf genau i. Insgesamt sind dies also
n−2∑
i=0
i= (n−1) ·(n−2)
2 = O(n2)
Schritte.

## Seite 259

244 8 Schwere Probleme und Heuristiken
Aufgabe 8.6
Implementieren Sie die Nearest-Insertion-Heuristik zum Finden einer m ¨oglichst op-
timalen L¨osung des Travelling-Salesman-Problems.
Aufgabe 8.7
Implementieren Sie die Farthest-Insertion-Heuristik zum Finden einer m ¨oglichst op-
timalen L¨osung des Travelling-Salesman-Problems.
Aufgabe 8.8
Vergleichen Sie die G ¨ute der gefundenen L ¨osungen durch die in Listing 8.3 gezeigte
Implementierung der Random-Insertion mit den durch . . .
 . . . Nearest-Insertion
 . . . Farthest-Insertion
. . . gefundenen L¨osungen.
Bei der L¨osung der vorangegangenen drei Aufgaben konnte man sehen, dass die Nearest-
Insertion-Heuristik deutlich schlechtere Ergebnisse liefert als die Farthest-Insertion-
Heuristik. Der Grund daf ¨ur ist, dass bei der Nearest-Insertion-Heuristik gegen Ende
des Algorithmus, wenn nur noch wenige weit entfernte Knoten ¨ubrig bleiben, sehr lange
Wege entstehen k¨onnen.
8.3.3 Tourverschmelzung
Eine sich in der Praxis gut bew ¨ahrende Heuristik ist die der Tourverschmelzung: Man
w¨ahlt zun¨achst einen beliebigen Startknoten v und generiert n−1 Stichtouren zu den
verbleibenden n−1 Knoten. In jedem Schritt werden zwei der vorhandenen Stichtouren
verschmolzen (siehe Abbildung 8.4), und zwar immer so, dass die sich daraus ergebende
Kostenersparnis maximal ist. Aus einem Graphen G= (V,E) werden also zwei Touren
touri (mit Knoten x∈touri, {v,x}∈ E) und tourj (mit u∈tourj und {v,u}∈ E) so
gew¨ahlt, dass der Ausdruck
w(v,u) + w(v,x) −w(u,x) (8.3)
maximiert wird.
Folgendes Listing 8.4 implementiert die Tourenverschmelzung: In Zeile 7 wird zun¨achst
mittels choice ein Knoten v zuf¨allig aus der Knotenmenge ausgew ¨ahlt. In Zeile 8 wird
der Anfangszustand hergestellt, bestehend aus einer Liste von n−1 einelementigen
Touren. In jedem Durchlauf der while-Schleife ab Zeile 9 werden zwei Touren t1 und t2
verschmolzen, indem eine Verbindung zwischen Knoten u und Knoten x eingef¨ugt wird,

## Seite 260

8.3 Greedy-Heuristiken 245
x y
u
vw
t2
t1
Abb. 8.4:Sukzessive Verschmelzung von Touren. Die zwei zu verschmelzenden Touren t1 und
t2 werden so gew ¨ahlt, dass die aus der Verschmelzung entstehende Kostenersparnis maximal
ist.
1 from random import choice
2 def tspMelt(graph):
3 def melt(t1,t2 ):
4 return [(graph.w(v,u) +graph.w(v,x) -graph.w(u,x), u==t1[0], t1, x==t2[0], t2)
5 for u in [t1 [0], t1 [ -1]] for x in [t2 [0], t2 [ -1]]]
6 n = graph.numNodes
7 v = choice(graph.V())
8 tours = [[ i ] for i in range(1,n +1) if i̸=v]
9 while len(tours)>1:
10 ( fst u ,t1, fst x ,t2) = max([m for t1 in tours for t2 in tours if t1̸=t2
11 for m in melt(t1,t2) ]) [-4:]
12 t1 [: ] = ( t1[ :: -1] if fst u else t1) +\
13 (t2 if fst x else t2 [ :: -1])
14 tours.remove(t2)
15 return [v] +tours[0] + [v ]
Listing 8.4: Implementierung der Tourverschmelzung.
und daf ¨ur die beiden Kanten {v,u}und {v,x}gel¨oscht werden. ¨Uber die Listenkom-
prehension in den Zeilen 10 und 11 werden die beiden Touren so ausgesucht, dass die
Einsparung gem¨aß Gleichung (8.3) maximiert wird. Die Listenkomprehension erstellt
eine Liste aller Verschmelzungen von Touren t1,t2 ∈tours. Was eine ”Verschmelzung“
ist, wird durch die ab Zeile 3 deﬁnierte lokale Funktion melt bestimmt: N ¨amlich die
Liste aller m¨oglichen Verbindungen (davon gibt es 4: Der erste/der letze Knoten von t1
kombiniert mit dem ersten/letzten Knoten von t2) der beiden Touren. Jede der 4 Kom-
binationen ist ein 5-Tupel: Die erste Komponente ist die Einsparung, die sich aus der
Kombination ergibt. Da die sp ¨atere Maximumsbildung sich an der Einsparung orien-
tiert, ist es wichtig, dass dieser Wert an der ersten Stelle steht. Die zweite Komponente
gibt an, ob u der erste Knoten aus t1 ist, die dritte Komponente ist die Tour t1 selbst,
die vierte Komponente gibt an, ob x der erste Knoten aus t2 ist und die letzte Kom-
ponente ist die Tour t2. Die Maximumsbildung in Zeile 10 liefert das 5-Tupel mit der
maximalen Einsparung und die Indizierung [ -4 :] selektiert die letzten 4 Komponenten
dieses 5-Tupels.

## Seite 261

246 8 Schwere Probleme und Heuristiken
In den Zeilen 12 und 13 wird schließlich die Tour t1 um die Tour t2 erweitert. Wie dies
zu geschehen hat, h ¨angt davon ab, ob sich u, bzw. x, am Anfang oder am Ende der je-
weiligen Tour beﬁnden. Schließlich wird in Zeile 14 die Tourt2 aus tours gel¨oscht. Bleibt
schließlich nur noch eine Tour in tours ¨ubrig, so wird diese eine Tour zusammen mit
dem Knoten v als Start- und Endknoten als R ¨uckgabewert von tspMelt zur¨uckgeliefert.
Die Laufzeit dieser Implementierung ist O(n3): Es gibt n−2 while-Schleifendurchl¨aufe.
In jedem Durchlauf werden alle Kombinationen zweier Touren – das sind jeweils
len(tours)2 −len(tours) viele – in Betracht gezogen und die g ¨unstigste dieser Kombi-
nationen ausgew¨ahlt. Die Laufzeit von melt ist eine Konstante, also in O(1). Insgesamt
ergibt sich damit als Laufzeit
1∑
i=n−2
i2 −i= O(n3)
.
Aufgabe 8.9
Was die Laufzeit betriﬀt, kann die in Listing 8.4 gezeigte Implementierung der Tour-
verschmelzung verbessert werden. Anstatt die optimalen Verschmelzungs-Knoten je-
desmal neu zu berechnen – wie in den Zeilen 9 und 10 in Listing 8.4 – kann man sich
jeweils die optimalen Nachbarn der Anfangs- und Endknoten einer Teiltour merken
und – nach einer Verschmelzung – gegebenenfalls anpassen.
Entwerfen Sie eine entsprechend optimierte Version der in Listing 8.4 gezeigten Im-
plementierung und analysieren Sie, welche Laufzeit der Algoritmus nach diese Opti-
mierung hat.
8.4 Lokale Verbesserung
Die Heuristik ”lokale Verbesserung“ nimmt eine durch eine andere Heuristik vorge-
schlagene L¨osung als Ausgangspunkt und nimmt auf dieser (mehr oder weniger geziel-
te) Ver¨anderungen vor; in diesem Zusammenhang werden diese Ver ¨anderungen meist
als Mutationen bezeichnet. Eine die aktuelle Tour verbessernde Mutation – falls es
¨uberhaupt eine solche geben sollte – wird als Ausgangspunkt f ¨ur die n ¨achste Iteration
genommen, usw. Dies wird solange fortgesetzt, bis keine verbessernde Mutation mehr
gefunden werden kann. Man beachte, dass im Allgemeinen durch eine lokale Verbes-
serungsstrategie nicht das globale Optimum, sondern lediglich ein lokales Optimum
erreicht wird.
F¨ur die L¨osung des Travelling-Salesman-Problems hat sich in der Praxis das sog. 2-Opt-
Verfahren bzw. das allgemeinere k-Opt-Verfahren als praktikabel erwiesen.

## Seite 262

8.4 Lokale Verbesserung 247
8.4.1 Die 2-Opt-Heuristik
Die 2-Opt-Heuristik l ¨oscht in einer vorhandenen Tour zwei Kanten und verbindet die
dabei frei gewordenen vier Knoten ¨uber Kreuz; Abbildung 8.5 zeigt dies graphisch.
=⇒vi
vk
vk+1
vi+1
v0
vk+1
vi
vk
vi+1
v0
Abb. 8.5: Eine durch die 2-Opt-Heuristik durchgef ¨uhrte Mutation einer Tour
(v0,v1,...,v n,v0). Zwei Tourkanten (vi,vi+1) und (vk,vk+1) werden gel ¨oscht und statt-
dessen die Kanten (vi,vk) und (vi+1,vk+1) in die Tour eingef¨ugt; sollte dies eine Verbesserung
(bzw. die gr ¨oßte Verbesserung) gegen¨uber der urspr ¨unglichen Variante ergeben, so wird diese
Mutation als Ausgangspunkt f ¨ur weitere Mutationen verwendet.
Listing 8.5 zeigt eine Python-Implementierung der 2-Opt-Strategie. Man beachte, dass
die Funktion tsp2Opt neben dem zugrundeliegenden Graphen einen Algorithmus
heuristik ¨ubergeben bekommt. Die durch diesen Algorithmus berechnete Tour dient
(siehe Zeile 3 in Listing 8.5) als Ausgangspunkt f ¨ur die Durchf ¨uhrung der 2-Opt-
Heuristik.
1 def tsp2Opt(graph,heuristik ):
2 n = graph.numNodes
3 tour = heuristik(graph)
4 while True:
5 (opt, i ,k) = max([(graph.w(tour [i],tour[i +1]) +graph.w(tour[k],tour[k +1]) -
6 graph.w(tour[i ], tour [k ]) -graph.w(tour[i +1],tour [k +1]), i,k)
7 for i in range(n) for k in range(i +2,n) ])
8 if opt≤0: return tour
9 else: tour = tour[:i +1] +tour[k:i : -1] +tour[k +1:]
Listing 8.5: Implementierung der 2-Opt-Strategie.
Die Listenkomprehension in den Zeilen 5 bis 7 ermittelt die Mutation der Tour, die sich
am ehesten lohnt. Es werden also die beiden Tourkanten ( vi,vi+1) und (vk,vk+1) mit
i,k ∈range(0,n) und i≤k−2 ausgew¨ahlt, f¨ur die die Kostenersparnis
w(vi,vi+1) + w(vk,vk+1) −w(vi,vk) −w(vi+1,vk+1)
maximal ist. Sollte durch Mutation keine Kostenersparnis mehr m ¨oglich sein, d. h. soll-
te die maximal m ¨ogliche Kostenersparnis opt kleiner Null sein (dies wird in Zeile 8

## Seite 263

248 8 Schwere Probleme und Heuristiken
gepr¨uft), so wird die 2-Opt-Strategie abgebrochen und die aktuelle Tour zur ¨uckgelie-
fert. Andernfalls wird in Zeile 9 die Mutation durchgef ¨uhrt. Hierbei muss – das ist in
Abbildung 8.5 sch ¨on zu sehen – die bisherige Tour bis zu Knoten i ¨ubernommen wer-
den (was genau dem Ausdruck tour [ :i +1] entspricht), daran Knoten kbis Knoten i−1
in umgekehrter Reihenfolge angef ¨ugt werden (was genau dem Ausdruck tour [k :i : -1]
entspricht) und schließlich alle Knoten ab k ans Ende geh¨angt werden (was genau dem
Ausdruck tour [k +1 :] entspricht).
8.4.2 Die 2.5-Opt-Heuristik
Die 2.5-Opt-Heuristik l¨oscht drei Tourkanten, von denen zwei benachbart sind. Dadurch
entsteht, wie in Abbildung 8.6 veranschaulicht, (jeweils) eine m ¨ogliche Neuverbindung
einer so zerfallenen Tour. Die 2.5-Opt-Heuristik pr ¨uft, ob es eine Neuverbindung dieser
Art gibt, mit der eine bestehende Tour verk ¨urzt werden kann.
v0
vi12
vi11
vi10
vi01
vi00
=⇒
vi00
vi01
vi12
vi10
vi11
v0
v0
vi00
vi01
vi02
vi11
vi10
=⇒
vi00
v0
vi11
vi10
vi02
vi01
entweder: ... oder:
Abb. 8.6: Die 2.5-Opt-Heuristik erlaubt jeweils genau eine Mutation einer Tour
(v0,v1,...,v n,v0), die durch Entfernung von 3 Kanten (davon zwei benachbarten) Kanten
entsteht.
Die in Listing 8.6 implementierte Funktion crossTour2 5 erzeugt die in Abbildung 8.6
gezeigte Neuverbindung einer Tour tour. Der Parameter i speziﬁziert die Kanten, die
in der Tour zu entfernen sind. Der in der linken H ¨alfte von Abbildung 8.6 gezeigten
Situation w ¨urde der Parameter i = (( i00,i01,i02),(i10,i11)) entsprechen, wobei i01 =
i00 + 1, i02 = i00 + 2 und i11 = i10 + 1. Der in der rechten H ¨alfte von Abbildung
8.6 gezeigten Situation w ¨urde der Parameter i = ((i00,i01),(i10,i11,i12)) entsprechen,
wobei i01 = i00 + 1, i11 = i10 + 1 und i12 = i10 + 2.
1 def crossTour2 5(tour,i ):
2 if len(i [0])==3:
3 return tour[:i [0] [0] +1] + tour [i [0] [2]: i [1] [0] +1] +\

## Seite 264

8.4 Lokale Verbesserung 249
4 [tour [i [0] [1] ] ] +tour [i [1] [1]: ]
5 else:
6 return tour[:i [0] [0] +1] + [tour [i [1] [1] ] ] +\
7 tour [i [0] [1]: i [1] [0] +1] + tour [i [1] [2]: ]
Listing 8.6:Erzeugung einer Neuverbindung einer durch L¨oschung von drei (wobei zwei davon
benachbart sind) Kanten zerfallenen Tour.
Mit Hilfe dieser Funktion erfolgt dann die Implementierung der 2.5-Opt-Heursitik so
wie in folgendem Listing 8.7 gezeigt:
1 def tsp2 5Opt(graph,tour):
2 crTrs = map(lambda i: crossTour2 5(tour,i) ,all2 5Cuts(len(tour)))
3 return min([(pathVal(graph,c),c) for c in crTrs])
Listing 8.7: Implementierung der 2.5-Opt-Heuristik.
Zeile 2 wendet die in Listing 8.6 gezeigte FunktioncrossTour2 5 auf jede m¨ogliche durch
Entfernung von drei Kanten (zwei davon benachbart) zerfallene Tour an. Die Funktion
all2 5Cuts(n) erzeugt die Speziﬁkationen aller m¨oglichen L¨oschungen dreier Kanten aus
einer Tour der L¨ange n. In Zeile 3 wird dann diejenige Neuverbindung mit minimalem
Gewicht zur¨uckgeliefert.
Aufgabe 8.10
Implementieren Sie die Funktion all2 5Cuts(n), die alle Speziﬁkationen aller m ¨ogli-
chen L¨oschungen dreier Kanten erzeugt. Beispiel-Anwendungen:
>>>all2 5Cuts(10)
>>> [ ((0,1),(3,4,5)), ((0,1),(4,5,6)), ... , ((5,6,7),(8,9)) ]
Aufgabe 8.11
(a) Verwenden Sie statt der map-Funktion in Zeile 2 in Listing 8.7 eine Listenkom-
prehension.
(b) Schreiben Sie die in Listing 8.7 gezeigte Funktion tsp2 5Opt so um, dass der
Funktionsk¨orper lediglich aus einem return-Statement besteht.
Aufgabe 8.12
Implementieren Sie die 2.5-Opt-Heuristik performanter: ¨Uberpr¨ufen Sie dazu nicht
jedesmal die L¨ange der gesamten Tour (die durch Neuverbindung entsteht), sondern
vergleichen Sie immer nur die L ¨angen der durch Neuverbindung neu hinzugekom-
menen Kanten mit den L ¨angen der gel ¨oschten Kanten – analog wie in Listing 8.5
realisiert.

## Seite 265

250 8 Schwere Probleme und Heuristiken
8.4.3 Die 3-Opt- und k-Opt-Heuristik
Die k-Opt-Heuristik entfernt k disjunkte Kanten (d. h Kanten ohne gemeinsame Kno-
ten) aus der Tour und versucht die frei gewordenen Knoten so zu verbinden, dass die ent-
stehende Kostenersparnis maximiert wird. Dabei muss man darauf achten, dass durch
ungeschicktes Wiederverbinden die urspr ¨ungliche Tour nicht in mehrere Einzeltouren
zerf¨allt. Abbildung 8.7 zeigt alle M¨oglichkeiten, eine durch L¨oschung von drei disjunkten
=⇒=⇒ =⇒=⇒
v0
vk+1
vk
vj+1vj
vi
vi+1
v0
vk+1
vk
vj+1vj
vi+1vk
vj+1vj
v0
vk+1 vi
v0
vj+1vj
vi+1
vi vk+1
vk
vk+1
vk
vj+1
vi+1
vi
vj
vi+1
vi
v0
Abb. 8.7: Es gibt vier M ¨oglichkeiten eine durch L ¨oschung von drei disjunkten Tourkanten
zerfallene Tour neu zu verbinden – bzw. sogar acht M ¨oglichkeiten, wenn man urspr ¨ungliche
Kanten als Neuverbindungen zul ¨asst, d h. Kanten der Form (vm,vm+1), m∈{i,j,k }zul¨asst.
Tourkanten zerfallene Tour neu zu verbinden; aus dieser Menge von Neuverbindungen
w¨urde man im Laufe einer 3-Opt-Heuristik versuchen, eine verbessernde Neuverbindung
auszuw¨ahlen.
Aufgabe 8.13
Implementieren Sie die 3-Opt-Heuristik in Python und vergleichen Sie die G ¨ute der
berechneten Touren mit denen der 2-Opt-Heuristik.
Wir wollen einen Algorithmus pr ¨asentieren, der alle m¨oglichen Neuverbindungen einer
durch L ¨oschung von k Kanten zerfallenen Tour erzeugt und k ¨ummern uns zun ¨achst
darum, wie eine ”aufgeschnittene“ Tour repr¨asentiert werden kann. Abbildung 8.8 zeigt
eine M¨oglichkeit der Repr¨asentation, die sich in der Implementierung (siehe Listing 8.8)
als g ¨unstig erweist: die Repr ¨asentation erfolgt als Liste der entfernten Tourkanten –
genauer: durch die Liste der Indizes der Tourknoten zwischen denen Kanten entfernt
wurden. Abbildung 8.9 zeigt, wie man nach Einziehen einer neuen Tourkante diese
Repr¨asentation anpassen muss: durch Verschmelzung zweier Tupel.

## Seite 266

8.4 Lokale Verbesserung 251
vik−1+1
vik−1
vi0
vi0+1
vi1
vi1+1
Repr¨asentiert als
=⇒ [(i0,i0 +1),(i1,i1 +1),..., (ik−1,ik−1 +1)]
Abb. 8.8: Eine an k Kanten aufgeschnittene Tour (v0,v1,...,v n,v0). Wir werden eine auf-
geschnittene Tour durch die Liste der fehlenden Tourkanten repr ¨asentieren. Hierbei ist eine
Tourkante jeweils durch ein Tupel der beiden Indizes der Knoten repr ¨asentiert, die diese Kan-
te verbindet. Diese Darstellung ist auch f ¨ur die sp ¨atere Implementierung (siehe Listing 8.8)
g¨unstig.
vip+1+1
vip+1
vip+1
vip
vip−1+1
vip−1
vi1+1
vi1
vi0+1
vi0
v0
=⇒
[..., (ip−1,ip−1 + 1),(ip,ip + 1),(ip+1,ip+1 + 1),... ]
⇓
[..., (ip−1,ip + 1),(ip+1,ip+1 + 1),... ]
Abb. 8.9:Die Verwendung der neuen Tourkante (v0,vp) zieht in der Repr ¨asentation der feh-
lenden Tourkanten eine Verschmelzung der Tupel (ip−1,ip−1 + 1)und (ip,ip + 1)zum neuen
Tupel (ip−1,ip + 1)nach sich.
Aufgabe 8.14
Wie viele M ¨oglichkeiten gibt es eine durch L ¨oschung von k Kanten zerfallene Tour
wieder neu zu verbinden? Geben Sie eine entsprechende von k abh¨angige Formel an.
Wir wollen zun¨achst eine Python-Funktion schreiben, die die Liste aller m¨oglichen Neu-
verbindungen einer durch L ¨oschung von k (mit k =len(i)) Kanten zerfallenen Tour
erzeugt. Die in Listing 8.8 implementierte Funktion allCrosses liefert die Liste aller
m¨oglichen Neuverbindungen einer an den durch den Parameter i speziﬁzierten Stellen
aufgeschnittenen Tour. Die Liste i repr¨asentiert die Stellen an der die Tour aufgeschnit-
ten ist – und zwar genau so, wie in den Abbildungen 8.8 und 8.9 erl ¨autert; wir gehen
also davon aus, dass i eine Liste von Tupeln ist. Eine der (insgesamt 48) Kreuztouren
einer Tour, die an den Tourknoten mit Index 10, 20, 50 und 70 aufgeschnitten ist, erhal-
ten wir beispielsweise durch den unten dargestellten Ausdruck (der einfach das zehnte

## Seite 267

252 8 Schwere Probleme und Heuristiken
1 def allCrosses(i ):
2 if len(i)==1: return [[]]
3 ts = []
4 for p in range(1,len(i )):
5 if p>0:
6 # R¨uckw¨arts-Teiltour
7 ts += [[( i [p] [0], i [p -1][1])] +x
8 for x in allCrosses( i [: p -1] + [(i [p -1][0], i [p] [1]) ] + i [p +1:] )]
9 if p<len(i) -1:
10 # Vorw¨arts-Teiltour
11 ts += [[( i [p] [1], i [p +1][0])] +x
12 for x in allCrosses( i [: p] + [( i [p] [0], i [p +1][1])] +i [p +2:] )]
13 return ts
Listing 8.8:Funktion, die die Liste aller m ¨oglichken Neuverbindungen einer an den durch die
Tupel-Liste i speziﬁzierten Stellen aufgeschnittenen Tour zur ¨uckliefert.
Element, der durch allCrosses erzeugten Kreuztourenliste zur¨uckliefert); die Abbildung
rechts daneben stellt diese Kreuztour graphisch dar.
>>> allCrosses( [ (10,11), (20,21), (50,51), (70,71) ]) [10]
>>> [(20, 11), (50, 21), (51, 70)]
v0 v71
v70
v51
v50
v11
v20
v10
v21
Die in Listing 8.8 gezeigte Implementierung erfolgt rekursiv mit Rekursionsabbruch in
Zeile 2. Wir gehen davon aus, dass es f ¨ur eine Tour, der nur eine Kante fehlt, keine
neuen ¨Uberkreuztouren gibt. Falls i mindestens zwei Tupel enth ¨alt, sammeln wir in
der Liste ts alle ¨Uberkreuztouren systematisch auf. Nehmen wir an, die Tour w ¨are an
k Kanten aufgeschnitten und i h¨atte folglich die Form [(i 0,i0 + 1),..., (ip−1,ip−1 +
1),(ip,ip+ 1),(ip+1,ip+1 + 1),..., (ik−1,ik−1 + 1)]; siehe Abbildung 8.9 f¨ur eine graphi-
sche Veranschaulichung. Es gibt – ausgehend von dem Knoten bei dem wir uns aktuell
beﬁnden (der aufgrund vorheriger Tupel-Verschmelzungen in i nicht mehr auftaucht) –
2k−2 m¨ogliche Knoten zu denen wir eine neue ”Kreuz“-Kante ziehen k¨onnen, n¨amlich
i0 + 1, i1, . . . undik−1. Die Knoten i0 und ik−1 + 1 kommen f¨ur Neuverbindungen nicht
in Frage – eine ”Kreuz“-Kante zu diesen Knoten w ¨urde bedeuten, die Tour in mehrere
Teiltouren zerfallen zu lassen. Die beiden if-Anweisungen in den Zeilen 5 und 9 stellen
sicher, dass diese beiden Knoten bei dieser Auswahl nicht gew ¨ahlt werden.
F¨ur jeden dieser 2k −2 Knoten erfolgt in einer Listenkomprehension ein rekursiver
Aufruf an allCrosses. Wir erl ¨autern den ersten Fall (die ”R¨uckw¨arts-Teiltour“ in den
Zeilen 7 und 8) – die Erl ¨auterungen der ”Vorw¨arts-Teiltour“ gehen analog. Dieser Fall
entspricht der in Abbildung 8.9 graphisch dargestellten Situation. Die neu eingezogene

## Seite 268

8.4 Lokale Verbesserung 253
Kante geht also zu Knoten mit Tourindex ip. Von da aus werden die Knoten (relativ
zur urspr ¨unglichen Richtung) r¨uckw¨arts bis zum Tourknoten mit Tourindex ip−1 + 1
durchlaufen – daher sprechen wir auch von einer ”R¨uckwarts-Teiltour“. Die Variable x
durchl¨auft in Zeile 8 rekursiv alle Kreuztouren. Der Parameter
i [ :p -1] + [( i [p -1][0], i [p] [1]) ] + i [p +1 :]
des rekursiven Aufrufs von allCrosses in Zeile 8 repr¨asentiert die verbleibenden fehlen-
den Kanten. Diese verbleibenden fehlenden Kanten erh ¨alt man durch Verschmelzung
zweier Tupel aus i – und zwar genau, wie in Abbildung 8.9 dargestellt.
Abbildung 8.10 veranschaulicht diesen sukzessiven Tupel-Verschmelzungsprozess w¨ahr-
end des Einziehens neuer Kanten am Beispiel der Wiederverbindung einer durch L¨osch-
ung von 5 Kanten zerfallenen Tour.
vi1+1
vi0+1
v0
vi2
vi2+1
vi3
vi3+1
vi4+1
vi0
(1)
(2) (4)
(3)
vi1
(5)
vi4
=⇒
[(i0,i0 + 1),(i1,i1 + 1),(i2,i2 + 1),(i3,i3 + 1),(i4,i4 + 1)]
(1) ⇓
[(i0,i0 + 1),(i1,i1 + 1),(i2,i3 + 1),(i4,i4 + 1)]
(2) ⇓
[(i0,i1 + 1),(i2,i3 + 1),(i4,i4 + 1)]
(3) ⇓
[(i0,i3 + 1),(i4,i4 + 1)]
(4) ⇓
[(i0,i4 + 1)]
(5) ⇓
[ ]
Abb. 8.10: Jede neu eingezogene Tourkante in einer aufgeschnittenen Tour bewirkt in der
Repr¨asentation der Menge der fehlenden Kanten die Verschmelzung zweier Tupel in ein neues
Tupel. In Listing 8.8 geschieht diese Verschmelzung zweier Tupel jeweils in den Zeilen 5, 9,
und 13 im Argument des rekursiven Aufrufs von allCrosses .
Aufgabe 8.15
Vor allem wenn k relativ groß ist (etwa k >5), ist es nicht immer sinnvoll sich sy-
stematisch alle Kreuztouren generieren zu lassen; in diesen F ¨allen tut man besser
daran, sich zuf¨allig eine der vielen m ¨oglichen Kreuztouren auszuw¨ahlen. Implemen-
tieren Sie eine entsprechende Python-Funktion randCross, die – genau wie die Funk-
tion allCrosses aus Listing 8.8 – eine Liste der fehlenden Tourkanten als Argument
¨ubergeben bekommt und eine zuf ¨allig ausgew¨ahlte Kreuz-Tour zur¨uckliefert.
Man beachte, dass die Funktion allCrosses aus Listing 8.8 unabh ¨angig von einer kon-
kreten Tour ist. Zur¨uckgeliefert werden lediglich Tourpositionen an denen Kreuzkanten
eingef¨ugt werden. Mit Hilfe der in Listing 8.9 gezeigten FunktionallCrossTours wird aus
den durch allCrosses erzeugten L¨oschpositionen eine konkrete Tour neu verbunden.

## Seite 269

254 8 Schwere Probleme und Heuristiken
1 def allCrossTours(tour,i ):
2 tours = []
3 for cross in allCrosses(i ):
4 t = []
5 for (i0,i1) in cross:
6 t += tour[i0:i1 +1] if i0<i1 else tour[i0:i1 -1: -1]
7 tours.append(t)
8 return [tour[:i [0] [0] +1] +t +tour[i[ -1][1] +1:] for t in tours]
Listing 8.9: Die Funktion crossTour wendet die durch allCrosses erzeugten Positionen der
Neuverbindungen auf eine bestimmte Tour an.
Entscheidend ist die Zeile 6: Hier wird auf Basis der in cross enthaltenen Tupel die
Tour neu verbunden. Ist i0 < i1, so entsteht die Vorw ¨arts-Teiltour tour [i0 :i1 +1], an-
dernfalls entsteht die R¨uckw¨arts-Teiltour tour [i0 :i1 -1 :-1]. Schließlich werden in Zeile
8 noch an jede so entstandene Tour das Anfangsst ¨uck tour [ :i [0] [0] +1] und Endest ¨uck
tour [i [ -1][1] :] angeh ¨angt.
Aufgabe 8.16
Implementieren Sie die k-Opt-Heuristik folgendermaßen:
(a) Schreiben Sie zun ¨achst eine FunktionrandCut(n,k), die aus einer Tour mitn Kno-
ten zuf¨allig k disjunkte Kanten ausw¨ahlt und die Anfangsknoten dieser Kanten
zur¨uckliefert.
>>>randCut(100,5)
>>> [16, 30, 73, 84, 99]
(b) Schreiben Sie eine Funktion kOpt(graph,k,m), die die kOpt-Heuristik implemen-
tiert. F¨ur j = k,k −1,..., 2 werden jeweils n-mal zuf¨allig j zu l¨oschende Kanten
gew¨ahlt; aus dieser entsprechend zerfallenen Tour wird die k ¨urzeste Kreuztour
gew¨ahlt.
Aufgabe 8.17
Wir wollen eine Variante der kOpt-Heuristik implementieren, die gew¨ahrleistet, dass
alle Kreuztouren, aller m¨oglichen Schnitte mit in Betracht gezogen werden.
(a) Implementieren Sie eine Funktion allCuts(n,k), die die Liste aller m ¨oglichen
L¨oschungen von k Kanten aus einer Tour mit n Knoten erzeugt.
(b) Implementieren Sie eine Funktion kOptAll(graph,k), die die k-Opt-Heuristik im-
plementiert und hierbei tats ¨achlich alle M¨oglichkeiten durchspielt.

## Seite 270

8.5 Ein Genetischer Algorithmus 255
8.5 Ein Genetischer Algorithmus
Ein genetischer Algorithmus nimmt sich den Evolutionsprozess der Natur als Vorbild.
Er besteht aus mehreren Runden ( ˆ =Generationen); in jeder Runde erzeugt ein geneti-
scher Algorithmus eine ganze Menge von m ¨oglichen L¨osungen ( ˆ = diePopulation bzw.
der Genpool), bzw. Teill¨osungen. Um von Runde inach Runde i+1 zu gelangen, werden
die m¨oglichen L¨osungen aus Runde igekreuzt und anschließend nach bestimmten Opti-
malit¨atskriterien selektiert; die daraus entstehenden modiﬁzierten L ¨osungen bilden die
L¨osungen der Runde i+ 1. Die entscheidende Operation ist die Kreuzung (engl.: Cross-
Over) zweier L ¨osungen. Im Allgemeinen erfolgt eine Kreuzung zweier L ¨osungen l und
l′so, dass die erste H¨alfte der einen L¨osung mit der zweiten H¨alfte der anderen L¨osung
kombiniert wird. In vielen F¨allen (nicht jedoch beim Travelling-Salesman-Problem) be-
steht diese Kombination einfach in der Konkatenation 2 der beiden L¨osungsh¨alften – in
Python darstellbar durch den Konkatenations-Operation ”+“. Die beiden L ¨osungskan-
didaten f¨ur die n¨achste Runde h¨atten dann die Form
lneu = l [0 :n/2] + l′[n/2 :n] ; l′
neu = l ′[0 :n/2] + l [n/2 :n] (8.4)
Eine sinnvolle Wahl der Populationsgr¨oße, d. h. der Anzahl der L¨osungen in einer Runde,
die Selektionskriterien und vor allem die genaue Ausgestaltung des Cross-Overs zweier
L¨osungen zu einer neuen L ¨osung, h¨angt sehr stark von dem konkreten Problem ab. Im
Falle des Travelling-Salesman-Problems sind zwei sinnvolle Cross-Over-Techniken der
Knoten-Cross-Over und der Kanten-Cross-Over.
8.5.1 Knoten-Cross-Over
Leider kann man die Knoten zweier Touren nicht ganz so einfach kreuzen, wie in Glei-
chung (8.4) dargestellt – diese einfache Art des Cross-Over w¨urde doppelte oder fehlende
Knoten in der entstehenden Tour nach sich ziehen. Man kann dies jedoch einfach verhin-
dern, wenn man beim Anf ¨ugen der zweiten H ¨alfte der zweiten Tour schon vorhandene
Knoten ¨uberspringt und am Ende alle ¨ubriggebliebenen Knoten anf¨ugt. Abbildung 8.11
zeigt diese Art des Cross-Overs an einem Beispiel.
Dies implementiert die Funktion nodeCrossOver:
1 def nodeCrossOver(tour1,tour2):
2 n = len(tour1)
3 return tour1[:n/2] +\
4 [v for v in tour2[n/2:] if v not in tour1[:n/2]] +\
5 [v for v in tour1[n/2:] if v not in tour2[n/2:]]
Listing 8.10: Implementierung des Knoten-Cross-Over
8.5.2 Kanten-Cross-Over
Eine meist bessere M ¨oglichkeit besteht darin, die Kanten der beiden zu kreuzenden
Touren in einem neuen Graphen G′zusammenzufassen und dann ¨uber einen Random-
2Konkatenation = Aneinanderh¨angen, Verketten

## Seite 271

256 8 Schwere Probleme und Heuristiken
1
2
3
4
5
6
8
9
7
1
2
3
4
5
6
8
9
7
1
2
3
4
5
6
7
8
9
nodeCrossOver
=⇒
Abb. 8.11: Knoten-Cross-Over zweier Touren: Die Knoten samt deren Verbindungen (durch-
gehende Linien) der oben im Bild dargestellten Tour werden ¨ubernommen; anschließend werden
die fehlenden Knoten samt deren Verbindungen (gestrichelte Linien) der zweiten H ¨alfe der un-
ten im Bild dargestellten Tour so weit wie m ¨oglich ¨ubernommen. Ab Knoten ”8“ ist dies nicht
mehr m¨oglich, denn dessen Tournachfolger, Knoten ”2“ wurde schon besucht.
Walk oder eine andere Heuristik eine Rundtour in diesem Graphen G′ zu erzeugen.
Abbildung 8.12 veranschaulicht diese M¨oglichkeit anhand eines Beispiels.
Listing 8.11 zeigt eine Implementierung des Kanten-Cross-Over.
1 def edgeCrossOver(graph, tour1,tour2):
2 n = len(tour1) -1
3 G = graphs.Graph(n)
4 for i in range(n-1):
5 for tour in (tour1,tour2):
6 G.addEdge(tour[i],tour[i +1], graph.w(tour[i ], tour [i +1]))
7 for tour in (tour1,tour2):
8 G.addEdge(tour[n -1],tour [0], graph.w(tour[n -1], tour[0]))
9 return randomWalk(G,1)
Listing 8.11: Implementierung des Kanten-Cross-Over
Entscheidend sind die Zeilen 6 und 8: Hier werden (innerhalb der for-Schleifen) alle
auf den beiden Touren tour1 und tour2 beﬁndlichen Kanten in einem neuen Graphen
G zusammengefasst. Zur ¨uckgegeben wird in Zeile 9 eine zuf ¨allige Tour durch den so
entstandenen Graphen.

## Seite 272

8.5 Ein Genetischer Algorithmus 257
1
2
3
4
5
6
8
9
7
1
2
3
4
5
6
7
8
9
1
2
3
5
6
8
9
7
RandomWalk
=⇒4
1
2
3
4
5
6
8
9
7
=⇒
Kanten
Vereinigung der
Abb. 8.12: Kanten-Cross-Over zweier Touren: Die Kanten zweier Touren werden zu einem
neuen Graphen vereint; anschließend wird auf dem so entstandenen Graphen ein Random-Walk
durchgef¨uhrt.
Aufgabe 8.18
Implementieren Sie die in Zeile 9 in Listing 8.11 verwendete Funktion randomWalk
folgendermaßen: randomWalk soll mit vorhandenen Kanten versuchen eine zuf ¨allige
Tour zu konstruieren. Sollte es nicht mehr ”weitergehen“, weil alle Nachbarn des ak-
tuellen Knotens schon besucht wurden, dann sollterandomWalk zur¨ucksetzen und bei
einem vorherigen Knoten eine andere Alternative w ¨ahlen (ein solches Zur ¨ucksetzen
nennt man auch Backtracking).
8.5.3 Die Realisierung des genetischen Algorithmus
Die eigentliche Implementierung des genetischen Algorithmus kann wie in Listing 8.12
gezeigt erfolgen.
Durch den Parameter p kann die Populationsgr¨oße speziﬁziert werden; durch den Para-
meter g kann die Anzahl der Generationen festgelegt werden. In Zeile 2 wird auf Basis
der Random-Insertion-Heuristik die erste Generation erzeugt, bestehend aus p unter-
schiedlichen Touren – es k¨onnten selbstverst¨andlich auch andere Heuristiken verwenden
werden, um die initiale Population zu erzeugen, jedoch bietet sich die Random-Insertion-
Heuristik dadurch an, dass sie in (nahezu) jedem Durchlauf eine andere Tour liefert. Wir
gehen hier davon aus, dass tspRandIns immer ein Tupel bestehend aus der Tourl ¨ange
und der eigentlichen Tour zur¨uckliefert.
Die for-Schleife ab Zeile 3 durchl¨auft die g Generationen. Wir lassen hier grunds¨atzlich
das beste Drittel der letzten Generation ¨uberleben – dies ist jedoch eine mehr oder
weniger willk¨urliche Festlegung mit der man experimentieren kann. Die while-Schleife
ab Zeile 5 erzeugt dann die restlichen Individuen der neuen Population newPop.

## Seite 273

258 8 Schwere Probleme und Heuristiken
1 def tspGen(graph, p, g):
2 pop = sorted([tspRandIns(graph) for in range(p)])
3 for i in range(g):
4 newPop = pop[:p/3] # das beste Drittel ¨uberlebt
5 while len(newPop)<5 *len(pop):
6 tours = random.sample(pop,2)
7 childTour = edgeCrossOver(graph, tours[0][1], tours [1] [1])
8 newPop.append((pathVal(graph,childTour)/1000,childTour))
9 pop = sorted(newPop)[:p ]
10 return pop
Listing 8.12: Realisierung des genetischen Algorithmus
Aufgabe 8.19
Der in Listing 8.12 gezeigte genetische Algorithmus f ¨ur das Travelling-Salesman-
Problem weist folgende Schw ¨ache auf: Die Populationen tendieren dazu, ¨uber die
Zeit (nach etwa 5 Generationen) genetisch zu verarmen – in diesem Fall heißt das:
viele der erzeugten Individuen sind gleich.
(a) Passen Sie den Algorithmus so an, dass sichergestellt wird, dass eine Population
keine identischen Individuen enth¨alt.
(b) Man stellt jedoch schnell fest: Der Algorithmus ”schaﬀt“ es nach einigen Genera-
tionen grunds¨atzlich nicht mehr, neuartige Individuen hervorzubringen. Passen
Sie den Algorithmus so an, dass maximal 50-mal versucht wird ein neues Indivi-
duum hervorzubringen – danach wird einfach ein schon vorhandenes Individuum
der Population hinzugef¨ugt.
Aufgabe 8.20
Der Algorithmus in Listing 8.12 verwendet f¨ur zur Implementierung eines genetischen
Algorithmus das Kanten-Cross-Over als Reproduktionsart. Implementieren Sie eine
Variante, die stattdessen das Knoten-Cross-Over verwendet und vergleichen Sie die
Qualit¨aten der Ergebnisse f ¨ur die beiden Reproduktionstechniken.
8.6 Ein Ameisen-Algorithmus
¨Ahnlich, wie sich genetische Algorithmen ein Vorbild an der Funktionsweise nat ¨urli-
cher Prozesse nehmen, tun dies auch Ameisen-Algorithmen, die das Verhalten eines
Schwarmes bei der Suche nach L ¨osungen simulieren – vorzugsweise f ¨ur L¨osungen von
Problemen der kombinatorischen Optimierung. Die Heuristiken, die wir in diesem Ab-
schnitt beschreiben, sind auch unter dem Namen ”Ant Colony Optimization“ (kurz:
”ACO“) bekannt.

## Seite 274

8.6 Ein Ameisen-Algorithmus 259
wenig Pheromon
mehr Pheromon
viel Pheromon
Abb. 8.13: Je mehr Pheromon sich auf einem bestimmten Pfad beﬁndet, desto gr ¨oßer ist
die Wahrscheinlichkeit, dass die Ameisen den entsprechenden Pfad w ¨ahlen. Da das Pheromon
nach einer gewissen Zeit verdunstet, ist die Pheromonkonzentration auf dem l ¨angeren Pfad
geringer als auf dem k ¨urzeren; die Ameisen w ¨ahlen also nach einer gewissen Zeit mit gr ¨oßerer
Wahrscheinlichkeit den k ¨urzeren Pfad.
Auf der Wege-Suche nach Nahrung verhalten sich Ameisen in der folgenden Art und
Weise: Die einzelnen Tiere (bei der Implementierung in eine Software-System auch ge-
legentlich als ”Agenten“ bezeichnet) suchen die Umgebung zun¨achst zuf¨allig ab. Findet
ein Tier eine Nahrungsquelle, so kehrt es zum Nest zur ¨uck und hinterl¨asst eine Phero-
monspur3. Je gr ¨oßer die Pheromonkonzentration auf einem Pfad, desto gr ¨oßer ist die
Wahrscheinlichkeit, dass eine bestimmte Ameise diesen Pfad w¨ahlt. Pheromone sind al-
lerdings ﬂ¨uchtig und verdunsten nach einer gewissen Zeit. Je mehr Zeit eine bestimmte
Ameise ben¨otigt, um einen Pfad abzulaufen, desto mehr Zeit haben auch die hinterlas-
senen Pheromone um zu verdunsten. Dies ist genau der Grund, warum Ameisen in der
Lage sind, k¨urzeste Wege zu ﬁnden. Abbildung 8.13 veranschaulicht diesen Sachverhalt.
Typisch f¨ur Schw¨arme (wie eben Ameisen, oder große Vogel- oder Insektenschw ¨arme)
ist die Beobachtung, dass das Verhalten des Schwarmes nicht durch einen Anf¨uhrer oder
durch hierarchische Beziehungen unter den einzelnen ”Agenten“ zustande kommt. Es
gibt keine zentrale Abstimmung und jeder ”Agent“ in einem Schwarm folgt denselben
einfachen Regeln. Ein solches emergentes (d. h. aus sich selbst heraus entstehendes)
Verhalten bezeichnet man oft als Schwarm-Intelligenz. Es hat sich gezeigt, dass die
Methoden der Schwarm-Intelligenz und insbesondere die simulierte Verhaltensweise von
Ameisen, eine der eﬃzientesten Methoden liefert, eine gute L ¨osung f ¨ur das TSP zu
ﬁnden.
Um ein lokales Optimum des Travelling-Salesman-Problems durch einen simulierten
Ameisen-”Schwarm“ zu suchen, muss der dem TSP-Problem zugrundeliegende Ab-
standsgraph wie folgt konservativ erweitert werden: Ein Kante ( i,j) muss neben dem
3Als Pheromon bezeichnet man eine spezielle Art ﬂ ¨uchtiger Dufthormone, die Insekten – speziell:
Ameisen – zur Orientierung dienen.

## Seite 275

260 8 Schwere Probleme und Heuristiken
Gewicht w(i,j), das den Abstand der beiden Knoten iund jrepr¨asentiert, noch ein wei-
teres Gewicht p(i,j) haben. Der Wert p(i,j) repr¨asentiert hierbei Menge an Pheromon,
die sich auf der Kante ( i,j) beﬁndet.
8.6.1 Erster Ansatz
Jede Ameise durchl¨auft den Graphen komplett. Der jeweils n¨achste Knoten j von Kno-
ten i aus wird gem ¨aß einer bestimmten Wahrscheinlichkeit gew ¨ahlt, die sich aus der
Entfernung des n¨achsten Knotens und dem Pheromongehalt der entsprechenden Kan-
te ergibt – je h ¨oher hierbei der Pheromongehalt p(i,j) der Kante und je geringer der
Abstand w(i,j), desto wahrscheinlicher wird der Knoten j als n¨achster Knoten auf der
Rundtour gew¨ahlt.
¨Ubergangsregel. Nennen wir Pr k(i,j) die Wahrscheinlichkeit, dass die auf Knoten i
beﬁndliche Ameise k als N¨achstes den Knoten j w¨ahlt. Es erweist sich als g¨unstig diese
Wahrscheinlichkeit folgendermaßen festzulegen:
Prk(i,j) =









p(i,j) · 1
w(i,j)β
∑
v∈Γk(i)
p(i,v) · 1
w(i,v)β
, falls j ∈Γk(i)
0, sonst
(8.5)
wobei Γ k(i) die Menge der Knoten bezeichnet, die von Ameise k von Knoten i aus
erreichbar sind. ¨Uber den Parameter βkann man bestimmen, wie sich der Abstandswert
w gegen¨uber der Pheromonmenge p bei der Bestimmung der Wahrscheinlichkeit Pr k
verh¨alt: Je gr ¨oßer β gew¨ahlt wird, desto gr ¨oßer f ¨allt die Pheromonmenge der Kante
(i,j) in Gewicht und desto mehr wird der Abstandswert bei der Entscheidung dar ¨uber,
welcher Knoten als N¨achstes gew¨ahlt wird, ausgeblendet.
Um also zu berechnen, mit welcher Wahrscheinlichkeit die Kante (i,j ) gew¨ahlt wird,
wird das Verh ¨altnis zwischen L ¨ange und Pheromongehalt der Kante ( i,j) durch die
Summe der Verh¨altnisse aller von Knoten i aus erreichbaren Kanten geteilt.
Implementierung der ¨Ubergangsregel. Listing 8.13 zeigt den Python-Code zur Si-
mulation einer Ameise. Im Gegensatz zu allen vorigen Anwendungen, m ¨ussen wir hier
zwei Werte je Kante speichern: eine Entfernung und eine Pheromon-Konzentration. Der
Einfachheit halber vermeiden wir Anpassungen an der in Abschnitt 5.1.2 beschriebenen
Graph-Klasse, sondern gehen einfach davon aus, dass ein Gewicht graph.w(i, j) einer
Kante (i , j) des betrachteten Graphen aus zwei Komponenten besteht: Die erste Kom-
ponente graph.w(i, j) [0] speichert die Entfernung zwischen Knoten i und Knoten j, die
zweite Komponenten graph.w(i, j) [1] speichert den Pheromongehalt der Kante ( i , j).
In Variable i ist immer der als N¨achstes zu besuchende Knoten gespeichert. Diese wird
zun¨achst in Zeile 4 zuf¨allig gew¨ahlt. Die while-Schleife in Zeile 5 wird solange durchlau-
fen, bis alle Knoten des Graphen von der Ameise besucht wurden. Die Listetour enth¨alt

## Seite 276

8.6 Ein Ameisen-Algorithmus 261
die bisherige von der Ameise gelaufene Tour in Form eine Knotenliste. Die Knotenli-
ste js enth¨alt immer die noch zu besuchenden Knoten, entspricht also dem Ausdruck
Γk in Formel (8.5). Die in Zeile 8 deﬁnierte Liste ps enth¨alt die (noch nicht normier-
ten) ¨Ubergangswahrscheinlicheiten: ps [k ] enth¨alt die relative Wahrscheinlichkeit, dass
als N¨achstes der Knoten js [k ] gew ¨ahlt wird; dies entspricht genau dem Teilausdruck
p(i,j) · 1
w(i,j)β aus Formel (8.5). Die Funktion chooseIndex (siehe Aufgabe. 8.21) w ¨ahlt
auf Basis von ps per Zufallsentscheidung den n ¨achsten Knoten aus, den die Ameise
besucht.
1 def ant(graph):
2 def w(i,j ): return graph.w(i,j) [0]
3 def p(i , j ): return graph.w(i,j) [1]
4 tour = [] ; n = graph.numNodes ; i = randint(1,n)
5 while len(tour)<graph.numNodes-1:
6 tour.append(i)
7 js = [ j for j in range(1,n +1) if j not in tour ] # Liste der verbleibenden Knoten
8 ps = [ p(i , j) *1./(w(i,j)**beta) for j in js ] # Liste der Wahrscheinlichkeiten
9 i = js [chooseIndex(ps)] # N¨achster Knoten
10 tour = tour + [tour [0] ] # Rundtour!
11 return tour, pathVal(graph,tour)
Listing 8.13: Simulation einer Ameise
Aufgabe 8.21
Implementieren Sie die Funktion chooseIndex, die eine Liste von Zahlen [ x1,...x n]
¨ubergeben bekommt und mit Wahrscheinlichkeit pi die Zahl i zur¨uckliefert, wobei
pi = xi
n∑
k=1
xk
Pheromon-Anpassung. Wurde der Graph von allen Ameisen vollst ¨andig durchlau-
fen, wird der Pheromongehalt folgendermaßen angepasst: Zum Einen verﬂ ¨uchtigt sich
ein Teil des Pheromons; zum Anderen erh¨oht jede Ameise das Pheromon auf den von ihr
verwendeten Kanten umgekehrt proportional zur L¨ange der von ihr gelaufenen Tour. Bei
einer langen Tour wird das Pheromon also um einen geringen Betrag erh ¨oht, w¨ahrend
bei einer kurzen Tour das Pheromon um einen verh ¨altnism¨aßig großen Betrag erh ¨oht
wird.
p(i,j) := (1 −α) ·p(i,j) +
m∑
k=1
∆pk(i,j) (8.6)

## Seite 277

262 8 Schwere Probleme und Heuristiken
wobei
∆pk(i,j) =



1
pathVal(tourk), falls (i,j) ∈ tourk
0, sonst
Hierbei ist:
•pathVal(t) : die L ¨ange der Tour t
•tourk: die von Ameise k gegangene Tour
•m: die Anzahl der verwendeten Ameisen
•α: der Zerfallsparameter – je gr ¨oßer α, desto ﬂ ¨uchtiger ist das mo-
dellierte Pheromon.
Implementierung der Pheromon-Anpassung. Wir teilen die Umsetzung von For-
mel (8.6) auf zwei Funktionen auf. Am Ende eines Zyklus, nachdem alle Ameisen ¨uber
den Graphen gelaufen sind, l ¨asst die in Listing 8.14 gezeigte Funktion vapourize Phe-
romon auf jeder Kante ”verdunsten“. Die Zuweisung in Zeile 5 entspricht hierbei dem
ersten Summanden in Formel (8.6).
1 def vapourize(graph):
2 for i in range(1,graph.numNodes+1):
3 for j in range(1,graph.numNodes+1):
4 (w,p) = graph.w(i,j)
5 p neu = (1. -alpha) *p
6 graph.addEdge(i,j ,(w,p neu))
Listing 8.14: Diese Funktion l ¨asst einen durch α bestimmten Teil von Pheromon auf jeder
Kante von ”graph“ verdunsten.
Die in Listing 8.15 gezeigte Funktion adapt setzt den zweiten Summanden aus Formel
(8.6) um. Jede Ameise erh ¨oht auf den Kanten ”ihrer“ Tour den Pheromonwert um den
Kehrwert der L¨ange der Tour. In Zeile 5 in Listing 8.15 wird diese Anpassung berechnet.
1 def adapt(graph, tour, L k):
2 L kInv = 1./L k
3 for i in range(len(tour) -1):
4 (w,p) = graph.w(tour[i],tour [i +1])
5 p neu = p +L kInv
6 graph.addEdge(tour[i],tour [i +1],(w,p neu))
Listing 8.15: Diese Funktion erh ¨oht Pheromon auf den Kanten einer Tour ”tour“ antipro-
portional zur L ¨ange L k dieser Tour.
Implementierung eines ACO-Zyklus. Als einen ACO-Zyklus bezeichnen wir einen
kompletten Durchlauf aller Ameisen durch den Graphen zusammen mit der anschließen-
den Pheromon-Anpassung. Listing 8.16 zeigt die Implementierung eines ACO-Zyklus.

## Seite 278

8.6 Ein Ameisen-Algorithmus 263
1 def acoCycle(graph):
2 tours = [ant(graph) for in range(M)]
3 vapourize(graph)
4 for (t , tl ) in tours: adapt(graph,t , tl )
5 tours. sort(key=lambda x:x[1])
6 return tours[0][1] # L¨ange der k¨urzesten Tour
Listing 8.16:Implementierung eines ACO-Zyklus: Alle M Ameisen durchlaufen den Graphen;
anschließend werden die Pheromone auf den Kanten angepasst.
Zun¨achst werden in Zeile 2 die M Ameisen ”losgeschickt“ und die von ihnen gelaufe-
nen Touren in der Liste tours aufgesammelt. Der Aufruf von vapourize in Zeile 3 l ¨asst
anschließend Pheromon verdampfen. In Zeile 4 werden die Pheromon-Werte auf allen
Touren entsprechend dem zweiten Summanden aus Formel (8.6) erh¨oht. In Zeile 5 wer-
den die Touren ihrer L ¨ange nach sortiert, um schließlich die L ¨ange der k ¨urzesten Tour
zur¨uckzuliefern.
Aufgabe 8.22
In Zeile 5 in Listing 8.16 werden die Touren ihrer L¨ange nach sortiert, um schließlich
die k ¨urzeste Tour zur ¨uckzuliefern, die in diesem Zyklus von einer Ameise gelaufen
wurde.
(a) Es gibt jedoch eine schnellere Methode – zumindest was die asymptotische Lauf-
zeit betriﬀt – die k ¨urzeste Tour zu erhalten. Welche?
(b) Implementieren Sie mit Hilfe dieser Methode eine schnellere Variante von
acoCylceH.
(c) F ¨uhren mit Hilfe von Pythons timeit-Modul Laufzeitmessungen, um zu pr ¨ufen,
ob acoCycleH tats¨achlich performanter ist als acoCylce.
8.6.2 Verbesserte Umsetzung
Beim bisherigen Vorgehen durchl ¨auft jede Ameise die Knoten des Graphen komplett;
dann wird die Pheromonmenge auf allen Kanten aktualisiert und anschließend eine wei-
tere Iteration durchgef¨uhrt, usw. Mit diesem Vorgehen kann man – bei Wahl geeigneter
Parameter – zwar gute Touren ﬁnden, jedoch ist die Methode zu aufw ¨andig, als dass
sie auf große Probleme (mit mehr als 100 Knoten) angewendet werden k ¨onnte.
Wir stellen im Folgenden pragmatische Verbesserungen und Erweiterungen vor, mit
denen auch gr¨oßere TSP-Probleme in angemessener Zeit bearbeitet werden k ¨onnen.
Modiﬁkation der ¨Ubergangsregel. ¨Uber eine Zufallszahl q0 wird bestimmt, ob For-
mel (8.5) verwendet wird, oder ob einfach nicht-probabilistisch die ”beste“ (in Bezug
auf L¨ange und Pheromongehalt) Kante gew¨ahlt wird. F¨ur die Bestimmung des n¨achsten

## Seite 279

264 8 Schwere Probleme und Heuristiken
Knotens j, ausgehend von einem Knoten i ergibt sich also f ¨ur Ameise k die folgende
neue Formel:
j =



maxv∈Γk(i)
{
p(i,v)
w(i,v)β
}
, falls random() ≤q0
Bestimme j aus (8.5), sonst
(8.7)
wobei random() eine Zufallszahl auf dem Interval [0 ,1) ist.
Einf¨uhrung einer lokalen Pheromon-Anpassung. Zus¨atzlich zur im n¨achsten Ab-
schnitt beschriebenen (globalen) Pheromon-Anpassung, kommt nun noch eine lokale
Pheromon-Anpassung: Von jeder Ameise wird auf den von ihr besuchten Kanten eine
Pheromon-Anpassung folgendermaßen durchgef¨uhrt:
p(i,j) = (1 −ρ) ·p(i,j) + ρ·p0 (8.8)
Hierbei ist:
•p0 Eine Pheromon-Konstante. Ein m ¨oglicher einmalig berechneter
Wert hierf¨ur, der sich in Experimenten bew ¨ahrt hat, ist:
p0 = 1
pathVal(tournn)
wobei tournn die durch die Nearest-Neighbor-Heuristik gefundene
”optimale“ Rundtour durch den Graphen ist.
•ρ Weiterer Zerfallsparameter
Implementierung der modiﬁzierten ¨Ubergangsregel und lokalen Pheromon-
Anpassung. Listing 8.17 zeigt den modiﬁzierten Python-Code zur Simulation einer
Ameise. Die Ameise gehorcht der in Formel (8.7) beschriebenen modiﬁzierten ¨Uber-
gangsregel. Diese wird in den Zeilen 11 bis 15 umgesetzt. Zus¨atzlich wird auf jeder gegan-
genen Kante mittels der lokalen Funktion adaptLocal eine lokale Pheromon-Anpassung
durchgef¨uhrt; dies geschieht zum Einen in Zeile 16 innerhalb der while-Schleife, und
in Zeile 18 f ¨ur die zuletzt einf ¨ugte Kante zur ¨uck zum Ausgangsknoten. Die ab Zeile 5
deﬁnierte Funktion adaptLocal realisiert genau die in Formel (8.8) beschriebene lokale
Anpassung.
1 def ant(graph):
2 tour = [] ; n = graph.numNodes ; i = randint(1,n)
3 def w(i,j ): return graph.w(i,j) [0]
4 def p(i , j ): return graph.w(i,j) [1]
5 def adaptLocal(i, j ):
6 p neu = (1 -rho) *p(i,j) +rho *p 0
7 graph.addEdge(i,j ,(w(i, j ),p neu))
8 while len(tour)<graph.numNodes-1:
9 tour.append(i) ; i old = i
10 js = [j for j in range(1,n +1) if j not in tour]

## Seite 280

8.6 Ein Ameisen-Algorithmus 265
11 if random()<q 0:
12 i = max(js, key=lambda j: p(i,j) *1./(w(i,j)**beta))
13 else:
14 ps = [ p(i , j) *1./(w(i,j)**beta) for j in js ]
15 i = js [chooseIndex(ps)]
16 adaptLocal(i old , i)
17 tour = tour + [tour [0] ]
18 adaptLocal(tour[ -2],tour [ -1])
19 return tour, pathVal(graph,tour)
Listing 8.17: Simulation einer Ameise, die der modifzierten ¨Ubergangsregel gehorcht.
Modiﬁkation der (globalen) Pheromon-Anpassung. Formel (8.6) wird so ange-
passt, dass nicht mehr alle, sondern nur noch die k ¨urzeste Tour der aktuellen Iteration
betrachtet wird.
p(i,j) := (1 −α) ·p(i,j) + ∆p(i,j) (8.9)
wobei
∆p(i,j) =



1
pathVal(tourgb), falls (i,j) ∈ tourgb
0, sonst
Hierbei ist tourgb die global-beste Tour der aktuellen Iteration.
Implementierung der modiﬁzierten Pheronom-Anpassung. Listing 8.18 zeigt
die Implementierung der globalen Pheromon-Anpassung, basierend auf einer bestimm-
ten durch eine Ameise gegangenen Tour tour der L¨ange L k.
1 def adaptGlobal(graph, tour, L k):
2 L kInv = 1./L k
3 for i in range(len(tour) -1):
4 (w,p) = graph.w(tour[i],tour [i +1])
5 pNeu = p +L kInv
6 graph.addEdge(tour[i],tour [i +1],(w,pNeu))
Listing 8.18: Die Funktion adaptGlobal implementiert die globale Pheromon-Anpassung
In der for-Schleife ab Zeile 3 werden die Pheromone auf allen Kanten der Tour tour um
den Kehrwert L kInv der L¨ange L k der Tour erh¨oht. Hierbei ist p die alte Pheromon-
menge und pNeu die neu berechnete Pheromonmenge; in Zeile 6 wird schließlich der
alte Pheromonwert mit dem neuen ¨uberschrieben.

## Seite 281

266 8 Schwere Probleme und Heuristiken
Aufgabe 8.23
Wenden Sie den ”verbesserten“ Ameisenalgorithmus, auf das Suchen einer kurzen
Rundtour durch die 100 gr ¨oßten St ¨adte Deutschlands an und vergleichen Sie Er-
gebnisse mit denen anderer Heuristiken (etwa der Nearest-Neighbor-Heuristik, der
Farthest-Insertion-Heuristik oder der Tourverschmelzung). Halten Sie hierbei – um
eine gute Vergleichbarkeit zu gew¨ahrleisten – die Berechnungszeiten m¨oglichst gleich
lang.

## Seite 282

A Python Grundlagen
A.1 Die Pythonshell
Pythonprogramme werden i. A. nicht compiliert sondern durch einen Interpreter aus-
gef¨uhrt. Python bietet eine interaktive ”Shell“ an, mit der Pythonausdr ¨ucke und -
kommandos auch direkt am Pythoninterpreter ausprobiert werden k ¨onnen. Diese Shell
arbeitet in einer sog. Read-Eval-Print-Loop (kurz: REPL): Pythonausdr ¨ucke werden
also interaktiv eingelesen, diese werden ausgewertet und der Ergebniswert ausgegeben
(sofern er eine Stringrepr¨asentation besitzt). Wird dagegen ein Python-Kommando ein-
gegeben, so wird das Kommando einfach durch Python ausgef ¨uhrt. Diese interaktive
Pythonshell erweist sich besonders f¨ur das Erlernen, Ausprobieren und Experimentieren
mit Algorithmen als didaktisch n ¨utzlich.
Pythons Shell kann entweder von der Kommandozeile aus durch Eingabe des Kom-
mandos ”python“ gestartet werden – dies ist etwa unter Linux und Linux- ¨ahnlichen
Betriebssystemen ¨ublich. Windows-Installationen bieten dar¨uberhinaus oft die spezielle
Anwendung ”IDLE“ an, mit der die Pythonshell betreten werden kann. Hier ein Beispiel
f¨ur das Verhalten der Pythonshell (das ”>>>“ stellt hierbei die Eingabeauﬀorderung der
Pythonshell dar):
>>>x = 2**12
>>>x/2
2048
In der ersten Zeile wurde ein Kommando (n ¨amlich eine Zuweisung) eingegeben, das
durch Python ausgef¨uhrt wurde (und keinen R¨uckgabewert lieferte). In der zweiten Zeile
wurde ein Ausdruck eingegeben; dieser wird ausgewertet und die Stringrepr ¨asentation
auf dem Bildschirm ausgegeben.
A.2 Einfache Datentypen
A.2.1 Zahlen
Pythons wichtigste Zahlen-Typen sind Ganzzahlen ( int), lange Ganzzahlen (long int ),
Gleitpunktzahlen (ﬂoat ). Einige einfache Beispiele f¨ur Python-Zahlen sind”12“, ”3.141“,
”4.23E -5“ (Gleitpunkt-Darstellung), ”0xFE“ (hexadezimale Darstellung), ”3/4“ (Bruch-
zahlen), ”12084131941312L“ (long integers mit beliebig vielen Stellen).

## Seite 283

268 A Python Grundlagen
A.2.2 Strings
Strings sind in Python Sequenzen einzelner Zeichen. Im Gegensatz zu Listen und Dic-
tionaries (die wir sp¨ater ausf¨uhrlich behandeln) sind Strings unver¨anderlich, d. h. ist ein
bestimmter String einmal deﬁniert, so kann er nicht mehr ver ¨andert werden. Man hat
die Wahl, Strings entweder in doppelte Anf¨uhrungszeichen (also: "...") oder in einfache
Anf¨uhrungszeichen (also: '...') zu setzen. Die spezielle Bedeutung der Anf ¨uhrungs-
zeichen kann, ganz ¨ahnlich wie in der bash, mit dem Backspace (also: \) genommen
werden. Syntaktisch korrekte Python-Strings w¨aren demnach beispielsweise:
"Hallo", 'Hallo', '"Hallo"', '\'\'', "Python's", 'Hallo Welt', . . .
Verwendet man dreifache Anf ¨uhrungszeichen (also: """...""" oder '''...'''), so
kann man auch mehrzeilige Strings angeben.
Aufgabe A.1
Geben Sie mit dem Python print-Kommando den Text
Strings in Python koennen entweder mit "double ticks"
oder mit 'einfachen ticks' umschlossen werden.
A.2.3 Variablen
Variablen sind, genau wie in anderen Programmiersprachen auch, (ver¨anderliche) Platz-
halter f¨ur bestimmte Werte. Variablennamen m ¨ussen mit einem Buchstaben oder mit
dem Zeichen ” “ beginnen und d ¨urfen keine Leerzeichen oder Sonderzeichen (außer
eben dem Zeichen ” “) enthalten. Korrekte Variablennamen sind beispielsweise ”i“,
” i“, ”Kaese“ oder ”kaese“; die Zeichenketten ”2dinge“ oder ”leer zeichen “ w¨aren bei-
spielsweise keine korrekten Variablennamen.
A.2.4 Typisierung
Python ist, im Gegensatz zu vielen g ¨angigen Programmiersprachen, nicht statisch ge-
typt; d. h. der Typ einer Variablen muss nicht vor Ausf ¨uhrung eines Programms fest-
gelegt sein, sondern er wird dynamisch – also w ¨ahrend der Programmausf ¨uhrung –
bestimmt. Das hat den Vorteil, dass Variablen nicht deklariert werden m ¨ussen; man
muss Ihnen einfach einen Wert zuweisen, wie etwa in folgendem Beispiel:
>>>x = 2.01
Der Python-Interpreter leitet dann einfach den Typ der Variablen aus der ersten Zu-
weisung ab.
Die Verwendung von Variablen kann grunds ¨atzlich ﬂexibler erfolgen als bei statisch
getypten Programmiersprachen. Ein Beispiel (das die if-Anweisung verwendet, die im
n¨achsten Abschnitt eingef¨uhrt wird):
if gespraechig:
x = "Guten Morgen"

## Seite 284

A.2 Einfache Datentypen 269
else:
x = 12**12
print x
Der Typ der Variablen x ist vor Programmausf ¨uhrung nicht bestimmt. Ob s vom Typ
str oder vom Typ long int sein wird, h¨angt vom Inhalt der Variablen gespraechig ab.
A.2.5 Operatoren
Die folgende Tabelle zeigt eine Auswahl an Operatoren, die Python anbietet, um Aus-
dr¨ucke zu verkn¨upfen.
X +Y, X -Y Plus/Konkatenation, Minus
Beispiele: >>> 2 + 3
5
>>> '2' + '3'
'23'
>>> [1,2,3 ]+ [10]
[ 1,2,3,10 ]
X *Y, X **Y Multiplikation, Potenzierung
Beispiele: >>> 2 *6
12
>>> '2' *6
'222222'
>>> [0,1 ]*3
[ 0,1,0,1,0,1 ]
X / Y, X // Y Division, restlose Division
X %Y Rest (bei der Division)
Beispiele: >>> 2.0/3
0.66666666
>>> 2/3
0
>>> 17% 7
3
X<Y, X ≤Y kleiner, kleinergleich (lexikographisch bei Sequenzen)
X>Y, X ≥Y gr¨oßer, gr¨oßergleich (lexikographisch bei Sequenzen)
Beispiele: >>> 4<2
False
>>> 'big'<'small'
True
>>> [1,100] <[2,1]
True
X == Y, X= Y! Gleichheit, Ungleichheit (Werte)
X is Y, X is not Y Objektgleichheit, Objektungleichheit
X &Y, X |Y, X ˆ Y Bitweises ”Und“, bitweises ”Oder“, bitweises exkl. ”Oder“
˜ X Bitweise Negation
X <<Y, X ≫Y Schiebe X nach links, rechts um Y Bits
Beispiele: >>> 9 & 10
8
>>> 10 | 6
14
>>> 3 < <4
48
X and Y Wenn X falsch, dann X, andernfalls Y
X or Y Wenn X falsch, dann Y, andernfalls X
not X Wenn X falsch, dann True, andernfalls False
X in S Test auf Enthaltensein eines Elements X in einer Kollektion
S von Werten.
Beispiele: >>> True and False
False
>>> 'al' in 'hallo'
True
>>> 4 in [1,2,3 ]
False

## Seite 285

270 A Python Grundlagen
Einige der Operatoren sind polymorph, d. h sie sind auf unterschiedliche Typen anwend-
bar. Die hier wirkende Art der Polymorphie nennt man auch ¨Uberladung. Ein ¨uberla-
dener Operator verwendet i. A. f¨ur verschiedene Typen auch verschiedene Algorithmen.
Ein typisches Beispiel stellt der Python-Operator + dar: Er kann sowohl auf Strings
oder auf Listen, als auch auf Ganzzahlwerte, auf Fließkommawerte oder auf komplexe
Zahlen angewendet werden; w ¨ahrend der +-Operator Strings und Listen konkateniert
(d. h. zusammenf¨ugt) f¨uhrt er auf Zahlenwerten eine klassische Addition durch.
A.3 Grundlegende Konzepte
A.3.1 Kontrollﬂuss
Einr¨ucktiefe. Die Einr¨ucktiefe von Python-Kommandos spielt – im Gegensatz zu vie-
len anderen Programmiersprachen – eine Rolle. Damit haben die Leerzeichen am Zeilen-
anfang eine Bedeutung und sind Teil der Syntax der Programmiersprache. Die Einr¨uck-
tiefe dient dazu Anweisungsbl¨ocke zu speziﬁzieren: Anweisungen, die dem gleichen An-
weisungsblock angeh¨oren, m¨ussen die gleiche Einr¨ucktiefe haben. Der Anweisungsblock,
der einer if-Anweisung oder einer while-Anweisung folgt, wird also nicht explizit ein-
geklammert, sondern die Anweisungen werden durch den Python-Interpreter dadurch
als zugeh¨orig erkannt, dass sie dieselbe Einr ¨ucktiefe haben.
Steuerung des Kontrollﬂusses. Wie beschrieben im Folgenden die drei wichtigsten
Kommandos zur Steuerung des Kontrollﬂusses, d. h. zur Steuerung des Ablaufs der
Python-Kommandos: Die if-Anweisung, die while-Anweisung und die for-Anweisung.
F¨ur die Syntaxbeschreibungen dieser (und weiterer) Kommandos werden die folgenden
Formalismen verwendet:
 In eckigen Klammern eingeschlossene Teile (also: [. . . ]) sind optionale Teile, d. h.
diese Teil der Syntax k¨onnen auch weggelassen werden.
 Ist der in eckigen Klammern eingeschlossene Teil von einem Stern gefolgt (also:
[. . . ]*), so kann der entsprechende Teil beliebig oft (auch 0-mal) wiederholt wer-
den. Beispielsweise kann der elif-Teil der if-Anweisung beliebig oft (und eben
auch 0-mal) hintereinander verwendet werden.
Die for-Schleife:
if ⟨test⟩:
⟨Anweisungsfolge⟩
[ elif ⟨test⟩:
⟨Anweisungsfolge⟩]*
[else :
⟨Anweisungsfolge⟩]
Die if-Anweisung w¨ahlt eine aus mehreren Anweisungs-
folgen aus. Ausgew¨ahlt wird diejenige Anweisungsfolge,
die zum ersten ⟨test⟩mit wahrem Ergebnis geh¨ort.
Beispiel:

## Seite 286

A.3 Grundlegende Konzepte 271
if a < b:
x = [a,b]
elif a > b:
x = [b,a]
else:
x = a
Dieses Beispiel implementiert eine Fallunterscheidung:
Je nachdem, ob a < b, ob a > b oder ob keiner der bei-
den F ¨alle gilt, wird der Variablen x ein anderer Wert
zugewiesen.
Die while-Schleife:
while ⟨test⟩:
⟨Anweisungsfolge⟩
[else :
⟨Anweisungsfolge⟩]
Die while-Anweisung stellt die allgemeinste Schlei-
fe dar. Die erste ⟨Anweisungsfolge⟩ wird solan-
ge ausgef ¨uhrt, wie ⟨test⟩ wahr ergibt. Die zweite
⟨Anweisungsfolge⟩wird ausgef ¨uhrt, sobald die Schleife
normal (d. h. ohne Verwendung der break-Anweisung)
verlassen wird.
Beispiel:
z = 42 ;geraten = False
while notgeraten:
r=int(raw input('Zahl?'))
if r < z:
print 'Hoeher!'
elif r > z:
print 'Niedriger!'
else: geraten = True
Diese while-Schleife implementiert ein einfaches Rate-
spiel. Mittels der Funktion raw input wird von Standar-
deingabe ein String eingelesen und in mittels der Funkti-
on int in eine Zahl konvertiert. Ist der eingelesene Wert
ungleich z, so wird eine entsprechende Meldung ausgege-
ben. Hat der Benutzer richtig geraten, wird die Variable
geraten auf den Wert ”True“ gesetzt. Daraufhin bricht
die while-Schleife ab, da ihre Bedingung ”not geraten“
nicht mehr gilt.
Die for-Schleife:
for ⟨ziel⟩in ⟨sequenz⟩:
⟨Anweisungsfolge⟩
[else :
⟨Anweisungsfolge⟩]
Die for-Schleife ist eine Schleife ¨uber Sequenzen (al-
so Listen, Tupel, . . . ). Die Variable ⟨ziel⟩nimmt hier-
bei f¨ur jeden Schleifendurchlauf einen Wert der Sequenz
⟨sequenz⟩an.
Beispiel:
s=0
for c in '12345':
s + =int(c)
Die for-Schleife durchl¨auft den String '12345' zeichen-
weise; es wird also f ¨unftmal die Zuweisung s +=int(c)
ausgef¨uhrt, wobei die Variable c immer jeweils eines der
Zeichen in '12345' enth¨alt. Die Variable s enth¨alt also
nach Ausf¨uhrung der Schleife den Wert ∑5
i=1 i= 15.
for i in range(10,20):
print 'i ist jetzt',i
Die Funktion range erzeugt eine Liste der Zahlen von 10
bis ausschließlich 20. Dieses Programm gibt die Zahlen
10 bis (ausschließlich) 20 in der folgenden Form aus:
i ist jetzt 10
i ist jetzt 11
...
i ist jetzt 19

## Seite 287

272 A Python Grundlagen
Im letzten Programmbeispiel wird die Pythonfunktion range verwendet. Diese gibt ei-
ne Liste ganzer Zahlen im angegebenen Bereich zur ¨uck; range(a,b) liefert alle ganzen
Zahlen zwischen (einschließlich) a und (ausschließlich) b zur¨uck. Es gilt also:
range(a,b) == [ a,a +1,..., b -2, b -1]
Optional kann man auch als drittes Argument eine Schrittweite angeben. Beispielsweise
liefert range(1,9,2) als Ergebnis die Liste [ 1,3,5,7 ] zur ¨uck. Es gilt also
range(a,b,c) == [ a,a +c,a +2c, ..., b -2c, b -c]
¨ubergibt man range nur ein einziges Argument, so beginnt die Ergebnisliste bei 0. Es
gilt also
range(a) == [0,1, ... , a -2, a -1]
Aufgabe A.2
(a) Erweitern Sie das als Beispiel einer while-Schleife dienende Ratespiel so, dass
eine Ausgabe erfolgt, die informiert, wie oft geraten wurde (etwa ”Sie haben 6
Rate-Versuche gebraucht.“).
(b) Erweitern Sie das Programm so, dass das Ratespiel vier mal mit vier unter-
schiedlichen Zahlen abl¨auft; am Ende sollen Sie ¨uber den besten Rate-Lauf und
den schlechtesten Rate-Lauf informiert werden, etwa so:
Ihr schlechtester Lauf: 8 Versuche; ihr bester Lauf: 3 Versuche.
Aufgabe A.3
(a) Schreiben Sie ein Pythonskript, das die Summe aller Quadratzahlen zwischen 1
und 100 ausgibt.
(b) Schreiben Sie ein Pythonskript, das eine Zahl n von der Tastatur einliest und
den Wert ∑n
i=0 i3 zur¨uckliefert.
(c) Schreiben Sie ein Pythonskript, das zwei Zahlen n und m von der Tastatur
einliest und den Wert ∑m
i=ni3 zur¨uckliefert.Aufgabe A.4
Schreiben Sie ein Pythonskript, das Ihnen die vier kleinsten perfekten Zahlen ausgibt.
Eine nat¨urliche Zahl heißt perfekt, wenn sie genauso groß ist, wie die Summe Ihrer
positiven echten Teiler (d. h Teiler außer sich selbst). Beispielsweise ist 6 eine perfekte
Zahl, da es Summe seiner Teiler ist, also 6 = 1 + 2 + 3.
A.3.2 Schleifenabbruch
Die beiden im Folgenden vorgestellten Kommandos, break und continue geben dem
Programmierer mehr Flexibilit¨at im Umgang mit Schleifen; man sollte diese aber spar-

## Seite 288

A.3 Grundlegende Konzepte 273
sam verwenden, denn sie k ¨onnen Programme schwerer verst ¨andlich und damit auch
schwerer wartbar1 werden lassen.
Mit der break-Anweisung kann man vorzeitig aus einer Schleife aussteigen; auch ein
m¨oglicherweise vorhandener else-Zweig wird dabei nicht mehr gegangen. Folgendes Bei-
spiel liest vom Benutzer solange Zahlen ein, bis eine ”0“ eingegeben wurde.
while True:
i = int(raw input('Bitte eine Zahl eingeben: '))
if i == 0: break
print 'Fertig'
Mit der continue-Anweisung kann man die restlichen Anweisungen im aktuellen Schlei-
fendurchlauf ¨uberspringen und sofort zum Schleifen”kopf“ springen, d. h. zum zur Pr¨ufan-
weisung einer while-Schleife bzw. zum Kopf einer for-Schleife, der der Schleifenvaria-
blen das n¨achste Element der Sequenz zuordnet.
A.3.3 Anweisungen vs. Ausdr ¨ucke
Gerade f¨ur den Programmieranf ¨anger ist es wichtig, sich des Unterschieds bewusst zu
sein zwischen . . .
 . . . einerAnweisung, die etwas”tut“, d. h. eigentlich einen Rechner- oder Programm-
internen Zustand ver ¨andert, wie etwa das Ausf ¨uhren einer Variablenzuweisung,
das Ver¨andern des Speicherinhalts, das Ausf ¨uhren einer Bildschirmausgabe) und
 . . . einemAusdruck, der einen bestimmten Wert repr ¨asentiert.
Beispiele. Der Python-Code x=5 +3 stellt eine Anweisung dar, n ¨amlich die, der Va-
riablen x einen Wert zuzuweisen. Die rechte Seite dieser Zuweisung, n ¨amlich 5 +3, ist
dagegen ein Ausdruck, der f¨ur den Wert 8 steht. Man beachte in diesem Zusammenhang
den Unterschied zwischen”=“, das immer Teil einer Zuweisung (also: eines Kommandos)
ist und ”==“, das einen Vergleich darstellt (also einen Wahrheitswert zur¨uckliefert) und
folglich immer Teil eines Ausdrucks ist: Der Python-Code 5==3 ist also ein Ausdruck,
der f¨ur den Wert False steht.
Aufgabe A.5
Viele Anweisungen enthalten Ausdr¨ucke als Komponenten. Gibt es auch Ausdr ¨ucke,
die Anweisungen als Komponenten enthalten?
In der interaktiven Pythonshell kann der Programmierer sowohl Anweisungen als auch
Ausdr¨ucke eingeben. Die Pythonshell geht aber jeweils unterschiedlich mit diesen um:
Wird ein Kommando eingegeben, so f ¨uhrt die Pythonshell das Kommando aus. Wird
dagegen ein Ausdruck eingegeben, so wird der Ausdruck zun ¨achst (falls n ¨otig) ausge-
wertet und anschließend die String-Repr ¨asentation des Ausdrucks ausgegeben.
1Spricht man in der Softwaretechnik von Wartbarkeit, so an meint man damit i. A. die Einfachheit
ein Programm im nachhinein anzupassen oder zu erweitern. Je ¨ubersichtlicher und besser strukturiert
ein Programm bzw. Softwaresystem ist, desto besser wartbar ist es.

## Seite 289

274 A Python Grundlagen
if-Ausdr¨ucke. Neben der in Abschnitt A.3.1 vorgestellten if-Anweisung bietet Py-
thon auch die M¨oglichkeit Ausdr¨ucke mit if zu strukturieren:
⟨expr1⟩if ⟨condition⟩else ⟨expr2⟩ Dieser Ausdruck steht f ¨ur den Wert des
Ausdrucks ⟨expr1⟩falls ⟨condition⟩wahr ist,
andernfalls steht dieser if-Ausdruck f¨ur den
Wert des Ausdrucks ⟨expr2⟩
Beispiele:
>>>x=3 ; y=4
>>>'a' if x +1==y else 'b'
a
Da x +1==y wahr ist, steht der if-Ausdruck
in der zweiten Zeile f ¨ur den Wert 'a'.
>>>x=3 ; y=4
>>>'Hallo Welt' [7 if x==y else 4]
o
Der als String-Index verwendete if-
Ausdruck steht – da x̸=y – f¨ur den Wert 4;
der gesamte Ausdruck ergibt also als Wert
das (von Null an gez ¨ahlte) vierte Zeichen
des Strings 'Hallo Welt', also 'o'.
Aufgabe A.6
Welchen Wert haben die folgenden Python-Ausdr¨ucke:
(a) 'Hallo' [4 if (4 if 4==2 else 3)==3 else 5]
(b) 'Hallo' +'welt'if str(2 -1)==str(1) else 'Welt'
(c) [0 if i%3==0 else 1 for i in range(1,15)]
A.3.4 Funktionen
Komplexere Programme sollte man in kleinere Programmeinheiten aufteilen und die-
se dann zusammenf ¨ugen. Die g ¨angigste M¨oglichkeit, ein Programm in einfachere Teile
aufzuteilen, sind Funktionen; jede Funktion l¨ost eine einfache Teilaufgabe und am Ende
werden die Funktionen dann entsprechend kombiniert (beispielsweise durch Hinterein-
anderausf¨uhrung).
Funktionsdeﬁnitionen. In Python leitet man eine Funktionsdeﬁnition mit dem Schl¨ussel-
wort def ein:

## Seite 290

A.3 Grundlegende Konzepte 275
def ⟨bez⟩(⟨p1 ⟩, ⟨p2 ⟩, . . .):
⟨kommando1 ⟩
⟨kommando2 ⟩
. . .
[return ⟨ausdruck⟩]
Deﬁniert eine Funktion mit Namen ⟨bez⟩, die
mit den Paramtern ⟨p1 ⟩, ⟨p2 ⟩, . . . aufgerufen
wird. Ein Funktionsaufruf f ¨uhrt dann die
im Funktions”k¨orper“ stehenden Kommandos
⟨kommando1 ⟩, ⟨kommando2 ⟩, . . . aus. Mit dem
return-Kommando wird die Funktion verlas-
sen und der auf return folgende Ausdruck als
Wert der Funktion zur¨uckgeliefert. Enth¨alt der
Funktionsk¨orper kein return-Kommando, so
liefert die Funktion den Wert ”None“ zur ¨uck.
Beispiele:
def getMax(a,b):
if a > b: return a
else: return b
>>>getMax('hallo','welt')
'welt'
Die Funktion getMax erwartet zwei Parameter
a und b und liefert mittels return den gr¨oße-
ren der beiden Werte zur ¨uck. Die letzten bei-
den Zeilen zeigen eine Anwendung der Funktion
getMax in Pythons interaktiver Shell.
Es gibt eine weitere M¨oglichkeit der Parameter¨ubergabe ¨uber sog. benannte Parameter .
Die ¨Ubergabe eines benannten Parameters erfolgt nicht (wie bei Standard-Parametern)
¨uber eine festgelegte Position in der Parameterliste, sondern ¨uber einen Namen. Bei
der Funktionsdeﬁnition muss immer ein default-Wert f ¨ur einen benannten Parameter
speziﬁziert werden. Die im Folgenden deﬁnierte Funktionincr erwartet einen Parameter
x und optional einen benannten Parameterincrement, der – falls nicht explizit speziﬁzert
– den Wert ”1“ besitzt.
>>>def incr(x,increment=1):
... return x +increment
...
>>>incr(4)
5
>>>incr(4,increment=10)
14
¨Ubrigens m¨ussen benannte Parameter immer rechts der Standardparameter aufgef ¨uhrt
sein; ein Aufruf incr(increment=-2,4) w¨are also syntaktisch nicht korrekt.
Lokale Variablen. Alle in einer Funktion verwendeten Variablen sind lokal, d. h au-
ßerhalb der Funktion weder sichtbar noch verwendbar und nur innerhalb der Funktion
g¨ultig. Weist man einer bestimmten Variablen, die es im Hauptprogramm bzw. auf-
rufenden Programm schon gibt, einen Wert zu, so wird die Hauptprogramm-Variable
dadurch weder gel¨oscht noch ver¨andert; in der Funktion arbeitet man auf einer Kopie,
die von der Variablen des Hauptprogramms entkoppelt ist. L¨asst man beispielsweise den
Code auf der linken Seite durch Python ausf ¨uhren, so ergibt sich die auf der rechten

## Seite 291

276 A Python Grundlagen
Seite gezeigte Ausgabe:
>>> print 'f: x ist',x
>>> x=2
>>>
print 'f: lokales x ist',x
>>>
>>>x=50
>>> f(x)
>>>print 'x ist noch', x
erzeugt
=⇒
f: x ist 50
f: lokales x ist 2
x ist noch 50
Solange x kein neuer Wert zugewiesen wurde, wird das x aus dem Hauptprogramm ver-
wendet; erst nach der Zuweisung wird ein ”neues“ lokales x in der Funktion verwendet,
die vom x des Hauptprogramms abgekoppelt ist; außerdem wird sichergestellt, dass das
x des Hauptprogramms nicht ¨uberschrieben wird und nach dem Funktionsaufruf wieder
verf¨ugbar ist.
A.3.5 Referenzen
Eine Zuweisung wie
x = y
bewirkt im Allgemeinen nicht, dass eine neue Kopie eines Objektes y angelegt wird,
sondern nur, dass x auf den Teil des Hauptspeichers zeigt, an dem sich y beﬁndet.
Normalerweise braucht sich der Programmierer dar¨uber keine Gedanken zu machen; ist
man sich dieser Tatsache jedoch nicht bewusst, kann es zu ¨Uberraschungen kommen.
Ein einfaches Beispiel:
>>>a = [1,2,3 ]
>>>b = a
>>>a.append(5)
>>>b
[ 1,2,3,5 ]
Dass a und b tats¨achlich auf den gleichen Speicherbereich zeigen, zeigt sich durch Ver-
wendung der Funktion id: id(x) liefert die Hauptspeicheradresse des Objektes x zur¨uck.
F¨ur obiges Beispiel gilt:
>>> id(a) == id(b)
True
Will man, dass b eine tats¨achliche Kopie der Liste a enth¨alt und nicht nur, wie oben,
einen weiteren Zeiger auf die gleiche Liste, dann kann man dies folgendermaßen ange-
ben:
>>>b = a[:]
Dabei ist in obigem Fall a[ :] genau dasselbe wie a[0 :2] und bewirkt eine Kopie der
Liste.

## Seite 292

A.4 Zusammengesetzte Datentypen 277
Aufgabe A.7
Was ist der Wert der Variablen a, b und c nach der Eingabe der folgenden Komman-
dos in den Python-Interpreter:
>>>a = ['a','ab','abc' ]
>>>b = a
>>>b.append('abcd')
>>>c = b[: ]
>>>c [0] = '0'
A.4 Zusammengesetzte Datentypen
Python besitzt mehrere zusammengesetzte Datentypen, darunter Strings ( str), Listen
( list ), Tupel ( tuple), Mengen ( set) und sog. Dictionaries (dict), das sind Mengen
von Schl¨ussel-Wert-Paaren, die einen schnellen Zugriﬀ auf die Werte ¨uber die entspre-
chenden Schl¨ussel erlauben. Strings, Listen, Tupel, Mengen und sogar Dictionaries sind
iterierbar, d. h. man kann sie etwa mittels for-Schleifen durchlaufen.
Mittels der Funktionen list (s), tuple(s) und set(s) kann eine beliebige Sequenz s in
eine Sequenz vom Typ ”Liste“, ”Tupel“ bzw. ”Set“ ¨uberf¨uhrt werden. Im Folgenden
einige Beispiele:
>>> list ((1,2,3))
[1, 2, 3]
>>> tuple(range(10,15))
(10, 11, 12, 13, 14)
>>> set(range(5))
set( [0, 1, 2, 3, 4])
A.4.1 Listen
Python-Listen sind Sequenzen von durch Kommata getrennten Werten, eingeschlossen
in eckigen Klammern. Listen k¨onnen Werte verschiedener Typen enthalten, unter Ande-
rem k¨onnen Listen wiederum Listen enthalten; Listen k¨onnen also beliebig geschachtelt
werden. Folgende Python-Werte sind beispielsweise Listen:
[ ] (die leere Liste), [ 5,3,10,23 ], [ 'spam', [1,2,3 ], 3.14, [ [1], [ [2] ] ] ]
Listenmethoden. Folgende Auﬂistung zeigt eine Auswahl der wichtigsten Methoden
zur Manipulation von Listen. Alle hier gezeigten Methoden – (mit Ausnahme von
count()) – manipulieren eine Liste destruktiv und erzeugen keinen R ¨uckgabewert.
l .append(x) F¨ugt x am Ende der Liste l ein. Man beachte, dass append
ein reines Kommando darstellt, keinen R ¨uckgabewert liefert,
sondern lediglich die Liste l ver¨andert.
Beispiel:

## Seite 293

278 A Python Grundlagen
l = range(3)
l .append('last')
Die Liste l hat nach Ausf ¨uhrung dieser beiden Kommandos
den Wert [ 0,1,2, 'last' ]
l . sort() Sortiert ⟨liste⟩aufsteigend. Auch sort ist ein reines Kom-
mando, liefert also keinen R ¨uckgabewert sondern ver ¨andert
lediglich die Liste l.
Beispiel:
l = [4,10,3,14,22 ]
l . sort()
Die Liste l hat nach Ausf ¨uhrung dieser beiden Kommandos
den Wert [3, 4, 10, 14, 22].
l . reverse() Dreht die Reihenfolge der Listenelemente um. Auch reverse
ist ein reines Kommando und liefert keinen R ¨uckgabewert.
Beispiel:
l = list ('hallo')
l . reverse()
Die Liste l hat nach Ausf ¨uhrung dieser beiden Kommandos
den Wert [ 'o', 'l', 'l', 'a', 'h' ]
l . insert (i ,x) F¨ugt ein neues Element x an Stelle i in der Liste l ein. Die
Zuweisung l [i :i ] = [ x] h¨atte ¨ubrigens genau den selben Ef-
fekt.
Beispiel:
l = range(6)
l . insert (2,'neu')
Die Liste l hat nach Ausf ¨uhrung dieser beiden Kommandos
den Wert [0, 1, 'neu', 2, 3, 4, 5]
l .count(x) Gibt die Anzahl der Vorkommen von x in ⟨l⟩zur¨uck.
l .remove() L¨oscht das erste Auftreten von x in der Liste l.
Beispiel:
l = range(3)+ \
range(3)[ :: -1]
l .remove(1)
Die Liste l hat nach Ausf ¨uhrung dieser beiden Kommandos
den Wert [0, 2, 2, 1, 0].
Man kann sich alle Methoden des Datentyps list mit Hilfe der Pythonfunktion dir
ausgeben lassen. Der Aufruf
>>> dir( list )
[ ... , 'append', 'count', 'extend', 'index', 'insert', 'pop', 'remove', ...]

## Seite 294

A.4 Zusammengesetzte Datentypen 279
liefert eine Stringliste aller Methodennamen zur¨uck, die f¨ur den Datentyp list deﬁniert
sind.
Aufgabe A.8
Geben Sie in der Python-Shell den Ausdruck
[1,2,3 ]. remove(1)
ein. Was wird zur¨uckgeliefert? Erkl¨aren Sie das Ergebnis!
Aufgabe A.9
Geben Sie ein m ¨oglichst kurzes Pythonkommando / Pythonskript an, das . . .
(a) . . . die Anzahl der f ¨ur den Datentyp dict deﬁnierten Operationen ausgibt.
(b) . . . die Anzahl der f ¨ur den Datentyp list deﬁnierten Operationen ausgibt, die
mit 'c' beginnen.
(c) . . . die L¨ange des l¨angsten Operationsnamens der auf dem Datentyp list deﬁnier-
ten Operationen ausgibt. Hinweis: f ¨ur diese Aufgabe w ¨are die Pythonfunktion
map gut geeignet, die wir zwar noch nicht behandelt haben, ¨uber die Sie sich
aber mittels help(map) informieren k¨onnen.
A.4.2 Sequenzen
Listen, Tupel und Strings sind sog. Sequenz-Typen, d. h. die enthaltenen Werte besitzen
eine feste Anordnung. Dies ist sowohl beim set-Typ als auch bei Dictionaries nicht
der Fall: In welcher Reihenfolge sich die Elemente einer Menge beﬁnden wird nicht
gespeichert; ebenso ist die Anordnung der in einem Dictionary enthaltenen Schl ¨ussel-
Wert-Paare nicht relevant.
Slicing. Sei S eine Variable, die ein Sequenz-Objekt enth ¨alt – also etwa einen String,
eine Liste oder ein Tupel. Dann sind die folgenden Zugriﬀsoperationen aufS anwendbar.
S[i ]
Indizierung
Selektiert Eintr¨age an einer bestimmten Position. Negative
Indizes z¨ahlen dabei vom Ende her.
Beispiele:
S[0] liefert das erste Element der Sequenz S
S[ -2] liefert das zweitletzte Element der Sequenz S
['ab','xy' ][ -1][0] liefert 'x' zur¨uck.

## Seite 295

280 A Python Grundlagen
Slicing (Teilbereichsbildung)
S[i :j ] Selektiert einen zusammenh ¨angenden Bereich einer Se-
quenz; die Selektion erfolgt von einschließlich Index i bis
ausschließlich Index j.
S[ :j ] die Selektion erfolgt vom ersten Element der Sequenz bis
ausschließlich Index j
S[i :] die Selektion erfolgt vom einschließlich Index i bis zum
letzten Element der Sequenz.
Beispiele:
S[1 :5] selektiert den zusammenh¨angenden Bereich aller Elemente
ab einschließlich Index 1 bis ausschließlich Index 5
S[3 :] selektiert alle Elemente von S ab Index 3
S[ :-1] selektiert alle Elemente von S, bis auf das letzte
S[ :] selektiert alles, vom ersten bis zum letzten Element
S[i :j :k]
Extended Slicing
Durch k kann eine Schrittweite vorgegeben werden.
Beispiele:
S[ : :2] selektiert jedes zweite Element
S[ : :-1] selektiert alle Elemente von S in umgekehrter Reihenfolge
S[4 :1 :-1] selektiert die Elemente von rechts nach links ab Position 4
bis ausschließlich 1.
'Welt' [ : :-1] ergibt 'tleW'
'hallo welt' [ -2 : :-2] ergibt 'lwolh'
range(51)[ : :-10] ergibt [50, 40, 30, 20, 10, 0]
Handelt es sich bei der Sequenz um eine Liste, so kann – da Listen ja ver ¨anderliche
Objekte sind – auch eine Zuweisung ¨uber Slicing erfolgen. Es folgen zwei Beispiele, wie
Teile von Listen mittels Zuweisungen ver¨andert werden k¨onnen.
>>> l = range(7)
>>> l [2:5 ] = [ 'x' ] *3
>>> l
[0, 1, 'x', 'x', 'x', 5, 6]
>>> l = ['x' ] *6
>>> l [ ::2 ]=[0] *3
>>> l
[0, 'x', 0, 'x', 0, 'x' ]
>>> l = range(7)
>>> l [ -3:: -1]=range(5)
>>> l
[4, 3, 2, 1, 0, 5, 6]
Funktionen auf Sequenzen. Folgende Funktionen sind auf alle Sequenzen anwend-
bar; die meisten der hier aufgef ¨uhrten Funktionen liefern R¨uckgabewerte zur¨uck.

## Seite 296

A.4 Zusammengesetzte Datentypen 281
len(S) Liefert die L¨ange der Sequenz S zur¨uck.
Beispiele:
len('hallo') Liefert die L¨ange des String zur ¨uck, n¨amlich 5.
len( [1, [2,3 ] ]) Liefert die L¨ange der Liste zur ¨uck, n¨amlich 2.
min(S) Liefert das minimale Element der Sequenz S zur¨uck.
max(S) Liefert das maximale Element der Sequenz S zur¨uck.
Beispiele:
max('hallo') Liefert die maximale Element des Strings, n ¨amlich 'o'
zur¨uck.
max([101,123,99]) Liefert die Zahl 123 zur ¨uck.
sum(S) Liefert die Summe der Elemente der Sequenz S zur¨uck.
Beispiele:
sum(range((100)) Berechnet ∑99
i=0 und liefert entsprechend 4950 zur ¨uck.
del S[i ] L¨oscht einen Eintrag einer Sequenz.
del S[i :j :k] del kann auch mit Slicing und Extended Slicing verwendet
werden.
del kann man nur auf ver¨anderliche Sequenzen anwenden.
Beispiele:
l = range(10)
del l [ ::2 ] L¨oscht jedes zweite Element der Liste; l hat also
nach Ausf ¨uhrung der beiden Kommandos den Wert
[1, 3, 5, 7, 9].

## Seite 297

282 A Python Grundlagen
Aufgabe A.10
Bestimmen Sie den Wert der folgenden Ausdr ¨ucke:
(a) range(1,100) [1],range(1,100) [2]
(b) [ range(1,10), range(10,20) ] [1] [2]
(c) [ 'Hello',2,'World' ][0][2] +['Hello',2,'World' ][0]
(d) len(range(1,100))
(e) len(range(100,200)[0 :50 :2])
Hinweis: Versuchen Sie zum ¨achst die L ¨osung ohne die Hilfe des Pythoninterpreters
zu bestimmen.
Aufgabe A.11
Wie k¨onnen Sie in folgendem Ausdruck (der eine verschachtelte Liste darstellt)
[ [x ], [ [ [y] ] ] ]
auf den Wert von y zugreifen?
Aufgabe A.12
L¨osen sie die folgenden Aufgaben durch einen Python-Einzeiler:
(a) Erzeugen Sie die Liste aller geraden Zahlen zwischen 1 und 20.
(b) Erzeugen Sie die Liste aller durch 5 teilbarer Zahlen zwischen 0 und 100.
(c) Erzeugen Sie die Liste aller durch 7 teilbarer Zahlen zwischen 0 und 100; die
Liste soll dabei umgekehrt sortiert sein, d. h. die gr ¨oßten Elemente sollen am
Listenanfang und die kleinsten Elemente am Listenende stehen.
A.4.3 Tupel
Tupel sind Listen ¨ahnlich, jedoch sind Tupel – wie auch Strings – unver ¨anderlich. Tu-
pel werden in normalen runden Klammern notiert. Tupel k ¨onnen genauso wie andere
Sequenzen auch indiziert werden. Es folgen einige Beispiele:
>>>x = ('Das', 'ist', 'ein', 'Tupel')
>>>x [1]
'ist'
>>>x [2] [0]
'e'
>>>x [0] = 'Hier'
Traceback (most recent call last):

## Seite 298

A.4 Zusammengesetzte Datentypen 283
File "<stdin>", line 1, in <module>
TypeError: 'tuple' object does not support item assignment
Die letzte Zuweisung ist aufgrund der Unver ¨anderlichkeit von Tupeln verboten. Will
man in der Variablenx ein Tupelobjekt speichern, dessen erste Position den Wert'Hier'
enth¨alt und das ansonsten mit dem ”alten“ x identisch ist, so muss man wie folgt
vorgehen:
>>>x = ('Hier',) +x[1:]
>>>x
('Hier', 'ist', 'ein', 'Tupel')
Man beachte: Durch die Zuweisung in der ersten Zeile wurde kein Tupel-Objekt ver¨andert,
sondern ein neues Tupel-Objekt erzeugt, durch Konkatenation des ein-elementigen Tu-
pels ( 'Hier',) mit dem drei-elementigen Tupel x [1 :].
A.4.4 Dictionaries
Ein Dictionary-Objekt stellt eine eﬃziente Repr¨asentation einer Zuordnung von Schl¨us-
seln auf Werte dar. Ein Anwendungsbeispiel ist ein Adressbuch, das bestimmte Namen
(die Schl¨ussel) auf Adressen (die Werte) abbildet. Ein Dictionary-Objekt sollte die fol-
genden drei Operationen eﬃzient unterst ¨utzen: 1. Das Einf¨ugen eines neuen Wertes v
mit dem Schl¨ussel k. 2. Das Finden eines bestimmten Wertes v anhand seines Schl¨ussels
k. 3. Das L¨oschen eines Schl¨ussels k zusammen mit dem zugeh ¨origen Wert v.
Aufgrund der Tatsache, dass der Informatiker eine eﬃziente Unterst ¨utzung der Dictio-
nary-Operationen h¨auﬁg ben¨otigt, bietet Python einen eigenen internen Typ dict an,
der diese Operationen eﬃzient unterst ¨utzt. W¨ahrend Listen in eckigen Klammern und
Tupel in runden Klammern notiert werden, werden Dictionaries in geschweiften Klam-
mern geschrieben:
{⟨schl ¨ussel1 ⟩ : ⟨wert1 ⟩, ⟨schl¨ussel2 ⟩ : ⟨wert2 ⟩, . . .}
Ein einfaches Beispiel:
>>>ab = {'Carlo' : 'carlo@web.de',
'Hannes' : 'hannes@gmail.de',
'Matilda' : 'matilda@gmx.de' }
Die Operationen ”Einf¨ugen“ und ”Suchen“ werden ¨uber den Indizierungsoperator [ ... ]
angesprochen, so dass sich die Verwendung eines Dictionary-Objektes z. T. ”anf¨uhlt“
wie ein Listen- oder Tupelobjekt. Beispiele:
>>>ab['Hannes' ]
'hannes@gmail.de'
>>>ab['Hannes' ]='hannes@gmx.de'
>>>ab['Hannes' ]
'hannes@gmx.de'

## Seite 299

284 A Python Grundlagen
Die L¨oschfunktion ist ¨uber die Funktion del implementiert.
>>>del ab['Matilda' ]
>>>print 'Es gibt',len(ab),'Eintraege in ab'
'Es gibt 2 Eintraege in ab'
Man kann also, genau wie bei anderen ver¨anderbaren Sequenzen, auf einzelne Elemente
zugreifen, l¨oschen und alle f ¨ur Sequenzen deﬁnierte Funktionen anwenden. Wichtig zu
wissen ist, dass man nur unver ¨anderliche Werte als Schl ¨ussel verwenden kann – also
insbesondere keine Listen!
Aufgabe A.13
Erkl¨aren Sie, was das Problem w ¨are, wenn man auch ver ¨anderliche Werte (wie bei-
spielsweise Listen) als Schl¨ussel in Dictionaries zulassen w ¨urde.
Die Schl¨ussel m¨ussen nicht alle den gleichen Typ haben:
>>>ab[ (1,2,3) ] = 123
>>>ab[1] = 100
>>>ab[ (1,2,3) ]-ab[1]
23
Methoden auf Dictionaries. Die folgenden Methoden auf Dictionaries werden von
einigen der vorgestellten Algorithmen verwendet:
d.values() Liefert eine Liste aller in d enthaltenen Werte zur¨uck.
d.keys() Liefert eine Liste aller in d enthaltenen Schl¨ussel zur¨uck.
d.items() Liefert alle in d enthaltenen Schl ¨ussel-Werte-Paare als Tupel-Liste
zur¨uck.
Als Beispiele nehmen wir an, ein Dictionary d sei folgendermaßen deﬁniert:
>>>d = {1:'hallo', 'welt':[1,2,3], ( 'x','y' ):10, '20':'30', 2:{1: [ ], 2: [2] }, 3: [ ] }
Dann gilt beispielsweise:
>>>d.keys()
>>> [1, 2, 3, '20',
('x', 'y' ), 'welt' ]
>>>d.values()
>>> ['hallo', {1: [ ], 2: [2] }, [ ],
'30', 10, [1, 2, 3] ]
>>>d[2]. keys()
[1, 2]

## Seite 300

A.4 Zusammengesetzte Datentypen 285
A.4.5 Strings (Fortsetzung)
H¨auﬁg gebraucht, sowohl f¨ur große Programmierprojekte als auch f ¨ur viele kleine n¨utz-
liche Skripts, sind Funktionen auf Strings.
Strings sind – ebenso wie Listen und Tupel – Sequenzen und entsprechend sind alle im
vorigen Abschnitt beschriebenen Sequenzoperationen anwendbar. Strings sind, eben-
so wie Tupel, unver ¨anderlich, d. h. ein einmal deﬁnierter String kann nicht ver ¨andert
werden. Man kann also weder einzelne Zeichen aus einem einmal erstellten String her-
ausl¨oschen, noch kann man an einen einmal deﬁnierten String Zeichen anf ¨ugen.
Es folgt eine Liste der wichtigsten String-Operationen:
Suchen
s. ﬁnd(s1) Liefert den Oﬀset des ersten Vorkommens von s1 in s zur¨uck.
s. replace(s1,s2) Liefert einen String zur ¨uck, in dem alle Vorkommen von s1
durch s2 ersetzt sind.
s. startswith (s1) Liefert True zur¨uck, falls s mit s1 beginnt.
s.endswith(s1) Liefert True zur¨uck, falls s mit s1 endet.
Als Beispiel nehmen wir an, ein String s sei folgendermaßen deﬁniert:
>>>s = 'Hallo Welt, dies, genau dies, ist ein Teststring'
>>>s. ﬁnd('s,')
15
>>>s. replace('dies','das')
'Hallo Welt, das, genau
das, ist ein Teststring'
>>>s. startswith ('Ha')
True
Aufteilen, Zusammenf¨ugen
s. split (s1) Gibt eine Liste von W¨ortern von s zur¨uck, mit s1 als Tren-
ner.
s. partition (sep) Sucht nach dem Trenner sep in s und liefert ein 3-Tupel
(head,sep, tail ) zur ¨uck, wobei head der Teil vor sep und
tail der Teil nach sep ist.
s. join(l) Verkettet die Stringliste l zu einem einzigen String mit s
als Trenner.

## Seite 301

286 A Python Grundlagen
Beispiele:
>>>'Hi hi you foo'.split ()
['Hi', 'hi', 'you', 'foo' ]
>>>'1. Zwei. 3.'.split ('.')
['1', ' Zwei', ' 3', '' ]
>>>','. join( [
... 'a','b','c' ])
'a,b,c'
Aufgabe A.14
Schreiben Sie eine Pythonfunktion zipString, die zwei Strings als Argumente ¨uber-
geben bekommt und einen String zur¨uckliefert, der eine ”verschr¨ankte“ Kombination
der beiden ¨ubergebenen Strings ist.
Beispielanwendungen:
>>> zipString('Hello','World')
'HWeolrllod'
>>> zipString('Bla','123')
'B1l2a3'
A.4.6 Mengen: Der set-Typ
Einige Algorithmen ben ¨otigen duplikatfreie Sammlungen von Werten. Hier bietet sich
Pythons set-Datentyp an. Etwa der in Abschnitt 6.4 beschriebene LR-Parsergenerator
verwendet set-Objekte zur Repr ¨asentaton und Berechnung von FIRST- und FOLLOW-
Mengen.
set-Objekte k¨onnen aus Sequenzen (wie Listen, Tupel oder Strings) mittels der Konstruktor-
Funktion set () erzeugt werden. Beispielsweise erzeugt folgende Anweisung
s = set(range(3))
eine Menge, die die Zahlen ”0“, ”1“ und ”2“ enth¨alt.
Es folgt eine Liste der wichtigsten Methoden auf Mengen:
Einf¨ugen, L¨oschen
s.add(x) F¨ugt ein Elementx in eine Menge s ein. Beﬁndet sich der Wert
x bereits in der Menge s, so bleibt s durch dieses Kommando
unver¨andert. Die Methode add ist ein reines Kommando und
liefert keinen R¨uckgabewert.
s.remove(x) L¨oscht ein Element x aus der Menge s. Das Element x muss in
der Menge s enthalten sein – anderfalls entsteht einKeyError.
Auch die Methode remove ist ein reines Kommando und lie-
fert keinen R¨uckgabewert.

## Seite 302

A.5 Funktionale Programmierung 287
Beispiele (wir gehen davon aus, die Menge s sei jeweils durch s=set(range(3)) deﬁniert):
>>>s.add(10)
>>>s
set( [0, 1, 2, 10])
>>>s.add(2)
>>>s
set( [0, 1, 2])
>>>s.remove(0)
>>>s
set( [1, 2])
>>>s.remove(6)
KeyError: 6
Vereinigung, Schnitt
s.union(s1) Liefert die Vereinigung ”s ∪s1“ zur ¨uck. Es wird also ein set-
Objekt zur¨uckgeliefert, das alle Elemente enth¨alt, die sich ent-
weder in s oder in s1 beﬁnden. Die union-Methode ist rein
funktional und l¨asst sowohl s als auch s1 unver¨andert.
s. intersection (s1) Liefert den Schnitt ”s ∩s1“ zur ¨uck. Es wird also ein set-
Objekt zur ¨uckgeliefert, das alle Elemente enth ¨alt, die sich
sowohl in s als auch in s1 beﬁnden. auch die intersection-
Methode ver¨andert die Parameter nicht.
s. diﬀerence(s1) Liefert die Mengendiﬀerenz ”s\s1“ zur ¨uck. Es wird also ein
set-Objekt zur ¨uckgeliefert, das alle Elemente aus s enth¨alt,
die nicht in s1 enthalten sind. Auch die diﬀerence-Methode
ver¨andert die Parameter nicht.
Wir geben einige Beispiele an und gehen dabei davon aus, dass die folgenden beiden
Deﬁnitionen
>>>s=set('hallo welt')
>>>s1=set('hello world')
voranstehen:
>>>s.union(s1)
set( ['a',' ','e','d','h',
'l','o','r','t','w' ])
>>>s. intersection (s1)
set( [' ','e','h','l','o','w' ])
>>>s. diﬀerence(s1)
set( ['a', 't' ])
A.5 Funktionale Programmierung
Das Paradigma der Funktionalen Programmierung unterscheidet sich vom Paradig-
ma der imperativen Programmierung vor allem dadurch, dass imperativen Programme
¨uberwiegend Anweisungen verwenden. Eine Anweisung ”tut“ etwas, d. h. die ver¨andert
den Zustand des Programms bzw. des Speichers bzw. den Zustand von Peripherieger¨aten
(wie etwa des Bildschirms). Auch for- oder while-Schleifen sind typische Anweisungen:
In jedem Schleifendurchlauf ver¨andert sich i. A. der Zustand der Schleifenvariablen.
Funktionale Programme verwenden nur oder ¨uberwiegend Ausdr ¨ucke, die strengge-
nommen nichts ”tun“, sondern lediglich f ¨ur einen bestimmten Wert stehen und kei-

## Seite 303

288 A Python Grundlagen
ne Zust¨ande ver¨andern. Viele Programmierfehler entstehen, da der Programmierer den
¨Uberblick ¨uber die durch das Programm erzeugten Zust ¨ande verloren hat. Program-
miert man mehr mit Ausdr ¨ucken, so schließt man zumindest diese Fehlerquelle aus.
Beispielsweise lohnt es sich immer in Erw ¨agung zu ziehen, eine ”imperative“ Schleife
durch eine Listenkomprehension, eine map-Anweisung oder eine ﬁlter -Anweisung zu
ersetzen.
A.5.1 Listenkomprehensionen
Listenkomprehensionen sind Ausdr ¨ucke, keine Kommandos – sie stehen also f ¨ur einen
bestimmten Wert. Man kann Listenkomprehensionen als das funktionale Pendant zur
imperativen Schleife betrachten. Sie sind insbesondere f ¨ur Mathematiker interessant
und leicht verst ¨andlich aufgrund ihrer an die mathematische Mengenkomprehension
angelehnte Notation. Die Menge
{2 ·x |x∈{1,... 20}, xdurch 3 teilbar }
entspricht hierbei der Python-Liste(nkomprehension)
[ 2 *x for x in range(1,21) if x%3==0 ]
Jede Listenkomprehension besteht mindestens aus einem in eckigen Klammern [ ... ]
eingeschlossenen Ausdruck, gefolgt von einer oder mehreren sogenannten for-Klauseln.
Jede for-Klausel kann optional durch eine if-Klausel eingeschr¨ankt werden.
[⟨ausdr⟩for ⟨ausdr1 ⟩in ⟨sequenz1⟩[if ⟨bedingung1⟩]
for ⟨ausdr1 ⟩in ⟨sequenz2⟩[if ⟨bedingung2⟩] . . . ]
Der Bedingungsausdruck dieser if-Klauseln h ¨angt i. A. ab von einer (oder mehrerer)
durch vorangegangene for-Klauseln gebundenen Variablen. Dieser Bedingungsausdruck
”ﬁltert“ all diejenigen Ausdr ¨ucke der jeweiligen Sequenz aus f ¨ur die er den Wahrheits-
wert ”False“ liefert.
:Wert der Listen-komprehension
...,⟨sequenz1⟩: ]
][ ...,
fallsfalls
⟨bedingung1⟩? ⟨bedingung1⟩?
falls
⟨bedingung1⟩?
x1 , xn[ x0 ,
⟨ausdr⟩(xn)⟨ausdr⟩(x1),⟨ausdr⟩(x0),
Abb. A.1: Funktionsweise einer Listenkomprehension mit einer for-Schleife und einer if-
Bedingung. Die Ausdr¨ucke ⟨sequenz1⟩,⟨bedingung1⟩und ⟨ausdr⟩beziehen sich hier auf die ent-
sprechenden Platzhalter, die in obiger Syntaxbeschreibung verwendet wurden. Wie man sieht,
ist der Wert der Listenkomprehension immer eine Liste, deren Elemente durch Anwendung
von ⟨ausdr⟩auf die einzelnen Elemente der Liste ⟨sequenz1⟩entstehen.
Beispiele
Wir gehen in vielen der pr ¨asentierten Beispiel darauf ein, welchen Wert die einzel-
nen Platzhalter der obigen Syntaxbeschreibung haben, d. h. wir geben oft der Klar-
heit halber an, was der jeweilige ”Wert“ der Platzhalter ⟨ausdr⟩, ⟨ausdr1 ⟩, ⟨sequenz1⟩,
⟨bedingung1⟩, usw. ist.

## Seite 304

A.5 Funktionale Programmierung 289
i) Die Liste aller Quadratzahlen von 1 2 bis 52:
>>> [x *x for x in range(1,6) ]
[1, 4, 9, 16, 25]
⟨ausdr⟩entspricht hier dem Ausdruck x*x; ⟨sequenz1⟩entspricht range(1,6). F¨ur jeden
Wert in range(1,6), also f¨ur jeden Wert in [ 1,2,3,4,5 ], wird ein Listeneintrag der Ergeb-
nisliste durch Auswertung des Ausdrucks x*x erzeugt. Ergebnis ist also [1*1, 2*2, ... ].
Die folgende Abbildung veranschaulicht dies nochmals:
2 , 3 , 4 , 5 ][ 1 ,
1*1
1 , 4 , 9 ,
3*3
16 ,
4*4
25[ ]
⟨sequenz1⟩:
:
2*2 5*5⟨ausdr⟩:
Wert der Listen-komprehension
ii) Die Liste aller durch 3 oder durch 7 teilbarer Zahlen zwischen 1 und 20:
>>> [x for x in range(1,20)
... if x%3==0 or x%7==0 ]
[3, 6, 7, 9, 12, 14, 15, 18]
⟨ausdr⟩entspricht hier dem nur aus einer Variablen bestehenden Ausdruckx; ⟨sequenz1⟩
entspricht range(1,20); ⟨bedingung1⟩entspricht x%3==0 or x%7==0. Hier wird also eine
Liste erzeugt die aus allen x in range(1,20) besteht f¨ur die die if-Bedingung True ergibt.
Aufgabe A.15
(a) Schreiben Sie eine Pythonfunktion teiler (n), die die Liste aller Teiler einer als
Parameter ¨ubergebenen Zahl n zur¨uckliefert. Tipp: Am leichtesten mit Verwen-
dung einer Listenkomprehension. Beispielanwendung:
>>> teiler (45)
>>> [1, 3, 5, 9, 15]
(b) Geben Sie – mit Verwendung der eben geschriebenen Funktion teiler – einen
Python-Ausdruck (kein Kommando!) an, der eine Liste aller Zahlen zwischen 1
und 1000 ermittelt, die genau 5 Teiler besitzen.
(c) Geben Sie – mit Verwendung der eben geschriebenen Funktion teiler – einen
Python-Ausdruck an, der die Zahl zwischen 1 und 1000 ermittelt, die die meisten
Teiler besitzt.

## Seite 305

290 A Python Grundlagen
iii) Die Liste aller m ¨oglichen Tupel von Zahlen aus 1 bis 10.
>>> [ ( x,y) for x in range(1,10)
... for y in range(1,10) ]
[(1, 1), (1, 2), ... ,(1,9), (2,1), (2,2), ...
(9, 9) ]
Der Platzhalter ⟨ausdr⟩entspricht in diesem Fall dem Tupel ( x,y), der Platzhalter
⟨sequenz1⟩entspricht range(1,10) und der Platzhalter⟨sequenz2⟩entspricht range(1,10).
Man sieht: Es k ¨onnen beliebig viele for-Klauseln hintereinander stehen, was einer
Schachtelung von for-Schleifen entspricht. Im ersten Durchlauf hat x den Wert 1 und
y durchl¨auft die Zahlen von 1 bis (ausschließlich) 10; im zweiten Durchlauf hat x den
Wert 2 und y durchl¨auft wiederum die Zahlen von 1 bis ausschließlich 10, usw. Jede
dieser beiden for-Klauseln k¨onnte (auch wenn dies in obigem Beispiel nicht geschieht)
ein if-Statement verwenden, das die Werte f ¨ur x bzw. y, die durchgelassen werden,
einschr¨ankt.
iv) Die jeweils ersten Zeichen von in einer Liste beﬁndlichen Strings.
>>> [x [0] for x in ['alt','begin','char','do' ]]
['a','b','c','d' ]
Der Platzhalter ⟨ausdr⟩ entspricht hier dem Ausdruck x [0] und der Platzhalter
⟨sequenz1⟩entspricht der Stringliste ['alt','begin',... ]. Die Schleifenvariable x durch-
l¨auft nacheinander die Strings 'alt', 'begin', usw. In jedem Durchlauf wird das erste
Zeichen des jeweiligen Strings in die Ergebnisliste eingef ¨ugt. Die folgende Abbildung
veranschaulicht dies nochmals:
:Wert der Listen-komprehension
[ 'alt' ,
'alt' [0]
'b','a', 'c',[ 'd' ]
'begin' [0] 'char' [0] 'do' [0]⟨ausdr⟩:
⟨sequenz1⟩: 'do' ]'begin' , 'char' ,
Aufgabe A.16
Gegeben sei ein (evtl. langer) String, der '\n'-Zeichen (also Newline-Zeichen, oder
Zeilentrenner-Zeichen) enth¨alt. Geben Sie – evtl. unter Verwendung einer Listenkom-
prehension – einen Ausdruck an, der . . .
(a) . . . die Anzahl der Zeilen zur ¨uckliefert, die dieser String enth ¨alt.
(b) . . . alle Zeilen zur¨uckliefert, die weniger als 5 Zeichen enthalten.
(c) . . . alle Zeilen zur¨uckliefert, die das Wort 'Gruffelo' enthalten.
A.5.2 Lambda-Ausdr ¨ucke
Mittels des Schl¨usselworts lambda ist es m¨oglich ”anonyme“ Funktionen zu deﬁnieren
– Funktionen also, die keinen festgelegten Namen besitzen, ¨uber den sie wiederholt

## Seite 306

A.5 Funktionale Programmierung 291
aufgerufen werden k ¨onnen. Oft werden solche namenslose Funktionen in Funktionen
h¨oherer Ordnung – wie etwa map, reduce oder ﬁlter – verwendet. Folgende Tabelle
beschreibt die Syntax eines Lambda-Ausdrucks.
lambda x1,x2,... : e Dieser Lambda-Ausdruck repr ¨asentiert eine Funktion,
die die Argumente x1, x2, . . . erwartet und den Ausdruck
e (der ¨ublicherweise von den Argumenten abh ¨angt)
zur¨uckliefert.
Die folgenden beiden Deﬁnitionen ergeben genau dieselbe Funktion add3:
>>>def add3(x,y,z ): return x +y +z >>>add3 = lambda x,y,z : x +y +z
Beide der obigen Deﬁnitionen erlauben einen Aufruf wie in folgendem Beispiel gezeigt:
>>>add3(1,2,3)
6
Das durch den Lambda-Ausdruck erzeugte Funktionsobjekt kann auch sofort ausgewer-
tet werden wie etwa in folgendem Beispiel:
>>>(lambda x,y: x *(y -x))(2,5)
6
A.5.3 Die map-Funktion
Die map-Funktion verkn¨upft mehrere Listen elementweise mit einer als Parameter¨uber-
gebenen Funktion:
map(f , l1 , l2 , ... )
Die map-Funktion liefert als Ergebnis immer eine Liste zur ¨uck. Die map-Funktion ruft
die Funktion f zun¨achst auf alle ersten Elemente der Listen l1 , l2 , ... , auf, anschlie-
ßend f¨ur alle zweiten Elemente, usw. Die Menge der so erhaltenen Werte wird als Liste
zur¨uckgeliefert.
Folgendes Beispiel zeigt die Anwendung der map-Funktion auf eine zweistellige Funk-
tion f; es werden zwei Listen [x 0,x1,... ] und [ y0,y1,... ] elementweise verkn ¨upft und
daraus eine neue Liste [e0,e1,... ] erzeugt:
f
f
[ e0 , e1 , ] . . .
[ y0, y1, . . . ] )[ x0, x1, . . . ] ,map( f ,

## Seite 307

292 A Python Grundlagen
>>>def add(x,y): return x +y
>>>map(add, [1,3,5], [10,100,1000])
[11, 102, 1003]
H¨auﬁg wird ein Lambda-Ausdruck verwendet, um das als ersten Parameter erwartete
Funktionsobjekt zu erzeugen – dies zeigen die folgenden beiden Beispiele:
>>>map(lambda x,y:x +y,
... 'Hallo','Welt!')
['HW', 'ae', 'll', 'lt', 'o!' ]
>>>map(lambda x,y,z: (x +y) *z,
... [1,2,3 ], [4,5,6 ], range(10,13))
[50, 77, 108]
Aufgabe A.17
Verwenden Sie die map-Funktion, um einer (String-)Liste von Zeilen Zeilennummern
hinzuzuf¨ugen. Der Ausdruck:
['Erste Zeile', 'Zweite Zeile', 'Und die dritte Zeile' ]
sollte also umgewandelt werden in folgenden Ausdruck:
['1. Erste Zeile', '2. Zweite Zeile', '3. Und die dritte Zeile' ]
A.5.4 Die all - und die any-Funktion
Die all -Funktion und die any-Funktion verkn¨upfen eine Menge von Wahrheitswerten
mittels einer logischen Und-Verkn¨upfung bzw. mittels einer logischen Oder-Verkn¨upfung.:
all (l) Liefert genau dann ”True“ zur ¨uck, wenn alle Elemente
des iterierbaren Objektes l den Wahrheitswert ”True“
besitzen.
any(l) Liefert genau dann ”True“ zur¨uck, wenn mindestens ein
Element des iterierbaren Objektes l den Wahrheitswert
”True“ besitzt.
Beispiele:
>>> all ( [x<10 for x in range(9)])
True
>>>any(map(str. isdigit ,'124'))
True
A.5.5 Die enumerate-Funktion
Die enumerate-Funktion ist n¨utzlich, wenn man sich nicht nur f¨ur die einzelnen Elemente
einer Sequenz interessiert, sondern auch f ¨ur deren Index in der Sequenz.

## Seite 308

A.5 Funktionale Programmierung 293
enumerate(iter) Die enumerate-Funktion erh¨alt als Argument eine ite-
rierbares Objekt iter und erzeugt daraus als Ergebnis
wiederum einen Iterator. Dieser enth¨alt Paare bestehend
aus einem Z¨ahler und aus den einzelnen Elementen des
als Argument ¨ubergebenen Objekts.
Beispiele:
>>>enumerate('Hallo')
<enumerate object at ... >
>>> [x for x in enumerate('Hallo')]
[(0, 'H' ), (1, 'a' ), (2, 'l' ), (3, 'l' ), (4, 'o')]
A.5.6 Die reduce-Funktion
reduce(f , l) Verkn¨upft die Elemente einer Liste (bzw. einer Sequenz)
nacheinander mit einer zwei-stelligen Funktion. Die Ver-
kn¨upfung erfolgt von links nach rechts.
Der Aufruf (⊕stehe hierbei f ¨ur einen beliebigen bin ¨aren Operator)
reduce(lambda x,y:x ⊕y, [x0, x1 , x2 , . . . , xn] )
liefert also den Wert des Ausdrucks
(···(((x0 ⊕x1) ⊕x2) ⊕...) ⊕xn)
zur¨uck.
Wir verwenden die reduce-Funktion f¨ur die Implementierung von Hashfunktionen in
Abschnitt 3.4 und f ¨ur die Implementierung eines rollenden Hashs in Abschnitt 7.5.
Beispiele. Die folgende Aufz ¨ahlung gibt einige Anwendungsbeispiele f ¨ur die Verwen-
dung der reduce-Funktion:
i) Aufsummieren aller ungeraden Zahlen von 1 bis 1000.
>>>reduce(lambda x,y: x +y, range(1,1000,2))
250000
Berechnet die Summe (···((1 + 3) + 5) +... + 999). Die gleiche Berechnung kann man
auch mit sum(range(1,1000,2)) durchf¨uhren.
ii) Verkn¨upfen einer Menge von Strings zu einem String der aus einer Menge von Zeilen
besteht.
>>>reduce( lambda x,y: x +'\n' +y,
['Erste Zeile', 'Zweite Zeile', 'Dritte Zeile' ])
'Erste Zeile\nZweite Zeile\nDritte Zeile'

## Seite 309

294 A Python Grundlagen
Die als erster Parameter ¨ubergebene Funktion verkettet zwei Strings mit dem Newline-
Zeichen '\n' als Trenner. Die reduce-Funktion verkettet ebentsprechend alle Strings in
der Liste und f ¨ugt jeweils ein '\n'-Zeichen zwischen zwei Strings ein.
iii) Umwandeln einer als String repr ¨asentierten Hexadezimal-Zahl in einen
Python Integerwert unter Verwendung des Horner-Schemas:
Angenommen, die hexadezimale Zahl h0h1h2h3h4 sei gegeben. Will man daraus die
entsprechende Dezimalzahl ¨uber
h0 ∗164 + h1 ∗163 + h2 ∗162 + h3 ∗161 + h4 ∗160
berechnen, so ist dies wenig eﬃzient. Es werden zur Berechnung der Potenzen sehr viele
(n¨amlich 4+3+2) Multiplikationen durchgef¨uhrt – und Multiplikationen sind meist sehr
rechenintensiv. Die gleiche Berechnung kann folgendermaßen mit weniger Multiplika-
tionen durchgef¨uhrt werden:
(((h0 ∗16 + h1) ∗16 + h2) ∗16 + h3) ∗16 + h4
Dieses Berechnungs-Schema ist das sog. Horner-Schema. Eine Implementierung kann
elegant mit Hilfe der reduce-Funktion erfolgen:
>>>hexNum = '12fb3a'
>>>reduce(lambda x,y: 16 *x +y,
[c2h(h) for h in hexNum])
1243962
Wir nehmen an, c2h wandelt eine als String repr¨asentierte hexadezimale Ziﬀer in einen
Zahlenwert um. Die Listenkomprehension [ c2h(h) for h in hexNum] erzeugt zun ¨achst
eine Liste der Integerwerte, die den einzelnen Ziﬀern inhexNum entsprechen – hier w¨are
das die Liste [ 1,2,15,11,3,10 ]. Die reduce-Funktion verkn¨upft dann die Elemente der
Liste mit als Lambda-Ausdruck speziﬁzierten Funktion und verwendet so das Horner-
Schema um die Dezimalrepr¨asentation der Hexadezimalzahl '12fb3a' zu berechnen.
Aufgabe A.18
Verwenden Sie die reduce-Funktion, um eine Funktion max(lst) zu deﬁnieren, die das
maximale in lst beﬁndliche Element zur¨uckliefert.
Aufgabe A.19
Verwenden Sie diereduce-Funktion, um eine Liste von Tupeln”ﬂachzuklopfen“ und in
eine einfache Liste umzuwandeln. Beispiel: Die Liste [ (1,10), ( 'a','b'), ( [1], [2]) ]
sollte etwa in die Liste [1,10, 'a','b',[1], [2] ] umgewandelt werden.
Aufgabe A.20
Implementieren Sie die Funktionen any und all mittels der reduce-Funktion.

## Seite 310

A.6 Vergleichen und Sortieren 295
A.6 Vergleichen und Sortieren
Zum Einen beschreibt Abschnitt 2 Sortieralgorithmen, zum Anderen verwenden viele
in diesem Buch vorgestellten Algorithmen Sortierfunktionen – etwa einige Heuristiken
zur L¨osung des Travelling-Salesman-Problems (etwa der in Abschnitt 8.5.3 vorgestellte
genetische Algorithmus und der in Abschnitt 8.6 vorgestellte Ameisen-Algorithmus).
A.6.1 Vergleichen
F¨ur viele in diesem Buch vorgestellten Algorithmen ist es wichtig genau zu verstehen,
wie Werte in Python verglichen werden. W¨ahrend intuitiv klar sein d¨urfte, dass Zahlen-
werte einfach ihrer Gr ¨oße nach verglichen werden, bedarf es einer kurzen Erl ¨auterung
was Vergleiche von Werten zusammengesetzter Typen oder Vergleiche von Werten un-
terschiedlicher Typen betriﬀt.
Vergleiche mitNone. Der Wert None wird von Python immer als kleiner klassiﬁziert
als jeder andere Wert. Beispiele:
>>>None < 0
True
>>>None < -ﬂoat('inf')
True
>>>None < False
True
>>>None < None
False
Anmerkung: Der Python-Wert ﬂoat ('inf') steht f ¨ur den mathematischen Wert ∞
(”Unendlich“), Der Python-Wert -ﬂoat('inf') steht entsprechend f ¨ur den mathema-
tischen Wert −∞(”Minus Unendlich“).
Vergleiche mit booleschen Werten. Bei Vergleichen mit Booleschen Werten muss
man sich lediglich dar ¨uber im Klaren sein, dass in Python der boolesche Wert ”False“
der Zahl ”0“ und der boolesche Wert ”True“ der Zahl ”1“ entspricht:
>>>False == 0
True
>>>True == 1
True
Vergleiche zwischen booleschen Werten und Zahlen ergeben dementsprechende Ergeb-
nisse. Beispiele:
>>>False < True
True
>>>False < -1
False
>>>True < 10
True
Vergleiche von Sequenzen. Sequenzen sind in Python lexikographisch geordnet, d. h.
zwei Sequenzen werden von links nach rechts verglichen; die erste Stelle, die sie unter-
scheidet, entscheidet dar ¨uber, welche der Sequenzen kleiner bzw. gr ¨oßer ist. Dies ent-
spricht genau der Art und Weise, wie Namen in einem Telefonbuch angeordnet sind:
Die Namen werden zun¨achst nach dem linkesten Buchstaben sortiert; besitzen zwei Na-
men denselben linkesten Buchstaben, so entscheidet der n ¨achste Buchstabe ¨uber deren
Anordnung, usw.

## Seite 311

296 A Python Grundlagen
Beispielsweise gilt
>>>'aachen' < 'aalen'
True
da sich die ersten beiden Stellen nicht unterscheiden und 'c' < 'l' gilt.
Außerdem werden k¨urzere Sequenzen – bei identischem Pr¨aﬁx – als kleiner klassiﬁziert.
Einige weitere Beispiele f ¨ur Vergleiche von Sequenzen:
>>> [2,100] < [3,1]
True
>>> [0] < [1]
True
>>> [0] < [0,0,0 ]
True
>>> [ ] < [0]
True
Zahlen werden in Python immer als kleiner klassiﬁziert als Werte zusammengesetzter
Typen. Einige Beispiele:
>>>0 < [0]
True
>>> [0] < [[0]]
True
>>>100 < []
True
A.6.2 Sortieren
Python bietet eine destruktive Sortierfunktion sort (die keinen R ¨uckgabewert liefert)
und eine nicht-destruktive Sortierfunktion sorted (die die sortierte Version der Sequenz
als R¨uckgabewert liefert) an. Die Funktion sort sortiert in-place, ist also speichereﬃzi-
enter und schneller als die Funktion sorted, die zun ¨achst eine neue Kopie der Sequenz
anlegen muss.
Ein Beispiel f ¨ur die unterschiedliche Funktionsweise von sort und sorted; in beiden
F¨allen sei deﬁniert:
l = list ('Python')
>>> sorted(l)
['P', 'h', 'n', 'o', 't', 'y' ]
>>> l . sort()
>>> l
['P', 'h', 'n', 'o', 't', 'y' ]
Sortieren nach bestimmten Eigenschaften. H¨auﬁg m¨ochte man eine Sequenz von
Werten nicht nach der ¨ublichen (i. A. lexikographischen) Ordnung, sondern stattdessen
nach einer selbst bestimmten Eigenschaften sortieren. M¨ochten man etwa eine Liste von
Strings (anstatt lexikographisch) der L ¨ange der Strings nach sortieren, so k ¨onnte man
wie folgt vorgehen: Zun ¨achst ”dekoriert“ man die Strings mit der Information, die f ¨ur
die gew ¨unschte Sortierung relevant ist – in diesem Fall w ¨urde man also jeden String
mit seiner L ¨ange dekorieren und eine Liste von Tupeln der Form ( len(s ),s) erzeugen.
Ein Sortierung dieser Tupelliste bringt das gew ¨unschte Ergebnis: Die Tupel werden
nach ihrer erste Komponente (d. h. ihrer L ¨ange nach) sortiert; besitzen zwei Tupel
dieselbe erste Komponente (d. h. besitzen die entsprechenden Strings dieselbe L¨ange), so
werden diese nach ihrer zweiten Komponente geordnet, also lexikographisch nach ihrem

## Seite 312

A.6 Vergleichen und Sortieren 297
Namen. Anschließend m¨usste man die f¨ur die Sortierung relevante ”Dekoration“ wieder
entfernen. In dieser Weise k ¨onnte man etwa folgendermaßen Pythons Stringmethoden
ihrer L¨ange nach sortieren:
1 >>>methods = [(len(s ),s) for s in dir(str) ]
2 >>>methods.sort()
3 >>>methods = [s for l,s in methods]
4 >>>methods
5 ['find', 'join', 'count', 'index', 'ljust', 'lower', 'rfind', 'rjust', ...]
(Wir erinnern uns: dir(str) erzeugt die Liste aller Methoden des Typs str.)
Die Dekoration erfolgt durch die Listenkomprehension in Zeile 1, das Entfernen der
Dekoration erfolgt durch die Listenkomprehension in Zeile 3.
Pythons Sortierfunktionen bieten die M¨oglichkeit, sich diese ”Dekorationsarbeiten“ ab-
nehmen zu lassen. Den Funktionen sort und sorted kann man mittels eines sog. be-
nannten Parameters ”key“ eine Funktion ¨ubergeben, deren R ¨uckgabewert f¨ur die Sor-
tierung verwendet wird. Dadurch kann man Pythons Stringmethoden folgendermaßen
ihrer L¨ange nach sortieren:
1 >>>methods = dir(str)
2 >>>methods.sort(key=len)
3 >>>methods
4 ['find', 'join', 'count', 'index', 'ljust', 'lower', 'rfind', 'rjust', ...]
H¨auﬁg gibt man den ”key“-Parameter mittels eines Lambda-Ausdrucks an. Folgender-
maßen k¨onnte man etwa Pythons Stringmethoden sortiert nach der Anzahl der enthal-
tenen 'e's sortieren; die Sortierung erfolgt in diesem Beispiel ¨ubrigens absteigend, was
durch den benannten Parameter ”reverse“ festgelegt werden kann:
1 >>>methods=dir(str)
2 >>>methods.sort(key=lambda s: s.count('e'), reverse=True)
3 >>>methods
4 ['__reduce_ex__', '_formatter_field_name_split', '__getattribute__', ...]

## Seite 313

298 A Python Grundlagen
Aufgabe A.21
Sortieren Sie die Zeilen einer Datei test.txt . . .
(a) . . . absteigend ihrer L¨ange nach.
(b) . . . der Anzahl der enthaltenen Ziﬀern nach.
(c) . . . der Anzahl der enthaltenen W¨orter (verwenden Sie die String-Methode split )
nach.
(d) . . . der L¨ange des l¨angsten Wortes der jeweiligen Zeile nach.
Hinweis: Die Zeilen der Datei test.txt k¨onnen Sie folgendermaßen auslesen:
open('test.txt').readlines()
A.7 Objektorientierte Programmierung
Zentral f¨ur die objektorientierte Programmierung ist die M ¨oglichkeit neue Klassen er-
zeugen zu k¨onnen. Eine Klasse ist eigentlich nichts anderes als ein Python-Typ, genau
wie int, string, list oder dict. Die Syntax zur Erzeugung einer neuen Klasse lautet:
class ⟨name⟩:
⟨kommando1⟩
. . .
⟨kommandon⟩
Erzeugt eine neue Klasse mit Namen ⟨name⟩. Je-
desmal, wenn ein Objekt dieser Klasse erzeugt wird,
werden ⟨kommando1⟩, . . . ⟨kommandon⟩ ausgef¨uhrt.
H¨auﬁg beﬁnden sich unter den Kommandos Methoden-
Deﬁnitionen (d. h. relativ zur Klasse lokale Funktionen)
oder Deﬁnitionen von Klassenvariablen.
Listing A.33 zeigt ein Beispiel f ¨ur eine sehr einfache Klassendeﬁnition:
1 class Auto:
2 typ = 'VW Golf'
3 def sagHallo( self ):
4 print 'Hallo, ich bin ein Auto'
Listing A.33: Deﬁnition einer einfachen Klasse
In Zeile 2 wird eine relativ zur Klassendeﬁnition lokale Variabletyp deﬁniert; eine solche
lokale Variable nennt man im Sprachjargon der Objektorientierten Programmierung
als Klassenattribut. In Zeile 4 wird eine Funktion sagHallo deﬁniert; im Sprachjargon
der Objektorientierten Programmierung wird eine solche lokale Funktion als Methode
bezeichnet. Jede Methode muss als erstes Argument den Parameter ” self“ ¨ubergeben
bekommen; self enth¨alt immer die Referenz auf das Objekt selbst; so kann innerhalb der
Methode etwa auf Attribute des Objekts zugegriﬀen werden. Bei jedem Methodenaufruf
wird self immer explizit mit ¨ubergeben.

## Seite 314

A.7 Objektorientierte Programmierung 299
Durch folgende Anweisung
>>>einAuto = Auto()
kann man eine Instanz der Klasse erzeugen, im OO-Sprachjargon ¨ublicherweise auch
als ein Objekt (in diesem Fall der Klasse Auto) bezeichnet. Auf das Attribut typ kann
man mittels einAuto.typ zugreifen, und auf die Methode sagHallo kann man mittels
einAuto.sagHallo zugreifen – dadurch erh ¨alt die Methode implizit als erstes Argument
das Objekt einAuto; in der Deﬁnition von sagHallo wird dieses allerdings nicht verwen-
det.
>>>einAuto.typ
'VW Golf'
>>>einAuto.sagHallo()
'Hallo, ich bin ein Auto'
Enth¨alt eine Klassendeﬁnition die Methode init , so wird diese Methode bei jedem
Erzeugen eines Objektes automatisch ausgef ¨uhrt. Neben dem obligaten Argument self
kann die init -Methode noch weitere Argumente enthalten; die Erzeugung von Ob-
jekten kann so abh ¨angig von bestimmten Parametern erfolgen. Listing A.34 zeigt eine
modiﬁzierte Deﬁnition der Klasse Auto die bei der Objekterzeugung zwei Parameter t
und f erwartet:
1 class Auto:
2 anzAutos = 0
3
4 def init ( self , t , f ):
5 self .typ = t
6 self . farbe = f
7 Auto.anzAutos += 1
8
9 def del ( self ):
10 Auto.anzAutos -= 1
11
12 def ueberDich(self ):
13 print "Ich bin ein %ser %s; du hast momentan %d Autos" %\
14 ( self . farbe, self .typ, Auto.anzAutos)
Listing A.34: Deﬁnition einer komplexeren Auto-Klasse
Bei der Erzeugung einer neuen Instanz von Auto wird nun immer automatisch die
init -Methode ausgef¨uhrt, die neben self zwei weitere Argumente erwartet, die dann
in Zeile 6 und 7 den (Objekt-)Attributen typ und farbe zugewiesen werden. Man kann
mittels self .typ bzw. self . farbe auf die Attribute typ bzw. farbe des aktuellen Objektes
zugreifen.
Die Attribute self .typ und self . farbe geh¨oren also zu einem bestimmten Objekt der
Klasse Auto und k¨onnen f¨ur unterschiedliche Objekte unterschiedliche Werte annehmen.

## Seite 315

300 A Python Grundlagen
Dagegen ist das in Zeile 2 deﬁnierte Attribut anzAutos ein Klassenattribut, d. h. es
geh¨ort nicht zu einer bestimmten Instanz von Auto, sondern ist global f ¨ur alle Objekte
der Klasse sichtbar; Gleiches gilt f¨ur alle Methodendeklarationen – auch sie sind global
f¨ur alle Objekte der Klasse sichtbar.
Bei jeder Erzeugung einer Klasseninstanz erh ¨ohen wir die Variable anzAutos um Eins.
Die in Zeile 10 deﬁnierte spezielle Methode del wird immer dann automatisch auf-
gerufen, wenn mittels des del-Kommandos ein Objekt der Klasse gel¨oscht wird; in Zeile
11 erniedrigen wir die Variable anzAutos um Eins, wenn ein Objekt gel ¨oscht wird.
In folgendem Beispiel werden drei verschiedene Variablen vom Typ Auto erzeugt:
>>>a1 = Auto("Mercedes-Benz", "gruen")
>>>a2 = Auto("BMW", "rot")
>>>a3 = Auto("VW Golf", "schwarz")
Nun k¨onnen wir uns mittels der Methode ueberDich Informationen ¨uber das jeweilige
Objekt ausgeben lassen:
>>>a1.ueberDich()
Ich bin ein gruener Mercedes-Benz; du hast momentan 3 Autos
>>>del(a1)
>>>a2.ueberDich()
Ich bin ein roter BMW; du hast momentan 2 Autos
Man kann auch eine neue Klasse erzeugen, die auf den Attributen und Methoden einer
anderen Klasse basiert – im OO-Jargon nennt man das auch Vererbung. Falls uns das
Alter eines Autos nur dann interessiert, wenn es sich um einen Oldtimer handelt, dann
k¨onnten wir eine Klasse Oldtimer wie folgt deﬁnieren:
1 class Oldtimer(Auto):
2 def init ( self , t , f , a):
3 Auto. init ( self , t , f)
4 self . alter = a
5 def ueberDich(self ):
6 Auto.ueberDich(self)
7 print "Ausserdem bin ich %d Jahr alt" %self.alter
Wie man sieht, muss man die init -Methode der Basisklasse explizit aufrufen; Glei-
ches gilt auch f ¨ur andere gleichlautende Methoden: die Methode ueberDich muss die
gleichlautende Methode der Basisklasse explizit aufrufen. Wir k ¨onnen nun ein Objekt
vom Typ Oldtimer folgendermaßen erzeugen und verwenden:
>>>o1 = Oldtimer("BMW", "grau", 50)
>>>o1.ueberDich()
Ich bin ein grauer BMW; du hast momentan 3 Autos
Ausserdem bin ich 50 Jahr alt

## Seite 316

A.7 Objektorientierte Programmierung 301
Basisklassen modellieren i. A. allgemeinere Konzepte und daraus abgeleitete Klassen
modellieren entsprechend spezialisiertere Konzepte, wie es ja im Falle von Auto und
Oldtimer auch der Fall ist: ”Oldtimer“ ist ein Spezialfall von einem ”Auto“.
Neben der init -Methode und der del -Methode gibt es in Python noch eine
Reihe weiterer Methoden mit spezieller Bedeutung, unter Anderem:
 str ( self ): Diese Methode berechnet die String-Repr¨asentation eines bestimm-
ten Objektes; sie wird durch Pythons interne Funktion str( ... ) und durch die
print-Funktion aufgerufen.
 cmp ( self ,x): Diese Methode wird bei Verwendung von Vergleichsoperationen
aufgerufen; sie sollte eine negative ganze Zahl zur¨uckliefern, falls self <x; sie sollte
0 zur¨uckliefern, falls self ==x; sie sollte eine positive ganze Zahl zur¨uckliefern, falls
self >x.
 getitem ( self , i): Wird bei der Auswertung des Ausdrucks self [i ] ausgef¨uhrt.
 setitem ( self , i ,v): Wird bei einer Zuweisung self [i ]=v ausgef¨uhrt.
 len ( self ): Wird bei der Ausf ¨uhrung der Python internen Funktion len( ... )
aufgerufen.
A.7.1 Spezielle Methoden
Python interpretiert einige Methoden, deren Namen stets mit ” “ beginnen und mit
” “ enden, in einer besonderen Weise. Ein Beispiel haben wir hierbei schon kennenge-
lernt: die init -Methode, die immer dann aufgerufen wird, wenn eine neue Instanz
einer Klasse erzeugt wird. Wir lernen im Folgenden noch einige weitere (nicht alle)
solcher Methoden kennen.

## Seite 318

B Mathematische Grundlagen
B.1 Mengen, Tupel, Relationen
B.1.1 Mengen
Eine Menge fasst mehrere Elemente (z. B. Zahlen, Knoten, Strings, . . . ) zu einer Einheit
zusammen. ¨Ublicherweise werden die geschweiften Klammern ”{“ und ”}“ verwendet,
um eine Menge darzustellen. Eine Menge, die kein Element enth ¨alt, wird als die leere
Menge bezeichnet und ¨ublicherweise durch das Symbol ∅notiert. Die Notation einer
Menge erfolgt entweder ¨uber das Aufz¨ahlen ihrer Elemente, wie etwa in folgenden Bei-
spielen:
{1,10,100,2,20,200} {a,b,c} {{1, 2},{8,9},∅,200}
oder durch eine sog. Mengenkomprehension, wie etwa in folgenden Beispielen:
{x |x∈N ∧(x≤100 ∨x≥1000) } {x 3 |x∈N ∧ x≤10}
Mengenkomprehensionen ¨ahneln Python’s Listenkomprehensionen.
Im Gegensatz zu (mathematischen und Python’s) Tupeln und Python’s Listen sind
Mengen nicht geordnet, d. h. es gibt keine Reihenfolge der Elemente in einer Liste und
zwei Mengen gelten als gleich, wenn sie die gleichen Elemente enthalten. Beispielsweise
gilt also
{1,2,3}= {3,2,1} bzw. in Python set( [1,2,3 ]) == set([3,2,1])
B.1.2 Tupel
Auch Tupel fassen mehrere Elemente zu einer Einheit zusammen. Im Gegensatz zu
Mengen sind sie allerdings geordnet, d. h. die Reihenfolge in der die Elemente im Tupel
notiert sind spielt eine Rolle. Daher gilt beispielsweise
(x,y) ̸= (y,x) falls x̸= y
Das Kreuzprodukt zweier Mengen Aund B – notiert als A×B – bezeichnet die Menge
aller Tupel, deren erste Komponente Elemente aus A und deren zweite Komponente
Elemente aus B enthalten. Formaler kann das Kreuzprodukt folgendermaßen deﬁniert
werden:
A×B := {(x,y) |x∈A ∧y∈B}

## Seite 319

304 B Mathematische Grundlagen
Kreuzprodukte werden beispielsweise bei der Deﬁnition von gerichteten Graphen (siehe
Abschnitt 5) verwendet oder bei der Deﬁnition von Produktionen einer Grammatik
(siehe Abschnitt 6.1).
Mathematische Tupel entsprechen Pythons Tupel und Pythons Listen in der Hinsicht,
dass die Reihenfolge der Elemente eine Rolle spielt. Mathematische Mengen entsprechen
Objekten mit Pythons set-Typ.
B.1.3 Relationen
Formal deﬁniert sich eine Relation ¨uber den Mengen A und B als eine Teilmenge des
Kreuzproduktes A×Bder beiden Mengen. Relationen werden dazu verwendet, Elemente
aus A mit Elementen aus B in Beziehung zu setzen. Beispielsweise stellen folgende
Mengen Relationen dar ¨uber der Menge N und der Menge {a,b,c} dar:
{(1,a),(2,b), (3,c)} , ∅ , {(i,1) |i∈N}
Im Folgenden beschreiben wir wichtige Eigenschaften, die eine Relation haben kann;
insbesondere ein Verst¨andnis davon, was ”transitiv“ bedeutet ist eine Voraussetzung f¨ur
das Verst¨andnis einiger beispielsweise einiger Graphalgorithmen (etwa dem Warshall-
Algorithmus – siehe Abschnitt 5.3.2). Eine Reﬂexion R⊆ A×A heißt . . .
. . . reﬂexiv, falls ∀x ∈A : (x,x) ∈R. Eine Relation heißt also genau dann reﬂexiv,
wenn sich alle alle Tupel der Form (x,x) f¨ur x∈A in Rbeﬁnden.
. . . symmetrisch, falls (x,y) ∈R⇒ (y,x) ∈R. Eine Relation heißt alos genau dann
symmetrisch, wenn es zu jedem ( x,y) in Rauch ein (y,x) in Rgibt.
. . . anti-symmetrisch, falls ( x,y) ∈R∧ (y,x) ∈R⇒ x = y. Eine Relation heißt
also genau dann anti-symmetrisch, wenn es keine zwei Elemente (x,y ) und (y,x)
mit x ̸= y in Rgibt. Man beachte, dass ”nicht symmetrisch“ nicht gleich ”anti-
symmetrisch“ ist.
. . . transitiv, falls ( x,y) ∈R∧ (y,z) ∈R⇒ (x,z) ∈R. Eine Relation heißt also
genau dann transitiv, wenn – falls zwei Elemente x und z indirekt miteinander
in Relation stehen – sie automatisch auch immer direkt miteinander in Relation
stehen m¨ussen.
Einige Beispiele:
 R1 = {(1,3),(1,1)}ist nicht reﬂexiv (z.B. (2 ,2) fehlt), nicht symmetrisch (z. B.
(3,1) fehlt), anti-symmetrisch, und transitiv (die Transitivit ¨ats-Bedingung kann
mit den beiden vorhandenen Tupeln nicht verletzt werden).
 R2 = ∅ist nicht reﬂexiv, symmetrisch (es sind keine Tupel in der Relation, die
die Symmetriebedingung verletzen k ¨onnten), anti-symmetrisch und transitiv.
 R3 = {(x,y) |x,y ∈N, x = y}ist reﬂexiv, anti-symmetrisch und transitiv.

## Seite 320

B.1 Mengen, Tupel, Relationen 305
Aufgabe B.1
Betrachten Sie die folgenden Relationen und begr ¨unden Sie, ob diese reﬂexiv, sym-
metrisch, anti-symmetrisch oder transitiv sind.
(a) R4 = {(x,y) |x,y ∈R und x teilt y }
(b) R5 = {(x,y) |x,y ∈N ∧x≤10 ∧y≥100}
(c) R6 = {(x,y) |x,y ∈{a,b,...,z }und x kommt im Alphabet vor y }
(d) R7 = N ×N
Aufgabe B.2
Schreiben Sie eine Python-Funktion . . .
(a) . . . isReﬂexive (A,R), die testet, ob die als Sequenz von Paaren ¨ubergebene Re-
lation R reﬂexiv ist. Der Parameter A soll hierbei die Grundmenge speziﬁzieren.
Beispielanwendung:
>>> isReﬂexive ( [ 1,2,3,4 ], [ (1,1),(1,2),(2,2),(4,2),(3,3),(4,4) ])
>>>True
(b) . . . isSymmetric(A,R), die testet, ob die als Sequenz von Paaren ¨ubergebene Re-
lation R symmetrisch ist. Der Parameter A soll hierbei die Grundmenge speziﬁ-
zieren.
(c) . . . isAntiSymmetric(A,R), die testet, ob die als Sequenz von Paaren ¨ubergebene
Relation R anti-symmetrisch ist. Der Parameter A soll hierbei die Grundmenge
speziﬁzieren.
(d) . . . isTransitive(A,R), die testet, ob die als Sequenz von Paaren ¨ubergebene Re-
lation R transitiv ist. Der ParameterA soll hierbei die Grundmenge speziﬁzieren.
Die transitive H ¨ulle einer Relation Rist deﬁniert als die ”kleinste“ (betreﬀend der
Ordnungsrelation ”⊆“; d. h. mit m¨oglichst wenig Elementen) transitive Relation, die R
enth¨alt.
Aufgabe B.3
Was ist die transitive H¨ulle der Relation . . .
(a) R= {(1,2),(2,1),(4,1),(2,3)}, ¨uber A= {1,2,3,4,5}
(b) R= {(4,2),(1,2),(2,3),(3,4)}, ¨uber A= {1,2,3,4,5}

## Seite 321

306 B Mathematische Grundlagen
B.1.4 Vollst ¨andige Induktion
Die Beweistechnik der vollst¨andigen Induktion wird in der Mathematik h ¨auﬁg verwen-
det, wenn es um Beweise von Aussagen ¨uber ganze Zahlen geht. Aussagen dieser Art
sind in der diskreten Mathematik und der Zahlentheorie – und damit auch in der Al-
gorithmik – h¨auﬁg anzutreﬀen.
Außerdem lohnt sich ein Verstehen dieser Beweistechnik schon allein deshalb, weil diese
eng verwandt mit der Implementierungstechnik der Rekursion ist.
Ein Induktionsbeweis einer ¨uber eine ganze Zahl parametrierten Aussage A(n) – die im
n¨achsten Abschnitt vorgestellte Summenformel ist etwa eine solche Aussage – gliedert
sich in zwei Teile:
Induktionsanfang: Hier wird die Aussage zun ¨achst f¨ur den Fall n= 0 bzw. n= 1 –
bzw. je nachdem ab welchem n die zu zeigende Aussage g ¨ultig ist – gezeigt. Der
Induktionsanfang ist eng verwandt mit dem Rekursionsabbruch.
Induktionsschritt: Hier wird die Implikation A(k) ⇒A(k + 1) gezeigt. Man geht
also zun ¨achst hypothetisch davon aus, dass A(k) gilt und versucht aus dieser
Annahme (auch als Induktionshypothese bezeichnet) die G ¨ultigkeit der Aussage
A(k+ 1) abzuleiten. Man beachte hier wiederum die Analogie mit der Rekursion:
Auch bei der Programmierung des Rekursionsschritts muss man davon ausgehen,
dass der Aufruf mit dem ”kleineren“ Argument das richtige Ergebnis liefert; aus
dieser Annahme versucht man dann, das Ergebnis f ¨ur das gr ¨oßere Argument zu
konstruieren.
Wir geben ein Beispiel und zeigen ¨uber vollst¨andige Induktion, dass f ¨ur alle n∈N der
Ausdruck 4n3 −n immer durch 3 teilbar ist.
 Induktionsanfang: Es gilt 4 ·13 −1 = 3 ist durch 3 teilbar.
 Induktionsschritt: Wir nehmen als an, dass 4k3 −k durch 3 teilbar sei und wollen
unter Verwendung dieser Annahme zeigen, dass dann auch 4(k + 1)3 −(k+ 1)
durch 4 teilbar ist:
4(k+ 1)3 −(k+ 1) = 4(k3 + 3k2 + 3k+ 1) −k−1 = 4k3 + 12k2 + 11k+ 3
= (4k3 −k) + (12k2 + 12k+ 3) = (4k3 −k) + 3(4k2 + 4k+ 1)
Da laut Induktionshypothese der linke Summand durch drei teilbar ist und auch
der rechte Summand durch 3 teilbar ist, ist der Induktionsschritt gezeigt.
B.1.5 Summenformel
Satz 1
Es gilt f¨ur alle n∈N, dass
n∑
i=1
= n·(n+ 1)
2

## Seite 322

B.2 Fibonacci-Zahlen 307
Am einfachsten l ¨asst sich der Satz mit vollst ¨andiger Induktion ¨uber n beweisen. Ein
konstruktiver Beweis, wie er wohl schon vom jungen Carl-Friedrich Gauß erfolgte, ver-
wendet die Tatsache, dass sich die Summe der erstennZahlen zusammen mit der Summe
der r¨uckw¨arts gez¨ahlten ersten n Zahlen einfach berechnen l¨asst. Es gilt n ¨amlich:
n∑
i=1
+
1∑
i=n
= 1 + 2 + ...n −1 + n
+ n+ n−1 + ... 2 + 1
= (n + 1) +... + (n+ 1)
= n·(n+ 1)
B.2 Fibonacci-Zahlen
Leonardo da Pisa, auch unter dem Namen ”Fibonacci“ bekannt,
war ein italienischer Mathematiker und vielleicht einer der be-
deutensten Mathematiker des Mittelalters. Er ver¨oﬀentlichte das
”Buch der Rechenkunst“ (Liber abbaci) das in seinem Anspruch
und seiner theoretischen Durchdringung vieler mathematischer
Fragestellungen (vor allem aus dem Bereich der nat¨urlichen Zah-
len) weit ¨uber Niveau anderer mittelalterlicher Werke hinaus-
ging.
Deﬁnition. Der Wert der i-ten Fibonacci-Zahl Fi (f¨ur i ≥0) l¨asst sich wie folgt re-
kursiv deﬁnieren:
F0 = 0
F1 = 1
Fi = Fi−2 + Fi−1, f¨ur i≥2
Wenden wir diese Deﬁnition an, so erhalten wir also:
F2 = F0 + F1 = 1,
F3 = F2 + F1 = 2,
F4 = F3 + F2 = 3,
...
Folgende Pythonprozedur setzt direkt die Deﬁnition um und berechnet dien-te Fibonacci-
Zahl:
def F(n):
if n==0: return 0
if n==1: return 1
return F(n -2) +F(n -1)

## Seite 323

308 B Mathematische Grundlagen
Aufgabe B.4
(a) Erkl ¨aren Sie, warum die Laufzeit von der eben vorgestellten Python-Funktion
”F“ sehr ung ¨unstig ist und sch¨atzen Sie die Laufzeit ab.
(b) Implementieren Sie eine nicht-rekursive Funktion ﬁb (n), die die Liste der ersten
n Fibonacci-Zahlen berechnet. Anstatt rekursiver Aufrufe sollten die Fibonacci-
Zahlen in einer Liste gespeichert werden und bei der Berechnung des n ¨achstens
Wertes auf die schon in der Liste gespeicherten Werte zur ¨uckgegriﬀen werden.
(c) Geben Sie unter Verwendung von ﬁb einen Python-Ausdruck an, der ¨uberpr¨uft,
ob die Formel
Fn+2 = 1 +
n∑
i=0
Fn
f¨ur alle n≤1000 gilt.
Eigenschaften. Um Laufzeit-Eigenschaften von Fibonacci-Heaps zu zeigen, ben¨otigen
wir einige Eigenschaften von Fibonacci-Zahlen.
Satz 2
Sei Fi die i-te Fibonacci-Zahl. Dann gilt, dass
Fn+2 = 1 +
n∑
i=0
Fi
Wir zeigen Satz 2 durch vollst ¨andige Induktion ¨uber n.
n= 0: In diesem Fall ist zu zeigen, dass F2 = 1; nach Deﬁnition der Fibonacci-Zahlen
ist dies oﬀensichlich der Fall.
k−1 →k: Es gilt
Fk+2 = Fk+1 + Fk
I.H.= (1 +
k−1∑
i=0
) + Fk = 1 +
k∑
i=0
Fi
womit der Induktionsschritt und damit die Aussage bewiesen ist.
Satz 3
F¨ur alle n∈N gilt, dass Fn+2 ≥ϕn, wobei ϕ= (1 +
√
5)/2 (der ”Goldene Schnitt“)
ist.
Auch Satz 3 k¨onnen wir einfach durch vollst¨andige Induktion ¨uber n≥2 zeigen.
n= 2: Es gilt, dass F2 = 1 ≥ϕ0 = 1.

## Seite 324

B.3 Grundlagen der Stochastik 309
>k →k: Es gilt:
Fk+2 = Fk + Fk+1
I.H.
≥ ϕk−2 + ϕk−1 = ϕk−2(1 + ϕ) = ϕk−2ϕ2
Zur Begr¨undung des letzten Schritts bleibt zu zeigen, dass 1 + ϕ= ϕ2:
ϕ2 =
(
1 +
√
5
2
)2
= 1 + 2
√
5 + 5
4 = 2(3 +
√
5)
4 = 2 + 1 +
√
5
2 = 1 + ϕ
Damit ist auch der Induktionsschritt und somit die Aussage gezeigt.
B.3 Grundlagen der Stochastik
Die Stochastik befasst sich mit der Untersuchung von Zufallsexperimenten und mit
Gesetzm¨aßigkeiten der Eintrittswahrscheinlichkeit von Ereignissen. F ¨ur unsere Belan-
ge gen ¨ugen die Grundlagen der Stochastik etwa f ¨ur die Analyse der Average-Case-
Laufzeiten von Algorithmen (hierf ¨ur arbeitet man h ¨auﬁg mit Zufallsvariablen – wie
etwa bei der Average-Case-Analyse von Quicksort – siehe Abschnitt 2.3.3) oder f ¨ur das
Verst¨andnis von randomisierten Algorithmen und Datenstrukturen wie etwa Bloomﬁlter
(siehe Abschnitt 3.5) oder Skip-Listen (siehe Abschnitt 3.6).
B.3.1 Wahrscheinlichkeitsraum
Bei der Modellierung ”unsicherer“ Situationen deﬁniert man sich einen Wahrscheinlich-
keitsraum, der meist mit dem griechischen Buchstaben Ω ( ”Omega“) bezeichnet wird
und folgendermaßen deﬁniert ist.
Deﬁnition B.1 Wahrscheinlichkeitsraum, Elementarereignis
Ein (diskreter) Wahrscheinlichkeitsraum ist bestimmt durch . . .
 . . . eine Menge Ω ={e0,e1,... }von Elementarereignissen.
 . . . eine Zuordnung der Elementarereignisseei zu einer Wahrscheinlichkeit Pr[ei],
wobei gelten muss:
1. 0 ≤Pr[ei] ≤1
2. ∑
e∈Ω Pr[e] = 1
Entscheidend ist insbesondere die Eigenschaft, dass die Summe der Wahrscheinlichkei-
ten aller Elementarereignisse immer eins sein muss, d. h. ein Wahrscheinlichkeitsraum
muss insofern ”vollst¨andig“ sein, als dass immer sicher (eben mit Wahrscheinlichkeit
”1“) eines der Elementarereignisse eintreten muss.
Beispielsweise k¨onnte man f¨ur die Modellierung eines Zufallsexperiments ”W¨urfeln mit
einem sechseitigen W¨urfel“ den Wahrscheinlichkeitsraum Ω ={1,2,3,4,5,6}mit Pr[e] =
1/6 f¨ur alle e∈Ω w¨ahlen.
Neben Elementarereignissen ist auch der Begriﬀ des ”Ereignisses“ wichtig:

## Seite 325

310 B Mathematische Grundlagen
Deﬁnition B.2 Ereignis
Eine Menge E ⊆Ω heißt Ereignis. Die Wahrscheinlichkeit Pr[E] ist deﬁniert als
Pr[E] =
∑
e∈E
Pr[e]
In gewissem Sinn ist also der ”Operator“ Pr ¨uberladen und sowohl f¨ur Elementarereig-
nisse als auch f ¨ur Mengen von Elementarereignissen deﬁniert.
Einfache Eigenschaften. Es gilt:
 Pr[∅] = 0
 Pr[Ω] = 1
 Pr[E] = 1 −Pr[E], wobei E = Ω \E. Diese Tatsache ist beispielsweise relevant
f¨ur Abschnitt 3.5.3.
 Pr[E′] ≤Pr[E], falls E′⊆E.
 Pr[E] = Pr[E1] +... + Pr[En], falls E = ⋃n
i=1 Ei und die Ereignisse Ei paarweise
disjunkt.
Unabh¨angigkeit von Ereignissen. Der Eintritt eines Ereignisses kann von dem eines
anderen Ereignisses abh¨angen bzw. unabh¨angig sein. Hierf¨ur deﬁnieren wir formal:
Deﬁnition B.3 Unabh¨angigkeit von Ereignissen
Zwei Ereignisse A und B nennt man unabh¨angig, wenn gilt:
Pr[A∩B] = Pr[A] ·Pr[B]
Intuitiv bedeutet die Unabh ¨angigkeit zweier Ereignisse A und B: Man kann aus dem
Wissen, dass A eingetreten ist keine R ¨uckschl¨usse auf den Eintritt von B ziehen (und
umgekehrt).
B.3.2 Laplacesches Prinzip
Spricht nichts dagegen, gehen wir (wie in obigem einfachen Beispiel eines Wahrschein-
lichkeitsraums) davon aus, dass alle Elementarwahrscheinlichkeiten gleichwahrscheinlich
sind und folglich gilt:
Pr[e] = 1
|Ω| bzw. Pr[E ] = |E|
|Ω|
Beispiel: Es gibt
(49
6
)
m¨ogliche Lottoziehungen. Folglich ist die Wahrscheinlichkeit, 6
Richtige zu raten, genau 1/
(49
6
)
.

## Seite 326

B.3 Grundlagen der Stochastik 311
B.3.3 Zufallsvariablen und Erwartungswert
Oft will man jedem Ausgang eines Zufallsexperiments eine bestimmte Zahl zuordnen.
Bei einem W ¨urfelspiel w¨urde etwa jedes Ereignis einem bestimmten Gewinn (bzw. ne-
gativem Gewinn bei Verlust) entsprechen; bei einem randomisierten Algorithmus w¨urde
jedes Ereignis bestimmten Rechen”kosten“ entsprechen. Hierf¨ur deﬁnieren wir:
Deﬁnition B.4 Zufallsvariable
Sei ein Wahrscheinlichkeitsraum auf der Ergebnismenge Ω gegeben. Eine Abbildung
X : Ω →R heißt Zufallsvariable.
Ein Beispiel: Wir modellieren einen 4-maligen M ¨unzwurf einer M ¨unze mit ”Wappen“
W und Zahl Z und interessieren uns daf ¨ur, wo oft ”Zahl“ f¨allt. Hierzu verwenden wir
den Wahrscheinlichkeitsraum
Ω = {W,Z}4 (:= {W,Z}×{W,Z }×{W,Z }×{W,Z })
d. h. Ω enth ¨alt alle m ¨oglichen 4-Tupel, deren Komponenten aus der Menge {W,Z}
kommen. Die Zufallsvariable Y : Ω →{0, 1,2,3,4}ordnet jedem Elementarereignis aus
Ω die Anzahl der Zahlw ¨urfe zu. Beispielsweise gilt Y((K,Z,K,Z )) = 2.
Oft interessiert man sich f ¨ur die Wahrscheinlicheit, mit der eine Zufallsvariable X be-
stimmte Werte annimmt. Man schreibt:
 Pr[X = i] f ¨ur Pr[{e ∈Ω |X(e) = i}]
 Pr[X ≤i] f ¨ur Pr[{e ∈Ω |X(e) ≤i}]
 Pr[j ≤X ≤i] f ¨ur Pr[{e ∈Ω |j ≤X(e) ≤i}]
 Pr[X2 ≤i] f ¨ur Pr[{e ∈Ω |(X(e))2 ≤i}]
. . .
F¨ur obige Beispiel-Zufallsvariable Y gilt etwa Pr[Y ≤3] = 1−Pr[Y = 4] = 1−(1/2)4 =
15/16.
Man kann jeder Zufallsvariablen zwei Funktionen zuordnen:
Dichte und Verteilung. Die Funktion fX : R →[0,1] mit fX(i) = Pr[X = i] heißt
Dichte von X. Die Dichte fX ordnet also jeder reellen Zahl idie Wahrscheinlichkeit zu,
dass die Zufallsvariable diesen Wert i annimmt.
Die Funktion FX : R →[0,1] mit FX(i) = Pr[ X ≤i] heißt Verteilung von X. Die
Verteilung FX ordnet also jeder reellen Zahl i die Warhscheinlichkeit zu, dass die Zu-
fallsvariable einen Wert kleiner (oder gleich) i annimmt.
Die Abbildungen B.1 und B.2 zeigen jeweils ein Beispiel einer Dichte und Verteilung.

## Seite 327

312 B Mathematische Grundlagen
0 1 2 3 4
fY
Abb. B.1:Dichte der oben deﬁnierten Zu-
fallsvariablen Y.
0 1 2 3 4
FY
Abb. B.2:Verteilung der oben deﬁnierten
Zufallsvariablen Y.
Erwartungswert. Oft interessiert man sich f ¨ur die Frage, welchen Wert eine Zufalls-
variable im Durchschnitt liefert. Hierzu wird der Erwartungswert deﬁniert:
Deﬁnition B.5
Sei X eine Zufallsvariable mit X : Ω →WX. Dann ist der Erwartungswert E[X ]
deﬁniert als:
E[X] :=
∑
i∈WX
i·Pr[X = i]
Bemerkung: Man kann den Erwartungswert auch alternativ ¨uber die Elementarereig-
nisse wie folgt berechnen (was tats ¨achlich in vielen F¨allen der einfachere Weg ist):
E[X] =
∑
e∈Ω
X(e) ·Pr[e]
Ein Beispiel: Der Erwartungswert E[Y] der oben deﬁnierten Zufallsvariablen Y (die die
Anzahl der Zahlw¨urfe bei einem 4-maligen M¨unzwurf z¨ahlt) ist gem¨aß obiger Deﬁnition:
E[Y] = 1 ·Pr[Y = 1] + 2·Pr[Y = 2] + 3·Pr[Y = 3] + 4·Pr[Y = 4]
Aufgabe B.5
Berechnen Sie das Ergebnis obiger Summe, d. h. berechnen Sie den konkreten Wert
f¨ur den Erwartungswert E[Y ].
B.3.4 Wichtige Verteilungen
Zufallsvariablen sind eigentlich vollst¨andig ¨uber ihre Dichten bzw. Verteilung bestimmt.
Man kann daher auch die Verteilungen untersuchen, ohne auf ein konkretes Zufallsex-
periment Bezug zu nehmen.

## Seite 328

B.3 Grundlagen der Stochastik 313
Die Bernoulli-Verteilung. Die Zufallsvariable X : Ω →{0, 1}mit Dichte
fX(i) =
{
p f¨ur i= 1
1 −p f¨ur i= 0
heißt Bernoulli-verteilt. Der Parameter p heißt Erfolgswahrscheinlichkeit. Es gilt, dass
E[X] = p, d. h. der erwartete Wert istp(der nat¨urlich nie eintritt, aber der Erwartungs-
wert selbst muss auch nicht notwendigerweise im Wertebereich der Zufallsvariablen lie-
gen).
Binomialverteilung. Ist eine Zufallsvariable X als Summe X := X1 + ... + Xn von
n unabh¨angigen Bernoulli-verteilten Zufallsvariablen (mit gleicher Erfolgswahrschein-
lichkeit p) deﬁniert, so heißt X binomialverteilt mit Parameter n und p. Man schreibt
auch
X ∼Bin(n,p)
wenn man zum Ausdruck bringen m ¨ochte, dass die Zufallsvariable X binomialverteilt
ist.
F¨ur den Wertebereich WX einer binomialverteilten Zufallsvariablen X gilt WX =
{0,1,...,n }. F¨ur die Dichte fX der Binomialverteilung gilt
fX(i) =
(n
i
)
·pi ·(1 −p)n−i
Beispielsweise war die oben beispielhaft deﬁnierte Zufallsvariable Y, die die Zahlw ¨urfe
bei 4-maligem M ¨unzwurf z¨ahlt, binomialverteilt mit Parameter n= 4 und p= 1/2.
Geometrische Verteilung. Diese Wahrscheinlichkeit ist insbesondere relevant bei
der Bestimmung der H¨ohe eines neu einzuf ¨ugenden Elements in einer Skip-Liste (siehe
Abschnitt 3.6 auf Seite 93) und entsprechend bei der Laufzeitbetrachtung der Such-,
Einf¨uge-, und L¨oschoperation auf Skip-Listen.
Eine geometrische Verteilung liegt dann vor, wenn bei einem Experiment eine Aktion
so lange wiederholt wird, bis sie ”erfolgreich“ ist. Sei pdie Wahrscheinlichkeit, dass ein
Versuch erfolgreich ist. Die Zufallsvariable X enth¨alt als Wert die Anzahl der Versuche,
bis Erfolg eintritt. Die Dichte der geometrischen Verteilung ist dann
fX(i) = (1 −p)i−1 ·p
F¨ur den Erwartungswert E[X] der geometrischen Verteilung gilt E[ X] = 1/p.
Aufgabe B.6
Rechnen Sie mit Hilfe der Deﬁnition des Erwartungswerts nach, dass bei einer geo-
metrisch verteilten Zufallsvariablen X gilt, dass E[X] = 1/p.
Ein Beispiel: Steht in einem Rechnernetz eine bestimmte Leitung nur mit einer Wahr-
scheinlichkeit von p = 1/10 zur Verf ¨ugung, dann sind durchschnittlich 1/p = 10 Ver-
suche notwendig, bis ein Datenpaket erfolgreich ¨uber die Leitung verschickt werden
kann.

## Seite 329

314 B Mathematische Grundlagen
B.4 Graphen, B ¨aume und Netzwerke
In vielen Anwendungen (K ¨urzeste Wege, Optimale Fl ¨usse in Netzwerken, Suchen) bil-
den Graphen das angemessenste mathematische Modell f ¨ur denjenigen Ausschnitt der
Wirklichkeit in dem ein bestimmtes Problem gel ¨ost werden soll.
B.4.1 Graphen
Ein Graph G = (V,E ) besteht aus einer Menge V von Knoten und einer Menge E
von Kanten (=Verbindungen) zwischen den Knoten. Man unterscheidetgerichtete Gra-
phen, bei denen die Richtung der Verbindung zwischen zwei Knoten eine Rolle spielt
und ungerichtete Graphen, bei denen diese Richtung keine Rolle spielt. Bei gerichteten
Graphen werden Kanten mathematisch als Knotentupel repr¨asentiert; bei ungerichteten
Graphen werden Kanten mathematisch als 2-elementige Teilmengen aus der Knoten-
menge repr¨asentiert. Abbildung B.3 zeigt links ein Beispiel f ¨ur einen gerichteten und
rechts ein Beispiel f¨ur einen ungerichteten Graphen.
1 2
3 4
5
a c
e
d
bf
Abb. B.3: Linkes Bild: eine graphische Veranschaulichung eines gerichteten Graphen
G1 = (V1,E1) mit der Knotenmenge V1 = {1,2,3,4,5} und der Kantenmenge E1 =
{(1,2),(2,3),(2,4),(3,4),(2,5),(5,5)}. Rechtes Bild: eine graphische Veranschaulichung eines
ungerichteten Graphen G2 = (V2,E2) mit der Knotenmenge V2 = {a,b,c,d,e,f }und der
Kantenmenge E2 = {{a,b},{a,c}, {a,d}, {b,e}, {b,f},{b,d}, {c,d}}.
Deﬁnitionen.
Nachbarschaft Man deﬁniert die Nachbarschaft Γ(i) eines Knoten i ∈V in einem
gerichteteten Graphen G= (V,E) folgendermaßen:
Γ(i) := {j |(i,j) ∈E }
Die Nachbarschaft eines Knotens in einem ungerichteten Graphen deﬁniert man,
indem man einfach (i,j) durch {i,j}ersetzt.
Grad eines Knotens Die Gr¨oße der Nachbarschaft eines Knotens i bezeichnet man
auch als Grad des Knotens und schreibt:
deg(i) := |Γ(i)|
Pfad Ein (ungerichteter) Pfad eines Graphen G= (V,E) ist eine Folge (v0,v1,...,v n)
von Knoten mit {vi,vi+1}∈ E. Ein (gerichteter) Pfad eines Graphen G= (V,E)
ist eine Folge (v0,v1,...,v n) von Knoten mit (vi,vi+1) ∈E.
Die L¨ange eines Pfades ist n.

## Seite 330

B.4 Graphen, B ¨aume und Netzwerke 315
Weg Ein (ungerichteter) Weg eines Graphen ist ein Pfad dieses Graphen, in dem alle
Knoten paarweise verschieden sind. Ein (gerichteter) Weg eines Graphen ist ein
Pfad dieses Graphen, in dem alle Knoten paarweise verschieden sind. Die L ¨ange
eines Weges ist n.
Zyklus / Kreis Ein (ungerichteter) Kreis ist ein Pfad (v 0,...,v n) f ¨ur den gilt, dass
{v0,vn}∈ E. Ein (gerichteter) Kreis ist ein Pfad ( v0,...,v n), n≥2, f¨ur den gilt,
dass (v0,vn) ∈E.
Beispiele:
1
2
3
4
6 9
8
7 10
115
Abb. B.4: Gerichteter Graph
Pfade: (1,5,1,4), (7), (3,6,9), . . .
Wege: (7), (3,6,9), . . .
Kreise: (5,8,7), (1,5)
a
b
c
d
e
f
g
h
Abb. B.5: Ungerichteter Graph
Pfade: (d,e,g,d,a), (f), (a,b) . . .
Wege: (f), (a,b), (b,c,e,g) . . .
Kreise: (a,b,d), (d,e,g), . . .
DAG Ein DAG (engl: Directed Acyclic Graph) bezeichnet einen gerichteten kreisfreien
Graphen.
Baum Ein kreisfreier, zusammenh ¨angender Graph. F ¨ur einen Baum G = (V,E ) gilt
immer, dass |E|= |V|−1.
Beispiel: Entfernt man etwa vom dem in Abbildung B.3 gezeigten ungerichteten
Graphen die Kanten {a,d}und {b,d}, so erh¨alt man einen Baum – wie im linken
Teil der Abbildung B.6 zu sehen. Der rechte Teil der Abbildung zeigt denselben
Graphen – nur so gezeichnet, dass er als Wurzelbaum mit Wurzelknotenagesehen
werden kann.
a c
e
d
bf
b
f
a
e
c
d
Abb. B.6:Das linke Bild zeigt den Graphen G3, der aus dem in Abbildung B.3 gezeigten
Graphen G2 nach Entfernen der Kanten {a,d} und {b,d} entstanden ist. Dieser Graph
ist ein Baum. Das rechte Bild zeigt denselben Graphen G3, der nun aber so gezeichnet
ist, dass er als Wurzelbaum mit Wurzelknoten a interpretiert werden kann.
Wurzelbaum In der Informatik werden B¨aume h¨auﬁg dazu verwendet, Informationen
so abzulegen, dass sie schnell wiedergefunden werden k ¨onnen. Hierbei handelt es
sich meist um sogenannte Wurzelb¨aume, in denen ein bestimmter Knoten als die
Wurzel des Baumes deﬁniert wird. Alternativ kann man einen Wurzelbaum auch
deﬁnieren als einen kreisfreien gerichteten Graphen, bei dem ein spezieller Knoten
als Wurzel gekennzeichnet ist.

## Seite 331

316 B Mathematische Grundlagen
H¨ohe eines Knotens (in einem Wurzelbaum) entspricht der L¨ange des l¨angsten
Pfades von diesem Knoten zu einem Blattknoten.
Spannbaum Als Spannbaum bezeichnet man einen Teilgraphen GT = (VT,ET) eines
ungerichteten zusammenh ¨angenden Graphen G = (V,E ), der ein Baum (also
kreisfrei und zusammenh¨angend) ist. Der Teilgraph muss alle Knoten des Graphen
enthalten, es muss also gelten: VT = V und ET = E. Abbildung B.7 zeigt ein
einfaches Beispiel eines Spannbaums (unter vielen M ¨oglichen).
e
g
f hd a
b
c c e
b
a d f h
g
Abb. B.7: Zwei verschiedene (von vielen m ¨oglichen) Spannb¨aume des in Abbildung B.5 ge-
zeigten Graphen, zu sehen in Form der fett gezeichneten Kanten.
Zusammenhang Ein ungerichteter Graph heißt zusammenh¨angend, wenn es f¨ur jedes
Knotenpaar i,j ∈V,i ̸= j einen Pfad von i nach j gibt.
Ein gerichteter Graph heißt schwach zusammenh ¨angend, wenn der zugrundelie-
gende ungerichtete Graph (den man einfach dadurch erh ¨alt, in dem man jede
Kante (i,j) durch eine entsprechende Kante {i,j}ersetzt) zusammenh¨angend ist.
Ein gerichteter Graph heißt stark zusammenh ¨angend (oder kurz einfach: zusam-
menh¨angend) wenn es f ¨ur jedes Knotenpaar i,j ∈V,i ̸= j einen Pfad von i nach
j gibt.
Beispielsweise ist der Abbildung B.4 gezeigte Graph zwar schwach zusammen-
h¨angend, nicht jedoch stark zusammenh ¨angend.
(Zusammenhangs-)Komponente Ein maximaler zusammenh¨angender Teilgraph ei-
nes ungerichteten Graphen G heißt Zusammenhangskomponente (oder oft auch
nur: Komponente).
Aufgabe B.7
Bestimmen Sie f¨ur obige Beispielgraphen:
(a) Γ(2) und deg(2)
(b) Γ(1) und deg(1)
B.5 Potenzmengen
Die Potenzmenge P(M) einer Menge M ist deﬁniert als die Menge aller Teilmengen
von M; formaler:
P(M) := {N |N ⊆M }

## Seite 332

B.5 Potenzmengen 317
Beispielsweise gilt, dass
P({1,2,3}) = {∅,{1},{2},{3},{1,2},{1,3},{2,3},{1,2,3}}
Wir wollen uns¨uberlegen, wie man die Potenzmenge eine MengeM in Python berechnen
kann; wir repr ¨asentieren hierbei Mengen als Listen. Systematisch kann man sich f ¨ur
das eben erw ¨ahnte Beispiel folgendes Vorgehen vorstellen: Zun ¨achst erzeugt man alle
Teilmengen, die die 1 nicht enthalten und danach alle Teilmengen, die die 1 enthalten,
also
P([1,2,3]) = [
=P([2,3])
  
[ ], [2], [3], [2,3]],
=
[1]+
−→P([2,3])
  
[1],[1,2],[1,3],[1,2,3]]
Man sieht, dass die erste H¨alfe genau dem Wert von P([2,3]) entspricht; auch die zweite
H¨alfte basiert auf den Werten aus P([2,3]), nur dass vor jeder der Teilmengen die
1 angef ¨ugt wird. Daraus ergibt sich sehr direkt folgende Python-Implemetierung der
Potenzmengen-Funktion:
1 def pot(l ):
2 if l==[]: return [[]]
3 return pot(l[1: ]) +map(lambda p: [l [0]] +p, pot(l [1: ]))
Aufgabe B.8
(a) Wieviele Elemente hat P(M)?
(b) Was ist der Wert von len(pot(pot(pot([0,1]))))?
B.5.1 Permutationen
Eine Permutation ist eine endliche bijektive Abbildung π: X →X; endliche bedeutet:
|X|<∞, d. h. X enth¨alt nur endlich viele Elemente; bijektiv bedeutet: f¨ur jedes xi ∈X
gibt es genau ein xj ∈X mit π(xi) = xj, d. h. es gibt eins-zu-eins-Verh¨altnisse zwischen
Bild- und einem Urbildwerten.
Da Permutationen endliche Abbildungen sind, k¨onnen sie durch Auﬂistung aller m¨ogli-
chen Bild-Urbild-Paare dargestellt werden. Angenommen X = {1,...n }, dann k ¨onnte
man eine Permutation folgendermaßen darstellen:
π=
(
1 2 ... n
π(1) π(2) ... π(n)
)
Ist klar und eindeutig, in welcher Reihenfolge die Bildwerte angeordnet werden k¨onnen,
so kann die erste Zeile auch weg gelassen werden.
Es gibt immer n!-viele verschiedene Permutation einer n-elementigen Menge. Dies kann
man mit folgender ¨Uberlegung einfach nachvollziehen: Nimmt man das erste Elemente

## Seite 333

318 B Mathematische Grundlagen
aus der Menge, so gibt es nverschiedene M¨oglichkeiten dieses zu platzieren (n¨amlich an
die Position 1 oder an die Position 2, usw.). Nimmt man anschließend das zweite Element
aus der Menge, so gibt es nochn−1 verschiedene M¨oglichkeiten, dieses zu platzieren. F¨ur
jede der nM¨oglichkeiten, das erste Element zu platzieren gibt es alson−1 M¨oglichkeiten,
das zweite Element zu platzieren, insgesamt also n·(n−1) M¨oglichkeiten, die ersten
beiden Elemente zu platzieren, usw. Also gibt es insgesamt n·(n−1) ·... ·1 = n!
M¨oglichkeiten die Elemente der n-elementigen Menge anzuordnen.
Mit Hilfe einer Listenkomprehension kann man relativ einfach eine Python-Funktion
schreiben, die die Liste aller Permutation einer Menge (in Python repr ¨asentiert als
Liste) zur¨uckliefert.
1 def perms(xs):
2 if xs == []: return [[]]
3 return [i for perm in perms(xs[1:]) for i in ins(xs [0], perm)]
Listing B.1: Implementierung einer Funktion perms, die die Liste aller Permutationen der
als Argument ¨ubergebenen Liste xs zur ¨uckliefert.
Hierbei wird eine Hilfsfunktion ins(x,xs) ben ¨otigt (siehe Aufgabe B.9), die die Liste
aller m¨oglichen Einf¨ugungen des Elements x in die Liste xs zur¨uckliefert.
Zeile 2 implementiert den Rekursionsabbruch: die einzige Permutation der leeren Liste
ist wiederum die leere Liste. Bei der Implementierung des Rekursionsschrittes erfolgt der
rekursive Aufruf perms(xs[1 :]), angewendet auf die k ¨urzere Liste xs [1 :]. Wir nehmen
an, der rekursive Auruf arbeitet korrekt – diese Annahme geh ¨ort zu der in Abschnitt
1.2.1 besprochenen Denk-Strategie f¨ur die Programmierung rekursiver Funktionen. Un-
ter dieser Annahme fragen wir uns, wie wir die ”kleinere“ L¨osung perms(x[1 :]) anrei-
chern m¨ussen, um perms(xs) zu erhalten. Wir betrachten das in Abbildung B.8 gezeigte
Beispiel: Um aus den Permutationen der Elemente aus [2,3] die Permutationen der Ele-
mente aus [1, 2,3] zu erhalten, muss mittels der Funktion ins das erste Element – in
diesem Fall ist das die ”1“ – in jede Position jeder Permutation eingef ¨ugt werden. Dies
perms([2,3]) = [2,3] [3,2]
⇓ ⇓
ins(1,[2,3]) ins(1,[3,2])
perms([1,2,3]) =
⇓

 
[1,2,3] [2, 1,3] [2, 3,1]
⇓
  
[1,3,2] [3, 1,2] [3, 2,1]
Abb. B.8: Konstruktion von perms([1,2,3]) – der Liste aller Permutationen der Elemente
aus [1,2,3] – aus perms([1,2]): Auf jedes Element aus perms([2,3] wird einfach ins(1,...)
ausgef¨uhrt; alle daraus entstehenden Listen bilden die Permutationen aus [1,2,3].
wird durch die in Zeile 3 in Listing B.1 gezeigte Listenkomprehension implementiert.
Die Variable perm l¨auft ¨uber alle Permuationen von xs [1 :]; f ¨ur jede dieser Permutatio-
nen l¨auft die Variable i ¨uber alle Einf ¨ugungen des ersten Elements von xs. Alle diese
”Einf¨ugungen“ zusammengenommen ergeben die Liste aller gesuchten Permutationen.

## Seite 334

B.5 Potenzmengen 319
Aufgabe B.9
Implementieren Sie die Funktion ins(x,xs), die die Liste aller m¨oglichen Einf¨ugungen
des Elements x in die Liste xs zur¨uckliefert. Beispielanwendung:
>>>ins(1, [ 2,3,4,5 ])
>>> [ [ 1,2,3,4,5 ], [ 2,1,3,4,5 ], [ 2,3,1,4,5 ], [ 2,3,4,1,5 ], [ 2,3,4,5,1 ] ]
Tipp: Am einfachsten geht eine rekursive Implementierung. Es empﬁehlt sich auch
die Verwendung einer Listenkomprehension.
Aufgabe B.10
Implementieren Sie zwei Test-Funktionen, die (teilweise) ¨uberpr¨ufen k¨onnen, ob die
Implementierung der in Listing B.1 korrekt war.
(a) Eine Funktion allEqLen(xss) die ¨uberpr¨uft, ob alle in der als Argument ¨uberge-
benen Liste xss enthaltenen Listen die gleiche L ¨ange haben.
(b) Eine Funktion allEqElems(xss) die ¨uberpr¨uft, ob alle in der als Argument ¨uber-
gebenen Liste xss enthaltenen Listen die selben Elemente enthalten.
B.5.2 Teilmengen und Binomialkoeﬃzient
Wie viele k-elementige Teilmengen einer n-elementigen Menge gibt es? Dies ist eine
h¨auﬁge kombinatorische Fragestellungen, die entsprechend h¨auﬁg auch bei der Entwick-
lung von Optimierungs-Algorithmen auftaucht – bei der Entwicklung eines Algorithmus
zur L¨osung des Travelling-Salesman-Problems beispielsweise (siehe Kapitel 8.1.2 auf Sei-
te 238).
Man kann sich wie folgt¨uberlegen, wie vielek-elementige Teilmengen einern-elementigen
Menge es gibt. Betrachten wir zun ¨achst eine verwandte und einfachere Fragestellung:
Wie viele k-elementige Tupel aus einer n-elementigen Teilmenge gibt es? – Tupel sind,
im Gegensatz zu Mengen, geordnet, d. h. die Reihenfolge, in der sich die Elemente inner-
halb eines Tupels beﬁnden, spielt eine Rolle. F¨ur die erste zu besetzende Position haben
wir noch nm¨ogliche Elemente zur Wahl; f¨ur die zweite Position haben wir nur nochn−1
Elemente zu Auswahl, usw. Insgesamt gibt es alson·(n−1)·... ·(n−k+1) = n!/(n−k)!
viele m¨ogliche k-Tupel. Da jedes Tupel auf k! viele Arten angeordnet werden kann, ent-
sprechen immer genau k! viele Tupel einer k-elementigen Teilmenge. Insgesamt gibt
es also n!/k!(n−k)! viele k-elementige Teilmengen einer n-elementigen Menge. Genau
diese Zahl nennt man den Binomialkoeﬃzienten und schreibt daf¨ur
(n
k
)
:= n!
k!(n−k)! = Anz. k-elementiger Teilmengen einer n-elem. Menge
F¨ur
(n
k
)
spricht man auch ”n ¨uber k“.

## Seite 335

320 B Mathematische Grundlagen
Es gibt eine rekursive Formel, mit der man den Binomialkoeﬃzienten ohne Verwendung
der Fakult¨atsfunktion berechnen kann. Diese rekursive Formel kann man sich durch fol-
gende kombinatorische ¨Uberlegung herleiten. Die k-elementigen Teilmengen aus der
n-elementigen Menge lassen sich aufteilen in zwei Klassen:
1. All die Teilmengen, die das Element ”1“ enthalten. Diese Teilmengen bestehen al-
so aus ”1“ und einer (k −1)-elementigen Teilmenge der (n −1)-elementigen Menge
{2,...,n }. Davon gibt es genau
(n−1
k−1
)
viele.
2. All die Teilmengen, die das Element ”1“ nicht enthalten. Diese Teilmengen sind also
alle k-elementige Teilmengen der (n−1)-elementigen Menge {2,...,n }. Davon gibt es
genau
(n−1
k
)
viele.
Diese beiden Klassen sind ¨uberschneidungsfrei (disjunkt) und daher ist die Anzahl der
k-elementigen Teilmengen einer n-elementigen Menge genau die Summe der Elemente
der ersten und der zweiten Klasse, d. h. es gilt folgende rekursive Gleichung:
(n
k
)
=
(n−1
k−1
)
+
(n−1
k
)
(B.1)
Diese ¨Uberlegung war konstruktiv: Es ist m ¨oglich sich daraus einen Algorithmus ab-
zuleiten. Die in folgendem Listing B.2 gezeigte Implementierung erzeugt gem ¨aß obiger
¨Uberlegung alle k-elementigen Teilmengen der ¨ubergebenen Liste lst :
1 def choice( lst ,k):
2 if lst == []: return []
3 if len( lst ) == k: return [lst]
4 if len( lst ) ≤ k or k==0: return [[]]
5 return [[ lst [0] ] +choices for choices in choice( lst [1: ], k -1)] +choice( lst [1: ], k)
Listing B.2: Implementierung der Funktion choice, die eine Liste aller k-elementigen Teil-
mengen der Elemente aus lst zur ¨uckliefert.
Genau wie Gleichung B.1 enth ¨alt auch die Funktion choice( lst ,k) zwei rekursive Auf-
rufe die jeweils die um Eins kleinere Liste lst [1 :] verwenden: choice( lst [1 :], k -1) und
choice( lst [1 :], k).

## Seite 336

Literaturverzeichnis
[1] German stoppwords. http://solariz.de/download-7, April 2010.
[2] Burton H. Bloom. Space/time trade-oﬀs in hash coding with allowable errors.
Communications of the ACM, 13(7):422–426, 1970.
[3] Robert S. Boyer and Strother Moore. A fast string searching algorithm. Commu-
nications of the ACM, 20(10), Oktober 1977.
[4] Andrei Broder and Michael Mitzenmacher. Network applications of bloom ﬁlters:
A survey. Internet Mathematics, 1(4):485–509, 2005.
[5] Fay Chang, Jeﬀrey Dean, Sanjay Ghemawat, Wilson C. Hsieh, Deborah A. Wal-
lach, Mike Burrows, Tushar Chandra, Andrew Fikes, and Robert E. Gruber. Big-
table: A distributed storage system for structured data. 7th Conference on Usenix
Symposium on Operating Systems Design and Implementation , 9, 2006.
[6] Richard Cole and Ramesh Hariharan. Tighter upper bounds on the exact comple-
xity of string matching. SIAM J. Comput. , 26(3):803–856, 1997.
[7] Jeﬀrey Dean and Sanjay Ghemawat. Mapreduce: Simpliﬁed data processing on
large clusters. In OSDI,Sixth Symposium on Operating System Design and Imple-
mentation, pages 137–150, 2004.
[8] M. L. Fredman, R. Sedgewick, D. D. Sleator, and R. E. Tarjan. The pairing heap:
a new form of self-adjusting heap. Algorithmica, 1(1):111–129, 1986.
[9] Michael Fredman and Robert Tarjan. Fibonacci heaps and their uses in improved
network optimization algorithms. Journal of the ACM , 34(3):596–615, 1987.
[10] C.A.R. Hoare. Quicksort. Computer Journal, 5(1):10–15, 1962.
[11] Richard M. Karp. Reducibility among combinatorial problems. In R. E. Miller
and J. W. Thatcher, editors, Complexity of Computer Computations , pages 85–
103. New York: Plenum, 1972.
[12] Donald E. Knuth. The Art of Computer Programming. Vol. 3: Sorting and Sear-
ching. Addison-Wesley, second edition, 1998.
[13] The Lucene Webpages. lucene.apache.org.
[14] Fredrik Lundh. Python hash algorithms. http://eﬀbot.org/zone/python-hash.htm,
2002.

## Seite 337

322 Literaturverzeichnis
[15] Rob Pike, Sean Dorward, Robert Griesemer, and Sean Quinlan. Interpreting the
data: Parallel analysis with sawzall. Scientiﬁc Programming, 13(4):277–298, 2005.
[16] William Pugh. Skip lists: a probabilistic alternative to balanced trees. Communi-
cations of the ACM , 33(6), June 1990.
[17] Gaston H. Gonnet Ricardo A. Baeza-Yates. A new approach to text searching.
Communications of the ACM, 35(10):74–82, Oktober 1992.
[18] Jean Vuillemin. A data structure for manipulating priority queues. Communicati-
ons of the ACM , 21:309–314, 1978.
[19] John Zelle. Python Programming: An Introduction to Computer Science. Franklin
Beedle & Associates, Dezember 2003.

## Seite 338

Index
O(n), 2
Ord(n), 135
P, 4
P-NP-Problem, 6
Γ, 314
Ω, 309
Ω(n), 2
β, 77
... ∗-Operation, 186
NP, 5
ε, 185
deg, 314
k-Opt-Heuristik, 246
¨Uberladung, 269
AVLTree.
balance, 61
AVLTree. calcHeight, 58
AVLTree. doubleLeft, 62
AVLTree. simpleLeft, 61
AVLTree.insert, 59
BTree.deleteND, 55
BTree.insert, 53
BTree.search, 52
BloomFilter.insert, 87
Grammatik. addP, 191
Grammatik.automaton, 205
Grammatik.ﬁrstCalc, 194
Grammatik.followCalc, 196
Grammatik.goto, 204
Grammatik.huelle, 204
Grammatik.parse, 211
Grammatik.tabCalc, 209
Graph.E, 151
Graph.V, 151
Graph.addEdge, 151
Graph.isEdge, 151
Index.addFile, 111
Index.ask, 111
Index.crawl, 111
Index.toIndex, 111
KMP, 219
OurDict.
insert, 82
OurDict. lookup, 81
OurDict. resize, 84
Patricia. insert, 106
Patricia.search, 105
RBTree. balance, 66
RBTree. insert, 66
RBTree.insert, 66
SkipList .search, 94
SkipListe. delete, 97
SkipListe. insert, 95
TSPBruteForce, 238
Trie. insert, 103
Trie.search, 102
UF.ﬁnd, 176
UF.union, 176
VerschTab, 221
acoCycle, 263
adaptGlobal, 265
allCrossTours, 254
allCrosses, 251
ant, 261, 265
bfs (Breitensuche), 153
boyerMoore, 228
buildHeap (bin¨arer Heap), 42
decKey (Fibonacci-Heap), 137
dfs (Tiefensuche), 156
dijkstra , 163
edgeCrossOver, 256
extractMinND (Pairing-Heap), 144
extractMin (Fibonacci-Heap), 135
fullAddB, 124
getMinFH (Fibonacci-Heap), 131
getMin (Pairing-Heap), 143
hashStrSimple, 73
hashStr, 75
heapSort, 43
horner, 74

## Seite 339

324 Index
if-Ausdruck, 274
insND(l,key), 17
insND, 18
insertionSortRek, 18
insertionSort, 19
insert (Bin¨arer Heap), 37
insert (Fibonacci-Heap), 132
kruskal, 172
makedelta1, 223
match (Stringmatching), 214
maxFlow, 180
meltBinTree, 123
mergeSort, 34
merge (Binomial-Heaps), 126
merge (Pairing-Heap), 144
minExtractB (Binomial-Heaps), 127
minExtrakt (Bin¨arer Heap), 38
minHeapify (bin¨arer Heap), 40
nodeCrossOver, 255
pairmerge (Pairing-Heap), 144
partitionIP, 27, 28
quickSortIP, 28
quickSortIter, 31
quicksort, 24
rabinKarp, 231
rollhash, 230
shiftOr, 234
topSort (Topologische Sortierung), 160
tsp2Opt, 247
tsp2
5Opt, 249
tspGen, 257
tspMelt, 244
tspRandomInsertion, 243
tsp, 239
vapourize, 262
warshall, 166
s-t-Schnitt, 183
2-Opt-Heuristik, 246
2.5-Opt-Heuristik, 248
3-KNF, 6
3SAT, 6
Ableitung, 187
Ableitungsschritt, 187
ACO, 258
ACO-Zyklus, 262
Adelson-Welski, Georgi, 57
adjazent, 149
Adjazenzliste, 149
Adjazenzmatrix, 149
Agent, 259
Aktionstabelle, 208
All Pairs Shortest Paths, 162
Alphabet, 185
Ameisen-Algorithmen, 258
Amortisationsanalyse, 220
Amortisierte Laufzeit, 4
anonyme Funktion, 290
Ant Colony Optimization, 258
anti-symmetrisch, 304
Anweisung, 273
Anweisung vs. Ausdruck, 273
Ausdruck, 273
Ausf¨uhrungszeit, 83
Average-Case-Laufzeit, 4
AVL-Baum, 57
Implementierung
AVLTree.
balance, 61
AVLTree. calcHeight, 58
AVLTree. doubleLeft, 62
AVLTree. simpleLeft, 61
AVLTree.insert, 59
Backtracking, 156, 257
Bad-Character-Heuristik, 221
Bad-Charakter-Heuristik
Implementierung
badChar, 223
makedelta1, 223
balancierter Baum, 63
Baum, 315
Belegungsgrad β einer Hash-Tabelle, 77
Bellmannsches Optimalit¨atsprinzip, 238
benannter Parameter, 51, 275, 297
Bernoulli-Verteilung, 313
bin¨are Suche, 21
bin¨are Und-Verkn¨upfung, 229
Bin¨arer Heap, 116
Einf¨ugen eines Elements, 36
H¨ohe, 36
Implementierung
buildHeap, 42
insert, 37, 117
minExtract, 118

## Seite 340

Index 325
minExtrakt, 38
minHeapify, 40, 118
Repr¨asentation, 34, 116
Bin¨arer Suchbaum, 49
Implementierung
BTree.deleteND, 55
BTree.insert, 53
BTree.search, 52
Binomial-Heap, 119
Implementierung
fullAddB, 124
meltBinTree, 123
merge, 126
minExtractB, 127
Ordnung, 120
Binomialkoeﬃzient, 239
Binomialverteilung, 313
Bit-Maske, 80
Bloomﬁlter, 85
Implementierung, 87
BloomFilter.elem, 87
BloomFilter.insert, 87
L¨osch-Funktion, 88
BloomFilter.elem, 87
Breitensuche
Implementierung
bfs, 153
British Library, 47
Brute-Force, 237
Buchstabe, 185
Cache-Speicher, 112
Carry-Bit, 123
Chache, 92
charakteristischer Vektor, 232
Clique-Problem, 6
Clusterung (beim einfachen Hashing),
78
Countingﬁlter, 88, 89
L¨osch-Funktion, 89
Crawler, 109
Cross-Over zweier L¨osungen (Kreuzung),
255
d¨unn besetzt, 149
DAG, 315
Data Mining, 185
Datenbank, 47
Datenmengen (Vergleich), 47
Datenstruktur
AVL-Baum, 57
Bin¨arer Heap, 116
Bin¨arer Suchbaum, 49
Binomial-Heap, 119
Bloomﬁlter, 85
Fibonacci-Heap, 127
Graph, 147, 149
Hashtabelle, 72
Heap, 115
Pairing-Heap, 142
Patricia, 100
Rot-Schwarz-Baum, 63
Skip-Listen, 93
Trie, 100
Datentypen, 267
205
Dichte einer Zufallsvariablen, 311
Dictionary-Operationen, 72, 283
Dijkstra, Edsger, 162
Dijkstra-Algorithmus, 162
Implementierung
dijkstra , 163
disjunkt, 174
Divide-And-Conquer, 22
Doppelrotation, 59
doppeltes Hashing, 78
dynamic dispatch, 100
dynamisch, 83
dynamische Typisierung, 268
einfaches Hashing, 78
Einfachrotation, 59
Einr¨ucktiefe, 270
Elementarereignis, 309
Emergenz, 259
Endrekursion, 31
Entscheidungsbaum, 21
Ereignis, 310
Erf¨ullbarkeitsproblem, 6
Erfolgswahrscheinlichkeit, 313
Erwartungswert, 312
Erweiterungspfad, 180
Deterministischer endlicher Automat, 214
Deterministischer endlicherAutomat(DEA),

## Seite 341

326 Index
erzeugte Sprache, 187
Evolution, 255
Fakult¨atsfunktion, 7
falsch-positiv, 86
Farthest-Insertion-Heuristik, 242
Fibonacci, 307
Fibonacci-Baum, 128
Ordnung, 128
Fibonacci-Heap, 127
Implementierung
decKey, 137
extractMin, 135
getMinFH, 131
insert, 132
FIFO-Datenstruktur, 152
ﬁrst-in, ﬁrst-out, 152
Fluss in einem Netzwerk, 178
Flusserhaltung, 179
Ford-Fulkerson Algorithmus, 180
Ford-Fulkerson-Algorithmus, 179
Implementierung
maxFlow, 180
funktionale Programmierung, 287
Ganzzahlen (int in Python), 267
Gegenwahrscheinlichkeit, 89
Generation, 255
Genetischer Algorithmus, 255
Genpool, 255
Geometrische Verteilung, 313
Gesetz der Flusserhaltung, 179
getrennte Verkettung, 77
Gewichtsfunktion w, 161
Gleitpunktzahlen (ﬂoat in Python), 267
globales Optimum, 246
Goldener Schnitt, 308
Good-Suﬃx-Heuristik, 221, 224
Google, 47
Grad eines Knotens, 314
Grammatik
Implementierung
Grammatik.
addP, 191
Grammatik.automaton, 205
Grammatik.ﬁrstCalc, 194
Grammatik.followCalc, 196
Grammatik.huelle, 204
Grammatik.parse, 211
Grammatik.tabCalc, 209
Graph, 147
Implementierung
Graph.E, 151
Graph.V, 151
Graph.addEdge, 151
Graph.isEdge, 151
Pfad in. . . , 314
Repr¨asentation, 149
Weg in . . . , 315
Zusammenhang, 316
Zusammenhangskomponente, 316
Zyklus in . . . , 315
Greedy-Algorithmus, 162
Greedy-Heuristiken, 241
Groß-Oh-Notation, 1
Hohe eines Knotens (in einer Skip-Liste),¨
93
Halteproblem, 83
Handlungsreisender, 237
Hash-Funktion, 72
Hash-Tabelle, 72
Hashing, 72
doppeltes Hashing, 78
einfaches Hashing, 78
getrennte Verkettung, 77
Kollisionsbehandlung, 77
Haskell (Programmiersprache), 198
Heap, 34, 115
Heap Sort
Implementierung
heapSort, 43
Heap-Eigenschaft, 34
Heapsort, 34
Heuristik, 241
Heuristiken
k-Opt-Heuristik, 246
2-Opt-Heuristik, 246
2.5-Opt-Heuristik, 248
Farthest-Insertion-Heuristik, 242
Greedy, 241
Kanten-Cross-Over, 255
Knoten-Cross-Over, 255
lokale Verbesserung, 246
Nearest-Insertion-Heuristik, 242

## Seite 342

Index 327
Nearest-Neighbor-Heuristik, 241
Random-Insertion-Heuristik, 242
Tourverschmelzung, 244
Hintereinanderausf¨uhrung, 274
Hoare, C.A.R, 27
Horner-Schema, 74, 230, 294
Implementierung
horner2, 75
horner, 75
horner2, 75
IDLE, 267
imperative Programmierung, 287
Implementierung
destruktiv, 13
in-place, 13
nicht-destruktiv, 13
rekursiv, 7
Implementierungen
minExtract, 38
in-place, 19
Index, 109
Indexer, 109
Induktionsanfang, 306
Induktionshypothese, 306
Induktionsschritt, 306
Information Retrieval, 47, 108
Insertion Sort, 17
Implementierung
insND, 18
insertionSortRek, 18
insertionSort, 19
in-Place, 19
Laufzeit, 19
nicht-destruktiv, 17
Interpreter, 267
invertierter Index, 109
Iteration vs. Rekursion, 7
k¨urzeste Wege, 162
Kanten, 147, 314
Kanten eines Schnittes, 183
Kanten-Cross-Over, 255
kantenbewerteter Graph, 161
Kapazit¨at, 178
Kapazit¨at eines Schnittes, 183
Kirchhoﬀ’sches Gesetz, 179
Klasse, 298
Klassen
-instanzen, 299
-methoden, 298
ini -Methode, 299
Klassenattribut, 300
Klassendeﬁnitionen
AVLTree, 58
BTree, 50
BloomFilter, 87
Grammatik, 191
Graph, 150
Index, 111
OurDict, 79
Patricia, 104
RBTree, 63
SLEntry, 94
SkipList, 94
Trie, 102, 106
UF (Union-Find), 176
string, 76
Knoten, 147, 314
Knoten-Cross-Over, 255
Knuth-Morris-Pratt-Algorithmus, 216
Implementierung
KMP, 219
VerschTab, 221
Kollisionsbehandlung, 77
Komplexit¨atsklasse, 4
Komponente, 316
Konjunktive Normalform, 6
Konkatenation, 269
kostengunstigster Verbindungsgraph, 169¨
Kreis, 315
Kreiseigenschaft, 171
Kreuzprodukt, 303
Kreuzung von L ¨osungen (Cross-Over),
255
Kruskal-Algorithmus
Implementierung, 172
kruskal, 172
Korrektheit, 170
L¨ange eines Pfades, 314
L¨ange eines Weges, 315
Lambda-Ausdruck, 290
Landau-Symbole, 1

## Seite 343

328 Index
Landis, Jewgeni, 57
lange Ganzzahlen (long int in Python),
267
last-in, ﬁrst-out, 154
leere Menge, 303
leeres Wort ε, 185
Leonardo da Pisa, 307
lexikalische Suche, 108
LIFO-Datenstruktur, 154
Linksrekursion, 201
Listenkomprehension, 288
lokale Verbesserungsstrategien, 246
lokales Optimum, 246
Maske, 80
mathematische Tupel, 303
Matrix
d¨unn besetzt, 149
Max-Flow-Min-Cut-Theorem, 182
Max-Heap, 34
Max-Heap-Eigenschaft, 34
Maximaler Fluss, 178
Mehrdeutigkeit einer Grammatik, 188
Membership-Test, 85
Menge, 303
Mengenkomprehension, 288, 303
Mergesort, 33
merging, 33
Metasymbol (Nichtterminal), 186
Methode, 298
Min-Heap, 34
Min-Heap-Eigenschaft, 34
minimaler Schnitt, 183
minimaler Spannbaum, 169
Minimumsextraktion, 38
Mutation, 246
Nachbarschaft eines Knotens, 314
Navigationssystem, 162
NEA (=Nichtdeterministischer endlicher
Automat), 232
Nearest-Insertion-Heuristik, 242
Nearest-Neighbor-Heuristik, 241
Netzwerk, 178
Kapazit¨at, 178
NFA (nichtdeterministischer endlicher Au-
tomat, 214
Nicht-Determinismus, 5
nichtdeterministische Rechenmaschine, 5
nichtdeterministischer endlicher Automat,
232
Nichtdeterministischer endlicher Auuto-
mat, 214
Nichtterminal(-symbol), 186
NoSQL, 91
Objekt, 299
Objektattribut, 300
objektorientierte Programmierung, 298
Optimalit¨atsprinzip, 238
Ordnung
Binomial-Heap, 120
Fibonacci-Baum, 128
Pairing-Heap, 142
Implementierung
extractMinND, 144
getMin, 143
merge, 144
pairmerge, 144
Parsergenerator, 185, 197
Parsing, 185
Patricia, 100
Implementierung
Patricia. insert, 106
Patricia.search, 105
perfekte Zahl, 272
Permutation, 238
Persistenz, 114
Pfad, 314
L¨ange, 314
Pfadkomprimierung, 177
Pheromon, 259
Pheromonspur, 259
Pivot-Element, 23
Polymorphie, 269
polynomieller Algorithmus, 4
Potential-Funktion, 131
Potentialmethode (zur amortisierten Lauf-
zeitanalyse), 4
pr¨adiktive Grammatik, 198
pr¨adiktives Parsen, 198
Pr¨aﬁx, 216
praktisch l¨osbarer Algorithmus, 4

## Seite 344

Index 329
Priorit¨atswarteschlange, 35, 115
Priority Search Queue, 35
Problem des Handlungsreisenden, 237
Problemgr¨oße, 2
Produktion, 187
Programmstack, 8
Proxy, 92
Python-Referenzen, 276
Pythondatentypen
complex, 267
dict, 283
ﬂoat , 267
int, 267
list , 277
long, 267
str, 268, 285
tuple, 282
Pythonfunktionen
all , 292
any, 292
del, 280
dict .items(), 284
dict .keys(), 284
dict .values(), 284
dir, 278
enumerate, 292
len, 280
list .count, 277
map, 291
max, 280
min, 280
range, 272
reduce, 293
str . capitalize , 285
str .endswith, 285
str . ﬁnd, 285
str . join, 285
str .lower, 285
str . partition, 285
str . replace, 285
str . split , 285
str . startswith , 285
str .upper, 285
sum, 280
Pythonkommandos
break, 272
continue, 272
def, 274
elif, 270
for, 270
if-Ausdruck, 274
list .append, 277
list . insert, 277
list .remove, 277
list . reverse, 277
list . sort, 277
return, 275
while, 270
Pythonmethoden
cmp , 301
getitem , 301
ini , 301
len , 301
setitem , 301
str , 301
Pythonmodule
heapq, 44
marshal, 114
pickle, 114
pygeodb, 242
random, 30
shelve, 114
time, 30
Pythonoperatoren, 269
*, 270
+, 270
-, 270
/, 270
<<, 270
<, 270
==, 270
≫, 270
>, 270
%, 270
&, 270
ˆ, 270
˜, 270
and, 270
in, 270
is, 270
not, 270
or, 270
Pythonshell, 267
Pythonvariablen

## Seite 345

330 Index
lokale, 275
Quelle (Netzwerk), 178
Queue, 152
dequeue-Operation, 152
enqueue-Operation, 152
Quicksort, 22
Implementierung
mergeSort, 34
partitionIP, 28
quicksortIP, 28
quicksortIter , 31
quicksort, 24
in-Place, 27
Randomisiert, 29
Random-Insertion-Heuristik, 242
randomisierte Datenstruktur, 93
Read-Eval-Print-Loop (REPL), 267
Rechtsableitung, 202
reﬂexiv, 304
Rekursion, 6
‘Kochrezept’, 12
Rekursionsabbruch, 10
Rekursionsschritt, 12
rekursive Funktion, 6
rekursiver Abstieg, 8
rekursiver Aufstieg, 8
Relation, 304
REPL (Read-Eval-Print-Loop), 267
Repr¨asentation von Datenstrukturen, 14
Repr¨asentation als Dictionary, 15
Repr¨asentation als Klasse, 15
Repr¨asentation als Liste, 15
Restnetzwerk, 180
Retrieval, 47
Rollender Hash, 229
Rot-Schwarz-Baum, 63
Einf¨ugen eines Knotens, 64
Implementierung
RBTree.
balance, 66
RBTree.insert, 66
L¨oschen eines Knotens, 69
Rotation, 59
Routenplanung, 162
Routing-Tabelle, 100
Rucksack-Problem, 6
Satzform, 188
Schl¨ussel, 49
Schleife
Python:for, 270
Python:while, 270
Schleifenabbruch, 272
Schleifeninvariante, 43
Schleifenkopf, 273
Schnitt
s-t-Schnitt, 183
minimaler Schnitt, 183
Kanten eines Schnittes, 183
Kapazit¨at eines Schnittes, 183
Schnitt in einem Graphen, 182
Schnitteigenschaft, 172
schwach zusammenh¨angend, 316
Schwarm-Intelligenz, 259
semantische Suche, 108
Semaphore, 162
Senke, 178
Sequenzoperationen (in Python), 280
Shift-Or-Algorithmus, 232
Sierpinski-Dreieck, 12
Skelettautomat, 215
Skip-Liste, 93
H¨ohe, 93
H¨ohe eines Knotens, 93
Implementierung
SkipList . delete, 97
SkipList . insert, 95
SkipList .search, 95
Vorw¨artszeiger, 93
Slicing (in Python), 279
Sortieren, 17
Spannbaum, 169, 316
Sprache, 186
Springerproblem, 157
Sprungtabelle, 208
Stack, 8
pop-Operation, 154
push-Operation, 154
Stack Overﬂow, 8
Stackframe, 30
Stapelspeicher, 154
stark zusammenh¨angend, 316
Startsymbol (einer Grammatik), 186
statisch, 83

## Seite 346

Index 331
statische Typisierung, 268
Stemming, 109
Stoppwort, 114
Stringmatching, 213
Strings in Python, 268, 285
""". . .""", 268
". . .", 268
'. . .', 268
'''. . .''', 268
Suchmaschine, 108
Aufbau, 108
Implementierung, 108
symmetrisch, 304
Syntaxanalyse, 185
Syntaxanalysetabelle, 208
Syntaxbaum, 188
Syntaxbeschreibungsformalismen, 270
[. . . ], 270
[. . . ]*, 270
tail recursion, 31
Terminal(-symbol), 186
Tiefensuche, 154
Implementierung
dfs, 156
Top-Down-Parser, 197
Topologische Sortierung, 159
Implementierung
topSort, 160
Tourverschmelzung, 244
transitiv, 304
transitive H¨ulle, 167, 305
Travelling-Salesman-Problem, 6, 237
Trie, 100
Implementierung
Trie. insert, 103
Trie.search, 102
Tupel (in der Mathematik), 303
Tupel (in Python), 277, 282
Turingmaschine, 5
nicht-deterministisch, 5
Typ-2-Grammatik, 186
Typ-2-Sprache, 185, 188
Typ-3-Sprache, 185
Typisierung
dynamisch, 268
statisch, 268
Unabh¨angigkeit von Zufallsereignissen,
310
Und-Verkn¨upfung, 229
Union-Find-Operationen, 174
Balancierung, 176
Implementierung
UF.ﬁnd, 176, 177
UF.union, 176
Pfadkomprimierung, 177
Usability, 112
Variable (Nichtterminal), 186
Vereinigungs-Suche, 174
Vererbung, 300
Verschiebetabelle, 217
Verteilung einer Zufallsvariablen, 311
Vollst¨andige Induktion, 306
Vorw¨artszeiger einer Skip-Liste, 93
Wahrscheinlichkeitsraum, 309
Warshall-Algorithmus, 165
Implementierung
warshall, 166
Wartbarkeit von Programmen, 273
Warteschlange, 152
Web-Cache, 92
Web-Proxy, 92
Weg, 315
L¨ange, 315
Worst-Case-Laufzeit, 4
Wort, 186
Wurzelbaum, 315
Yacc, 185, 197
Zufallsvariable, 311
zusammengesetzte Datentypen, 277
zusammenh¨angender Graph, 316
Zusammenhangskomponente, 316
Zyklus, 315
