from flask import Flask, request, g
from flask_restful import Resource, Api
from sqlalchemy import create_engine, select, MetaData, Table
from flask import jsonify
import json
import eth_account
import algosdk
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import load_only

from models import Base, Order, Log
engine = create_engine('sqlite:///orders.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)

app = Flask(__name__)

#These decorators allow you to use g.session to access the database inside the request code
@app.before_request
def create_session():
    g.session = scoped_session(DBSession) #g is an "application global" https://flask.palletsprojects.com/en/1.1.x/api/#application-globals

@app.teardown_appcontext
def shutdown_session(response_or_exc):
    g.session.commit()
    g.session.remove()

"""
-------- Helper methods (feel free to add your own!) -------
"""

def log_message(d):
    # Takes input dictionary d and writes it to the Log table
    obj = Log()
    for r in d.keys():
        obj.__setattr__(r, d[r])
    session = g.session()
    session.add(obj)
    session.commit()

"""
---------------- Endpoints ----------------
"""
    
@app.route('/trade', methods=['POST'])
def trade():
    if request.method == "POST":
        content = request.get_json(silent=True)
        print( f"content = {json.dumps(content)}" )
        columns = [ "sender_pk", "receiver_pk", "buy_currency", "sell_currency", "buy_amount", "sell_amount", "platform" ]
        fields = [ "sig", "payload" ]
        error = False
        for field in fields:
            if not field in content.keys():
                print( f"{field} not received by Trade" )
                print( json.dumps(content) )
                log_message(content)
                return jsonify( False )
        
        error = False
        for column in columns:
            if not column in content['payload'].keys():
                print( f"{column} not received by Trade" )
                error = True
        if error:
            print( json.dumps(content) )
            log_message(content)
            return jsonify( False )
        #Your code here
        #Note that you can access the database session using g.session
        sig=content["sig"]
        payload=content["payload"]
        platform=payload["platform"]
        sender_pk=payload["sender_pk"]
        flag=False
        #check sig
        if platform=="Ethereum":
            msg=json.dumps(payload)
            eth_encoded_msg=eth_account.messages.encode_defunct(text=msg)
            user_account=eth_account.Account.recover_message(signable_message=eth_encoded_msg,signature=sig)
            if sender_pk==user_account:
                flag=True
        if platform=="Algorand":
            msg = json.dumps(payload)
            if algosdk.util.verify_bytes(msg.encode('utf-8'), sig,sender_pk):
                flag = True
        if flag:
            #save this order
            order_dict={}
            order_dict['sender_pk'] = payload['sender_pk']
            order_dict['receiver_pk'] = payload['receiver_pk']
            order_dict['buy_currency'] = payload['buy_currency']
            order_dict['sell_currency'] = payload['sell_currency']
            order_dict['buy_amount'] = payload['buy_amount']
            order_dict['sell_amount'] = payload['sell_amount']
            order_dict['signature'] = sig
            obj = Order()
            for r in order_dict.keys():
                obj.__setattr__(r, order_dict[r])
            session=g.session()
            session.add(obj)
            session.commit()
            error=True
        else:
            log_dict = {}
            log_dict['message'] = json.dumps(payload)
            log_message(log_dict)
            error=True
        return jsonify(error)



@app.route('/order_book')
def order_book():
    #Your code here
    #Note that you can access the database session using g.session
    result = {}
    session = g.session()
    data = session.query(Order).all()
    datas = []
    for obj in data:
        order_dict = {}
        order_dict['sender_pk'] = obj.sender_pk
        order_dict['receiver_pk'] = obj.receiver_pk
        order_dict['buy_currency'] = obj.buy_currency
        order_dict['sell_currency'] = obj.sell_currency
        order_dict['buy_amount'] = obj.buy_amount
        order_dict['sell_amount'] = obj.sell_amount
        order_dict['signature'] = obj.signature
        datas.append(order_dict)
    result["data"] = datas
    return jsonify(result)

if __name__ == '__main__':
    app.run(port='5002')
