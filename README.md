# statsimi

**Work in progress, without any warranty**

Framework for station similarity classification.

[![Two stations, marked by 3 station identifiers, in the fictional town of Newton.](example_res.png?raw=true)](example.png?raw=true)
*Three station identifiers of two stations in the fictional town of Newton, and some of their similarity relationships.*

## Requirements

 * `python3`
 * `sklearn`
 * `matplotlib`
 * `numpy`
 * `scipy`

## Building and Installation

Fetch this repository:

```
git clone https://github.com/ad-freiburg/statsimi
cd statsimi
```
Create virtual environment
```
python3 -m venv venv
source venv/bin/activate
```
Build & Install
```
pip install .
```

# Quickstart

Build a classification model `classify.mod` for Germany (uses a random 20% of the input as training samples per default):

```
wget https://download.geofabrik.de/europe/germany-latest.osm.bz2
bunzip2 germany-latest.osm.bz2
statsimi model --model_out classify.mod --train germany-latest.osm
```

Write a fix file `germany.fix` for `germany-latest.osm` based on the previously build model:

```
statsimi fix --model classify.mod --fix_out germany.fix --test germany-latest.osm
```


``

# General Usage

`statsimi` can be used to train and output a reusable classification model, to start a classification HTTP server or to evaluate methods against some dataset.

The following basic commands are supported:

* `model` (write a classification model for the given input data to a file)
* `evaluate` (test the given model or the given approach against a ground truth)
* `fix`	(write a file with fix suggestions and error highlights for the input OSM data)
* `http` (fire up a classification server for the given model and/or input data)


## Train a model
```
statsimi model --train <train_input> -p <train_perc> --model_out <model_file> --method <method>
```
where `method` may be one of those listed in `statsimi --help`.

## Classification server
Using a previously trained model, a classification HTTP server can be started like this:
```
statsimi http --model <model_file> --http_port <port>
```

A typical request then looks like this:
```
http://localhost:8282/?name1=Bertoldsbrunnen&lat1=47.995662&lon1=7.846041&name2=Freiburg,%20Bertoldsbrunnen&lat2=47.995321&lon2=7.846341
```

The answer will be

```
{"res": 1}
```
if the two stations are similar, or
```
{"res": 0}
```
if they are not similar.

## Evaluate a model

To evaluate a model against a ground truth, use

```
statsimi evaluate --model <model_file> --test <osm_data>
```

where `<model_file>` is a pre-trained model and `<osm_data>` is a OSM file (the ground truth data). `statsimi` will output precision, recall, F1 score, a confusion matrix and typical true positives, true negatives, false positives and false negatives.

## Fix OSM data

To fix OSM data, use

```
statsimi fix --model <model_file> --test <osm_data> --fix_out <fix_file>
```

where `<model_file>` is a pre-trained model and `<osm_data>` is an OSM file containing the data to be fixed. `statsimi` will analyze the input OSM data and output suggestions to stdout as well as into a file `<fix_file>` in a machine readable format (TODO: documentation of this format).
