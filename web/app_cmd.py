import click
import requests
import tensorflow as tf
from app import db, Prediction, MLModel


@click.command()
def run_predictions():
    ml_models = MLModel.query.all()
    r = requests.get(f"https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=3600&limit=169")
    json_data = r.json()
    ohlc = json_data["data"]["ohlc"]
    last_timestamp = int(ohlc[-1]["timestamp"])
    for ml_model in ml_models:
        model = tf.keras.models.load_model(ml_model.model_path)
        timestamp = last_timestamp + 3600
        pred = model.predict([[float(data["close"]) for data in ohlc[-ml_model.look_back-1:-1]]])
        predictions = pred.tolist()[0]
        prediction = Prediction()
        prediction.model_id = ml_model.id
        prediction.value = round(predictions[0], 2)
        prediction.timestamp = timestamp
        try:
            db.session.add(prediction)
            db.session.commit()
        except Exception as e:
            print(e)
            db.session.rollback()


if __name__ == "__main__":
    run_predictions()
