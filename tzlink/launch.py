#!/usr/bin/env python3
# coding: utf8

# Author: Lenz Furrer, 2018--2019


'''
Train or predict in ranking or classification mode.
'''


# NOTE: Ensemble prediction has put some restrictions on the code structure.
# - In order to free up memory after a model has finished predicting, each
#   model is run in a separate child process.
# - The std-lib multiprocessing module is used. The joblib implementation
#   seems not to allow creating a child process for a single worker; instead,
#   everything is run in the main process for `n_jobs=1`. But then memory won't
#   be freed between model loading. So joblib can't be used to load multiple
#   models in series.
# - If the parent process imports keras, it puts its hands on the GPU and
#   doesn't allow child processes to allocate any memory. Therefore, importing
#   keras is delayed until we know whether to do it in the main process
#   (training, regular prediction) or in the child processes (ensemble
#   prediction).


import sys
import logging
import tempfile
import importlib
import multiprocessing as mp

import numpy as np

from .util.util import get_config
from .util.record import Recorder
from .util import startup


def launch(config, record=False, **kwargs):
    '''
    Setup and run the CNN.
    '''
    conf = get_config(config)
    recorder = Recorder(conf)

    run(conf, summary=[sys.stdout, recorder.results], **kwargs)
    if record:
        recorder.dump()


def run(conf, mode, train=True, dumpfns=(), **evalparams):
    '''
    Run the CNN (incl. preprocessing).
    '''
    module = importlib.import_module('tzlink.{}'.format(mode))
    # Catch early some common option mistakes.
    if train:
        if not dumpfns:
            with tempfile.NamedTemporaryFile(delete=False) as f:
                dumpfns = [f.name]
        elif len(dumpfns) > 1:
            raise ValueError('cannot save model to multiple files')
        _run_train(conf, module, dumpfns[0], **evalparams)
    else:
        if not dumpfns:
            raise ValueError('no model to train or load')
        _run_predict(conf, module, dumpfns, **evalparams)


def _run_train(conf, module, dumpfn, **evalparams):
    '''
    Train a model and evaluate/predict.
    '''
    startup.run_scripts(conf)
    module.run_training(conf, dumpfn, **evalparams)


def _run_predict(conf, module, dumpfns, **evalparams):
    '''
    Load a model for evaluation/predictions.
    '''
    val_data = module.prediction_samples(conf)
    val_data.scores = _predict(conf, dumpfns, val_data.x)
    logging.info('evaluate and/or serialize...')
    module.Evaluator.handle_predictions(conf, val_data, **evalparams)
    logging.info('done.')


def _predict(conf, dumpfns, x):
    batch_size = conf.rank.batch_size
    if len(dumpfns) == 1:
        return _predict_one(conf, dumpfns[0], x, batch_size)

    # Ensemble prediction.
    with tempfile.NamedTemporaryFile() as f:
        np.savez(f, *x)  # avoid repeated pickling
        args = [(conf, fn, f.name, batch_size) for fn in dumpfns]
        workers = conf.rank.workers or 1
        with mp.Pool(workers, maxtasksperchild=1) as pool:
            scores = list(pool.map(_wrap_predict_one, args))
    return np.mean(scores, axis=0)


def _wrap_predict_one(args):
    conf, model_fn, x_fn, batch_size = args
    with np.load(x_fn) as f:
        x = [f[n] for n in sorted(f.files)]
    return _predict_one(conf, model_fn, x, batch_size)


def _predict_one(conf, fn, x, batch_size):
    startup.run_scripts(conf)
    from keras.models import load_model
    from .rank.cnn import PairwiseSimilarity

    logging.info('load pretrained model from %s...', fn)
    model = load_model(fn, custom_objects={
        'PairwiseSimilarity': PairwiseSimilarity,
    })
    logging.info('predict scores for validation data...')
    return model.predict(x, batch_size=batch_size)
