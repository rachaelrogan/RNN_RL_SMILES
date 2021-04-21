def main(Training, Transfer):
    with open(Transfer, 'r') as f:
        Train_List = []
        for i, line in enumerate(f):
            Train_List.append(line)
    with open(Transfer, 'r') as f:
        Transfure_List = []
        for i, line in enumerate(f):
            Transfure_List.append(line)
    master = []
    for i in Transfure_List:
        if i in Train_List:
            master.append(i)
    with open("LIMITED_" + Transfer, 'w+') as f:
        for i in master:
            f.write(str(i))

if __name__ == "__main__":
    main("LIMITED_Training_Database.smiles", "Transfure_Database.csv")