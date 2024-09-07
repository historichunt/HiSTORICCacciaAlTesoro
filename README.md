# HiSTORICCacciaAlTesoro
Caccie al tesoro di [hiSTORIC Trento](https://www.historictrento.it)

## gcloud commands
```
gcloud config list project
gcloud config set project historictrentobot
gcloud app deploy -q -v test/production
```

## run locally, use one of the following:
`uvicorn historic.main:app --port 5000 --reload`

## update metadata schema from `template`
python -m historic.bot.airtable_metadata

## Activating a game with url start
`https://t.me/hiSTORICtrentobot?start=secret_password`

## pyngrok cert problem
see https://stackoverflow.com/a/61294657/5489042