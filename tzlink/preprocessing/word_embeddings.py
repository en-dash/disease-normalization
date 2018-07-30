#!/usr/bin/env python3
# coding: utf8

# Author: Lenz Furrer, 2018


'''
Load word embeddings.
'''


import numpy as np
from gensim.models.keyedvectors import KeyedVectors


def load(econf):
    '''
    Load embeddings from binary and create a lookup table.
    '''
    fn = econf.embedding_fn
    if fn.endswith('.kv'):
        wv = KeyedVectors.load(fn, mmap='r')
    else:
        wv = KeyedVectors.load_word2vec_format(fn, binary=fn.endswith('.bin'))
    lookup = {w: i+2 for i, w in enumerate(wv.index2word)}
    # Add two rows in the beginning: one for padding and one for unknown words.
    dim = wv.syn0.shape[1]
    dtype = wv.syn0.dtype
    padding = np.zeros(dim, dtype)
    unknown = np.random.standard_normal(dim).astype(dtype)
    matrix = np.concatenate([[padding, unknown], wv.syn0])
    return lookup, matrix
