import selfies
import sys

def convert(smile_string):
    return selfies.encoder(str(smile_string.strip()),print_error=True)
def main(file):
    with open(file, 'r') as f:
        selfies_list = []
        for i, line in enumerate(f):
            selfies_list.append(convert(line))
    for i in selfies_list:
        if(i == None):
            selfies_list.remove(i)
    with open("SELFIES_" + file, 'w+') as f:
        for i in selfies_list:
            f.write(str(i) + "\n")

if __name__ == "__main__":
    file = sys.argv[1]
    main(file)