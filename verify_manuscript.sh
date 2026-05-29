#!/usr/bin/env bash
# verify_manuscript.sh — reviewer-grade manuscript health check
# Usage: bash verify_manuscript.sh [--no-compile]
cd "$(dirname "$0")"

PASS=0; FAIL=0; WARN=0
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
SKIP_COMPILE=0; [[ "${1:-}" == "--no-compile" ]] && SKIP_COMPILE=1

ok()   { echo -e "  ${GREEN}✓${NC}  $*"; ((PASS++));  }
fail() { echo -e "  ${RED}✗${NC}  $*"; ((FAIL++));   }
warn() { echo -e "  ${YELLOW}~${NC}  $*"; ((WARN++)); }
hdr()  { echo ""; echo -e "${CYAN}── $* ──${NC}"; }
# Count lines matching pattern in one file safely (no multi-file colon prefix)
cnt()  { grep -c "$1" "$2" 2>/dev/null || echo 0; }
# Check if pattern exists in file
has()  { grep -q "$1" "$2" 2>/dev/null; }

echo "════════════════════════════════════════════════════════════"
echo "  MANUSCRIPT VERIFICATION  —  $(date '+%Y-%m-%d %H:%M')"
echo "════════════════════════════════════════════════════════════"

# ── 1. COMPILE ────────────────────────────────────────────────────────────────
hdr "1. Compile"
if [[ "$SKIP_COMPILE" -eq 0 ]]; then
  cd manuscript
  pdflatex -interaction=nonstopmode main.tex > /tmp/ms_p1.log 2>&1
  bibtex   main                              > /tmp/ms_bib.log 2>&1
  pdflatex -interaction=nonstopmode main.tex > /tmp/ms_p2.log 2>&1
  pdflatex -interaction=nonstopmode main.tex > /tmp/ms_p3.log 2>&1
  cp main.pdf ../main.pdf 2>/dev/null
  cd ..
  ok "Compile finished"
else
  warn "Compile skipped (--no-compile)"
fi
LOG=manuscript/main.log

# ── 2. LATEX ERRORS ───────────────────────────────────────────────────────────
hdr "2. LaTeX fatal errors  (expect 0)"
N=$(grep -c "^!" "$LOG" 2>/dev/null || echo 0)
if [[ "$N" -eq 0 ]]; then ok "0 fatal errors"
else
  fail "$N fatal error(s)"
  grep "^!" "$LOG" | head -8 | sed 's/^/      /'
fi

# ── 3. UNDEFINED REFS ─────────────────────────────────────────────────────────
hdr "3. Undefined citations / labels  (expect 0)"
N=$(grep -c "LaTeX Warning:.*undefined" "$LOG" 2>/dev/null || echo 0)
if [[ "$N" -eq 0 ]]; then ok "0 undefined references"
else
  fail "$N undefined reference(s)"
  grep "LaTeX Warning:.*undefined" "$LOG" | sed 's/^/      /'
fi

# ── 4. BIBTEX ─────────────────────────────────────────────────────────────────
hdr "4. BibTeX warnings  (expect 0)"
N=$(grep -c "^Warning" /tmp/ms_bib.log 2>/dev/null || echo 0)
if [[ "$N" -eq 0 ]]; then ok "0 BibTeX warnings"
else
  fail "$N BibTeX warning(s)"
  grep "^Warning" /tmp/ms_bib.log | sed 's/^/      /'
fi

# ── 5. PAGE COUNT ─────────────────────────────────────────────────────────────
hdr "5. Page count  (expect ≥ 27)"
PAGES=$(grep "Output written" "$LOG" | grep -oP '\d+ page' | grep -oP '\d+' || echo 0)
[[ "${PAGES:-0}" -ge 27 ]] && ok "$PAGES pages" \
  || fail "$PAGES pages — a section may have been deleted"

# ── 6. PDF SIZE ───────────────────────────────────────────────────────────────
hdr "6. PDF size  (expect 300 KB – 1 MB)"
BYTES=$(stat -c%s main.pdf 2>/dev/null || echo 0)
KB=$((BYTES/1024))
[[ $KB -ge 300 && $KB -le 1024 ]] && ok "${KB} KB" \
  || warn "${KB} KB — outside expected range (check figures)"

# ── 7. FIGURES ────────────────────────────────────────────────────────────────
hdr "7. Required figures"
while IFS= read -r fig; do
  base=$(basename "$fig")
  if [[ -f "figures/$base" ]]; then
    ok "$base  ($(du -h "figures/$base" | cut -f1))"
  else
    fail "$base — MISSING from figures/"
  fi
done < <(grep -h "includegraphics" manuscript/chapter*.tex 2>/dev/null \
         | grep -oP '(?<=\{)[^}]+\.(pdf|png)' | sort -u)

