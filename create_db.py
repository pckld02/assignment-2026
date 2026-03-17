import sqlite3

connection = sqlite3.connect('database.db')
cursor = connection.cursor() # notice the use of the same connection object named on the previous line
cursor.execute(
    '''CREATE TABLE IF NOT EXISTS cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card TEXT NOT NULL,
    suit TEXT NOT NULL
    )'''
)

# Use loops to add cards to the cards table
values = ['2','3','4','5','6','7','8','9','T','J','Q','K','A']
suits = ["\u2660", "\u2665", "\u2666", "\u2663"]
cards = []
for suit in suits:
    for value in values:
        card = (value,suit)
        cards.append(card)

print(cards)

cursor.executemany('INSERT INTO cards (card, suit) VALUES (?,?)', cards)

connection.commit() # This saves the changes you have made
connection.close() # This closes the connection
