import pandas as pd
from urllib.request import Request, urlopen
import requests
from bs4 import BeautifulSoup as bs
import datetime
import numpy as np
import os
from pathlib import Path
from collections import Counter


def getPageURL(offset=0, limit=20000):
    #Creates list with URL for each decklist on page.
    url = "https://ygoprodeck.com/api/decks/getDecks.php?tournament=tier-2&offset=" + str(offset) + "&limit=" + str(limit)
    req = Request(url, headers={'User-Agent': 'XYZ/3.0'})
    webpage = urlopen(req, timeout=10).read()
    html = str(bs(webpage, features="lxml"))
    deckURLs = html.split('"pretty_url":"')
    for x in range(len(deckURLs)):
        deckURLs[x] = deckURLs[x].split('"')[0]
    deckURLs.pop(0)
    return deckURLs

def createURL(limit=200000, filename="urlList.csv"):
    #Creates a csv file with URL for each topping decklist.
    urlList = []
    for x in range(round(limit/20)+1):
        try:
            urlList.extend(getPageURL(offset=(x*20), limit=limit))
            if x%20 == 0:
                print(str(x) + ": " + str(urlList[-1]))
        except:
            break
    df = pd.DataFrame({'url': urlList})
    if filename == "new":
        return df
    else:
        id = []
        for x in df["url"].to_list():
            id.append(int(np.char.rpartition(x, "-")[2]))
        df["id"] = id
        df = df.drop_duplicates()
        df = df.sort_values(by="id", ascending=True)
        df.to_csv(filename, sep='|', index=False)
        return

def updateURL(limit=200000, filename="urlList.csv"):
    #Updates existing deck URL file with newly added decks. Returns list of URLs of new decks.
    oldList = pd.read_csv("urlList.csv", sep="|")
    newList = createURL(limit=limit, filename="new")
    new = newList["url"].to_list()
    old = oldList["url"].to_list()
    diff = list(set(new)-set(old))
    if len(diff) > 0:
        print("--New decklist being added:")
        for currDeck in diff:
            oldList.loc[len(oldList.index)] = [currDeck, int(np.char.rpartition(currDeck, "-")[2])]
            print(currDeck)
    else:
        print("--No new decklist available.")
    
    oldList = oldList.sort_values(by="id", ascending=True)

    oldList.to_csv(filename, sep="|", index=False)
    oldList.tail(len(diff)).to_csv("newURLList.csv", sep="|", index=False)
    return diff

def addID(file):
    x = pd.read_csv("newURLList.csv", sep="|")
    idList = []
    for url in x["url"]:
        idList.append(url.split("-").pop())
    x["id"] = idList
    x.to_csv("newURLList.csv", sep="|", index=False)
    print("newURLList.csv 'fixed'.")
    return


def getDeckList(url, id):
    #scrapes the decklist from the URL and returns a dataframe with all cards and deck metadata
    url = "https://ygoprodeck.com/deck/" + url
    req = requests.get(url, headers={'User-Agent': 'XYZ/3.0'}).text
    html = bs(req, features="lxml")
    
    date = html.find(class_="deck-metadata-info").find_all("span")[len(html.find(class_="deck-metadata-info").find_all("span"))-1].get_text()
    date = date[1:].replace("st","").replace("nd","").replace("rd","").replace("th","")
    formatedDate = datetime.datetime.strptime(date, '%b %d %Y')

    tagAndFormat = html.find(class_="deck-metadata-container deck-bgimg").find_all("a")
    format, formatFlag, tags = "", 0, []
    for x in range(len(tagAndFormat)):
        if formatFlag == 1:
            tags.append(tagAndFormat[x].get_text())
        if tagAndFormat[x].get_text() == "Tournament Meta Decks":
            format = "TCG"
            formatFlag = 1
        elif tagAndFormat[x].get_text() == "Tournament Meta Decks OCG":
            format = "OCG"
            formatFlag = 1
        elif tagAndFormat[x].get_text() == "Tournament Meta Decks OCG (Asian-English)":
            format = "OCG(Asia-English)"
            formatFlag = 1
        elif tagAndFormat[x].get_text() == "Tournament Meta Decks Worlds":
            format = "Worlds(TCG)"
            formatFlag = 1
        elif tagAndFormat[x].get_text() == "Master Duel Decks":
            format = "Worlds(MasterDuel)"
            formatFlag = 1
        elif tagAndFormat[x].get_text() == "Non-Meta Decks":
            format = "undefined"
            formatFlag = 1

    
    nameList, typeList, deckList, codeList, imgSourceList, count = [], [], [], [], [], []
    for deckType in ["main_deck", "extra_deck", "side_deck"]:
        for type in html.find_all(id=deckType):
            for types in type.find_all(class_="lazy"):
                nameList.append(types.get("data-cardname"))
                typeList.append(types.get("data-cardtype"))
                codeList.append(types.get("data-name"))
                imgSourceList.append(types.get("data-src"))
                deckList.append(deckType)
    
    tagLen = len(tags)
    tag1, tag2, tag3 = "", "", ""
    if tagLen >= 1:
        tag1 = tags[0]
    if tagLen >= 2:
        tag2 = tags[1]
    if tagLen == 3:
        tag3 = tags[2]

    df = pd.DataFrame({"name": nameList, "type": typeList, "deck": deckList, "code": codeList, "imgSource": imgSourceList})
    df["deckID"], df["date"], df["format"], df["tag1"], df["tag2"], df["tag3"] = id, formatedDate, format, tag1, tag2, tag3
    return df

