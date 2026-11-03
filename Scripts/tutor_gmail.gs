/**
 * tutor_gmail.gs — Espone al tutor del vault i post del forum Moodle "Diario delle lezioni" che arrivano per email
 * nella Gmail della Sapienza. Legge solo quelle email e risponde solo a chi conosce il codice.
 *
 * Installazione (una volta, con l'account della Sapienza):
 *  1. Apri https://script.google.com → Nuovo progetto, incolla tutto questo file al posto del codice di esempio.
 *  2. Sostituisci CODICE_SEGRETO qui sotto con il codice che trovi in .antigravity/tutor/secrets.json ("gmail_key").
 *  3. Esegui una volta la funzione "prova" (menu in alto) e concedi l'accesso a Gmail quando Google lo chiede.
 *  4. Distribuisci → Nuova distribuzione → tipo "App web": Esegui come "Me", Chi ha accesso "Chiunque".
 *  5. Copia l'URL dell'app web (finisce con /exec) in .antigravity/tutor/secrets.json come "gmail_url".
 * L'URL da solo non basta: senza il codice lo script risponde {"error":"forbidden"}.
 */
const KEY = "CODICE_SEGRETO";
const QUERY = '"Diario delle lezioni" newer_than:60d';

function doGet(e) {
  if (!e || !e.parameter || e.parameter.key !== KEY) return json({ error: "forbidden" });
  const out = [];
  for (const thread of GmailApp.search(QUERY, 0, 100)) {
    for (const msg of thread.getMessages()) {
      const subject = msg.getSubject();
      if (!/Lezione\s+del/i.test(subject)) continue;
      out.push({ subject: subject, date: msg.getDate().toISOString(), body: cleanBody(msg.getPlainBody()) });
    }
  }
  return json(out);
}

/** Toglie dal testo la parte che aggiunge Moodle (link al post, istruzioni per disiscriversi). */
function cleanBody(text) {
  const cut = text.search(/\n\s*(Vai al post|Visualizza il post|Rispondi|Disiscriviti|-{5,})/i);
  return (cut > 0 ? text.slice(0, cut) : text).trim();
}

function json(data) {
  return ContentService.createTextOutput(JSON.stringify(data)).setMimeType(ContentService.MimeType.JSON);
}

function prova() {
  Logger.log(doGet({ parameter: { key: KEY } }).getContent().slice(0, 2000));
}
