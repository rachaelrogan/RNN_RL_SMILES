import numpy as np
import random
import re
import pickle
from rdkit import Chem
import sys
import time
import math
import torch
from torch.utils.data import Dataset
import selfies
from smiles_to_selfies import convert

from utils import Variable

class Vocabulary(object):
    """A class for handling encoding/decoding from SMILES to an array of indices"""
    def __init__(self, init_from_file=None, max_length=140):
        self.special_tokens = ['EOS', 'GO']
        self.additional_chars = set()
        self.chars = self.special_tokens
        self.vocab_size = len(self.chars)
        self.vocab = dict(zip(self.chars, range(len(self.chars))))
        self.reversed_vocab = {v: k for k, v in self.vocab.items()}
        self.max_length = max_length
        if init_from_file: self.init_from_file(init_from_file)

    def encode(self, char_list):
        """Takes a list of characters (eg '[NH]') and encodes to array of indices"""
        smiles_matrix = np.zeros(len(char_list), dtype=np.float32)
        for i, char in enumerate(char_list):
            if char in self.vocab:
                smiles_matrix[i] = self.vocab[char]

        return smiles_matrix

    def decode(self, matrix): ### change to SELFIES
        """Takes an array of indices and returns the corresponding SMILES"""
        chars = []
        for i in matrix:
            if i == self.vocab['EOS']: break
            chars.append(self.reversed_vocab[i])
        smiles = "".join(chars)
        smiles = smiles.replace("L", "Cl").replace("R", "Br")
        return smiles

    def tokenize(self, smiles): ### change to SELFIES
        """Takes a SMILES and return a list of characters/tokens"""
        regex = '(\[[^\[\]]{1,6}\])'
        # smiles = replace_halogen(smiles)
        char_list = re.split(regex, smiles)
        tokenized = []
        for char in char_list:
            if char.startswith('['):
                tokenized.append(char)
            else:
                chars = [unit for unit in char]
                [tokenized.append(unit) for unit in chars]
        tokenized.append('EOS')
        return tokenized

    def add_characters(self, chars):
        """Adds characters to the vocabulary"""
        for char in chars:
            self.additional_chars.add(char)
        char_list = list(self.additional_chars)
        char_list.sort()
        self.chars = char_list + self.special_tokens
        self.vocab_size = len(self.chars)
        self.vocab = dict(zip(self.chars, range(len(self.chars))))
        self.reversed_vocab = {v: k for k, v in self.vocab.items()}

    def init_from_file(self, file):
        """Takes a file containing \n separated characters to initialize the vocabulary"""
        with open(file, 'r') as f:
            chars = f.read().split()
        self.add_characters(chars)

    def __len__(self):
        return len(self.chars)

    def __str__(self):
        return "Vocabulary containing {} tokens: {}".format(len(self), self.chars)

class MolData(Dataset): ### change to SELFIES
    """Custom PyTorch Dataset that takes a file containing SMILES.

        Args:
                fname : path to a file containing \n separated SMILES.
                voc   : a Vocabulary instance

        Returns:
                A custom PyTorch dataset for training the Prior.
    """
    def __init__(self, fname, voc):
        self.voc = voc
        self.smiles = []
        with open(fname, 'r',encoding='utf-8-sig') as f:
            for line in f:
                self.smiles.append(line.split()[0])

    def __getitem__(self, i):
        mol = self.smiles[i]
        # tokenized = self.voc.tokenize(mol)
        # encoded = self.voc.encode(tokenized)
        vocab_stoi = {}
        with open("data/Voc_danish", 'r')as f:
            dic = f.readlines()
        for i in range(0,len(dic)):
            vocab_stoi[(dic[i].strip())] = i
        pad_to_len = selfies.len_selfies(mol)
        # needs to be the second argument into selfies.selfies_to_encoding; should this be the length of the vocabulary or the selfies string itself? - I belive the vocab.. I may be very wrogn on that through
        #  :param vocab_stoi: a dictionary that maps SELFIES symbols (the keys) to a non-negative index. The indices of the dictionary must contiguous, starting from 0. ^ I think that makes sense because we want them all to be the same length? - Yes? :)
        
        encoded = selfies.selfies_to_encoding(mol, vocab_stoi=vocab_stoi, pad_to_len=pad_to_len, enc_type="label")
        encoded = np.array(encoded, dtype=float)
        if encoded is not None:
            return Variable(encoded)

    def __len__(self):
        return len(self.smiles)

    def __str__(self):
        return "Dataset containing {} structures.".format(len(self))

    @classmethod
    def collate_fn(cls, arr):
        """Function to take a list of encoded sequences and turn them into a batch"""
        max_length = max([seq.size(0) for seq in arr])
        collated_arr = Variable(torch.zeros(len(arr), max_length))
        for i, seq in enumerate(arr):
            collated_arr[i, :seq.size(0)] = seq
        return collated_arr