def createCardList(urlListFile, cardListFile=""):
    urlDF = pd.read_csv(urlListFile, delimiter="|")
    urlList = urlDF["url"].to_list()
    idList = urlDF["id"].to_list()
    decklistDF = getDeckList(urlList[0], idList[0])
    for x in range(1, len(urlList)):
        decklist = getDeckList(urlList[x], idList[x])
        decklistDF = pd.concat([decklistDF, decklist])
        if x%20 == 0:
            print(str(x) + ": " + str(urlList[x]))
    decklistDF = decklistDF.reset_index(drop=True)
    if cardListFile != "":
        decklistDF.to_csv(cardListFile, sep='|', index=False)
    return decklistDF

def updateCardList(newURLListFile, cardListFile):
    decklistDF = pd.read_csv(cardListFile, delimiter="|")
    newdeckListDF = createCardList(newURLListFile)
    newdeckListDF["date"] = pd.to_datetime(newdeckListDF["date"]).dt.date
    decklistDF = pd.concat([decklistDF, newdeckListDF])
    decklistDF.to_csv(cardListFile, sep='|', index=False)
    return

"""
def deckPartitioner():
    x = pd.read_csv("cardListFile.csv", delimiter="|")
    x["date"] = pd.to_datetime(x["date"])
    mainArchetypeList = list(set(x["tag1"].to_list()))
    #mainArchetypeList = ["Snake-Eye", "Melodious", "Mikanko"]
    today = datetime.datetime.today()
    num = 1
    print("Total Archetypes: " + str(len(list(set(x["tag1"].to_list())))))
    for archetype in mainArchetypeList:
        archetypeName = "".join(x for x in str(archetype) if x.isalnum())
        print(str(num) + " " + str(archetypeName))
        num += 1
        for formats in ["TCG", "OCG"]:
            for timeFrame in [datetime.timedelta(days=31), datetime.timedelta(days=93), datetime.timedelta(days=186), datetime.timedelta(days=365), datetime.timedelta(days=100000)]:
                for deckType in ["main_deck", "extra_deck", "side_deck"]:
                    os.makedirs("dataframes/"+archetypeName, exist_ok=True)
                    df = x[(x["tag1"]==archetype) & (x["format"]==formats) & (today - x["date"] <= timeFrame) & (x["deck"]==deckType)]
                    df.to_csv("dataframes/"+archetypeName+"/"+formats+"_"+str(timeFrame).split(",")[0]+"_"+deckType+".csv", sep="|", index=False)
    return
"""

def deckPartitioner():
    x = pd.read_csv("cardListFile.csv", delimiter="|")
    x["date"] = pd.to_datetime(x["date"])
    mainArchetypeList = list(set(x["tag1"].to_list()+x['tag2'].to_list()+x["tag3"].to_list()))
    #mainArchetypeList = ["Snake-Eye", "Melodious", "Mikanko"]
    today = datetime.datetime.today()
    num = 1
    print("Total Archetypes: " + str(len(mainArchetypeList)))
    for archetype in mainArchetypeList:
        archetypeName = "".join(x for x in str(archetype) if x.isalnum())
        print(str(num) + " " + str(archetypeName))
        num += 1
        for formats in ["TCG", "OCG"]:
            for timeFrame in [datetime.timedelta(days=31), datetime.timedelta(days=93), datetime.timedelta(days=186), datetime.timedelta(days=365), datetime.timedelta(days=100000)]:
                for deckType in ["main_deck", "extra_deck", "side_deck"]:
                    os.makedirs("dataframes/"+archetypeName, exist_ok=True)
                    df = x[(x["tag1"]==archetype) & (x["format"]==formats) & (today - x["date"] <= timeFrame) & (x["deck"]==deckType)]
                    df.to_csv("dataframes/"+archetypeName+"/"+formats+"_"+str(timeFrame).split(",")[0]+"_"+deckType+".csv", sep="|", index=False)
                    os.makedirs("dataframes/"+archetypeName+" (sub)", exist_ok=True)
                    df = x[(x["tag2"]==archetype) | (x["tag3"]==archetype)]
                    df = df[(today - df["date"] <= timeFrame) & (df["deck"]==deckType)]
                    df.to_csv("dataframes/"+archetypeName+" (sub)/"+formats+"_"+str(timeFrame).split(",")[0]+"_"+deckType+".csv", sep="|", index=False)
    return


