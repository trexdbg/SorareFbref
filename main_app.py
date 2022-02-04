import streamlit as st
import pandas as pd
import time
from matplotlib.backends.backend_agg import RendererAgg
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import seaborn as sns
import re

from fuzzywuzzy import fuzz

from bs4 import BeautifulSoup

from requests import get as get
from requests import post as post
import json


####
### CONSTANT
####

_lock = RendererAgg.lock
plt.style.use('default')

url = 'https://api.sorare.com/graphql'

link_competition = {'Serie A': 'https://fbref.com/fr/comps/11/Statistiques-Serie-A',
 'MLS': 'https://fbref.com/fr/comps/22/Statistiques-Major-League-Soccer',
 'Ligue 1': 'https://fbref.com/fr/comps/13/Statistiques-Ligue-1',
 'Bundesliga': 'https://fbref.com/fr/comps/20/Statistiques-Bundesliga',
 'Primera División' : 'https://fbref.com/fr/comps/12/Statistiques-La-Liga'}

not_compet = ['Supercopa de España', 'Copa del Rey', 'Coupe de France']
not_xg_compet = ["Coupe d'Afrique des Nations", "WCQ"]

jour_semaine = {
0:'Lundi',
1:'Mardi',
2:'Mercredi',
3:'Jeudi',
4:'Vendredi',
5:'Samedi',
6:'Dimanche',
}

cm = sns.light_palette("#b520ba", as_cmap=True)

#####

st.sidebar.title('Application de comparaison xG/xA avec les scores Sorare')

##PLAYER NAME

# Competition

competitions = ["bundesliga-de",
                "ligue-1-fr",
                "laliga-santander",
                "serie-a-it"]


select_competition = st.sidebar.selectbox("Choisir une competition", competitions, 1)


query_clubs_compet = f"""{{competition(slug:"{select_competition}")
            {{
                clubs
                {{
                    nodes
                        {{
                            slug
                            name
                        }}
                    }}
                }}
            }}"""


r = post(url, json={'query': query_clubs_compet})

jok = r.text
joks = pd.DataFrame(json.loads(jok)['data']['competition']['clubs'])
joks['name'] = joks.nodes.apply(lambda x: x['name'])
joks['slug'] = joks.nodes.apply(lambda x: x['slug'])

# Club

select_clubs = st.sidebar.selectbox("Choisir un club", joks['name'].unique(), 12)
club_sluggy = joks[joks['name'] == select_clubs]['slug'].values[0]

query_clubs_compet = f"""{{club(slug:"{club_sluggy}")
            {{
                activePlayers
                {{
                    nodes
                        {{
                            displayName
                            slug
                        }}
                    }}
                }}
            }}"""

r = post(url, json={'query': query_clubs_compet})

jok = r.text
joks = pd.DataFrame(json.loads(jok)['data']['club']['activePlayers'])
joks['displayName'] = joks.nodes.apply(lambda x: x['displayName'])
joks['slug'] = joks.nodes.apply(lambda x: x['slug'])

# Player

select_players = st.sidebar.selectbox("Choisir un joueur", joks['displayName'].unique(), 1)
player_request = joks[joks['displayName'] == select_players]['slug'].values[0]


big_query = f"""query{{player(slug:"{player_request}"){{
          displayName
          age
appearances
position
matchName
 pictureUrl
 lastClub{{
            name
            domesticLeague{{name}}
            upcomingGames(first:5){{so5Fixture{{gameWeek
            eventType
            cutOffDate}}}}
          }}
cards(rarities:limited){{
    nodes{{
              onSale
            serialNumber
              liveSingleSaleOffer{{price}}
              publicSingleBuyOfferMinPrice{{amount}}
            }}
    pageInfo
        {{
            endCursor
            hasNextPage
        }}
    }}
allSo5Scores(first:10){{
        nodes{{
              score
              playerGameStats{{game{{so5Fixture{{gameWeek}}date}}}}
            }}}}
}}}}"""
r = post(url, json={'query': big_query})

qsodejose = r.text
qsodejoseoks = json.loads(qsodejose)

# image

st.sidebar.image(qsodejoseoks['data']['player']['pictureUrl'], width=100)
st.sidebar.write(player_request)


