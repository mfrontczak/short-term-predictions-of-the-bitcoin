# How to run
Tested with Python 3.9.6.

### pre-requisites
```shell
python -m venv venv
. venv\Scripts\activate 
pip install -r requirements.txt
```

### creating database tables
```shell
flask db init
flask db migrate
flask db upgrade
```

### Running web application
```shell
flask run
```


