import datetime

import psycopg2

# Database connection parameters


try:
    # Connect to the PostgreSQL database
    conn = psycopg2.connect(
        dbname="babyfoot",
        host="localhost",
        port="5432"
    )
    cursor = conn.cursor()

    # Update query to set mu_overall to 25 and sigma_overall to 25/3
    fetch_query = "SELECT id FROM players;"
    cursor.execute(fetch_query)
    player_ids = cursor.fetchall()  # Fetch all player IDs as a list of tuples

    # Insert rows into current_player_rank for each player ID
    for player_id_tuple in player_ids:
        player_id = player_id_tuple[0]  # Extract the player ID from the tuple
        insert_query = """
        INSERT INTO current_player_rank (
            player_id, mu_overall, sigma_overall, mu_monthly, sigma_monthly, mu_yearly, sigma_yearly,last_updated
        ) VALUES (
            %s, 25, 25.0/3.0, 25, 25.0/3.0, 25, 25.0/3.0,%s
        )
        ON CONFLICT (player_id) DO NOTHING;  -- Avoid duplicate entries
        """
        cursor.execute(insert_query, (player_id, datetime.datetime.now()))

    # Commit the changes
    conn.commit()
    print("Update successful!")

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    # Close the database connection
    if cursor:
        cursor.close()
    if conn:
        conn.close()
