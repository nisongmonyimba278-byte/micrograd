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
has()  { grep -q "$1" "$2" 2>/dev/null; }

echo "════════════════════════════════════════════════════════════"
echo "  MANUSCRIPT VERIFICATION  —  $(date '+%Y-%m-%d %H:%M')"
echo "════════════════════════════════════════════════════════════"

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
LOG="$(pwd)/manuscript/main.log"

hdr "2. LaTeX fatal errors  (expect 0)"
N=$(grep "^!" "$LOG" 2>/dev/null | wc -l)
if [[ "$N" -eq 0 ]]; then ok "0 fatal errors"
else fail "$N fatal error(s)"; grep "^!" "$LOG" | head -6 | sed 's/^/      /'; fi

hdr "3. Undefined citations / labels  (expect 0)"
N=$(grep "LaTeX Warning:.*undefined" "$LOG" 2>/dev/null | wc -l)
if [[ "$N" -eq 0 ]]; then ok "0 undefined references"
else fail "$N undefined reference(s)"; grep "LaTeX Warning:.*undefined" "$LOG" | sed 's/^/      /'; fi

hdr "4. BibTeX warnings  (expect 0)"
N=$(grep "^Warning" /tmp/ms_bib.log 2>/dev/null | wc -l)
if [[ "$N" -eq 0 ]]; then ok "0 BibTeX warnings"
else fail "$N BibTeX warning(s)"; grep "^Warning" /tmp/ms_bib.log | sed 's/^/      /'; fi

hdr "5. Page count  (expect >= 27)"
PAGES=$(grep "Output written" "$LOG" | grep -oP '\d+ page' | grep -oP '\d+' || echo 0)
[[ "${PAGES:-0}" -ge 27 ]] && ok "$PAGES pages" || fail "$PAGES pages — section may be missing"

hdr "6. PDF size  (expect 300 KB - 1 MB)"
BYTES=$(stat -c%s main.pdf 2>/dev/null || echo 0); KB=$((BYTES/1024))
[[ $KB -ge 300 && $KB -le 1024 ]] && ok "${KB} KB" || warn "${KB} KB — check figures"

hdr "7. Required figures"
while IFS= read -r fig; do
  base=$(basename "$fig")
  if [[ -f "figures/$base" ]]; then ok "$base  ($(du -h "figures/$base" | cut -f1))"
  else fail "$base — MISSING from figures/"; fi
done < <(grep -h "includegraphics" manuscript/chapter*.tex 2>/dev/null \
         | grep -oP '(?<=\{)[^}]+\.(pdf|png)' | sort -u)

hdr "8. Required sections"
check_section() { has "$1" "manuscript/$2" && ok "$3" || fail "$3 — not found in $2"; }
check_section "Brinkman"                  "abstract.tex"                     "Abstract"
check_section "Nondimensional analysis"   "chapter2_mathematical_model.tex"  "Nondimensional analysis"
check_section "Finite element"            "chapter3_numerical_methods.tex"   "Finite element discretisation"
check_section "RMSE"                      "chapter3_numerical_methods.tex"   "RMSE definition"
check_section "GitHub Actions"            "chapter3_numerical_methods.tex"   "CI / reproducibility"
check_section "tab:metrics"               "chapter4_results.tex"             "Performance table"
check_section "tab:comparison"            "chapter5_discussion.tex"          "Literature comparison table"
check_section "sec:conclusion"            "chapter6_conclusion.tex"          "Conclusion"
check_section "micrograd"                 "chapter7_data_availability.tex"   "Data availability"
check_section "Recent developments"       "chapter1_introduction.tex"        "Recent developments paragraph"
check_section "sec:s1"                    "chapter8_appendices.tex"          "Appendix S1 (mesh convergence)"
check_section "sec:s10"                   "chapter8_appendices.tex"          "Appendix S10 (adjoint FD test)"
check_section "sec:s12"                   "chapter8_appendices.tex"          "Appendix S12 (double-peak)"

