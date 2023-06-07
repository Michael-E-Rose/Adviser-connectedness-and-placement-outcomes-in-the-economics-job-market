clear all

import delimited "./880_distance_masters/adviser.csv"

encode(adv_scopus), gen(numericadv_scop)

********************************* Construction of variables
replace extensive=0 if extensive>=.

gen coauthor_dist_diff = coauthor_d_dist-coauthor_dist
gen coauthor_r_dist_diff = coauthor_r_dist-coauthor_dist

gen plc_close=0
replace plc_close=1 if coauthor_dist<5

********************************* Labels for most important variables
label variable extensive "Placed student"

label variable plc_scorew "Placement score"
label variable school_scorew "PhD school score"

label variable adv_euclid "Adviser Euclid"
label variable adv_experience "Adviser experience"

label variable adv_evwwin99std "Adviser centrality"
label variable first_evwwin99std_mean "Adviser's coauthors centrality"

label variable coauthor_dist "Social distance before death"
label variable coauthor_d_dist "Social distance after death"
label variable coauthor_dist_diff "Increase in social distance after death"
label variable coauthor_r_dist "Social distance after random death"
label variable coauthor_r_dist_diff "Increase in social distance after random death"
label variable citation_dist "Citation distance"

label variable plc_close "Distance to placement < 5"

********************************* Conditions
bysort numericadv_scop: egen totalextensiveadv = sum(extensive)
keep if totalextensiveadv>0 /* Drop advisers w/o placements */
drop totalextensiveadv
drop if missing(plc_scorew)

********************************* Summary stats
estimates clear
qui estpost summarize extensive coauthor_dist_diff coauthor_dist adv_euclid adv_experience school_scorew plc_scorew
esttab using ./990_output/Tables/distance_summary.tex, replace label ///
	cells("mean(fmt(2) label(Mean)) sd(fmt(2) label(SD)) min(fmt(2) label(Min.)) max(fmt(2) label(Max.))") ///
	stats(N, fmt(%9.0fc)) nogap nomtitle nonumber booktab alignment(rrrr)

********************************* Regressions on full sample	
* Adviser centrality included *
estimates clear
eststo: qui vcemway reg adv_evwwin99std first_evwwin99std_mean coauthor_dist citation_dist adv_euclid i.stu_year i.adv_experience school_scorew plc_scorew i.numericadv_scop, cl(numericadv_scop school_scopus)
qui qui estadd scalar N_adv = e(N_clust1)
eststo: qui vcemway ivprobit extensive (adv_evwwin99std = first_evwwin99std_mean) coauthor_dist citation_dist adv_euclid i.stu_year adv_experience school_scorew plc_scorew i.numericadv_scop, cl(numericadv_scop school_scopus)
qui qui estadd scalar N_adv = e(N_clust1)
eststo: qui vcemway ivreg2 extensive (adv_evwwin99std = first_evwwin99std_mean) coauthor_dist citation_dist adv_euclid i.stu_year adv_experience school_scorew plc_scorew i.numericadv_scop, cl(numericadv_scop school_scopus)
qui qui estadd scalar N_adv = e(N_clust1)
weakivtest
qui qui estadd scalar F_eff = r(F_eff)
eststo: qui vcemway reg extensive c.first_evwwin99std_mean##c.plc_scorew coauthor_dist citation_dist adv_euclid i.stu_year i.adv_experience school_scorew i.numericadv_scop, cl(numericadv_scop school_scopus)
qui qui estadd scalar N_adv = e(N_clust1)
esttab using ./990_output/Tables/distance_2sls_centrality.tex, replace ///
	order(adv_evwwin99std) noconstant ///
	alignment(D{.}{.}{-1}) label substitute("\_" "_") delimiter(_tab "&") booktabs ///
	wrap varwidth(30) modelwidth(15) legend nonote ///
	star(* 0.1 ** 0.05 *** 0.01) b(3) se(3) ///
	stats(N N_adv F_eff, fmt(%9.0fc %9.0fc %13.1fc) labels("N" "\# of advisers" "Effective F")) ///
	indicate("Adviser FE = *.numericadv_scop*" "Adviser experience FE = *adv_experience" "Graduation year FE = *.stu_year*", labels(\checkmark ""))

