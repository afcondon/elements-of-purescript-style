// The Elements of PureScript Style — Review App
// Votes and notes stored in localStorage.

const STORAGE_KEY = "ps-style-votes";
const NOTES_KEY = "ps-style-notes";

let data = null;
let currentFilter = "all";

// -- Storage --

function loadVotes() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; }
  catch { return {}; }
}

function saveVotes(votes) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(votes));
}

function loadNotes() {
  try { return JSON.parse(localStorage.getItem(NOTES_KEY)) || {}; }
  catch { return {}; }
}

function saveNotes(notes) {
  localStorage.setItem(NOTES_KEY, JSON.stringify(notes));
}

// -- Markdown rendering (minimal) --

function renderMarkdown(text) {
  // Escape HTML first so prose can't inject tags (e.g. <script>)
  text = escapeHtml(text);

  // Code blocks: ```purescript ... ``` (already escaped, no need for escapeHtml again)
  text = text.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    return `<pre><code>${code.trim()}</code></pre>`;
  });

  // Inline code
  text = text.replace(/`([^`]+)`/g, "<code>$1</code>");

  // Bold
  text = text.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  // Italic (single *)
  text = text.replace(/\*(.+?)\*/g, "<em>$1</em>");

  // Split into paragraphs (but not inside pre blocks)
  const blocks = [];
  let inPre = false;
  let current = "";

  for (const line of text.split("\n")) {
    if (line.startsWith("<pre>")) {
      if (current.trim()) blocks.push(`<p>${current.trim()}</p>`);
      current = "";
      inPre = true;
      current = line;
    } else if (line.includes("</pre>")) {
      current += "\n" + line;
      blocks.push(current);
      current = "";
      inPre = false;
    } else if (inPre) {
      current += "\n" + line;
    } else if (line.trim() === "") {
      if (current.trim()) blocks.push(`<p>${current.trim()}</p>`);
      current = "";
    } else {
      current += (current ? " " : "") + line;
    }
  }
  if (current.trim()) {
    blocks.push(inPre ? current : `<p>${current.trim()}</p>`);
  }

  return blocks.join("\n");
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// -- Rendering --

function renderEntry(entry, votes, notes) {
  const id = String(entry.id);
  const vote = votes[id] || null;
  const note = notes[id] || "";
  const isDG = entry.section === "degustibus";
  const num = isDG ? "DG" : String(entry.id);

  const badgeHtml = vote
    ? `<span class="entry-badge badge-${vote}">${vote}</span>`
    : "";

  const voteButtons = isDG
    ? "" // De Gustibus entries don't get voted on the same way
    : ["good", "poor", "wrong", "obsolete", "taste"].map(v => {
        const cls = vote === v ? `voted-${v}` : "";
        return `<button class="vote-btn ${cls}" data-id="${id}" data-vote="${v}">${v}</button>`;
      }).join("\n");

  const collapsed = vote && currentFilter === "all" ? "collapsed" : "";

  return `
    <div class="entry ${collapsed}" data-entry-id="${id}" data-vote="${vote || "unreviewed"}" data-section="${entry.section}">
      <div class="entry-header">
        <span class="entry-num">${num}</span>
        <span class="entry-title">${escapeHtml(entry.title)}</span>
        ${badgeHtml}
      </div>
      <div class="entry-body">
        ${renderMarkdown(entry.body)}
      </div>
      ${voteButtons ? `<div class="vote-bar">${voteButtons}</div>` : ""}
      <div class="note-area">
        <textarea placeholder="Notes..." data-note-id="${id}">${escapeHtml(note)}</textarea>
      </div>
    </div>
  `;
}

function renderAll() {
  const votes = loadVotes();
  const notes = loadNotes();
  const container = document.getElementById("entries");

  let html = "";

  // Filter entries
  const filtered = data.entries.filter(e => matchesFilter(e, votes));
  html += filtered.map(e => renderEntry(e, votes, notes)).join("");

  // De Gustibus section
  if (currentFilter === "all" || currentFilter === "degustibus" || currentFilter === "unreviewed") {
    const filteredDG = currentFilter === "degustibus"
      ? data.degustibus
      : currentFilter === "unreviewed"
        ? data.degustibus.filter(e => !votes[String(e.id)])
        : data.degustibus;

    if (filteredDG.length > 0) {
      html += `
        <div class="dg-separator">
          De Gustibus
          <div class="dg-subtitle">Matters where reasonable programmers differ. We present the cases without ruling.</div>
        </div>
      `;
      html += filteredDG.map(e => renderEntry(e, votes, notes)).join("");
    }
  }

  container.innerHTML = html;
  updateStats(votes);
  attachListeners();
}

function matchesFilter(entry, votes) {
  const vote = votes[String(entry.id)] || null;
  if (currentFilter === "all") return entry.section !== "degustibus";
  if (currentFilter === "unreviewed") return !vote && entry.section !== "degustibus";
  if (currentFilter === "degustibus") return false; // handled separately
  return vote === currentFilter;
}

function updateStats(votes) {
  const total = data.entries.length;
  const counts = { good: 0, poor: 0, wrong: 0, obsolete: 0, taste: 0 };
  let reviewed = 0;

  for (const entry of data.entries) {
    const v = votes[String(entry.id)];
    if (v) {
      reviewed++;
      if (counts[v] !== undefined) counts[v]++;
    }
  }

  const statsText = `${reviewed}/${total} reviewed: ${counts.good} good, ${counts.poor} poor, ${counts.wrong} wrong, ${counts.obsolete} obsolete, ${counts.taste} taste`;
  document.getElementById("stats").textContent = statsText;
  const statsBar = document.getElementById("stats-bar");
  if (statsBar) statsBar.textContent = statsText;
}

function attachListeners() {
  // Vote buttons
  document.querySelectorAll(".vote-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = btn.dataset.id;
      const vote = btn.dataset.vote;
      const votes = loadVotes();

      if (votes[id] === vote) {
        delete votes[id]; // toggle off
      } else {
        votes[id] = vote;
      }
      saveVotes(votes);
      renderAll();
    });
  });

  // Collapse/expand on header click
  document.querySelectorAll(".entry-header").forEach(header => {
    header.addEventListener("click", () => {
      header.closest(".entry").classList.toggle("collapsed");
    });
  });

  // Notes
  document.querySelectorAll("textarea[data-note-id]").forEach(ta => {
    ta.addEventListener("input", () => {
      const notes = loadNotes();
      const id = ta.dataset.noteId;
      if (ta.value.trim()) {
        notes[id] = ta.value;
      } else {
        delete notes[id];
      }
      saveNotes(notes);
    });
  });
}

// -- Filter buttons --

document.querySelectorAll(".filter-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    currentFilter = btn.dataset.filter;
    renderAll();
  });
});

// -- Export/Clear --

document.getElementById("export-btn").addEventListener("click", () => {
  const votes = loadVotes();
  const notes = loadNotes();
  const exported = {
    votes,
    notes,
    exportedAt: new Date().toISOString(),
    entries: data.entries.length,
    degustibus: data.degustibus.length
  };
  const blob = new Blob([JSON.stringify(exported, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "ps-style-review.json";
  a.click();
  URL.revokeObjectURL(url);
});

document.getElementById("clear-btn").addEventListener("click", () => {
  if (confirm("Clear all votes and notes? This cannot be undone.")) {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(NOTES_KEY);
    renderAll();
  }
});

// -- Init --

fetch("entries.json")
  .then(r => r.json())
  .then(d => {
    data = d;
    renderAll();
  })
  .catch(err => {
    document.getElementById("entries").innerHTML =
      `<p style="color: #991b1b;">Failed to load entries: ${err.message}</p>`;
  });