def codeCorrector(df):
    nameList = list(set(df["name"].to_list()))
    #print(nameList)
    for name in nameList:
        if name == "":
            continue
        else:
            subDF = df[df["name"]==name].sort_values(by="code")
            minID = min(subDF["code"].to_list())
            indexList = subDF.index
            subDF = subDF.reset_index(drop=True)
            imgSource = subDF["imgSource"].iloc[0]
            for index in indexList:
                df.at[index, "code"] = minID
                df.at[index, "imgSource"] = imgSource
    return df

def cardTypeAssigner(cardType):
    if "Monster" in cardType:
        return "Monster"
    elif "Spell" in cardType:
        return "Spell"
    elif "Trap" in cardType:
        return "Trap"
    else:
        return "Z"

def deckAnalysis(df):
    df = df.fillna("")
    cardIDList = list(set(df["code"].to_list()))
    #cardNameList = list(set(df["name"].to_list()))
    '''
    if len(cardIDList) != len(cardNameList):
        df = codeCorrector(df)
        cardIDList = list(set(df["code"].to_list()))
        #print(x[x["name"]=="Ash Blossom & Joyous Spring"])
    '''
    df = codeCorrector(df)
    cardIDList = list(set(df["code"].to_list()))
    totalDeckCount = len(list(set(df["deckID"].to_list())))
    cardDeckCount, cardAvgCount, cardName, cardImgSource, cardType = [], [], [], [], []
    for cardID in cardIDList:
        cardDF = df[df["code"]==cardID].reset_index(drop=True)
        cardDeckList = list(set(cardDF["deckID"].to_list()))
        cardAvgCount.append(round(np.mean(list(Counter(cardDF["deckID"]).values())),3))
        cardDeckCount.append(len(cardDeckList))
        cardImgSource.append(cardDF["imgSource"].iloc[0].replace("cards_small", "cards"))
        cardName.append(df.loc[df["code"]==cardID, "name"].iloc[0])
        cardType.append(cardTypeAssigner(df.loc[df["code"]==cardID, "type"].iloc[0]))
    df = pd.DataFrame({"code": cardIDList, "deckCount": cardDeckCount, "image": cardImgSource, "count": cardAvgCount, "cardType": cardType})
    df["% of decks"] = round(df["deckCount"] / totalDeckCount, 3)
    df["name"] = cardName
    df = df[["image", "name", "% of decks", "count", "cardType"]].sort_values(["% of decks", "cardType", "count", "name"], ascending=[False, True, False, True]).reset_index(drop=True)
    df = df.drop("cardType", axis=1)
    return df

"""
def deckAnalysis(df):
    df = df.fillna("")
    cardIDList = list(set(df["code"].to_list()))
    #cardNameList = list(set(df["name"].to_list()))
    '''
    if len(cardIDList) != len(cardNameList):
        df = codeCorrector(df)
        cardIDList = list(set(df["code"].to_list()))
        #print(x[x["name"]=="Ash Blossom & Joyous Spring"])
    '''
    df = codeCorrector(df)
    cardIDList = list(set(df["code"].to_list()))
    totalDeckCount = len(list(set(df["deckID"].to_list())))
    cardDeckCount, cardAvgCount, cardName, cardImgSource = [], [], [], []
    for cardID in cardIDList:
        cardDF = df[df["code"]==cardID].reset_index(drop=True)
        cardDeckList = list(set(cardDF["deckID"].to_list()))
        cardAvgCount.append(round(np.mean(list(Counter(cardDF["deckID"]).values())),3))
        cardDeckCount.append(len(cardDeckList))
        cardImgSource.append(cardDF["imgSource"].iloc[0].replace("cards_small", "cards"))
        cardName.append(df.loc[df["code"]==cardID, "name"].iloc[0])
    df = pd.DataFrame({"code": cardIDList, "deckCount": cardDeckCount, "image": cardImgSource, "count": cardAvgCount})
    df["% of decks"] = round(df["deckCount"] / totalDeckCount, 3)
    df["name"] = cardName
    df = df[["image", "name", "% of decks", "count"]].sort_values(["% of decks", "count", "name"], ascending=False).reset_index(drop=True)
    return df
"""