* Social proximity threshold effects *
estimates clear
eststo: qui	vcemway reg extensive plc_close i.stu_year adv_euclid i.adv_experience school_scorew plc_scorew i.numericadv_scop, cl(numericadv_scop school_scopus)
qui qui estadd scalar N_adv = e(N_clust1)
* Excluding coauthor dept
eststo: qui	vcemway reg extensive plc_close i.stu_year adv_euclid i.adv_experience school_scorew plc_scorew i.numericadv_scop if coauthor_dist>1, cl(numericadv_scop school_scopus)
qui qui estadd scalar N_adv = e(N_clust1)
* Only third neighbours
eststo: qui	vcemway reg extensive plc_close i.stu_year adv_euclid i.adv_experience school_scorew plc_scorew i.numericadv_scop if coauthor_dist>2, cl(numericadv_scop school_scopus)
qui qui estadd scalar N_adv = e(N_clust1)
* Write out
esttab using ./990_output/Tables/distance_ols_proximity.tex, replace ///
	noconstant ///
	alignment(D{.}{.}{-1}) label substitute("\_" "_") delimiter(_tab "&") booktabs ///
	wrap varwidth(30) modelwidth(15) legend nonote ///
	star(* 0.1 ** 0.05 *** 0.01) b(3) se(3) ///
	stats(N N_adv, fmt(%9.0fc %9.0fc) labels("N" "\# of advisers" )) ///
	indicate("Adviser FE = *.numericadv_scop*" "Adviser experience FE = *.adv_experience" "Graduation year FE = *.stu_year*", labels(\checkmark ""))

* Distance *
preserve
keep if extensive == 1
estimates clear
eststo: qui vcemway reg plc_close first_evwwin99std_mean adv_euclid i.stu_year i.adv_experience school_scorew i.numericadv_scop, cl(numericadv_scop school_scopus)
qui qui estadd scalar N_adv = e(N_clust1)
eststo: qui ivreg2 plc_close (adv_evwwin99std = first_evwwin99std_mean) adv_euclid i.stu_year i.adv_experience school_scorew i.numericadv_scop, cl(numericadv_scop school_scopus)
qui qui estadd scalar N_adv = e(N_clust1)
qui weakivtest
qui qui estadd scalar F_eff = r(F_eff)
eststo: qui vcemway reg coauthor_d_dist first_evwwin99std_mean adv_euclid i.stu_year i.adv_experience school_scorew i.numericadv_scop if extensive == 1, cl(numericadv_scop school_scopus)
qui qui estadd scalar N_adv = e(N_clust1)
eststo: qui	ivreg2 coauthor_d_dist (adv_evwwin99std = first_evwwin99std_mean) adv_euclid i.stu_year i.adv_experience school_scorew i.numericadv_scop if extensive == 1, cl(numericadv_scop school_scopus)
qui qui estadd scalar N_adv = e(N_clust1)
qui weakivtest
qui qui estadd scalar F_eff = r(F_eff)
esttab using ./990_output/Tables/distance_2sls_closeplacement.tex, replace ///
	order(adv_evwwin99std first_evwwin99std_mean) noconstant ///
	alignment(D{.}{.}{-1}) label substitute("\_" "_") delimiter(_tab "&") booktabs ///
	wrap varwidth(30) modelwidth(15) legend nonote ///
	star(* 0.1 ** 0.05 *** 0.01) b(3) se(3) ///
	stats(N N_adv F_eff, fmt(%9.0fc %9.0fc %13.1fc) labels("N" "\# of advisers" "Effective F")) ///
	indicate("Adviser FE = *.numericadv_scop*" "Adviser experience FE = *.adv_experience" "Graduation year FE = *.stu_year*", labels(\checkmark ""))
