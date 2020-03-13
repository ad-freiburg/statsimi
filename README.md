# staty

**Work in progress, without any warranty**

Framework for station similarity classification.

## Requirements

 * `python3`
 * `sklearn`
 * `matplotlib`
 * `numpy`
 * `scipy`

## Building and Installation

Fetch this repository and init submodules:

```
git clone --recurse-submodules https://github.com/ad-freiburg/staty
cd staty
```
Create virtual environment
```
python3 -m venv venv
source venv/bin/activate
```
Build dependencies
```
pip3 install -r requirements.txt
make install
```

# Quickstart

Build a classification model `classify.mod` for Germany (uses a random 20% of the input as training samples per default):

```
wget https://download.geofabrik.de/europe/germany-latest.osm.bz2
bunzip2 germany-latest.osm.bz2
python3 staty.py model --model_out classify.mod --train germany-latest.osm
```

Write a fix file `germany.fix` for `germany.osm` based on the previously build model:

```
python3 staty.py fix --model classify.mod --fix_out germany.fix --test germany-latest.osm
```


``

# General Usage

`staty` can be used to train and output a reusable classification model, to start a classification HTTP server or to evaluate methods against some dataset.

The following basic commands are supported:

* `model` (write a classification model for the given input data to a file)
* `evaluate` (test the given model or the given approach against a ground truth)
* `fix`	(write a file with fix suggestions and error highlights for the input OSM data)
* `http` (fire up a classification server for the given model and/or input data)


## Train a model
```
python3 staty.py model --train <train_input> -p <train_perc> --model_out <file> --method <method>
```

## Evaluate a model
```
python3 staty.py model --train <train_input> -p <train_perc> --model_out <file> --method <method>
```

TODO