#deckAnalysis(pd.read_csv("dataframes/SnakeEye/TCG_93 days_main_deck.csv", sep="|"))

def createArchetypeTables():
    archetypes = os.listdir("E:\Various Programs\Coding Projects\YGO Decklist Analytics\dataframes")
    archetypes = [x for x in archetypes if x != 'nan']
    with open('archetype.csv', 'w') as f:
        for archetype in archetypes:
            f.write(f"{archetype}\n")
    dateRanges = ["OCG_31 days_main_deck", "OCG_93 days_main_deck", "OCG_186 days_main_deck", "OCG_365 days_main_deck", "OCG_100000 days_main_deck",
                "OCG_31 days_extra_deck", "OCG_93 days_extra_deck", "OCG_186 days_extra_deck", "OCG_365 days_extra_deck", "OCG_100000 days_extra_deck",
                "OCG_31 days_side_deck", "OCG_93 days_side_deck",  "OCG_186 days_side_deck", "OCG_365 days_side_deck", "OCG_100000 days_side_deck",
                "TCG_31 days_main_deck", "TCG_93 days_main_deck", "TCG_186 days_main_deck", "TCG_365 days_main_deck", "TCG_100000 days_main_deck",
                "TCG_31 days_extra_deck", "TCG_93 days_extra_deck", "TCG_186 days_extra_deck", "TCG_365 days_extra_deck", "TCG_100000 days_extra_deck",
                "TCG_31 days_side_deck", "TCG_93 days_side_deck", "TCG_186 days_side_deck", "TCG_365 days_side_deck", "TCG_100000 days_side_deck",]
    for archetype in archetypes: 
        print(archetype)
        if "(sub)" in archetype:
            for dateRange in dateRanges:
                df = pd.read_csv("dataframes/" + archetype + "/" + dateRange + ".csv", sep="|")
                #Get count of all tags that arnt "archetype"
        else:
            for dateRange in dateRanges:
                df = pd.read_csv("dataframes/" + archetype + "/" + dateRange + ".csv", sep="|")
                archetypeTable = deckAnalysis(df)
                os.makedirs("tables/"+archetype, exist_ok=True)
                archetypeTable['count'] = pd.Series([f"{count:.2f}" for count in archetypeTable['count']], index = archetypeTable.index)
                archetypeTable["% of decks"] = pd.Series(["{0:.2f}%".format(perc * 100) for perc in archetypeTable["% of decks"]], index = archetypeTable.index)
                if archetypeTable.empty:
                    emptyRow = ["https://github.com/gregknothe/YGO-Decklist-Analytics-v2/NoAvailableData.jpeg", "No Data", "N/A", "N/A"]
                    archetypeTable = pd.concat([archetypeTable,pd.DataFrame(columns=archetypeTable.columns, data=[emptyRow])])
                archetypeTable.to_csv("tables/" + archetype + "/" + dateRange + ".csv", sep="|", index=False)
                #Get deck size counts, prob just count of unique deck ids
    return

def updateBlankNames():
    #Adds name values to cards without names but have repeating code values. Ex: OCG exclusives
    df = pd.read_csv("cardListFile.csv", delimiter="|").fillna("")
    noName = df[df["name"]==""]
    codeList = list(set(noName["code"].tolist()))
    for code in codeList:
        subDF = df[df["code"]==code]
        codeIndex = subDF.index
        nameList = list(set(subDF["name"].tolist()))
        cardName = list(filter(None, nameList))
        if len(nameList) > 1:
            for index in codeIndex:
                df.at[index, "name"] = cardName[0]
            print(cardName[0] + " - " + str(code))
    df.to_csv("cardListFile.csv", sep="|", index=False)
    print("------------------Names updated.------------------")
    return

#--------------------------Clean Set Up---------------------------------            446394
#createURL() #4:35 
#createCardList("urlList.csv", "cardListFile.csv") #1:30:23
#deckPartitioner() #17:45
#createArchetypeTables() #8:47

#updateURL(limit=300) 
#addID("newURLList.csv") #Only if you fuck up
#updateCardList("newURLList.csv", "cardListFile.csv")
#updateBlankNames()

#deckPartitioner()
createArchetypeTables()


#x = pd.read_csv("E:\Various Programs\Coding Projects\YGO Decklist Analytics\dataframes\SnakeEye\TCG_93 days_extra_deck.csv", sep="|")
#y = codeCorrector(x.fillna(""))
#y.to_csv("testtesttest.csv", sep='|')


#make it look better
#function to add in name of missing name cards based on ID if they are added later (main data set)
