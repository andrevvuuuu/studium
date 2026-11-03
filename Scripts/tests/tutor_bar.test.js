const test = require("node:test");
const assert = require("node:assert");
const { view } = require("../tutor_bar.js");

const missing = (title) => ({ status: "da_creare", concept: title, title, reason: `manca ${title}` });
const covered = { status: "coperto", concept: "U(Z_n)", note: "U(Z_n)", reason: "c'è" };

const STATE_WITH_3_MISSING_1_COVERED = {
    recupero: false,
    courses: [{ id: "analisi", nome: "Analisi", esami: [], previsione: [], prossima_lezione: null,
        lessons: [{ date: "2026-11-02", items: [missing("Serie a segni alterni"), missing("Criterio di Leibniz"), missing("Convergenza assoluta"), covered] }] }]
};

test("al passo quando non ci sono voci da creare", () => {
    const v = view({ courses: [{ id: "algebra", nome: "Algebra", lessons: [{ date: "2026-10-30", items: [covered] }], esami: [], previsione: [],
        prossima_lezione: { data: "2026-11-09", ora: "10:00" } }] }, "2026-11-03");
    assert.equal(v.mode, "al_passo");
    assert.match(v.pill, /Vault al passo con le lezioni/);
    assert.match(v.pill, /Prossima: Algebra, lunedì 10:00/);
});

test("conta le note da creare e nasconde le coperte", () => {
    const v = view(STATE_WITH_3_MISSING_1_COVERED, "2026-11-03");
    assert.equal(v.mode, "lavoro");
    assert.equal(v.pill, "Tutor · 3 note da creare");
    assert.equal(v.lessons[0].items.length, 3);
    assert.equal(v.lessons[0].hidden, 1);
});

test("esame entro 30 giorni e previsione nel piede", () => {
    const st = JSON.parse(JSON.stringify(STATE_WITH_3_MISSING_1_COVERED));
    st.courses[0].esami = [{ nome: "Primo esonero", data: "2026-11-13" }, { nome: "Appello", data: "2027-02-10" }];
    st.courses.push({ id: "algebra", nome: "Algebra", lessons: [], esami: [], prossima_lezione: null,
        previsione: ["Equazioni diofantee.", "Teoria della cardinalità.", "Calcolo combinatorio.", "Binomiale."] });
    const v = view(st, "2026-11-03");
    assert.match(v.foot, /Primo esonero \(Analisi\) tra 10 giorni/);
    assert.doesNotMatch(v.foot, /Appello/);
    assert.match(v.foot, /Prossime lezioni di Algebra \(programma dell'anno scorso\): Equazioni diofantee · Teoria della cardinalità · Calcolo combinatorio/);
});

test("un errore di un corso è una riga discreta, gli altri dati restano", () => {
    const st = JSON.parse(JSON.stringify(STATE_WITH_3_MISSING_1_COVERED));
    st.courses[0].errore = "script Google non ancora configurato";
    const v = view(st, "2026-11-03");
    assert.deepEqual(v.problems, ["Analisi: script Google non ancora configurato"]);
    assert.equal(v.lessons[0].items.length, 3);
});

test("recupero raggruppa le lezioni dalla più vecchia", () => {
    const st = { recupero: true, courses: [{ id: "algebra", nome: "Algebra", esami: [], previsione: [], prossima_lezione: null,
        lessons: [{ date: "2026-10-02", items: [missing("A")] }, { date: "2026-10-30", items: [missing("B"), { status: "da_completare", concept: "C", note: "C", missing: "dimostrazione", reason: "r" }] }] }] };
    const v = view(st, "2026-11-03");
    assert.equal(v.mode, "recupero");
    assert.match(v.pill, /Recupero: 2 da creare, 1 da completare/);
    assert.deepEqual(v.lessons.map(l => l.date), ["2026-10-02", "2026-10-30"]);
});

test("senza stato: caricamento", () => {
    assert.equal(view(null, "2026-11-03").mode, "loading");
});
