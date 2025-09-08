import requests
from bs4 import BeautifulSoup
import psycopg2
from datetime import datetime

# Connect to PostgreSQL Database
conn = psycopg2.connect(
    dbname="babyfoot",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()


# Function to fetch and parse the match data for a specific month
def fetch_and_parse_matches(year, month):
    url = f'https://babyfoot.chamrai.fr/?md={year}-{month:02d}'
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin"
    }

    # Send request
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract matches
    matches = []

    accordion = soup.find("div", id="matches")
    accordion_items = accordion.find_all("div", class_="accordion-item")

    for item in accordion_items:
        # Extract date from accordion-header button
        match_date_button = item.find("button", class_="accordion-button")
        match_date_text = match_date_button.get_text(strip=True)  # Extract date text, e.g., "30/08/2019"
        try:
            # Convert the date to the proper format (YYYY-MM-DD)
            match_date = datetime.strptime(match_date_text, "%d/%m/%Y").date()
        except Exception as e:
            print(e)
            continue
        match_rows = item.find_all("div", class_="align-items-center")

        for row in match_rows[::-1]:
            time = row.find_parent().find_parent().find("em").get_text(strip=True)
            match_timestamp = datetime.strptime(f"{match_date} {time}", "%Y-%m-%d %H:%M").replace(tzinfo=None)
            players = row.find_all("div", class_="col-sm-3")
            results = row.find_all("div", class_="text-result")

            if players and results:
                # Extract team players and results
                team1_players = players[0].get_text("+").split("+")
                team2_players = players[1].get_text("+").split("+")

                result_team1 = int(results[0].get_text(strip=True))
                result_team2 = int(results[1].get_text(strip=True))

                matches.append((match_timestamp, team1_players, team2_players, result_team1, result_team2))

    return sorted(matches, key=lambda x: x[0])


# Function to save matches and associated teams to the PostgreSQL database
def save_matches_to_db(matches):
    cursor.execute("SELECT id, player_name FROM players")
    players = cursor.fetchall()  # list of tuples like [(1, 'Alice'), (2, 'Bob'), ...]
    player_map = {name: pid for pid, name in players}  # dict: {"Alice": 1, "Bob": 2, ...}

    for match in matches:
        match_date, team1_players, team2_players, result_team1, result_team2 = match
        match_date = match_date.strftime("%Y-%m-%d %H:%M:%S")

        # Insert match details and get match ID
        cursor.execute('''INSERT INTO games (game_timestamp, result_team1, result_team2) 
                          VALUES ( %s, %s, %s) RETURNING id''',
                       (match_date, result_team1, result_team2))
        match_id = cursor.fetchone()[0]

        # Insert players for team 1

        # Insert team 1 players
        for player in team1_players:
            player_id = player_map.get(player)
            if player_id:
                cursor.execute(
                    '''INSERT INTO teams (game_id, player_id, team_number)
                       VALUES (%s, %s, %s)''',
                    (match_id, player_id, 1)
                )
            else:
                print(f"Player '{player}' not found in players table")

        # Insert team 2 players
        for player in team2_players:
            player_id = player_map.get(player)
            if player_id:
                cursor.execute(
                    '''INSERT INTO teams (game_id, player_id, team_number)
                       VALUES (%s, %s, %s)''',
                    (match_id, player_id, 2)
                )
            else:
                print(f"Player '{player}' not found in players table")

    conn.commit()


# Fetch and save matches from 2019-08 to now
start_year = 2018
start_month = 11
current_year = datetime.now().year
current_month = datetime.now().month

for year in range(start_year, current_year + 1):
    for month in range(1, 13):
        if year == start_year and month < start_month:
            continue
        if year == current_year and month > current_month:
            break

        print(f"Fetching matches for {year}-{month:02d}")
        matches = fetch_and_parse_matches(year, month)
        if matches:
            save_matches_to_db(matches)
        else:
            print(f"No matches found for {year}-{month:02d}")

# Close the connection
cursor.close()
conn.close()

print("All matches and team data have been saved to the PostgreSQL database.")
