# -*- coding: utf-8 -*-
"""
Created on Mon Jun 14 13:29:06 2021

@author: bsraf3
"""

#%% import modules
import numpy as np
import pandas as pd
#%% data cleaning exercise
n_alts = 3 
n_situations = 8
df = pd.read_csv("data/firstphase_data.csv")
df1 = pd.read_excel("data/blocked_design.xlsx")
#df1 = pd.read_excel("C:/Users/Richlove/OneDrive - Loughborough University/PhD/Data Collection - Respondi/blocked_design.xlsx")
df.drop(labels = [0,1], axis = 0, inplace = True) #delete first two rows corresponding to renamed columns
df = df.reset_index(drop = True)
df = df[df['CE_ChoiceTask1_1.1']== "Option 2"]
df.fillna('', inplace=True)
#get columns of interest
df = df[['return_tic','CE_ChoiceTask1_1', 'CE_ChoiceTask2_1', 'CE_ChoiceTask3_1', 'CE_ChoiceTask4_1', 'CE_ChoiceTask5_1', 'CE_ChoiceTask6_1', 'CE_ChoiceTask7_1', 'CE_ChoiceTask8_1', 'CE_ChoiceTask9_1', 'CE_ChoiceTask10_1', 'CE_ChoiceTask11_1', 'CE_ChoiceTask12_1', 
         'CE_ChoiceTask13_1', 'CE_ChoiceTask14_1', 'CE_ChoiceTask15_1', 'CE_ChoiceTask16_1', 'CE_ChoiceTask17_1', 'CE_ChoiceTask18_1', 'CE_ChoiceTask19_1', 'CE_ChoiceTask20_1', 'CE_ChoiceTask21_1', 'CE_ChoiceTask22_1', 'CE_ChoiceTask23_1', 'CE_ChoiceTask24_1',
         'Mobility choice', 'Car_owner','Reason', 'Reason_5_TEXT', 'Trip purpose', 'Trip purpose_5_TEXT', 'Usage', 'Car_engine', 'Car_size', 'Duration', 'Pre_walk_distance', 'Post_walk_distance', 'Max_relocat_distance','Gender', 'Age', 'Employment', 'Employment_6_TEXT', 
         'Income']]
df = df.replace(["Option 1", "Option 2", "Option 3"], [1,2,3])
df = df.loc[df.index.repeat(n_situations)].reset_index(drop=True)
#%% getting block number for choice_scenarios
def blockdesign(row):
    if (row['CE_ChoiceTask1_1'] != '') & (row['CE_ChoiceTask9_1'] == '') & (row['CE_ChoiceTask17_1'] == ''):
        val = 1
    if (row['CE_ChoiceTask9_1'] != '') & (row['CE_ChoiceTask1_1'] == '') & (row['CE_ChoiceTask17_1'] == ''):
        val = 2
    if (row['CE_ChoiceTask17_1'] != '') & (row['CE_ChoiceTask1_1'] == '') & (row['CE_ChoiceTask9_1'] == ''):
        val = 3
    return val

df["Block"] = df.apply(blockdesign, axis=1)
#df = df.merge(df1,how="inner")
df = df.assign(distance1='', discount1='',distance2='', discount2='',distance3='',discount3='', choice ='')
return_tic = df["return_tic"].unique()
#%%
#get the distance and discount values for each block
distance1 = []
discount1 = []
distance2 = []
discount2 = []
distance3 = []
discount3 = []
for i in range(1,n_alts+1):
    distance1.append(df1[df1["Block"] == i]["A1_1"].to_list())
    discount1.append(df1[df1["Block"] == i]["A1_2"].to_list())
    distance2.append(df1[df1["Block"] == i]["A2_1"].to_list())
    discount2.append(df1[df1["Block"] == i]["A2_2"].to_list())
    distance3.append(df1[df1["Block"] == i]["A3_1"].to_list())
    discount3.append(df1[df1["Block"] == i]["A3_2"].to_list())
    
