#%% Import libraries and modules
from config import ModelConfig
from environment import EnergyEnvironment
from utils import naive_policy, contribution, possible_actions
from NNmodel import build_nn

import pandas as pd
import numpy as np
import random

from sklearn.linear_model import LinearRegression
from sklearn.svm import LinearSVR
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import time

#%%
# ============================================================
# ADP PIPELINE
# ============================================================

class EnergyStorageADP:

    def __init__(self, cfg: ModelConfig):

        self.cfg = cfg
        self.env = EnergyEnvironment(cfg)

        self.policy_dicts = {"MLR": {}, "SVR": {}, "NN": {}}
        self.value_models = {}

        self.action_space = self.build_action_space()

    # --------------------------------------------------------
    # PRECOMPUTE ACTION SPACE
    # --------------------------------------------------------

    def build_action_space(self):

        actions = {}

        for b in range(self.cfg.R_max + 1):

            actions[b] = list(range(
                max(self.cfg.R_min, b - self.cfg.gamma_W),
                min(b + self.cfg.gamma_I, self.cfg.R_max) + 1
            ))

        return actions

    # --------------------------------------------------------
    # SAMPLE GENERATION
    # --------------------------------------------------------

    def generate_samples(self):

        rows = []

        for m in range(self.cfg.M):

            demand = random.randint(self.cfg.D_min, self.cfg.D_max)
            renewable = random.randint(self.cfg.E_min, self.cfg.E_max)
            buy_price = random.randint(self.cfg.C_min, self.cfg.C_max)
            sell_price = random.randint(self.cfg.P_min, self.cfg.P_max)

            random_exogenousinfo = [demand, renewable, buy_price, sell_price]

            for t in range(self.cfg.T):

                demand, renewable, buy_price, sell_price = self.env.next_exogenous_state(random_exogenousinfo, t)

                rows.append([
                    m, t, demand, renewable, buy_price, sell_price
                ])


        df = pd.DataFrame(rows, columns=[
            "m","t","demand","renewable_source",
            "buyingprice","sellingprice"
        ])

        return df

    # --------------------------------------------------------
    # POLICY EVALUATION
    # --------------------------------------------------------

    def evaluate_policy(self, samples):

        paths = samples.groupby("m")

        results = {"MLR": [], "SVR": [], "NN": []}

        for b0 in range(self.cfg.R_max + 1):

            for m, path in paths:

                path = path.sort_values("t")

                battery = {k: b0 for k in results.keys()}

                contrib = {k: [] for k in results.keys()}
                rows = {k: [] for k in results.keys()}

                for row in path.itertuples(index=False):

                    t = row.t
                    demand = row.demand
                    renewable = row.renewable_source
                    buy_price = row.buyingprice
                    sell_price = row.sellingprice

                    for method in results.keys():

                        b = battery[method]

                        state = (t+1,b,demand,renewable,buy_price,sell_price)

                        actions = self.policy_dicts[method].get(
                            state,
                            naive_policy(
                                t+1,self.cfg.T,b,
                                demand,renewable,
                                self.cfg.gamma_W
                            )
                        )

                        eb,es,est,el = actions

                        c = contribution(
                            self.cfg,b,demand,
                            buy_price,sell_price,
                            eb,es,est,el
                        )

                        contrib[method].append(c)

                        rows[method].append([
                            m,t+1,b,eb,es,est,el,c
                        ])

                        battery[method] = est

                for method in results.keys():

                    c = np.array(contrib[method])

                    future = np.flip(np.cumsum(np.flip(c)))

                    for i,r in enumerate(rows[method]):

                        r.append(future[i])

                        results[method].append(r)

        dfs = {}

        for method in results.keys():

            dfs[method] = pd.DataFrame(
                results[method],
                columns=[
                    "m","t","battery",
                    "energy_bought","energy_sold",
                    "energy_stored","energy_lost",
                    "contribution","future_contribution"
                ]
            )

        return dfs

    # --------------------------------------------------------
    # VALUE FUNCTION
    # --------------------------------------------------------

    def fit_value_functions(self, eval_results):

        models = {}

        for method, df in eval_results.items():

            X = df[[
                "t","battery",
                "energy_bought","energy_sold",
                "energy_stored","energy_lost"
            ]].values

            y = df["future_contribution"].values

            if method == "MLR":

                model = Pipeline([
                    ("scaler",StandardScaler()),
                    ("reg",LinearRegression())
                ])

                model.fit(X,y)
                models[method] = model

            elif method == "SVR":

                model = Pipeline([
                    ("scaler",StandardScaler()),
                    ("svr",LinearSVR(max_iter=1000))
                ])

                model.fit(X,y)
                models[method] = model

            elif method == "NN":

                scaler = StandardScaler()
                Xs = scaler.fit_transform(X)

                nn = build_nn(X.shape[1])

                nn.fit(Xs,y,epochs=15,batch_size=100,verbose=0)

                models["NN"] = nn
                models["NN_scaler"] = scaler

        self.value_models = models

    # --------------------------------------------------------
    # POLICY IMPROVEMENT
    # --------------------------------------------------------

    def policy_improvement(self, samples):

        paths = samples.groupby("m")

        methods = ["MLR","SVR","NN"]

        sample_size = max(
            1,
            int(self.cfg.subsample_fraction * samples.m.nunique())
        )

        selected = np.random.choice(
            list(paths.groups.keys()),
            size=sample_size,
            replace=False
        )

        for b0 in range(self.cfg.R_max + 1):

            for m in selected:

                path = paths.get_group(m).sort_values("t")

                battery = {k:b0 for k in methods}

                for row in path.itertuples(index=False):

                    t = row.t
                    demand = row.demand
                    renewable = row.renewable_source

                    buy_price = row.buyingprice
                    sell_price = row.sellingprice

                    net_demand = demand - renewable

                    for method in methods:

                        model = self.value_models[method]

                        b = battery[method]

                        best_val = -np.inf
                        best_action = None

                        for storage in self.action_space[b]:

                            eb,es,est,el = possible_actions(
                                t+1,self.cfg.T,
                                net_demand,b,storage
                            )

                            imm = contribution(
                                self.cfg,b,demand,
                                buy_price,sell_price,
                                eb,es,est,el
                            )

                            if t+1 < self.cfg.T:

                                X = np.array([[t+1,b,eb,es,est,el]])

                                if method == "NN":

                                    scaler = self.value_models["NN_scaler"]
                                    X = scaler.transform(X)

                                    future = float(
                                        np.squeeze(
                                            model.predict(X,verbose=0)
                                        )
                                    )

                                else:

                                    future = float(
                                        np.squeeze(model.predict(X))
                                    )

                            else:

                                future = 0

                            total = imm + future

                            if total > best_val:

                                best_val = total
                                best_action = (eb,es,est,el)

                        state = (
                            t+1,b,demand,renewable,
                            buy_price,sell_price
                        )

                        self.policy_dicts[method][state] = best_action

                        battery[method] = best_action[2]
                        
    # --------------------------------------------------------
    # MAIN PIPELINE
    # --------------------------------------------------------

    def run(self):

        for n in range(self.cfg.N):
            # print(f"=== ADP Iteration {n + 1} ===")
            start_time = time.time()

            samples = self.generate_samples()

            eval_res = self.evaluate_policy(samples)

            self.fit_value_functions(eval_res)

            self.policy_improvement(samples)
            # print(f"Run time for improvement stage {n+1}: { (time.time() - start_time)/60}")

        return self.policy_dicts
