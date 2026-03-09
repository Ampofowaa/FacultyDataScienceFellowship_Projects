#%% Load important modules and libraries
import os
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
from tensorflow.keras import layers, regularizers, optimizers, Sequential, Input
#%%
def build_nn(dim):
    #Build a 2-layer NN with 10+10 neurons, L2 regularization and dropout.
    model = Sequential([

        Input(shape=(dim,)),

        layers.Dense(
            10,activation="relu",
            kernel_regularizer=regularizers.l2(0.01),
            activity_regularizer=regularizers.l2(0.01)
        ),

        layers.Dropout(0.2),

        layers.Dense(
            10,activation="relu",
            kernel_regularizer=regularizers.l2(0.01),
            activity_regularizer=regularizers.l2(0.01)
        ),

        layers.Dropout(0.2),

        layers.Dense(1)
    ])

    model.compile(
        optimizer=optimizers.Adam(learning_rate=0.01),
        loss="mse"
    )

    return model