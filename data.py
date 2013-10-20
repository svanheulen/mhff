import argparse
import array
import os


def extract_data(data_file, out_path):
    with open(data_file, 'rb') as data:
        toc_size = array.array('I', data.read(4))[0] * 2048
        file_size = data.seek(0, os.SEEK_END)
        data.seek(0)
        temp = array.array('I', data.read(toc_size))
        file_count = temp.index(file_size // 2048)
        toc = []
        for i in range(file_count):
            toc.append([temp[i] * 2048, (temp[i+1] - temp[i]) * 2048])
        for i in range(file_count + 1, len(temp), 2):
            if temp[i] >= file_count:
                break
            toc[temp[i]][1] = temp[i+1]
        for i in range(len(toc)):
            data.seek(toc[i][0])
            open(os.path.join(out_path, '%04d' % i), 'wb').write(data.read(toc[i][1]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extracts all files from the DATA.BIN file from Monster Hunter')
    parser.add_argument('datafile', help='DATA.BIN file to extract')
    parser.add_argument('outpath', nargs='?', default='', help='path to extract to')
    args = parser.parse_args()
    extract_data(args.datafile, args.outpath)

