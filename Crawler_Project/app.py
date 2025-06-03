from flask import Flask, render_template, request, jsonify
import mysql.connector
import urllib.parse

app = Flask(__name__)

def get_db_connection():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="news_db"
    )
    return connection

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_top_words/<path:category>', methods=['GET'])
def get_top_words(category):
    category = urllib.parse.unquote(category)  # 디코딩 추가
    connection = get_db_connection()
    cursor = connection.cursor()
    
    cursor.execute("""
        SELECT keyword, COUNT(*) as freq 
        FROM keywords_links 
        WHERE category = %s 
        GROUP BY keyword 
        ORDER BY freq DESC 
        LIMIT 20
    """, (category,))
    
    top_words = cursor.fetchall()
    cursor.close()
    connection.close()
    return jsonify(top_words)

@app.route('/search', methods=['POST'])
def search():
    word = request.json['word']
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT title, link FROM news_data WHERE title LIKE %s", ("%" + word + "%",))
    links = cursor.fetchall()
    cursor.close()
    connection.close()
    return jsonify([{"title": link[0], "link": link[1]} for link in links])

if __name__ == '__main__':
    app.run(debug=True)