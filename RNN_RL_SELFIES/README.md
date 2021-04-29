# RNN and RL model for molecular generation
Models and codes for the paper: 
[Molecular Generation Targeting Desired Electronic Properties via Deep Generative Models](https://chemrxiv.org/articles/Molecular_Generation_Targeting_Desired_Electronic_Properties_via_Deep_Generative_Models/9913865)

Prior model adapted and modified from https://arxiv.org/abs/1704.07555
## Requirements

Python 3.6

PyTorch 0.1.12

RDkit (my-rdkit-env)

Scikit-Learn (for QSAR scoring function)

tqdm (for training Prior)

## Usage
First, we must translate our SMILES strings into SELFIES strings and generate a vocabulary from those SELFIES strings to train our model with. To do this, run:

python data_structs.py mols.smi Voc_danish danish.smi 

where
- mols.smi - the SMILES file on which you want to train
- Voc_danish - the SELFIES file we are writing the vocabulary to (this will be placed in the data folder)
- danish.smi - the SELFIES file to which we are writing the translated strings (this will be a file containing all the same molecules as mols.smi but translated into SELFIES strings and will be placed in the data folder)

Next, we want to train our Prior model and save it in our data folder. To do this, run:

python train_prior.py data/Voc_danish data/SELFIES_danish.smi

where
- data/Voc_danish - the vocabulary we created from running data_structs.py as above
- data/SELFIES_danish.smi - the SELFIES file we created from running data_structs.py as above

To do transfer learning on a target dataset, use transfer_userinpt.py.



