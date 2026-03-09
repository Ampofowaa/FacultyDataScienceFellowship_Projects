# Project Understanding:

The single energy node storage problem refers to the problem of optimally managing a storage device (e.g. battery) that interacts with both the grid and an uncertain renewable energy source (e.g. solar or wind) to satisfy demand whilst considering the electricity spot prices can also be referred to as the energy storage problem.

In this regard, the energy storage problem is that of deciding when to buy or sell electricity from or to the grid, when to use the the renewable energy source and when to charge or discharge the battery. We model this problem as a stochastic dynamic program and implement an Approximate Policy Iteration Algorithm which uses Multiple Linear Regression (MLR), Support Vector Regression (SVR) and Neural Networks (NN) to approximate the value function


# Python Code: 
energy_storage_adp/
│
├── main.py
├── config.py --> configuration class for parameters
├── environment.py --> stochastic environment logic
├── utils.py --> utility functions
├── NNmodel.py --> machine learning model builders
├── adp.py -- core algorithm
└── io_utils.py --> file output utilities

The ADP pipeline codes structure is as follows:
  - generate_samples()
  - evaluate_policy()
  - fit_value_function()   # MLR / SVR / NN
  - policy_improvement()

The outputs are 3 policy matrices for each value function approximation method which suggests the optimal decisions of when to buy, sell, store or lose energy given the time, initial battery level, demand, renewable energy source, the buying and selling prices.
