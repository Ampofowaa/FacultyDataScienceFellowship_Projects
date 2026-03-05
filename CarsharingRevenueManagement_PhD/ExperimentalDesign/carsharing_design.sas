/*design with restrictions on distance - discount combinations */
%mktex(4 6, /* factor level list for one alternative */
n=24, options=noqc) /* number of candidate alternatives */
data final;
   if _n_ = 1 then do;  
      f1 = 1; f2 = 0; f3 = 0; f4=0; x1 = 0; x2 = 0; output;
      end;
   set design;
   f1 = 0;
   f2 = (x1 <= 3) * (x2 <= 5);
   f3 = (x1 >= 2) * (x1 >= 2);
   /*f2 = (x1<=2) * (x2 <= 4);*/
   /*f3 = (2<=x1<=3)  * (2<=x2 <= 5);*/
   /*f4 = (x1>=3) * (x2 >= 3)*/;
   if sum(of f1-f3); 
   output;
run;
proc print data=final; run;
%macro res;
/*bad = ((x[2,1] >= x[3,1]) + (x[2,1] >= x[4,1]) + (x[3,1] >= x[4,1])) +
      ((x[2,2] >= x[3,2]) + (x[2,2] >= x[4,2]) + (x[3,2] >= x[4,2]));*/
bad = ((x[2,1] >= x[3,1])) + ((x[2,2] >= x[3,2]));  
%mend;
%choiceff(data=final, /* candidate set of alternatives */
model=class(x1-x2 / sta), /* model with stdz orthogonal coding */
nsets=24, /* number of choice sets */
flags=f1-f3, /* flag which alt can go where, 4 alts */
seed=121, /* random number seed */
maxiter=10, /* maximum number of designs to make */
drop = x10 x20,
options=relative nodups, /* display relative D-efficiency */
restrictions=res,  resvars=x1 x2,
beta=zero) /* assumed beta vector, Ho: b=0 */
proc print data=bestcov label;
title ’Variance-Covariance Matrix’;
id __label;
label __label = x;
var x:;
run;
title;
proc format;
value sf 1 = 5 2 = 10 3 = 15 4 = 20;
value cf 1 = 5 2 = 20 3 = 35 4 = 50 5 = 65 6= 80;
run;
data ChoiceDesign2;
set best;
format x1 sf. x2 cf. ;
label x1 = ’Distance (mins)’ x2 = ’Discount (%)’;
run;
* Block the choice design. Ask for 3 blocks;
%mktblock(data=ChoiceDesign2, nalts=3, nblocks=3, factors=x1-x2, seed=472)
proc print label; var x1-x2; id set; by set; run;
%mktdups(generic, data=ChoiceDesign2, factors=x1-x2, nalts=3)
proc print; run;


