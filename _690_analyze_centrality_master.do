clear all

import delimited "./680_centrality_masters/master.csv"

******** Construction of variables************

drop if adv_evwwin99std == .

foreach v of varlist best_adviser stu_jel plc_type stu_school stu_sex {
	encode `v', gen(new`v')
	drop `v'
	rename new`v' `v'
}

gen diffrank = change_rankw-plc_rankw
gen changejobtime = change_year-plc_year
gen diffrankdummy=1
replace diffrankdummy=0 if diffrank<0
replace diffrankdummy=0 if diffrank==0

gen school_rankw_top=0
replace school_rankw_top=1 if school_rankw_quartile==1 | school_rankw_quartile==2

gen centralitydeathshock_adv = adv_evwwin99std_d-adv_evwwin99std
gen centralitychange_adv = adv_evwwin99std_l1-adv_evwwin99std

replace third_dec=1 if third_dec>1 & third_dec<5

encode( stu_plc ), gen(stu_plc_numeric)

********************************* Labels for most important variables

label variable adv_euclid "Adviser Euclid"
label variable adv_euclid_quartile "Adviser Euclid quartile"
label variable adv_experience "Adviser experience"
label variable adv_experience_quartile "Adviser experience quartile"

label variable adv_evw "Adviser eigenvector score"
label variable first_evw_mean "Adviser neigh. mean eigenvector score"
label variable second_evw_mean "Adviser 2nd neigh. mean eigenvector score"

label variable adv_deg "Adviser degree"
label variable first_deg_mean "Adviser neigh. mean degree"
label variable second_deg_mean "Adviser 2nd neigh. mean degree"

label variable plc_scorewstd "Placement score"
label variable adv_evwstd "Std. adviser centrality"
label variable adv_evwwin99std "Adviser centrality"
label variable first_evwstd_mean "Std. adviser's coauthors centrality"
label variable first_evwwin99std_mean "Adviser's coauthors centrality"
label variable second_evwstd_mean "Std. adviser's 2nd neigh. centrality"
label variable second_evwwin99std_mean "Adviser's second neighbour centrality'"

replace stu_sex=0 if stu_sex==1
replace stu_sex=1 if stu_sex==2
label variable stu_sex "Student male"
label define Student_sex 0 "Student female" 1 "Student male"
label values stu_sex Student_sex

label variable plc_rankw "Placement rank"
label variable plc_scorew "Placement score"
label variable school_rankw "PhD school rank"
label variable school_scorew "PhD school score"
label define top_labels 1 "Top 20 PhD school"
label values school_rankw_top top_labels
label variable school_rankw_quartile "School rank quartile"
label define quartile_labels 1 "Top quartile school" 2 "2nd quartile schools" 3 "3rd quartile school" 4 "Bottom quartile school"
label values school_rankw_quartile quartile_labels

label variable plc_same06 "Same affiliation 6 years later"
label variable plc_same07 "Same affiliation 7 years later"

label variable citestock_growth9699 "Citation growth rate 96-99"
label variable citeflow_growth1 "Citation growth last year"
label variable citestock_growth3 "Citation growth past 3 years"

label variable stu_citestock_5p "5-year student citations"

label variable adv_evwwin99std_l1 "Adviser centrality in t+1"
label variable first_evwwin99std_mean_l1 "Adviser's coauthors centrality in t+1"
label variable second_evwwin99std_mean_l1 "Adviser's 2nd neigh. centrality in t+1"

label variable adv_evwwin99std_l2 "Adviser centrality in t+2"
label variable first_evwwin99std_mean_l2 "Adviser's coauthors centrality in t+2"
label variable second_evwwin99std_mean_l2 "Adviser's 2nd neigh. centrality in t+2"

label variable adv_dist "Social distance adviser to placement"

label variable centralitydeathshock_adv "Change in centrality due to death"

label variable diffrank "Rank difference"
label variable diffrankdummy "Second plc worse than first"

label variable first_dec "Coauthor died"
label variable second_dec "Second neighbour died"
label variable third_dec "Third neighbour died"