# ── 8. REQUIRED SECTIONS ──────────────────────────────────────────────────────
hdr "8. Required sections"
check_section() { # usage: check_section "search term" "filename" "label"
  has "$1" "manuscript/$2" && ok "$3" || fail "$3 — not found in $2"
}
check_section "Brinkman"                    "abstract.tex"                      "Abstract (Brinkman)"
check_section "Nondimensional analysis"     "chapter2_mathematical_model.tex"   "Nondimensional analysis"
check_section "Finite element"              "chapter3_numerical_methods.tex"    "Finite element discretisation"
check_section "RMSE"                        "chapter3_numerical_methods.tex"    "RMSE definition"
check_section "GitHub Actions"              "chapter3_numerical_methods.tex"    "CI / reproducibility"
check_section "sec:results"                 "chapter4_results.tex"              "Results section"
check_section "tab:metrics"                 "chapter4_results.tex"              "Performance table"
check_section "tab:comparison"              "chapter5_discussion.tex"           "Literature comparison table"
check_section "Interpretation"              "chapter5_discussion.tex"           "Discussion §5.1"
check_section "sec:conclusion"              "chapter6_conclusion.tex"           "Conclusion section"
check_section "micrograd"                   "chapter7_data_availability.tex"    "Data availability"
check_section "Recent developments"         "chapter1_introduction.tex"         "Recent developments paragraph"

# ── 9. REQUIRED EQUATIONS & LABELS ───────────────────────────────────────────
hdr "9. Required equations and labels"
for label in \
  eq:brinkman eq:convdiff eq:rmse eq:Re eq:Pe eq:Da eq:Uc eq:alpha \
  eq:heaviside eq:sensitivity eq:oc eq:supg \
  sec:model sec:methods sec:results sec:discussion sec:conclusion \
  sec:brinkman sec:convdiff sec:nondim sec:supg sec:reproducibility sec:ci \
  fig:comparison fig:convergence fig:gallery fig:topology \
  tab:metrics tab:comparison; do
  grep -rq "\\\\label{$label}" manuscript/*.tex 2>/dev/null \
    && ok "\\label{$label}" \
    || fail "\\label{$label} — missing"
done

# ── 10. CITATIONS ─────────────────────────────────────────────────────────────
hdr "10. Key citations in references.bib"
for key in \
  borrvall2003 whitesides2006 jeon2000 jeon2005 yang2020 \
  fenicsx2022 brooks1982 lazarov2011 wang2011 bendsoe2003 svanberg1987 \
  elman2014 geuzaine2009 giles2000 scroggs2022 \
  bezgin2023jaxfluids lu2021hpinn papadopoulos2022stokes \
  kou2025neural karniadakis2021pinns liu2025phasefield \
  wang2022christmastree kim2019finger fink2022automatic \
  GitHubActions2024 micrograd2025zenodo; do
  grep -q "$key" manuscript/references.bib 2>/dev/null \
    && ok "$key" || fail "$key — missing from references.bib"
done

# ── 11. MACRO VALUES ──────────────────────────────────────────────────────────
hdr "11. Macro values"
check_macro() { # usage: check_macro name expected_pattern description
  local name="$1" pat="$2" desc="$3"
  local line val
  line=$(grep "newcommand{\\\\$name}" manuscript/macros.tex 2>/dev/null || echo "")
  if [[ -z "$line" ]]; then
    fail "$name — not defined in macros.tex"
    return
  fi
  val=$(echo "$line" | grep -oP '(?<=\}\{).*(?=\}$)' \
        | sed 's/\\ensuremath{//g; s/}$//g; s/^[[:space:]]*//; s/[[:space:]]*$//')
  if echo "$val" | grep -q "nan\|XXXXXXX\|yourusername\|TODO"; then
    fail "$name = $val  ← placeholder/invalid"
  elif [[ -n "$pat" ]] && ! echo "$val" | grep -qP "$pat"; then
    warn "$name = $val  (expected pattern: $pat)"
  else
    ok "$name = $val  ${desc:+(${desc})}"
  fi
}
check_macro rmseTopOpt    "^0\.[0-9]"           "dimensionless RMSE"
check_macro rmseTopOptPP  "^[0-9]"              "RMSE as percentage points"
check_macro hydResTopOpt  "times10"             "optimised hydraulic resistance"
check_macro treeHydRes    "times10"             "Christmas-tree hydraulic resistance"
check_macro treeRMSE      "^0\.[0-9]"           "Christmas-tree RMSE"
check_macro flowRateTopOpt "times10"            "optimised flow rate"
check_macro finalJ        "times10|^[0-9]"      "final objective value"
check_macro reduction     "^[0-9]"              "% resistance reduction"
check_macro alphaMin      "10"                  "α_min"
check_macro alphaMaxFinal "10"                  "α_max final"
check_macro alphaMaxStart "10"                  "α_max start"
check_macro Rey           "mathit"              "Re symbol"
check_macro Pe            "mathit"              "Pe symbol"
check_macro Da            "mathit"              "Da symbol"

