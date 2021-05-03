#!usr/bin/env python
import sys
import torch
from torch.utils.data import DataLoader
import pickle
from rdkit import Chem, rdBase
from tqdm import tqdm
import selfies
from data_structs import MolData, Vocabulary
from model import RNN
from utils import Variable, decrease_learning_rate
rdBase.DisableLog('rdApp.error')


def pretrain(vocab_file, data_file, restore_from=None):
    "Train the Prior RNN"
    voc = Vocabulary(init_from_file=vocab_file)
    moldata = MolData(data_file, voc)
    data = DataLoader(moldata, batch_size=10, shuffle=True, drop_last=True,
                     collate_fn=MolData.collate_fn)
    Prior = RNN(voc)
    if restore_from:
        Prior.rnn.load_state_dict(torch.loag(restore_from))

    optimizer = torch.optim.Adam(Prior.rnn.parameters(), lr=0.001)

    for epoch in range(1, 6):
        # When training on a few million compounds, this model converges
        # in a few of epochs or even faster. If model sized is increased
        # its probably a good idea to check loss against an external set of
        # validation SMILES to make sure we dont overfit too much.
        for step, batch in tqdm(enumerate(data), total=len(data)):
            
            # Sample from Dataloader
            seqs = batch.long()

            # Calculate loss
            log_p, _ = Prior.likelihood(seqs)
            loss = - log_p.mean()

            # Calculate gradients and take a step
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            # Every 500 steps we decrease learning rate and print some information
            if step % 100 == 0 and step != 0:
                decrease_learning_rate(optimizer, decrease_by=0.03)
                tqdm.write('*'*50)
                tqdm.write("Epoch {:3d}   step {:3d}    loss: {:5.2f}\n".format(epoch, step, loss.data.item()))
                tqdm.write('*'*50 + '\n')
                torch.save(Prior.rnn.state_dict(), 'data/Prior_local.ckpt')
        # Save the prior
        torch.save(Prior.rnn.state_dict(), 'data/Prior_local.ckpt')


if __name__ == '__main__':
    voc_file = sys.argv[1] 
    dataset_file = sys.argv[2] 
    pretrain(voc_file, dataset_file)