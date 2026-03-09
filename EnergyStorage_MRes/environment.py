#%% Load important libraires and modules
from config import ModelConfig
import numpy as np
#%%
# # ============================================================
# ENVIRONMENT
# ============================================================

class EnergyEnvironment:

    def __init__(self, cfg: ModelConfig):
        self.cfg = cfg

        # Precompute price scenarios
        if self.cfg.price_sample_type.lower() != "mc":
            self._precompute_price_scenarios()

        
    def _precompute_price_scenarios(self):

        from itertools import product
        
        supports = np.array(
            list(product(
                self.cfg.price_noise_support,
                self.cfg.price_noise_support2,
                self.cfg.price_noise_support3
            ))
        )

        probs = np.array(
            list(product(
                self.cfg.price_probs1,
                self.cfg.price_probs2,
                self.cfg.price_probs3
            ))
        )

        self.price_supports = supports.sum(axis=1)

        self.price_probs = np.prod(probs, axis=1)
        self.price_probs /= self.price_probs.sum()

    
    def price_sampling(self, price_type, price):
        if price_type == 'buyprice':
            price_min = self.cfg.C_min
            price_max = self.cfg.C_max
        else:
            price_min = self.cfg.P_min
            price_max = self.cfg.P_max

        if self.cfg.price_sample_type.lower() == "mc":

            noise = np.random.choice(self.cfg.price_noise_support)

            next_price = np.clip(
                price + noise,
                price_min,
                price_max
            )

        else:

            price_next = np.clip(
                price + self.price_supports,
                price_min,
                price_max
            )

            next_price = np.random.choice(price_next, p=self.price_probs)

        return next_price   
    
    def next_exogenous_state(self, state, t):

        demand, renewable, buy_price, sell_price = state

        next_t = t + 1

        base = 3 - 4 * np.sin(2 * np.pi * next_t / self.cfg.T)

        D_next = np.clip(
            np.floor(base) + self.cfg.D_noise_support,
            self.cfg.D_min,
            self.cfg.D_max
        )

        demand = np.random.choice(D_next, p=self.cfg.D_probs)

        renewable = np.clip(
            renewable + np.random.choice(self.cfg.E_noise_support),
            self.cfg.E_min,
            self.cfg.E_max
        )

        #price sampling --> buyngprice > sellingprice
        p1 = self.price_sampling("buyprice", buy_price)
        p2 = self.price_sampling("sellprice", sell_price)
       
        buy_price, sell_price = sorted([p1, p2], reverse=True)

        return [int(demand), int(renewable), int(buy_price), int(sell_price)]
