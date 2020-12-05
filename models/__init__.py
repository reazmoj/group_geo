from __future__ import absolute_import

from .ResNetGcn_siamese_relative_part_1 import *


__factory = {
    'resnet50gcn_siamese_relative_part_1': ResNet50Gcn_siamese_relative_part_1
}

def get_names():
    return __factory.keys()

def init_model(name, *args, **kwargs):
    if name not in __factory.keys():
        raise KeyError("Unknown model: {}".format(name))
    return __factory[name](*args, **kwargs)
