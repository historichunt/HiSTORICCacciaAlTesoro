# HiSTORICCacciaAlTesoro
Caccie al tesoro di [hiSTORIC Trento](https://www.historictrento.it)

## gcloud commands
```
gcloud config list project
gcloud config set project historictrentobot
gcloud app deploy -q -v test/production
```

## run locally, use one of the following:
1. `flask run`
2. `gunicorn -b localhost:5000 main:app --chdir bot`

## Activating a game with url start
`https://t.me/hiSTORICtrentobot?start=secret_password`
