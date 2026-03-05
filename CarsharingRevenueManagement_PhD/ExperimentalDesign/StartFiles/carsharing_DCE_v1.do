/*******************************************************************************************
A step-by-step procedure to implement discrete choice experiments in Qualtrics 
Sylvain Weber, University of Neuchâtel, sylvain.weber@unine.ch
02 Oct 2019

Objective of this dofile: Transform DCE experimental design into Qualtrics' txt file
Input: ExpDesign.xlsx (experimental design coded in a spreadsheet)
Output: DCE_EN.txt or DCE_FR.txt (advanced format txt file to be imported into Qualtrics)

Notes:
	- This dofile makes use of the user-written command texdoc (Jann, 2016).
	  To check if texdoc is already installed, type "which texdoc.ado". 
	  To install texdoc, type "ssc install texdoc".
	- To produce the txt file, run this dofile by typing "texdoc do ExpDesign_to_Qualtrics".
*******************************************************************************************/

version 15	
clear all
set more off

*** 1. Import experimental design ***

*Request language (useful in multi-language survey)
*noi: di as txt "Language (EN/FR): " _request(lg)
*if !inlist("$lg","EN","FR") di as err "Only EN or FR are available. Please retry."

*Import experimental design from spreadsheet
*calculate no_alternatives before importing spreadsheet
#d ;
import excel using dce_scenarios_100.xlsx, clear 
	sheet(ExperimentalDesign) 
	cellrange(A1:K101)
	first
;
#d cr

*** 2. Label attributes and levels ***
*Note: where necessary, labels must be translated

*Attribute 1	
forv i = 1/4 {
	la var A`i'_1 " Walking distance from the original drop-off station D"
}
forv l = 0(5)20 {
	la def walkdistance `l' "`l' mins", modify
}
la val A?_1 walkdistance

*Attribute 2
forv i = 1/4 {
	la var A`i'_2 "Fare discount"
}
forv l = 0(5)80 {
	la def farediscount `l' "`l' %", modify
}
la val A?_2 farediscount

*Transform all variables from numeric to string.
*Makes it easier to include the elements in HTML
*table to be constructed below.
forv i = 1/4 {
	forv j = 1/2 {
		decode A`i'_`j', gen(tmp)
		drop A`i'_`j'
		ren tmp A`i'_`j'
	}
}

*** 3. Build HTML tables and include them in a Qualtrics' advanced format TXT file ***

*Definition of parameters for HTML tables
*Reference for HTML colors: https://www.w3schools.com/colors/colors_picker.asp
local rulecolor #1524D9 // (= bright blue) color of the table's rules
local cellcolor #BEDCFC // (= light blue) background color of the table's cells
local firstheadcolstyle style="width:180px; border-bottom: 1px solid `rulecolor';"
local headcolstyle bgcolor="`cellcolor'" style="width:270px; text-align: center; border-left: 4px solid `rulecolor'; border-top: 4px solid `rulecolor'; border-right: 4px solid `rulecolor'; border-bottom: 1px solid `rulecolor';"
local headrowstyle height="100" style="text-align: left; border-bottom: 1px solid `rulecolor';"
local rowstyle bgcolor="`cellcolor'" style="text-align: center; border-left: 4px solid `rulecolor'; border-right: 4px solid `rulecolor'; border-bottom: 1px solid `rulecolor';"
local lastrowstyle bgcolor="`cellcolor'" style="text-align: center; border-left: 4px solid `rulecolor'; border-right: 4px solid `rulecolor'; border-bottom: 4px solid `rulecolor';"

*Initialize txt document
texdoc init carsharing_DCE_v1.txt, replace
tex [[AdvancedFormat]]

forv n = 1/`=_N' { // = foreach line in the dataset
	*Store the values in locals
	local B = block[`n']
	local C = choicetask[`n']
	*display "choice task, `C'" 
	local D = no_alternatives[`n']
	forv i = 1/`D' {
		forv j = 1/2 {
			local header_`j': variable label A1_`j'
			*display "`header_`j'"
			local A`i'_`j' = A`i'_`j'[`n']
			*display " A`i'_`j'"
		}
	}
	
	*Include a Qualtrics' block separator 
	*(if the block is different from previous one)
	if block[`n']!=block[`=`n'-1'] {
		tex [[Block:CE_Block`B']]
	}

	*Include a Qualtrics' question separator and a question label
	tex [[Question:Matrix]]
	tex [[ID:CE_ChoiceTask`C']]
	
	*Question to be asked to the respondent
	*tex Suppose you originally request a car from station O to station D and other drop-off stations with different discounts are made available to you, which one do you prefer? </br >
	
	*Beginning of HTML table for displaying the choice task
	tex <br />
	tex <style type="text/css">table {
	tex border: none;
	tex border-collapse: collapse;
	tex }
	tex th, td {
	tex padding: 5px;
	tex }
	tex th {
	tex text-align: left;
	tex }
	tex td:first-child {
	tex border-left: none;
	tex border-top: none;
	tex }
	tex </style>
	tex <table>
	tex <tbody>
	
	*Column headers	
	tex <tr>
	tex <td `firstheadcolstyle'>&nbsp;</td>
	forv i = 1/`D' {
	if (`i' == 1 ){
	tex <td `headcolstyle'><strong>Option `i' (Original Booking)</strong></td>	
	}
	else {
	tex <td `headcolstyle'><strong>Option `i' </strong></td>
	}
	}
	tex </tr>
	
	*Attribute 1 (all but the last)
	tex <tr>
	tex <td `headrowstyle'><strong>`header_1'</strong></td>
	forv i = 1/`D' {
		tex <td `rowstyle'>`A`i'_1'</td>
		}
	tex </tr>
	
	*Attribute 2 (bottom rule is different for the last attribute)
	tex <tr>
	tex <td `headrowstyle'><strong>`header_2'</strong></td>
	forv i = 1/`D' {
		tex <td `lastrowstyle'>`A`i'_2'</td>
		}
	tex </tr>

	tex </tbody>
	tex </table>
	
	*Choices
	tex [[Choices]]
	tex Your choice:
	tex [[AdvancedAnswers]]
	forv i = 1/`D' {
		tex [[Answer]]
		tex Option `i'
	}
	
	tex [[PageBreak]]	
}
texdoc close


exit