row1_1, row1_space2, row1_2, row1_space3, row1_3, row1_space4 = st.columns(
    (5, .3, 5, .00000001, 3, 0.15))


## Data api sorare

So_ligue = qsodejoseoks['data']['player']['lastClub']['domesticLeague']['name']
club = qsodejoseoks['data']['player']['lastClub']['name']
next_gw = qsodejoseoks['data']['player']['lastClub']['upcomingGames'][0]['so5Fixture']

## PATCH FIXE BUG

# PLAYER

player = player_request
player = 'borja iglesias' if player == 'borja-iglesias-quintas' else player
player = 'neymar' if player == 'neymar-da-silva-santos-junior' else player
player = 'juanmi' if player == 'juan-miguel-jimenez-lopez' else player

# CLUB

club = 'betis' if club == 'Real Betis Balompié' else club



url_comp = link_competition[So_ligue]

res_1 = get(url_comp)
comm = re.compile("<!--|-->")
soup = BeautifulSoup(comm.sub("",res_1.text),'lxml')
all_tables = soup.findAll("tbody")
team_table = all_tables[0]
url_club = []

for idx in team_table.findAll("a"):
    if 'Statistiques' in idx.get('href'):
        r_f = fuzz.ratio(idx.get_text(), club)
        url_club.append([idx.get('href'), r_f])


url_club = pd.DataFrame(url_club).sort_values(by=[1]).tail(1)[0].values[0]
st.sidebar.write(url_club.split('/')[4])

res_2 = get('https://fbref.com'+url_club)
### URL player

comm = re.compile("<!--|-->")
soup = BeautifulSoup(comm.sub("",res_2.text),'lxml')
all_tables = soup.findAll("tbody")
player_table = all_tables[0]

url_player = []

for idx in player_table.findAll("a"):
    r_f = fuzz.ratio(idx.get_text(), player)
    url_player.append([idx.get('href'), r_f])


url_player = pd.DataFrame(url_player).sort_values(by=[1]).tail(1)[0].values[0]

st.sidebar.write(url_player.split('/')[4])

test = url_player.split('/')

link_rapport = 'matchs/2021-2022/summary/Journaux-de-match-'
test.insert(-1, link_rapport)
test[-2:] = [''.join(test[-2:])]
link_rapport_ok = "/".join(test)

### Rapport de match

res_3 = get('https://fbref.com'+link_rapport_ok)
comm = re.compile("<!--|-->")
soup = BeautifulSoup(comm.sub("",res_3.text),'lxml')
all_tables = soup.findAll("table")
stats_table = all_tables[0]
df_matchs_players = pd.read_html(str(stats_table))[0].dropna(subset=[('Unnamed: 0_level_0', 'Date')])
df_matchs_players = df_matchs_players[~df_matchs_players[('Unnamed: 2_level_0', 'Comp')].isin(not_compet)].tail(10)[[
('Unnamed: 0_level_0', 'Date'),
 ('Unnamed: 2_level_0', 'Comp'),
 ('Unnamed: 7_level_0', 'Adversaire'), ('Attendu', 'xG'),('Attendu', 'xA'),
('Performance', 'Buts'),
 ('Performance', 'PD')]]

df_matchs_players['Date'] = pd.to_datetime(df_matchs_players['Unnamed: 0_level_0', 'Date'])

df_matchs_players[('Performance', 'Buts')] = pd.to_numeric(df_matchs_players[('Performance', 'Buts')], errors='coerce').fillna(0, downcast='infer')
df_matchs_players[('Performance', 'Buts')] = df_matchs_players[('Performance', 'Buts')].astype(int)

df_matchs_players[('Performance', 'PD')] = pd.to_numeric(df_matchs_players[('Performance', 'PD')], errors='coerce').fillna(0, downcast='infer')
df_matchs_players[('Performance', 'PD')] = df_matchs_players[('Performance', 'PD')].astype(int)

df_matchs_players[('Attendu', 'xG')] = pd.to_numeric(df_matchs_players[('Attendu', 'xG')], errors='coerce').fillna(0, downcast='infer')
df_matchs_players[('Attendu', 'xG')] = df_matchs_players[('Attendu', 'xG')].astype(float)

