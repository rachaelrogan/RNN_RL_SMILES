#!/usr/bin/env python

import torch
from torch.utils.data import DataLoader
import pickle
from rdkit import Chem
from rdkit import rdBase
from tqdm import tqdm
from rdkit.Chem import AllChem
from data_structs import MolData, Vocabulary
from model import RNN
from utils import Variable, decrease_learning_rate, unique
import torch.nn as nn
import argparse
import pandas as pd
rdBase.DisableLog('rdApp.error')
import selfies


def cano_selfies_file(fname, outfn):
    """
    canonicalize smile file
    Args:
        fname: location of file containing the SMILES structures
        outfn: Filename for output Canolized SMILES

    Returns: None

    """
    out = open(outfn, 'w')
    with open (fname) as f:
        for line in f:
            smi = line.rstrip()
            can_smi = Chem.MolToSmiles(Chem.MolFromSmiles(smi))
            out.write(can_smi + '\n')
    out.close()


def train_model(voc_dir, smi_dir, prior_dir, tf_dir,tf_process_dir,freeze=False):
    """
    Transfer learning on target molecules using the SMILES structures
    Args:
        voc_dir: location of the vocabulary
        smi_dir: location of the SMILES file used for transfer learning
        prior_dir: location of prior trained model to initialize transfer learning
        tf_dir: location to save the transfer learning model
        tf_process_dir: location to save the SMILES sampled while doing transfer learning
        freeze: Bool. If true, all parameters in the RNN will be frozen except for the last linear layer during
        transfer learning.

    Returns: None

    """
    voc = Vocabulary(init_from_file=voc_dir)
    moldata = MolData(smi_dir, voc)
    data = DataLoader(moldata, batch_size=10, shuffle=True, drop_last=False,
                      collate_fn=MolData.collate_fn)
    transfer_model = RNN(voc)
    if freeze:
        for param in transfer_model.rnn.parameters():
            param.requires_grad = False
        transfer_model.rnn.linear = nn.Linear(512, voc.vocab_size)
    # if torch.cuda.is_available():
    #     transfer_model.rnn.load_state_dict(torch.load(prior_dir))
    # else:
    transfer_model.rnn.load_state_dict(torch.load(prior_dir,
                                                    map_location=lambda storage, loc: storage))

    optimizer = torch.optim.Adam(transfer_model.rnn.parameters(), lr=0.0005)

    smi_lst = []; epoch_lst = []
    for epoch in range(1, 11):

        # SELFIES RUN ISSUE 1: This was the beginning of the problem, when we were pulling from data
        for step, batch in tqdm(enumerate(data), total=len(data)):
            seqs = batch.long()
            if len(seqs.tolist()) != 0:
                
                log_p, _ = transfer_model.likelihood(seqs)
                loss = -log_p.mean()
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                if step % 80 == 0 and step != 0:
                    decrease_learning_rate(optimizer, decrease_by=0.03)
                    tqdm.write('*'*50)
                    tqdm.write("Epoch {:3d}   step {:3d}    loss: {:5.2f}\n".format(epoch, step, loss.data.item()))
                    tqdm.write("*"*50 + '\n')
                    torch.save(transfer_model.rnn.state_dict(), tf_dir)
        seqs, likelihood, _ = transfer_model.sample(1024)
        valid = 0
        for i, seq in enumerate(seqs.cpu().numpy()):
            for a in range(seq.size):
                if seq[a] == 46 or seq[a]== 45 or a == seq.size-1: # I had to change this to 46 and 45 because the vocab size is different than from mol.smi (these are, I think, GO and EOS)
                    selfie = selfies.encoding_to_selfies(seq[:a], vocab_itos=moldata.vocab_itos, enc_type="label")
                    smile = selfies.decoder(selfie) 
                    if Chem.MolFromSmiles(smile):
                        try:
                            AllChem.GetMorganFingerprintAsBitVect(Chem.MolFromSmiles(smile), 2, 1024)
                            valid += 1
                            smi_lst.append(smile)
                            epoch_lst.append(epoch)
                        except:
                            continue
                    break

        torch.save(transfer_model.rnn.state_dict(), tf_dir)

    transfer_process_df = pd.DataFrame(columns=['SELFIES', 'Epoch'])
    transfer_process_df['SELFIES'] = pd.Series(data=smi_lst)
    transfer_process_df['Epoch'] = pd.Series(data=epoch_lst)
    transfer_process_df.to_csv(tf_process_dir)


