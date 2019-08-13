# Copyright 2019 Cortex Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys

import tensorflow as tf

from cortex.lib import util
from cortex import consts


CORTEX_TYPE_TO_TF_TYPE = {
    consts.COLUMN_TYPE_INT: tf.int64,
    consts.COLUMN_TYPE_INT_LIST: tf.int64,
    consts.COLUMN_TYPE_FLOAT: tf.float32,
    consts.COLUMN_TYPE_FLOAT_LIST: tf.float32,
    consts.COLUMN_TYPE_STRING: tf.string,
    consts.COLUMN_TYPE_STRING_LIST: tf.string,
}


CPP_LOG_LEVEL = {"DEBUG": "1", "INFO": "2", "WARN": "3", "ERROR": "4", "FATAL": "5"}


def set_logging_verbosity(verbosity):
    tf.logging.set_verbosity(verbosity)
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = CPP_LOG_LEVEL[verbosity]


def get_column_tf_types(model_name, ctx, training=True):
    """Generate a dict {column name -> tf_type}"""
    model = ctx.models[model_name]

    column_types = {}
    for column_name in ctx.extract_column_names(model["input"]):
        column_type = ctx.get_inferred_column_type(column_name)
        column_types[column_name] = CORTEX_TYPE_TO_TF_TYPE[column_type]

    if training:
        for column_name in ctx.extract_column_names(model["target_column"]):
            column_type = ctx.get_inferred_column_type(column_name)
            column_types[column_name] = CORTEX_TYPE_TO_TF_TYPE[column_type]

        for column_name in ctx.extract_column_names(model.get("training_input")):
            column_type = ctx.get_inferred_column_type(column_name)
            column_types[column_name] = CORTEX_TYPE_TO_TF_TYPE[column_type]

    return column_types


def get_feature_spec(model_name, ctx, training=True):
    """Generate a dict {column name -> FixedLenFeatures} for use in tf.parse_example"""
    column_types = get_column_tf_types(model_name, ctx, training)
    feature_spec = {}
    for column_name, tf_type in column_types.items():
        column_type = ctx.get_inferred_column_type(column_name)
        if column_type in consts.COLUMN_LIST_TYPES:
            feature_spec[column_name] = tf.FixedLenSequenceFeature(
                shape=(), dtype=tf_type, allow_missing=True
            )
        else:
            feature_spec[column_name] = tf.FixedLenFeature(shape=(), dtype=tf_type)
    return feature_spec


def get_base_input_columns(model_name, ctx):
    model = ctx.models[model_name]
    base_column_names = set()
    for column_name in ctx.extract_column_names(model["input"]):
        if ctx.is_raw_column(column_name):
            base_column_names.add(column_name)
        else:
            transformed_column = ctx.transformed_columns[column_name]
            for name in ctx.extract_column_names(transformed_column["input"]):
                base_column_names.add(name)

    return [ctx.raw_columns[name] for name in base_column_names]