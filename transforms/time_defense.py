'''
    part of code from https://github.com/SpeakerGuard/SpeakerGuard
'''
import numpy as np
import torch
import math
import torch
import torch.nn.functional as F

class TimeDomainDefense(): 

    def __init__(self, defense_type: str, *args) -> None:

        self.defense_type = defense_type
    
    def __call__(self, x, *args):

        if self.defense_type == 'AT':
            output = AT(x)
        elif self.defense_type == 'AS':
            output = AS(x)
        elif self.defense_type == 'MS':
            output = MS(x)
        else:
            raise NotImplementedError(f'Unknown defense type: {self.defense_type}!')
        return output
    
    def _get_name(self, *args):

        if self.defense_type == 'AT':
            name = 'Audio_Turbulence'
        elif self.defense_type == 'AS':
            name = 'Average_Smoothing'
        elif self.defense_type == 'MS':
            name = 'Median_Smoothing'
        else:
            raise NotImplementedError(f'Unknown defense type: {self.defense_type}!')
        return name

def AT(audio, param=25, same_size=True):

    assert torch.is_tensor(audio) == True
    ori_shape = audio.shape
    if len(audio.shape) == 1:
        audio = audio.unsqueeze(0) # (T, ) --> (1, T)
    elif len(audio.shape) == 2: # (B, T)
        pass
    elif len(audio.shape) == 3:
        audio = audio.squeeze(1) # (B, 1, T) --> (B, T)
    else:
        raise NotImplementedError('Audio Shape Error')

    snr = param
    snr = 10 ** (snr / 10)
    batch, N = audio.shape
    power_audio = torch.sum((audio / math.sqrt(N)) ** 2, dim=1, keepdims=True) # (batch, 1)
    power_noise = power_audio / snr # (batch, 1)
    noise = torch.randn((batch, N), device=audio.device) * torch.sqrt(power_noise) # (batch, N)
    noised_audio = audio + noise
    return noised_audio.view(ori_shape)

def AS(audio, param=3, same_size=True):

    assert torch.is_tensor(audio) == True
    ori_shape = audio.shape
    if len(audio.shape) == 1:
        audio = audio.unsqueeze(0) # (T, ) --> (1, T)
    elif len(audio.shape) == 2: # (B, T)
        pass
    elif len(audio.shape) == 3:
        audio = audio.squeeze(1) # (B, 1, T) --> (B, T)
    else:
        raise NotImplementedError('Audio Shape Error')

    batch, _ = audio.shape

    kernel_size = param
    assert kernel_size % 2 == 1
    audio = audio.view(batch, 1, -1) # (batch, in_channel:1, max_len)

    ################# Using torch.nn.functional ###################
    kernel_weights = np.ones(kernel_size) / kernel_size
    weight = torch.tensor(kernel_weights, dtype=torch.float, device=audio.device).view(1, 1, -1) # (out_channel:1, in_channel:1, kernel_size)
    output = F.conv1d(audio, weight, padding=(kernel_size-1)//2) # (batch, 1, max_len)
    ###############################################################

    return output.squeeze(1).view(ori_shape) # (batch, max_len)


def MS(audio, param=3, same_size=True):
    r"""
    Apply median smoothing to the 1D tensor over the given window.
    """

    assert torch.is_tensor(audio) == True
    ori_shape = audio.shape
    if len(audio.shape) == 1:
        audio = audio.unsqueeze(0) # (T, ) --> (1, T)
    elif len(audio.shape) == 2: # (B, T)
        pass
    elif len(audio.shape) == 3:
        audio = audio.squeeze(1) # (B, 1, T) --> (B, T)
    else:
        raise NotImplementedError('Audio Shape Error')

    win_length = param
    # Centered windowed
    pad_length = (win_length - 1) // 2

    # "replicate" padding in any dimension
    audio = F.pad(audio, (pad_length, pad_length), mode="constant", value=0.)

    # indices[..., :pad_length] = torch.cat(pad_length * [indices[..., pad_length].unsqueeze(-1)], dim=-1)
    roll = audio.unfold(-1, win_length, 1)

    values, _ = torch.median(roll, -1)
    return values.view(ori_shape)