********************************* Logit on Match quality Regressions
estimates clear
local tenurevars = "plc_same06 plc_same07"
foreach v of varlist `tenurevars' {
	eststo: qui vcemway logit `v' adv_evwwin99std adv_euclid i.adv_experience  ib1.stu_sex school_scorew plc_scorew i.stu_year i.stu_jel i.best_adviser if adv_occ>1, cl(best_adviser stu_school)
	qui estadd scalar N_adv = e(N_clust1)
	eststo: qui vcemway logit `v' adv_evwwin99std adv_euclid i.adv_experience ib1.stu_sex school_scorew plc_scorew i.stu_year i.stu_jel, cl(best_adviser stu_school)
	qui estadd scalar N_adv = e(N_clust1)
}
esttab using ./990_output/Tables/centrality_logit_match.tex, replace ///
	drop(1.stu_sex) ///
	alignment(D{.}{.}{-1}) label substitute("\_" "_") delimiter(_tab "&") booktabs ///
	wrap varwidth(30) modelwidth(15) legend nonote ///
	star(* 0.1 ** 0.05 *** 0.01) b(3) se(3) ///
	stats(N N_adv, fmt(%9.0fc %9.0fc) labels("N" "\# of advisers")) ///
	indicate("Adviser FE = *.best_adviser*" "Adviser experience FE = *.adv_experience" "Field FE = *.stu_jel*" "Graduation year FE = *.stu_year**", labels(\checkmark ""))

********************************* Student citations
preserve
estimates clear
eststo: qui vcemway reg stu_citestock_5p adv_evwwin99std adv_euclid ib1.stu_sex school_rankw plc_rankw i.adv_experience i.stu_year i.stu_jel i.best_adviser, cl (stu_school best_adviser)
qui estadd scalar N_adv = e(N_clust1)
keep if adv_occ > 1
eststo: qui vcemway reg stu_citestock_5p adv_evwwin99std adv_euclid ib1.stu_sex school_rankw plc_rankw i.adv_experience i.stu_year i.stu_jel i.best_adviser, cl (stu_school best_adviser)
qui estadd scalar N_adv = e(N_clust1)
eststo: qui ivreg2 stu_citestock_5p (adv_evwwin99std = first_evwwin99std_mean) adv_euclid ib1.stu_sex school_rankw plc_rankw i.adv_experience i.stu_year i.stu_jel i.best_adviser, cl (stu_school best_adviser)
qui estadd scalar N_adv = e(N_clust1)
qui weakivtest
qui estadd scalar F_eff = r(F_eff)
esttab using ./990_output/Tables/centrality_reg_stucitation.tex, replace ///
	nobase ///
	alignment(D{.}{.}{-1}) label substitute("\_" "_") delimiter(_tab "&") booktabs ///
	wrap varwidth(30) modelwidth(15) legend nonote ///
	star(* 0.1 ** 0.05 *** 0.01) b(3) se(3) ///
	stats(N N_adv F_eff, fmt(%9.0fc %9.0fc %13.1fc) labels("N" "\# of advisers" "Effective F")) ///
	indicate("Adviser FE = *.best_adviser*" "Adviser experience FE = *.adv_experience" "Field FE = *.stu_jel*" "Graduation year FE = *.stu_year**", labels(\checkmark ""))
restore

********************************* Drop observations where the adviser did not place two student in two different years

keep if adv_occ > 1


********************************* Adviser distance
estimates clear
eststo: qui ivreg2 adv_dist (adv_evwwin99std = first_evwwin99std_mean) adv_euclid i.adv_experience i.best_adviser ib1.stu_sex school_rankw i.stu_year i.stu_jel, cl(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
qui weakivtest
qui estadd scalar F_eff = r(F_eff)
eststo: qui ivreg2 adv_dist (adv_evwwin99std = second_evwwin99std_mean) adv_euclid i.adv_experience i.best_adviser ib1.stu_sex school_rankw i.stu_year i.stu_jel, cl(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
qui weakivtest
qui estadd scalar F_eff = r(F_eff)
esttab using ./990_output/Tables/centrality_2sls_distance.tex, replace ///
	order(adv_evwwin99std) drop(1.stu_sex) ///
	alignment(D{.}{.}{-1}) label substitute("\_" "_") delimiter(_tab "&") booktabs ///
	wrap varwidth(30) modelwidth(15) legend nonote ///
	star(* 0.1 ** 0.05 *** 0.01) b(3) se(3) ///
	stats(N N_adv F_eff, fmt(%9.0fc %9.0fc %13.1fc) labels("N" "\# of advisers" "Effective F")) ///
	indicate("Adviser FE = *.best_adviser*" "Adviser experience FE = *.adv_experience" "Field FE = *.stu_jel*" "Graduation year FE = *.stu_year**", labels(\checkmark ""))


drop if plc_scorewstd == .

********************************* Summary stats
estimates clear
qui estpost summarize plc_scorewstd adv_evwwin99std first_evwwin99std_mean adv_euclid adv_experience stu_sex school_rankw if adv_occ>1
esttab using ./990_output/Tables/centrality_summary.tex, replace label ///
	cells("mean(fmt(2) label(Mean)) sd(fmt(2) label(SD)) min(fmt(2) label(Min.)) max(fmt(2) label(Max.))") ///
	nogap nomtitle nonumber booktab alignment(rrrr)

********************************* OLS Baseline
estimates clear
eststo: qui vcemway reg plc_scorewstd adv_evwwin99std adv_euclid i.adv_experience i.best_adviser ib1.stu_sex school_rankw i.stu_jel i.stu_year, cluster(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
eststo: qui vcemway reg plc_scorewstd first_evwwin99std_mean adv_euclid i.adv_experience i.best_adviser ib1.stu_sex school_rankw i.stu_jel i.stu_year, cluster(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
eststo: qui vcemway reg plc_scorewstd second_evwwin99std_mean adv_euclid i.adv_experience i.best_adviser ib1.stu_sex school_rankw i.stu_jel i.stu_year, cluster(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
esttab using ./990_output/Tables/centrality_ols_baseline.tex, replace ///
	order(adv_evwwin99std first_evwwin99std_mean second_evwwin99std_mean) nobase ///
	alignment(D{.}{.}{-1}) label substitute("\_" "_") delimiter(_tab "&") booktabs ///
	wrap varwidth(30) modelwidth(15) legend nonote ///
	star(* 0.1 ** 0.05 *** 0.01) b(3) se(3) ///
	stats(N N_adv, fmt(%9.0fc %9.0fc) labels("N" "\# of advisers")) ///
	indicate("Adviser FE = *.best_adviser*" "Adviser experience FE = *.adv_experience" "Field FE = *.stu_jel*" "Graduation year FE = *.stu_year**", labels(\checkmark ""))


********************************* 2SLS IV Baseline
estimates clear
eststo: ivreg2 plc_scorewstd (adv_evwwin99std = first_evwwin99std_mean) adv_euclid i.adv_experience i.best_adviser ib1.stu_sex school_rankw i.stu_year i.stu_jel, cl(best_adviser stu_school) first savefirst savefprefix(st1)
qui estadd scalar N_adv = e(N_clust1)
qui weakivtest
qui estadd scalar F_eff = r(F_eff)
eststo: qui ivreg2 plc_scorewstd (adv_evwwin99std = second_evwwin99std_mean) adv_euclid i.adv_experience i.best_adviser ib1.stu_sex school_rankw i.stu_year i.stu_jel, cl(best_adviser stu_school) first savefirst savefprefix(st2)
qui estadd scalar N_adv = e(N_clust1)
qui weakivtest
qui estadd scalar F_eff = r(F_eff)
esttab st1* st2* est1 est2 using ./990_output/Tables/centrality_2sls_baseline.tex, replace ///
	order(adv_evwwin99std first_evwwin99std_mean second_evwwin99std_mean) nobase ///
	alignment(D{.}{.}{-1}) label substitute("\_" "_") delimiter(_tab "&") booktabs ///
	wrap varwidth(30) modelwidth(15) legend nonote ///
	star(* 0.1 ** 0.05 *** 0.01) b(3) se(3) ///
	stats(N N_adv F_eff, fmt(%9.0fc %9.0fc %13.1fc) labels("N" "\# of advisers" "Effective F")) ///
	indicate("Adviser FE = *.best_adviser*" "Adviser experience FE= *.adv_experience" "Field FE = *.stu_jel*" "Graduation year FE = *.stu_year**", labels(\checkmark ""))

* For comparison ivreghdfe, which correctly handles fixed effects but does not allow for weakivtest:
ivreghdfe plc_scorewstd ib1.stu_sex school_rankw adv_euclid (adv_evwwin99std=first_evwwin99std_mean), absorb(best_adviser adv_experience stu_year* stu_jel) cl(best_adviser stu_school) first

********************************* Adviser citations
estimates clear
eststo: qui ivreg2 plc_scorewstd (adv_evwwin99std = first_evwwin99std_mean) citestock_growth9699 citestock_growth3 citeflow_growth1 adv_euclid i.adv_experience i.best_adviser ib1.stu_sex school_rankw i.stu_year i.stu_jel, cl(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
qui weakivtest
qui estadd scalar F_eff = r(F_eff)
eststo: qui ivreg2 plc_scorewstd (adv_evwwin99std = second_evwwin99std_mean) citestock_growth9699 citestock_growth3 citeflow_growth1 adv_euclid i.adv_experience i.best_adviser ib1.stu_sex school_rankw i.stu_year i.stu_jel, cl(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
qui weakivtest
qui estadd scalar F_eff = r(F_eff)
esttab using ./990_output/Tables/centrality_2sls_advcitation.tex, replace ///
	nobase ///
	alignment(D{.}{.}{-1}) label substitute("\_" "_") delimiter(_tab "&") booktabs ///
	wrap varwidth(30) modelwidth(15) legend nonote ///
	star(* 0.1 ** 0.05 *** 0.01) b(3) se(3) ///
	stats(N N_adv F_eff, fmt(%9.0fc %9.0fc %13.1fc) labels("N" "\# of advisers" "Effective F")) ///
	indicate("Adviser FE = *.best_adviser*" "Adviser experience FE = *.adv_experience" "Field FE = *.stu_jel*" "Graduation year FE = *.stu_year**", labels(\checkmark ""))

********************************* Centrality leads
estimates clear
eststo: qui ivreg2 plc_scorewstd (adv_evwwin99std_l1 = first_evwwin99std_mean_l1) adv_euclid i.adv_experience i.best_adviser ib1.stu_sex school_rankw i.stu_year i.stu_jel, cl(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
qui weakivtest
qui estadd scalar F_eff = r(F_eff)
eststo: qui ivreg2 plc_scorewstd (adv_evwwin99std_l2 = first_evwwin99std_mean_l2) adv_euclid i.adv_experience i.best_adviser ib1.stu_sex school_rankw i.stu_year i.stu_jel, cl(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
qui weakivtest
qui estadd scalar F_eff = r(F_eff)
eststo: qui ivreg2 plc_scorewstd (adv_evwwin99std_l1 = second_evwwin99std_mean_l1) adv_euclid i.adv_experience i.best_adviser ib1.stu_sex school_rankw i.stu_year i.stu_jel, cl(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
qui weakivtest
qui estadd scalar F_eff = r(F_eff)
eststo: qui ivreg2 plc_scorewstd (adv_evwwin99std_l2 = second_evwwin99std_mean_l2) adv_euclid i.adv_experience i.best_adviser ib1.stu_sex school_rankw i.stu_year i.stu_jel, cl(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
qui weakivtest
qui estadd scalar F_eff = r(F_eff)
esttab using ./990_output/Tables/centrality_2sls_leads.tex, replace ///
	order(adv_evwwin99std_l1 adv_evwwin99std_l2) nobase ///
	alignment(D{.}{.}{-1}) label substitute("\_" "_") delimiter(_tab "&") booktabs ///
	wrap varwidth(30) modelwidth(15) legend nonote ///
	star(* 0.1 ** 0.05 *** 0.01) b(3) se(3) ///
	stats(N N_adv F_eff, fmt(%9.0fc %9.0fc %13.1fc) labels("N" "\# of advisers" "Effective F")) ///
	indicate("Adviser FE = *.best_adviser*" "Adviser experience FE = *.adv_experience" "Field FE = *.stu_jel*" "Graduation year FE = *.stu_year**", labels(\checkmark ""))

********************************* Experience interacted with Euclid
estimates clear
eststo: qui ivreg2 plc_scorewstd (adv_evwwin99std = first_evwwin99std_mean) adv_euclid c.adv_experience##c.adv_euclid c.adv_experience##c.adv_experience i.best_adviser ib1.stu_sex school_rankw i.stu_year i.stu_jel, cl(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
qui weakivtest
qui estadd scalar F_eff = r(F_eff)
eststo: qui ivreg2 plc_scorewstd (adv_evwwin99std = first_evwwin99std_mean) adv_euclid c.adv_experience##i.adv_euclid_quartile c.adv_experience##c.adv_experience i.best_adviser ib1.stu_sex school_rankw i.stu_year i.stu_jel, cl(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
qui weakivtest
qui estadd scalar F_eff = r(F_eff)
eststo: qui ivreg2 plc_scorewstd (adv_evwwin99std = first_evwwin99std_mean) adv_euclid i.adv_experience_quartile##i.adv_euclid_quartile c.adv_experience##c.adv_experience i.best_adviser ib1.stu_sex school_rankw i.stu_year i.stu_jel, cl(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
qui weakivtest
qui estadd scalar F_eff = r(F_eff)
esttab using ./990_output/Tables/centrality_2sls_experience-euclid.tex, replace ///
	drop(*.adv_experience_quartile *.adv_euclid_quartile) nobase ///
	alignment(D{.}{.}{-1}) label substitute("\_" "_") delimiter(_tab "&") booktabs ///
	wrap varwidth(30) modelwidth(15) legend nonote eqlabels(none) ///
	star(* 0.1 ** 0.05 *** 0.01) b(3) se(3) ///
	coeflabels(c.adv_experience#c.adv_experience "Adv. experience$^2$") ///
	stats(N N_adv F_eff, fmt(%9.0fc %9.0fc %13.1fc) labels("N" "\# of advisers" "Effective F")) ///
	indicate("Adviser FE = *.best_adviser*" "Field FE = *.stu_jel*" "Graduation year FE = *.stu_year**", labels(\checkmark ""))

********************************* Centrality after deaths
estimates clear
eststo: qui ivreg2 plc_scorewstd (adv_evwwin99std = first_evwwin99std_mean) adv_euclid first_dec second_dec third_dec ib1.stu_sex school_rankw i.stu_year i.stu_jel i.adv_experience i.best_adviser, first savefirst savefprefix(st1) cl(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
qui weakivtest
qui estadd scalar F_eff = r(F_eff)
eststo: qui vcemway reg plc_scorewstd centralitydeathshock_adv adv_euclid i.adv_experience i.best_adviser ib1.stu_sex school_rankw i.stu_year i.stu_jel, cl(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
esttab st1* est1 est2 using ./990_output/Tables/centrality_reg_death.tex, replace ///
	order(adv_evwwin99std first_evwwin99std_mean centralitydeathshock_adv) nobase ///
	alignment(D{.}{.}{-1}) label substitute("\_" "_") delimiter(_tab "&") booktabs ///
	wrap varwidth(30) modelwidth(15) legend nonote ///
	star(* 0.1 ** 0.05 *** 0.01) b(3) se(3) ///
	stats(N N_adv F_eff, fmt(%9.0fc %9.0fc %13.1fc) labels("N" "\# of advisers" "Effective F")) ///
	indicate("Adviser FE = *.best_adviser*" "Adviser experience FE = *.adv_experience" "Field FE = *.stu_jel*" "Graduation year FE = *.stu_year**", labels(\checkmark ""))

********************************* Degree
estimates clear
eststo: qui ivreg2 plc_scorewstd (adv_deg = first_deg_mean) adv_euclid i.adv_experience i.best_adviser ib1.stu_sex school_rankw i.stu_year i.stu_jel, first savefirst savefprefix(st1) cl(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
qui weakivtest
qui estadd scalar F_eff = r(F_eff)
eststo: qui vcemway reg plc_scorewstd adv_deg adv_euclid i.adv_experience i.best_adviser ib1.stu_sex school_rankw i.stu_year i.stu_jel, cl(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
eststo: qui vcemway reg plc_scorewstd first_deg_mean adv_euclid i.adv_experience i.best_adviser ib1.stu_sex school_rankw i.stu_year i.stu_jel, cl(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
esttab st1* est1 est2 est3 using ./990_output/Tables/centrality_reg_degree.tex, replace ///
	order(adv_deg first_deg_mean) nobase ///
	alignment(D{.}{.}{-1}) label substitute("\_" "_") delimiter(_tab "&") booktabs ///
	wrap varwidth(30) modelwidth(15) legend nonote ///
	star(* 0.1 ** 0.05 *** 0.01) b(3) se(3) ///
	stats(N N_adv F_eff, fmt(%9.0fc %9.0fc %13.1fc) labels("N" "\# of advisers" "Effective F")) ///
	indicate("Adviser FE = *.best_adviser*" "Adviser experience FE = *.adv_experience" "Field FE = *.stu_jel*" "Graduation year FE = *.stu_year**", labels(\checkmark ""))

********************************* 2SLS IV on second placement
estimates clear
* Indicator for worse placement
eststo: qui ivreg2 diffrankdummy (adv_evwwin99std = first_evwwin99std_mean) adv_euclid i.adv_experience ib1.stu_sex school_scorew plc_scorew i.stu_year i.stu_jel i.best_adviser if changejobtime<8, cl(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
qui weakivtest
qui estadd scalar F_eff = r(F_eff)
* Difference in rank
eststo: qui ivreg2 diffrank (adv_evwwin99std = first_evwwin99std_mean) adv_euclid i.adv_experience ib1.stu_sex school_scorew plc_scorew i.stu_year i.stu_jel i.best_adviser if changejobtime<8, cl(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
qui weakivtest
qui estadd scalar F_eff = r(F_eff)
esttab using ./990_output/Tables/centrality_2sls_change.tex, replace ///
	nobase ///
	alignment(D{.}{.}{-1}) label substitute("\_" "_") delimiter(_tab "&") booktabs ///
	wrap varwidth(30) modelwidth(15) legend nonote ///
	star(* 0.1 ** 0.05 *** 0.01) b(3) se(3) ///
	stats(N N_adv F_eff, fmt(%9.0fc %9.0fc %13.1fc) labels("N" "\# of advisers" "Effective F")) ///
	indicate("Adviser FE = *.best_adviser*" "Adviser experience FE = *.adv_experience" "Field FE = *.stu_jel*" "Graduation year FE = *.stu_year**", labels(\checkmark ""))

********************************* School rank polynomials
estimates clear
eststo: qui ivreg2 plc_scorewstd (adv_evwwin99std = first_evwwin99std_mean) adv_euclid i.adv_experience ib1.stu_sex c.school_rankw##c.school_rankw i.stu_year i.stu_jel i.best_adviser, cl(best_adviser stu_school) first savefirst savefprefix(st1)
qui estadd scalar N_adv = e(N_clust1)
qui weakivtest
qui estadd scalar F_eff = r(F_eff)
eststo: qui ivreg2 plc_scorewstd (adv_evwwin99std = first_evwwin99std_mean) adv_euclid i.adv_experience ib1.stu_sex c.school_rankw##c.school_rankw##c.school_rankw i.stu_year i.stu_jel i.best_adviser, cl(best_adviser stu_school) first savefirst savefprefix(st2)
qui estadd scalar N_adv = e(N_clust1)
qui weakivtest
qui estadd scalar F_eff = r(F_eff)
esttab st1* st2* est1 est2 using ./990_output/Tables/centrality_2sls_polynomials.tex, replace ///
	order(adv_evwwin99std first_evwwin99std_mean) nobase ///
	alignment(D{.}{.}{-1}) label substitute("\_" "_") delimiter(_tab "&") booktabs ///
	wrap varwidth(30) modelwidth(15) legend nonote ///
	star(* 0.1 ** 0.05 *** 0.01) b(3) se(3) ///
	stats(N N_adv F_eff, fmt(%9.0fc %9.0fc %13.1fc) labels("N" "\# of advisers" "Effective F")) ///
	coeflabels(c.school_rankw#c.school_rankw "PhD school rank$^2$" c.school_rankw#c.school_rankw#c.school_rankw "PhD school rank$^3$") ///
	indicate("Adviser FE = *.best_adviser*" "Adviser experience FE = *.adv_experience" "Field FE = *.stu_jel*" "Graduation year FE = *.stu_year**", labels(\checkmark ""))

********************************* School rank sample splits reduced form
estimates clear
* Median: 1st half
eststo: qui ivreg2 plc_scorewstd (adv_evwwin99std = first_evwwin99std_mean) adv_euclid i.adv_experience ib1.stu_sex school_rankw i.stu_year i.stu_jel i.best_adviser if school_rankw_quartile==1 | school_rankw_quartile==2, cl(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
weakivtest
qui estadd scalar F_eff = r(F_eff)
* Median: 2nd half
eststo: qui ivreg2 plc_scorewstd (adv_evwwin99std = first_evwwin99std_mean) adv_euclid i.adv_experience ib1.stu_sex school_rankw i.stu_year i.stu_jel i.best_adviser if school_rankw_quartile==3 | school_rankw_quartile==4, cl(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
weakivtest
qui estadd scalar F_eff = r(F_eff)
* Quartiles: 1st quartile
eststo: qui ivreg2 plc_scorewstd (adv_evwwin99std = first_evwwin99std_mean) adv_euclid i.adv_experience ib1.stu_sex school_rankw i.stu_year i.stu_jel i.best_adviser if school_rankw_quartile==1, cl(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
weakivtest
qui estadd scalar F_eff = r(F_eff)
* Quartiles: 2nd quartile
eststo: qui ivreg2 plc_scorewstd (adv_evwwin99std = first_evwwin99std_mean) adv_euclid i.adv_experience ib1.stu_sex school_rankw i.stu_year i.stu_jel i.best_adviser if school_rankw_quartile==2, cl(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
weakivtest
qui estadd scalar F_eff = r(F_eff)
* Quartiles: 3rd quartile
eststo: qui ivreg2 plc_scorewstd (adv_evwwin99std = first_evwwin99std_mean) adv_euclid i.adv_experience ib1.stu_sex school_rankw i.stu_year i.stu_jel i.best_adviser if school_rankw_quartile==3, cl(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
weakivtest
qui estadd scalar F_eff = r(F_eff)
* Quartiles: 4th quartile
eststo: qui ivreg2 plc_scorewstd (adv_evwwin99std = first_evwwin99std_mean) adv_euclid i.adv_experience ib1.stu_sex school_rankw i.stu_year i.stu_jel i.best_adviser if school_rankw_quartile==4, cl(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
weakivtest
qui estadd scalar F_eff = r(F_eff)
* Write out
esttab using ./990_output/Tables/centrality_2sls_splits.tex, replace ///
	nobase ///
	alignment(D{.}{.}{-1}) label substitute("\_" "_") delimiter(_tab "&") booktabs ///
	wrap varwidth(30) modelwidth(15) legend nonote ///
	star(* 0.1 ** 0.05 *** 0.01) b(3) se(3) ///
	stats(N N_adv F_eff, fmt(%9.0fc %9.0fc %13.1fc) labels("N" "\# of advisers" "Effective F")) ///
	indicate("Adviser FE = *.best_adviser*" "Adviser experience FE = *.adv_experience" "Field FE = *.stu_jel*" "Graduation year FE = *.stu_year**", labels(\checkmark ""))

********************************* Interactions
estimates clear
* Continuous interaction
eststo: qui vcemway reg plc_scorewstd c.school_rankw##c.adv_evwwin99std c.school_rankw##c.school_rankw##c.school_rankw adv_euclid ib1.stu_sex i.stu_jel i.stu_year i.adv_experience i.best_adviser, cluster(best_adviser stu_school)
qui estadd scalar N_adv = e(N_clust1)
* with median dummy
*eststo: qui vcemway reg plc_scorewstd c.adv_evwwin99std##i.school_rankw_top c.school_rankw##c.school_rankw##c.school_rankw adv_euclid ib1.stu_sex i.stu_jel i.stu_year i.adv_experience i.best_adviser, cluster(best_adviser stu_school)
* qui estadd scalar N_adv = e(N_clust1)
* with quartiles
*eststo: qui vcemway reg plc_scorewstd c.adv_evwwin99std##school_rankw_quartile c.school_rankw##c.school_rankw##c.school_rankw adv_euclid ib1.stu_sex i.stu_jel i.stu_year i.adv_experience i.best_adviser, cluster(best_adviser stu_school)
* qui estadd scalar N_adv = e(N_clust1)
esttab using ./990_output/Tables/centrality_ols_interactions.tex, replace ///
	 nobase ///
	alignment(D{.}{.}{-1}) label substitute("\_" "_") delimiter(_tab "&") booktabs ///
	wrap varwidth(30) modelwidth(15) legend nonote ///
	star(* 0.1 ** 0.05 *** 0.01) b(3) se(3) ///
	coeflabels(c.school_rankw#c.school_rankw "PhD school rank$^2$" c.school_rankw#c.school_rankw#c.school_rankw "PhD school rank$^3$") ///
	stats(N N_adv, fmt(%9.0fc %9.0fc) labels("N" "\# of advisers")) ///
	indicate("Adviser FE = *.best_adviser*" "Adviser experience FE = *.adv_experience" "Field FE = *.stu_jel*" "Graduation year FE = *.stu_year**", labels(\checkmark ""))
