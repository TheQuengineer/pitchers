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
import pandas as pd
from xml.dom.minidom import parseString
import xml.etree.ElementTree as ET

def fetch_data(query):
    config = {'user': 'root',
        'password': 'MYwedin05!',
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


def read_xml_as_dataframe(filename):
    in_file = open(filename, "rb") # opening for [r]eading as [b]inary
    xml_data = in_file.read() # if you only wanted to read 512 bytes, do .read(512)
    in_file.close()
    xml2df = XML2DataFrame(xml_data)
    xml_dataframe=xml2df.process_data()
    del xml_dataframe['Pitcher']
    del xml_dataframe['PitcherId']
    xml_dataframe['AdjustedScore'] = xml_dataframe.AdjustedScore.astype(float)
    return xml_dataframe
    
app = Flask(__name__)

def func(row):
    xml = ['    <Pitcher>']
    for field in row.index:
        xml.append('        <{0}>{1}</{0}>'.format(field, row[field]))
    xml.append('    </Pitcher>')
    return '\n'.join(xml)

class XML2DataFrame:

    def __init__(self, xml_data):
        self.root = ET.XML(xml_data)

    def parse_root(self, root):
        return [self.parse_element(child) for child in iter(root)]

    def parse_element(self, element, parsed=None):
        if parsed is None:
            parsed = dict()
        for key in element.keys():
            parsed[key] = element.attrib.get(key)
        if element.text:
            parsed[element.tag] = element.text
        for child in list(element):
            self.parse_element(child, parsed)
        return parsed

    def process_data(self):
        structure_data = self.parse_root(self.root)
        return pd.DataFrame(structure_data)

        
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

@app.route('/api/v1.0/genxml', methods=['GET'])
def genxml():
    query = "SELECT ﻿Rk as PitcherId, Name, FIP as Fip, 2018_salary as Salary FROM `pitchers`.`mlb_stats_2018`;"
    data = fetch_data(query)
    df = pd.DataFrame(data)

    #Calculate the mean and standard deviation of our FIP and Salary core fields
    FipStd = round(df['Fip'].std(),4)
    SalaryStd = round(df['Salary'].std(),4)
    FipMean = round(df['Fip'].mean(),4)
    SalaryMean = round(df['Salary'].mean(),4)

    #Calculate the standard deviations from the mean of our FIP and Salary core fields
    df['FipStdDev'] = round((df['Fip'] - FipMean)/FipStd,4)
    df['SalaryStdDev'] = round((df['Salary'] - SalaryMean)/SalaryStd,4)

    #Calculate the adjusted score of the pitcher by summing the standard deviations from the mean for FIP and Salary.
    #Since low scores in FIP and Salary are good, multiply the sum by -1 so to get a score where high scores are good.
    df['AdjustedScore'] = round(-1 * (df['FipStdDev'] + df['SalaryStdDev']),4)

    #Convert to XML
    xmlHeader = '<?xml version="1.0"?>' + '\n' + '<Pitchers>' + '\n'
    xml = xmlHeader + '\n'.join(df.apply(func, axis=1)) + '\n' + '</Pitchers>'

    #Write XML to a file
    dom = parseString(xml)
    f1=open('data/RankedPitchers.xml', 'w+')
    f1.write(dom.toprettyxml())
    f1.close()

    #Write response XML back to the screen
    return Response(xml, mimetype='text/xml')

    
@app.route('/api/v1.0/calctopten', methods=['GET'])
def calctopten():
    xml_dataframe = read_xml_as_dataframe('data/RankedPitchers.xml') 
    xml_dataframe=xml_dataframe.nlargest(10, 'AdjustedScore')
    return render_template('topten.html',tables=[xml_dataframe.to_html(index=False)],titles = ['na', 'Top Ten Pitchers Most Worth Their Salary'])

@app.route('/api/v1.0/calcbottomten', methods=['GET'])
def calcbottomten():
    xml_dataframe = read_xml_as_dataframe('data/RankedPitchers.xml') 
    xml_dataframe=xml_dataframe.nsmallest(10, 'AdjustedScore')
    return render_template('bottomten.html',tables=[xml_dataframe.to_html(index=False)],titles = ['na', 'Top Ten Pitchers Least Worth Their Salary'])

if __name__ == '__main__':
    app.run(debug=True)
