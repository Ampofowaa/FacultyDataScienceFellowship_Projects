# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def naive_policy(t, T, battery, demand, renewable, gamma_W):
    """
    Naive policy:
    1. Sell all renewable energy.
    2. Buy all demand from the grid.
    3. Keep battery unchanged until final period.
    4. At final period, discharge up to gamma_W and sell it.
    """

    energy_bought = demand

    if t < T:
        energy_sold = renewable
        energy_stored = battery
        energy_lost = 0

    else:

        discharge = min(battery, gamma_W)
        energy_sold = renewable + discharge
        energy_stored = 0
        energy_lost = max(battery - gamma_W, 0)

    return energy_bought, energy_sold, energy_stored, energy_lost



def contribution(cfg, prev_storage, demand, buy_price, sell_price,
                 energy_bought, energy_sold, energy_stored, energy_lost):

    # Base contribution
    val = (
        demand * buy_price
        + sell_price * energy_sold
        - buy_price * energy_bought
        - cfg.P_min * energy_lost
        - cfg.storage_rent * energy_stored
    )

    # Change in storage
    delta = energy_stored - prev_storage

    # Adjustment depending on storage change
    if delta < 0: # battery discharged
        val -= cfg.eta_W * buy_price * (-delta)

    elif delta > 0: # battery charged
        val -= cfg.eta_I * buy_price * delta

    return val


def possible_actions(t, T, net_demand, prev_storage, storage_level): #compute possible actions in the policy improvement step
    
    energy_stored = storage_level # Energy stored after decision
    balance = -net_demand + prev_storage - storage_level # Energy balance after meeting demand and storage decision

    if balance >= 0:
        energy_sold = balance
        energy_bought = 0

    else:
        energy_sold = 0
        energy_bought = -balance

    # energy lost only in final period
    if t < T:
        energy_lost = 0
    else:
        energy_lost = energy_stored

    return energy_bought, energy_sold, energy_stored, energy_lost