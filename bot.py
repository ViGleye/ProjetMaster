import discord
from discord.ext import commands
import requests
import config  # Importez le fichier de configuration

intents = discord.Intents.all()

bot = commands.Bot(command_prefix='!', intents=intents)
api_key_lol = config.lolAPI  # Utilisez la clé API depuis le fichier de configuration

@bot.event
async def on_ready():
    print(f'Bot is connected as {bot.user.name}')

def convert_puuid_to_username(puuids):
    usernames = []
    for puuid in puuids:
        summoner_url = f'https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}?api_key={api_key_lol}'
        summoner_response = requests.get(summoner_url)
        try:
            summoner_data = summoner_response.json()
            summoner_name = summoner_data['name']
            usernames.append(summoner_name)
        except (ValueError, KeyError):
            usernames.append(f'Unknown Summoner ({puuid})')
    return usernames

@bot.command(name='stat')
async def get_player_stats(ctx, summoner_name_region):
    [summoner_name, summoner_code] = summoner_name_region.split('#')
    await ctx.send(f'{summoner_name}, {summoner_code}')

    # Étape 1 : Récupérer le puuid
    account_url = f'https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{summoner_name}/{summoner_code}?api_key={api_key_lol}'
    account_response = requests.get(account_url)

    try:
        account_data = account_response.json()
        puuid = account_data['puuid']
    except (ValueError, KeyError):
        await ctx.send(f'Impossible de trouver le joueur {summoner_name}. Veuillez vérifier le nom du joueur et réessayer.')
        return

    # Étape 2 : Récupérer le summoner ID
    summoner_url = f'https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}?api_key={api_key_lol}'
    summoner_response = requests.get(summoner_url)
    try:
        summoner_data = summoner_response.json()
        summoner_id = summoner_data['id']
    except (ValueError, KeyError):
        await ctx.send(f'Impossible de récupérer les informations du summoner pour {summoner_code}.')
        return

    league_url = f'https://euw1.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}?api_key={api_key_lol}'
    league_response = requests.get(league_url)
    league_data = league_response.json()  # Ajoutez cette ligne pour décoder le JSON
    
    try : 
            solo_ranked = next(league for league in league_data if league['queueType'] == 'RANKED_SOLO_5x5')
    except StopIteration:
            solo_ranked =  {"tier":"UNRANKED", "rank":"UNRANKED", "leaguePoints":0, "wins":0, "losses":0, "leagueName":"UNRANKED"}
    try :
            flex_ranked = next(league for league in league_data if league['queueType'] == 'RANKED_FLEX_SR')
    except StopIteration:
            flex_ranked =  {"tier":"UNRANKED", "rank":"UNRANKED", "leaguePoints":0, "wins":0, "losses":0, "leagueName":"UNRANKED"}
    
        # Afficher les informations de la ligue
    if solo_ranked:
            solo_tier = solo_ranked['tier']
            solo_rank = solo_ranked['rank']
            solo_lp = solo_ranked['leaguePoints']
            solo_wins = solo_ranked['wins']
            solo_losses = solo_ranked['losses']
            solo_winrate = (solo_wins / (solo_wins + solo_losses)) * 100 if (solo_wins + solo_losses) > 0 else 0

            await ctx.send(f"**Ranked Solo 5v5:** {solo_tier} {solo_rank} ({solo_lp} LP)\n"
                           f"**Wins/Losses:** {solo_wins}/{solo_losses}\n"
                           f"**Winrate:** {solo_winrate:.2f}%")

    if flex_ranked:
            flex_tier = flex_ranked['tier']
            flex_rank = flex_ranked['rank']
            flex_lp = flex_ranked['leaguePoints']
            flex_wins = flex_ranked['wins']
            flex_losses = flex_ranked['losses']
            flex_winrate = (flex_wins / (flex_wins + flex_losses)) * 100 if (flex_wins + flex_losses) > 0 else 0

            await ctx.send(f"**Ranked Flex:** {flex_tier} {flex_rank} ({flex_lp} LP)\n"
                           f"**Wins/Losses:** {flex_wins}/{flex_losses}\n"
                           f"**Winrate:** {flex_winrate:.2f}%")



