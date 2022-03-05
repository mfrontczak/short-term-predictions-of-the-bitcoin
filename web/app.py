import os
import requests
from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from flask_migrate import Migrate
import tensorflow as tf

os.environ['SQL_ALCHEMY_DATABASE_URI'] = 'mariadb+mariadbconnector://bh_live_predict:h3llo_crk$po1@127.0.0.1:3306/btclive'

config = {
    "DEBUG": True,          # some Flask specific configs
    "CACHE_TYPE": "SimpleCache",  # Flask-Caching related configs
    "CACHE_DEFAULT_TIMEOUT": 3600,
    "SQLALCHEMY_DATABASE_URI": os.getenv('SQL_ALCHEMY_DATABASE_URI'),
    "SQLALCHEMY_ENGINE_OPTIONS": {'pool_pre_ping': True, 'pool_recycle': 60, 'echo':'debug'}

}

app = Flask(__name__)
app.config.from_mapping(config)
cache = Cache(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)


class MLModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    model_path = db.Column(db.String(255), unique=True)
    model_internal_id = db.Column(db.Integer, nullable=True, default=0)
    look_forward = db.Column(db.Integer, nullable=False)
    look_back = db.Column(db.Integer, nullable=False)
    interval = db.Column(db.Integer, nullable=False, default=3600)  # 3600s
    train_rmse = db.Column(db.Float, nullable=True, default=-1)
    test_rmse = db.Column(db.Float, nullable=True, default=-1)

    def __repr__(self):
        return f"<MLModel:{self.model_path}>"


class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    model_id = db.Column(db.Integer, db.ForeignKey(MLModel.id))
    value = db.Column(db.Float)
    timestamp = db.Column(db.Integer)

    def __repr__(self):
        return f"<Prediction: v:{self.value} ts:{self.timestamp} mlid:{self.model_id}>"

    def to_dict(self):
        return {
            'y': self.value,
            'x': self.timestamp
        }


@app.route('/')
def index():
    ml_models = MLModel.query.all()
    return render_template('index.html', ml_models=ml_models)

@cache.cached(timeout=60)
@app.route('/api/predictions/<ml_id>/')
def api_prediction(ml_id=1):
    ml_model = MLModel.query.get(int(ml_id))
    data = []
    if ml_model:
        r = requests.get(f"https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=3600&limit={ml_model.look_back+1}")
        json_data = r.json()
        ohlc = json_data["data"]["ohlc"]
        last_timestamp = int(ohlc[-1]["timestamp"])
        timestamp = last_timestamp + 3600
        historical_predictions = Prediction.query.filter_by(model_id=ml_model.id)\
            .order_by(Prediction.timestamp)\
            .limit(48).all()
        model = tf.keras.models.load_model(ml_model.model_path)
        pred = model.predict([[float(data["close"]) for data in ohlc[:-1]]])
        predictions = pred.tolist()[0]
        for value in predictions:
            data.append({
                'y': value,
                'x': timestamp
            })
            timestamp += 3600
        data = [hp.to_dict() for hp in historical_predictions] + data
    return jsonify({'data': data})


if __name__ == '__main__':
    app.run()