#%%
#populate the corresponding distance and discount values
for i in return_tic:
    data = df[df["return_tic"] == i]
    data2 = None
    #print(data.index)
    if  data["Block"].unique()[0] == 1:
        data2=(data.iloc[0,1:9].to_list())
        df.iloc[data.index[0]:data.index[0]+8,44]= distance1[0]
        df.iloc[data.index[0]:data.index[0]+8,45]= discount1[0]
        df.iloc[data.index[0]:data.index[0]+8,46]= distance2[0]
        df.iloc[data.index[0]:data.index[0]+8,47]= discount2[0]
        df.iloc[data.index[0]:data.index[0]+8,48]= distance3[0]
        df.iloc[data.index[0]:data.index[0]+8,49]= discount3[0]
        df.iloc[data.index[0]:data.index[0]+8,50]= data2        
    elif data["Block"].unique()[0] == 2:
        data2=(data.iloc[0,9:17].to_list())
        df.iloc[data.index[0]:data.index[0]+8,44]= distance1[1]
        df.iloc[data.index[0]:data.index[0]+8,45]= discount1[1]
        df.iloc[data.index[0]:data.index[0]+8,46]= distance2[1]
        df.iloc[data.index[0]:data.index[0]+8,47]= discount2[1]
        df.iloc[data.index[0]:data.index[0]+8,48]= distance3[1]
        df.iloc[data.index[0]:data.index[0]+8,49]= discount3[1]
        df.iloc[data.index[0]:data.index[0]+8,50]= data2   
    else:
        data2=(data.iloc[0,17:25].to_list())  
        df.iloc[data.index[0]:data.index[0]+8,44]= distance1[2]
        df.iloc[data.index[0]:data.index[0]+8,45]= discount1[2]
        df.iloc[data.index[0]:data.index[0]+8,46]= distance2[2]
        df.iloc[data.index[0]:data.index[0]+8,47]= discount2[2]
        df.iloc[data.index[0]:data.index[0]+8,48]= distance3[2]
        df.iloc[data.index[0]:data.index[0]+8,49]= discount3[2]
        df.iloc[data.index[0]:data.index[0]+8,50]= data2 

# df_initial = df[['return_tic','choice','distance1','discount1','distance2','discount2','distance3','discount3', 
#                 'Mobility choice', 'Car_owner',
#                 'Reason', 'Reason_5_TEXT', 'Trip purpose', 'Trip purpose_5_TEXT', 'Usage', 'Car_engine', 'Car_size', 'Duration', 'Pre_walk_distance', 'Post_walk_distance', 'Max_relocat_distance','Gender', 'Age', 'Employment', 'Employment_6_TEXT', 
#                 'Income']]
df['respondent_id'] = [i + 1 for i in range(len(df))]
df_final1 = df[['return_tic','choice','distance1','distance2','distance3', 
                'discount1','discount2','discount3','Mobility choice', 'Car_owner',
                'Reason', 'Reason_5_TEXT', 'Trip purpose', 'Trip purpose_5_TEXT', 'Usage', 'Car_engine', 'Car_size', 'Duration', 'Pre_walk_distance', 'Post_walk_distance', 'Max_relocat_distance','Gender', 'Age', 'Employment', 'Employment_6_TEXT', 
                'Income']]
df_final2 = df[['respondent_id','choice','distance1','distance2','distance3', 
                'discount1','discount2','discount3','Mobility choice', 'Car_owner',
                'Reason', 'Reason_5_TEXT', 'Trip purpose', 'Trip purpose_5_TEXT', 'Usage', 'Car_engine', 'Car_size', 'Duration', 'Pre_walk_distance', 'Post_walk_distance', 'Max_relocat_distance','Gender', 'Age', 'Employment', 'Employment_6_TEXT', 
                'Income']]
df_wide = df[['choice','distance1','distance2','distance3', 'discount1','discount2','discount3']]
df_final1.to_csv("data/firstphase_alldatawidev1.csv")
df_final2.to_csv("data/firstphase_alldatawidev2.csv")
df_wide.to_csv("data/firstphase_wide.csv") #cols: idcase, choice, distance1, distance2, distance3, discount1, discount2, discount3
