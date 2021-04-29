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

    # Reads vocabulary from a file
    # voc = Vocabulary(init_from_file="data/Voc")
    # voc = Vocabulary(init_from_file="mols.smi")
    voc = Vocabulary(init_from_file=vocab_file)

    # Create a Dataset from a SMILES file
    # moldata = MolData("data/ChEMBL_filtered", voc)
    # moldata = MolData("data/danish.smi", voc)
    # moldata = MolData("data/Voc_danish_Selfies_mol", voc) # needs to be the translated SELFIES file
    moldata = MolData(data_file, voc)
    data = DataLoader(moldata, batch_size=1, shuffle=True, drop_last=True,
                     collate_fn=MolData.collate_fn)

    # print("data", data)
    print("in pretrain(), voc: ", voc)
    Prior = RNN(voc)

    # Can restore from a  saved RNN
    if restore_from:
        Prior.rnn.load_state_dict(torch.loag(restore_from))

    optimizer = torch.optim.Adam(Prior.rnn.parameters(), lr=0.001)

    for epoch in range(1, 6):
        # When training on a few million compounds, this model converges
        # in a few of epochs or even faster. If model sized is increased
        # its probably a good idea to check loss against an external set of
        # validation SMILES to make sure we dont overfit too much.
        # print("len(data)", len(data))
        # print("data", data)
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
            if step % 10 == 0 and step != 0:
                decrease_learning_rate(optimizer, decrease_by=0.03)
                tqdm.write('*'*50)
                tqdm.write("Epoch {:3d}   step {:3d}    loss: {:5.2f}\n".format(epoch, step, (loss.data.ndimension())))
                seqs, likelihood, _ = Prior.sample(128)
                valid = 0
                for i, seq in enumerate(seqs.cpu().numpy()): # did we deicde we didn't need this? - We do still need the if statment to determin valid strings, becuase were not handling them as selfies strings until we convert them back
                    # print("seq", seq)
                    smile = voc.decode(seq)
                    # print("smile", smile)
                    if selfies.decoder(smile.strip()) != None:
                        valid += 1
                    # if i < 5:
                    #     tqdm.write(smile) Does this do anything other then print the smile string to console?
                tqdm.write("\n{:>4.1f}% valid SELFIES".format(100 * valid / len(seqs)))
                tqdm.write('*'*50 + '\n')
                torch.save(Prior.rnn.state_dict(), 'data/Prior_local.ckpt')
        # Save the prior
        torch.save(Prior.rnn.state_dict(), 'data/Prior_local.ckpt')


if __name__ == '__main__':
    voc_file = sys.argv[1] # the vocabulary created from data_structs.py
    dataset_file = sys.argv[2] # the SELFIES file that was generated in data_structs.py
    pretrain(voc_file, dataset_file)


#  python train_prior.py data/Voc_danish data/SELFIES_danish.smi