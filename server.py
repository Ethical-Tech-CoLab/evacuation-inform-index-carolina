#!/usr/bin/env python3
"""Evacuation Inform Index — local backend.

Serves the static site AND a /api/detail endpoint that pulls, server-side:
  • Tavily  -> live news / developments per crisis (real-time)
  • ACLED   -> structured, dated conflict events for the timeline
Keys are read from a gitignored .env file (or the environment).
Stdlib only — no pip install needed.  Run:  python3 server.py
"""
import json, os, re, time, hashlib, hmac, threading, urllib.request, urllib.parse, http.server, email.utils
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", "8000"))
CACHE_DIR = os.path.join(ROOT, ".cache")
CACHE_TTL = 6 * 3600  # 6 hours — repeat clicks within this window are free

# ---- API-usage tracking (so you don't blow through Tavily credits) ----
# Tavily bills per *search* (basic = 1 credit), not per token. We count every
# real outbound call here; cache hits cost nothing and are not counted.
USAGE_PATH = os.path.join(CACHE_DIR, "usage.json")
SESSION_USAGE = {"tavily": 0, "acled": 0, "earth_image": 0}  # since this process started

def usage_bump(kind):
    SESSION_USAGE[kind] = SESSION_USAGE.get(kind, 0) + 1
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        data = json.load(open(USAGE_PATH)) if os.path.exists(USAGE_PATH) else {}
        data[kind] = data.get(kind, 0) + 1
        json.dump(data, open(USAGE_PATH, "w"))
    except Exception:
        pass

def usage_read():
    try:
        return json.load(open(USAGE_PATH)) if os.path.exists(USAGE_PATH) else {}
    except Exception:
        return {}

def _cache_path(key):
    return os.path.join(CACHE_DIR, hashlib.sha1(key.encode()).hexdigest()[:16] + ".json")

def cache_get(key):
    p = _cache_path(key)
    if os.path.exists(p) and time.time() - os.path.getmtime(p) < CACHE_TTL:
        try:
            return json.load(open(p))
        except Exception:
            return None
    return None

def cache_set(key, obj):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        json.dump(obj, open(_cache_path(key), "w"))
    except Exception:
        pass

# ---- ACLED country-name aliases (INFORM name -> ACLED name) ----
ACLED_ALIAS = {
    "DR Congo": "Democratic Republic of Congo",
    "Congo DRC": "Democratic Republic of Congo",
    "DRC": "Democratic Republic of Congo",
    "CAR": "Central African Republic",
    "Syrian Arab Republic": "Syria",
    "occupied Palestinian territory": "Palestine",
    "State of Palestine": "Palestine",
    "Venezuela (Bolivarian Republic of)": "Venezuela",
    "Iran (Islamic Republic of)": "Iran",
    "Tanzania": "United Republic of Tanzania",
    "Moldova": "Republic of Moldova",
    "Bolivia": "Bolivia",
}