restore

* All other regressions *
estimates clear
* OLS
eststo: qui vcemway reg extensive coauthor_dist_diff coauthor_dist adv_euclid school_scorew plc_scorew i.stu_year i.adv_experience i.numericadv_scop, cl(numericadv_scop school_scopus)
qui qui estadd scalar N_adv_base = e(N_clust1)
qui estadd ysumm
qui qui estadd scalar means_base = e(ymean)
* with Citation control
eststo: qui vcemway reg extensive coauthor_dist_diff coauthor_dist adv_euclid citation_dist school_scorew plc_scorew i.stu_year i.adv_experience i.numericadv_scop, cl(numericadv_scop school_scopus)
qui qui estadd scalar N_adv_citation = e(N_clust1)
qui estadd ysumm
qui qui estadd scalar means_citation = e(ymean)
* Logit
eststo: qui vcemway logit extensive coauthor_dist_diff coauthor_dist adv_euclid school_scorew plc_scorew i.stu_year i.adv_experience i.numericadv_scop, cl(numericadv_scop school_scopus)
qui qui estadd scalar N_adv_logit = e(N_clust1)
qui estadd ysumm
qui qui estadd scalar means_logit = e(ymean)
* OLS random
eststo: qui vcemway reg extensive coauthor_r_dist_diff coauthor_dist adv_euclid school_scorew plc_scorew i.stu_year i.adv_experience i.numericadv_scop, cl(numericadv_scop school_scopus)
qui qui estadd scalar N_adv_random = e(N_clust1)

********************************* Regressions on institutions that hired
drop if missing(hiring)

* OLS
eststo: qui vcemway reg extensive coauthor_dist_diff coauthor_dist adv_euclid school_scorew plc_scorew i.stu_year i.adv_experience i.numericadv_scop, cl(numericadv_scop school_scopus)
qui qui estadd scalar N_adv_base = e(N_clust1)
qui estadd ysumm
qui qui estadd scalar means_base = e(ymean)
* with Citation control
eststo: qui vcemway reg extensive coauthor_dist_diff coauthor_dist adv_euclid citation_dist school_scorew plc_scorew i.stu_year i.adv_experience i.numericadv_scop, cl(numericadv_scop school_scopus)
qui qui estadd scalar N_adv_citation = e(N_clust1)
qui estadd ysumm
qui qui estadd scalar means_citation = e(ymean)
* Logit
eststo: qui vcemway logit extensive coauthor_dist_diff coauthor_dist adv_euclid school_scorew plc_scorew i.stu_year i.adv_experience i.numericadv_scop, cl(numericadv_scop school_scopus)
qui qui estadd scalar N_adv_logit = e(N_clust1)
qui estadd ysumm
qui qui estadd scalar means_logit = e(ymean)
* OLS random
eststo: qui vcemway reg extensive coauthor_r_dist_diff coauthor_dist adv_euclid school_scorew plc_scorew i.stu_year i.adv_experience i.numericadv_scop, cl(numericadv_scop school_scopus)
qui qui estadd scalar N_adv_random = e(N_clust1)

********************************* Regressions on institutions tha hired and with PhD programs
keep if plc_phd==1
bysort numericadv_scop: egen totalextensiveadv = sum(extensive)
keep if totalextensiveadv>0 /* Drop advisers w/o placements */