@bot.command(name='match')
async def get_match_details(ctx, summoner_name_region, match_number: int):
    [summoner_name, summoner_code] = summoner_name_region.split('#')
    await ctx.send(f'{summoner_name}, {summoner_code}')

    # Étape 1 : Récupérer le puuid
    account_url = f'https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{summoner_name}/{summoner_code}?api_key={api_key_lol}'
    account_response = requests.get(account_url)

    try:
        account_data = account_response.json()
        puuid = account_data['puuid']
    except (ValueError, KeyError):
        await ctx.send(f'Impossible de trouver le joueur {summoner_name}. Veuillez vérifier le nom du joueur et réessayer.')
        return

    # Étape 2 : Récupérer le compte
    summoner_url = f'https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}?api_key={api_key_lol}'
    summoner_response = requests.get(summoner_url)
    try:
        summoner_data = summoner_response.json()
        account_id = summoner_data['accountId']
    except (ValueError, KeyError):
        await ctx.send(f'Impossible de récupérer les informations du compte pour {summoner_code}.')
        return

    # Étape 3 : Get les match IDs
    matchlist_url = f'https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=20&api_key={api_key_lol}'
    matchlist_response = requests.get(matchlist_url)
    matchlist_data = matchlist_response.json()

    # Vérifier si le numéro de match est dans la plage des 20 dernières parties
    if match_number < 1 or match_number > len(matchlist_data):
        await ctx.send("Numéro de match invalide. Utilisez un numéro entre 1 et 20.")
        return

    # Sélectionner le match en fonction du numéro fourni
    match_id = matchlist_data[match_number - 1]

    # Étape 4 : Get les infos de la partie sélectionnée
    match_info_url = f'https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={api_key_lol}'
    match_info_response = requests.get(match_info_url)
    match_info_data = match_info_response.json()

    # Récupérer le statut de victoire du joueur actuel
    participant_data = next(participant for participant in match_info_data['info']['participants'] if participant['puuid'] == puuid)
    win_status = participant_data['win']

    # Afficher le statut de victoire
    if win_status:
        await ctx.send(f"{summoner_name} a gagné la partie {match_number} et il y avait :")
    else:
        await ctx.send(f"{summoner_name} a perdu la partie {match_number} et il y avait :")

    # Récupérer les noms des joueurs dans l'équipe et ceux contre
    participants = match_info_data['info']['participants']

    team1 = [participant for participant in participants if participant["teamId"] == 100]
    team2 = [participant for participant in participants if participant["teamId"] == 200]
    lanes = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY", "Invalid"]

    if team1[0]['individualPosition'] != "Invalid":
        team1.sort(key=lambda x: lanes.index(x["individualPosition"]))
        team2.sort(key=lambda x: lanes.index(x["individualPosition"]))
    # mise en forme de la sortie pour !match 
    res = "```Equipe 1                                                    Equipe 2\n"
    for i in range(len(team1)):
        txt = f"{team1[i]['summonerName']} ({team1[i]['championName']})"
        space = " "*(60-len(txt))
        res += f"{txt}{space}{team2[i]['summonerName']} ({team2[i]['championName']})\n"
        txt = f"KDA : {team1[i]['kills']}/{team1[i]['deaths']}/{team1[i]['assists']}"
        space = " "*(60-len(txt))
        res += f"{txt}{space}KDA : {team2[i]['kills']}/{team2[i]['deaths']}/{team2[i]['assists']}\n"
    res += "```"

    # Afficher les noms des joueurs
    await ctx.send(res)

    # Récupérer le temps de la partie
    game_duration = match_info_data['info']['gameDuration']
    minutes, seconds = divmod(game_duration, 60)

    # Afficher le temps de la partie
    await ctx.send(f"**Durée de la partie:** {minutes} minutes et {seconds} secondes")



@bot.event
async def on_message(message):
    if bot.user.mentioned_in(message):
        await message.channel.send(f'{message.author.mention}, voici la commande `!stat` avec le nom du joueur : `!stat "nomjoueur#euw` "Et la commande `!match nomjoueur#*** (partie entre 1-20)` pour afficher votre  match !"')

    await bot.process_commands(message)

bot.run(config.discordAPI)