hdr "9. Required labels"
for label in \
  eq:brinkman eq:convdiff eq:rmse eq:Re eq:Pe eq:Da eq:Uc \
  eq:alpha eq:heaviside eq:sensitivity eq:oc eq:supg \
  sec:model sec:methods sec:results sec:discussion sec:conclusion \
  sec:brinkman sec:convdiff sec:nondim sec:supg sec:reproducibility sec:ci \
  fig:comparison fig:convergence fig:gallery fig:topology \
  tab:metrics tab:comparison; do
  grep -rq "\\\\label{$label}" manuscript/*.tex 2>/dev/null \
    && ok "\\label{$label}" || fail "\\label{$label} — missing"
done

hdr "10. Key citations in references.bib"
for key in \
  borrvall2003 whitesides2006 jeon2000 yang2020 \
  fenicsx2022 brooks1982 lazarov2011 wang2011 bendsoe2003 svanberg1987 \
  elman2014 geuzaine2009 giles2000 scroggs2022 \
  bezgin2023jaxfluids lu2021hpinn papadopoulos2022stokes \
  kou2025neural karniadakis2021pinns liu2025phasefield \
  wang2022christmastree kim2019finger fink2022automatic \
  GitHubActions2024 micrograd2025zenodo; do
  grep -q "$key" manuscript/references.bib 2>/dev/null \
    && ok "$key" || fail "$key — missing from references.bib"
done

hdr "11. Macro values"
check_macro() {
  local name="$1" desc="$2" line val
  line=$(grep "newcommand{\\\\$name}" manuscript/macros.tex 2>/dev/null || echo "")
  if [[ -z "$line" ]]; then fail "$name — not defined in macros.tex"; return; fi
  val=$(echo "$line" | grep -oP '(?<=\}\{).*(?=\}$)' \
        | sed 's/\\ensuremath{//g; s/}*$//; s/^[[:space:]]*//; s/[[:space:]]*//')
  if echo "$val" | grep -qP "nan|XXXXXXX|yourusername|TODO"; then
    fail "$name = $val  (placeholder)"
  else
    ok "$name = $val  ($desc)"
  fi
}
check_macro rmseTopOpt    "dimensionless RMSE"
check_macro rmseTopOptPP  "RMSE as percentage points"
check_macro hydResTopOpt  "optimised hydraulic resistance"
check_macro treeHydRes    "Christmas-tree hydraulic resistance"
check_macro treeRMSE      "Christmas-tree RMSE"
check_macro flowRateTopOpt "optimised flow rate"
check_macro finalJ        "final objective value"
check_macro reduction     "resistance reduction"
check_macro alphaMin      "alpha_min"
check_macro alphaMaxFinal "alpha_max final"
check_macro alphaMaxStart "alpha_max start"
check_macro Rey           "Re symbol"
check_macro Pe            "Pe symbol"
check_macro Da            "Da symbol"

hdr "12. Number consistency"
has "alpha_min=1e-4" micrograd/utilities.py \
  && ok "utilities.py alpha_min=1e-4 matches macro" \
  || fail "utilities.py alpha_min mismatch"
BAD=$(grep -rh "RMSE.*0\.\(098\|329\|584\)" manuscript/chapter*.tex \
      manuscript/abstract.tex 2>/dev/null || true)
[[ -z "$BAD" ]] && ok "No stale hardcoded RMSE found" \
  || fail "Stale hardcoded RMSE: $(echo "$BAD" | head -1 | cut -c1-70)"