* OLS
eststo: qui vcemway reg extensive coauthor_dist_diff coauthor_dist adv_euclid school_scorew plc_scorew i.stu_year i.adv_experience i.numericadv_scop, cl(numericadv_scop school_scopus)
qui qui estadd scalar N_adv_base = e(N_clust1)
qui estadd ysumm
qui qui estadd scalar means_base = e(ymean)
* with Citation control
eststo: qui vcemway reg extensive coauthor_dist_diff coauthor_dist adv_euclid citation_dist school_scorew plc_scorew i.stu_year i.adv_experience i.numericadv_scop, cl(numericadv_scop school_scopus)
qui qui estadd scalar N_adv_citation = e(N_clust1)
qui estadd ysumm
qui qui estadd scalar means_citation = e(ymean)
* Logit
eststo: qui vcemway logit extensive coauthor_dist_diff coauthor_dist adv_euclid school_scorew plc_scorew i.stu_year i.adv_experience i.numericadv_scop, cl(numericadv_scop school_scopus)
qui qui estadd scalar N_adv_logit = e(N_clust1)
qui estadd ysumm
qui qui estadd scalar means_logit = e(ymean)
* OLS random
eststo: qui vcemway reg extensive coauthor_r_dist_diff coauthor_dist adv_euclid school_scorew plc_scorew i.stu_year i.adv_experience i.numericadv_scop, cl(numericadv_scop school_scopus)
qui qui estadd scalar N_adv_random = e(N_clust1)

* Write out *
esttab est1 est5 est9 using ./990_output/Tables/distance_ols_baseline.tex, replace ///
	order(coauthor_dist_diff coauthor_dist) ///
	alignment(D{.}{.}{-1}) label substitute("\_" "_") delimiter(_tab "&") booktabs ///
	wrap varwidth(30) modelwidth(15) legend nonote ///
	star(* 0.1 ** 0.05 *** 0.01) b(3) se(3) ///
	stats(N N_adv_base means_base, fmt(%9.0fc %9.0f %9.3f) labels("N" "\# of advisers" "Mean")) ///
	indicate("Adviser FE = *.numericadv_scop*" "Adviser experience FE = *.adv_experience" "Graduation year FE = *.stu_year*", labels(\checkmark ""))

esttab est2 est6 est10 using ./990_output/Tables/distance_ols_citation.tex, replace ///
	order(coauthor_dist_diff coauthor_dist citation_dist citation_dist) noconstant ///
	alignment(D{.}{.}{-1}) label substitute("\_" "_") delimiter(_tab "&") booktabs ///
	wrap varwidth(30) modelwidth(15) legend nonote ///
	star(* 0.1 ** 0.05 *** 0.01) b(3) se(3) ///
	stats(N N_adv_citation means_citation, fmt(%9.0fc %9.0f %9.3f) labels("N" "\# of advisers" "Mean")) ///
	indicate("Adviser FE = *.numericadv_scop*" "Adviser experience FE = *.adv_experience" "Graduation year FE = *.stu_year*", labels(\checkmark ""))

esttab est3 est7 est11 using ./990_output/Tables/distance_logit_baseline.tex, replace ///
	order(coauthor_dist_diff coauthor_dist) ///
	alignment(D{.}{.}{-1}) label substitute("\_" "_") delimiter(_tab "&") booktabs ///
	wrap varwidth(30) modelwidth(15) legend nonote ///
	star(* 0.1 ** 0.05 *** 0.01) b(3) se(3) ///
	stats(N N_adv_logit means_logit, fmt(%9.0fc %9.0f %9.3f) labels("N" "\# of advisers" "Mean")) ///
	indicate("Adviser FE = *.numericadv_scop*" "Adviser experience FE = *.adv_experience" "Graduation year FE = *.stu_year*", labels(\checkmark ""))

esttab est4 est8 est12 using ./990_output/Tables/distance_ols_random.tex, replace ///
	order(coauthor_r_dist_diff coauthor_dist) ///
	alignment(D{.}{.}{-1}) label substitute("\_" "_") delimiter(_tab "&") booktabs ///
	wrap varwidth(30) modelwidth(15) legend nonote ///
	star(* 0.1 ** 0.05 *** 0.01) b(3) se(3) ///
	stats(N N_adv_random, fmt(%9.0fc %9.0f) labels("N" "\# of advisers")) ///
	indicate("Adviser FE = *.numericadv_scop*" "Adviser experience FE = *.adv_experience" "Graduation year FE = *.stu_year*", labels(\checkmark ""))
