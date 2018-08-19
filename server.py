#!flask/bin/python

"""
Starts the Pitcher Web server
"""

from flask import Flask
from flask import Flask, abort, request, render_template
from flask import Response
import logging
import mysql.connector
from mysql.connector import errorcode
from dicttoxml import dicttoxml


def fetch_data(query):
    config = {'user': 'root',
        'password': 'Qbg157.8',
        'host': 'localhost',
        'database': 'Pitchers'}
    try:
        cnx = mysql.connector.connect(**config)
        cursor = cnx.cursor()
        cursor.execute(query)
        query_result = [ dict(line) for line in [zip([ column[0] for column in cursor.description], row) for row in cursor.fetchall()]]
        return query_result
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)
    else:
        cnx.close()



app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/v1.0/pitchers/<amount>', methods=['POST', 'GET'])
def pitchers(amount):
    global my_num;
    my_num = int(amount)
    query = "SELECT * FROM mlb_stats_2018 LIMIT {0};".format(str(amount))
    data = fetch_data(query)
    xml = dicttoxml(data, custom_root='Pitchers', attr_type=True)
    return Response(xml, mimetype='text/xml')


@app.route('/api/v1.0/all', methods=['GET'])
def all():
    query = "SELECT * FROM mlb_stats_2018;"
    data = fetch_data(query)
    xml = dicttoxml(data, custom_root='Pitchers', attr_type= True)
    return Response(xml, mimetype='text/xml')


@app.route('/api/v1.0/salaries', methods=['GET'])
def salaries():
    query = "SELECT DISTINCT(Name), 2018_salary FROM mlb_stats_2018 WHERE 2018_salary > 0 ORDER BY 2018_salary DESC;"
    data = fetch_data(query)
    xml = dicttoxml(data, custom_root='Salaries', attr_type= True)
    return Response(xml, mimetype='text/xml')

@app.route('/api/v1.0/members', methods=['GET'])
def members():
    return render_template('team.html')

if __name__ == '__main__':
    app.run(debug=True)