hdr "13. Promotional language  (expect 0)"
NHITS=0
for phrase in "paves the way" "fully in.silico" "opens the door" \
  "unprecedented" "groundbreaking" "state-of-the-art" "exotic" \
  "supports for" "it is worth noting" "obviously" "clearly,"; do
  FILES=$(grep -ril "$phrase" manuscript/*.tex 2>/dev/null | tr '\n' ' ')
  [[ -n "$FILES" ]] && { warn "\"$phrase\" in: $FILES"; ((NHITS++)); }
done
[[ $NHITS -eq 0 ]] && ok "No promotional language found"

hdr "14. Mesh consistency"
has "80.times.20\|80\\\\times20" manuscript/chapter3_numerical_methods.tex \
  && ok "80x20 in Methods" || fail "80x20 missing from Methods"
has "80.times.20\|80\\\\times20" manuscript/abstract.tex \
  && ok "80x20 in Abstract" || fail "80x20 missing from Abstract"
! has "All results.*coarse\|All results.*20.times.5" manuscript/abstract.tex \
  && ok "Abstract does not misattribute results to 20x5" \
  || fail "Abstract still claims all results on 20x5"

hdr "15. alpha consistency"
has "10^{-4}" manuscript/chapter2_mathematical_model.tex \
  && ok "alpha_min=1e-4 in Chapter 2" || fail "alpha_min not found in Chapter 2"
has "10^{9}" manuscript/chapter2_mathematical_model.tex \
  && ok "alpha_max=1e9 in Chapter 2"  || fail "alpha_max=1e9 not found in Chapter 2"

hdr "16. Supplementary cross-references"
for sref in S1 S2 S3 S4 S10 S12; do
  if grep -rq "\\b${sref}\\b" manuscript/chapter[1-7]*.tex 2>/dev/null; then
    has "$sref\|sec:s${sref#S}" manuscript/chapter8_appendices.tex \
      && ok "$sref cited and present in appendices" \
      || fail "$sref cited but MISSING from appendices"
  fi
done

hdr "17. Recent literature (2021-2026)"
RECENT_OK=0
for year in 2021 2022 2023 2024 2025; do
  N=$(grep -c "year.*=.*{$year}" manuscript/references.bib 2>/dev/null || echo 0)
  if [[ "$N" -gt 0 ]]; then ok "$year: $N reference(s)"; ((RECENT_OK++))
  else warn "$year: 0 references"; fi
done
[[ $RECENT_OK -ge 4 ]] && ok "Recent coverage adequate" \
  || fail "Recent literature weak"

hdr "18. CI and reproducibility"
[[ -f ".github/workflows/ci.yml" ]] \
  && ok ".github/workflows/ci.yml present" || fail "ci.yml MISSING"
has "dolfinx" .github/workflows/ci.yml && ok "CI uses dolfinx container" \
  || warn "dolfinx not in ci.yml"
has "docker run\|Docker" manuscript/chapter3_numerical_methods.tex \
  && ok "Docker one-liner in Methods" || fail "Docker one-liner missing"
if grep -rq "XXXXXXX" manuscript/*.tex 2>/dev/null; then
  warn "Zenodo DOI placeholder — register at zenodo.org before submission"
else
  ok "No Zenodo placeholder found"
fi
[[ -f "environment.yaml" || -f "environment.yml" || -f "requirements.txt" ]] \
  && ok "Environment lockfile present" || warn "No environment lockfile found"

hdr "19. Grammar issues"
! has "supports for" manuscript/abstract.tex \
  && ok "Abstract: 'supports for' removed" \
  || fail "Abstract: 'supports for' grammar error present"
! { has "et~al.*2000\|et al.*2000" manuscript/chapter1_introduction.tex \
    && has "cite{jeon2005}" manuscript/chapter1_introduction.tex; } \
  && ok "Jeon citation consistent" \
  || fail "Jeon: prose says 2000 but cites jeon2005"

hdr "20. Output"
WIN=$(wslpath -w "$(pwd)/main.pdf" 2>/dev/null | tr -d '\r\n' \
      || echo "$(pwd)/main.pdf")
ok "PDF: $WIN"
ok "Modified: $(date -r main.pdf '+%Y-%m-%d %H:%M' 2>/dev/null)"
ok "${PAGES:-?} pages, ${KB} KB"

echo ""
echo "════════════════════════════════════════════════════════════"
printf "  PASS %-4d  FAIL %-4d  WARN %-4d\n" "$PASS" "$FAIL" "$WARN"
echo ""
if   [[ "$FAIL" -eq 0 && "$WARN" -eq 0 ]]; then
  echo -e "  ${GREEN}✅  SUBMISSION-READY${NC}"
elif [[ "$FAIL" -eq 0 ]]; then
  echo -e "  ${YELLOW}⚠️   $WARN warning(s) — review before submission${NC}"
else
  echo -e "  ${RED}❌  $FAIL issue(s) must be fixed before submission${NC}"
fi
echo "════════════════════════════════════════════════════════════"
