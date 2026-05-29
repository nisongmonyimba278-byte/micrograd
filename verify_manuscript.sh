#!/usr/bin/env bash
# verify_manuscript.sh — full manuscript health check
# Run from ~/micrograd: bash verify_manuscript.sh
set -uo pipefail
cd "$(dirname "$0")"

PASS=0; FAIL=0; WARN=0
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC}  $1"; ((PASS++)); }
fail() { echo -e "  ${RED}✗${NC}  $1"; ((FAIL++)); }
warn() { echo -e "  ${YELLOW}~${NC}  $1"; ((WARN++)); }
hdr()  { echo ""; echo "── $1 ──"; }

# ─────────────────────────────────────────────────────────────────────────────
echo "════════════════════════════════════════════════════════════"
echo "  MANUSCRIPT VERIFICATION  —  $(date '+%Y-%m-%d %H:%M')"
echo "════════════════════════════════════════════════════════════"

# ── 1. FRESH COMPILE ─────────────────────────────────────────────────────────
hdr "1. Fresh compile"
cd manuscript
pdflatex -interaction=nonstopmode main.tex > /tmp/ms_pass1.log 2>&1
bibtex   main                              > /tmp/ms_bibtex.log 2>&1
pdflatex -interaction=nonstopmode main.tex > /tmp/ms_pass2.log 2>&1
pdflatex -interaction=nonstopmode main.tex > /tmp/ms_pass3.log 2>&1
cp main.pdf ../main.pdf 2>/dev/null
cd ..
ok "Compile finished"

# ── 2. FATAL ERRORS ──────────────────────────────────────────────────────────
hdr "2. LaTeX errors  (expect 0)"
N=$(grep -c "^!" manuscript/main.log 2>/dev/null | awk -F: '{s+=$NF} END{print s+0}')
[[ "$N" -eq 0 ]] && ok "0 fatal errors" || {
    fail "$N fatal error(s)"
    grep "^!" manuscript/main.log | head -10 | sed 's/^/      /'
}

# ── 3. UNDEFINED REFERENCES ──────────────────────────────────────────────────
hdr "3. Undefined citations / labels  (expect 0)"
N=$(grep "LaTeX Warning:.*undefined" manuscript/main.log 2>/dev/null | wc -l | tr -d " ")
[[ "$N" -eq 0 ]] && ok "0 undefined references" || {
    fail "$N undefined reference(s)"
    grep "LaTeX Warning:.*undefined" manuscript/main.log | sed 's/^/      /'
}

# ── 4. BIBTEX ────────────────────────────────────────────────────────────────
hdr "4. BibTeX  (expect 0 warnings)"
N=$(grep -c "^Warning" /tmp/ms_bibtex.log 2>/dev/null | awk -F: '{s+=$NF} END{print s+0}')
[[ "$N" -eq 0 ]] && ok "0 BibTeX warnings" || {
    fail "$N BibTeX warning(s)"
    grep "^Warning" /tmp/ms_bibtex.log | sed 's/^/      /'
}

# ── 5. PAGE COUNT ────────────────────────────────────────────────────────────
hdr "5. Page count  (expect ≥ 27)"
PAGES=$(grep "Output written" manuscript/main.log \
        | grep -oP '\d+ page' | grep -oP '\d+' || echo 0)
[[ "${PAGES:-0}" -ge 27 ]] \
    && ok "$PAGES pages" \
    || fail "$PAGES pages — something was deleted"

# ── 6. PDF SIZE ───────────────────────────────────────────────────────────────
hdr "6. PDF size  (expect 300 KB – 1 MB)"
BYTES=$(stat -c%s main.pdf 2>/dev/null || echo 0)
KB=$((BYTES/1024))
[[ "$KB" -ge 300 && "$KB" -le 1024 ]] \
    && ok "${KB} KB" \
    || warn "${KB} KB — outside expected range (check figures)"

