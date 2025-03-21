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

def deckPartitioner():
    #Splits the raw data into archetypes
    x = pd.read_csv("cardListFile.csv", delimiter="|")
    x["date"] = pd.to_datetime(x["date"])
    mainArchetypeList = list(set(x["tag1"].to_list()+x['tag2'].to_list()+x["tag3"].to_list()))
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
    #Cleans code data so cards are easily identifable at later steps
    nameList = list(set(df["name"].to_list()))
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
    #simplifying card type, removing unnneeded categories 
    if "Monster" in cardType:
        return "Monster"
    elif "Spell" in cardType:
        return "Spell"
    elif "Trap" in cardType:
        return "Trap"
    else:
        return "Z"


def deckAnalysis(df):
    #Generates in archetype data
    df = df.fillna("")
    cardIDList = list(set(df["code"].to_list()))
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


def createArchetypeTables():
    #Creates archetype data tables
    archetypes = os.listdir("E:\Various Programs\Coding Projects\YGO Decklist Analytics v2\dataframes")
    archetypes = [x for x in archetypes if x != 'nan']
    archetypes = [x for x in archetypes if "(sub)" not in x]
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
        #Main Deck Stuff - Get deck sizes
        for dateRange in dateRanges:
            df = pd.read_csv("dataframes/" + archetype + "/" + dateRange + ".csv", sep="|")
            archetypeTable = deckAnalysis(df)
            os.makedirs("tables/"+archetype, exist_ok=True)
            archetypeTable['count'] = pd.Series([f"{count:.2f}" for count in archetypeTable['count']], index = archetypeTable.index)
            archetypeTable["% of decks"] = pd.Series(["{0:.2f}%".format(perc * 100) for perc in archetypeTable["% of decks"]], index = archetypeTable.index)
            if archetypeTable.empty:
                emptyRow = ["https://raw.githubusercontent.com/gregknothe/YGO-Decklist-Analytics-v2/refs/heads/main/NoAvailableData.jpeg", "No Data", "N/A", "N/A"]
                archetypeTable = pd.concat([archetypeTable,pd.DataFrame(columns=archetypeTable.columns, data=[emptyRow])])
            archetypeTable.to_csv("tables/" + archetype + "/" + dateRange + ".csv", sep="|", index=False)
        
            if "main" in dateRange:
                os.makedirs("tables/" + archetype + "_data", exist_ok=True)

                #Sub Archetypes
                dfmain = df.drop_duplicates(subset='deckID', keep='first').reset_index(drop=True)
                count2 = dfmain["tag2"].value_counts()
                count3 = dfmain["tag3"].value_counts()
                count2 = count2.add(count3, fill_value=0)
                count2 = count2.sort_values(ascending=False)
                count2 = count2.reset_index()
                count2.to_csv("tables/" + archetype + "_data/sub_archetypes_" + dateRange + ".csv", sep="|", index=False, header=False)

                #Main Archetypes
                dfsub = pd.read_csv("dataframes/" + archetype + " (sub)/" + dateRange + ".csv", sep="|")
                dfsub = dfsub.drop_duplicates(subset='deckID', keep='first').reset_index(drop=True)
                count1 = dfsub["tag1"].value_counts()
                count1 = count1.sort_values(ascending=False)
                count1 = count1.reset_index()
                count1.to_csv("tables/" + archetype + "_data/main_archetypes_" + dateRange + ".csv", sep="|", index=False, header=False)

                #Main Size Count
                idCount = df["deckID"].value_counts()
                if idCount.empty:
                    size = [["n/a"], ["n/a"], ["n/a"], ["n/a"]]
                else:
                    avgSize = sum(idCount.values)/len(df["deckID"].unique())
                    maxSize = max(idCount.values)
                    minSize = min(idCount.values)
                    size = [[len(idCount)], [avgSize], [maxSize], [minSize]]
                sizeDF = pd.DataFrame(size)
                sizeDF.to_csv("tables/" + archetype + "_data/deck_size_" + dateRange + ".csv", sep="|", index=False, header=False)
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

#--------------------------Popular Table Generation-------------------------------

def popularTableGeneration():
    #Generates popular tables
    df = pd.read_csv("cardListFile.csv", delimiter="|")
    df["date"] = pd.to_datetime(df["date"])
    today = datetime.datetime.today()
    df = df[today - df["date"] <= datetime.timedelta(days=31)]
    df = df.reset_index(drop=True)
    mainDF = df[df["deck"] == "main_deck"]
    sideDF = df[df["deck"] == "side_deck"]
    extraDF = df[df["deck"] == "extra_deck"]
    mainDFTags = mainDF.drop_duplicates(subset="deckID", keep="first").reset_index(drop=True)
    mainCards = mainDF.drop_duplicates(subset="code", keep="first").reset_index(drop=True)
    sideCards = sideDF.drop_duplicates(subset="code", keep="first").reset_index(drop=True)
    extraCards = extraDF.drop_duplicates(subset="code", keep="first").reset_index(drop=True)

    for formats in ["TCG", "OCG"]:
        #Getting Tags for "Top Archetypes" and "Top Sub Archetypes" list

        deckCount = len(mainDFFormat["deckID"].unique())

        mainDFFormat = mainDFTags[mainDFTags["format"]==formats]
        mainArchCount = mainDFFormat["tag1"].value_counts()
        subArchCount = mainDFFormat["tag2"].value_counts().add(mainDFFormat["tag3"].value_counts(), fill_value=0)

        mainArchCount.sort_values(ascending=False).head(10).to_csv("popList/main_" + formats + "_arch.csv", sep="|", header=False)

        subArchCount.sort_values(ascending=False).head(10).to_csv("popList/sub_" + formats + "_arch.csv", sep="|", header=False)

        mainDFCards = mainDF[mainDF["format"]==formats].drop_duplicates()
        mainCardFormat = mainDFCards["name"].value_counts()

        mainCardFormat = pd.DataFrame({"name": mainCardFormat.index, "perc": mainCardFormat.values})
        mainCardFormat["perc"] = round(mainCardFormat["perc"] / deckCount, 2)

        mainCardFormat.head(50).to_csv("popList/main_" + formats + "_cards.csv", sep="|", header=False, index=False)


        extraDFCards = extraDF[extraDF["format"]==formats].drop_duplicates()
        extraCardFormat = extraDFCards["name"].value_counts()

        extraCardFormat = pd.DataFrame({"name": extraCardFormat.index, "perc": extraCardFormat.values})
        extraCardFormat["perc"] = round(extraCardFormat["perc"] / deckCount, 2)

        extraCardFormat.head(30).to_csv("popList/extra_" + formats + "_cards.csv", sep="|", header=False, index=False)


        sideDFCards = sideDF[sideDF["format"]==formats].drop_duplicates()
        sideCardFormat = sideDFCards["name"].value_counts()

        sideCardFormat = pd.DataFrame({"name": sideCardFormat.index, "perc": sideCardFormat.values})
        sideCardFormat["perc"] = round(sideCardFormat["perc"] / deckCount, 2)

        sideCardFormat.head(30).to_csv("popList/side_" + formats + "_cards.csv", sep="|", header=False, index=False)
        
    return