def load_env():
    env = {}
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("TAVILY_API_KEY", "ACLED_EMAIL", "ACLED_PASSWORD", "NASA_API_KEY"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env

# ---- Local-security config (env-overridable, safe defaults) -------------
# /api/detail spends real Tavily credits, so the API is treated as private:
# loopback-only bind, an origin allowlist instead of wildcard CORS, per-IP
# rate limiting, and *optional* token auth (off unless EII_API_TOKEN is set,
# so an unset variable never locks out normal local use).
_ENV_FILE = load_env()

def _cfg(name, default=""):
    v = os.environ.get(name)
    if v is None:
        v = _ENV_FILE.get(name)
    return (v if v is not None else default).strip()

HOST = _cfg("HOST", "127.0.0.1")
ALLOWED_ORIGINS = {o.strip() for o in _cfg(
    "ALLOWED_ORIGINS",
    f"http://localhost:{PORT},http://127.0.0.1:{PORT}").split(",") if o.strip()}
API_TOKEN = _cfg("EII_API_TOKEN", "")          # empty = auth disabled
try:
    RATE_LIMIT = int(_cfg("RATE_LIMIT_PER_MIN", "30") or 30)  # 0 = unlimited
except ValueError:
    RATE_LIMIT = 30

_RATE, _RATE_LOCK = {}, threading.Lock()

def rate_ok(ip):
    """Sliding 60s window, per client IP. Cheap and stdlib-only."""
    if RATE_LIMIT <= 0:
        return True
    now = time.time()
    with _RATE_LOCK:
        hits = [t for t in _RATE.get(ip, []) if now - t < 60]
        allowed = len(hits) < RATE_LIMIT
        if allowed:
            hits.append(now)
        _RATE[ip] = hits
        if len(_RATE) > 512:  # bound memory
            for k in [k for k, v in _RATE.items() if not v or now - v[-1] > 300]:
                _RATE.pop(k, None)
    return allowed

def http_json(url, data=None, headers=None, method="GET"):
    body = json.dumps(data).encode() if data is not None else None
    h = {"Content-Type": "application/json", "User-Agent": "EII/1.0"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def tavily_news(key, query, days=60, max_results=10):
    out = http_json("https://api.tavily.com/search", method="POST", data={
        "api_key": key, "query": query, "topic": "news",
        "days": days, "max_results": max_results,
        "include_answer": True, "search_depth": "basic",
    })
    items = []
    for r in out.get("results", []):
        items.append({
            "title": r.get("title"),
            "url": r.get("url"),
            "date": r.get("published_date"),
            "snippet": (r.get("content") or "")[:260],
            "source": urllib.parse.urlparse(r.get("url", "")).netloc.replace("www.", ""),
        })
    return {"answer": out.get("answer"), "items": items}

# ---- Road access / blockages -------------------------------------------
# Whether the roads out are usable is the single most decisive input to
# evacuation feasibility, and no open, global, structured road-closure feed
# covers conflict zones — so this reads the news for it via Tavily.
#
# Two honest limits, surfaced in the UI rather than hidden:
#   1. News prose carries NO geometry. There are no coordinates for "the
#      Salah al-Din road is cut", so blockages are reported as a list and a
#      feasibility signal, never drawn as lines on the map.
#   2. The status below is keyword-derived from the headline and snippet, not
#      verified. It is a triage hint that points at a source to read.
ROAD_QUERY = ("road closures, blocked highways, destroyed bridges, checkpoints, "
              "border crossing closures and impassable evacuation routes")
# Word boundaries are load-bearing here: without them "closure" fires on
# "disclosure", "mined" on "examined", and "passable" on "impassable" — which
# would flip a blocked road to reopened.
ROAD_PATTERNS = [
    ("blocked",    r"\bblock(ed|ade|ades|ing|s)?\b|\bclos(e|es|ed|ure|ures|ing)\b|"
                   r"\bshut(s|ting)?\b|\bhalt(s|ed|ing)?\b|\bsuspend(s|ed|ing)?\b|"
                   r"\bseal(ed|s|ing)?\b|cut off|cut-off|impassab|inaccessib|besieg|siege|"
                   r"encircl|\btrapped\b|\bstranded\b|no way out"),
    ("damaged",    r"destroy|damag|collaps|\bbomb(ed|ing|s)?\b|\bshell(ed|ing)\b|"
                   r"\bstruck\b|washed away|landslide|\bflood(ed|ing|s)?\b|"
                   r"landmine|land mine|\bmined\b|\bcrater(s|ed)?\b"),
    ("checkpoint", r"checkpoint|road ?block|barricade|\bpermit(s)?\b|screening|"
                   r"turned back|denied passage"),
    ("reopened",   r"reopen|re-open|restored|\bclear(ed|ing)\b|repair|resumed|"
                   r"\bpassable\b|corridor open|humanitarian corridor"),
]
# Weight per status when turning counts into a 0–1 obstruction signal. Reopenings
# genuinely offset blockages, so they subtract.
ROAD_WEIGHTS = {"blocked": 1.0, "damaged": 0.8, "checkpoint": 0.5, "reopened": -0.5}
ROAD_SATURATE = 5.0   # weighted score at which the signal reaches 1.0

# ---- Relevance gates -----------------------------------------------------
# Tavily ranks by relevance but still returns loosely-related news, and the
# status patterns above are generic enough to fire on any of it: "Mozambique
# flood crisis threatens food security" matches \bflood\b, and a Michigan
# lane-closure story matches \bclosure\b. Without these gates every crisis
# saturated at signal 1.0, which would have applied the maximum feasibility
# penalty to all 104 crises on evidence about other continents.

# The item has to be about land movement at all. A naval blockade closes a sea
# lane, not a road, and is excluded below rather than counted as an obstruction.
ROAD_SUBJECT = (r"\broad(s|way|ways|block|blocks)?\b|\bhighway(s)?\b|\bbridge(s)?\b|"
                r"\broute(s)?\b|\bcorridor(s)?\b|\bcheckpoint(s)?\b|\bcrossing(s)?\b|"
                r"\bstreet(s)?\b|\bmotorway(s)?\b|\bconvoy(s)?\b|\boverland\b|"
                r"\bland route(s)?\b|\bsupply line(s)?\b|\bevacuation route(s)?\b|"
                r"\btravel\b|\btraffic\b|\bdrive\b|\bdriving\b|\bvehicle(s)?\b")
# Encirclement is the most absolute road blockage there is, and it is reported
# without ever naming a road: "RSF forces encircle el-Obeid" is a statement that
# every route out is closed. Requiring a road noun would discard exactly the
# siege reporting this tool most needs, so this language satisfies the subject
# gate on its own.
SIEGE_SUBJECT = (r"\bbesieg(e|ed|ing)?\b|\bsiege\b|\bencircl(e|ed|ing|ement)\b|"
                 r"\bsurrounded\b|\bcut off\b|\bcut-off\b|\bsealed off\b|"
                 r"\btrapped\b|no way out|\bescape\b|\bfleeing\b|\bflee\b|"
                 r"\bstranded\b|\bblockade(d)?\b")
# Maritime and air disruption uses the same verbs ("blockade", "closed") but
# says nothing about whether people can drive out.
NON_ROAD_SUBJECT = (r"\bnaval\b|\bmaritime\b|\bshipping\b|\bvessel(s)?\b|\btanker(s)?\b|"
                    r"\bport(s)?\b|\bharbou?r(s)?\b|\bsea ?lane(s)?\b|\bairspace\b|"
                    r"\bflight(s)?\b|\bairport(s)?\b|\bairline(s)?\b|\bstrait(s)?\b|"
                    r"\bcanal\b|\bwaterway(s)?\b|\bgulf\b|\bred sea\b|\bhormuz\b|"
                    r"\brunway(s)?\b|\bferry\b|\bferries\b|"
                    # Trade-route language is about freight moving between
                    # countries, not civilians driving out of one. The Houthi
                    # "declared blockade of Saudi Arabia" reporting names no
                    # maritime noun in the first 260 characters, so the nouns
                    # above never fire and a sea blockade scored as two blocked
                    # roads in Yemen. These phrases are what such a story always
                    # carries instead.
                    r"\bchoke ?point(s)?\b|\btrade route(s)?\b|\btrade\b|"
                    r"\bexport(s|ed|ing)?\b|\bimport(s|ed|ing)?\b|\bcargo\b|"
                    r"\bfreight\b|\bcommercial traffic\b")
# Words that carry no geographic signal, so they must not satisfy the place gate.
_PLACE_STOPWORDS = {
    "republic", "democratic", "state", "states", "islamic", "federal", "united",
    "people", "peoples", "kingdom", "territory", "occupied", "province",
    "region", "north", "south", "east", "west", "northern", "southern",
    "eastern", "western", "central", "greater", "new", "city", "district",
}

# A word that is some *other* country's entire name cannot identify this one.
# Splitting "South Sudan" on whitespace leaves {"sudan"} once the direction word
# is dropped as a stopword, and every Sudan story was consequently pinned on
# South Sudan as well — including the el-Obeid encirclement, which is 800 km
# inside Sudan. Multi-word names keep the full phrase instead.
_OTHER_COUNTRY_WORDS = {"sudan", "congo", "guinea", "korea", "niger", "china"}

# Demonyms and plurals a country name takes in prose. Matching has to reach
# "Yemeni" from "Yemen" and "Sudanese" from "Sudan", which is why the tokens
# were substring-matched in the first place — but bare substring matching also
# reaches "Nigeria" from "Niger", and an IOM plan for Nigeria became Niger's
# only checkpoint report. Anchoring the front of the token and allowing only
# these endings keeps the demonyms and rejects the neighbour.
#   -ian/-ians are deliberately absent: they would readmit "Nigerian" for Niger,
#   and country names ending in -ia ("Ethiopia" -> "Ethiopian") are already
#   covered by the plain -n ending.
_DEMONYM_SUFFIX = r"(i|is|s|n|ns|an|ans|ese|na|ien|iens)?"

# Country names in the INFORM data are not the names reporters use. Two failure
# modes both need fixing here:
#   1. Abbreviations yield no token at all ("CAR", "DRC" are under four
#      characters), which used to disable the place gate entirely and let a
#      Michigan lane-closure story score against Bangui.
#   2. Reporting names the sub-national theatre, not the country — coverage of
#      Gaza or the West Bank rarely contains the word "Palestine".
# Only crises whose reporting genuinely uses other names are listed; everything
# else is served fine by the country name itself.
PLACE_ALIASES = {
    "CAR": ("central african", "bangui"),
    "DRC": ("congo", "kinshasa", "goma", "kivu", "ituri"),
    "DR Congo": ("congo", "kinshasa", "goma", "kivu", "ituri"),
    "Democratic Republic of Congo": ("congo", "kinshasa", "goma", "kivu", "ituri"),
    "Palestine": ("gaza", "west bank", "rafah", "khan younis", "jerusalem"),
    "occupied Palestinian territory": ("palestin", "gaza", "west bank", "rafah"),
    "State of Palestine": ("palestin", "gaza", "west bank", "rafah"),
    "Sudan": ("sudan", "khartoum", "darfur", "el fasher", "el-fasher",
              "obeid", "omdurman"),
    "South Sudan": ("south sudan", "juba", "upper nile", "unity state"),
    "Syria": ("syria", "aleppo", "damascus", "idlib", "homs"),
    "Yemen": ("yemen", "sanaa", "sana'a", "aden", "hodeidah", "taiz", "marib"),
    "Myanmar": ("myanmar", "burma", "rakhine", "kachin", "shan", "sagaing"),
    "Ethiopia": ("ethiopia", "tigray", "amhara", "oromia", "afar"),
    "Nigeria": ("nigeria", "borno", "maiduguri", "yobe", "adamawa"),
    "Somalia": ("somalia", "mogadishu", "puntland", "jubaland"),
    "Mali": ("mali", "bamako", "mopti", "gao", "timbuktu"),
    "Burkina Faso": ("burkina", "ouagadougou", "sahel region"),
    "Niger": ("niger", "niamey", "diffa", "tillaberi"),
    "Afghanistan": ("afghan", "kabul", "kandahar", "herat"),
    "Ukraine": ("ukrain", "kyiv", "kharkiv", "donetsk", "kherson", "zaporizhzhia"),
    "Lebanon": ("lebanon", "beirut", "bekaa", "lebanese"),
    "Haiti": ("haiti", "port-au-prince", "haitian"),
    "Mozambique": ("mozambiqu", "cabo delgado", "beira", "pemba"),
    "Venezuela": ("venezuela", "caracas"),
    "Chad": ("chad", "n'djamena", "ndjamena"),
    "Cameroon": ("cameroon", "yaounde", "douala", "far north"),
}

# Sub-national crises need the same treatment one level down. A curated place
# label names the theatre ("Mindanao (BARMM and central Mindanao)") but not the
# towns reporters actually file from, and the country name is far too coarse to
# stand in: three copies of a hotel collapsing in Angeles City, Pampanga —
# northern Luzon, ~900 km away — were the largest contributor to the Mindanao
# obstruction signal, purely because the word "Philippines" appears in them.
# Keyed by a lowercase substring of the place label in geo/locations.csv.
# Extend as sub-national crises acquire road reports; an absent entry simply
# falls back to the words in the place label itself.
SUBPLACE_ALIASES = {
    "mindanao": ("mindanao", "barmm", "cotabato", "maguindanao", "marawi",
                 "lanao", "zamboanga", "davao", "general santos", "sultan kudarat",
                 "sulu", "basilan", "tawi-tawi", "surigao"),
    "gaza": ("gaza", "rafah", "khan younis", "deir al-balah", "jabalia"),
    "west bank": ("west bank", "jenin", "nablus", "hebron", "ramallah", "tulkarem"),
    "cabo delgado": ("cabo delgado", "pemba", "mocimboa", "palma", "macomia"),
    "cox's bazar": ("cox's bazar", "coxs bazar", "kutupalong", "balukhali", "teknaf"),
    "darién": ("darien", "darién", "bajo chiquito", "canaan membrillo"),
}


def _tok_pattern(tok):
    """A place token as a regex: anchored at a word start, demonyms allowed.

    Multi-word tokens ("south sudan", "general santos") are matched literally —
    the ambiguity this guards against only arises for single words.
    """
    if " " in tok or "-" in tok or "'" in tok:
        return r"\b" + re.escape(tok)
    return r"\b" + re.escape(tok) + _DEMONYM_SUFFIX + r"\b"


def _match_tokens(text, toks):
    """True if any token identifies `text` as being about that place."""
    return any(re.search(_tok_pattern(tok), text) for tok in toks)


def _words_of(src):
    """Significant lowercase words in a place or country name."""
    return [t for t in re.split(r"[^a-z']+", (src or "").lower())
            if len(t) >= 4 and t not in _PLACE_STOPWORDS]


def _all_words_of(src):
    """Every word of a name, stopwords kept.

    The significant-words filter is right for picking out individual tokens and
    wrong for rebuilding the name: "South Sudan" loses its direction word and
    collapses to "Sudan", which is the whole reason Sudan's news reached South
    Sudan's pin. The full phrase has to be assembled before that filter runs.
    """
    return [t for t in re.split(r"[^a-z']+", (src or "").lower()) if len(t) >= 3]


def _place_tokens(country, place=None):
    """Distinctive lowercase terms that mark an item as being about this crisis.

    "Democratic Republic of Congo" reduces to {"congo"}; the generic half would
    otherwise match any story containing the word "republic". Tokens are matched
    with _tok_pattern, which reaches the demonym ("Yemen" -> "Yemeni") without
    reaching the neighbour ("Niger" -> "Nigeria").

    A multi-word country name keeps the whole phrase and drops any single word
    that is another country's name outright, so "South Sudan" no longer answers
    to plain "Sudan".

    Returns an empty set only when nothing usable can be derived, and callers
    treat that as "cannot verify location" rather than "location verified".
    """
    toks = set()
    full = _all_words_of(country)
    if len(full) > 1:
        toks.add(" ".join(full))
        toks.update(w for w in _words_of(country) if w not in _OTHER_COUNTRY_WORDS)
    else:
        toks.update(_words_of(country))
    toks.update(_place_only_tokens(country, place))
    for alias in PLACE_ALIASES.get(country, ()):
        toks.add(alias.lower())
    return toks


def _place_only_tokens(country, place=None):
    """Tokens that identify the sub-national area *and not merely the country*.

    The country's own words are removed: a place label routinely repeats them
    ("Borno, Adamawa & Yobe states (BAY), north-east Nigeria"), and leaving
    "nigeria" in would make the sub-national gate no stricter than the country
    one it exists to tighten.
    """
    if not place:
        return set()
    toks = {w for w in _words_of(place)}
    low = place.lower()
    for key, aliases in SUBPLACE_ALIASES.items():
        if key in low:
            toks.update(a.lower() for a in aliases)
    country_words = set(_words_of(country)) | {
        a.lower() for a in PLACE_ALIASES.get(country, ())}
    return {t for t in toks if t not in country_words}

# Domains that carry user-generated posts, open-wiki travel copy, or link-dump
# indexes rather than reported journalism. The relevance gates judge the text; a
# post can pass them and still be nobody's reporting — DRC's only pin, and its
# whole −2-point feasibility penalty, was a wikitravel "Travel news" index page
# that merely mentioned Congo and floods, and two other items were Facebook
# posts. This is a *deny* list, deliberately not an allow list: an allow list
# would silently drop reliefweb, OCHA/IOM, and the local-language outlets that
# carry the earliest road news, which is the worse error on a map about whether
# people can leave. It names only sources that are categorically not newsrooms.
SOURCE_DENYLIST = {
    # social / user-generated
    "facebook.com", "twitter.com", "x.com", "instagram.com", "tiktok.com",
    "youtube.com", "reddit.com", "t.me", "telegram.me", "linkedin.com",
    "pinterest.com", "threads.net", "vk.com", "medium.com", "quora.com",
    # open wikis and travel link-dumps
    "wikitravel.org", "wikivoyage.org", "wikipedia.org", "tripadvisor.com",
    "lonelyplanet.com",
}


def source_is_admissible(source):
    """False for social, open-wiki, and travel-aggregator domains.

    `source` is the stored netloc (www-stripped) or a full URL. Matches the
    registrable domain and its subdomains, so m.facebook.com and
    en.wikitravel.org are caught too.
    """
    host = source or ""
    if "//" in host:
        host = urllib.parse.urlparse(host).netloc
    host = host.lower().split("@")[-1].split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    return not any(host == d or host.endswith("." + d) for d in SOURCE_DENYLIST)


def road_item_is_relevant(text, country, place=None):
    """True if this item is plausibly about land access *in this crisis's area*.

    Both gates are required. Either one alone lets through the two failure modes
    seen in practice: right-topic-wrong-country (Michigan lane closures scored
    against Yemen) and right-country-wrong-topic (a Mozambique food-security
    story scored as road damage).
    """
    t = (text or "").lower()
    if not (re.search(ROAD_SUBJECT, t) or re.search(SIEGE_SUBJECT, t)):
        return False
    # Maritime/air-only items mention no land subject beyond the generic verbs.
    # A naval blockade matches SIEGE_SUBJECT via "blockade", so this gate has to
    # run after it, not before.
    if re.search(NON_ROAD_SUBJECT, t) and not re.search(
            r"\broad(s|way|ways)?\b|\bhighway(s)?\b|\bbridge(s)?\b|\bcheckpoint(s)?\b|"
            r"\bland route(s)?\b|\boverland\b|\bconvoy(s)?\b|\bbesieg|\bsiege\b|"
            r"\bencircl", t):
        return False
    # A crisis with a curated sub-national area has to be matched at that level.
    # Its reporting is about one theatre inside the country, so the country name
    # alone confirms nothing: "Philippines" is true of a Luzon building collapse
    # and of a Mindanao earthquake alike, and the map cannot tell them apart on
    # that evidence. Under-counting here is the safer error — the UI already
    # says plainly that an absent report is not an all-clear.
    if place:
        sub = _place_only_tokens(country, place)
        return bool(sub) and _match_tokens(t, sub)
    toks = _place_tokens(country, place)
    if not toks:
        # No way to confirm the item is about this crisis. Returning True here
        # is what disabled the gate for "CAR" and "DRC" and scored those crises
        # at maximum obstruction off unrelated news. A missing blockage report
        # is visibly labelled as such in the UI; a fabricated one is not.
        return False
    return _match_tokens(t, toks)

# "no immediate reports of damages", "no damage reported", "without damage" —
# an earthquake story whose whole point is that nothing broke matched \bdamag\b
# and became Guatemala's only road-damage report. The negation has to be read,
# not just the keyword.
NEGATED_DAMAGE = (r"\bno (immediate )?(reports? of )?(major |serious |significant )?"
                  r"(damage|damages|casualties)\b|"
                  r"\bwithout (major |serious )?damage\b|"
                  r"\bno damage (was |were )?(reported|recorded)\b|"
                  r"\bdamage (was |were )?not reported\b")
# `reopened` subtracts from the obstruction signal, so a false positive there is
# worse than a missed one: it argues that routes have opened. "schools were
# reopening after a long break" is not a road reopening, and it discounted the
# Mindanao earthquake by half a point. Require the reopening to be predicated of
# something people travel on.
REOPEN_SUBJECT = (r"\broad(s|way|ways)?\b|\bhighway(s)?\b|\bbridge(s)?\b|"
                  r"\broute(s)?\b|\bcorridor(s)?\b|\bcrossing(s)?\b|\bborder(s)?\b|"
                  r"\bport(s)?\b|\bpass(es)?\b|\baccess\b|\btraffic\b|\bconvoy(s)?\b|"
                  r"\bsupply line(s)?\b|\bcheckpoint(s)?\b")


def classify_road(text):
    """Return (primary_status, all_matched_tags) for one news item.

    An item saying "the coast road reopened after weeks closed" matches both
    directions, so every match is kept in `tags` and the caller can see the
    ambiguity. `status` prefers the obstruction reading, because under-calling a
    blocked route is the more dangerous error for an evacuation tool to make.

    Two patterns are qualified rather than taken at face value: `damaged` is
    dropped where the text negates the damage, and `reopened` is dropped unless
    something traversable is what reopened.
    """
    t = (text or "").lower()
    tags = [name for name, pat in ROAD_PATTERNS if re.search(pat, t)]
    if "damaged" in tags and re.search(NEGATED_DAMAGE, t):
        tags.remove("damaged")
    if "reopened" in tags and not re.search(REOPEN_SUBJECT, t):
        tags.remove("reopened")
    for name in ("blocked", "damaged", "checkpoint", "reopened"):
        if name in tags:
            return name, tags
    return "unclear", tags

def crisis_query(country, crisis, place=None):
    """The search subject for one crisis.

    `place` is the curated sub-national location from geo/locations.csv. Naming
    it puts the actual affected area in the query — "Cabo Delgado province"
    instead of "northern Mozambique", "Kutupalong" instead of "Bangladesh" —
    which is how the reporting is actually written. It is omitted for
    country-scope crises, where it would only repeat the country term.
    """
    return f"{place}, {country} {crisis}" if place else f"{country} {crisis}"

# Words too common to distinguish one story from another when comparing headlines.
_HEADLINE_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "in", "on", "at", "to", "for", "from",
    "as", "by", "with", "into", "after", "amid", "over", "still", "says", "say",
    "new", "more", "than", "that", "this", "it", "its", "is", "are", "was",
    "were", "be", "been", "has", "have", "had", "will", "could", "would",
}


def _headline_key(title):
    """Content words of a headline, with the syndicating outlet's suffix removed.

    Tavily returns wire copy once per outlet that ran it. "3 dead, 17 mostly
    workers still missing in collapse of unfinished hotel in Philippines - The
    Sun Chronicle" and the "4 dead" revision of the same story are one report,
    and counting them separately trebled a single building collapse.
    """
    t = (title or "").lower()
    t = re.sub(r"\s+[-–|]\s+[^-–|]{1,40}$", "", t)      # trailing " - Outlet"
    words = [w for w in re.split(r"[^a-z0-9']+", t)
             if w and w not in _HEADLINE_STOPWORDS]
    return set(words)


# News-agency tags that appear in a wire dateline. A syndicated dispatch keeps
# its origin dateline ("ABDIN, Syria (AP) — …") on every outlet that reruns it,
# even when the outlet rewrites the headline, so the dateline is a surer identity
# for a wire story than the headline the current rule matches on.
_WIRE_AGENCIES = (r"AP|Reuters|AFP|Bloomberg|dpa|EFE|Xinhua|Kyodo|Anadolu|TASS|"
                  r"AAP|Associated Press|Agence France-Presse")
_DATELINE_RE = re.compile(
    r"\b([A-Z][A-Z.'\-]{1,}(?:\s+[A-Z][A-Z.'\-]+)*"     # ALL-CAPS origin city
    r"(?:,\s*[A-Z][A-Za-z.'\- ]+?)?)"                    # optional ", Region"
    r"\s*\(\s*(" + _WIRE_AGENCIES + r")\s*\)\s*[—–\-]")  # (AGENCY) —


def _wire_dateline(snippet):
    """Normalised 'city|agency' from a wire dateline, or None if there is none.

    Returns just the origin city (first token) and the agency, both lowercased,
    so two rehostings of one dispatch share a key even when everything after the
    dateline — headline included — has been rewritten.
    """
    m = _DATELINE_RE.search(snippet or "")
    if not m:
        return None
    city = re.split(r"[,\s]", m.group(1).strip())[0].lower()
    return f"{city}|{m.group(2).lower()}"


def _is_duplicate(item, kept):
    """True if `item` reports the same story as something already kept.

    Exact URL first, then a shared wire dateline, then headline overlap. The
    dateline check catches re-headlined wire copy that the headline rule misses
    (the AP and Greenwich reruns of one Abdin dispatch share only ~45% of their
    headline words). The headline threshold stays deliberately high: merging two
    genuinely distinct blockages would understate obstruction, the error this
    tool must not make, so dateline matching only fires when both items actually
    carry one.
    """
    url = (item.get("url") or "").split("?")[0].rstrip("/")
    key = _headline_key(item.get("title"))
    dateline = _wire_dateline(item.get("snippet"))
    for k in kept:
        if url and url == (k.get("url") or "").split("?")[0].rstrip("/"):
            return True
        if dateline and dateline == _wire_dateline(k.get("snippet")):
            return True
        other = _headline_key(k.get("title"))
        if not key or not other:
            continue
        overlap = len(key & other) / len(key | other)
        if overlap >= 0.75:
            return True
    return False


def road_date_window(item, days):
    """Where an item's published_date falls relative to a `days`-day window.

    Returns 'in', 'out', or 'undated'. Tavily's `days` parameter is not honoured
    for every result, so this is the backstop that keeps a three-year-old border
    closure off a map read for whether people can leave today. Undated items are
    surfaced as such rather than silently kept — an unplaceable date is a fact
    the reader should see, not one the tool should paper over.
    """
    raw = item.get("date")
    if not raw:
        return "undated"
    try:
        dt = email.utils.parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return "undated"
    if dt is None:
        return "undated"
    if dt.tzinfo is not None:                 # normalise to naive UTC to compare
        dt = (dt - dt.utcoffset()).replace(tzinfo=None)
    return "in" if (datetime.utcnow() - dt) <= timedelta(days=days) else "out"


def tavily_roads(key, country, crisis, days=60, max_results=10, place=None):
    """Road-access items for one crisis, classified and scored."""
    news = tavily_news(key, f"{crisis_query(country, crisis, place)} {ROAD_QUERY}",
                       days=days, max_results=max_results)
    items, counts = [], {"blocked": 0, "damaged": 0, "checkpoint": 0, "reopened": 0}
    dropped = duplicates = stale = low_source = 0
    for it in news["items"]:
        blob = f"{it.get('title','')} {it.get('snippet','')}"
        # Publisher first: a social post or travel-wiki index is nobody's
        # reporting, however well it matches the road topic below.
        if not source_is_admissible(it.get("source") or it.get("url")):
            low_source += 1
            continue
        # Relevance next: an item about another country, or about shipping
        # rather than roads, must not reach the classifier at all.
        if not road_item_is_relevant(blob, country, place):
            dropped += 1
            continue
        # Then recency: an item published outside the requested window is dropped
        # outright; an undated one is kept but flagged so the popup can say so.
        window = road_date_window(it, days)
        if window == "out":
            stale += 1
            continue
        if window == "undated":
            it = dict(it, undated=True)
        status, tags = classify_road(blob)
        if status == "unclear":
            continue                       # no road language at all — drop the noise
        # Deduplicate after classification so the count reflects distinct
        # reports. One wire story on four outlets is one road blockage.
        if _is_duplicate(it, items):
            duplicates += 1
            continue
        counts[status] += 1
        items.append(dict(it, status=status, tags=tags))
    score = sum(ROAD_WEIGHTS[s] * n for s, n in counts.items())
    signal = max(0.0, min(1.0, score / ROAD_SATURATE))
    return {"answer": news.get("answer"), "items": items, "counts": counts,
            "signal": round(signal, 3), "considered": len(news["items"]),
            "off_topic": dropped, "duplicates": duplicates, "stale": stale,
            "low_source": low_source, "query_days": days}

# ---- ArcGIS drive-time service areas (isochrones) -----------------------
# The road-access signal above is derived from news prose, which carries no
# geometry — there are no coordinates for "the Salah al-Din road is cut". This
# supplies the missing half: ArcGIS solves service areas on Esri's actual street
# network, so the map can show how far a vehicle can physically get from a
# crisis point.
#
# The two sources answer different questions and neither substitutes for the
# other:
#   • ArcGIS  -> where the roads go and how far they reach (network geometry)
#   • Tavily  -> whether those roads are passable this week (current status)
# An isochrone is the reachable area on an undisrupted network. It is a ceiling
# on movement, not a claim that the routes are open today, and the UI says so.
ARCGIS_SA_URL = ("https://route-api.arcgis.com/arcgis/rest/services/World/"
                 "ServiceAreas/NAServer/ServiceArea_World/solveServiceArea")
# Drive-time bands in minutes. Evacuation planning cares about the first couple
# of hours; beyond that the network assumptions stop being credible in a crisis.
ARCGIS_BREAKS = "30 60 120"

def arcgis_service_area(key, lat, lng, breaks=ARCGIS_BREAKS):
    """Drive-time polygons outward from one crisis point.

    Returns rings in WGS84 so Leaflet can draw them directly, plus the break
    each ring belongs to. Raises on transport or service errors; callers decide
    whether a missing isochrone is fatal.
    """
    params = {
        "f": "json",
        "token": key,
        "facilities": json.dumps({
            "features": [{"geometry": {"x": float(lng), "y": float(lat)}}]
        }),
        "defaultBreaks": breaks,
        # People are leaving the crisis point, so solve outward from it. The
        # default direction (toward the facility) would answer the responder's
        # question, not the civilian's, and the two differ on one-way networks.
        "travelDirection": "esriNATravelDirectionFromFacility",
        # Simplified geometry keeps 104 baked snapshots to a sane size; detailed
        # polygons are an order of magnitude larger for no visual gain at the
        # zoom levels this map uses.
        "outputPolygons": "esriNAOutputPolygonSimplified",
        "outSR": 4326,
    }
    out = http_json(ARCGIS_SA_URL + "?" + urllib.parse.urlencode(params))
    # ArcGIS reports failures inside a 200 response, so this must be checked
    # explicitly rather than relying on urlopen to raise.
    if "error" in out:
        e = out["error"]
        raise RuntimeError(f"arcgis {e.get('code')}: {e.get('message')} "
                           f"{'; '.join(e.get('details') or [])}".strip())
    bands = []
    for feat in (out.get("saPolygons", {}) or {}).get("features", []):
        attrs = feat.get("attributes", {}) or {}
        rings = (feat.get("geometry", {}) or {}).get("rings")
        if not rings:
            continue
        bands.append({
            "from": attrs.get("FromBreak"),
            "to": attrs.get("ToBreak"),
            "rings": rings,
        })
    # Smallest band last so it draws on top of the larger ones.
    bands.sort(key=lambda b: (b["to"] is None, -(b["to"] or 0)))
    return {"breaks": breaks, "bands": bands,
            "source": "Esri ArcGIS service areas (World street network)"}

# ACLED migrated to OAuth2 in 2025: log in with email+password -> Bearer token
# (valid 24h) -> query https://acleddata.com/api/acled/read. The legacy
# api.acleddata.com key+email endpoint is deprecated.
ACLED_OAUTH_URL = "https://acleddata.com/oauth/token"
ACLED_READ_URL = "https://acleddata.com/api/acled/read"
_ACLED_TOKEN = {"token": None, "exp": 0}

def acled_token(email, password):
    if _ACLED_TOKEN["token"] and _ACLED_TOKEN["exp"] - 120 > time.time():
        return _ACLED_TOKEN["token"]
    tp = os.path.join(CACHE_DIR, "acled_token.json")
    if os.path.exists(tp):
        try:
            c = json.load(open(tp))
            if c.get("exp", 0) - 120 > time.time():
                _ACLED_TOKEN.update(c)
                return c["token"]
        except Exception:
            pass
    body = urllib.parse.urlencode({
        "username": email, "password": password, "grant_type": "password",
        "client_id": "acled", "scope": "authenticated",
    }).encode()
    req = urllib.request.Request(
        ACLED_OAUTH_URL, data=body, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "EII/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.load(r)
    tok = out["access_token"]
    exp = time.time() + int(out.get("expires_in", 86400))
    _ACLED_TOKEN.update({"token": tok, "exp": exp})
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        json.dump({"token": tok, "exp": exp}, open(tp, "w"))
    except Exception:
        pass
    return tok

def acled_timeline(email, password, country, months=18):
    name = ACLED_ALIAS.get(country, country)
    token = acled_token(email, password)
    # Some access tiers serve only data >=12 months old; request a wide lower
    # bound and let the API enforce its own recency cutoff. Page ascending.
    since = (datetime.utcnow() - timedelta(days=(months + 14) * 31)).strftime("%Y-%m-%d")
    buckets, types = {}, {}
    newest, cutoff, total_rows, truncated = None, None, 0, False
    MAX_PAGES = 30
    page = 1
    while page <= MAX_PAGES:
        url = ACLED_READ_URL + "?" + urllib.parse.urlencode({
            "country": name, "event_date": since, "event_date_where": ">=",
            "fields": "event_date|event_type|fatalities", "limit": 5000, "page": page,
        })
        out = http_json(url, headers={"Authorization": "Bearer " + token})
        if cutoff is None:
            try:
                cutoff = out["data_query_restrictions"]["date_recency"].get("date")
            except Exception:
                cutoff = None
        rows = out.get("data") or []
        if not rows:
            break
        total_rows += len(rows)
        for e in rows:
            d = e.get("event_date") or ""
            m = d[:7]
            if not m:
                continue
            if newest is None or d > newest:
                newest = d
            b = buckets.setdefault(m, {"month": m, "events": 0, "fatalities": 0})
            b["events"] += 1
            try:
                b["fatalities"] += int(e.get("fatalities") or 0)
            except (TypeError, ValueError):
                pass
            t = e.get("event_type") or "Other"
            types[t] = types.get(t, 0) + 1
        if len(rows) < 5000:
            break
        page += 1
    else:
        truncated = True
    kept = sorted(buckets.values(), key=lambda x: x["month"])[-months:]
    note = ""
    if cutoff:
        note = f"Your ACLED access tier serves data up to {cutoff} (~12-month embargo)."
    if truncated:
        note += " High event volume — earliest portion shown; recent months may be undercounted."
    return {
        "country_used": name,
        "months": kept,
        "by_type": sorted(types.items(), key=lambda x: -x[1]),
        "total_events": sum(b["events"] for b in kept),
        "total_fatalities": sum(b["fatalities"] for b in kept),
        "newest": newest,
        "cutoff": cutoff,
        "truncated": truncated,
        "note": note,
    }

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def log_message(self, *a):
        pass  # quiet

    def send_cors(self):
        """Echo the request Origin only when it is on the allowlist (no '*')."""
        o = self.headers.get("Origin")
        self.send_header("Vary", "Origin")
        if o and o in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", o)

    def send_json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_cors()
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def api_guard(self):
        """Gate every /api/* call. Returns True to proceed, else already replied."""
        origin = self.headers.get("Origin")
        if origin and origin not in ALLOWED_ORIGINS:
            self.send_json({"error": "origin_not_allowed"}, 403)
            return False
        # Drive-by CSRF (e.g. <img src="http://localhost:8000/api/detail?...">
        # on a page the user visits) arrives with Sec-Fetch-Site: cross-site.
        # Same-origin XHR/fetch and address-bar navigations ("none") pass, as do
        # non-browser clients that send no such header (curl, snapshot.py).
        if self.headers.get("Sec-Fetch-Site") in ("cross-site", "same-site"):
            self.send_json({"error": "cross_site_blocked"}, 403)
            return False
        if API_TOKEN:  # opt-in hard auth
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            tok = self.headers.get("X-API-Token") or (q.get("token") or [""])[0]
            if not hmac.compare_digest(tok, API_TOKEN):
                self.send_json({"error": "unauthorized"}, 401)
                return False
        if not rate_ok(self.client_address[0]):
            self.send_json({"error": "rate_limited"}, 429)
            return False
        return True

    def do_GET(self):
        if self.path.startswith("/api/") and not self.api_guard():
            return
        if self.path.startswith("/api/detail"):
            return self.api_detail()
        if self.path.startswith("/api/earth-image"):
            return self.api_earth_image()
        if self.path.startswith("/api/usage"):
            return self.api_usage()
        return super().do_GET()

    def api_earth_image(self):
        """Proxy NASA's keyed Earth Imagery API -> a Landsat snapshot for one
        location. Key stays server-side; image bytes are disk-cached (the NASA
        endpoint is slow), and any failure returns JSON so the client hides it."""
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        try:
            lat = float((q.get("lat") or [""])[0])
            lon = float((q.get("lon") or [""])[0])
        except ValueError:
            return self.send_json({"error": "bad_coords"}, 400)
        dim = (q.get("dim") or ["0.5"])[0]
        key = load_env().get("NASA_API_KEY")
        if not key:
            return self.send_json({"error": "no_nasa_key"}, 404)
        cpath = os.path.join(CACHE_DIR, "img_" + hashlib.sha1(
            f"earth|{lat}|{lon}|{dim}".encode()).hexdigest()[:16] + ".png")
        data = None
        if os.path.exists(cpath) and time.time() - os.path.getmtime(cpath) < 7 * 86400:
            try:
                data = open(cpath, "rb").read()
            except Exception:
                data = None
        if data is None:
            url = "https://api.nasa.gov/planetary/earth/imagery?" + urllib.parse.urlencode(
                {"lon": lon, "lat": lat, "dim": dim, "api_key": key})
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "EII/1.0"})
                with urllib.request.urlopen(req, timeout=35) as r:
                    ctype = r.headers.get("Content-Type", "")
                    data = r.read()
                if not ctype.startswith("image"):
                    return self.send_json(
                        {"error": "nasa_no_image",
                         "detail": data[:200].decode("utf-8", "ignore")}, 502)
                os.makedirs(CACHE_DIR, exist_ok=True)
                open(cpath, "wb").write(data)
                usage_bump("earth_image")
            except Exception as e:
                return self.send_json({"error": "nasa_unreachable", "detail": str(e)}, 502)
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Cache-Control", "public, max-age=604800")
        self.send_cors()
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def api_usage(self):
        """Report API spend so the user can watch their Tavily credits."""
        self.send_json({
            "total": usage_read(),          # cumulative across all runs (persisted)
            "session": SESSION_USAGE,        # since this server process started
            "note": "Tavily basic search = 1 API credit. A detail call spends 2 "
                    "(news + road access); add ?roads=0 to spend 1. Cached results "
                    "(≤6h) cost 0. Check your monthly limit at app.tavily.com.",
        })

    def api_detail(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        crisis = (q.get("crisis") or [""])[0]
        country = (q.get("country") or [""])[0]
        place = (q.get("place") or [""])[0] or None
        try:
            days = max(1, min(365, int((q.get("days") or ["60"])[0])))
        except ValueError:
            days = 60
        env = load_env()
        tk = env.get("TAVILY_API_KEY")
        ae, ap = env.get("ACLED_EMAIL"), env.get("ACLED_PASSWORD")
        nocache = "nocache" in q
        # Road access is a second Tavily search, so it doubles the credit cost
        # of a detail call. On by default (it is the point of the feature);
        # pass ?roads=0 to skip it when conserving credits.
        want_roads = (q.get("roads") or ["1"])[0] not in ("0", "false", "no")
        # `place` is part of the cache key: changing the search location changes
        # the results, so a cached response from before the geography fix must
        # not be served for the newly place-anchored query.
        ckey = (f"{crisis}|{country}|{place or ''}|d{days}"
                f"|t{bool(tk)}|a{bool(ae and ap)}|r{int(want_roads)}")
        if not nocache:
            hit = cache_get(ckey)
            if hit:
                hit["cached"] = True
                return self.send_json(hit)
        resp = {"crisis": crisis, "country": country, "place": place,
                "cached": False, "days": days,
                "tavily": None, "acled": None, "roads": None, "errors": [], "keys": {}}
        resp["keys"]["tavily"] = bool(tk)
        if tk:
            try:
                resp["tavily"] = tavily_news(
                    tk, f"{crisis_query(country, crisis, place)} "
                        "latest conflict, security and humanitarian developments",
                    days=days)
                usage_bump("tavily")  # a real search credit was spent
            except Exception as e:
                resp["errors"].append(f"tavily: {e}")
            if want_roads:
                try:
                    resp["roads"] = tavily_roads(tk, country, crisis, days=days, place=place)
                    usage_bump("tavily")   # second search = second credit
                except Exception as e:
                    resp["errors"].append(f"roads: {e}")
        else:
            resp["errors"].append("no_tavily_key")
        resp["keys"]["acled"] = bool(ae and ap)
        if ae and ap:
            try:
                resp["acled"] = acled_timeline(ae, ap, country)
                usage_bump("acled")
            except Exception as e:
                resp["errors"].append(f"acled: {e}")
        else:
            resp["errors"].append("no_acled_key")
        if resp.get("tavily") or resp.get("acled") or resp.get("roads"):
            cache_set(ckey, resp)  # only cache real data
        self.send_json(resp)

if __name__ == "__main__":
    httpd = http.server.ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"EII backend on http://{HOST}:{PORT}  (/api/detail live)")
    print(f"  bind: HOST={HOST} (set HOST=0.0.0.0 to expose on the LAN — spends API credits)")
    print(f"  cors: {', '.join(sorted(ALLOWED_ORIGINS)) or '(none)'}")
    print(f"  rate: {RATE_LIMIT}/min per IP · auth: {'on (EII_API_TOKEN)' if API_TOKEN else 'off'}")
    httpd.serve_forever()
