clear all
 
% Declare GLOBAL variables
global NCS  
global NAMES B 
global MAXITERS PARAMTOL LLTOL
global VARS CUSID CHOICE OFFERID

data = readmatrix("data\firstphase_long.csv"); %load csv file containing data

CUSID= data(:, 1); %cus_id column
OFFERID= data(:, 2); %alternative/  column
CHOICE =  data(:, 3); %choice column
NCS = max(CUSID); %no of choice situations/ distinct customers in dataset.
VARS = data(:,[4 5]); %distance and disount as explanatory variables
NAMES={'distance' 'discount' }; %explanatory variable names

%Gives starting values for the coefficients of these variables.
B=[0 0]; %starting beta values
% OPTIMIZATION PARAMETERS
%{ 
Maximum number of iterations for the optimization routine.
The code will abort after ITERMAX iterations, even if convergence has
not been achieved. The default is 400, which is used when MAXITERS=[];
%}
MAXITERS=[]; 
%{ 
Convergence criterion based on the maximum change in parameters that is considered
to represent convergence. If all the parameters change by less than PARAMTOL 
from one iteration to the next, then the code considers convergence to have been
achieved. The default is 0.000001, which is used when PARAMTOL=[];
%}
PARAMTOL=[];
 
%{
Convergence criterion based on change in the log-likelihood that is
considered to represent convergence. If the log-likelihood value changes
less than LLTOL from one iteration to the next, then the optimization routine
considers convergence to have been achieved. The default is 0.000001,
which is used when LLTOL=[];
%}
LLTOL=[];

disp('Start estimation');
disp('The negative of the log-likelihood is minimized,');
disp('which is the same as maximizing the log-likelihood.');
 
tic;
param=B';  %starting values: take transpose since must be col vector
options=optimset('LargeScale','off','Display','iter','GradObj','off',...
    'MaxFunEvals',100000,'MaxIter',MAXITERS,'TolX',PARAMTOL,'TolFun',LLTOL,'DerivativeCheck','off');
[paramhat,fval,exitflag,output,grad,hessian]=fminunc(@loglike,param,options);

disp(['Estimation took ' num2str(toc./60) ' minutes.']);
disp(' ');
if exitflag == 1
  disp('Convergence achieved.');
elseif exitflag == 2
  disp('Convergence achieved by criterion based on change in parameters.');
  if size(PARAMTOL,1)>0
     disp(['Parameters changed less than PARAMTOL= ' num2str(PARAMTOL)]);
  else
     disp('Parameters changed less than PARAMTOL=0.000001, set by default.');
  end
  disp('You might want to check whether this is actually convergence.');
  disp('The gradient vector is');
  grad
elseif exitflag == 3
  disp('Convergence achieved by criterion based on change in log-likelihood value.');
  if size(PARAMTOL,1)>0
     disp(['Log-likelihood value changed less than LLTOL= ' num2str(LLTOL)]);
  else
     disp('Log-likelihood changed less than LLTOL=0.000001, set by default.');
  end
     disp('You might want to check whether this is actually convergence.');
     disp('The gradient vector is');
     grad
else
    disp('Convergence not achieved.');
    disp('The current value of the parameters and hessian');
    disp('can be accesses as variables paramhat and hessian.');
    disp('Results are not printed because no convergence.');
    return
end
 
disp(['Value of the log-likelihood function at convergence: ' num2str(-fval)]);
%Calculate standard errors of parameters
disp('Taking inverse of hessian for standard errors.');
ihess=inv(hessian);
stderr=sqrt(diag(ihess));
t_stat =  paramhat ./ stderr; 
results = [paramhat, stderr, t_stat];
disp(['The value of grad*inv(hessian)*grad is: ' num2str(grad'*ihess*grad)]);
 
disp(['Value of the log-likelihood function at convergence: ' num2str(-fval)]);
disp(' ');
disp('ESTIMATION RESULTS');
disp(' ')
disp('              ---------------------------- ');
disp('                Est         SE      t-stat');
for r=1:size(NAMES,2);
    fprintf('%-10s %10.4f %10.4f %10.4f\n', NAMES{1,r}, [paramhat(r,1) stderr(r,1) paramhat(r,1)./stderr(r,1) ]);
end
disp(' ');
 
disp(' ');
disp('You can access the estimated parameters as variable paramhat,');
disp('the gradient of the negative of the log-likelihood function as variable grad,');
disp('the hessian of the negative of the log-likelihood function as variable hessian,');
disp('and the inverse of the hessian as variable ihess.');
disp('The hessian is calculated by the BFGS updating procedure.');
 
%Inputs: coef is Kx1 where K is number of explanatory variables
%
%Globals: NCS: scale number of choice situations
%         CUSID: NROWSx1 vector identifying the rows for each choice situation (1-NCS), where NROWS is number of alternatives
%                          in all choice situations combined
%         CHOICE: NROWSx1 vector identifying the chosen alternative (1=chosen, 0=nonchosen)
%         VARS: NROWSxK matrix of explanatory variables
 
%Output: probs: NROWSx1 vector of predicted probabilities for each alternative in 
 
function ll =loglike(coef);
global NCS CUSID CHOICE VARS;
p = zeros(NCS,1);
v = VARS * coef; % utility = B_distance * distance + B_discount * discount
v = exp(v); % calculate the exponential of the utility
for n=1:NCS;
  vv=sum(v(CUSID==n,1)); %sum of exponential utility for all alternatives
  vy= v(CUSID==n & CHOICE==1,1); %exponential utility for selected alternative
  p(n,1)= vy/vv; %p = exp(selected alternative)/ sum(exp of all alternatives)
end
p=max(p,0.00000001); %As a precaution
ll=-sum(log(p),1);  %Negative since neg of ll is minimized
end
