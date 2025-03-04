import pandas as pd
import os

df = pd.read_csv('E:/Various Programs/Coding Projects\YGO Decklist Analytics v2/dataframes/Purrely/TCG_93 days_main_deck.csv', sep="|")

dfmain = df.drop_duplicates(subset='deckID', keep='first').reset_index(drop=True)
count2 = dfmain["tag2"].value_counts()
count3 = dfmain["tag3"].value_counts()
count2 = count2.add(count3, fill_value=0)
count2 = count2.sort_values(ascending=False)

print(count2)