# ── 7. ALL REQUIRED FIGURES PRESENT ─────────────────────────────────────────
hdr "7. Required figures"
ALL_FIG_OK=true
while IFS= read -r fig; do
    base=$(basename "$fig")
    if [[ -f "figures/$base" ]]; then
        sz=$(du -h "figures/$base" | cut -f1)
        ok "$base  ($sz)"
    else
        fail "$base  — MISSING from figures/"
        ALL_FIG_OK=false
    fi
done < <(grep -h "includegraphics" manuscript/chapter*.tex 2>/dev/null \
         | grep -oP '(?<=\{)[^}]+\.(pdf|png)' | sort -u)

# ── 8. REQUIRED SECTIONS ─────────────────────────────────────────────────────
hdr "8. Required sections"
declare -A SECTIONS=(
    ["Brinkman-penalised"]="abstract.tex"
    ["Mathematical model"]="chapter2_mathematical_model.tex"
    ["Nondimensional analysis"]="chapter2_mathematical_model.tex"
    ["Finite element discretisation"]="chapter3_numerical_methods.tex"
    ["RMSE definition"]="chapter3_numerical_methods.tex"
    ["Results"]="chapter4_results.tex"
    ["Discussion"]="chapter5_discussion.tex"
    ["Conclusion"]="chapter6_conclusion.tex"
    ["micrograd"]="chapter7_data_availability.tex"
    ["GitHub Actions"]="chapter3_numerical_methods.tex"
)
for section in "${!SECTIONS[@]}"; do
    file="manuscript/${SECTIONS[$section]}"
    grep -qi "$section" "$file" 2>/dev/null \
        && ok "$section" \
        || fail "$section  — not found in ${SECTIONS[$section]}"
done

