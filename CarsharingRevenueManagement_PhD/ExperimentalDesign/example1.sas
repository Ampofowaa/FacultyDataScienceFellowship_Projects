%mktruns(4 6) /* factor level list for one alternative */
%mktex(4 6, /* factor level list for one alternative */
n=24) /* number of candidate alternatives */
%choiceff(data=design, /* candidate set of alternatives */
model=class(x1-x2 / sta), /* model with stdz orthogonal coding */
nsets=8, /* number of choice sets */
flags=3, /* 3 alternatives, generic candidates */
seed=100, /* random number seed */
maxiter=100, /* maximum number of designs to make */
options=relative, /* display relative D-efficiency */
beta=zero) /* assumed beta vector, Ho: b=0 */
proc print; var x1-x2; id set; by set; run;
proc print data=bestcov label;
title ’Variance-Covariance Matrix’;
id __label;
label __label = x;
var x:;
run;
title;
%mktdups(generic, data=best, factors=x1-x2, nalts=2)
proc format;
value sf 1 = 5 2 = 10 3 = 15 4 = 20;
value cf 1 = 5 2 = 20 3 = 35 4 = 50 5 = 65 6= 80;
run;
data ChoiceDesign;
set best;
format x1 sf. x2 cf. ;
label x1 = ’Distance (mins)’ x2 = ’Discount (%)’;
run;
proc print label; var x1-x2; id set; by set; run;