# ── 12. NUMBER CONSISTENCY ────────────────────────────────────────────────────
hdr "12. Hardcoded numbers that must match macros"
RMSE_VAL=$(grep "newcommand{\\\\rmseTopOpt}" manuscript/macros.tex \
           | grep -oP '(?<=\}\{)[^}]+')
# Check no chapter hardcodes a different RMSE
for f in manuscript/chapter*.tex manuscript/abstract.tex; do
  bad=$(grep -oP '(?<=RMSE[=~\s]{0,3})\$?0\.\d+' "$f" 2>/dev/null \
        | grep -v "^${RMSE_VAL}$" | grep -v "0\.605\|0\.13\|0\.18\|0\.31\|0\.66" || true)
  [[ -n "$bad" ]] && fail "$(basename $f) hardcodes RMSE=$bad (macro=$RMSE_VAL)" \
                  || true
done
ok "No conflicting hardcoded RMSE values found"

# Check alpha_min consistent
has "alpha_min=1e-4" micrograd/utilities.py \
  && ok "utilities.py: alpha_min=1e-4 matches macros" \
  || fail "utilities.py: alpha_min mismatch — check against \\alphaMin macro"
has "alpha_min" manuscript/chapter2_mathematical_model.tex \
  && { has "10^{-4}\|10^{-3}" manuscript/chapter2_mathematical_model.tex \
       && ok "Chapter 2: alpha_min stated" \
       || warn "Chapter 2: alpha_min value not found"; } \
  || fail "Chapter 2: alpha_min not mentioned"

