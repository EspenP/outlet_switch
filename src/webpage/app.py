"""
Scythron
"""

import sys

from flask import Flask, render_template, request, jsonify
from datetime import date

# Append necessary python source code folders
sys.path.append('../comm/')

# Import custom packages
from RxTx import RxTx
from DataRW import DataRW
import keys

app = Flask(__name__)

@app.route('/')
def index():
    today = date.today()
    today = today.strftime('%A, %d %B, %Y')
    event = 'TBD'
    return render_template('index.html', today=today, event=event)

@app.route('/schedule.html')
def schedule():
    return render_template('schedule.html')

@app.route('/checkTitle', methods=['POST'])
def checkTitle():
    title = request.form['title']
    if data.exists(title):
        return jsonify({'result': 'Title Exists'})
    else:
        return jsonify({'result': ''})

@app.route('/getTitles', methods=['POST'])
def getTitles():
    titles = data.getTitles()
    # Need the array in reverse order for proper load in webpage
    titles.reverse()

    return jsonify({'result': titles})

@app.route('/turnOn', methods=['POST'])
def turnOn():
    title = request.form['title']

    c1, c2, c3, c4, c5, c6 = data.getOnParameters(title)
    rxtx.txCode(c1, c2, c3, c4, c5, c6)

    return jsonify({'result': ''})

@app.route('/turnOff', methods=['POST'])
def turnOff():
    title = request.form['title']

    c1, c2, c3, c4, c5, c6 = data.getOffParameters(title)
    rxtx.txCode(c1, c2, c3, c4, c5, c6)

    return jsonify({'result': ''})

@app.route('/deleteOutlets', methods=['POST'])
def deleteOutlets():
    titles = request.form.getlist('titles[]')

    for title in titles:
        data.remove(title)

    return jsonify({'result': ''})

@app.route('/removeAdd', methods=['POST'])
def removeAdd():
    title = request.form['title']

    data.remove(title)

    return jsonify({'result': ''})

def _sniffer(type):
    """
    Function used to sniff a code of a certain type (ON / OFF)
    and return the data object

    Parameters:
    -----------
    type : String
        Either keys.TYPE_CODE_ON or keys.TYPE_CODE_OFF

    Returns:
    --------
    l_data : dict
        The dictionary object containing all of the metadata
        associated with this sniffed code
    """
    # Ensure the input is a proper value
    if type != keys.TYPE_CODE_ON and type != keys.TYPE_CODE_OFF:
        s = "'type' in _sniffer() not proper value\n"
        s += "Expected %s or %s, received %s" % (keys.TYPE_CODE_ON,
                                                 keys.TYPE_CODE_OFF, type)
        raise(Exception(s))

    codes = rxtx.sniffCode()
    l_data = {}

    if codes is not None:
        title = request.form['title']
        c1, c2, c3, c4, c5, c6 = codes
        l_data[keys.OUTLET_TITLE] = title
        l_data[keys.TYPE] = type
        l_data[keys.CODE] = c1
        l_data[keys.ONE_HIGH_TIME] = c2
        l_data[keys.ONE_LOW_TIME] = c3
        l_data[keys.ZERO_HIGH_TIME] = c4
        l_data[keys.ZERO_LOW_TIME] = c5
        l_data[keys.INTERVAL] = c6

    return l_data

@app.route('/findOnCode', methods=['POST'])
def findOnCode():
    l_data = _sniffer(keys.TYPE_CODE_ON)
    out = {'result': 'Code Not Found'}

    if len(l_data) == 0:
        return jsonify(out)

    if not data.comboExists(l_data[keys.OUTLET_TITLE], keys.TYPE_CODE_ON):
        data.writeData(l_data)
        out['result'] = l_data[keys.CODE]

    return jsonify(out)

@app.route('/findOffCode', methods=['POST'])
def findOffCode():
    l_data = _sniffer(keys.TYPE_CODE_OFF)
    out = {'result': 'Code Not Found'}

    if len(l_data) == 0:
        return jsonify(out)

    if not data.comboExists(l_data[keys.OUTLET_TITLE], keys.TYPE_CODE_OFF):
        data.writeData(l_data)
        out['result'] = l_data[keys.CODE]

    return jsonify(out)


if __name__ == '__main__':
    rxtx = RxTx()
    try:
        data = DataRW()
        app.run(host='192.168.1.200', port=5000, debug=True)
        rxtx.cleanup()
    except Exception:
        print(f"Exception ocurred: {e}")
    finally:
        rxtx.cleanup()
