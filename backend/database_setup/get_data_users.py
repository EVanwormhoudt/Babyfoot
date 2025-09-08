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

# Create table for players with a column for player name and color
cursor.execute('''CREATE TABLE IF NOT EXISTS players (
    id SERIAL PRIMARY KEY,
    player_name TEXT UNIQUE,
    player_color TEXT,
    active BOOLEAN,
    rating INTEGER DEFAULT 1000
)''')
conn.commit()


# Function to fetch and parse the player list from the HTML
def fetch_and_parse_players():
    url = 'https://babyfoot.chamrai.fr/'  # Replace with the actual URL that contains the player list
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin"
    }

    # Send request
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract players from the HTML
    players = []
    player_rows = soup.find_all("td", class_="text-nowrap")

    for player_row in player_rows:
        # Extract the player color from the <input> tag
        player_color = player_row.find("input", {"type": "color"}).get("value")

        # Extract the player name from the <span> with class 'player-name'
        player_name = player_row.find("span", class_="player-name").get_text(strip=True)

        # Extract the active status from the checkbox (checked means active)
        active_checkbox = player_row.find("input", {"type": "checkbox", "name": "active"})
        is_active = active_checkbox is not None and active_checkbox.has_attr('checked')

        players.append((player_name, player_color, is_active))

    return players


# Function to save players to the PostgreSQL database (skip duplicates)
def save_players_to_db(players):
    for player in players:
        try:
            cursor.execute('''INSERT INTO players (player_name, player_color, active) 
                              VALUES (%s, %s, %s) 
                              ON CONFLICT (player_name) 
                              DO UPDATE SET player_color = EXCLUDED.player_color, active = EXCLUDED.active''', player)
        except Exception as e:
            print(f"Error inserting player: {player}, {e}")
    conn.commit()


# Fetch and save players
players = fetch_and_parse_players()
if players:
    save_players_to_db(players)
    print(f"{len(players)} players have been saved to the database.")
else:
    print("No players found.")

# Close the connection
cursor.close()
conn.close()