# ── 13. PROMOTIONAL LANGUAGE ──────────────────────────────────────────────────
hdr "13. Promotional / hedging language  (expect 0)"
NHITS=0
for phrase in \
  "paves the way" "paving the way" "fully in.silico" "opens the door" \
  "unprecedented" "groundbreaking" "revolutionary" "state-of-the-art" \
  "powerful framework" "exotic" "supports for" "novel, non-intuitive" \
  "it is worth noting" "it should be noted" "needless to say" \
  "as expected" "obviously" "clearly" "trivially"; do
  FILES=$(grep -ril "$phrase" manuscript/*.tex 2>/dev/null | tr '\n' ' ')
  [[ -n "$FILES" ]] && { warn "\"$phrase\" in: $FILES"; ((NHITS++)); }
done
[[ $NHITS -eq 0 ]] && ok "No promotional or hedging language found"

# ── 14. MESH CONSISTENCY ──────────────────────────────────────────────────────
hdr "14. Mesh consistency"
has "80.times.20\|80\\\\times20" manuscript/chapter3_numerical_methods.tex \
  && ok "80×20 stated in §Methods" \
  || fail "80×20 missing from §Methods"
has "80.times.20\|80\\\\times20" manuscript/chapter5_discussion.tex \
  && ok "80×20 stated in §Discussion table" \
  || fail "80×20 missing from §Discussion table"
has "80.times.20\|80\\\\times20" manuscript/abstract.tex \
  && ok "80×20 stated in Abstract" \
  || fail "80×20 missing from Abstract"
! has "All results.*coarse\|All results.*20.times.5" manuscript/abstract.tex \
  && ok "Abstract does not misattribute results to 20×5 mesh" \
  || fail "Abstract still claims all results on 20×5"
has "20.times.5\|20\\\\times5" manuscript/chapter3_numerical_methods.tex \
  && ok "20×5 screening mesh mentioned in §Methods" \
  || warn "20×5 screening mesh not mentioned in §Methods"

# ── 15. ALPHA CONSISTENCY ─────────────────────────────────────────────────────
hdr "15. α_min / α_max consistency"
has "10^{-4}\|10^{-3}" manuscript/chapter2_mathematical_model.tex \
  && ok "α_min stated in §Model" || warn "α_min not found in §Model"
! has "alpha_{\\\(\\\\)?min\b.*10^{-3}" manuscript/chapter2_mathematical_model.tex \
  && ok "§Model does not use wrong α_min=10⁻³" \
  || fail "§Model still says α_min=10⁻³ (code uses 1e-4)"
has "10^{9}\|10^8\|10^{8}" manuscript/chapter2_mathematical_model.tex \
  && ok "α_max stated in §Model" || fail "α_max not found in §Model"
# Da uses alpha_max=1e9
has "10^{9}.*Da\|Da.*10^{9}\|alpha.*10^{9}" manuscript/chapter2_mathematical_model.tex \
  && ok "Darcy number uses α_max=10⁹" \
  || warn "Darcy number section: verify α_max=10⁹ is used"

# ── 16. MISSING SUPPLEMENTARY SECTIONS ────────────────────────────────────────
hdr "16. Supplementary material cross-references"
for sref in S10 S12; do
  if grep -rq "$sref" manuscript/chapter*.tex 2>/dev/null; then
    has "$sref" manuscript/chapter8_appendices.tex \
      && ok "$sref cited in main text and present in appendices" \
      || fail "$sref cited in main text but MISSING from chapter8_appendices.tex"
  fi
done
# Check S1 S2 S3 S4 too
for sref in S1 S2 S3 S4; do
  if grep -rq "\\b$sref\\b" manuscript/chapter[1-7]*.tex 2>/dev/null; then
    has "$sref" manuscript/chapter8_appendices.tex \
      && ok "$sref cited and present" \
      || fail "$sref cited in main text but not found in appendices"
  fi
done

# ── 17. RECENT LITERATURE ─────────────────────────────────────────────────────
hdr "17. Recent literature (2021–2026)"
RECENT_OK=0
for year in 2021 2022 2023 2024 2025; do
  N=$(grep -c "year.*=.*{$year}" manuscript/references.bib 2>/dev/null || echo 0)
  if [[ "$N" -gt 0 ]]; then
    ok "$year: $N reference(s)"
    ((RECENT_OK++))
  else
    warn "$year: 0 references"
  fi
done
[[ $RECENT_OK -ge 4 ]] && ok "Recent coverage adequate (≥4 years represented)" \
  || fail "Recent literature weak — add 2021–2026 references"

# ── 18. CI AND REPRODUCIBILITY ────────────────────────────────────────────────
hdr "18. CI and reproducibility"
[[ -f ".github/workflows/ci.yml" ]] \
  && ok ".github/workflows/ci.yml present" \
  || fail ".github/workflows/ci.yml MISSING"
has "dolfinx" .github/workflows/ci.yml \
  && ok "CI uses dolfinx Docker container" \
  || warn "CI: dolfinx container not found in ci.yml"
has "docker run\|Docker" manuscript/chapter3_numerical_methods.tex \
  && ok "Docker one-liner present in §Methods" \
  || fail "Docker one-liner missing from §Methods"
has "zenodo\|XXXXXXX" manuscript/chapter3_numerical_methods.tex \
  && { ! has "XXXXXXX" manuscript/chapter3_numerical_methods.tex \
       && ok "Zenodo DOI present (no placeholder)" \
       || warn "Zenodo DOI still contains XXXXXXX placeholder"; } \
  || warn "Zenodo DOI not mentioned in §Methods"
has "environment.yaml\|requirements" . \
  && ok "Environment lockfile mentioned" \
  || warn "No environment lockfile mentioned"

# ── 19. GRAMMAR / LANGUAGE CHECKS ────────────────────────────────────────────
hdr "19. Known grammar issues"
! has "supports for" manuscript/abstract.tex \
  && ok "Abstract: 'supports for' removed" \
  || fail "Abstract still contains 'supports for' (grammar error)"
! has "fully in.silico\|fully in-silico" manuscript/abstract.tex \
  && ok "Abstract: 'fully in-silico' removed" \
  || warn "Abstract still contains 'fully in-silico'"
# Jeon citation year check
has "Jeon.*2000\|2000.*Jeon" manuscript/chapter1_introduction.tex \
  && { has "jeon2000" manuscript/chapter1_introduction.tex \
       && ok "Jeon 2000: text year matches cite key" \
       || fail "Jeon: text says '2000' but cites jeon2005 (key mismatch)"; } \
  || ok "Jeon citation: no year conflict detected"

# ── 20. WINDOWS PDF PATH ─────────────────────────────────────────────────────
hdr "20. Output"
WIN=$(wslpath -w ~/micrograd/main.pdf 2>/dev/null || echo "~/micrograd/main.pdf")
MTIME=$(date -r main.pdf '+%Y-%m-%d %H:%M' 2>/dev/null || echo "unknown")
ok "PDF: $WIN"
ok "Last modified: $MTIME"
[[ "${PAGES:-0}" -ge 27 ]] && ok "${PAGES} pages, ${KB} KB" || true

# ── FINAL VERDICT ──────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════"
printf "  PASS %-3d   FAIL %-3d   WARN %-3d\n" "$PASS" "$FAIL" "$WARN"
echo ""
if [[ "$FAIL" -eq 0 && "$WARN" -eq 0 ]]; then
  echo -e "  ${GREEN}✅  MANUSCRIPT IS SUBMISSION-READY${NC}"
elif [[ "$FAIL" -eq 0 ]]; then
  echo -e "  ${YELLOW}⚠️   $WARN warning(s) — review before submission${NC}"
else
  echo -e "  ${RED}❌  $FAIL issue(s) must be fixed before submission${NC}"
fi
echo "════════════════════════════════════════════════════════════"
