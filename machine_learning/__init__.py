from machine_learning.PipelineManager import PipelineManager
from machine_learning.cnn import CNN1d
from machine_learning.fusion_autoencoder import FusionAutoencoderManager
from machine_learning.gmm import GMMManager
from machine_learning.rnn import RNN
from machine_learning.svc import EnsembleSVC, SimpleSVC
from machine_learning.transformer import Transformer


MODEL_MAPPING = {
    "EnsembleSVC": EnsembleSVC,
    "SimpleSVC": SimpleSVC,
    "CNN1d": CNN1d,
    "RNN": RNN,
    "Transformer": Transformer,
    "FusionAutoencoderManager": FusionAutoencoderManager,
    "GMMManager": GMMManager,
    "PipelineManager": PipelineManager

}