def replace_halogen(string):
    """Regex to replace Br and Cl with single letters"""
    br = re.compile('Br')
    cl = re.compile('Cl')
    string = br.sub('R', string)
    string = cl.sub('L', string)

    return string

def tokenize(smiles): ### change to SELFIES
    """Takes a SMILES string and returns a list of tokens.
    This will swap 'Cl' and 'Br' to 'L' and 'R' and treat
    '[xx]' as one token."""
    regex = '(\[[^\[\]]{1,6}\])'
    smiles = replace_halogen(smiles)
    char_list = re.split(regex, smiles)
    tokenized = []
    for char in char_list:
        if char.startswith('['):
            tokenized.append(char)
        else:
            chars = [unit for unit in char]
            [tokenized.append(unit) for unit in chars]
    tokenized.append('EOS')
    return tokenized

def canonicalize_smiles_from_file(fname): ### change to SELFIES
    # """Reads a SMILES file and returns a list of RDKIT SMILES"""
    # with open(fname, 'r') as f:
    #     smiles_list = []
    #     for i, line in enumerate(f):
    #         #print("i: ", i)
    #         if i % 100000 == 0:
    #             print("{} lines processed.".format(i))
    #         smiles = line.split(" ")[0]
    #         mol = Chem.MolFromSmiles(smiles)
    #         if filter_mol(mol):
    #             smiles_list.append(Chem.MolToSmiles(mol))
    #     print("{} SMILES retrieved".format(len(smiles_list)))
    #     #print("smiles_list: ", smiles_list)
    #     return smiles_list
    """Reads a SMILES file and returns a list of SELFIES strings"""
    # encoder returning None: https://selfies-mirror.readthedocs.io/en/latest/selfies.html
    # Either the molecules we are dealing with are not able to be changed to SELFIES at all, 
    # or we must change the semantic constraints of selfies? (This didn't work based on how
    # I implemented it.)
    with open(fname, 'r') as f:
        selfies_list = []
        # default_constraints = selfies.get_semantic_constraints()
        # new_constraints = default_constraints
        # new_constraints['O'] = 4
        # new_constraints['C'] = 8
        # selfies.set_semantic_constraints(new_constraints)  # update constraints
        # print("constraints: ", selfies.get_semantic_constraints())
        for i, line in enumerate(f):
            smiles = line.split(" ")[0]
            mol = Chem.MolFromSmiles(smiles)
            if filter_mol(mol):  
                encoded = convert(smiles)
                # print("encoded: ", encoded)
                selfies_list.append(encoded)
        print("{} SMILES retrieved".format(len(selfies_list)))
        return selfies_list



def filter_mol(mol, max_heavy_atoms=50, min_heavy_atoms=10, element_list=[6,7,8,9,16,17,35,33,51]):
    """Filters molecules on number of heavy atoms and atom types"""
    if mol is not None:
        num_heavy = min_heavy_atoms<mol.GetNumHeavyAtoms()<max_heavy_atoms
        elements = all([atom.GetAtomicNum() in element_list for atom in mol.GetAtoms()])
        #if num_heavy and elements: remove the limit of elementlist for donor-acceptors
        if num_heavy:
            return True
        else:
            return False

def write_smiles_to_file(smiles_list, fname): ### convert from SELFIES to SMILES first
    """Write a list of SMILES to a file."""
    with open(fname, 'w') as f:
        for smiles in smiles_list:
            f.write(smiles + "\n")

def filter_on_chars(smiles_list, chars): ### change to SELFIES = ?
    """Filters SMILES on the characters they contain.
       Used to remove SMILES containing very rare/undesirable
       characters."""
    smiles_list_valid = []
    for smiles in smiles_list:
        tokenized = tokenize(smiles)
        if all([char in chars for char in tokenized][:-1]):
            smiles_list_valid.append(smiles)
    return smiles_list_valid

