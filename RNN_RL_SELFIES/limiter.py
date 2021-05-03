import sys

def main(file):
    with open(file, 'r') as f:
        selfies_list = []
        for i, line in enumerate(f):
            if (i < 5000):
                selfies_list.append(line)
    for i in selfies_list:
        if(i == None):
            selfies_list.remove(i)
    with open("LIMITED_" + file, 'w+') as f:
        for i in selfies_list:
            f.write(str(i))
if __name__ == "__main__":
    file = sys.argv[1]
    main(file)