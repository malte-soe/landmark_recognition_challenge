import os

import torch
from absl import flags
from torch import nn
from torch.hub import load_state_dict_from_url
from torchvision import models

from utils import layers

flags.DEFINE_enum(
    "model", "imagenet", ["imagenet", "places365"], "Pretrained model to use"
)
FLAGS = flags.FLAGS


class ResNet(models.resnet.ResNet):
    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        return x


def _resnet(arch, block, layers, pretrained, progress, **kwargs):
    model = ResNet(block, layers, **kwargs)
    if pretrained:
        state_dict = load_state_dict_from_url(
            models.resnet.model_urls[arch], progress=progress
        )
        model.load_state_dict(state_dict)
    return model


def resnet50(pretrained=False, progress=True, **kwargs):
    """Constructs a ResNet-50 model.
    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
        progress (bool): If True, displays a progress bar of the download to stderr
    """
    return _resnet(
        "resnet50",
        models.resnet.Bottleneck,
        [3, 4, 6, 3],
        pretrained,
        progress,
        **kwargs
    )


def resnet50_places365():
    model_file = "resnet50_places365.pth.tar"
    if not os.access(model_file, os.W_OK):
        weight_url = (
            "http://places2.csail.mit.edu/models_places365/" + model_file
        )
        os.system("wget " + weight_url)

    model = resnet50(num_classes=365)
    checkpoint = torch.load(
        model_file, map_location=lambda storage, loc: storage
    )
    state_dict = {
        str.replace(k, "module.", ""): v
        for k, v in checkpoint["state_dict"].items()
    }
    model.load_state_dict(state_dict)
    return model


def build_model(out_dim=1024):
    if FLAGS.model == "imagenet":
        model = nn.Sequential(
            resnet50(pretrained=True),
            layers.Lambda(lambda x: x.flatten(start_dim=1)),
            nn.Linear(2048 * 7 * 7, out_dim),
        )
    elif FLAGS.model == "places365":
        model = nn.Sequential(
            resnet50_places365(),
            layers.Lambda(lambda x: x.flatten(start_dim=1)),
            nn.Linear(2048 * 7 * 7, out_dim),
        )
    return model
