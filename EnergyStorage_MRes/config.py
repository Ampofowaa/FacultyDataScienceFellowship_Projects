# ============================================================
# 1. CONFIGURATION OBJECT
# ============================================================

#%% Important libraries
import numpy as np
from scipy.stats import norm

class ModelConfig:

    def __init__(self):

        # Battery parameters
        self.gamma_I = 6 #maximum charging rate
        self.gamma_W = 3 #maximum discharge rate

        self.charging_efficiency = 0.95
        self.discharge_efficiency = 0.95

        self.eta_I = 1 - self.charging_efficiency #charging inefficiencies
        self.eta_W = 1 - self.discharge_efficiency #discharging inefficiencies

        self.R_min = 0 #minimum battery capacity
        self.R_max = 10 #maximum battery capacity

        self.storage_rent = 0.0005

        # Time parameters
        self.T = 5#10
        self.M = 300#3000
        self.N = 5#10

       #Upper and lower bounds for Buying Price (C), Selling Price (P), Renewable Source (E), Demand(D)
        self.C_min = 3
        self.C_max = 13

        self.P_min = 2
        self.P_max = 12

        self.D_min = 1
        self.D_max = 15

        self.E_min = 1
        self.E_max = 7

    
        # Noise processes
        self.delta = 1

        self.E_noise_support = np.arange(-1, 2, self.delta)

        self.price_sample_type = "mc_jump"

        self.price_noise_support = np.arange(-8, 9, self.delta)

        self.price_noise_support2 = np.array([0, 1])
        self.price_probs2 = np.array([0.031, 1 - 0.031])

        self.price_noise_support3 = np.arange(-40, 41, self.delta)

        self.price_probs1 = norm.pdf(self.price_noise_support, 0, 0.5)
        self.price_probs1 /= self.price_probs1.sum()

        self.price_probs3 = norm.pdf(self.price_noise_support3, 0, 50)
        self.price_probs3 /= self.price_probs3.sum()

        self.D_noise_support = np.arange(-2, 3, self.delta)
        pdf_vals = norm.pdf(self.D_noise_support, 0, 2)
        self.D_probs = pdf_vals / pdf_vals.sum()


        # Simulation parameters
        self.subsample_fraction = 0.01 #sample used for improvement