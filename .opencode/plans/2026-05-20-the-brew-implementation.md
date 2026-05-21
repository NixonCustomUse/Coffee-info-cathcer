# The Brew Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Coffee Info Catcher static dashboard from a dark coffee-house theme to a light newspaper-style dashboard called "The Brew".

**Architecture:** Single HTML file with inline CSS and JS, deployed via Cloudflare Workers. Rewrite `public/index.html` (and sync to root `index.html`) with new CSS + layout, keeping the existing DATA array and JS filtering logic.

**Tech Stack:** Vanilla HTML/CSS/JS, Google Fonts (Playfair Display, Lora, Source Sans 3, JetBrains Mono), Cloudflare Workers

---

### Task 1: Rewrite public/index.html — CSS + Structure

**Files:**
- Modify: `public/index.html` (full rewrite)
- Modify: `index.html` (root — sync after public is done)

This is a single large task since the file is entirely rewritten. The plan covers all changes in one go.

- [ ] **Step 1: Write new HTML structure**

Replace the entire `public/index.html` with the new newspaper design:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Brew — Coffee Intelligence</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;0,900;1,400&family=Lora:ital,wght@0,400;0,500;0,600;1,400&family=Source+Sans+3:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
/* CSS reset */
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  font-family:'Source Sans 3','Helvetica Neue',sans-serif;
  background:#f6f3ee;color:#1a1a1a;
  line-height:1.6;-webkit-font-smoothing:antialiased;
  min-height:100dvh;
}
::selection{background:rgba(139,26,26,0.12);color:#1a1a1a}
a{color:#8b1a1a;text-decoration:none;transition:color .15s}
a:hover{color:#b82a2a}
button{cursor:pointer;font-family:'Source Sans 3',sans-serif}

/* CONTAINER */
.container{max-width:1240px;margin:0 auto;padding:24px 28px;}

/* MASTHEAD */
.masthead{text-align:center;padding:32px 0 20px;border-bottom:2px solid #1a1a1a;margin-bottom:20px;}
.masthead-name{
  font-family:'Playfair Display',Georgia,serif;
  font-size:clamp(2.2rem,5vw,3.6rem);font-weight:900;
  letter-spacing:.06em;text-transform:uppercase;color:#1a1a1a;line-height:1;
}
.masthead-sub{
  font-size:.78rem;color:#8a8478;
  display:flex;justify-content:center;gap:20px;margin-top:8px;
  font-family:'Source Sans 3',sans-serif;
}
.masthead-sub .sep{color:#d0ccc4}
.masthead-date{font-weight:500;color:#5a5448}

/* FILTER BAR */
.filter-bar{display:flex;gap:5px;flex-wrap:wrap;margin:16px 0 6px;align-items:center;}
.filter-pill{
  padding:5px 14px;border-radius:100px;border:1px solid #d0ccc4;
  background:transparent;color:#5a5448;font-size:.75rem;font-weight:500;
  transition:all .15s;white-space:nowrap;
}
.filter-pill:hover{border-color:#8b1a1a;color:#8b1a1a}
.filter-pill.active{background:#8b1a1a;border-color:#8b1a1a;color:#fff}
.filter-pill .count{font-family:'JetBrains Mono',monospace;font-size:.65rem;margin-left:3px;opacity:.6}
.filter-pill.active .count{opacity:.8}

.sub-filter-bar{display:flex;gap:4px;flex-wrap:wrap;margin:6px 0 12px;}
.sub-chip{
  padding:3px 10px;border-radius:100px;border:1px solid #e0ddd6;
  background:transparent;color:#8a8478;font-size:.68rem;
  transition:all .15s;white-space:nowrap;
}
.sub-chip:hover{border-color:#8b1a1a;color:#8b1a1a}
.sub-chip.active{background:rgba(139,26,26,0.08);border-color:#8b1a1a;color:#8b1a1a;font-weight:500}

/* STATS */
.stats-row{display:flex;gap:16px;margin:0 0 16px;font-size:.78rem;color:#8a8478;}
.stats-row strong{color:#1a1a1a;font-weight:600;}

/* RESET LINK */
.reset-row{text-align:right;margin-top:-8px;margin-bottom:8px;min-height:24px;}
.reset-link{font-size:.72rem;color:#8a8478;cursor:pointer;transition:color .15s;background:none;border:none;padding:0;}
.reset-link:hover{color:#8b1a1a}

/* CARDS GRID */
.cards-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
.card{
  background:#fff;border-radius:8px;padding:18px 20px;
  border:1px solid #e0ddd6;transition:all .2s;cursor:pointer;
  position:relative;
}
.card:hover{border-color:#c0b8ac;box-shadow:0 2px 12px rgba(0,0,0,.04);}
.card:active{transform:scale(.99)}
.card-top{display:flex;align-items:flex-start;gap:12px;margin-bottom:4px;}
.card-score{
  font-family:'JetBrains Mono',monospace;font-size:.6rem;font-weight:500;
  color:#fff;background:#8b1a1a;width:26px;height:26px;border-radius:5px;
  display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:1px;
}
.card-title{
  font-family:'Lora',Georgia,serif;font-size:.92rem;font-weight:500;
  color:#1a1a1a;line-height:1.35;flex:1;
}
.card-meta{font-size:.72rem;color:#8a8478;margin-bottom:5px;display:flex;gap:10px;}
.card-source{color:#8b1a1a;font-weight:500;}
.card-tags{display:flex;gap:3px;flex-wrap:wrap;margin-bottom:4px;}
.card-tag{
  font-size:.62rem;padding:2px 9px;border-radius:100px;
  background:#f0ede6;color:#5a5448;
}
.card-subtags{display:flex;gap:3px;flex-wrap:wrap;margin-bottom:5px;}
.card-subtag{
  font-size:.58rem;padding:1px 7px;border-radius:3px;
  background:rgba(139,26,26,.06);color:#8b1a1a;border:1px solid rgba(139,26,26,.1);
  font-family:'JetBrains Mono',monospace;
}
.card-summary{
  font-size:.78rem;color:#6b655a;line-height:1.55;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;
}
.empty-state{grid-column:1/-1;text-align:center;padding:60px 20px;color:#8a8478;font-size:.9rem;}

/* MOBILE */
@media(max-width:740px){
  .container{padding:16px;}
  .cards-grid{grid-template-columns:1fr;gap:10px;}
  .masthead{padding:24px 0 16px;}
  .card{padding:14px 16px;}
  .card-title{font-size:.85rem;}
  .card-summary{font-size:.74rem;}
  .filter-bar{gap:4px;}
  .filter-pill{font-size:.7rem;padding:4px 10px;}
}
</style>
</head>
<body>

<div class="container" id="app">
  <!-- MASTHEAD -->
  <div class="masthead">
    <div class="masthead-name">The Brew</div>
    <div class="masthead-sub">
      <span class="masthead-date" id="mastDate"></span>
      <span class="sep">·</span>
      <span><strong id="totalCount">0</strong> signals</span>
      <span class="sep">·</span>
      <span><strong id="sourceCount">0</strong> sources</span>
    </div>
  </div>

  <!-- FILTERS -->
  <div class="filter-bar" id="filterBar"></div>
  <div class="sub-filter-bar" id="subBar"></div>

  <!-- STATS + RESET -->
  <div class="stats-row" id="statsRow"></div>
  <div class="reset-row"><button class="reset-link" id="resetBtn" onclick="resetFilters()" style="display:none">← All articles</button></div>

  <!-- CARDS -->
  <div class="cards-grid" id="cardsGrid"></div>
</div>

<script>
const DATA = [/* DATA ARRAY HERE */];

let activeFilter = null;
let activeSub = null;

document.getElementById('mastDate').textContent = new Date().toLocaleDateString('en-US',{weekday:'long',year:'numeric',month:'long',day:'numeric'});

function getSources(items){return[...new Set(items.map(i=>i.s))];}
function getCategories(items){const m={};items.forEach(i=>i.c.forEach(c=>{m[c]=(m[c]||0)+1}));return Object.entries(m).sort((a,b)=>b[1]-a[1]);}
function getSubcategories(items){const m={};items.forEach(i=>i.sc.forEach(s=>{m[s]=(m[s]||0)+1}));return Object.entries(m).sort((a,b)=>b[1]-a[1]);}

function filtered(){
  let items=DATA;
  if(activeFilter)items=items.filter(i=>i.c.includes(activeFilter));
  if(activeSub)items=items.filter(i=>i.sc.includes(activeSub));
  return items;
}

function render(){
  const items=filtered();
  document.getElementById('totalCount').textContent=DATA.length;
  document.getElementById('sourceCount').textContent=getSources(DATA).length;

  const stats=document.getElementById('statsRow');
  stats.innerHTML='<span><strong>'+items.length+'</strong> signals</span><span><strong>'+getSources(items).length+'</strong> sources</span>';

  const allCats=getCategories(DATA);
  document.getElementById('filterBar').innerHTML=
    '<button class="filter-pill'+(activeFilter?'':' active')+'" onclick="setFilter(null)">All <span class="count">'+DATA.length+'</span></button>'+
    allCats.map(([c,n])=>'<button class="filter-pill'+(activeFilter===c?' active':'')+'" onclick="setFilter(\''+c.replace(/'/g,"\\'")+'\')">'+c+' <span class="count">'+n+'</span></button>').join('');

  const allSubs=getSubcategories(activeFilter?DATA.filter(i=>i.c.includes(activeFilter)):DATA);
  document.getElementById('subBar').innerHTML=
    '<button class="sub-chip'+(activeSub?'':' active')+'" onclick="setSub(null)">All</button>'+
    allSubs.map(([s,n])=>'<button class="sub-chip'+(activeSub===s?' active':'')+'" onclick="setSub(\''+s.replace(/'/g,"\\'")+'\')">'+s+'</button>').join('');

  document.getElementById('resetBtn').style.display=(activeFilter||activeSub)?'inline':'none';

  const grid=document.getElementById('cardsGrid');
  if(!items.length){
    grid.innerHTML='<div class="empty-state">No articles match your filters.</div>';
    return;
  }
  grid.innerHTML=items.map(i=>
    '<div class="card" onclick="window.open(\''+i.u.replace(/'/g,"\\'")+'\',\'_blank\')">'+
      '<div class="card-top"><span class="card-score">'+i.tc+'</span><div class="card-title">'+esc(i.t)+'</div></div>'+
      '<div class="card-meta"><span class="card-source">'+esc(i.s)+'</span><span>'+i.p.slice(0,10)+'</span></div>'+
      '<div class="card-tags">'+i.c.map(c=>'<span class="card-tag">'+c+'</span>').join('')+'</div>'+
      (i.sc.length?'<div class="card-subtags">'+i.sc.map(s=>'<span class="card-subtag">'+s+'</span>').join('')+'</div>':'')+
      (i.su?'<div class="card-summary">'+esc(i.su)+'</div>':'')+
    '</div>'
  ).join('');
}

function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function setFilter(cat){activeFilter=cat;activeSub=null;render();}
function setSub(sub){activeSub=sub===activeSub?null:sub;render();}
function resetFilters(){activeFilter=null;activeSub=null;render();}

render();
</script>
</body>
</html>
```

- [ ] **Step 2: Read the current DATA from public/index.html**

The current `public/index.html` has a `const DATA = [...]` array around line 357. Extract that entire `DATA` array (from `const DATA = [` to the closing `];`) and insert it into the new template at the `/* DATA ARRAY HERE */` marker.

```bash
# Extract the DATA array from the current file
python3 -c "
import re
with open('public/index.html') as f:
    content = f.read()
match = re.search(r'const DATA = (\[.*?\]);', content, re.DOTALL)
if match:
    print(match.group(0))
"
```

Then insert the extracted data into the new template at the placeholder.

- [ ] **Step 3: Write the new public/index.html**

Write the full file with the DATA array embedded.

- [ ] **Step 4: Sync to root index.html**

Copy the new `public/index.html` to `index.html` (root).

```bash
cp public/index.html index.html
```

- [ ] **Step 5: Verify the HTML parses correctly**

```bash
python3 -c "
with open('public/index.html') as f:
    html = f.read()
assert 'The Brew' in html, 'Missing masthead'
assert 'const DATA = [' in html, 'Missing DATA array'
assert 'getCategories' in html, 'Missing JS logic'
assert 'Lora' in html, 'Missing font link'
print(f'OK: {len(html)} bytes, DATA array present')
"
```

- [ ] **Step 6: Open in browser to verify visually (manual)**

Open `public/index.html` in a browser and check:
- Masthead shows "The Brew" with date
- Article cards display in a 2-column grid
- Filter pills work: clicking a category filters articles
- Subcategory chips filter correctly
- Reset link appears when filter is active
- Clicking a card opens the URL
- Mobile layout stacks to 1 column

### Task 2: Update generate_html.py

**Files:**
- Modify: `generate_html.py`

Update the CSS and HTML template in `generate_html.py` to match the new newspaper design.

- [ ] **Step 1: Update the CSS variable in generate_html.py**

Replace the `CSS` string with the new newspaper-themed CSS (same as Task 1 but adapted for Chinese output — keep the `.container`, cards, filters, masthead styling).

- [ ] **Step 2: Update build_html() to use the new structure**

Change the template to use the newspaper layout with "The Brew" / "Coffee Radar" masthead instead of the old dashboard.

- [ ] **Step 3: Verify generate_html.py works**

```bash
python3 generate_html.py --input data/items.enriched.jsonl --output /tmp/test-report.html
python3 -c "
with open('/tmp/test-report.html') as f:
    html = f.read()
assert 'Coffee Radar' in html or 'The Brew' in html
print(f'OK: {len(html)} bytes')
"
```
