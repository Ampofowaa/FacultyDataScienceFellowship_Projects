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
noi: di as txt "Language (EN/FR): " _request(lg)
if !inlist("$lg","EN","FR") di as err "Only EN or FR are available. Please retry."

*Import experimental design from spreadsheet
#d ;
import excel using ExpDesign.xlsx, clear 
	sheet(ExperimentalDesign) 
	cellrange(A1:L17)
	first
;
#d cr


*** 2. Label attributes and levels ***
*Note: where necessary, labels must be translated

*Attribute 1
forv i = 1/2 {
	if "$lg"=="EN" la var A`i'_1 "Return airfare"
	if "$lg"=="FR" la var A`i'_1 "Prix du billet aller-retour"

	recode A`i'_1 (0=350) (1=450) (2=550) (3=650)
}
forv l = 350(100)650 {
	if "$lg"=="EN" la def farelab `l' "\$`l'", modify
	if "$lg"=="FR" la def farelab `l' "`l' USD", modify
}
la val A?_1 farelab

*Attribute 2
forv i = 1/2 {
	if "$lg"=="EN" la var A`i'_2 "Total travel time, including stops"
	if "$lg"=="FR" la var A`i'_2 "Temps de trajet, escales incluses"
}
forv l = 0/3 {
	la def timelab `l' "`=`l'+4'h", modify
}
la val A?_2 timelab

*Attribute 3
forv i = 1/2 {
	if "$lg"=="EN" la var A`i'_3 "Food/beverage"
	if "$lg"=="FR" la var A`i'_3 "Nourriture"
}
if "$lg"=="EN" {
	la def foodlab 0 "none", modify
	la def foodlab 1 "beverages only", modify
	la def foodlab 2 "beverages +<br />cold snack", modify
	la def foodlab 3 "beverages +<br />hot meal", modify
}
if "$lg"=="FR" {
	la def foodlab 0 "aucune", modify
	la def foodlab 1 "boissons uniquement", modify
	la def foodlab 2 "boissons +<br />en-cas froid", modify
	la def foodlab 3 "boissons +<br />repas chaud", modify
}
la val A?_3 foodlab

*Attribute 4
forv i = 1/2 {
	if "$lg"=="EN" la var A`i'_4 "Audio/Video entertainment"
	if "$lg"=="FR" la var A`i'_4 "Divertissement audio/vidéo"
}
if "$lg"=="EN" {
	la def audiolab 0 "none", modify
	la def audiolab 1 "audio only", modify
	la def audiolab 2 "audio +<br />short video clips", modify
	la def audiolab 3 "audio + movie", modify
}
if "$lg"=="FR" {
	la def audiolab 0 "aucun", modify
	la def audiolab 1 "audio uniquement", modify
	la def audiolab 2 "audio +<br />brefs clips vidéo", modify
	la def audiolab 3 "audio + film", modify
}
la val A?_4 audiolab

*Attribute 5
forv i = 1/2 {
	if "$lg"=="EN" la var A`i'_5 "Type of airplane"
	if "$lg"=="FR" la var A`i'_5 "Type d'avion"
}
la def planelab 0 "Boeing 737", modify
la def planelab 1 "Boeing 757", modify
la def planelab 2 "Boeing 767", modify
la def planelab 3 "Boeing 777", modify
la val A?_5 planelab

*Transform all variables from numeric to string.
*Makes it easier to include the elements in HTML
*table to be constructed below.
forv i = 1/2 {
	forv j = 1/5 {
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
texdoc init DCE_${lg}.txt, replace
tex [[AdvancedFormat]]

forv n = 1/`=_N' { // = foreach line in the dataset
	*Store the values in locals
	local B = block[`n']
	local C = choicetask[`n']
	forv i = 1/2 {
		forv j = 1/5 {
			local header_`j': variable label A1_`j'
			local A`i'_`j' = A`i'_`j'[`n']
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
	if "$lg"=="EN" {
		tex Among the following travel options, which one do you prefer? </br >
	}
	if "$lg"=="FR" {
		tex Parmi les options de voyage suivantes, laquelle préférez-vous? </br >
	}
	
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
	tex <td `headcolstyle'><strong>Option 1</strong></td>
	tex <td `headcolstyle'><strong>Option 2</strong></td>
	tex </tr>
	
	*Attribute 1 to 4 (all but the last)
	forv j = 1/4 {
		tex <tr>
		tex <td `headrowstyle'><strong>`header_`j''</strong></td>
		tex <td `rowstyle'>`A1_`j''</td>
		tex <td `rowstyle'>`A2_`j''</td>
		tex </tr>
	}
	*Attribute 5 (bottom rule is different for the last attribute)
	tex <tr>
	tex <td `headrowstyle'><strong>`header_5'</strong></td>
	tex <td `lastrowstyle'>`A1_5'</td>
	tex <td `lastrowstyle'>`A2_5'</td>
	tex </tr>

	tex </tbody>
	tex </table>
	
	*Choices
	tex [[Choices]]
	if "$lg"=="EN" {
		tex Your choice:
	}
	if "$lg"=="FR" {
		tex Votre choix:
	}
	tex [[AdvancedAnswers]]
	tex [[Answer]]
	tex Option 1
	tex [[Answer]]
	tex Option 2

	tex [[PageBreak]]
}
texdoc close

exit