df_matchs_players[('Attendu', 'xA')] = pd.to_numeric(df_matchs_players[('Attendu', 'xA')], errors='coerce').fillna(0, downcast='infer')
df_matchs_players[('Attendu', 'xA')] = df_matchs_players[('Attendu', 'xA')].astype(float)

df_matchs_players = df_matchs_players[~df_matchs_players[('Unnamed: 2_level_0', 'Comp')].isin(not_xg_compet)]

comm = re.compile("<!--|-->")
soup = BeautifulSoup(comm.sub("",res_2.text),'lxml')
all_tables = soup.findAll("table")
df_calendar1 = pd.read_html(str(all_tables[1]))[0]
df_calendar1['Date'] = pd.to_datetime(df_calendar1['Date'])
df_calendar= df_calendar1[df_calendar1['Date']> datetime.today()].head()[['Tribune','Adversaire', 'Date','Jour','Comp']].reset_index(drop=True)
df_calendar.loc[0,'GW'] = next_gw['gameWeek']
df_calendar['Jour'] = df_calendar['Date'].apply(lambda x: x.weekday())
df_calendar['Jour'] = df_calendar['Jour'].replace(jour_semaine)
comm = re.compile("<!--|-->")
soup = BeautifulSoup(comm.sub("",res_1.text),'lxml')
team_table = soup.findAll("table")
team_df = pd.read_html(str(team_table[0]))[0]

maj_gw = next_gw['gameWeek']
for idx in range(len(df_calendar)):
    if idx == 0:
        pass

    elif df_calendar.loc[idx, 'Comp'] in not_compet:
        df_calendar.loc[idx, 'GW'] = None

    elif df_calendar.loc[idx, 'Jour'] in ['Mardi', 'Mercredi', 'Jeudi']:
        df_calendar.loc[idx, 'GW'] = maj_gw + 1
        maj_gw += 1
    elif df_calendar.loc[idx, 'Jour'] in ['Vendredi', 'Samedi', 'Dimanche']:
        df_calendar.loc[idx, 'GW'] = maj_gw + 2
        maj_gw += 2

    if df_calendar.loc[idx, 'Adversaire'] not in team_df['Équipe'].to_list():
        pass
    else:
        df_calendar.loc[idx, 'Classement'] = team_df[team_df['Équipe'] == df_calendar.loc[idx, 'Adversaire']][
            'Clt'].values

last_scores = []
for i in qsodejoseoks['data']['player']['allSo5Scores']['nodes']:

    last_scores.append(
        [i['score'], i['playerGameStats']['game']['so5Fixture']['gameWeek'], i['playerGameStats']['game']['date']])
df_last_scores = pd.DataFrame(last_scores, columns=['Score', 'Game week', 'date']).reset_index(drop=True)
df_last_scores['date'] = pd.to_datetime(df_last_scores.date).dt.date
df_last_scores =  df_last_scores.drop_duplicates(subset=['Game week']).reset_index(drop=True)

####   xScore

for idx in range(len(df_last_scores)):

    df_work = df_matchs_players[df_matchs_players[
                                    ('Unnamed: 0_level_0', 'Date')] == str(df_last_scores.loc[idx, 'date'])]

    if len(df_work) > 0:

        score = df_last_scores.loc[idx, 'Score']
        buts = df_work[('Performance', 'Buts')].values[0]
        passD = df_work[('Performance', 'PD')].values[0]
        xG = df_work[('Attendu', 'xG')].values[0]
        xA = df_work[('Attendu', 'xA')].values[0]

        if buts + passD == 1:
            score -= 35
        elif buts + passD > 1:

            retire_score = 35 + ((buts + passD - 1) * 10)
            score -= retire_score

        if xG + xA <= 1:
            xScore = score + ((xG + xA) * 35)
        else:
            xGrest = (xG + xA) - 1
            xScore = score + (35 + xGrest * 10)

        df_last_scores.loc[idx, 'xScore'] = xScore

df_last_scores = df_last_scores.set_index('Game week')
df_last_scores = df_last_scores[['Score','xScore','date']]


with row1_1, _lock:


    st.info('Derniers Scores')
    gamelog_style = df_last_scores.style.background_gradient(cmap=cm).set_precision(0)
    st.dataframe(gamelog_style, width=500,height=500)



