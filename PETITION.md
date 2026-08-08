# Petition: an open local interface for the BORA dryer

**English summary — the German text below is the actual petition to Roth-Kippe.**

The Roth-Kippe BORA is a great dryer with a WLAN interface that, today, can only
be *read*. There is no documented way to start or stop a program, choose a cycle,
or reset the filter counter over the network. This petition asks Roth-Kippe to
publish a small, local control API so the BORA can become a genuinely smart
appliance — no cloud required.

### How to sign

If you own a BORA and want an open interface:

1. 👍 React with a thumbs-up on the pinned issue:
   **[» Petition: Open local API for the BORA dryer «](https://github.com/chriguschneider/hass-bora-dryer/issues/4)**
2. Optionally add a one-line comment with your **model and firmware version**
   (from the `Firmware version` sensor, or `http://<bora-ip>/info.html`).

That's it. Every signature is one more owner telling Roth-Kippe this matters.

---

## Offener Brief an die Roth-Kippe AG

**Betrifft: Offene lokale Schnittstelle für die BORA Raumluft-Wäschetrockner**

Sehr geehrte Damen und Herren

Wir sind Besitzerinnen und Besitzer eines BORA-Raumluft-Wäschetrockners und
begeistert von der Qualität und Effizienz Ihrer Geräte. Genau deshalb wenden wir
uns mit einem gemeinsamen Anliegen an Sie.

Die BORA verfügt bereits über eine WLAN-Schnittstelle. Aktuell lässt sich darüber
jedoch **nur der Status auslesen** — Betriebszustand, Temperatur, Luftfeuchte und
Filter-Stunden. Eine **Steuerung** (Programmwahl, Start/Stopp, Zurücksetzen des
Filterzählers) über das Netzwerk ist nicht vorgesehen.

Wir möchten Sie ermutigen, einen kleinen, **dokumentierten lokalen
Steuerungs-Zugang** anzubieten. Damit würde die BORA zu einem vollwertigen
Smart-Home-Gerät — ganz ohne Cloud, ohne Konto, ohne Abhängigkeit von einem
Hersteller-Server. Konkret wünschen wir uns:

1. **Eine lokale Steuer-Schnittstelle** (z. B. eine einfache HTTP-API) für
   Programmwahl, Start/Stopp und das Zurücksetzen des Filterzählers.
2. **Eine kurze Dokumentation** dieser Schnittstelle, damit Integrationen für
   offene Plattformen wie Home Assistant oder Matter entstehen können.
3. **Optional:** eine grundlegende Absicherung der Schnittstelle (die heutige
   Weboberfläche ist unauthentifiziert und zeigt u. a. das WLAN-Passwort im
   Klartext).

Der Nutzen ist konkret und alltagsnah:

- **Wäsche starten, wenn die eigene Photovoltaik Überschuss liefert** — der
  Trockner läuft mit selbst produziertem Strom statt aus dem Netz.
- **Betrieb in günstige Stromtarif-Fenster verschieben** (dynamische Tarife).
- **Filter-Erinnerung und -Reset automatisieren**, ohne Gang in den Keller.
- **Fertig-Meldung aufs Handy** und Einbindung in bestehende Haus-Automationen.

Als Vorleistung existiert bereits eine quelloffene, rein lesende Home-Assistant-
Integration für die BORA, die von mehreren Besitzern genutzt wird:
<https://github.com/chriguschneider/hass-bora-dryer>. Sie zeigt, dass das
Interesse real ist — es fehlt nur der schreibende Zugang.

Ein offenes, lokal steuerbares Gerät ist heute ein echtes **Verkaufsargument**
bei technisch interessierten Kundinnen und Kunden — und kostet Sie im Betrieb
nichts, da alles lokal und ohne Server-Infrastruktur läuft. Wir bringen unsere
Vorarbeit und Erfahrung gerne ein.

Über eine Rückmeldung — auch eine ablehnende — freuen wir uns sehr.

Freundliche Grüsse
**Die unterzeichnenden BORA-Besitzerinnen und -Besitzer**

*Unterschriften siehe verlinktes GitHub-Issue.*

---

## For the maintainer — how this petition runs

GitHub has no built-in "petition" feature, so a **pinned issue** serves as the
signature sheet:
[issue #4](https://github.com/chriguschneider/hass-bora-dryer/issues/4) carries
the German open letter as its body and is pinned in the repo — `👍` reactions and
comments are the signatures.

When there is a meaningful number of signatures, send Roth-Kippe a short mail
linking the issue so they see the demand is real and quantified.