def sample_smiles(voc_dir, nums, outfn,tf_dir, until=False):
    """Sample smiles using the transferred model"""
    voc = Vocabulary(init_from_file=voc_dir)
    transfer_model = RNN(voc)
    output = open(outfn, 'w')

    # if torch.cuda.is_available():
    #     transfer_model.rnn.load_state_dict(torch.load(tf_dir))
    # else:
    transfer_model.rnn.load_state_dict(torch.load(tf_dir,
                                                map_location=lambda storage, loc:storage))
    for param in transfer_model.rnn.parameters():
        param.requires_grad = False

    if not until:

        seqs, likelihood, _ = transfer_model.sample(nums)
        valid = 0
        double_br = 0
        unique_idx = unique(seqs)
        seqs = seqs[unique_idx]
        for i, seq in enumerate(seqs.cpu().numpy()):

            smile = voc.decode(seq)
            if Chem.MolFromSmiles(smile):
                try:
                    AllChem.GetMorganFingerprintAsBitVect(Chem.MolFromSmiles(smile), 2, 1024)
                    valid += 1
                    output.write(smile+'\n')
                except:
                    continue
        tqdm.write('\n{} molecules sampled, {} valid SMILES, {} with double Br'.format(nums, valid, double_br))
        output.close()
    else:
        valid = 0
        n_sample = 0
        while valid < nums:
            seq, likelihood, _ = transfer_model.sample(1)
            n_sample += 1
            seq = seq.cpu().numpy()
            seq = seq[0]
            smile = voc.decode(seq)
            if Chem.MolFromSmiles(smile):
                try:
                    AllChem.GetMorganFingerprintAsBitVect(Chem.MolFromSmiles(smile), 2, 1024)
                    valid += 1
                    output.write(smile + '\n')
                except:
                    continue
        tqdm.write('\n{} valid molecules sampled, with {} of total samples'.format(nums, n_sample))



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transfer learning for SMILES generation")
    parser.add_argument('--task', action='store', dest='task', choices=['train_model', 'sample_smiles'],
                        default='train_model',help='What task to perform')
    parser.add_argument('--voc', action='store', dest='voc_dir',
                        default='data/Voc_danish', help='Directory for the vocabulary')
    parser.add_argument('--smi', action='store', dest='smi_dir', default='LIMITED_Transfure_Database.csv',
                        help='Directory of the SMILES file for tranfer learning')
    parser.add_argument('--prior_model', action='store', dest='prior_dir', default='data/Prior_local.ckpt',
                        help='Directory of the prior trained RNN')
    parser.add_argument('--tf_model',action='store', dest='tf_dir', default='data/Prior_local.ckpt',
                        help='Directory of the transfer model')
    parser.add_argument('--nums', action='store', dest='nums', default='1024',
                        help='Number of SMILES to sample for transfer learning')
    parser.add_argument('--save_smi',action='store',dest='save_dir',default='SELFIES_transfer_save_smi.csv',
                        help='Directory to save the generated SMILES')
    parser.add_argument('--save_process_smi',action='store',dest='tf_process_dir',default='SELFIES_transfer_process_smi_transfer_Database.csv',
                        help='Directory to save the generated SMILES')
    arg_dict = vars(parser.parse_args())
    task_, voc_, smi_, prior_, tf_, nums_, save_smi_, tf_process_dir_ = arg_dict.values()

    if task_ == 'train_model':
        train_model(voc_dir=voc_, smi_dir=smi_, prior_dir=prior_, tf_dir=tf_,
                    tf_process_dir=tf_process_dir_,freeze=False)
    if task_ == 'sample_smiles':
        sample_smiles(voc_, nums_,save_smi_,tf_, until=False)