def popArchCalc(formats, startDate, endDate):
    #Generates popular archetype tables
    df = pd.read_csv("cardListFile.csv", delimiter="|")
    df["date"] = pd.to_datetime(df["date"])
    today = datetime.datetime.today()

    df = df[(today - df["date"] <= datetime.timedelta(days=endDate)) & (today - df["date"] >= datetime.timedelta(days=startDate))]
    df = df[df["format"]==formats]

    df = df.drop_duplicates(subset=["deckID"], keep="first")
    
    deckCount = len(df["deckID"].unique())

    mainCount = df["tag1"].value_counts()
    subCount = df["tag2"].value_counts().add(df["tag3"].value_counts(), fill_value=0)

    mainCount = pd.DataFrame({"name": mainCount.index, "perc": mainCount.values})
    mainCount["perc"] = round(mainCount["perc"] / deckCount, 2) 

    subCount = pd.DataFrame({"name": subCount.index, "perc": subCount.values})
    subCount["perc"] = round(subCount["perc"] / deckCount, 2)   

    mainCount.sort_values(by="perc", ascending=False).head(20).to_csv("popList/main_" + formats + "_arch.csv", sep="|", header=False, index=False)
    subCount.sort_values(by="perc", ascending=False).head(20).to_csv("popList/sub_" + formats + "_arch.csv", sep="|", header=False, index=False)

    return


def popCalc(formats, deck, startDate, endDate):
    df = pd.read_csv("cardListFile.csv", delimiter="|")
    df["date"] = pd.to_datetime(df["date"])
    today = datetime.datetime.today()
    pic = df.drop_duplicates(subset=["name"], keep="first")
    pic = pic[["name", "imgSource"]]

    df = df[(today - df["date"] <= datetime.timedelta(days=endDate)) & (today - df["date"] >= datetime.timedelta(days=startDate))]
    df = df[df["format"]==formats]
    df = df[df["deck"]==deck]

    df = df.drop_duplicates()
    df = df.reset_index(drop=True)
    deckCount = len(df["deckID"].unique())
    df = df["name"].value_counts()
    df = pd.DataFrame({"name": df.index, "perc": df.values})
    df["perc"] = round(df["perc"] / deckCount, 2)
    if deck == "main_deck":
        df = df.head(50)
    else:
        df = df.head(30)
    df = pd.merge(df, pic, on="name", how="left")
    return df


def popTable():
    for f in ["TCG", "OCG"]:
        for d in ["main_deck", "side_deck", "extra_deck"]:
            thisMonth = popCalc(f, d, 0, 31)
            lastMonth = popCalc(f, d, 32, 62)
            diff = pd.merge(thisMonth, lastMonth, on="name", how="left")
            diff.fillna(0, inplace=True)
            diff["perc"] = round(diff["perc_x"] - diff["perc_y"], 2)
            diff = pd.DataFrame({"img": diff["imgSource_x"], "name": diff["name"], "perc": diff["perc_x"], "diff": diff["perc"]})
            diff.to_csv("popList/" + d.replace("_deck", "") + "_" + f + "_cards.csv", sep="|", header=False, index=False)
        popArchCalc(f, 0, 31)
    return

#--------------------------Clean Set Up---------------------------------            
#createURL() #4:35 
#createCardList("urlList.csv", "cardListFile.csv") #1:30:23
#deckPartitioner() #17:45
#createArchetypeTables() #8:47

#updateURL(limit=300) 
#addID("newURLList.csv") #Only if you fuck up
#updateCardList("newURLList.csv", "cardListFile.csv")
#updateBlankNames()

#deckPartitioner()
#createArchetypeTables()

#popTable()
#-------------------------------------------------------------------------

def updateData():
    currTime = datetime.datetime.now()
    print("<--------------------- Gathering URLs --------------------->")
    updateURL(limit=300)
    print("<--------------------- Updating Card List --------------------->")
    updateCardList("newURLList.csv", "cardListFile.csv")
    print("<--------------------- Updating Blank Names --------------------->")
    updateBlankNames()
    print("<--------------------- Partitioning Decks --------------------->")
    deckPartitioner()
    print("<--------------------- Creating Arch Tables --------------------->")
    createArchetypeTables()
    print("<--------------------- Creating Pop Tables --------------------->")
    popTable()
    print(datetime.datetime.now() - currTime)
    return

updateData()