with row1_2, _lock:

    st.warning('Action attendu VS Réél (10 gw)')
    st.metric('xD - attendu', str(round(df_matchs_players[('Attendu', 'xG')].sum() + df_matchs_players[('Attendu', 'xA')].sum(), 1)))
    st.metric('dA - réél', str(df_matchs_players[('Performance', 'Buts')].sum() +  df_matchs_players[('Performance', 'PD')].sum()))


###
# Min price

req_api_card = qsodejoseoks['data']['player']['cards']['pageInfo']
endCursor = req_api_card['endCursor']
hasNextPage = req_api_card['hasNextPage']

cards_df = pd.DataFrame(qsodejoseoks['data']['player']['cards']['nodes']).dropna(subset=['liveSingleSaleOffer'])
cards_df = cards_df[cards_df.onSale == True]

new_card = []
while hasNextPage is True:

    big_query = f"""query{{player(slug:"{player_request}"){{
              displayName
              age
    appearances
    position
    matchName
     pictureUrl
     lastClub{{
                name
                domesticLeague{{name}}
                upcomingGames(first:5){{so5Fixture{{gameWeek
                eventType
                cutOffDate}}}}
              }}
    cards(rarities:limited,after:"{endCursor}"){{
        nodes{{
                  onSale
                serialNumber
                  liveSingleSaleOffer{{price}}
                  publicSingleBuyOfferMinPrice{{amount}}
            }}
        pageInfo
            {{
                endCursor
                hasNextPage
            }}
        }}
        }}
    }}
    """
    r = post(url, json={'query': big_query})

    qsodejose = r.text
    qsodejoseoks = json.loads(qsodejose)


    req_api_card = qsodejoseoks['data']['player']['cards']['pageInfo']
    endCursor = req_api_card['endCursor']
    hasNextPage = req_api_card['hasNextPage']

    cards_df_next = pd.DataFrame(qsodejoseoks['data']['player']['cards']['nodes']).dropna(subset=['liveSingleSaleOffer'])
    cards_df_next = cards_df_next[cards_df_next.onSale == True]
    new_card.append(cards_df_next)

new_card.append(cards_df)
cards_df_ok = pd.concat(new_card)
cards_df_ok['price'] = cards_df_ok.liveSingleSaleOffer.apply(lambda x: int(x["price"][:-10]))
price = cards_df_ok['price'].min() / 100000000
st.info('Prix minimum - Limited')
st.metric('ETH', price)

### match a venir

st.info('Matchs à venir')
df_calendar = df_calendar.set_index('GW')
df_calendar = df_calendar.astype(str)

gamelog_style_df_calendar = df_calendar.T.style.background_gradient(cmap=cm).set_precision(0)

st.dataframe(gamelog_style_df_calendar, width=1200, height=1000)

st.write("data : Fbref, Sorare API")
st.subheader("xScore")
st.write("le **xScore** correspond au score sorare en remplaçant les actions décisives par \n"
         "les xG pour les buts et les xA pour les passes décisives. Par exemple, si le score \n"
         "est de **100** avec **1** but et une passe d, le score sans les actions décisives est de **55**. \n"
         "Si les xG sont de **0.7** et les xA **0.3**, le cumul serait de **1**, soit **35** pts sorare. Donc un score \n"
         "de **90**.")

st.subheader("Action attendu VS Réél (10 gw)")
st.write("**xD attendu** = Cumul des xG + xA depuis 10 matchs")
st.write("**dA** = Cumul des actions décisives depuis 10 matchs (buts + passes)")

st.subheader("Prix minimum - Limited")
st.write("Prix (eth) miminum d'une carte limited actuellement en vente.")

st.subheader("Matchs à venir")
st.write("Calendrier des 5 prochains matchs avec une estimation de la GW et le classement du futur adversaire.")

st.subheader("Si ca vous plait!")
st.write("l'application comporte de nombreux bugs, vous pouvez me faire des retours. Si vous avez des idées n'hésitez pas\n "
         "c'est un projet purement formateur pour moi ! :) ")
st.write("**contact sur Twitter** : @nununuA1124")
st.write("**manager sorare** : nunununu - l'arriere train sifflera 3 fois")