# ── 9. REQUIRED EQUATIONS & LABELS ──────────────────────────────────────────
hdr "9. Required equations and labels"
for label in eq:brinkman eq:convdiff eq:rmse eq:Re eq:Pe eq:Da eq:Uc \
             sec:nondim sec:brinkman sec:supg sec:ci sec:reproducibility; do
    grep -rq "\\\\label{$label}" manuscript/*.tex 2>/dev/null \
        && ok "\\label{$label}" \
        || fail "\\label{$label}  — missing"
done

# ── 10. REQUIRED CITATIONS PRESENT IN BIB ───────────────────────────────────
hdr "10. Key citations in references.bib"
for key in borrvall2003 whitesides2006 jeon2000 yang2020 \
           fenicsx2022 brooks1982 lazarov2011 \
           bezgin2023jaxfluids lu2021hpinn papadopoulos2022stokes \
           kou2025neural karniadakis2021pinns \
           GitHubActions2024 micrograd2025zenodo; do
    grep -q "$key" manuscript/references.bib 2>/dev/null \
        && ok "$key" \
        || fail "$key  — missing from references.bib"
done

# ── 11. MACRO VALUES ─────────────────────────────────────────────────────────
hdr "11. Macro values (no nan, no XXXXXXX)"
while IFS= read -r line; do
    name=$(echo "$line" | grep -oP '(?<=\\newcommand{\\)[^}]+')
    val=$(echo  "$line" | grep -oP '(?<=\}\{).*' | sed 's/\\ensuremath{//g; s/}*$//')
    [[ "$val" == *nan*       ]] && { fail "$name = $val  (nan — run generate_macros.py)"; continue; }
    [[ "$val" == *XXXXXXX*   ]] && { warn "$name = $val  (Zenodo DOI not yet registered)"; continue; }
    [[ "$val" == *yourusername* ]] && { fail "$name = $val  (placeholder URL)"; continue; }
    ok "$name = $val"
done < <(grep "newcommand" manuscript/macros.tex | grep -v "^%")

# ── 12. PROMOTIONAL LANGUAGE ─────────────────────────────────────────────────
hdr "12. Promotional language  (expect 0 hits)"
PROMO_HITS=0
for phrase in "paves the way" "paving the way" "fully in silico" \
              "novel, non-intuitive" "opens the door" \
              "unprecedented" "groundbreaking" "revolutionary" \
              "state-of-the-art" "powerful framework"; do
    found=$(grep -ril "$phrase" manuscript/*.tex 2>/dev/null | wc -l)
    [[ "$found" -gt 0 ]] && { warn "\"$phrase\" still present"; ((PROMO_HITS++)); }
done
[[ "$PROMO_HITS" -eq 0 ]] && ok "No promotional language found" \
    || warn "$PROMO_HITS phrase(s) to review"

# ── 13. MESH CONSISTENCY ─────────────────────────────────────────────────────
hdr "13. Mesh consistency"
PRIMARY="80.times.20\|80\\\\times20"
SCREENING="20.times.5\|20\\\\times5"
# Primary mesh should appear in ch3 (methods) and ch5 (table)
grep -q "80.times.20\|80\\\\times20" manuscript/chapter3_numerical_methods.tex 2>/dev/null \
    && ok "80×20 present in chapter3 (methods)" \
    || fail "80×20 missing from chapter3"
grep -q "80.times.20\|80\\\\times20" manuscript/chapter5_discussion.tex 2>/dev/null \
    && ok "80×20 present in chapter5 (table)" \
    || fail "80×20 missing from chapter5"
# Abstract should NOT say "all results on 20×5"
grep -q "All results.*20.times.5\|All results.*coarse" manuscript/abstract.tex 2>/dev/null \
    && fail "Abstract still says 'All results on coarse 20×5'" \
    || ok "Abstract does not claim all results on 20×5"

# ── 14. RECENT REFERENCES (2021-2026) ────────────────────────────────────────
hdr "14. Recent literature coverage  (2021–2026)"
RECENT_OK=0
for year in 2021 2022 2023 2024 2025; do
    N=$(grep -c "year.*=.*{$year}" manuscript/references.bib 2>/dev/null || echo 0)
    if [[ "$N" -gt 0 ]]; then ok "$year: $N reference(s)"; ((RECENT_OK++)); else warn "$year: 0 references"; fi
done
[[ "$RECENT_OK" -ge 4 ]] && ok "Recent literature coverage adequate" \
    || fail "Recent literature coverage weak — add 2021–2026 references"

# ── 15. CI AND REPRODUCIBILITY ────────────────────────────────────────────────
hdr "15. CI and reproducibility"
grep -q "GitHub Actions\|ci\.yml\|dolfinx" manuscript/chapter3_numerical_methods.tex 2>/dev/null \
    && ok "CI description present in chapter3" \
    || fail "CI description missing from chapter3"
grep -q "run_all.sh\|docker run\|Docker" manuscript/chapter3_numerical_methods.tex 2>/dev/null \
    && ok "Docker one-liner present" \
    || fail "Docker one-liner missing"
[[ -f ".github/workflows/ci.yml" ]] \
    && ok ".github/workflows/ci.yml exists" \
    || fail ".github/workflows/ci.yml missing"

# ── FINAL VERDICT ─────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════"
printf "  PASS: ${GREEN}%d${NC}   FAIL: ${RED}%d${NC}   WARN: ${YELLOW}%d${NC}\n" \
    "$PASS" "$FAIL" "$WARN"
echo ""
if [[ "$FAIL" -eq 0 ]]; then
    echo -e "  ${GREEN}✅  MANUSCRIPT IS SUBMISSION-READY${NC}"
else
    echo -e "  ${RED}❌  $FAIL issue(s) must be fixed before submission${NC}"
fi
echo "════════════════════════════════════════════════════════════"
echo "  PDF: $(wslpath -w ~/micrograd/main.pdf 2>/dev/null || echo ~/micrograd/main.pdf)"
echo "════════════════════════════════════════════════════════════"