def filter_file_on_chars(smiles_fname, voc_fname): ### change to SELFIES
    """Filters a SMILES file using a vocabulary file.
       Only SMILES containing nothing but the characters
       in the vocabulary will be retained."""
    smiles = []
    with open(smiles_fname, 'r') as f:
        for line in f:
            smiles.append(line.split()[0])
    chars = []
    with open(voc_fname, 'r') as f:
        for line in f:
            chars.append(line.split()[0])
    valid_smiles = filter_on_chars(smiles, chars)
    with open(smiles_fname + "_filtered", 'w') as f:
        for smiles in valid_smiles:
            f.write(smiles + "\n")

def combine_voc_from_files(fnames):
    """Combine two vocabularies"""
    chars = set()
    for fname in fnames:
        with open(fname, 'r') as f:
            for line in f:
                chars.add(line.split()[0])
    with open("_".join(fnames) + '_combined', 'w') as f:
        for char in chars:
            f.write(char + "\n")

def construct_vocabulary(selfies_list, fname): ### change to SELFIES
    """Returns all the characters present in a SMILES file.
       Uses regex to find characters/tokens of the format '[x]'."""
    # add_chars = set()
    # for i, smiles in enumerate(smiles_list):
    #     regex = '(\[[^\[\]]{1,6}\])'
    #     smiles = replace_halogen(smiles)
    #     char_list = re.split(regex, smiles)
    #     for char in char_list:
    #         if char.startswith('['):
    #             add_chars.add(char)
    #         else:
    #             chars = [unit for unit in char]
    #             [add_chars.add(unit) for unit in chars]

    # add_chars = []
    add_chars = set()
    for selfie in selfies_list:
        # add_chars.append(selfies.get_alphabet_from_selfies(selfie))
        symbols = selfies.split_selfies(selfie)
        for symbol in symbols:
            add_chars.add(symbol)

    print("Number of characters: {}".format(len(add_chars)))
    with open(fname, 'w') as f:
        for char in add_chars:
            f.write(char + "\n")
    return add_chars

def can_smi_file(fname):
    """

    Args:
        fname:

    Returns:

    """
    out = open(fname+'cano', 'w')
    with open (fname) as f:
        for line in f:
            smi = line.rstrip()
            can_smi = Chem.MolToSmiles(Chem.MolFromSmiles(smi))
            out.write(can_smi + '\n')
    out.close()


def batch_iter(data, batch_size=128, shuffle=True):
    batch_num = math.ceil(len(data)/batch_size)
    idx_arr = list(range(len(data)))
    if shuffle:
        np.random.shuffle(idx_arr)
    for i in range(batch_num):
        indices= idx_arr[i*batch_size: (i+1)*batch_size]
        examples = [data[idx] for idx in indices]
        examples = sorted(examples, key=lambda e:len(e), reverse=True)
        yield i, examples


def pad_seq(seqs):
    batch_size = len(seqs)
    seq_lengths = torch.LongTensor(list(map(len,seqs)))
    max_length = len(seqs[0])
    pad_seq = torch.zeros(batch_size, max_length,dtype=torch.long)
    for i, seq in enumerate(seqs):
        pad_seq[i, :len(seq)] = seq
    return seq_lengths,pad_seq

def mask_seq(seqs, seq_lens):
    mask = torch.zeros(seqs.size(0),seqs.size(1))
    for i, length in enumerate(seq_lens):
        mask[i, 0:length] = seqs[i, 0:length]
    return mask

def write_selfies_to_file(file, selfies_strings):
    with open("./data/SELFIES_" + file, 'w+') as f:
        for i in selfies_list:
            if i != None:
                f.write(str(i) + "\n")

if __name__ == "__main__":
    smiles_file = sys.argv[1] # the SMILES file we are translating from   mols.smi
    selfies_vocab_file = sys.argv[2] # the SELFIES file we are writing the vocabulary to   ./data/Voc_danish
    empty_selfies_file = sys.argv[3] # ./data/danish.smi
    selfies_vocab_file = 'data/' + selfies_vocab_file
    print("Reading smiles...")
    selfies_list = canonicalize_smiles_from_file(smiles_file)
    # print("selfies_list", selfies_list)
    print("Constructing vocabulary...")
    voc_chars = construct_vocabulary(selfies_list, selfies_vocab_file)
    write_selfies_to_file(empty_selfies_file, selfies_list)
    # write_smiles_to_file(selfies_list, "data/danish.smi")


# python data_structs.py mols.smi Voc_danish danish.smi