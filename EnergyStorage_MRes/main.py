from config import ModelConfig
from adp import EnergyStorageADP
from io_utils import write_policy_dict_to_csv

def main():

    cfg = ModelConfig()

    model = EnergyStorageADP(cfg)

    policies = model.run()

    for method, policy_dict in policies.items():
        write_policy_dict_to_csv(policy_dict, f"policy_{method}_final.csv")
    

if __name__ == "__main__":
    main()