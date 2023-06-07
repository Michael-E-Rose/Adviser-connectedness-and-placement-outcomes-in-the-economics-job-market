clear all

********************************* Random assignments with actual distribution

foreach i in 0 1 2 3 4 {

	local files : dir "./680_centrality_masters/" files "random_distribution`i'*.csv"

	foreach file in `files' {
		import delimited "./680_centrality_masters/`file'", clear
			foreach v of varlist adviser stu_jel stu_school stu_sex {
			encode `v', gen(new`v')
			drop `v'
			rename new`v' `v'
		}
		keep if adv_occ > 1
		eststo: qui ivreg2 plc_scorewstd (adv_evwwin99std = first_evwwin99std_mean) adv_euclid i.adv_experience i.adviser ib1.stu_sex school_rankw i.stu_year i.stu_jel, cl(adviser stu_school)
	}

	esttab using "./691_random_results/distribution`i'.csv", replace ///
		drop(1.stu_sex) noconstant nostar p noparentheses nogaps nonotes ///
		indicate("Adviser FE = *.adviser*" "Adviser experience FE= *.adv_experience" "Field FE = *.stu_jel*" "Placement year FE = *.stu_year*")
	eststo clear
}


********************************* Random assignments with actual field

local files : dir "./680_centrality_masters/" files "random_field`i'*.csv"

foreach file in `files' {
	import delimited "./680_centrality_masters/`file'", clear
		foreach v of varlist adviser stu_jel stu_school stu_sex {
		encode `v', gen(new`v')
		drop `v'
		rename new`v' `v'
	}
	keep if adv_occ > 1
	eststo: qui ivreg2 plc_scorewstd (adv_evwwin99std = first_evwwin99std_mean) adv_euclid i.adv_experience i.adviser ib1.stu_sex school_rankw i.stu_year i.stu_jel, cl(adviser stu_school)
}

esttab using "./691_random_results/field.csv", replace ///
	drop(1.stu_sex) noconstant nostar p noparentheses nogaps nonotes ///
	indicate("Adviser FE = *.adviser*" "Adviser experience FE= *.adv_experience" "Field FE = *.stu_jel*" "Placement year FE = *.stu_year*")
eststo clear
